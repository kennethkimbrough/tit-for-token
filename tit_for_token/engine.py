"""The iterated prisoner's dilemma: rules, payoffs, seeded match length, and the match loop.

Everything here is pure: no I/O, no network. Players are only called through the
``Player`` protocol, so the same loop runs bots, models, and fakes in tests.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
from dataclasses import dataclass, field
from typing import Protocol

Move = str  # "A" (cooperate) or "B" (defect); players never see those words
MOVES = ("A", "B")
COOPERATE, DEFECT = "A", "B"

#: Payoff for (my move, other's move) -> (my payoff, other's payoff).
PAYOFFS: dict[tuple[Move, Move], tuple[int, int]] = {
    ("A", "A"): (3, 3),
    ("A", "B"): (0, 5),
    ("B", "A"): (5, 0),
    ("B", "B"): (1, 1),
}

#: Probability that the match ends after any given round.
DEFAULT_END_PROBABILITY = 0.1


@dataclass(frozen=True)
class Rules:
    end_probability: float = DEFAULT_END_PROBABILITY
    max_rounds: int = 200  # safety cap so a pathological seed cannot run forever

    def __post_init__(self) -> None:
        if not 0 < self.end_probability <= 1:
            raise ValueError("end_probability must be in (0, 1]")
        if self.max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")


@dataclass(frozen=True)
class MatchView:
    """What a player is allowed to see when choosing a move."""

    rules: Rules
    match_id: str
    seat: int  # 0 for the first player, 1 for the second
    round_number: int  # 1-based
    my_moves: tuple[Move, ...]
    their_moves: tuple[Move, ...]

    @property
    def my_score(self) -> int:
        return sum(PAYOFFS[m, t][0] for m, t in zip(self.my_moves, self.their_moves))

    @property
    def their_score(self) -> int:
        return sum(PAYOFFS[m, t][1] for m, t in zip(self.my_moves, self.their_moves))


@dataclass(frozen=True)
class Decision:
    """A player's answer for one round.

    ``flags`` records anything worth analysing later: a model that needed a
    retry ("retried") or that forfeited the round ("forfeit").
    """

    move: Move
    flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.move not in MOVES:
            raise ValueError(f"move must be one of {MOVES}, got {self.move!r}")


class Player(Protocol):
    name: str

    async def move(self, view: MatchView) -> Decision: ...


@dataclass(frozen=True)
class Round:
    moves: tuple[Move, Move]
    flags: tuple[tuple[str, ...], tuple[str, ...]] = ((), ())

    @property
    def payoffs(self) -> tuple[int, int]:
        return PAYOFFS[self.moves]


@dataclass
class MatchRecord:
    match_id: str
    players: tuple[str, str]
    seed: int
    length: int
    rounds: list[Round] = field(default_factory=list)

    @property
    def scores(self) -> tuple[int, int]:
        a = sum(r.payoffs[0] for r in self.rounds)
        b = sum(r.payoffs[1] for r in self.rounds)
        return a, b

    def moves_of(self, index: int) -> tuple[Move, ...]:
        return tuple(r.moves[index] for r in self.rounds)

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "players": list(self.players),
            "seed": self.seed,
            "length": self.length,
            "rounds": [
                {"moves": list(r.moves), "flags": [list(r.flags[0]), list(r.flags[1])]}
                for r in self.rounds
            ],
            "scores": list(self.scores),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MatchRecord":
        rec = cls(
            match_id=d["match_id"],
            players=(d["players"][0], d["players"][1]),
            seed=d["seed"],
            length=d["length"],
        )
        for r in d["rounds"]:
            rec.rounds.append(
                Round(
                    moves=(r["moves"][0], r["moves"][1]),
                    flags=(tuple(r["flags"][0]), tuple(r["flags"][1])),
                )
            )
        return rec


def match_seed(tournament_seed: int, match_id: str) -> int:
    """A stable 63-bit seed for a match, so results never depend on scheduling order."""
    digest = hashlib.sha256(f"{tournament_seed}:{match_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") >> 1


def draw_length(seed: int, rules: Rules) -> int:
    """Number of rounds, drawn up front: after each round the match ends with ``end_probability``.

    Drawing before play keeps the match length independent of anything the
    players do and lets a match replay exactly from its seed.
    """
    rng = random.Random(seed)
    length = 1
    while length < rules.max_rounds and rng.random() >= rules.end_probability:
        length += 1
    return length


async def play_match(
    match_id: str,
    first: Player,
    second: Player,
    seed: int,
    rules: Rules = Rules(),
) -> MatchRecord:
    """Play one match. Both players choose simultaneously: neither sees the other's current move."""
    record = MatchRecord(
        match_id=match_id,
        players=(first.name, second.name),
        seed=seed,
        length=draw_length(seed, rules),
    )
    first_moves: list[Move] = []
    second_moves: list[Move] = []
    for round_number in range(1, record.length + 1):
        view_first = MatchView(rules, match_id, 0, round_number, tuple(first_moves), tuple(second_moves))
        view_second = MatchView(rules, match_id, 1, round_number, tuple(second_moves), tuple(first_moves))
        # Moves are simultaneous, so both players are asked at once; neither view contains this round.
        d1, d2 = await asyncio.gather(first.move(view_first), second.move(view_second))
        first_moves.append(d1.move)
        second_moves.append(d2.move)
        record.rounds.append(Round(moves=(d1.move, d2.move), flags=(d1.flags, d2.flags)))
    return record
