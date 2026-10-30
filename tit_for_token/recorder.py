"""Record every model call so a tournament can be replayed exactly, offline, for free.

The recording is the source of truth: model APIs are not fully deterministic
even at temperature 0, so results are reproduced from what was recorded, not
by asking the model again.

File format: JSON lines, one call per line, ``{"key", "request", "response"}``.
The key is ``CompletionRequest.key()``; the request is stored too so the file
is readable by a person.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from .llm import CompletionRequest, CompletionResponse, Transport


class MissingRecordingError(Exception):
    """A replay asked for a request that was never recorded."""


class Recording:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._responses: dict[str, CompletionResponse] = {}
        self._lock = threading.Lock()
        if self.path.exists():
            with self.path.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        self._responses[entry["key"]] = CompletionResponse.from_dict(entry["response"])

    def __len__(self) -> int:
        return len(self._responses)

    def call_stats(self) -> dict[str, dict]:
        """Per model: call count, latency percentiles, tokens, cut-off answers. Read back from the file."""
        if not self.path.exists():
            return {}
        per_model: dict[str, list[dict]] = {}
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    per_model.setdefault(entry["request"]["model"], []).append(entry["response"])
        stats = {}
        for model, responses in sorted(per_model.items()):
            latencies = sorted(r["latency_ms"] for r in responses)

            def pct(q: float) -> int:
                return latencies[min(len(latencies) - 1, int(q * len(latencies)))]

            stats[model] = {
                "calls": len(responses),
                "latency_ms_p50": pct(0.5),
                "latency_ms_p95": pct(0.95),
                "latency_ms_max": latencies[-1],
                "prompt_tokens": sum(r["prompt_tokens"] for r in responses),
                "completion_tokens": sum(r["completion_tokens"] for r in responses),
                "reasoning_tokens": sum(r.get("reasoning_tokens", 0) for r in responses),
                "cut_off": sum(1 for r in responses if r.get("finish_reason") == "length" and not r["text"].strip()),
                "empty": sum(1 for r in responses if not r["text"].strip()),
            }
        return stats

    def get(self, request: CompletionRequest) -> CompletionResponse | None:
        return self._responses.get(request.key())

    def put(self, request: CompletionRequest, response: CompletionResponse) -> None:
        key = request.key()
        line = json.dumps(
            {"key": key, "request": request.to_record(), "response": response.to_dict()},
            sort_keys=True,
        )
        with self._lock:
            if key in self._responses:
                return
            self._responses[key] = response
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")


class RecordingTransport:
    """Live mode: answer from the recording when the request is already there, otherwise call and record.

    Reusing recorded answers is what makes a resumed run free for the matches
    that already happened, and what makes a repeated request (the same history
    reached twice) return the same answer.
    """

    def __init__(self, inner: Transport, recording: Recording) -> None:
        self._inner = inner
        self._recording = recording
        self.live_calls = 0

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        cached = self._recording.get(request)
        if cached is not None:
            return cached
        response = await self._inner.complete(request)
        self._recording.put(request, response)
        self.live_calls += 1
        return response


class ReplayTransport:
    """Replay mode: never touches the network. A missing request is an error, not a silent live call."""

    def __init__(self, recording: Recording) -> None:
        self._recording = recording

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        cached = self._recording.get(request)
        if cached is None:
            raise MissingRecordingError(
                f"no recorded response for {request.model} (key {request.key()[:12]}); "
                "the recording does not cover this match"
            )
        return cached
