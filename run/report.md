```
{
  "calls_by_model": {
    "anthropic/claude-haiku-5.5": {
      "calls": 909,
      "completion_tokens": 13502,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 4577,
      "latency_ms_p50": 700,
      "latency_ms_p95": 1209,
      "prompt_tokens": 387121,
      "reasoning_tokens": 3132
    },
    "deepseek/deepseek-v4.1-flash": {
      "calls": 630,
      "completion_tokens": 195199,
      "cut_off": 4,
      "empty": 4,
      "latency_ms_max": 76252,
      "latency_ms_p50": 1557,
      "latency_ms_p95": 12713,
      "prompt_tokens": 217047,
      "reasoning_tokens": 191627
    },
    "google/gemini-2.5-flash": {
      "calls": 644,
      "completion_tokens": 228016,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 4472,
      "latency_ms_p50": 2246,
      "latency_ms_p95": 2693,
      "prompt_tokens": 196135,
      "reasoning_tokens": 224097
    },
    "openai/gpt-5-mini": {
      "calls": 703,
      "completion_tokens": 104323,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 11938,
      "latency_ms_p50": 1960,
      "latency_ms_p95": 3858,
      "prompt_tokens": 218147,
      "reasoning_tokens": 74496
    }
  },
  "completed": true,
  "live_calls": 2515,
  "matches": 250,
  "matches_total": 250,
  "name": "m3-named",
  "recorded_calls": 2886,
  "replay": false,
  "spent_usd": 1.335276,
  "stopped_reason": ""
}
```
250 matches, 2311 rounds, 7 players. Brackets are 95% bootstrap intervals over matches.

| Player | Matches | Payoff/round | Cooperation | Retaliation | Forgiveness | vs Always Cooperate | Retried | Forfeits | Cut off |
|---|---|---|---|---|---|---|---|---|---|
| haiku | 70 | 2.68 [2.46–2.86] | 86% [76–94] | 100% [100–100] | 1% [0–3] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| deepseek-flash | 70 | 2.62 [2.25–2.93] | 83% [66–98] | 100% [100–100] | 0% [0–0] | 3.00 [3.00–3.00] | 1% [0–1] | 0% [0–0] | 1% [0–1] |
| gemini-flash | 70 | 2.47 [2.15–2.76] | 65% [50–78] | 99% [98–100] | 0% [0–0] | 3.39 [3.00–3.97] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| tit-for-tat | 60 | 2.47 [2.13–2.79] | 76% [60–92] | 100% [100–100] | 2% [0–9] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| gpt-mini | 70 | 2.40 [2.11–2.65] | 73% [60–84] | 97% [91–100] | 2% [0–6] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| always-cooperate | 60 | 2.40 [1.96–2.74] | 100% [100–100] | 0% [0–0] | – | – | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| always-defect | 60 | 1.80 [1.46–2.26] | 0% [0–0] | 100% [100–100] | 0% [0–0] | 5.00 [5.00–5.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |

Fingerprint: share of rounds where the player's move matches each classic rule, given the same history.

| Player | always-cooperate | always-defect | tit-for-tat | grim-trigger |
|---|---|---|---|---|
| haiku | 86% [76–94] | 14% [6–24] | 100% [99–100] | 100% [100–100] |
| deepseek-flash | 83% [66–98] | 17% [2–34] | 100% [100–100] | 100% [100–100] |
| gemini-flash | 65% [50–78] | 35% [22–50] | 93% [86–97] | 93% [86–97] |
| tit-for-tat | 76% [60–92] | 24% [8–40] | 100% [100–100] | 96% [87–100] |
| gpt-mini | 73% [60–84] | 27% [16–40] | 97% [95–99] | 94% [86–99] |
| always-cooperate | 100% [100–100] | 0% [0–0] | 82% [69–93] | 82% [69–93] |
| always-defect | 0% [0–0] | 100% [100–100] | 73% [61–81] | 73% [61–81] |

Mutual cooperation: share of rounds where both players chose A, per pairing.

| | haiku | deepseek-flash | gemini-flash | tit-for-tat | gpt-mini | always-cooperate | always-defect |
|---|---|---|---|---|---|---|---|
| haiku | 100% [100–100] | 100% [100–100] | 63% [29–100] | 100% [100–100] | 88% [74–100] | 100% [100–100] | 0% [0–0] |
| deepseek-flash | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 100% [100–100] | 0% [0–0] |
| gemini-flash | 63% [29–100] | 100% [100–100] | 71% [35–99] | 74% [38–100] | 82% [44–100] | 81% [51–100] | 0% [0–0] |
| tit-for-tat | 100% [100–100] | 100% [100–100] | 74% [38–100] | – | 97% [94–100] | 100% [100–100] | 0% [0–0] |
| gpt-mini | 88% [74–100] | 100% [100–100] | 82% [44–100] | 97% [94–100] | 74% [46–94] | 100% [100–100] | 0% [0–0] |
| always-cooperate | 100% [100–100] | 100% [100–100] | 81% [51–100] | 100% [100–100] | 100% [100–100] | – | 0% [0–0] |
| always-defect | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | – |

Mean payoff per round, row player against column player.

| | haiku | deepseek-flash | gemini-flash | tit-for-tat | gpt-mini | always-cooperate | always-defect |
|---|---|---|---|---|---|---|---|
| haiku | 3.00 | 3.00 | 2.23 | 3.00 | 2.91 | 3.00 | 0.90 |
| deepseek-flash | 3.00 | 3.00 | 3.00 | 3.00 | 3.00 | 3.00 | 0.91 |
| gemini-flash | 2.39 | 3.00 | 2.50 | 2.59 | 2.86 | 3.39 | 0.93 |
| tit-for-tat | 3.00 | 3.00 | 2.48 | – | 2.99 | 3.00 | 0.91 |
| gpt-mini | 2.80 | 3.00 | 2.60 | 2.99 | 2.57 | 3.00 | 0.93 |
| always-cooperate | 3.00 | 3.00 | 2.42 | 3.00 | 3.00 | – | 0.00 |
| always-defect | 1.40 | 1.35 | 1.29 | 1.34 | 1.30 | 5.00 | – |
