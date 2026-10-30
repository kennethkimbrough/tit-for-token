"""Chat-completion transports: the HTTP client, and the wrappers that add retries, throttling and a budget.

The pieces compose. A live tournament uses::

    Recording(Budgeted(Throttled(Retrying(OpenRouter))))

and a replay uses just ``Replay`` (see ``recorder.py``), so nothing below the
recording layer is touched and nothing costs money.

Only the standard library is used, so the project has no runtime dependencies.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# HTTP calls block, so they run on threads. asyncio's default pool has only min(32, CPUs + 4)
# threads (8 on a 4-core CI machine), which would silently cap the whole tournament at 8 calls
# in flight whatever the per-model limits say. The real limits are the per-model semaphores.
_HTTP_THREADS = ThreadPoolExecutor(max_workers=64, thread_name_prefix="http")
API_KEY_ENV = "OPENROUTER_API_KEY"


@dataclass(frozen=True)
class CompletionRequest:
    model: str
    messages: tuple[tuple[str, str], ...]  # (role, content) pairs
    temperature: float
    max_tokens: int
    tag: str = ""  # which call this is: match, seat, round, attempt; never sent to the API
    reasoning: str | None = None  # OpenRouter reasoning effort ("none", "minimal", "low", ...); None = provider default

    def key(self) -> str:
        """Hash of the request content plus its tag; the recording is keyed by this.

        The tag matters: without it, every match's first round (identical
        prompts) would share one recorded answer, and a model playing itself
        would get the same answer on both sides. Each call must be its own
        sample from the model.
        """
        canonical = json.dumps(
            {
                "tag": self.tag,
                "model": self.model,
                "messages": [list(m) for m in self.messages],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "reasoning": self.reasoning,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode()).hexdigest()

    def to_dict(self) -> dict:
        """The API request body."""
        body = {
            "model": self.model,
            "messages": [{"role": r, "content": c} for r, c in self.messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.reasoning is not None:
            # OpenRouter counts reasoning tokens against max_tokens, so the effort is set explicitly
            # and the reasoning text is left out of the response (it is still billed).
            body["reasoning"] = {"effort": self.reasoning, "exclude": True}
        return body

    def to_record(self) -> dict:
        return {"tag": self.tag, **self.to_dict()}


@dataclass(frozen=True)
class CompletionResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    finish_reason: str = ""  # "stop", "length", ... as reported by the API
    reasoning_tokens: int = 0  # part of completion_tokens spent on hidden reasoning

    @property
    def truncated(self) -> bool:
        """The model hit max_tokens before producing an answer (usually: reasoning used the whole budget)."""
        return self.finish_reason == "length" and not self.text.strip()

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "latency_ms": self.latency_ms,
            "finish_reason": self.finish_reason,
            "reasoning_tokens": self.reasoning_tokens,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CompletionResponse":
        return cls(
            d["text"], d["prompt_tokens"], d["completion_tokens"], d["latency_ms"],
            d.get("finish_reason", ""), d.get("reasoning_tokens", 0),
        )


class Transport(Protocol):
    async def complete(self, request: CompletionRequest) -> CompletionResponse: ...


class TransportError(Exception):
    def __init__(self, message: str, retryable: bool = False, status: int | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status = status


class BudgetExceeded(Exception):
    """Raised before a call that would push spending past the cap."""


class OpenRouterTransport:
    """One POST per completion. The key is read from the environment and never stored anywhere else."""

    def __init__(self, api_key: str | None = None, url: str = OPENROUTER_URL, timeout: float = 60.0) -> None:
        self._key = api_key or os.environ.get(API_KEY_ENV, "")
        if not self._key:
            raise TransportError(f"Set {API_KEY_ENV} to run live; use --replay to run without network.")
        self._url = url
        self._timeout = timeout

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        return await asyncio.get_running_loop().run_in_executor(_HTTP_THREADS, self._post, request)

    def _post(self, request: CompletionRequest) -> CompletionResponse:
        body = json.dumps(request.to_dict()).encode()
        req = urllib.request.Request(
            self._url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/kennethkimbrough/tit-for-token",
                "X-Title": "tit-for-token",
            },
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            retryable = e.code == 429 or e.code >= 500
            raise TransportError(f"HTTP {e.code} from {self._url}", retryable=retryable, status=e.code) from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise TransportError(f"network error: {e}", retryable=True) from e
        latency_ms = int((time.monotonic() - started) * 1000)
        return parse_openai_style(payload, latency_ms)


def parse_openai_style(payload: dict, latency_ms: int) -> CompletionResponse:
    """Read an OpenAI-style chat completion body (OpenRouter uses the same shape)."""
    if "error" in payload and not payload.get("choices"):
        err = payload["error"]
        message = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        raise TransportError(f"API error: {message}", retryable=False)
    try:
        choice = payload["choices"][0]
        text = choice["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise TransportError(f"unexpected response shape: {payload!r}"[:300], retryable=False) from e
    usage = payload.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    return CompletionResponse(
        text=text,
        prompt_tokens=int(usage.get("prompt_tokens", 0)),
        completion_tokens=int(usage.get("completion_tokens", 0)),
        latency_ms=latency_ms,
        finish_reason=str(choice.get("finish_reason") or choice.get("native_finish_reason") or ""),
        reasoning_tokens=int(details.get("reasoning_tokens", 0)),
    )


class RetryingTransport:
    """Exponential backoff with jitter on rate limits, server errors and network failures."""

    def __init__(self, inner: Transport, attempts: int = 5, base_delay: float = 1.0, max_delay: float = 30.0) -> None:
        self._inner = inner
        self._attempts = attempts
        self._base = base_delay
        self._max = max_delay

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        for attempt in range(1, self._attempts + 1):
            try:
                return await self._inner.complete(request)
            except TransportError as e:
                if not e.retryable or attempt == self._attempts:
                    raise
                delay = min(self._max, self._base * 2 ** (attempt - 1)) * (0.5 + random.random())
                await asyncio.sleep(delay)
        raise AssertionError("unreachable")


class ThrottledTransport:
    """At most N calls in flight per provider, so one tournament cannot trip a provider's rate limit."""

    def __init__(self, inner: Transport, concurrency: int) -> None:
        self._inner = inner
        self._sem = asyncio.Semaphore(concurrency)

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        async with self._sem:
            return await self._inner.complete(request)


