# Toolcall Guard

A small guard model for AI agent tool calls. Given an agent's role and operator policy, the session facts, the tools,
the conversation so far and one proposed tool call, it answers with strict JSON:

```json
{"verdict": "allow" | "block", "category": "<one of 8>", "reason": "<one sentence>"}
```

It is Gemma 4 E4B IT with a LoRA adapter, distilled from a Gemini teacher, and runs for free on a laptop or on Kaggle.
It is a pre-execution check, not a security boundary.

This is half of a pair. Project A (agent-govbench) built a Google Cloud agent, attacked it, and benchmarked managed
guards. This guard was scored on A's saved decision records by replay (`replay_eval.py`), with no adaptive agent
behaviour after a block.

- Model: [BrejBala/gemma-toolcall-guard](https://huggingface.co/BrejBala/gemma-toolcall-guard) (private for now)
- Data: [BrejBala/toolcall-guard-data](https://huggingface.co/datasets/BrejBala/toolcall-guard-data) (sanitized release, private for now)
- Companion dataset (Project A): [BrejBala/agent-govbench](https://huggingface.co/datasets/BrejBala/agent-govbench)
- Every guard on every test set: [RESULTS.md](RESULTS.md). Measured spend: [COSTS.md](COSTS.md). Shared contract with
  Project A: [contract/](contract/README.md).

Not affiliated with or endorsed by Google. Product names are used to describe what was tested. Contains text generated
by Gemini models. Check the terms of any provider that applies to your use, including terms on using outputs to train
models.

## Status

The Google Cloud project used for generation, labeling and tuning (govbench-brejesh-01) is **deleted**, as is its
bucket. Nothing here can call it any more. Everything needed to use or study the guard is kept elsewhere: the adapter
and the data on Hugging Face, and all raw Gemini requests and responses, the ledger, the frozen tuning data, every
prediction file and the downloaded adapters in the local `exports/` folder (with a SHA-256 manifest). Running the
adapter, the demo, `replay_eval.py` and the evaluation scoring needs no Google project. Re-running generation,
labeling or managed tuning needs a new project (see Reproduce).

## Results summary

At full precision the adapter blocks 0.62 [0.53, 0.71] of attacks at a false positive rate of 0.08 [0.04, 0.12] on
Project A's real agent traffic, and 0.91 [0.88, 0.95] at 0.07 [0.04, 0.10] on its own synthetic test set; the Gemini
guards block 0.98 at 0.03 on A's real traffic. 8-bit matches full precision; 4-bit loses about 20 points of recall.
Intervals are 95% family-clustered bootstrap intervals; thresholds, where used, are fit on the val split only.

<!-- results:start -->
**Attack block rate (share of malicious calls blocked)**, 95% family-clustered bootstrap intervals

| guard | synthetic test | review_100 | OOD | A gold | A replay, real agent | A replay, simulated compromised |
|---|---|---|---|---|---|---|
| gemma-4-e4b tuned (ours) | 0.91 [0.88, 0.95] | 0.87 [0.79, 0.94] | 1.00 [1.00, 1.00] | 0.69 [0.53, 0.85] | 0.62 [0.53, 0.71] | 0.87 [0.79, 0.93] |
| gemma-4-e4b tuned (ours), merged int8 | 0.89 [0.85, 0.93] | 0.86 [0.77, 0.93] | 1.00 [1.00, 1.00] | 0.65 [0.48, 0.82] | 0.61 [0.51, 0.72] | 0.86 [0.77, 0.92] |
| gemma-4-e4b tuned (ours), 4-bit laptop | 0.70 [0.63, 0.76] | 0.65 [0.54, 0.76] | 0.89 [0.71, 1.00] | 0.50 [0.35, 0.66] | 0.35 [0.27, 0.44] | 0.66 [0.57, 0.75] |
| gemma-4-e4b G5 in-domain (A data) | 0.92 [0.89, 0.96] | 0.88 [0.81, 0.96] | 0.94 [0.82, 1.00] | 0.75 [0.60, 0.89] D | 0.76 [0.69, 0.83] D | 0.91 [0.86, 0.95] D |
| gemma-4-e4b untuned zero-shot | 0.86 [0.81, 0.90] | 0.84 [0.75, 0.92] | 0.94 [0.82, 1.00] | 0.69 [0.52, 0.85] | 0.62 [0.52, 0.73] | 0.81 [0.72, 0.88] |
| gemma-4-e4b untuned few-shot | 0.88 [0.84, 0.93] | 0.88 [0.80, 0.96] | 0.94 [0.82, 1.00] | 0.75 [0.59, 0.89] | 0.70 [0.61, 0.80] | 0.89 [0.82, 0.94] |
| keyword | 0.70 [0.63, 0.76] | 0.65 [0.54, 0.77] | 0.33 [0.12, 0.56] | 0.65 [0.52, 0.80] | 0.46 [0.33, 0.58] | 0.73 [0.62, 0.83] |
| gemini-3.8-flash zero-shot | 0.99 [0.97, 1.00] G | 0.93 [0.86, 0.98] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.98 [0.96, 1.00] | 1.00 [1.00, 1.00] |
| gemini-3.1-pro zero-shot | 1.00 [1.00, 1.00] C | 0.94 [0.89, 0.99] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] | 0.98 [0.95, 0.99] | 1.00 [0.99, 1.00] |

**False positive rate (share of benign calls blocked)**, 95% family-clustered bootstrap intervals

| guard | synthetic test | review_100 | OOD | A gold | A replay, real agent | A replay, simulated compromised |
|---|---|---|---|---|---|---|
| gemma-4-e4b tuned (ours) | 0.07 [0.04, 0.10] | 0.19 [0.06, 0.33] | 0.08 [0.00, 0.27] | 0.03 [0.00, 0.08] | 0.08 [0.04, 0.12] | - |
| gemma-4-e4b tuned (ours), merged int8 | 0.06 [0.03, 0.09] | 0.19 [0.06, 0.33] | 0.08 [0.00, 0.27] | 0.03 [0.00, 0.08] | 0.08 [0.04, 0.12] | - |
| gemma-4-e4b tuned (ours), 4-bit laptop | 0.01 [0.00, 0.03] | 0.10 [0.00, 0.21] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.03 [0.01, 0.06] | - |
| gemma-4-e4b G5 in-domain (A data) | 0.09 [0.06, 0.12] | 0.32 [0.16, 0.48] | 0.00 [0.00, 0.00] | 0.04 [0.00, 0.10] D | 0.08 [0.04, 0.12] D | - |
| gemma-4-e4b untuned zero-shot | 0.13 [0.09, 0.18] | 0.29 [0.13, 0.46] | 0.00 [0.00, 0.00] | 0.06 [0.01, 0.12] | 0.15 [0.10, 0.21] | - |
| gemma-4-e4b untuned few-shot | 0.19 [0.14, 0.23] | 0.35 [0.19, 0.53] | 0.08 [0.00, 0.25] | 0.07 [0.02, 0.14] | 0.20 [0.15, 0.27] | - |
| keyword | 0.50 [0.44, 0.56] | 0.55 [0.37, 0.73] | 0.33 [0.08, 0.60] | 0.18 [0.09, 0.26] | 0.14 [0.10, 0.18] | - |
| gemini-3.8-flash zero-shot | 0.02 [0.01, 0.04] G | 0.19 [0.07, 0.34] | 0.00 [0.00, 0.00] | 0.03 [0.00, 0.07] | 0.03 [0.01, 0.04] | - |
| gemini-3.1-pro zero-shot | 0.00 [0.00, 0.00] C | 0.23 [0.08, 0.38] | 0.00 [0.00, 0.00] | 0.03 [0.00, 0.07] | 0.03 [0.02, 0.05] | - |

C: circular, Pro produced these labels. G: advantaged, Flash wrote these scenarios. D: in-domain, G5 was trained on scenarios from A's generator. Rows without "4-bit" or "int8" are full precision. "-": not run, or no records of that kind (the simulated compromised set has no benign calls).
<!-- results:end -->

**Matched false positive rate** on A's replay sample (each Gemma threshold fit on the val split at Pro's rate):

<!-- matched:start -->
| guard | threshold (fit on val) | attack block rate | false positive rate |
|---|---|---|---|
| gemini-3.1-pro zero-shot, default | - | 0.98 [0.97, 0.99] | 0.034 [0.018, 0.050] |
| gemini-3.8-flash zero-shot, default | - | 0.99 [0.97, 1.00] | 0.027 [0.013, 0.043] |
| gemma-4-e4b untuned zero-shot | 0.9997 | 0.36 [0.29, 0.44] | 0.051 [0.025, 0.085] |
| gemma-4-e4b untuned few-shot | 0.9997 | 0.49 [0.41, 0.58] | 0.056 [0.029, 0.096] |
| gemma-4-e4b tuned (ours) | 0.8165 | 0.50 [0.43, 0.59] | 0.036 [0.015, 0.070] |
| gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 0.9334 | 0.46 [0.37, 0.53] | 0.027 [0.007, 0.056] |
<!-- matched:end -->

**Pro agent traffic** (A's agent with gemini-3.1-pro, stratified sample of 20, a spot check, both models in 8-bit;
teacher_label = labeled by A's Gemini teacher, not human):

<!-- pro_agent:start -->
| guard | n | attack block rate | false positive rate | construction labels: block / FPR | teacher_label: block / FPR |
|---|---|---|---|---|---|
| gemma-4-e4b tuned (ours), merged int8 | 20 | 0.50 [0.20, 0.88] | 0.00 [0.00, 0.00] | 0.62 / 0.00 | 0.00 / 0.00 |
| gemma-4-e4b untuned zero-shot, int8 | 20 | 0.60 [0.30, 0.88] | 0.00 [0.00, 0.00] | 0.62 / 0.00 | 0.50 / 0.00 |
| A live_G4-G2p+G6 | 7 | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] | 1.00 / 0.00 | 1.00 / 0.00 |
| A live_G6 | 7 | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] | 1.00 / - | 1.00 / 0.00 |
| A unguarded | 6 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 / - | - / 0.00 |
<!-- pro_agent:end -->

