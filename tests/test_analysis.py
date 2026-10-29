import asyncio

from tit_for_token.analysis import (
    FORFEIT_WARNING_RATE,
    Side,
    cooperation,
    estimate,
    fingerprint,
    forgiveness,
    markdown_report,
    mutual_cooperation,
    payoff_matrix,
    retaliation,
    summarize_players,
    truncated,
    validity_warnings,
)
from tit_for_token.engine import Rules, play_match
from tit_for_token.players import AlwaysCooperate, AlwaysDefect, GrimTrigger, TitForTat


def side(mine, theirs, player="p", opponent="o"):
    return Side(player, opponent, tuple(mine), tuple(theirs), tuple(() for _ in mine), 0, 0)


def test_per_side_statistics():
    s = side("AABBA", "ABBAA")
    assert cooperation(s) == (3, 5)
    # retaliation: rounds after they played B (rounds 2, 3 -> my rounds 3, 4): I played B, B
    assert retaliation(s) == (2, 2)
    # forgiveness: I retaliated at round 3 (their B at 2, my B at 3) -> my round 4 was B (no); retaliated at 4 -> round 5 A (yes)
    assert forgiveness(s) == (1, 2)
    assert fingerprint(side("AB", "BA"), "tit-for-tat") == (2, 2)
    assert fingerprint(side("AB", "BA"), "always-cooperate") == (1, 2)
    assert fingerprint(side("AAB", "ABA"), "grim-trigger") == (3, 3)
    assert fingerprint(side("AAA", "ABA"), "grim-trigger") == (2, 3)


def test_estimate_interval_contains_the_value_and_is_tight_for_constant_data():
    group = [side("AAAA", "BBBB") for _ in range(20)]
    e = estimate(cooperation, group, reps=200)
    assert e.value == e.low == e.high == 1.0
    mixed = [side("AAAA", "BBBB")] * 10 + [side("BBBB", "BBBB")] * 10
    e = estimate(cooperation, mixed, reps=500)
    assert e.low <= 0.5 <= e.high and e.low < e.high
    empty = estimate(cooperation, [], reps=10)
    assert empty.fmt() == "–"


def tournament():
    bots = {b.name: b for b in (AlwaysCooperate(), AlwaysDefect(), TitForTat(), GrimTrigger())}
    matches = []
    names = list(bots)
    for i, a in enumerate(names):
        for b in names[i:]:
            for k in range(3):
                matches.append(asyncio.run(play_match(f"{a}--{b}--{k:03d}", bots[a], bots[b], seed=100 * i + k, rules=Rules(0.2))))
    return matches


def test_summaries_match_the_known_strategies():
    summaries = {p.player: p for p in summarize_players(tournament(), reps=100)}
    assert summaries["always-cooperate"].cooperation.value == 1.0
    assert summaries["always-defect"].cooperation.value == 0.0
    assert summaries["always-defect"].retaliation.value == 1.0
    assert summaries["tit-for-tat"].fingerprints["tit-for-tat"].value == 1.0
    assert summaries["grim-trigger"].fingerprints["grim-trigger"].value == 1.0
    assert summaries["always-defect"].vs_always_cooperate.value == 5.0
    assert summaries["tit-for-tat"].vs_always_cooperate.value == 3.0
    assert summaries["always-cooperate"].forfeits.value == 0.0


def test_pair_tables():
    matches = tournament()
    mutual = mutual_cooperation(matches, reps=50)
    assert mutual[("always-cooperate", "tit-for-tat")].value == 1.0
    assert mutual[("always-defect", "always-defect")].value == 0.0
    matrix = payoff_matrix(matches)
    assert matrix["always-defect"]["always-cooperate"] == 5.0
    assert matrix["always-cooperate"]["always-defect"] == 0.0


def test_markdown_report_has_every_table():
    text = markdown_report(tournament(), reps=50)
    assert "| Player | Matches | Payoff/round |" in text
    assert "Fingerprint" in text and "Mutual cooperation" in text and "Mean payoff per round" in text
    assert "always-defect" in text and "95% bootstrap" in text


def test_self_play_counts_one_unit_per_match():
    bot = TitForTat()
    matches = [asyncio.run(play_match(f"tit-for-tat--tit-for-tat--{k:03d}", bot, bot, seed=k, rules=Rules(0.3))) for k in range(5)]
    summary = summarize_players(matches, reps=50)[0]
    assert summary.matches == 5, "both sides of a self-play match are one bootstrap unit"
    assert summary.cooperation.value == 1.0


def test_forfeit_warning_names_the_cause():
    flags = tuple(("forfeit", "truncated") for _ in range(4))
    cut = Side("m", "o", ("B", "B", "B", "B"), ("A", "A", "A", "A"), flags, 20, 0)
    assert truncated(cut) == (4, 4)
    matches = tournament()
    players = summarize_players(matches, reps=20)
    assert validity_warnings(players) == []
    fake = type(players[0])(**{**players[0].__dict__, "player": "m", "forfeits": estimate(lambda s: (1, 10), [cut]),
                                "truncated": estimate(lambda s: (1, 10), [cut])})
    (warning,) = validity_warnings([fake])
    assert "cut off at max_tokens" in warning and "not valid" in warning
    assert 0.1 > FORFEIT_WARNING_RATE
