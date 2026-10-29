"""A language model as a player: build the prompt, call the transport, parse the answer, retry once."""

from __future__ import annotations

import json
import re

from ..engine import DEFECT, MOVES, PAYOFFS, Decision, MatchView
from ..llm import CompletionRequest, Transport

# The options are called A and B and the game is never named, so the model
# reasons from the payoff table rather than recalling a textbook strategy.
SYSTEM_PROMPT = """\
You are playing a repeated two-player game against another player.

Each round, you and the other player each choose option A or option B at the same time, \
without seeing the other's choice for that round. Payoffs per round, written as (yours, theirs):
- you A, they A: ({AA}, {AA_t})
- you A, they B: ({AB}, {AB_t})
- you B, they A: ({BA}, {BA_t})
- you B, they B: ({BB}, {BB_t})

After each round the game continues with probability {cont:.2f} and ends with probability {end:.2f}, \
so you never know which round is the last. Your goal is to earn as many points as you can in total \
over the whole game.

Reply with JSON only, exactly {{"move": "A"}} or {{"move": "B"}}, and nothing else."""

REMINDER = 'That answer was not valid. Reply with exactly {"move": "A"} or {"move": "B"} and nothing else.'

_JSON_OBJECT = re.compile(r"\{[^{}]*\}")


def system_prompt(view: MatchView) -> str:
    return SYSTEM_PROMPT.format(
        AA=PAYOFFS["A", "A"][0], AA_t=PAYOFFS["A", "A"][1],
        AB=PAYOFFS["A", "B"][0], AB_t=PAYOFFS["A", "B"][1],
        BA=PAYOFFS["B", "A"][0], BA_t=PAYOFFS["B", "A"][1],
        BB=PAYOFFS["B", "B"][0], BB_t=PAYOFFS["B", "B"][1],
        cont=1 - view.rules.end_probability,
        end=view.rules.end_probability,
    )


def round_prompt(view: MatchView) -> str:
    if not view.my_moves:
        history = "No rounds have been played yet."
    else:
        lines = [
            f"Round {i}: you chose {m}, they chose {t}."
            for i, (m, t) in enumerate(zip(view.my_moves, view.their_moves), start=1)
        ]
        history = "History so far:\n" + "\n".join(lines)
        history += f"\nTotals so far: you {view.my_score}, they {view.their_score}."
    return f"{history}\n\nRound {view.round_number}. Choose your move."


def parse_move(text: str):
    """The move in the first JSON object of the form {"move": "A"|"B"}, or None if there is none."""
    for candidate in _JSON_OBJECT.findall(text):
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("move"), str):
            move = obj["move"].strip().upper()
            if move in MOVES:
                return move
    return None


class ModelPlayer:
    def __init__(
        self,
        name: str,
        model: str,
        transport: Transport,
        temperature: float = 0.7,
        max_tokens: int = 50,
        reasoning: str | None = None,
    ) -> None:
        self.name = name
        self.model = model
        self._transport = transport
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._reasoning = reasoning

    def _request(self, messages: list[tuple[str, str]], view: MatchView, attempt: int) -> CompletionRequest:
        return CompletionRequest(
            model=self.model,
            messages=tuple(messages),
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            tag=f"{view.match_id}/seat{view.seat}/round{view.round_number}/attempt{attempt}",
            reasoning=self._reasoning,
        )

    async def move(self, view: MatchView) -> Decision:
        """One call; on a bad answer, one retry with a reminder; then a forfeit.

        Flags tell the analysis what happened: "retried" (the second answer was
        used), "forfeit" (recorded as B because neither answer was usable), and
        "truncated" (an answer was cut off at max_tokens, which usually means
        the model's reasoning used the whole budget). A truncated forfeit is a
        configuration problem, not a choice the model made, and the report
        says so.
        """
        messages = [("system", system_prompt(view)), ("user", round_prompt(view))]
        first = await self._transport.complete(self._request(messages, view, 0))
        move = parse_move(first.text)
        if move is not None:
            return Decision(move)

        messages += [("assistant", first.text), ("user", REMINDER)]
        second = await self._transport.complete(self._request(messages, view, 1))
        move = parse_move(second.text)
        truncated = ("truncated",) if (first.truncated or second.truncated) else ()
        if move is not None:
            return Decision(move, flags=("retried",) + truncated)
        return Decision(DEFECT, flags=("forfeit",) + truncated)
