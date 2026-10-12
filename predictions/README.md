# Predictions on Project A's test records

One JSON line per record and guard: `predictions/<set>/<guard>.jsonl`. Only this project's guards; Project A's own
guard results are A's to publish. Each row holds Project A's record `id` and our output, never A's record text (the
records are in A's companion dataset, BrejBala/agent-govbench).

Fields: `id`; `pred` (`verdict`, `category`, `reason`, or null when the reply did not parse, which scoring counts as a
block); `verdict_prob` (probability of the first allow or block token, Gemma guards only); `latency_ms`; `cost_usd` (the
standard on-demand price for Gemini, 0 for local guards); `tokens` (prompt and output); `precision` and `hardware`
where recorded; `raw` only when the reply did not parse.

Sets: `a_gold` (A's gold slice, 120), `a_replay` (all 863 attacks and 1,000 random real-agent benign calls from A's
final test set), `a_pro_agent` (the 20-record spot check), `a_adaptive` (A's 87 adaptive rewrites). The G5 4-bit file
on `a_replay` is partial (1,403 of 1,863 records). Text fields carry Project A's release replacements, so domains match
A's public data. `index.json` lists every file and its row count. Settings and seeds: "Replication information" in the
main README.
