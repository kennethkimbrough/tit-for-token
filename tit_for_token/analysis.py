"""Metrics over recorded matches, with bootstrap confidence intervals.

Everything is a plain function of ``MatchRecord`` objects. Confidence
intervals resample matches, not rounds, because rounds within a match are not
independent of each other.
"""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .engine import COOPERATE, DEFECT, MatchRecord, Move
from .players.bots import BOT_RULES


@dataclass(frozen=True)
class Side:
    """One player's view of one match: its own moves, the opponent's, its flags, and the opponent's name."""

    player: str
    opponent: str
    my_moves: tuple[Move, ...]
    their_moves: tuple[Move, ...]
    my_flags: tuple[tuple[str, ...], ...]
    my_score: int
    their_score: int


def sides(matches: Iterable[MatchRecord]) -> list[Side]:
    out = []
    for m in matches:
        s0, s1 = m.scores
        m0, m1 = m.moves_of(0), m.moves_of(1)
        f0 = tuple(r.flags[0] for r in m.rounds)
        f1 = tuple(r.flags[1] for r in m.rounds)
        out.append(Side(m.players[0], m.players[1], m0, m1, f0, s0, s1))
        out.append(Side(m.players[1], m.players[0], m1, m0, f1, s1, s0))
    return out


# ---- per-side statistics (each returns (numerator, denominator) so they pool correctly) ----

def cooperation(side: Side) -> tuple[int, int]:
    return sum(m == COOPERATE for m in side.my_moves), len(side.my_moves)


def payoff(side: Side) -> tuple[int, int]:
    return side.my_score, len(side.my_moves)


def retaliation(side: Side) -> tuple[int, int]:
    """P(I play B this round | they played B last round)."""
    num = den = 0
    for i in range(1, len(side.my_moves)):
        if side.their_moves[i - 1] == DEFECT:
            den += 1
            num += side.my_moves[i] == DEFECT
    return num, den


def forgiveness(side: Side) -> tuple[int, int]:
    """P(I play A this round | I retaliated last round), where retaliating = B right after their B."""
    num = den = 0
    for i in range(2, len(side.my_moves)):
        retaliated = side.their_moves[i - 2] == DEFECT and side.my_moves[i - 1] == DEFECT
        if retaliated:
            den += 1
            num += side.my_moves[i] == COOPERATE
    return num, den


def retried(side: Side) -> tuple[int, int]:
    return sum("retried" in f for f in side.my_flags), len(side.my_moves)


def forfeits(side: Side) -> tuple[int, int]:
    return sum("forfeit" in f for f in side.my_flags), len(side.my_moves)


def truncated(side: Side) -> tuple[int, int]:
    """Rounds where an answer was cut off at max_tokens: a configuration problem, not a choice."""
    return sum("truncated" in f for f in side.my_flags), len(side.my_moves)


def fingerprint(side: Side, rule_name: str) -> tuple[int, int]:
    """Share of rounds where the player's move equals what the named bot rule would have played, given the same history."""
    rule = BOT_RULES[rule_name]
    num = 0
    for i, move in enumerate(side.my_moves):
        if rule(side.my_moves[:i], side.their_moves[:i]) == move:
            num += 1
    return num, len(side.my_moves)


Stat = Callable[[Any], tuple[int, int]]  # any item -> (numerator, denominator)


@dataclass(frozen=True)
class Estimate:
    value: float
    low: float
    high: float
    n_matches: int

    def fmt(self, pct: bool = True) -> str:
        if self.n_matches == 0 or self.value != self.value:  # NaN
            return "–"
        if pct:
            return f"{100 * self.value:.0f}% [{100 * self.low:.0f}–{100 * self.high:.0f}]"
        return f"{self.value:.2f} [{self.low:.2f}–{self.high:.2f}]"


def pooled(stat: Stat, group: list) -> float:
    """``group`` holds units; a unit is one item or a list of items (the sides of one match)."""
    num = den = 0
    for unit in group:
        for item in unit if isinstance(unit, list) else [unit]:
            n, d = stat(item)
            num += n
            den += d
    return num / den if den else float("nan")


