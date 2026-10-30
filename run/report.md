```
{
  "calls_by_model": {
    "anthropic/claude-haiku-5.5": {
      "calls": 1089,
      "completion_tokens": 26173,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 5248,
      "latency_ms_p50": 767,
      "latency_ms_p95": 2436,
      "prompt_tokens": 438994,
      "reasoning_tokens": 14384
    },
    "deepseek/deepseek-v4.1-flash": {
      "calls": 781,
      "completion_tokens": 580002,
      "cut_off": 23,
      "empty": 23,
      "latency_ms_max": 48095,
      "latency_ms_p50": 3311,
      "latency_ms_p95": 18797,
      "prompt_tokens": 260206,
      "reasoning_tokens": 573181
    },
    "google/gemini-2.5-flash": {
      "calls": 918,
      "completion_tokens": 335610,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 9866,
      "latency_ms_p50": 2255,
      "latency_ms_p95": 2721,
      "prompt_tokens": 286403,
      "reasoning_tokens": 329948
    },
    "openai/gpt-5-mini": {
      "calls": 905,
      "completion_tokens": 251400,
      "cut_off": 0,
      "empty": 0,
      "latency_ms_max": 24842,
      "latency_ms_p50": 3943,
      "latency_ms_p95": 8420,
      "prompt_tokens": 272572,
      "reasoning_tokens": 211968
    }
  },
  "completed": true,
  "live_calls": 3693,
  "matches": 400,
  "matches_total": 400,
  "name": "m1-small-models",
  "recorded_calls": 3693,
  "replay": false,
  "spent_usd": 2.65876,
  "stopped_reason": ""
}
```
400 matches, 3772 rounds, 9 players. Brackets are 95% bootstrap intervals over matches.

