# Design

## The claim

> Here is how current language models behave in repeated strategic games,
> against each other and against classic strategies, measured with confidence
> intervals and reproducible from recorded runs.

Every number in the README must trace to a committed run and be reproducible
with `--replay`. No result is reported without a confidence interval.

## Game 1: iterated prisoner's dilemma

Each round both players choose simultaneously. Payoffs (row player, column
player):

|        | A      | B      |
|--------|--------|--------|
| **A**  | 3, 3   | 0, 5   |
| **B**  | 5, 0   | 1, 1   |

A is cooperate, B is defect, but players never see those words.

Decisions and why:

- **Neutral labels.** Options are "A" and "B" and the game is never named, so
  models reason from the payoff table instead of recalling textbook
  strategies. How much the framing changes behaviour is a later experiment
  (milestone 3), not an accident of the prompt.
- **Random length.** After every round the match ends with probability 0.1
  (expected length 10), so there is no known last round to defect on. The
  length is drawn up front from a per-match seed, so a match replays exactly.
- **Simultaneous moves.** Both players commit before either sees the other's
  move for that round.
- **What a model sees each round:** the rules, the payoff table, the
  continuation probability, the round number, and the full history of both
  players' moves. It must answer with JSON: `{"move": "A"}` or `{"move": "B"}`.
- **Malformed answers.** One retry with a short reminder of the format. A
  second failure is a forfeit, recorded as defect and flagged. The
  malformed-answer rate per model is a reported metric.
- **Reasoning models.** Providers count hidden reasoning against
  `max_tokens`, and a model whose reasoning uses the whole budget returns an
  empty answer. That would be recorded as a forfeit, i.e. as defection, and
  would make reasoning models look uncooperative for a configuration reason.
  So the reasoning effort is set explicitly per model (and is part of the
  recording key), an answer cut off at `max_tokens` carries its own
  "truncated" flag, and the report refuses to present a player's numbers as
  valid when its forfeit rate is above 2%, naming the cause. A dry run with
  one match per pairing checks the cut-off rate is zero before money is
  spent on the full run.
- **Sampling.** Fixed temperature and settings per model, recorded with every
  call.

## Players

One interface for every player:

```python
class Player(Protocol):
    name: str
    async def move(self, view: MatchView) -> Move: ...
```

Baseline bots (deterministic except Random, which takes a seed):

| Bot | Rule |
|---|---|
| Always Cooperate | always A |
| Always Defect | always B |
| Tit-for-Tat | A first, then copy the opponent's last move |
| Grim Trigger | A until the opponent plays B once, then B forever |
| Random | A or B with probability 0.5, seeded |

Bots cost nothing, give the tests deterministic expectations, and anchor the
results ("model X matches Tit-for-Tat's move in 80% of rounds").

Model players go through one adapter: build the prompt, call the API, parse
and validate the JSON, retry once. API keys come from environment variables
only and are never written to disk or logs.

## Architecture

Python only, one package.

```
engine/     rules, payoffs, seeded match length, match loop      pure, fully unit-tested
players/    bots + model adapter                                  one Player interface
recorder/   every model call stored as request hash -> response  JSONL, committed with the run
runner/     round-robin scheduler                                 asyncio
analysis/   metrics and bootstrap confidence intervals            plain functions over match records
site/       static results page and match viewer                  milestone 2
```

### Recording and replay

Model APIs are not fully deterministic, even at temperature 0, so the
recording is the source of truth, not the model.

- The request key is a hash of everything that determines the request: model
  id, sampling settings, the exact messages, and a tag naming the call (match,
  seat, round, attempt). The tag matters: without it every match's first
  round, which has an identical prompt, would share one recorded answer, and a
  model playing itself would get the same answer on both sides. Each call is
  its own sample. The response is stored with token counts and latency.
- Live mode answers from the recording when the call is already there and
  makes a live call otherwise, appending it. That is what makes a resumed run
  free for the matches that already happened.
- `--replay` makes no network calls; a request missing from the recording is
  an error, never a silent live call.
- A test runs a small tournament live against a fake model, then replays it
  and asserts the match records are byte-identical. CI runs a replay of the
  committed tournament on every push, at no API cost.

### Runner

- Round-robin: every pair of players plays N matches (and each model also
  plays itself), each with its own seed derived from the tournament seed and
  the pairing, so results don't depend on scheduling order.
- Concurrency: an `asyncio` semaphore per model (each model has its own rate
  limit at the provider), exponential backoff with jitter on rate limits and
  server errors.
- Spending cap: estimated cost from token counts is checked before each call;
  the run stops cleanly when the cap would be exceeded.
- Resume: completed matches are written as they finish, keyed by match id; a
  rerun skips them.

## Metrics

Per player, over all its matches:

- cooperation rate, and mutual-cooperation rate per pairing
- average payoff per round
- retaliation: P(B | opponent played B last round)
- forgiveness: P(A | I retaliated last round)
- exploitation: payoff gap against Always Cooperate and against weaker models
- fingerprint: the share of rounds where its move matches each bot's rule,
  given the same history
- malformed-answer rate

Confidence intervals by bootstrap over matches (not rounds, since rounds in a
match are not independent). When a model plays itself, both of its sides come
from one match and are resampled together, so self-play does not narrow the
interval falsely. Report 95% intervals; call two players different only when
the intervals say so.

## Milestone 1 (done means all of these are true)

1. Engine and the five bots, with unit tests including seeded match lengths
   and payoff accounting.
2. Model adapter for three or four inexpensive models behind one API key,
   with JSON validation, one retry, and forfeit handling.
3. Recorder with record and replay modes, and the byte-identical replay test.
4. Round-robin runner with per-provider concurrency, backoff, spending cap
   and resume.
5. One committed tournament (four models plus five bots, ten matches per
   pairing, about 4,000 model calls, expected to cost a few dollars with
   small models) with a results table and confidence intervals in the README.
6. GitHub Actions running the tests and the replay check.

## Later milestones

- **2:** static results site on GitHub Pages: leaderboard, per-pair tables,
  and a match viewer that steps through any recorded match round by round.
- **3:** cheap talk (players may send one short message before each move) and
  the framing experiment (neutral labels vs. named game).
- **4:** a second game: the ultimatum game or a public-goods game.
- **Later:** larger frontier models on a sampled subset; a negotiation game.

## Out of scope

A general multi-agent framework, a hosted service, user accounts, and any
claim about what models "intend". The project reports behaviour, not motives.