def estimate(stat: Stat, group: list, reps: int = 1000, seed: int = 0, level: float = 0.95) -> Estimate:
    """Pooled value over the group, with a bootstrap percentile interval from resampling units.

    A unit is a match: in a self-play match the same player holds both sides,
    and they are resampled together so the interval is not falsely narrow.
    """
    value = pooled(stat, group)
    if not group or value != value:
        return Estimate(float("nan"), float("nan"), float("nan"), len(group))
    rng = random.Random(seed)
    samples = []
    for _ in range(reps):
        resample = [group[rng.randrange(len(group))] for _ in group]
        v = pooled(stat, resample)
        if v == v:
            samples.append(v)
    samples.sort()
    if not samples:
        return Estimate(value, value, value, len(group))
    lo = samples[int((1 - level) / 2 * (len(samples) - 1))]
    hi = samples[int((1 + level) / 2 * (len(samples) - 1))]
    return Estimate(value, lo, hi, len(group))


@dataclass
class PlayerSummary:
    player: str
    matches: int
    cooperation: Estimate
    payoff: Estimate
    retaliation: Estimate
    forgiveness: Estimate
    vs_always_cooperate: Estimate  # payoff per round against Always Cooperate; 3 = cooperates, 5 = exploits fully
    fingerprints: dict[str, Estimate]
    retried: Estimate
    forfeits: Estimate
    truncated: Estimate


def summarize_players(matches: list[MatchRecord], reps: int = 1000) -> list[PlayerSummary]:
    # One bootstrap unit per (player, match): a list of that player's sides in the match,
    # which has two entries when the player played itself.
    units: dict[str, dict[str, list[Side]]] = defaultdict(lambda: defaultdict(list))
    for m in matches:
        for s in sides([m]):
            units[s.player][m.match_id].append(s)
    out = []
    for name, by_match in units.items():
        group = list(by_match.values())
        vs_ac = [[s for s in unit if s.opponent == "always-cooperate"] for unit in group]
        vs_ac = [u for u in vs_ac if u]
        out.append(
            PlayerSummary(
                player=name,
                matches=len(group),
                cooperation=estimate(cooperation, group, reps),
                payoff=estimate(payoff, group, reps),
                retaliation=estimate(retaliation, group, reps),
                forgiveness=estimate(forgiveness, group, reps),
                vs_always_cooperate=estimate(payoff, vs_ac, reps),
                fingerprints={r: estimate(lambda s, r=r: fingerprint(s, r), group, reps) for r in BOT_RULES},
                retried=estimate(retried, group, reps),
                forfeits=estimate(forfeits, group, reps),
                truncated=estimate(truncated, group, reps),
            )
        )
    out.sort(key=lambda p: -p.payoff.value if p.payoff.value == p.payoff.value else 0)
    return out


#: Above this forfeit rate a player's other numbers are not worth reading: forfeits are recorded as B.
FORFEIT_WARNING_RATE = 0.02


def validity_warnings(players: list[PlayerSummary]) -> list[str]:
    warnings = []
    for p in players:
        if p.forfeits.value == p.forfeits.value and p.forfeits.value > FORFEIT_WARNING_RATE:
            cause = "cut off at max_tokens" if p.truncated.value > 0 else "not answering in the required format"
            warnings.append(
                f"{p.player} forfeited {100 * p.forfeits.value:.1f}% of rounds ({cause}). Forfeits are recorded as B, "
                "so its cooperation and payoff numbers are not valid; fix the configuration and rerun."
            )
    return warnings


def mutual_cooperation(matches: list[MatchRecord], reps: int = 1000) -> dict[tuple[str, str], Estimate]:
    """Share of rounds where both players cooperated, per unordered pairing."""
    by_pair: dict[tuple[str, str], list[MatchRecord]] = defaultdict(list)
    for m in matches:
        by_pair[tuple(sorted(m.players))].append(m)

    def both(m: MatchRecord) -> tuple[int, int]:
        return sum(r.moves == (COOPERATE, COOPERATE) for r in m.rounds), len(m.rounds)

    return {pair: estimate(both, ms, reps) for pair, ms in by_pair.items()}