@dataclass(frozen=True)
class Price:
    """USD per million tokens."""

    input: float
    output: float

    def cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens * self.input + completion_tokens * self.output) / 1_000_000


class Budget:
    """Tracks spending across every transport in a run. Reserves an estimate before each call."""

    def __init__(self, cap_usd: float) -> None:
        self.cap = cap_usd
        self.spent = 0.0
        self.reserved = 0.0
        self.calls = 0
        self._lock = asyncio.Lock()

    async def reserve(self, estimate: float) -> None:
        async with self._lock:
            if self.spent + self.reserved + estimate > self.cap:
                raise BudgetExceeded(
                    f"spending cap of ${self.cap:.2f} would be exceeded "
                    f"(spent ${self.spent:.4f}, reserved ${self.reserved:.4f}, next ~${estimate:.4f})"
                )
            self.reserved += estimate

    async def settle(self, estimate: float, actual: float) -> None:
        async with self._lock:
            self.reserved -= estimate
            self.spent += actual
            self.calls += 1


class BudgetedTransport:
    def __init__(self, inner: Transport, budget: Budget, price: Price) -> None:
        self._inner = inner
        self._budget = budget
        self._price = price

    @staticmethod
    def estimate_prompt_tokens(request: CompletionRequest) -> int:
        chars = sum(len(c) for _, c in request.messages)
        return chars // 3 + 8 * len(request.messages)  # deliberately generous

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        estimate = self._price.cost(self.estimate_prompt_tokens(request), request.max_tokens)
        await self._budget.reserve(estimate)
        actual = 0.0
        try:
            response = await self._inner.complete(request)
            actual = self._price.cost(response.prompt_tokens, response.completion_tokens)
            return response
        finally:
            await self._budget.settle(estimate, actual)