| Player | Matches | Payoff/round | Cooperation | Retaliation | Forgiveness | vs Always Cooperate | Retried | Forfeits | Cut off |
|---|---|---|---|---|---|---|---|---|---|
| haiku | 90 | 2.65 [2.44–2.80] | 81% [71–89] | 99% [98–100] | 1% [0–2] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| deepseek-flash | 90 | 2.63 [2.34–2.88] | 77% [62–91] | 98% [94–100] | 5% [2–17] | 3.00 [3.00–3.00] | 2% [1–3] | 1% [0–2] | 2% [1–5] |
| tit-for-tat | 80 | 2.45 [2.18–2.71] | 75% [63–88] | 100% [100–100] | 11% [4–28] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| gpt-mini | 90 | 2.43 [2.18–2.63] | 69% [56–79] | 91% [85–95] | 10% [5–17] | 3.10 [3.00–3.26] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| grim-trigger | 80 | 2.42 [2.18–2.65] | 65% [52–79] | 100% [100–100] | 0% [0–0] | 3.00 [3.00–3.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| always-cooperate | 80 | 2.32 [2.00–2.62] | 100% [100–100] | 0% [0–0] | – | – | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| gemini-flash | 90 | 2.27 [2.01–2.53] | 49% [37–62] | 95% [92–97] | 4% [2–8] | 3.39 [3.00–4.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| always-defect | 80 | 1.89 [1.56–2.28] | 0% [0–0] | 100% [100–100] | 0% [0–0] | 5.00 [5.00–5.00] | 0% [0–0] | 0% [0–0] | 0% [0–0] |
| random | 80 | 1.86 [1.51–2.21] | 49% [45–52] | 53% [48–58] | 46% [38–53] | 4.06 [3.94–4.23] | 0% [0–0] | 0% [0–0] | 0% [0–0] |

Fingerprint: share of rounds where the player's move matches each classic rule, given the same history.

| Player | always-cooperate | always-defect | tit-for-tat | grim-trigger |
|---|---|---|---|---|
| haiku | 81% [71–89] | 19% [11–29] | 98% [96–99] | 99% [97–100] |
| deepseek-flash | 77% [62–91] | 23% [9–38] | 96% [90–100] | 95% [91–99] |
| tit-for-tat | 75% [63–88] | 25% [11–37] | 100% [100–100] | 95% [91–99] |
| gpt-mini | 69% [56–79] | 31% [21–44] | 92% [88–95] | 90% [85–94] |
| grim-trigger | 65% [52–79] | 35% [21–48] | 95% [91–98] | 100% [100–100] |
| always-cooperate | 100% [100–100] | 0% [0–0] | 80% [70–89] | 75% [63–86] |
| gemini-flash | 49% [37–62] | 51% [38–63] | 86% [80–90] | 89% [84–93] |
| always-defect | 0% [0–0] | 100% [100–100] | 71% [61–78] | 75% [66–82] |
| random | 49% [45–52] | 51% [48–55] | 52% [48–56] | 51% [48–55] |

Mutual cooperation: share of rounds where both players chose A, per pairing.

| | haiku | deepseek-flash | tit-for-tat | gpt-mini | grim-trigger | always-cooperate | gemini-flash | always-defect | random |
|---|---|---|---|---|---|---|---|---|---|
| haiku | 100% [100–100] | 100% [100–100] | 100% [100–100] | 82% [45–100] | 100% [100–100] | 100% [100–100] | 40% [12–80] | 0% [0–0] | 31% [14–54] |
| deepseek-flash | 100% [100–100] | 100% [100–100] | 97% [92–100] | 87% [56–100] | 100% [100–100] | 100% [100–100] | 80% [55–97] | 0% [0–0] | 9% [3–32] |
| tit-for-tat | 100% [100–100] | 97% [92–100] | – | 86% [55–100] | 100% [100–100] | 100% [100–100] | 59% [22–95] | 0% [0–0] | 25% [11–47] |
| gpt-mini | 82% [45–100] | 87% [56–100] | 86% [55–100] | 89% [70–98] | 77% [47–100] | 95% [87–100] | 46% [8–87] | 0% [0–0] | 24% [14–33] |
| grim-trigger | 100% [100–100] | 100% [100–100] | 100% [100–100] | 77% [47–100] | – | 100% [100–100] | 40% [7–78] | 0% [0–0] | 10% [3–25] |
| always-cooperate | 100% [100–100] | 100% [100–100] | 100% [100–100] | 95% [87–100] | 100% [100–100] | – | 81% [50–100] | 0% [0–0] | 47% [38–53] |
| gemini-flash | 40% [12–80] | 80% [55–97] | 59% [22–95] | 46% [8–87] | 40% [7–78] | 81% [50–100] | 60% [19–90] | 0% [0–0] | 10% [3–20] |
| always-defect | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | 0% [0–0] | – | 0% [0–0] |
| random | 31% [14–54] | 9% [3–32] | 25% [11–47] | 24% [14–33] | 10% [3–25] | 47% [38–53] | 10% [3–20] | 0% [0–0] | – |

Mean payoff per round, row player against column player.

| | haiku | deepseek-flash | tit-for-tat | gpt-mini | grim-trigger | always-cooperate | gemini-flash | always-defect | random |
|---|---|---|---|---|---|---|---|---|---|
| haiku | 3.00 | 3.00 | 3.00 | 2.70 | 3.00 | 3.00 | 1.85 | 0.90 | 2.55 |
| deepseek-flash | 3.00 | 3.00 | 2.99 | 2.80 | 3.00 | 3.00 | 2.73 | 0.91 | 2.75 |
| tit-for-tat | 3.00 | 2.99 | – | 2.84 | 3.00 | 3.00 | 2.31 | 0.91 | 1.98 |
| gpt-mini | 2.70 | 2.87 | 2.91 | 2.88 | 2.58 | 3.10 | 1.91 | 0.93 | 2.39 |
| grim-trigger | 3.00 | 3.00 | 3.00 | 2.76 | – | 3.00 | 1.96 | 0.90 | 2.34 |
| always-cooperate | 3.00 | 3.00 | 3.00 | 2.86 | 3.00 | – | 2.42 | 0.00 | 1.41 |
| gemini-flash | 1.96 | 2.85 | 2.46 | 2.18 | 1.87 | 3.39 | 2.44 | 0.94 | 2.65 |
| always-defect | 1.40 | 1.35 | 1.34 | 1.27 | 1.41 | 5.00 | 1.26 | – | 2.98 |
| random | 1.83 | 1.35 | 2.46 | 1.97 | 1.27 | 4.06 | 1.28 | 0.50 | – |