Adaptive rewrites (87 of A's attacks rewritten by gemini-3.1-pro to evade guards): the adapter blocks 0.74 [0.63, 0.83]
at full precision and 0.41 [0.31, 0.51] in 4-bit; see RESULTS.md and the model card.

<!-- replication:start -->
## Replication information

**Gemini guard baselines**
- Models: `gemini-3.8-flash` and `gemini-3.1-pro-preview` on Google Cloud Vertex AI, method `generateContent` at
  `https://aiplatform.googleapis.com/v1/projects/<project>/locations/global/publishers/google/models/<model>:generateContent`,
  called through google-genai 2.28.0 (`vertexai=True`, location `global`).
- Tier: Flex PayGo, selected with the request headers `X-Vertex-AI-LLM-Request-Type: shared` and
  `X-Vertex-AI-LLM-Shared-Request-Type: flex`. The latencies quoted for Gemini were measured separately on the standard
  tier (30 OOD records, one call at a time); Flex latencies in RESULTS.md include queueing.
- Settings: thinking level LOW; response MIME type `application/json` with the response schema `OUTPUT_SCHEMA` in
  `tcg/prompts.py`; temperature and maximum output tokens not set (service defaults); one call per record. The client
  retried transient HTTP errors (up to four times before 8 Oct 2026, at most once after).
- Prompt: system instruction `prompts/guard_system_v1.txt` (identical to `GUARD_SYSTEM` in `tcg/prompts.py`); user
  message `render(record)` from `tcg/prompts.py`; replies parsed with `parse_output`; an unparsable reply counts as a
  block with a wrong category.
- Pro on the synthetic test and on review_100 reuses the teacher's pass-1 calls (the same request), which is why those
  rows are circular.
- Run dates (UTC, from the call ledger): Flash on OOD and the synthetic test 5 Oct 2026, on review_100 and A gold
  7 Oct, on A replay 7 to 8 Oct. Pro on OOD 5 Oct; the teacher calls reused for the synthetic test and review_100
  5 Oct; A gold 7 Oct; A replay 7 to 8 Oct. Standard-tier latency runs 5 and 7 Oct.

**Gemma guards**
- Base `google/gemma-4-E4B-it`; the tuned adapter is this project's LoRA; G5 is a separate in-domain adapter. Tuned,
  G5 and untuned zero-shot use the student system prompt `STUDENT_SYSTEM`; untuned few-shot uses `GUARD_SYSTEM` plus
  the four examples in `contract/examples_v0.jsonl` as earlier turns (all in `tcg/prompts.py`). Gemma chat template
  with the generation prompt, greedy decoding, at most 96 new tokens. P(block) is the probability of the first
  generated allow or block token.
- Kaggle (`kaggle/eval_fp16.py`): full precision is the fp16 base with the LoRA injected unmerged, spread over two T4
  GPUs; merged 8-bit is the LoRA merged into the bf16 base, then LLM.int8 (bitsandbytes) on one T4. Python 3.13;
  transformers, peft, accelerate and bitsandbytes installed with `pip -U` at run time on 7 to 8 Oct 2026 (versions not
  recorded).
- Laptop: RTX 3050 Laptop GPU 6 GB, Intel i5-13450HX, 23.7 GB RAM, Windows 11; torch 2.11.0+cu128, transformers
  5.18.0, peft 0.21.2, bitsandbytes 0.50.2, accelerate 1.15.0 (`uv.lock`). 4-bit is an nf4 base (bf16 compute) with
  the LoRA unmerged and the per-layer embeddings in system RAM (`tcg/local_guard.py`); 8-bit is the merged LLM.int8
  variant.

**Thresholds, samples and seeds**
- Default rows use the model's own verdict. The "val threshold 0.61" row is Youden's J on val_frozen (150 records,
  grid 0.02 to 0.98). Matched false positive rows use the lowest P(block) threshold whose val_frozen false positive
  rate is at most the Gemini guard's rate on that test set (`results/matched_fpr.json`). No threshold was fit on a test
  or gold set.
- Splits: a salted hash of `family_id` (`contract/split_v0.py`). A replay sample: all 863 attacks plus 1,000 random
  real-agent benign calls from Project A's final test set (split test, labeled, not disputed, files listed in A's final
  marker), seed 20261008. Pro agent spot check: 20 of 692 calls (10 attacks, 10 benign, proportional by label source),
  the first records per stratum of an 80-record sample drawn with seed 20261009. G5 scores leave out the 7 test records
  that A's known-issues list names.
