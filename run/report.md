```
{
  "calls_by_model": {
    "anthropic/claude-haiku-5.5": {
      "calls": 138,
      "completion_tokens": 1709,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 2475,
      "latency_ms_p50": 687,
      "latency_ms_p95": 1123,
      "prompt_tokens": 78234,
      "reasoning_tokens": 188
    },
    "deepseek/deepseek-v4.1-flash": {
      "calls": 69,
      "completion_tokens": 27362,
      "cut_off": 1,
      "empty": 1,
      "latency_ms_max": 30232,
      "latency_ms_p50": 1898,
      "latency_ms_p95": 14480,
      "prompt_tokens": 26221,
      "reasoning_tokens": 27056
    },
    "google/gemini-2.5-flash": {
      "calls": 69,
      "completion_tokens": 25069,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 2551,
      "latency_ms_p50": 2059,
      "latency_ms_p95": 2449,
      "prompt_tokens": 21052,
      "reasoning_tokens": 24650
    },
    "openai/gpt-5-mini": {
      "calls": 95,
      "completion_tokens": 12674,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 3858,
      "latency_ms_p50": 1947,
      "latency_ms_p95": 3259,
      "prompt_tokens": 30727,
      "reasoning_tokens": 8704
    }
  },
  "completed": true,
  "live_calls": 371,
  "matches": 25,
  "matches_total": 25,
  "name": "m3-named-dry-run",
  "recorded_calls": 371,
  "replay": false,
  "spent_usd": 0.21747,
  "stopped_reason": ""
}
```
25 matches, 291 rounds, 7 players. Brackets are 95% bootstrap intervals over matches.

| Player | Matches | Payoff/round | Cooperation | Retaliation | Forgiveness | vs Always Cooperate | Retried | Forfeits | Cut off |
|---|---|---|---|---|---|---|---|---|---|
| deepseek-flash | 7 | 2.96 [2.67–3.00] | 100% [100–100] | – | – | 3.00 [3.00–3.00] | 1% [0–2] | 0% [0–0] | 1% [0–2] |
| gpt-mini | 7 | 2.81 [2.09–3.00] | 92% [62–100] | 100% [100–100] | 0% [0–0] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| haiku | 7 | 2.80 [1.62–3.00] | 91% [38–100] | 100% [100–100] | 0% [0–0] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| always-cooperate | 6 | 2.27 [0.46–3.00] | 100% [100–100] | 0% [0–0] | – | – | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| always-defect | 6 | 2.09 [1.25–3.81] | 0% [0–0] | 100% [100–100] | 0% [0–0] | 5.00 [5.00–5.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| gemini-flash | 7 | 2.07 [1.33–3.00] | 41% [7–82] | 100% [100–100] | 0% [0–0] | 5.00 [5.00–5.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| tit-for-tat | 6 | 1.59 [1.04–3.00] | 34% [8–100] | 100% [100–100] | 0% [0–0] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |

Fingerprint: share of rounds where the player's move matches each classic rule, given the same history.

| Player | always-cooperate | always-defect | tit-for-tat | grim-trigger |
|---|---|---|---|---|
| deepseek-flash | 100% [100–100] | 0% [0–0] | 100% [100–100] | 100% [100–100] |
| gpt-mini | 92% [62–100] | 8% [0–37] | 99% [98–100] | 99% [98–100] |
| haiku | 91% [38–100] | 9% [0–59] | 100% [100–100] | 100% [100–100] |
| always-cooperate | 100% [100–100] | 0% [0–0] | 78% [24–100] | 78% [24–100] |
| always-defect | 0% [0–0] | 100% [100–100] | 67% [26–88] | 67% [26–88] |
| gemini-flash | 41% [7–82] | 59% [18–93] | 88% [69–97] | 88% [69–97] |
| tit-for-tat | 34% [8–100] | 66% [0–92] | 100% [100–100] | 100% [100–100] |

Mutual cooperation: share of rounds where both players chose A, per pairing.

| | deepseek-flash | gpt-mini | haiku | always-cooperate | always-defect | gemini-flash | tit-for-tat |
|---|---|---|---|---|---|---|---|
| deepseek-flash | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 0% [0–0] | 100% [100–100] | 100% [100–100] |
| gpt-mini | 100% [100–100] | 96% [96–96] | 100% [100–100] | 100% [100–100] | 0% [0–0] | 100% [100–100] | 100% [100–100] |
| haiku | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 0% [0–0] | 100% [100–100] | 100% [100–100] |
| always-cooperate | 100% [100–100] | 100% [100–100] | 100% [100–100] | – | 0% [0–0] | 0% [0–0] | 100% [100–100] |
| always-defect | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | – | 0% [0–0] | 0% [0–0] |
| gemini-flash | 100% [100–100] | 100% [100–100] | 100% [100–100] | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| tit-for-tat | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 0% [0–0] | 0% [0–0] | – |

Mean payoff per round, row player against column player.

| | deepseek-flash | gpt-mini | haiku | always-cooperate | always-defect | gemini-flash | tit-for-tat |
|---|---|---|---|---|---|---|---|
| deepseek-flash | 3.00 | 3.00 | 3.00 | 3.00 | 0.00 | 3.00 | 3.00 |
| gpt-mini | 3.00 | 2.98 | 3.00 | 3.00 | 0.88 | 3.00 | 3.00 |
| haiku | 3.00 | 3.00 | 3.00 | 3.00 | 0.92 | 3.00 | 3.00 |
| always-cooperate | 3.00 | 3.00 | 3.00 | – | 0.00 | 0.00 | 3.00 |
| always-defect | 5.00 | 1.50 | 1.31 | 5.00 | – | 1.50 | 1.15 |
| gemini-flash | 3.00 | 3.00 | 3.00 | 5.00 | 0.88 | 1.30 | 1.19 |
| tit-for-tat | 3.00 | 3.00 | 3.00 | 3.00 | 0.96 | 0.95 | – |
