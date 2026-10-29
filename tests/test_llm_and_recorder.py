import asyncio

import pytest
from conftest import ExplodingTransport, FakeModelTransport

from tit_for_token.llm import (
    Budget,
    BudgetExceeded,
    BudgetedTransport,
    CompletionRequest,
    CompletionResponse,
    Price,
    RetryingTransport,
    ThrottledTransport,
    TransportError,
    parse_openai_style,
)
from tit_for_token.recorder import MissingRecordingError, Recording, RecordingTransport, ReplayTransport


def req(tag="t", content="hello", model="m"):
    return CompletionRequest(model=model, messages=(("user", content),), temperature=0.7, max_tokens=50, tag=tag)


def test_request_key_covers_content_and_tag():
    assert req().key() == req().key()
    assert req(tag="other").key() != req().key()
    assert req(content="x").key() != req().key()
    assert req(model="n").key() != req().key()
    assert "tag" not in req().to_dict(), "the tag is never sent to the API"
    assert req().to_record()["tag"] == "t"


def test_parse_openai_style():
    payload = {"choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
               "usage": {"prompt_tokens": 7, "completion_tokens": 2}}
    r = parse_openai_style(payload, 123)
    assert (r.text, r.prompt_tokens, r.completion_tokens, r.latency_ms) == ("hi", 7, 2, 123)
    assert r.finish_reason == "stop" and not r.truncated

    cut = {"choices": [{"message": {"content": ""}, "finish_reason": "length"}],
           "usage": {"prompt_tokens": 7, "completion_tokens": 50, "completion_tokens_details": {"reasoning_tokens": 50}}}
    r = parse_openai_style(cut, 1)
    assert r.truncated and r.reasoning_tokens == 50
    assert CompletionResponse.from_dict(r.to_dict()) == r
    assert CompletionResponse.from_dict({"text": "x", "prompt_tokens": 1, "completion_tokens": 1, "latency_ms": 1}).finish_reason == ""
    with pytest.raises(TransportError):
        parse_openai_style({"error": {"message": "bad key"}}, 1)
    with pytest.raises(TransportError):
        parse_openai_style({"choices": []}, 1)


def test_retrying_transport_retries_only_retryable_errors(monkeypatch):
    monkeypatch.setattr("tit_for_token.llm.asyncio.sleep", _no_sleep)
    inner = FakeModelTransport(fail_first=2)
    r = asyncio.run(RetryingTransport(inner, attempts=3, base_delay=0).complete(req()))
    assert "move" in r.text and inner.calls == 3

    inner = FakeModelTransport(fail_first=5)
    with pytest.raises(TransportError):
        asyncio.run(RetryingTransport(inner, attempts=3, base_delay=0).complete(req()))
    assert inner.calls == 3

    class Fatal:
        calls = 0

        async def complete(self, request):
            self.calls += 1
            raise TransportError("HTTP 401", retryable=False, status=401)

    fatal = Fatal()
    with pytest.raises(TransportError):
        asyncio.run(RetryingTransport(fatal, attempts=3, base_delay=0).complete(req()))
    assert fatal.calls == 1


async def _no_sleep(_):
    return None


def test_throttled_transport_limits_concurrency():
    class Slow:
        def __init__(self):
            self.in_flight = 0
            self.peak = 0

        async def complete(self, request):
            self.in_flight += 1
            self.peak = max(self.peak, self.in_flight)
            await asyncio.sleep(0.01)
            self.in_flight -= 1
            return CompletionResponse("{}", 1, 1, 1)

    async def go():
        slow = Slow()
        t = ThrottledTransport(slow, concurrency=3)
        await asyncio.gather(*(t.complete(req(tag=str(i))) for i in range(10)))
        return slow.peak

    assert asyncio.run(go()) == 3


def test_budget_reserves_then_settles_and_stops_at_the_cap():
    async def go():
        budget = Budget(cap_usd=0.0001)
        price = Price(input=1000.0, output=1000.0)  # $1 per 1,000 tokens: expensive on purpose
        t = BudgetedTransport(FakeModelTransport(), budget, price)
        with pytest.raises(BudgetExceeded):
            await t.complete(req())
        assert budget.calls == 0 and budget.spent == 0

        budget = Budget(cap_usd=10.0)
        t = BudgetedTransport(FakeModelTransport(), budget, price)
        await t.complete(req(content="x" * 400))
        assert budget.calls == 1
        assert budget.reserved == 0
        assert budget.spent == pytest.approx(price.cost(100, 12))

    asyncio.run(go())


def test_recording_round_trips_through_the_file(tmp_path):
    path = tmp_path / "calls.jsonl"
    rec = Recording(path)
    resp = CompletionResponse('{"move": "A"}', 10, 3, 42)
    rec.put(req(), resp)
    rec.put(req(), CompletionResponse("different", 1, 1, 1))  # second put for the same key is ignored
    assert rec.get(req()) == resp
    assert rec.get(req(tag="other")) is None

    again = Recording(path)
    assert len(again) == 1
    assert again.get(req()) == resp
    assert path.read_text().count("\n") == 1


def test_recording_transport_reuses_and_replay_never_goes_live(tmp_path):
    async def go():
        live = FakeModelTransport()
        rec = Recording(tmp_path / "calls.jsonl")
        t = RecordingTransport(live, rec)
        first = await t.complete(req())
        second = await t.complete(req())
        assert first == second and live.calls == 1 and t.live_calls == 1

        replay = ReplayTransport(Recording(tmp_path / "calls.jsonl"))
        assert await replay.complete(req()) == first
        with pytest.raises(MissingRecordingError):
            await replay.complete(req(tag="never-recorded"))

        exploding = RecordingTransport(ExplodingTransport(), rec)
        assert await exploding.complete(req()) == first  # answered from the recording, never live

    asyncio.run(go())