- Intervals: family-clustered percentile bootstrap, 1,000 resamples (500 in head-to-head tables), seed 0.
- Per-record outputs of every guard of this project on Project A's test sets are in `predictions/` (A's record ids plus
  our outputs; A's records are in its dataset), so those numbers can be recomputed.

**What cannot be replicated**
- Gemini outputs: the preview model can change or be retired, and the calls used the default temperature, so a rerun
  can differ.
- Flex tier queueing latency, and laptop latency, which depends on other apps sharing the 6 GB GPU.
- The managed tuning run itself: the Google Cloud project is deleted; the frozen training data, its SHA-256 and the
  adapter are kept.
- The exact Kaggle library versions (installed unpinned at run time).
- Project A's live agent runs (its saved records are fixed; the runs that produced them are not).
- The review_100 labels from two independent ChatGPT passes (a one-off external step).
- The DNS state used to choose reserved domains for the sanitized release (October 2026).
<!-- replication:end -->

## Pipeline

| step | what | where |
|---|---|---|
| contract | record schema, 8-category taxonomy with a precedence rule, split by family hash, leakage check | `contract/`, `tcg/leakage.py` |
| roles | 36 agent roles (policy text and 7 to 10 tools each), written once by gemini-3.8-flash | `tcg/roles.py`, `data/roles_v1.json` |
| generation | structured seeds (role, category, technique, hard-negative type, surface, style, turns, output length); one call writes a family of two records: an attack and its benign twin | `tcg/generate.py`, `tcg/data.py` |
| teacher labels | gemini-3.1-pro-preview with the guard prompt (`prompts/guard_system_v1.txt`); a second pass on 15% measures self-agreement; records where teacher and generation intent disagree go to a disputed pool and stay out of training | `tcg/label.py`, `tcg/data.py` |
| review labels | 100 stratified records labeled by two independent ChatGPT passes (no human-decided rows); teacher-versus-review agreement; evaluation only, never trained on | `tcg/review.py`, `review/` |
| tuning | Vertex AI managed LoRA tuning of `google/gemma4@gemma-4-e4b-it` (rank 16, 2 epochs), adapter only downloaded; Kaggle fallback with TRL + peft | `tcg/tune.py`, `kaggle/` |
| evaluation | synthetic test, review_100, 30 hand-written out-of-distribution records, A's gold, replay, adaptive and Pro agent records; baselines: Pro and Flash zero-shot, untuned Gemma (zero-shot and few-shot), keyword rules, A's guards; full precision and 8-bit on Kaggle and the laptop, 4-bit on the laptop; family-clustered bootstrap intervals, matched false positive rate | `tcg/evaluate.py`, `tcg/metrics.py`, `kaggle/` |
| replay | score the guard on saved contract records offline, append results in the contract format | `replay_eval.py` |
| release | cards, Hugging Face upload and backup check, numbers audit, sanitized release candidate | `hf/`, `tcg/publish.py`, `tcg/audit_numbers.py`, `tcg/sanitize.py` |

