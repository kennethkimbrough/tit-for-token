import asyncio

from conftest import FakeModelTransport

from tit_for_token.engine import MatchView, Rules
from tit_for_token.players.model import ModelPlayer, parse_move, round_prompt, system_prompt


def view(mine=(), theirs=(), n=None):
    return MatchView(Rules(), "m--n--000", 0, n or len(mine) + 1, tuple(mine), tuple(theirs))


def test_parse_move_accepts_json_anywhere_and_nothing_else():
    assert parse_move('{"move": "A"}') == "A"
    assert parse_move('Sure. {"move":"b"}') == "B"
    assert parse_move('```json\n{"move": "A"}\n```') == "A"
    assert parse_move('{"reason": "x", "move": "B"}') == "B"
    assert parse_move("A") is None
    assert parse_move('{"move": "C"}') is None
    assert parse_move('{"choice": "A"}') is None
    assert parse_move("") is None


def test_prompts_never_name_the_game_or_the_moves():
    text = (system_prompt(view()) + round_prompt(view(("A", "B"), ("B", "A")))).lower()
    for word in ("cooperat", "defect", "prisoner", "dilemma", "tit"):
        assert word not in text, word
    assert "(3, 3)" in text and "(0, 5)" in text and "(5, 0)" in text and "(1, 1)" in text
    assert "0.90" in text and "0.10" in text


def test_round_prompt_shows_history_and_totals():
    assert "No rounds have been played yet" in round_prompt(view())
    text = round_prompt(view(("A", "B"), ("B", "A")))
    assert "Round 1: you chose A, they chose B." in text
    assert "Round 2: you chose B, they chose A." in text
    assert "Totals so far: you 5, they 5." in text
    assert "Round 3." in text


def test_valid_answer_needs_one_call():
    t = FakeModelTransport()
    player = ModelPlayer("m", "fake/model", t)
    d = asyncio.run(player.move(view(("A",), ("B",))))
    assert d.move == "B" and d.flags == ()
    assert t.calls == 1
    assert t.seen[0].tag == "m--n--000/seat0/round2/attempt0"
    assert t.seen[0].model == "fake/model"


def test_malformed_answer_is_retried_once():
    t = FakeModelTransport(malformed_every=1)  # every first attempt is prose
    d = asyncio.run(ModelPlayer("m", "fake/model", t).move(view()))
    assert d.move == "A" and d.flags == ("retried",)
    assert t.calls == 2
    roles = [r for r, _ in t.seen[1].messages]
    assert roles == ["system", "user", "assistant", "user"], "the retry carries the bad answer and a reminder"
    assert t.seen[1].tag.endswith("attempt1")


def test_second_failure_is_a_forfeit():
    t = FakeModelTransport(malformed_every=1, stubborn=True)
    d = asyncio.run(ModelPlayer("m", "fake/model", t).move(view()))
    assert d.move == "B" and d.flags == ("forfeit",)
    assert t.calls == 2


def test_cut_off_answers_are_flagged_as_truncated():
    t = FakeModelTransport(truncate=True)
    d = asyncio.run(ModelPlayer("m", "fake/model", t, reasoning="low", max_tokens=20).move(view()))
    assert d.move == "B" and d.flags == ("forfeit", "truncated")
    assert t.calls == 2
    body = t.seen[0].to_dict()
    assert body["reasoning"] == {"effort": "low", "exclude": True} and body["max_tokens"] == 20


def test_reasoning_setting_is_part_of_the_recording_key():
    t = FakeModelTransport()
    asyncio.run(ModelPlayer("m", "fake/model", t).move(view()))
    asyncio.run(ModelPlayer("m", "fake/model", t, reasoning="none").move(view()))
    assert t.seen[0].key() != t.seen[1].key()
    assert "reasoning" not in t.seen[0].to_dict(), "nothing is sent when no effort is configured"


def test_named_framing_changes_only_the_description_of_the_game():
    neutral = system_prompt(view())
    named = system_prompt(view(), "named")
    assert "prisoner's dilemma" in named and "A (cooperate)" in named and "B (defect)" in named
    # Payoffs, continuation, goal and answer format are word for word the same.
    for line in neutral.splitlines()[3:]:
        assert line in named, line
    assert "dilemma" not in neutral


def test_framing_is_sent_to_the_model_and_unknown_framings_are_refused():
    import pytest

    t = FakeModelTransport()
    asyncio.run(ModelPlayer("m", "fake/model", t, framing="named").move(view()))
    assert "prisoner's dilemma" in t.seen[0].messages[0][1]
    with pytest.raises(ValueError):
        ModelPlayer("m", "fake/model", t, framing="poker")
