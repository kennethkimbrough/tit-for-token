import asyncio
import json

import pytest
from conftest import ExplodingTransport, FakeModelTransport

from tit_for_token.config import config_from_dict
from tit_for_token.llm import Budget
from tit_for_token.recorder import Recording
from tit_for_token.runner import all_match_ids, build_transports, load_matches, pairings, run_tournament

RAW = {
    "name": "t",
    "seed": 7,
    "matches_per_pairing": 2,
    "end_probability": 0.3,
    "spending_cap_usd": 10.0,
    "bots": ["always-cooperate", "always-defect", "tit-for-tat", "grim-trigger", "random"],
    "model_defaults": {"temperature": 0.5, "max_tokens": 40},
    "models": [
        {"name": "m1", "model": "fake/one", "price": {"input_usd_per_million": 1.0, "output_usd_per_million": 5.0}},
        {"name": "m2", "model": "fake/two", "provider": "other", "concurrency": 2},
    ],
}


def cfg(**overrides):
    raw = json.loads(json.dumps(RAW))
    raw.update(overrides)
    return config_from_dict(raw)


def test_config_validation():
    assert cfg().player_names == ("always-cooperate", "always-defect", "tit-for-tat", "grim-trigger", "random", "m1", "m2")
    with pytest.raises(ValueError):
        cfg(bots=["random", "random"])
    with pytest.raises(ValueError):
        cfg(models=[{"name": "bad--name", "model": "x"}])
    with pytest.raises(ValueError):
        cfg(matches_per_pairing=0)


def test_pairings_and_match_ids():
    c = cfg()
    ps = pairings(c)
    assert len(ps) == 7 * 6 // 2 + 2, "every unordered pair plus self-play for the two models"
    assert {(p.first, p.second) for p in ps if p.first == p.second} == {("m1", "m1"), ("m2", "m2")}
    ids = [mid for _, mid in all_match_ids(c)]
    assert len(ids) == len(set(ids)) == len(ps) * 2
    assert ids[0] == "always-cooperate--always-defect--000"
    assert pairings(cfg(self_play=False)) == [p for p in ps if p.first != p.second]


def live_factory(fakes):
    def make(spec):
        fakes[spec.name] = FakeModelTransport(malformed_every=7)
        return fakes[spec.name]
    return make


def test_full_run_then_resume_then_replay_are_identical(tmp_path):
    c = cfg()
    out = tmp_path / "run"
    fakes = {}
    result = asyncio.run(run_tournament(c, out, live_factory=live_factory(fakes), log=lambda *a: None))
    assert result.completed and result.played == result.total == 23 * 2
    first_bytes = (out / "matches.jsonl").read_bytes()
    matches = load_matches(out / "matches.jsonl")
    assert sorted(matches) == [m for m in matches], "written sorted on completion"
    assert result.live_calls > 0 and result.spent_usd > 0
    assert any("retried" in r.flags[0] or "retried" in r.flags[1] for m in matches.values() for r in m.rounds)

    # Resume: drop half the matches; the recording still covers every call, so nothing goes live.
    kept = list(matches.values())[::2]
    (out / "matches.jsonl").write_text("".join(json.dumps(m.to_dict(), sort_keys=True) + "\n" for m in kept))
    fakes2 = {}
    result2 = asyncio.run(run_tournament(c, out, live_factory=live_factory(fakes2), log=lambda *a: None))
    assert result2.completed and result2.skipped == len(kept) and result2.played == result.total - len(kept)
    assert result2.live_calls == 0 and all(f.calls == 0 for f in fakes2.values())
    assert (out / "matches.jsonl").read_bytes() == first_bytes

    # Replay into a fresh directory from the recording alone: byte-identical, no transport at all.
    replay_dir = tmp_path / "replay"
    result3 = asyncio.run(run_tournament(c, replay_dir, replay=True, recording_path=out / "calls.jsonl", log=lambda *a: None))
    assert result3.completed and result3.live_calls == 0 and result3.spent_usd == 0
    assert (replay_dir / "matches.jsonl").read_bytes() == first_bytes
    run_info = json.loads((replay_dir / "run.json").read_text())
    assert run_info["replay"] is True and run_info["completed"] is True


def test_same_prompt_in_different_matches_gets_its_own_call(tmp_path):
    c = cfg(bots=[], models=[{"name": "m1", "model": "fake/one"}], matches_per_pairing=3)
    fakes = {}
    asyncio.run(run_tournament(c, tmp_path / "run", live_factory=live_factory(fakes), log=lambda *a: None))
    tags = [r.tag for r in fakes["m1"].seen if r.tag.endswith("round1/attempt0")]
    assert len(tags) == 3 * 2, "three self-play matches, two seats each, each round-1 prompt is a separate call"
    assert len(set(tags)) == len(tags)


def test_budget_stop_is_clean_and_resumable(tmp_path):
    c = cfg(spending_cap_usd=0.00002, bots=["always-cooperate"], models=[
        {"name": "m1", "model": "fake/one", "price": {"input_usd_per_million": 1.0, "output_usd_per_million": 5.0}}
    ], matches_per_pairing=4)
    out = tmp_path / "run"
    fakes = {}
    result = asyncio.run(run_tournament(c, out, live_factory=live_factory(fakes), log=lambda *a: None))
    assert not result.completed
    assert "spending cap" in result.stopped_reason
    assert len(load_matches(out / "matches.jsonl")) < result.total
    assert json.loads((out / "run.json").read_text())["completed"] is False

    bigger = cfg(spending_cap_usd=10.0, bots=["always-cooperate"], models=c.source["models"], matches_per_pairing=4)
    result2 = asyncio.run(run_tournament(bigger, out, live_factory=live_factory({}), log=lambda *a: None))
    assert result2.completed and result2.total == 8


def test_replay_fails_loudly_when_the_recording_is_incomplete(tmp_path):
    c = cfg(bots=["tit-for-tat"], models=[{"name": "m1", "model": "fake/one"}], matches_per_pairing=1)
    with pytest.raises(Exception, match="no recorded response"):
        asyncio.run(run_tournament(c, tmp_path / "r", replay=True, recording_path=tmp_path / "empty.jsonl", log=lambda *a: None))


def test_build_transports_groups_by_provider(tmp_path):
    c = cfg()
    made = []
    transports = build_transports(c, Recording(tmp_path / "c.jsonl"), False, Budget(1.0), live_factory=lambda s: made.append(s) or ExplodingTransport())
    assert set(transports) == {"m1", "m2"}
    assert [s.name for s in made] == ["m1", "m2"], "one raw transport per provider"
