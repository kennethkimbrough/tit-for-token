"""Classic strategies. They cost nothing, give tests deterministic expectations, and anchor the results.

Each bot's rule is also exposed as a pure function of the history
(``BOT_RULES``) so the analysis can ask "what would Tit-for-Tat have played
here?" for every round a model played.
"""

from __future__ import annotations

import random
from typing import Callable

from ..engine import COOPERATE, DEFECT, Decision, MatchView, Move

Rule = Callable[[tuple[Move, ...], tuple[Move, ...]], Move]  # (my_moves, their_moves) -> move


def always_cooperate(my: tuple[Move, ...], their: tuple[Move, ...]) -> Move:
    return COOPERATE


def always_defect(my: tuple[Move, ...], their: tuple[Move, ...]) -> Move:
    return DEFECT


def tit_for_tat(my: tuple[Move, ...], their: tuple[Move, ...]) -> Move:
    return their[-1] if their else COOPERATE


def grim_trigger(my: tuple[Move, ...], their: tuple[Move, ...]) -> Move:
    return DEFECT if DEFECT in their else COOPERATE


#: Deterministic rules, usable as fingerprints for any player's behaviour.
BOT_RULES: dict[str, Rule] = {
    "always-cooperate": always_cooperate,
    "always-defect": always_defect,
    "tit-for-tat": tit_for_tat,
    "grim-trigger": grim_trigger,
}


class _RuleBot:
    rule: Rule

    def __init__(self, name: str) -> None:
        self.name = name

    async def move(self, view: MatchView) -> Decision:
        return Decision(type(self).rule(view.my_moves, view.their_moves))


class AlwaysCooperate(_RuleBot):
    rule = staticmethod(always_cooperate)

    def __init__(self) -> None:
        super().__init__("always-cooperate")


class AlwaysDefect(_RuleBot):
    rule = staticmethod(always_defect)

    def __init__(self) -> None:
        super().__init__("always-defect")


class TitForTat(_RuleBot):
    rule = staticmethod(tit_for_tat)

    def __init__(self) -> None:
        super().__init__("tit-for-tat")


class GrimTrigger(_RuleBot):
    rule = staticmethod(grim_trigger)

    def __init__(self) -> None:
        super().__init__("grim-trigger")


class RandomBot:
    """A or B with probability 0.5 each, from a seed so a match replays exactly.

    The bot's randomness is derived from the match seed, so the same seed gives
    the same sequence of moves regardless of what the opponent does.
    """

    name = "random"

    def __init__(self, seed: int = 0) -> None:
        self._rng = random.Random(seed)

    def reseed(self, seed: int) -> None:
        self._rng = random.Random(seed ^ 0x5EED)

    async def move(self, view: MatchView) -> Decision:
        return Decision(COOPERATE if self._rng.random() < 0.5 else DEFECT)


def bot_by_name(name: str):
    bots = {
        "always-cooperate": AlwaysCooperate,
        "always-defect": AlwaysDefect,
        "tit-for-tat": TitForTat,
        "grim-trigger": GrimTrigger,
        "random": RandomBot,
    }
    if name not in bots:
        raise KeyError(f"unknown bot {name!r}; choose from {sorted(bots)}")
    return bots[name]()