def payoff_matrix(matches: list[MatchRecord]) -> dict[str, dict[str, float]]:
    """Mean payoff per round for the row player against the column player."""
    totals: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for s in sides(matches):
        cell = totals[s.player][s.opponent]
        cell[0] += s.my_score
        cell[1] += len(s.my_moves)
    return {p: {o: (c[0] / c[1] if c[1] else float("nan")) for o, c in row.items()} for p, row in totals.items()}


def markdown_report(matches: list[MatchRecord], reps: int = 1000) -> str:
    players = summarize_players(matches, reps)
    names = [p.player for p in players]
    lines = []
    n_rounds = sum(len(m.rounds) for m in matches)
    lines.append(f"{len(matches)} matches, {n_rounds} rounds, {len(names)} players. "
                 "Brackets are 95% bootstrap intervals over matches.\n")
    for w in validity_warnings(players):
        lines.append(f"> **Warning:** {w}\n")

    lines.append("| Player | Matches | Payoff/round | Cooperation | Retaliation | Forgiveness | vs Always Cooperate | Retried | Forfeits | Cut off |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for p in players:
        lines.append(
            f"| {p.player} | {p.matches} | {p.payoff.fmt(pct=False)} | {p.cooperation.fmt()} | "
            f"{p.retaliation.fmt()} | {p.forgiveness.fmt()} | {p.vs_always_cooperate.fmt(pct=False)} | "
            f"{p.retried.fmt()} | {p.forfeits.fmt()} | {p.truncated.fmt()} |"
        )

    lines.append("\nFingerprint: share of rounds where the player's move matches each classic rule, given the same history.\n")
    rules = list(BOT_RULES)
    lines.append("| Player | " + " | ".join(rules) + " |")
    lines.append("|---|" + "---|" * len(rules))
    for p in players:
        lines.append(f"| {p.player} | " + " | ".join(p.fingerprints[r].fmt() for r in rules) + " |")

    lines.append("\nMutual cooperation: share of rounds where both players chose A, per pairing.\n")
    mutual = mutual_cooperation(matches, reps)
    lines.append("| | " + " | ".join(names) + " |")
    lines.append("|---|" + "---|" * len(names))
    for row in names:
        cells = []
        for col in names:
            est = mutual.get(tuple(sorted((row, col))))
            cells.append("–" if est is None else est.fmt())
        lines.append(f"| {row} | " + " | ".join(cells) + " |")

    lines.append("\nMean payoff per round, row player against column player.\n")
    matrix = payoff_matrix(matches)
    lines.append("| | " + " | ".join(names) + " |")
    lines.append("|---|" + "---|" * len(names))
    for row in names:
        cells = []
        for col in names:
            v = matrix.get(row, {}).get(col, float("nan"))
            cells.append("–" if v != v else f"{v:.2f}")
        lines.append(f"| {row} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


# ---- comparing two runs of the same matches (the framing experiment) ----

BOT_NAMES = frozenset({"always-cooperate", "always-defect", "tit-for-tat", "grim-trigger", "random"})


@dataclass(frozen=True)
class Change:
    """A statistic in two runs over the same matches, and the paired difference (second minus first)."""

    first: Estimate
    second: Estimate
    diff: Estimate


def paired_change(stat: Stat, first: list, second: list, reps: int = 1000, seed: int = 0, level: float = 0.95) -> Change:
    """``first[i]`` and ``second[i]`` are the same match in two runs; resample match indices for both together.

    Because the two runs share match ids, seeds and lengths, the difference is
    computed within each resample, which gives a tighter and more honest
    interval than comparing two independent intervals.
    """
    if len(first) != len(second):
        raise ValueError("paired groups must have the same length")
    a, b = pooled(stat, first), pooled(stat, second)
    n = len(first)
    if not n or a != a or b != b:
        nan = float("nan")
        return Change(estimate(stat, first, reps, seed), estimate(stat, second, reps, seed), Estimate(nan, nan, nan, n))
    rng = random.Random(seed)
    diffs = []
    for _ in range(reps):
        idx = [rng.randrange(n) for _ in range(n)]
        da = pooled(stat, [first[i] for i in idx])
        db = pooled(stat, [second[i] for i in idx])
        if da == da and db == db:
            diffs.append(db - da)
    diffs.sort()
    lo = diffs[int((1 - level) / 2 * (len(diffs) - 1))] if diffs else b - a
    hi = diffs[int((1 + level) / 2 * (len(diffs) - 1))] if diffs else b - a
    return Change(estimate(stat, first, reps, seed), estimate(stat, second, reps, seed), Estimate(b - a, lo, hi, n))


@dataclass
class FramingComparison:
    player: str
    matches: int
    cooperation: Change
    cooperation_vs_models: Change
    retaliation: Change
    forgiveness: Change
    vs_always_cooperate: Change
    payoff: Change


def compare_runs(first: list[MatchRecord], second: list[MatchRecord], reps: int = 1000) -> list[FramingComparison]:
    """Per model, each statistic in both runs over the matches the runs share, with paired intervals.

    Only players that are not classic bots are compared (a bot plays the same
    whatever the framing), and only match ids present in both runs count.
    """
    by_id_a = {m.match_id: m for m in first}
    by_id_b = {m.match_id: m for m in second}
    shared = sorted(set(by_id_a) & set(by_id_b))
    for mid in shared:
        if len(by_id_a[mid].rounds) != len(by_id_b[mid].rounds):
            raise ValueError(f"match {mid} has a different length in the two runs; they are not the same matches")

    def units(matches: dict[str, MatchRecord], player: str, keep=lambda s: True) -> list[list[Side]]:
        out = []
        for mid in shared:
            unit = [s for s in sides([matches[mid]]) if s.player == player and keep(s)]
            if unit:
                out.append(unit)
        return out

    players = sorted({p for mid in shared for p in by_id_a[mid].players} - BOT_NAMES)
    result = []
    for p in players:
        ua, ub = units(by_id_a, p), units(by_id_b, p)
        not_bot = lambda s: s.opponent not in BOT_NAMES  # noqa: E731
        ac = lambda s: s.opponent == "always-cooperate"  # noqa: E731
        result.append(
            FramingComparison(
                player=p,
                matches=len(ua),
                cooperation=paired_change(cooperation, ua, ub, reps),
                cooperation_vs_models=paired_change(cooperation, units(by_id_a, p, not_bot), units(by_id_b, p, not_bot), reps),
                retaliation=paired_change(retaliation, ua, ub, reps),
                forgiveness=paired_change(forgiveness, ua, ub, reps),
                vs_always_cooperate=paired_change(payoff, units(by_id_a, p, ac), units(by_id_b, p, ac), reps),
                payoff=paired_change(payoff, ua, ub, reps),
            )
        )
    return result


def _fmt_change(c: Change, pct: bool) -> str:
    if c.diff.n_matches == 0 or c.diff.value != c.diff.value:
        return "–"
    if pct:
        return (f"{100 * c.first.value:.0f}% → {100 * c.second.value:.0f}% "
                f"({100 * c.diff.value:+.0f} pts [{100 * c.diff.low:+.0f} to {100 * c.diff.high:+.0f}])")
    return f"{c.first.value:.2f} → {c.second.value:.2f} ({c.diff.value:+.2f} [{c.diff.low:+.2f} to {c.diff.high:+.2f}])"


def markdown_comparison(first: list[MatchRecord], second: list[MatchRecord], first_name: str, second_name: str,
                        reps: int = 1000) -> str:
    rows = compare_runs(first, second, reps)
    shared = len({m.match_id for m in first} & {m.match_id for m in second})
    lines = [
        f"{first_name} → {second_name}, over the {shared} matches the two runs share (same ids, seeds and lengths). "
        "Brackets are 95% paired bootstrap intervals for the change, resampling matches. "
        "A change whose interval excludes zero is a finding; one that includes zero is not.\n",
        "| Model | Matches | Cooperation | Cooperation vs models | Retaliation | Forgiveness | vs Always Cooperate | Payoff/round |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.player} | {r.matches} | {_fmt_change(r.cooperation, True)} | {_fmt_change(r.cooperation_vs_models, True)} | "
            f"{_fmt_change(r.retaliation, True)} | {_fmt_change(r.forgiveness, True)} | "
            f"{_fmt_change(r.vs_always_cooperate, False)} | {_fmt_change(r.payoff, False)} |"
        )
    return "\n".join(lines) + "\n"
