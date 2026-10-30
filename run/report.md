```
{
  "calls_by_model": {
    "anthropic/claude-haiku-5.5": {
      "calls": 154,
      "completion_tokens": 2845,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 4047,
      "latency_ms_p50": 746,
      "latency_ms_p95": 2302,
      "prompt_tokens": 81250,
      "reasoning_tokens": 1204
    },
    "deepseek/deepseek-v4.1-flash": {
      "calls": 77,
      "completion_tokens": 56090,
      "cut_off": 6,
      "empty": 6,
      "latency_ms_max": 68019,
      "latency_ms_p50": 5033,
      "latency_ms_p95": 26114,
      "prompt_tokens": 29140,
      "reasoning_tokens": 55512
    },
    "google/gemini-2.5-flash": {
      "calls": 113,
      "completion_tokens": 41051,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 4646,
      "latency_ms_p50": 2242,
      "latency_ms_p95": 2709,
      "prompt_tokens": 36900,
      "reasoning_tokens": 40353
    },
    "openai/gpt-5-mini": {
      "calls": 106,
      "completion_tokens": 28586,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 13005,
      "latency_ms_p50": 4108,
      "latency_ms_p95": 6941,
      "prompt_tokens": 32486,
      "reasoning_tokens": 24064
    }
  },
  "completed": true,
  "live_calls": 450,
  "matches": 40,
  "matches_total": 40,
  "name": "m1-dry-run",
  "recorded_calls": 450,
  "replay": false,
  "spent_usd": 0.332013,
  "stopped_reason": ""
}
```
40 matches, 397 rounds, 9 players. Brackets are 95% bootstrap intervals over matches.

| Player | Matches | Payoff/round | Cooperation | Retaliation | Forgiveness | vs Always Cooperate | Retried | Forfeits | Cut off |
|---|---|---|---|---|---|---|---|---|---|
| grim-trigger | 8 | 2.94 [2.65–3.00] | 100% [100–100] | – | – | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| deepseek-flash | 9 | 2.92 [2.56–3.00] | 100% [100–100] | – | – | 3.00 [3.00–3.00] | 8% [0–13] | 0% [0–0] | 8% [0–13] |
| gpt-mini | 9 | 2.79 [2.11–3.00] | 91% [61–100] | 100% [100–100] | 0% [0–0] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| haiku | 9 | 2.75 [1.84–3.00] | 87% [42–100] | 100% [100–100] | 0% [0–0] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| random | 8 | 2.49 [1.52–3.35] | 40% [25–52] | 70% [30–86] | 33% [20–100] | 3.91 [3.91–3.91] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| always-cooperate | 8 | 2.36 [1.13–3.00] | 100% [100–100] | 0% [0–0] | – | – | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| gemini-flash | 9 | 2.21 [1.55–2.85] | 63% [27–94] | 90% [61–100] | 3% [0–21] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| always-defect | 8 | 2.06 [1.29–3.64] | 0% [0–0] | 100% [100–100] | 0% [0–0] | 5.00 [5.00–5.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| tit-for-tat | 8 | 1.65 [1.14–3.00] | 39% [14–100] | 100% [100–100] | 0% [0–0] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |

Fingerprint: share of rounds where the player's move matches each classic rule, given the same history.

| Player | always-cooperate | always-defect | tit-for-tat | grim-trigger |
|---|---|---|---|---|
| grim-trigger | 100% [100–100] | 0% [0–0] | 100% [100–100] | 100% [100–100] |
| deepseek-flash | 100% [100–100] | 0% [0–0] | 100% [100–100] | 100% [100–100] |
| gpt-mini | 91% [61–100] | 9% [0–39] | 100% [100–100] | 100% [100–100] |
| haiku | 87% [42–100] | 13% [0–58] | 99% [91–100] | 100% [100–100] |
| random | 40% [25–52] | 60% [48–74] | 55% [42–69] | 58% [48–69] |
| always-cooperate | 100% [100–100] | 0% [0–0] | 81% [43–100] | 74% [27–100] |
| gemini-flash | 63% [27–94] | 37% [6–73] | 92% [83–100] | 88% [69–100] |
| always-defect | 0% [0–0] | 100% [100–100] | 67% [31–86] | 68% [31–87] |
| tit-for-tat | 39% [14–100] | 61% [0–86] | 100% [100–100] | 100% [100–100] |

Mutual cooperation: share of rounds where both players chose A, per pairing.

| | grim-trigger | deepseek-flash | gpt-mini | haiku | random | always-cooperate | gemini-flash | always-defect | tit-for-tat |
|---|---|---|---|---|---|---|---|---|---|
| grim-trigger | – | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 0% [0–0] | 100% [100–100] |
| deepseek-flash | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 50% [50–50] | 100% [100–100] | 100% [100–100] | 0% [0–0] | 100% [100–100] |
| gpt-mini | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 20% [20–20] | 100% [100–100] | 100% [100–100] | 0% [0–0] | 100% [100–100] |
| haiku | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 0% [0–0] | 100% [100–100] | 100% [100–100] | 0% [0–0] | 100% [100–100] |
| random | 100% [100–100] | 50% [50–50] | 20% [20–20] | 0% [0–0] | – | 55% [55–55] | 38% [38–38] | 0% [0–0] | 33% [33–33] |
| always-cooperate | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 55% [55–55] | – | 100% [100–100] | 0% [0–0] | 100% [100–100] |
| gemini-flash | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 38% [38–38] | 100% [100–100] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| always-defect | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | – | 0% [0–0] |
| tit-for-tat | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 33% [33–33] | 100% [100–100] | 0% [0–0] | 0% [0–0] | – |

Mean payoff per round, row player against column player.

| | grim-trigger | deepseek-flash | gpt-mini | haiku | random | always-cooperate | gemini-flash | always-defect | tit-for-tat |
|---|---|---|---|---|---|---|---|---|---|
| grim-trigger | – | 3.00 | 3.00 | 3.00 | 3.00 | 3.00 | 3.00 | 0.00 | 3.00 |
| deepseek-flash | 3.00 | 3.00 | 3.00 | 3.00 | 1.50 | 3.00 | 3.00 | 0.00 | 3.00 |
| gpt-mini | 3.00 | 3.00 | 3.00 | 3.00 | 2.00 | 3.00 | 3.00 | 0.88 | 3.00 |
| haiku | 3.00 | 3.00 | 3.00 | 3.00 | 1.78 | 3.00 | 3.00 | 0.92 | 3.00 |
| random | 3.00 | 4.00 | 2.00 | 1.22 | – | 3.91 | 2.88 | 0.88 | 3.00 |
| always-cooperate | 3.00 | 3.00 | 3.00 | 3.00 | 1.64 | – | 3.00 | 0.00 | 3.00 |
| gemini-flash | 3.00 | 3.00 | 3.00 | 3.00 | 1.94 | 3.00 | 1.30 | 0.88 | 1.19 |
| always-defect | 5.00 | 5.00 | 1.50 | 1.31 | 1.50 | 5.00 | 1.50 | – | 1.15 |
| tit-for-tat | 3.00 | 3.00 | 3.00 | 3.00 | 1.33 | 3.00 | 0.95 | 0.96 | – |
