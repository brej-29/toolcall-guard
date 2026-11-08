# Cascade results

Generated from `results/cascade_flash.json` by `uv run python -m tcg.cascade --records <a_replay_eval.jsonl>`. Replay on Project A's real agent traffic, report half only (981 calls, families split by SHA-256 parity; thresholds were chosen on the other half).

| guard | attacks blocked | false positives | calls sent to Gemini | USD per 1,000 |
|---|---|---|---|---|
| adapter only | 0.72 [0.59, 0.83] | 0.07 [0.03, 0.13] | 0% | 0.00 |
| Gemini 3.8 Flash only | 0.98 [0.95, 1.00] | 0.03 [0.01, 0.05] | 100% | 3.42 |
| cascade (local first, Flash when unsure) | 0.98 [0.95, 1.00] | 0.02 [0.01, 0.03] | 69% | 2.43 |

**What this says.** The cascade matches Gemini 3.8 Flash on this half and costs about 29% less, but about 69% of calls still go to Gemini. The adapter's confidence is only a modest saving signal: its confident blocks are not reliable enough to trust (the selected rule never accepts a local block), so only confident allows stay local. The lower false positive rate than Flash alone is inside the intervals; do not read it as an improvement.

**Method and limits.** Intervals are family-clustered bootstrap. Selection rule: lowest escalation rate keeping at least 95% of the hosted guard's (block rate minus FPR) on the fit half. The adapter row here is full precision on a half of the families, so it differs from the headline 0.62 on all records. Replay is per decision point. Some labels on A's traffic are teacher labels. Local inference is counted as cost 0. The full operating curve is in `results/cascade_flash.json`.
