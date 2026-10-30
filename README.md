# tit-for-token

[![CI](https://github.com/kennethkimbrough/tit-for-token/actions/workflows/ci.yml/badge.svg)](https://github.com/kennethkimbrough/tit-for-token/actions/workflows/ci.yml)

How do language models behave in repeated strategic games, against each other
and against classic strategies like Tit-for-Tat? tit-for-token runs round-robin
tournaments of the iterated prisoner's dilemma between models and baseline
bots, records every model call so any tournament can be replayed exactly and
for free, and reports cooperation, retaliation, forgiveness and exploitation
with bootstrap confidence intervals.

**Results site: [kennethkimbrough.github.io/tit-for-token](https://kennethkimbrough.github.io/tit-for-token/)**,
with a sortable leaderboard, every pairing as a heatmap, and a viewer that
steps through any of the 400 recorded matches round by round. It is built from
the committed run on every push.

**Status:** milestones 1 and 2 are complete: the tournament harness, one
committed tournament between four small models, and the results site. Next is
a test of how the game's framing changes behaviour (milestone 3). See
[DESIGN.md](DESIGN.md).

## Results: milestone 1

Four small models from different labs and five classic bots, 400 matches
(3,772 rounds), from [`runs/m1-small-models`](runs/m1-small-models). Every
number below comes from that run, and CI replays it from its recording
(3,693 model calls) on every push. Brackets are 95% bootstrap intervals over
matches; the full report, with pairwise tables, is
[`runs/m1-small-models/report.md`](runs/m1-small-models/report.md).

| Player | Payoff per round | Cooperates | Retaliates | Forgives | vs Always Cooperate |
|---|---|---|---|---|---|
| Claude Haiku 5.5 | **2.65** [2.45–2.80] | 81% [71–89] | 99% [98–100] | 1% [0–2] | 3.00 [3.00–3.00] |
| DeepSeek V4.1 Flash | **2.63** [2.34–2.87] | 77% [62–91] | 98% [94–100] | 5% [2–16] | 3.00 [3.00–3.00] |
| Tit-for-Tat | 2.45 [2.19–2.71] | 75% [63–88] | 100% | 11% [4–28] | 3.00 |
| GPT-5 mini | 2.43 [2.19–2.64] | 69% [57–79] | 91% [86–95] | 10% [5–17] | 3.10 [3.00–3.25] |
| Grim Trigger | 2.42 [2.19–2.65] | 65% [52–79] | 100% | 0% | 3.00 |
| Always Cooperate | 2.32 [2.00–2.61] | 100% | 0% | – | – |
| Gemini 2.5 Flash | 2.27 [2.00–2.53] | **49%** [37–62] | 95% [93–97] | 4% [2–7] | **3.39** [3.00–4.00] |
| Always Defect | 1.89 [1.59–2.28] | 0% | 100% | 0% | 5.00 |
| Random | 1.86 [1.53–2.21] | 49% [45–53] | 53% [48–58] | 46% [39–53] | 4.06 [3.94–4.25] |

*Retaliates: plays B in the round after the opponent played B. Forgives:
plays A in the round after retaliating. vs Always Cooperate: payoff per round
against an unconditional cooperator, where 3 means cooperating with it and 5
means exploiting it fully.*

What the run shows, stated no more strongly than the intervals allow:

- **Haiku and DeepSeek play almost exactly like Grim Trigger.** They open
  with A, answer a betrayal with B 98–99% of the time, and almost never go
  back to A. Haiku's move matches Grim Trigger's rule in 99% of rounds
  [97–100]. That style earned the most per round in this field, though the
  top four players' intervals overlap.
- **Gemini Flash is the clear outlier on cooperation.** It chose A in 49% of
  its rounds against Haiku's 81%, and those intervals do not overlap. It also
  has the highest payoff of any model against an unconditional cooperator
  (3.39) and the lowest payoff per round of the four models (2.27), but both
  of those intervals overlap the other models', so they are leads to test
  with more matches, not findings. Gemini and Haiku cooperated in only 40%
  [11–80] of the rounds they played against each other.
- **GPT-5 mini forgives more often than Haiku** (10% [5–17] against 1%
  [0–2]) and retaliates less consistently (91% [86–95] against 99%
  [98–100]).
- **Against themselves,** Haiku and DeepSeek cooperated in every round;
  Gemini managed 60% [17–90].

Conditions, which the results depend on:

- One framing of the game: neutral A/B labels, the payoff table, a 10%
  chance of ending after each round, simultaneous moves. A different framing
  could change behaviour; that is milestone 3.
- Temperature 0.7, and every model asked for **low reasoning effort**. The
  same request does not produce the same amount of thinking: per call,
  Haiku reasoned for about 13 tokens, GPT-5 mini 234, Gemini 359 and
  DeepSeek 734 (from [`run.json`](runs/m1-small-models/run.json)).
- This field of opponents. In a round-robin, payoff rankings depend on who
  else is playing, so they describe this tournament, not the models in
  general. Cooperation, retaliation and forgiveness are less sensitive to
  the field than payoff is.
- DeepSeek forfeited 1% of its rounds (an answer still cut off at a
  4,000-token cap), recorded as B. That is under the report's 2% validity
  threshold, but it slightly lowers DeepSeek's cooperation figure.
- 90 matches per model. Differences inside the intervals are not findings.

The run took 21 minutes on a GitHub Actions runner and cost about $2.66 at
OpenRouter's listed prices.

## How it works

Each match is an iterated prisoner's dilemma. Both players choose at the same
time between two options; the options are called A and B and the game is never
named, so a model reasons from the payoff table instead of recalling a textbook
strategy. After every round the match ends with probability 0.1, so there is no
known last round to defect on; the length is drawn from the match seed before
play, so a match replays exactly.

| | A | B |
|---|---|---|
| **A** | 3, 3 | 0, 5 |
| **B** | 5, 0 | 1, 1 |

Players are classic bots (Always Cooperate, Always Defect, Tit-for-Tat, Grim
Trigger, seeded Random) and language models reached through one OpenRouter
key. A model answers each round with `{"move": "A"}` or `{"move": "B"}`; a
malformed answer gets one retry with a reminder, and a second failure is a
forfeit (recorded as B and flagged). Reasoning models get an explicit
reasoning effort, an answer cut off at `max_tokens` is flagged separately, and
the report marks a player's numbers invalid if it forfeits more than 2% of
rounds, since a forfeit counts as B. The retry, forfeit and cut-off rates are
all reported.

Every model call is recorded, keyed by the request content plus a tag naming
the call (match, seat, round, attempt), so each call is its own sample and a
tournament replays byte-for-byte from `calls.jsonl` without touching the
network. The runner plays every pairing N times with per-match seeds, limits
concurrency per provider, backs off on rate limits, stops cleanly at a
spending cap, and resumes from where it stopped.

The report gives, per player: payoff per round, cooperation rate, retaliation
(P(B | they played B last round)), forgiveness (P(A | I retaliated last
round)), payoff against Always Cooperate (3 means it cooperates, 5 means it
exploits fully), how often its moves match each classic rule given the same
history, and the retry and forfeit rates. Intervals are 95% bootstrap
intervals over matches, not rounds, since rounds within a match are not
independent. Two pairing tables show mutual cooperation and mean payoff for
every pair.

The full design and the decisions behind it are in [DESIGN.md](DESIGN.md).

## Run it

Python 3.11+, no runtime dependencies.

```sh
pip install -e ".[dev]"
pytest                                   # 48 tests, no network

export OPENROUTER_API_KEY=...            # never goes in a file
python -m tit_for_token run configs/m1-small-models.toml
python -m tit_for_token report runs/m1-small-models
python -m tit_for_token check  runs/m1-small-models    # replay from the recording and compare
python -m tit_for_token site   runs/m1-small-models --out site   # build the results site into site/
```

A run directory holds the config it was made with, `calls.jsonl` (the
recording), `matches.jsonl` (one match per line, sorted) and `run.json`
(counts and spending). Re-running the same command resumes; `--replay` makes
no network calls at all and fails loudly if the recording does not cover a
match.

Before a live run, check the model ids and prices in the config against
[openrouter.ai/models](https://openrouter.ai/models): the prices feed the
spending cap. Then do a dry run with `matches_per_pairing = 1` (about 400
calls) and check the report's "Cut off" column is 0% for every model.
`configs/m1-small-models.toml` (four small models from different labs, all at
low reasoning effort, five bots, ten matches per pairing) is about 4,000 calls.

## Layout

```
tit_for_token/
  engine.py          rules, payoffs, seeded length, the match loop (pure)
  players/bots.py    the five classic strategies, also exposed as rules for fingerprinting
  players/model.py   prompt, parse, retry, forfeit
  llm.py             OpenRouter client (stdlib), retry, throttle, budget
  recorder.py        record and replay
  config.py          TOML tournament config
  runner.py          round-robin scheduling, resume, output files
  analysis.py        metrics, bootstrap intervals, Markdown report
  site.py            results site: run data -> one self-contained index.html
  site_template.html the page itself (no framework, no build step)
  cli.py             run / report / check / site
tests/               pytest, with a fake model transport; no network
configs/             tournament configurations
runs/                committed tournaments (recording + matches), replayed in CI
```

## License

MIT
