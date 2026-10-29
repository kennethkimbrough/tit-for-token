import asyncio
from statistics import mean

import pytest

from tit_for_token.engine import (
    PAYOFFS,
    Decision,
    MatchRecord,
    MatchView,
    Rules,
    draw_length,
    match_seed,
    play_match,
)
from tit_for_token.players import AlwaysCooperate, AlwaysDefect, GrimTrigger, RandomBot, TitForTat


def test_payoff_table_is_a_prisoners_dilemma():
    t, r, p, s = PAYOFFS["B", "A"][0], PAYOFFS["A", "A"][0], PAYOFFS["B", "B"][0], PAYOFFS["A", "B"][0]
    assert t > r > p > s, "temptation > reward > punishment > sucker"
    assert 2 * r > t + s, "mutual cooperation beats alternating exploitation"
    for (a, b), (pa, pb) in PAYOFFS.items():
        assert PAYOFFS[b, a] == (pb, pa), "the table is symmetric"


def test_decision_rejects_unknown_moves():
    with pytest.raises(ValueError):
        Decision("C")


def test_rules_validation():
    with pytest.raises(ValueError):
        Rules(end_probability=0)
    with pytest.raises(ValueError):
        Rules(max_rounds=0)


def test_match_seed_is_stable_and_distinct():
    assert match_seed(1, "a--b--000") == match_seed(1, "a--b--000")
    assert match_seed(1, "a--b--000") != match_seed(1, "a--b--001")
    assert match_seed(1, "a--b--000") != match_seed(2, "a--b--000")
    assert 0 <= match_seed(1, "x") < 2**63


def test_draw_length_is_deterministic_and_geometric():
    rules = Rules(end_probability=0.1)
    assert draw_length(42, rules) == draw_length(42, rules)
    lengths = [draw_length(seed, rules) for seed in range(4000)]
    assert min(lengths) >= 1
    assert 9 < mean(lengths) < 11, "expected length is 1/end_probability = 10"
    assert draw_length(7, Rules(end_probability=1.0)) == 1
    assert all(draw_length(seed, Rules(end_probability=0.001, max_rounds=5)) <= 5 for seed in range(50))


def test_view_scores():
    view = MatchView(Rules(), "m", 0, 3, ("A", "B"), ("A", "A"))
    assert view.my_score == 3 + 5
    assert view.their_score == 3 + 0


def test_tit_for_tat_against_always_defect():
    rec = asyncio.run(play_match("m", TitForTat(), AlwaysDefect(), seed=3, rules=Rules(end_probability=0.5)))
    assert rec.length == len(rec.rounds) >= 1
    assert rec.moves_of(0)[0] == "A", "tit-for-tat opens with A"
    assert all(m == "B" for m in rec.moves_of(0)[1:]), "then copies the defection"
    assert all(m == "B" for m in rec.moves_of(1))
    first, second = rec.scores
    assert first == 0 + (rec.length - 1) * 1
    assert second == 5 + (rec.length - 1) * 1


def test_grim_trigger_never_forgives():
    class DefectOnceThenCooperate:
        name = "once"

        async def move(self, view):
            return Decision("B" if view.round_number == 2 else "A")

    rec = asyncio.run(play_match("m", GrimTrigger(), DefectOnceThenCooperate(), seed=11, rules=Rules(end_probability=0.05, max_rounds=12)))
    grim = rec.moves_of(0)
    assert grim[:2] == ("A", "A")
    assert all(m == "B" for m in grim[2:])


def test_always_cooperate_pair_and_random_is_seeded():
    rec = asyncio.run(play_match("m", AlwaysCooperate(), AlwaysCooperate(), seed=5))
    assert rec.scores == (3 * rec.length, 3 * rec.length)

    a, b = RandomBot(), RandomBot()
    a.reseed(99)
    b.reseed(99)
    ra = asyncio.run(play_match("m", a, AlwaysCooperate(), seed=5))
    rb = asyncio.run(play_match("m", b, AlwaysCooperate(), seed=5))
    assert ra.moves_of(0) == rb.moves_of(0)
    assert set(ra.moves_of(0)) <= {"A", "B"}


def test_players_see_only_the_past():
    seen = []

    class Spy:
        name = "spy"

        async def move(self, view):
            seen.append((view.seat, view.round_number, view.my_moves, view.their_moves))
            return Decision("A")

    asyncio.run(play_match("m", Spy(), AlwaysDefect(), seed=1, rules=Rules(end_probability=0.5)))
    for seat, n, mine, theirs in seen:
        assert seat == 0
        assert len(mine) == len(theirs) == n - 1


def test_record_round_trips_through_dict():
    rec = asyncio.run(play_match("x--y--000", TitForTat(), AlwaysDefect(), seed=8))
    rec.rounds[0] = type(rec.rounds[0])(moves=rec.rounds[0].moves, flags=(("retried",), ()))
    again = MatchRecord.from_dict(rec.to_dict())
    assert again.to_dict() == rec.to_dict()
    assert again.rounds[0].flags == (("retried",), ())
