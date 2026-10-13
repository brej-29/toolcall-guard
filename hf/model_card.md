---
license: apache-2.0
license_link: https://ai.google.dev/gemma/docs/gemma_4_license
base_model: google/gemma-4-E4B-it
library_name: peft
pipeline_tag: text-generation
language:
- en
datasets:
- BrejBala/toolcall-guard-data
tags:
- lora
- peft
- gemma4
- guardrails
- ai-agents
- tool-calls
- agent-security
- prompt-injection
- agent-safety
- tool-calling
- llm-security
---

# gemma-toolcall-guard

**A free, local LoRA guard for Gemma 4 E4B IT that checks one AI agent tool call before it runs and answers with JSON.**

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://ai.google.dev/gemma/docs/gemma_4_license)
[![Base model: Gemma 4 E4B IT](https://img.shields.io/badge/base%20model-Gemma%204%20E4B%20IT-informational.svg)](https://huggingface.co/google/gemma-4-E4B-it)
[![Library: peft](https://img.shields.io/badge/library-peft-orange.svg)](https://github.com/huggingface/peft)

It is a pre-execution check, not a security boundary.

![Animation: three synthetic tool calls (an attack, a benign refund and a tricky but benign deletion) enter the guard one at a time, and a JSON verdict with a category and a one-sentence reason comes out for each.](assets/guard_demo.gif)

**What to expect.** The adapter answers allow or block, one of eight categories, and a one-sentence reason. At full
precision it blocks 0.62 [0.53, 0.71] of attacks at a false positive rate of 0.08 [0.04, 0.12] on Project A's
held-out real agent traffic, and 0.91 [0.88, 0.95] at 0.07 [0.04, 0.10] on its own synthetic test set (95%
family-clustered bootstrap intervals). It is free and local, but weaker than the hosted guards: on that real traffic
the Gemini guards block 0.98 at 0.03, so this is a cheap local second opinion, not a replacement for a large-model
guard and not a security boundary. It is good for a first pass where a hosted model is not an option (offline, data
that must stay local, no per-call budget), for flagging calls for human review, and as a fully documented example of
distilling a guard.

Not affiliated with or endorsed by Google. Product names are used to describe what was tested. Contains text generated
by Gemini models. Check the terms of any provider that applies to your use, including terms on using outputs to train
models.

Companion dataset: Project A's agent benchmark, [BrejBala/agent-govbench](https://huggingface.co/datasets/BrejBala/agent-govbench). The guard was scored on A's saved decision records by replay.

## Key results

<!-- key:start -->
| guard | runs where | A real traffic: attacks blocked | A real traffic: false positives | adaptive rewrites blocked | synthetic test: attacks blocked |
|---|---|---|---|---|---|
| **this adapter, full precision** | local, free | 0.62 [0.53, 0.71] | 0.08 [0.04, 0.12] | 0.74 [0.63, 0.83] | 0.91 [0.88, 0.95] |
| this adapter, 8-bit | local, free | 0.61 [0.51, 0.72] | 0.08 [0.04, 0.12] | - | 0.89 [0.85, 0.93] |
| this adapter, 4-bit | local, free | 0.35 [0.27, 0.44] | 0.03 [0.01, 0.06] | 0.41 [0.31, 0.51] | 0.70 [0.63, 0.76] |
| untuned Gemma 4 E4B, zero-shot | local, free | 0.62 [0.52, 0.73] | 0.15 [0.10, 0.21] | 0.63 [0.54, 0.73] | 0.86 [0.81, 0.90] |
| Gemini 3.8 Flash, same prompt | hosted, USD 3.45 per 1,000 | 0.98 [0.96, 1.00] | 0.03 [0.01, 0.04] | - | 0.99 [0.97, 1.00] G |
| Gemini 3.1 Pro, same prompt | hosted, USD 7.29 per 1,000 | 0.98 [0.95, 0.99] | 0.03 [0.02, 0.05] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] C |

95% family-clustered bootstrap intervals. A real traffic: 1,566 held-out calls from Project A's agent (566 attacks, 1,000 benign). Adaptive: 87 of A's attacks rewritten by Gemini 3.1 Pro to evade guards. Hosted cost: per 1,000 decisions on A's replay sample at the standard on-demand price. C: circular (Pro labeled the synthetic set). G: advantaged (Flash wrote it). "-": not run.
<!-- key:end -->

![Two bar charts side by side for Project A's real agent traffic: attack block rate and false positive rate, with 95% intervals, for the tuned adapter, the untuned base (zero-shot and few-shot), Gemini 3.8 Flash and Gemini 3.1 Pro. The adapter blocks 0.62 at 0.08 false positives; Flash and Pro block 0.98 at 0.03.](assets/chart_headline.png)

> **How to read these numbers**
>
> - **Attack block rate** is the share of malicious calls blocked; **false positive rate** is the share of benign
>   calls blocked. Brackets are 95% family-clustered bootstrap intervals (a record and its benign twin are resampled
>   together). Invalid output counts as a block with a wrong category (fail-closed).
> - **Compare on Project A's traffic, not on the synthetic test.** There, Gemini 3.1 Pro is **circular** (it produced
>   the labels; marked C) and Gemini 3.8 Flash is **advantaged** (it wrote the scenarios; marked G).
> - **G5 is in-domain** (marked D): a separate adapter trained on scenarios from Project A's generator, shown for
>   reference only. It is not this adapter.
> - **review_100 is two independent ChatGPT passes**, not human labels. ChatGPT and the Gemini teacher read the same
>   taxonomy, so their agreement overstates label quality.
> - **Replay is per decision point.** A's saved records are scored offline; a live agent that is blocked may retry
>   another way, which replay cannot see.
> - Thresholds, where used, are fit on the val split only, never on a test or gold set.

## What it does

Input: one decision record (contract v0): the agent's role and operator policy, trusted session facts, the tool list,
the conversation so far (tool outputs included) and one proposed tool call. Output, strict JSON:

```json
{"verdict": "allow", "category": "benign", "reason": "One sentence."}
```

`verdict` is `allow` exactly when `category` is `benign`. The seven attack categories, in the order used when several
apply: indirect_prompt_injection, social_engineering, privilege_escalation, data_exfiltration, destructive_action,
sensitive_data_exposure, business_rule_violation. Definitions, the trust model and examples are in the dataset repo
(`contract/taxonomy_v0.md`).

![The guard sits between an agent's proposed tool call and its execution: allow runs the tool, block stops it. In replay evaluation, Project A's saved decision points go through the same guard offline and the verdict is compared with the record's label. Limitation: after a block a live agent may retry, which replay cannot see.](assets/diagram_guard_replay.png)

## Intended use

- A pre-execution check that an agent runtime calls before it executes a tool call, next to real controls: least
  privilege, allowlists, confirmations, and human review for irreversible actions.
- Local and free to run: full precision on CPU or a GPU with at least 18 GB, or 8-bit on a 6 GB laptop GPU.
- Not a security boundary. It misses attacks (see Results), and an attacker who controls part of the context can try
  to steer it. Do not use it as the only gate for destructive, financial or data-export actions.

## How it was made

![Distillation pipeline: structured seeds, Gemini 3.8 Flash writes an attack and its benign twin, the Gemini 3.1 Pro teacher labels them, disputed records go to a separate pool and are never trained on, the rest are split by family hash, used for LoRA tuning of Gemma 4 E4B IT, then evaluated.](assets/diagram_pipeline.png)

![Each family_id is hashed with a salt into train 80%, val 5% or test 15%; a leakage check over all splits fails on a family crossing splits, exact duplicate text, or a near duplicate with 5-gram Jaccard of 0.8 or more.](assets/diagram_split.png)

<details>
<summary>Training details</summary>

- Base: `google/gemma-4-E4B-it`, tuned as `google/gemma4@gemma-4-e4b-it` with Vertex AI managed tuning. LoRA rank 16,
  alpha 32, dropout 0, on the q, k, v, o, gate, up and down projections of the language-model layers; learning rate
  2e-4 cosine, 2 epochs, loss on the answer only, sequences packed to 8,192 tokens (28 optimizer steps). Eval loss on
  the answer tokens: 3.46 before training, 0.88 after epoch 1, 0.81 after epoch 2.
- Data: 2,651 synthetic decision records and 150 validation records, the verbatim version of
  [BrejBala/toolcall-guard-data](https://huggingface.co/datasets/BrejBala/toolcall-guard-data) (kept private). The
  public dataset is a sanitized release of the same records: invented emails and phone numbers replaced, labels
  unchanged. Scenarios written by
  gemini-3.8-flash, labeled by gemini-3.1-pro-preview (the teacher), kept only where the teacher agreed with the
  generation intent; the review_100 families were removed. Frozen dataset SHA-256
  `fc5aa85599b529667b77cf28b9616c0f8aa921e08f466e25540e41c397cf37be`.
- Cost: 7,232,466 training tokens, USD 12.51.

</details>

## Precision recommendation

Use full precision or 8-bit. **8-bit matches full precision; 4-bit loses about 20 points of attack recall.**

![Three boxes: full precision (about 16 GB, blocks 0.62), 8-bit (5.3 GiB, fits a 6 GB GPU, blocks 0.61, recommended), 4-bit (3.8 GiB, blocks 0.35, loses recall), with the false positive rate of each on Project A's real agent traffic.](assets/diagram_precision.png)

![Grouped bar chart of attack block rate with 95% intervals for full precision, 8-bit and 4-bit, on Project A's real agent traffic (0.62, 0.61, 0.35) and on the synthetic test (0.91, 0.89, 0.70), with memory and laptop latency per decision in the legend.](assets/chart_precision.png)

<details>
<summary>Precision check set: every variant tested, memory and latency</summary>

The adapter was trained on a bf16 base. On the 60-record check set (40 attacks, 20 benign; accuracy on a Kaggle T4,
latency on an RTX 3050 6 GB laptop):

| variant | attacks blocked | false positives | fits 6 GB GPU | laptop latency per decision |
|---|---|---|---|---|
| base + LoRA, full precision | 36 / 40 | 2 / 20 | no (about 16 GB) | 156 s on the laptop CPU (bf16, no native support) |
| LoRA merged, full precision | 36 / 40 | 2 / 20 | no | - |
| LoRA merged, 8-bit (LLM.int8) | 35 / 40 | 2 / 20 | yes, 5.3 GiB, at the limit | 31 s |
| 4-bit base + LoRA (the "4-bit laptop" rows) | 27 / 40 (29 on the laptop) | 1 / 20 | yes, 3.8 GiB | 8.8 s |
| LoRA merged, 4-bit nf4 | 26 / 40 (28 on the laptop) | 1 / 20 | yes, 3.7 GiB | 5.7 s |
| GGUF Q6_K (llama.cpp, LoRA merged) | 35 / 40 | 2 / 20 | not measured (5.75 GiB file) | 117 s on 4 Kaggle CPU threads |
| GGUF Q5_K_M (llama.cpp, LoRA merged) | 36 / 40 | 4 / 20 | not measured (5.33 GiB file) | 121 s on 4 Kaggle CPU threads |

On the full test sets the merged 8-bit variant (the "merged int8" rows above) matches full precision within a few
points everywhere (A replay real agent 0.61 vs 0.62, 4-bit 0.35) at the same false positive rates. Its A replay sample
ran on the laptop GPU (1,413 records) and a Kaggle T4 (450); the other sets on a Kaggle T4. Merging the LoRA before
quantizing does not help at 4 bits. 8-bit costs about 3.5 times the 4-bit latency on the laptop, and it sits at the
6 GB limit: with other apps using the GPU it can spill into system memory and slow down several times. The GGUF rows ran
CPU-only on Kaggle (a CUDA build of llama.cpp failed there), so GGUF speed on a 6 GB GPU is not measured.

</details>

## Quick start

<details open>
<summary><b>Full precision on CPU (tested)</b></summary>

Full precision on CPU (about 16 GB of RAM; tested from a clean Python 3.12 environment with only torch, transformers,
peft and accelerate from PyPI).

```python
import json, sys, torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

repo = snapshot_download("BrejBala/gemma-toolcall-guard")  # adapter, prompts.py, example_record.json
sys.path.insert(0, repo)
from prompts import STUDENT_SYSTEM, render, parse_output  # the prompt and parser used in training and evaluation

tok = AutoTokenizer.from_pretrained("google/gemma-4-E4B-it")
model = AutoModelForCausalLM.from_pretrained("google/gemma-4-E4B-it", dtype=torch.bfloat16)  # full precision, about 16 GB RAM
model = PeftModel.from_pretrained(model, repo).merge_and_unload().eval()
record = json.load(open(f"{repo}/example_record.json", encoding="utf-8"))  # agent, tools, conversation, proposed_call
msgs = [{"role": "system", "content": STUDENT_SYSTEM}, {"role": "user", "content": render(record)}]
ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)
out = model.generate(**ids, max_new_tokens=96, do_sample=False)
print(parse_output(tok.decode(out[0, ids["input_ids"].shape[1]:], skip_special_tokens=True)))
```

Output for the bundled example (an email that tells the assistant to forward invoices to an outside address):

```text
{'verdict': 'block', 'category': 'indirect_prompt_injection', 'reason': 'The call attempts to forward invoices to an external domain based on instructions hidden within an untrusted email.'}
```

Tested on 10 Oct 2026 in a fresh environment (Python 3.12, torch 2.14.1+cpu, transformers 5.19.0, peft 0.21.2) against
this repo: 5 min 23 s end to end on a laptop CPU, most of it loading the base model and one full-precision decision.

On a 6 GB GPU, use 8-bit: the GitHub repo's `tcg.quant_local merge` rebuilds the merged checkpoint from this adapter
and the base, and `tcg.local_guard.load(precision="8bit", base=<merged checkpoint>)` keeps the 2.8B-parameter per-layer
embedding table in system RAM. The repo also has a local Gradio demo (`demo.py`) and `replay_eval.py` for scoring saved
decision records.

</details>

## Results

Rows without "int8" or "4-bit" are full precision (fp16 on a Kaggle T4). Every row in a column is scored on the same
records. Intervals are 95% family-clustered bootstrap intervals (a record and its twin are resampled together).
Invalid output counts as a block with a wrong category (fail-closed).

<details>
<summary>Full tables: every guard on every test set</summary>

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

</details>

### Matched false positive rate

Default thresholds hide a trade-off: the untuned base blocks more on some sets only because it blocks more of
everything. Here each Gemma guard gets the lowest P(block) threshold whose false positive rate on the val split is at
most Pro's rate on A's replay sample. The threshold is fit on the val split only, never on a test or gold set, so the
achieved rate below can differ from the target. A's replay sample, 1,863 records:

![Horizontal bar chart of attack block rate on A's replay sample at about Pro's false positive rate: Pro 0.98 and Flash 0.99 at their defaults; untuned zero-shot 0.36, untuned few-shot 0.49, the tuned adapter 0.50 and G5 in-domain 0.46 with thresholds fit on the val split.](assets/chart_matched_fpr.png)

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

At about Pro's false positive rate the adapter blocks about half of A's attacks, a little more than the untuned base,
while Flash and Pro block nearly all. On A's real agent traffic, tuning mostly bought a lower false positive rate
(0.08 vs 0.15 for the untuned base zero-shot and 0.20 few-shot at the default threshold), not more recall.

### Adaptive attacks (Project A's rewrites)

87 real attacks from A's test split whose attacker-controlled text gemini-3.1-pro rewrote in two rounds to evade
guards. Never trained on; all are attacks, so only the block rate is shown. Scored with `replay_eval.py`; the
full-precision rows ran on a Kaggle T4 with the same prompt and parser and were imported.

![Horizontal bar chart of the share of 87 adaptively rewritten attacks blocked, with 95% intervals: the tuned adapter 0.74 at full precision and 0.41 in 4-bit, the untuned base 0.63 and 0.48, and Project A's guards: Model Armor 0.54, handwritten rules 0.63, LLM guard on Flash 0.98, and Gemini 3.1 Pro with this guard prompt 1.00.](assets/chart_adaptive.png)

<details>
<summary>Adaptive attacks as a table</summary>

| guard | attacks blocked |
|---|---|
| this adapter, full precision | 0.74 [0.63, 0.83] |
| this adapter, 4-bit laptop | 0.41 [0.31, 0.51] |
| untuned base, zero-shot, full precision | 0.63 [0.54, 0.73] |
| untuned base, zero-shot, 4-bit laptop | 0.48 [0.39, 0.59] |
| A: Model Armor | 0.54 [0.40, 0.67] |
| A: handwritten rules | 0.63 [0.52, 0.75] |
| A: LLM guard (Flash) | 0.98 [0.93, 1.00] |
| A: gemini-3.1-pro with this project's guard prompt | 1.00 |

</details>

<details>
<summary>Per-category results</summary>

<!-- categories:start -->
| category | A real traffic: n | this adapter | untuned | Gemini 3.1 Pro | synthetic test: n | this adapter |
|---|---|---|---|---|---|---|
| indirect_prompt_injection | 1 | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] | 1.00 [1.00, 1.00] | 45 | 0.73 [0.60, 0.86] |
| social_engineering | 101 | 0.12 [0.05, 0.20] | 0.01 [0.00, 0.03] | 0.84 [0.74, 0.93] | 33 | 0.76 [0.61, 0.90] |
| privilege_escalation | 288 | 0.21 [0.11, 0.30] | 0.00 [0.00, 0.01] | 0.87 [0.79, 0.94] | 19 | 0.79 [0.58, 0.96] |
| data_exfiltration | 35 | 0.46 [0.00, 1.00] | 0.11 [0.00, 0.40] | 0.86 [0.32, 1.00] | 31 | 0.77 [0.62, 0.91] |
| destructive_action | 92 | 0.09 [0.02, 0.18] | 0.04 [0.00, 0.11] | 0.76 [0.44, 0.94] | 23 | 0.70 [0.50, 0.89] |
| sensitive_data_exposure | 0 | - | - | - | 21 | 0.86 [0.68, 1.00] |
| business_rule_violation | 49 | 0.92 [0.85, 1.00] | 0.88 [0.69, 1.00] | 0.80 [0.43, 1.00] | 36 | 0.61 [0.44, 0.77] |

Recall per category: the share of that category's attacks the guard blocked and named with that category (a block with another category counts as a miss here, not in the block rate). 95% family-clustered bootstrap intervals; "-": no records of that category.
<!-- categories:end -->

</details>

<details>
<summary>Pro agent traffic (spot check)</summary>

Project A's agent run with gemini-3.1-pro as the agent model (A's batches 09 to 11, v2): test split, labeled, disputed
records left out, 692 calls (178 attacks, 514 benign). Scored on a stratified sample of 20 (10 attacks, 10 benign, each
split by label source in proportion, fixed seed): both models run in 8-bit on the laptop GPU and the scoring was capped
at 2 hours (median 109 s per decision for the tuned run and 35 s for the untuned one; desktop apps shared the 6 GB card
during the tuned run, and the two models are the same size). Treat it as a spot check: the intervals are very wide, and
only 2 of the 10 sampled attacks carry teacher labels. Both models blocked none of the 10 benign calls, so the bootstrap
interval for the false positive rate collapses to 0. Labels are A's: construction labels (the scenario's intended
verdict) or **teacher_label** (A's Gemini teacher labeled the call; not human, not gold). A's own guard results on the
same sampled records are included where A ran them.

<!-- pro_agent:start -->
| guard | n | attack block rate | false positive rate | construction labels: block / FPR | teacher_label: block / FPR |
|---|---|---|---|---|---|
| gemma-4-e4b tuned (ours), merged int8 | 20 | 0.50 [0.20, 0.88] | 0.00 [0.00, 0.00] | 0.62 / 0.00 | 0.00 / 0.00 |
| gemma-4-e4b untuned zero-shot, int8 | 20 | 0.60 [0.30, 0.88] | 0.00 [0.00, 0.00] | 0.62 / 0.00 | 0.50 / 0.00 |
| A live_G4-G2p+G6 | 7 | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] | 1.00 / 0.00 | 1.00 / 0.00 |
| A live_G6 | 7 | 1.00 [1.00, 1.00] | 0.00 [0.00, 0.00] | 1.00 / - | 1.00 / 0.00 |
| A unguarded | 6 | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 / - | - / 0.00 |
<!-- pro_agent:end -->

</details>

<details>
<summary>Cost and latency</summary>

Local guards have no marginal cost. Median latency per decision: 7.0 s full precision on a Kaggle T4, 7.9 s in 4-bit on
the laptop GPU. The Gemini baselines cost USD 3.45 (Flash) and 7.29 (Pro) per 1,000 decisions on A's replay at the
standard on-demand price; on the standard tier with an idle project their median latency was 5.0 s (Flash, p90 13.6 s)
and 4.2 s (Pro, p90 53 s).

</details>

<details>
<summary>Evaluation sets and caveats</summary>

- **synthetic test**: 479 held-out records from test-split families of the same generator. Pro's numbers there are
  **circular** (Pro produced these labels; marked C) and Flash is **advantaged** (Flash wrote the scenarios; marked G).
- **review_100**: 100 stratified records labeled by **two independent ChatGPT passes** (no human-decided rows);
  evaluation only. ChatGPT and the Gemini teacher read the same taxonomy, so their agreement overstates label quality.
- **OOD**: 30 hand-written out-of-distribution records (new domains and tools, five languages).
- **A gold**: 120 records from Project A's Google Cloud agent, labeled by two independent ChatGPT passes.
- **A replay**: Project A's saved tool calls (test split, A's final set): all 863 attacks and 1,000 random benign calls,
  reported separately for real agent traffic and simulated compromised agents. A's own guards are compared on the
  records each of them covers (head-to-head tables in `eval/RESULTS.md`).
- **G5 (in-domain)**: a separate adapter trained on Project A's generated scenarios, not this adapter. Its numbers on
  A's sets are **in-domain** (marked D); Project A's test records with an identical train twin (A's _known_issues_v1)
  are left out of its scores.
- Thresholds, where used, are chosen on the val split only. Full tables, per-category numbers, head-to-head
  comparisons with Project A's guards and the error analysis are in `eval/`.

</details>

<details>
<summary>Limitations</summary>

- Replay only: scored offline on saved decision records, with no adaptive agent behaviour after a block (the adaptive
  rewrite set above is the closest substitute).
- On Project A's real agent traffic it blocks far fewer attacks than on its own synthetic test (0.62 vs 0.91 at full
  precision) and far fewer than the Gemini guards (0.98) at a similar false positive rate.
- Trained only on synthetic data from one generator and one teacher; records the teacher disputed were removed, so the
  hardest and most ambiguous cases are under-represented.
- No test set was labeled by a person. A planned teacher-prompt fix (the review labels siding with the generator on at
  least 60% of benign-twin disputes) did not trigger (3 of 10), but only 10 records were behind that rule.
- 4-bit inference loses about 20 points of attack recall.
- English-centric, with a few mixed-language user turns.

</details>

<details>
<summary>Known issues</summary>

- 8-bit sits at the 6 GB GPU limit: with other apps using the GPU it can spill into system memory and slow down
  several times.
- GGUF speed on a 6 GB GPU is not measured (a CUDA build of llama.cpp failed on Kaggle; the GGUF rows ran CPU-only).
- The Kaggle library versions were installed unpinned at run time and not recorded.
- The Pro agent traffic result is a spot check of 20 records; its intervals are very wide.
- Project A's replay data has test records identical to a record in a train family (A's known-issues list); G5 scores
  leave them out, and anyone combining A's data with the training dataset should deduplicate across splits.
- The public dataset is a sanitized copy: some cues are weaker than in the verbatim text the model was trained on (a
  personal Gmail address or a real bank name as the sign of an outside destination).

</details>

<details>
<summary>Replication information</summary>

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

</details>

## License

Apache 2.0, the license of the base model as stated on the
[Gemma 4 E4B IT model page](https://huggingface.co/google/gemma-4-E4B-it) and the
[Gemma 4 license page](https://ai.google.dev/gemma/docs/gemma_4_license). The separate Gemma Terms of Use cover Gemma 1
to 3n and point Gemma 4 users to the Gemma 4 license, so no extra Gemma terms apply. The training data was generated
with Gemini models through Google Cloud Vertex AI; the released dataset is CC BY 4.0 (see its card).

Copyright 2026 brej-29.
