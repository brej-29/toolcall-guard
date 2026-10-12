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
