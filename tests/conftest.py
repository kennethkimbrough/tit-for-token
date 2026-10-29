"""Shared fakes. No test touches the network."""

from __future__ import annotations

import re

import pytest

from tit_for_token.llm import CompletionRequest, CompletionResponse, TransportError
from tit_for_token.players.model import REMINDER

_THEY = re.compile(r"they chose ([AB])")


class FakeModelTransport:
    """Stands in for a model API. Plays tit-for-tat by reading the history in the prompt.

    ``malformed_every``: every n-th first attempt is answered with prose and no
    JSON, to exercise the retry path. ``stubborn`` makes the retry fail too,
    so the player forfeits. ``fail_first``: raise a retryable error that many
    times before answering, to exercise backoff.
    """

    def __init__(self, malformed_every: int = 0, stubborn: bool = False, fail_first: int = 0, truncate: bool = False) -> None:
        self.calls = 0
        self.failures_left = fail_first
        self.malformed_every = malformed_every
        self.stubborn = stubborn
        self.truncate = truncate  # answer like a reasoning model that spent its whole budget thinking
        self.seen: list[CompletionRequest] = []

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.calls += 1
        self.seen.append(request)
        if self.failures_left > 0:
            self.failures_left -= 1
            raise TransportError("HTTP 429", retryable=True, status=429)
        role, content = request.messages[-1]
        if self.truncate:
            return CompletionResponse(text="", prompt_tokens=len(content) // 4, completion_tokens=request.max_tokens,
                                      latency_ms=5, finish_reason="length", reasoning_tokens=request.max_tokens)
        if content == REMINDER:
            text = "Sorry about that." if self.stubborn else '{"move": "A"}'
        elif self.malformed_every and self.calls % self.malformed_every == 0:
            text = "I will choose option A this round because it seems fair."
        else:
            found = _THEY.findall(content)
            move = found[-1] if found else "A"
            text = f'Thinking about it... {{"move": "{move}"}}'
        return CompletionResponse(text=text, prompt_tokens=len(content) // 4, completion_tokens=12, latency_ms=5)


class ExplodingTransport:
    """Any call is a test failure: used to prove replays never go live."""

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.calls += 1
        raise AssertionError("live call during replay")


@pytest.fixture
def fake_model() -> FakeModelTransport:
    return FakeModelTransport()
