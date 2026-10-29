# tit-for-token

[![CI](https://github.com/kennethkimbrough/tit-for-token/actions/workflows/ci.yml/badge.svg)](https://github.com/kennethkimbrough/tit-for-token/actions/workflows/ci.yml)

How do language models behave in repeated strategic games, against each other
and against classic strategies like Tit-for-Tat? tit-for-token runs round-robin
tournaments of the iterated prisoner's dilemma between models and baseline
bots, records every model call so any tournament can be replayed exactly and
for free, and reports cooperation, retaliation, forgiveness and exploitation
with bootstrap confidence intervals.

**Status:** the engine, bots, model adapter, recorder, runner, analysis and
command line are built and tested (no network in the tests). **No tournament
has been run against real models yet**, so there are no results to report.
Results will appear here only when they come from a run committed under
`runs/`, where CI replays it from its recording on every push.

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
forfeit (recorded as B and flagged). The retry and forfeit rates are reported.

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
pytest                                   # 37 tests, no network

export OPENROUTER_API_KEY=...            # never goes in a file
python -m tit_for_token run configs/m1-small-models.toml
python -m tit_for_token report runs/m1-small-models
python -m tit_for_token check  runs/m1-small-models    # replay from the recording and compare
```

A run directory holds the config it was made with, `calls.jsonl` (the
recording), `matches.jsonl` (one match per line, sorted) and `run.json`
(counts and spending). Re-running the same command resumes; `--replay` makes
no network calls at all and fails loudly if the recording does not cover a
match.

Before a live run, check the model ids and prices in the config against
[openrouter.ai/models](https://openrouter.ai/models): the prices feed the
spending cap. `configs/m1-small-models.toml` (four small models from
different labs, five bots, ten matches per pairing) is about 4,000 calls.

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
  cli.py             run / report / check
tests/               pytest, with a fake model transport; no network
configs/             tournament configurations
runs/                committed tournaments (recording + matches), replayed in CI
```

## License

MIT