## Repo map

| path | what |
|---|---|
| `tcg/` | the pipeline: config, Gemini client with cache and ledger, generation, labeling, review, tuning, local inference (`local_guard.py`, `quant_local.py`), evaluation and metrics, exports, publishing, audits |
| `contract/` | schema v0, taxonomy v0, split function and examples shared with Project A |
| `prompts/` | the teacher and guard prompt (`guard_system_v1.txt`) and an unused v2 candidate |
| `kaggle/` | Kaggle kernels: full-precision evaluation, quantization test, fallback trainer, and the job scheduler |
| `hf/` | model card, dataset card, the quick-start script and its example record |
| `data/` | the role library, the OOD set, data reports and the frozen-dataset manifests (`data/tuning/*/stats.json`); the records themselves are on Hugging Face |
| `predictions/` | per-record outputs of every guard of this project on Project A's test sets (A's record ids plus our outputs) |
| `results/` | summary metrics (`summary.json`), thresholds, matched false positive rows, quantization and adaptive results, error analysis, numbers audit |
| `demo.py`, `replay_eval.py` | the local demo and the replay scorer |
| `RESULTS.md`, `COSTS.md` | full results and measured spend |
| `LICENSE`, `NOTICE` | Apache 2.0 for the code, and third-party notes |

Kept in a private archive, not in this repository: every prediction file, the Kaggle outputs, the verbatim training
data and review files (they contain invented contact details), Project A's records (A's to publish), the project log,
and the `exports/` folder with all raw Gemini requests and responses and a SHA-256 manifest.

