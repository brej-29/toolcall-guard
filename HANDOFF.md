# Handoff: Toolcall Guard

For portfolio write-ups, LinkedIn posts and interviews. Every number below comes from files in this repo (RESULTS.md, COSTS.md, results/cascade.md); nothing is estimated.

## One line

A free, local guard model (Gemma 4 E4B + LoRA, distilled from a Gemini teacher) that checks one AI agent tool call before it runs, plus a cascade that pays for Gemini only when the local model is unsure, an MCP server and a static website.

## Links

| what | where |
|---|---|
| Code | https://github.com/brej-29/toolcall-guard |
| Site | https://brej-29.github.io/toolcall-guard/ |
| Model | https://huggingface.co/BrejBala/gemma-toolcall-guard |
| Data | https://huggingface.co/datasets/BrejBala/toolcall-guard-data |
| Companion (Project A) | https://huggingface.co/datasets/BrejBala/agent-govbench |

## What it does

Input: agent role and policy, session facts, tools, conversation, one proposed call. Output: `{"verdict": allow|block, "category": one of 8, "reason": one sentence}`.

## What we were trying to do

1. Distill a hosted Gemini guard into a small model that runs free on a laptop.
2. Judge it honestly on real agent traffic from Project A, not only on its own synthetic test set.
3. (This release) Make it useful: a cascade that cuts hosted cost, an MCP server, a site people can use with their own key.

## Pipeline

Structured seeds -> Gemini 3.8 Flash writes attack + benign twin per family -> Gemini 3.1 Pro labels (kept 3,329, disputed pool 1,011 never trained on) -> family-hash split 80/5/15 with leakage checks -> LoRA tuning of Gemma 4 E4B IT -> evaluation on synthetic test, OOD and Project A replay.

## Key results (Project A real traffic, 95% intervals)

| guard | attacks blocked | false positives |
|---|---|---|
| this adapter, full precision | 0.62 [0.53, 0.71] | 0.08 [0.04, 0.12] |
| untuned Gemma 4 E4B zero-shot | 0.62 [0.52, 0.73] | 0.15 [0.10, 0.21] |
| Gemini 3.8 Flash | 0.98 [0.96, 1.00] | 0.03 [0.01, 0.04] |
| Gemini 3.1 Pro | 0.98 [0.95, 0.99] | 0.03 [0.02, 0.05] |

On its own synthetic test the adapter blocks 0.91 at 0.07 false positives. 4-bit blocks only 0.35 on real traffic, so quantization costs a lot of recall. The honest message: tuning mainly cut false positives (0.15 to 0.08) rather than raising recall, and the free model is not a sole gate.

## Cascade (new in this release)

On 981 held-out real-traffic calls: cascade 0.98 [0.95, 1.00] blocked, 0.02 false positives, 69% of calls sent to Gemini, USD 2.43 vs 3.42 per 1,000 for Flash alone (about 29% cheaper). Thresholds chosen on a separate half of the families. See results/cascade.md. The saving is modest; the adapter's confident blocks were not reliable enough to trust, so only confident allows stay local.

## Problems faced (all documented in the repo history and STATE notes)

| problem | what happened |
|---|---|
| Gemini batch jobs | two 5-row batch jobs for the 3.x models in the global location failed with an internal error after about 65 minutes queued, no rows billed; switched to Flex and online calls |
| Managed tuning location | tuning in `global` failed with a permission error, regional `us-central1` worked; later fell back to Kaggle (T4) for training and evaluation |
| Kaggle quirks | input mounts at unexpected paths, TRL warmup parameter changes, LoRA targets had to be the language-model regex (short names hit the vision tower), fp16 needs fp32 LoRA weights |
| 6 GB laptop GPU | 2.8B-parameter per-layer embedding table kept on CPU, decoder in 4-bit; fit but costs recall |
| Circular and advantaged evaluation | Pro labeled the synthetic set (circular) and Flash wrote it (advantaged), so comparisons are made on Project A's traffic instead |
| Label quality | review_100 was two ChatGPT passes, not human labels; documented as such |
| Replay limits | each decision point scored alone; a live agent might retry after a block, which replay cannot see |
| Cost | total recorded USD 67.50 (COSTS.md) |
| Codex handoff | the Codex delegate hit its usage limit during the cascade work, so that part was done directly in Claude |

## What was added in this release

| item | file |
|---|---|
| Cascade logic and offline sweep | tcg/cascade.py, tests/test_cascade.py, results/cascade.md, results/cascade_flash.json |
| MCP server (stdio, 4 backends) | tcg/mcp_server.py, docs/mcp.md, tests/test_mcp.py |
| Website (playground, cascade explorer, policy suite, SEO, JSON-LD, llms.txt) | site/ |
| Pages deploy workflow | .github/workflows/pages.yml |

## Not verified

- `local` and `cascade` MCP backends were not run end to end after the MCP code was written (no GPU run).
- The Gemini call in the browser playground was not exercised with a real key.
- MCP use inside Claude Desktop, Claude Code and Cursor was not tested.
- Google and Bing search ranking cannot be guaranteed; the site has metadata, sitemap, JSON-LD and llms.txt only.

## Portfolio and LinkedIn angles

- Honest evaluation: report where the free model is weak, with intervals, and avoid circular benchmarks.
- Cost engineering: measured cascade, 29% cheaper at the same measured quality, with the caveats.
- Distillation end to end: data generation, teacher labeling, leakage checks, LoRA, quantization trade-offs.
- Shipping: MCP server plus a no-backend site where users bring their own key.

Draft post hook (edit freely): "I tuned a free guard model for AI agents and it blocks only 62% of real attacks. Here is why I shipped it anyway, and what I measured when I let it call Gemini only when unsure."

## Reproduce

```bash
uv run python -m tcg.cascade --records <a_replay_eval.jsonl>   # records come from Project A's dataset
python site/build_data.py                                       # refresh site/data.json
uv run --no-project --with pytest python -m pytest tests -q
```
