### What the run shows

Stated no more strongly than the intervals allow:

- **Haiku and DeepSeek play almost exactly like Grim Trigger.** They open with A, answer a betrayal with B 98–99% of the time, and almost never go back to A. Haiku's move matches Grim Trigger's rule in 99% of rounds [97–100]. That style earned the most per round in this field, though the top four players' intervals overlap.
- **Gemini Flash is the clear outlier on cooperation.** It chose A in 49% of its rounds against Haiku's 81%, and those intervals do not overlap. Its higher payoff against an unconditional cooperator (3.39) and lower payoff per round (2.27) both have intervals that overlap the other models', so they are leads to test with more matches, not findings. Gemini and Haiku cooperated in only 40% [11–80] of the rounds they played against each other.
- **GPT-5 mini forgives more often than Haiku** (10% [5–17] against 1% [0–2]) and retaliates less consistently (91% [86–95] against 99% [98–100]).
- **Against themselves,** Haiku and DeepSeek cooperated in every round; Gemini managed 60% [17–90].

### Conditions the results depend on

- One framing of the game: neutral A/B labels, the payoff table, a 10% chance of ending after each round, simultaneous moves. A different framing could change behaviour.
- Temperature 0.7, and every model asked for low reasoning effort. The same request does not produce the same amount of thinking: per call, Haiku reasoned for about 13 tokens, GPT-5 mini 234, Gemini 359 and DeepSeek 734.
- This field of opponents. In a round-robin, payoff rankings depend on who else is playing, so they describe this tournament, not the models in general. Cooperation, retaliation and forgiveness depend less on the field than payoff does.
- DeepSeek forfeited 1% of its rounds (an answer still cut off at a 4,000-token cap), recorded as B. That is under the 2% validity threshold, but it slightly lowers DeepSeek's cooperation figure.
- 90 matches per model. Differences inside the intervals are not findings.