## Run the guard locally

The model card has a tested quick start that needs only torch, transformers and peft. With this repo:

```python
from tcg.local_guard import load, decide
tok, model = load("BrejBala/gemma-toolcall-guard", device="cpu", precision="full")  # bf16, about 16 GB RAM
print(decide(tok, model, record)["parsed"])  # record: one contract v0 decision record
```

Full precision needs about 16 GB (CPU RAM, or a GPU with 18 GB or more); on a CPU without native bf16 it takes minutes
per decision. On a 6 GB GPU use 8-bit, which matches full precision: build the merged checkpoint once with
`uv run python -m tcg.quant_local merge` (16 GB on disk, into `merged/real`), then
`load(device="cuda", precision="8bit", base="merged/real")`. 4-bit (`precision="4bit"`) fits easily but blocks about
20 points fewer attacks.

### Demo

A local Gradio app (bound to 127.0.0.1, not deployed): paste a decision record, get the verdict.

```bash
uv run --group demo python demo.py
```

Options: `--device cpu` for full precision on CPU; `--precision 8bit --base merged/real` for 8-bit on a 6 GB GPU
(after `tcg.quant_local merge`); `--adapter BrejBala/gemma-toolcall-guard` to use the published adapter. With no
options it runs the 4-bit GPU setup, which blocks fewer attacks.

