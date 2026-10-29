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
    num = den = 0
    for s in group:
        n, d = stat(s)
        num += n
        den += d
    return num / den if den else float("nan")


def estimate(stat: Stat, group: list, reps: int = 1000, seed: int = 0, level: float = 0.95) -> Estimate:
    """Pooled value over the group, with a bootstrap percentile interval from resampling matches."""
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


def summarize_players(matches: list[MatchRecord], reps: int = 1000) -> list[PlayerSummary]:
    by_player: dict[str, list[Side]] = defaultdict(list)
    for s in sides(matches):
        by_player[s.player].append(s)
    out = []
    for name, group in by_player.items():
        vs_ac = [s for s in group if s.opponent == "always-cooperate"]
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
            )
        )
    out.sort(key=lambda p: -p.payoff.value if p.payoff.value == p.payoff.value else 0)
    return out


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

    lines.append("| Player | Matches | Payoff/round | Cooperation | Retaliation | Forgiveness | vs Always Cooperate | Retried | Forfeits |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for p in players:
        lines.append(
            f"| {p.player} | {p.matches} | {p.payoff.fmt(pct=False)} | {p.cooperation.fmt()} | "
            f"{p.retaliation.fmt()} | {p.forgiveness.fmt()} | {p.vs_always_cooperate.fmt(pct=False)} | "
            f"{p.retried.fmt()} | {p.forfeits.fmt()} |"
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
