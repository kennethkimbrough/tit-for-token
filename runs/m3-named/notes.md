### What naming the game changed

The same four models, told they are playing the iterated prisoner's dilemma, with option A labelled
"cooperate" and option B "defect". Every other word of the prompt, every setting and every match is
the same as milestone 1: each of the 250 matches here has the same id, seed and length as a match in
`runs/m1-small-models`, so the two runs are compared match by match (`comparison.md`).

- **Naming the game did not measurably change how often any model cooperated.** The changes were +1
  to +10 points, and every interval includes zero. Gemini moved the most (55% → 65%), but its
  interval runs from -7 to +26 points.
- **It made two models stricter.** Gemini answered a defection with defection more consistently
  (95% → 99%, change +5 points [+2 to +8]), and DeepSeek stopped going back to cooperating after
  retaliating (4% → 0%, change -4 points [-22 to -1]). Gemini's forgiveness fell too (2% → 0%), but
  that interval reaches zero. These are small changes to behaviour that was already rare.
- **Nothing else moved.** Exploitation of an unconditional cooperator and payoff per round stayed
  the same within their intervals.

### Conditions

- Milestone 1's conditions apply: temperature 0.7, low reasoning effort, the same caps.
- Three bots instead of five (Always Cooperate, Always Defect, Tit-for-Tat), so payoff rankings are
  not comparable with milestone 1's table. The comparison only uses matches both runs contain.
- The two arms were run hours apart on the same day. A provider changing a model in between would
  look like a framing effect; nothing suggests that happened, but it cannot be ruled out.
- 70 matches per model. A real effect smaller than about 10 points of cooperation would not show up
  at this size.