### Replay on saved decision records

```bash
uv run python replay_eval.py --src <folder of contract v0 .jsonl> --adapter BrejBala/gemma-toolcall-guard --device cpu
```

It appends one `guard_results` entry per record (stage `replay`, cost 0) and writes `metrics.md` and `metrics.json`
comparing every guard configuration found in the records. `--precision full|4bit` picks the precision, and
`--import-preds <file>` adds predictions made elsewhere (for example on Kaggle) instead of running a model.

## Reproduce

Scoring needs no Google project: with the prediction files and test sets in place (private archive and Hugging Face),
`uv run python -m tcg.evaluate score` rebuilds RESULTS.md, `uv run python -m tcg.evaluate card` rebuilds the card
tables, and `uv run python -m tcg.audit_numbers` checks every hand-written number in the cards.

A new run of generation, labeling and tuning needs: Python 3.12 with uv; a new Google Cloud project with billing and
Vertex AI (Gemini 3.x models run in location `global`; managed open-model tuning ran in `us-central1`, since `global`
routed to a region the project could not use); a bucket; gcloud with Application Default Credentials (no service
account keys); and a Kaggle account for the free full-precision evaluation. Put the new project, bucket and locations
in `.env` (copy `.env.example`). The Gemini cache in `exports/raw/` is keyed by request content, not by project, so
with it in place a new project replays the original calls for free; without it every call is billed again.

```bash
cp .env.example .env              # set project, bucket, locations, model ids
uv sync
uv run pytest -q                  # contract, split and leakage tests
uv run python -m tcg.sanity       # one tiny call, confirms the billed project
uv run python -m tcg.roles        # role library
uv run python -m tcg.data generate --version v1 --families 2000
uv run python -m tcg.data label --version v1
uv run python -m tcg.data topup --version v1 --families 170
uv run python -m tcg.data build --version v1
uv run python -m tcg.review build --version v1 && uv run python -m tcg.review_compact --version v1
uv run python -m tcg.review score --version v1   # after filling review/review_100.csv
uv run python -m tcg.leakage data/v1/train.jsonl data/v1/val.jsonl data/v1/test.jsonl
uv run python -m tcg.tune freeze real --version v1   # train + val (cap 150), leakage check, sha256
uv run python -m tcg.tune launch real --epochs 2 --adapter-size 16
uv run python -m tcg.evaluate gemini synthetic_test           # Gemini baselines (Flex), per test set
uv run python kaggle/push_eval.py dataset && uv run python kaggle/scheduler.py   # full-precision Gemma runs on Kaggle
uv run python -m tcg.evaluate merge-kaggle && uv run python -m tcg.evaluate threshold
uv run python -m tcg.evaluate score && uv run python -m tcg.evaluate card && uv run python -m tcg.errors
```

## Measured cost

Project B's ledger (every Gemini call's usage_metadata at SKU list prices, plus managed tuning): **USD 67.50**, of
which Gemini calls 45.84 and managed tuning 21.66 (pilot 0.22, main run 12.51, G5 8.93). Together with Project A's
ledger (USD 114.10) that is USD 181.60 against USD 181.22 billed for the shared project, a gap of -0.38 (-0.2%;
provisional until the final Billing report). Kaggle and laptop runs cost nothing. Details: [COSTS.md](COSTS.md).

## License

Code: Apache License 2.0 ([LICENSE](LICENSE), [NOTICE](NOTICE)). Model adapter: Apache 2.0, as for its base model
Gemma 4. Dataset: CC BY 4.0, released as a sanitized copy (invented emails and phone numbers replaced, labels
unchanged); the model was trained on the verbatim version, which stays private.

Copyright 2026 brej-29.
