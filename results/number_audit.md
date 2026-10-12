# Numbers audit

83 hand-written numbers checked against their source files; 0 failed. Generated tables (RESULTS.md, and the results and pro_agent blocks in the model card and README) come straight from the prediction files and are checked by regenerating them (git diff must be empty).

| doc | phrase | source | ok |
|---|---|---|---|
| card | Data: 2,651 synthetic decision records and 150 validation records | data/tuning/real/stats.json | PASS |
| card | SHA-256 `fc5aa85599b529667b77cf28b9616c0f8aa921e08f466e25540e41c397cf37be` | data/tuning/real/stats.json | PASS |
| card | USD 12.51 | exports/ledger.jsonl (tuning, real) | PASS |
| card | Cost: 7,232,466 training tokens, USD 12.51 | exports/ledger.jsonl (real tuning job, training_tokens) | PASS |
| card | Eval loss on the answer tokens: 3.46 before training, 0.88 after epoch 1, 0.81 after epoch 2 | adapters/real/runs tensorboard eval/loss 3.464, 0.8792, 0.8053 | PASS |
| card | (28 optimizer steps) | adapters/real/runs tensorboard, last train step 28 | PASS |
| card | **synthetic test**: 479 held-out records | data/v1/test.jsonl | PASS |
| card | **A gold**: 120 records | data/a_gold.jsonl | PASS |
| card | all 863 attacks and 1,000 random benign calls | data/a_replay_eval.jsonl | PASS |
| card | **OOD**: 30 hand-written | data/ood/ood_v1.jsonl | PASS |
| card | matched FPR prose: the adapter blocks about half (0.45 to 0.55), a little more than the untuned base, Gemini nearly all | RESULTS.md a_replay matched FPR | PASS |
| card | (0.08 vs 0.15 for the untuned base zero-shot and 0.20 few-shot | results/summary.json a_replay real_agent | PASS |
| card | blocks 0.62 [0.53, 0.71] of attacks at a false positive rate of 0.08 [0.04, 0.12] on Project A's | results/summary.json a_replay real_agent | PASS |
| card | 0.91 [0.88, 0.95] at 0.07 [0.04, 0.10] on its own synthetic test set | results/summary.json synthetic_test | PASS |
| readme | blocks 0.62 [0.53, 0.71] of attacks at a false positive rate of 0.08 [0.04, 0.12] on Project A's | results/summary.json a_replay real_agent | PASS |
| readme | 0.91 [0.88, 0.95] at 0.07 [0.04, 0.10] on its own synthetic test set | results/summary.json synthetic_test | PASS |
| card | the Gemini guards block 0.98 at 0.03 | results/summary.json a_replay real_agent | PASS |
| readme | guards block 0.98 at 0.03 on A's real traffic | results/summary.json a_replay real_agent | PASS |
| card | / this adapter, full precision / 0.74 [0.63, 0.83] / | results/adaptive/metrics.json tcg_tuned_fp16_kaggle | PASS |
| card | / this adapter, 4-bit laptop / 0.41 [0.31, 0.51] / | results/adaptive/metrics.json tcg_tuned_4bit_laptop | PASS |
| card | / untuned base, zero-shot, full precision / 0.63 [0.54, 0.73] / | results/adaptive/metrics.json tcg_untuned_zs_fp16_kaggle | PASS |
| card | / untuned base, zero-shot, 4-bit laptop / 0.48 [0.39, 0.59] / | results/adaptive/metrics.json tcg_untuned_zs_4bit_laptop | PASS |
| card | / A: Model Armor / 0.54 [0.40, 0.67] / | results/adaptive/metrics.json model_armor_direct | PASS |
| card | / A: handwritten rules / 0.63 [0.52, 0.75] / | results/adaptive/metrics.json handwritten_rules_g2prime | PASS |
| card | / A: LLM guard (Flash) / 0.98 [0.93, 1.00] / | results/adaptive/metrics.json llm_guard_flash | PASS |
| card | / A: gemini-3.1-pro with this project's guard prompt / 1.00 / | results/adaptive/metrics.json | PASS |
| card | 87 real attacks from A's test split | data/a/adaptive/adaptive_rewrite_v1.jsonl | PASS |
| card | 692 calls (178 attacks, 514 benign) | data/a/pro_agent (test, labeled, not disputed) | PASS |
| card | stratified sample of 20 (10 attacks, 10 benign | data/a_pro_agent_eval.jsonl | PASS |
| card | median 109 s per decision for the tuned run and 35 s for the untuned one | results/preds/a_pro_agent latency | PASS |
| card | only 2 of the 10 sampled attacks carry teacher labels | data/a_pro_agent_eval.jsonl label_stratum | PASS |
| card | none of the 10 benign calls | data/a_pro_agent_eval.jsonl | PASS |
| card | both Pro agent false positive rates are 0 | results/summary.json a_pro_agent | PASS |
| card | / base + LoRA, full precision / 36 / 40 / 2 / 20 / no (about 16 GB) / 156 s on the laptop CPU | kaggle quant + quant_local merged_full cpu | PASS |
| card | / LoRA merged, full precision / 36 / 40 / 2 / 20 / | kaggle quant merged_fp16 | PASS |
| card | / LoRA merged, 8-bit (LLM.int8) / 35 / 40 / 2 / 20 / yes, 5.3 GiB, at the limit / 31 s / | kaggle quant + quant_local merged_int8 cuda | PASS |
| card | / 4-bit base + LoRA (the "4-bit laptop" rows) / 27 / 40 (29 on the laptop) / 1 / 20 / yes, 3.8 GiB / 8.8 s / | kaggle + laptop nf4_base+lora | PASS |
| card | / LoRA merged, 4-bit nf4 / 26 / 40 (28 on the laptop) / 1 / 20 / yes, 3.7 GiB / 5.7 s / | kaggle + laptop merged_nf4 (retime) | PASS |
| card | / GGUF Q6_K (llama.cpp, LoRA merged) / 35 / 40 / 2 / 20 / not measured (5.75 GiB file) / 117 s on 4 Kaggle CPU threads / | gguf-cpu summary | PASS |
| card | / GGUF Q5_K_M (llama.cpp, LoRA merged) / 36 / 40 / 4 / 20 / not measured (5.33 GiB file) / 121 s on 4 Kaggle CPU threads / | gguf-cpu summary | PASS |
| card | A replay real agent 0.61 vs 0.62, 4-bit 0.35 | results/summary.json a_replay real_agent | PASS |
| card | laptop GPU (1,413 records) and a Kaggle T4 (450) | int8 a_replay hardware field | PASS |
| card | 7.0 s full precision on a Kaggle T4, 7.9 s in 4-bit | results/summary.json a_replay latency | PASS |
| card | USD 3.45 (Flash) and 7.29 (Pro) | results/summary.json a_replay cost | PASS |
| card | 5.0 s (Flash, p90 13.6 s) and 4.2 s (Pro, p90 53 s) | results/latency/*.json | PASS |
| card | (0.62 vs 0.91 at full precision) | results/summary.json | PASS |
| card | Gemini guards (0.98) | results/summary.json a_replay real_agent | PASS |
| card | did not trigger (3 of 10), but only 10 records | data/v1/review_agreement.json | PASS |
| data_card | / `data/train.jsonl` / 2,660 / 1,534 benign; | data/v1/train.jsonl | PASS |
| data_card | 225 indirect prompt injection, 190 social engineering, 171 business rule violation, 143 privilege escalation, 141 data exfiltration, 131 destructive action, 125 sensitive data exposure | data/v1/train.jsonl categories | PASS |
| data_card | / `data/val.jsonl` / 190 / | data/v1/val.jsonl | PASS |
| data_card | / `data/val_frozen_150.jsonl` / 150 / | data/v1/val_frozen.jsonl | PASS |
| data_card | / `data/test.jsonl` / 479 / 271 benign / | data/v1/test.jsonl | PASS |
| data_card | / `data/disputed.jsonl` / 1,011 / | data/v1/disputed.jsonl | PASS |
| data_card | / `data/review_100.jsonl` / 100 / | data/v1/review_eval.jsonl | PASS |
| data_card | / `data/ood_30.jsonl` / 30 / | data/ood/ood_v1.jsonl | PASS |
| data_card | 2,170 families in train, val, test and disputed combined | data/v1 family_id | PASS |
| data_card | Benign share of kept records: 57% | data/v1 train+val+test | PASS |
| data_card | Teacher self-agreement on 586 double-labeled records: verdict 97.3%, category 92.2% | data/v1/report.json | PASS |
| data_card | (586 records) | data/v1/report.json self_agreement.n | PASS |
| data_card | Disputed rate: 23.3% of generated records (1,011 of 4,340) | data/v1/report.json | PASS |
| data_card | verdict 88%, category 71% on all 100; 90.9% and 89.1% on the 55 not-disputed records; 84.4% and 48.9% on the 45 disputed ones | data/v1/review_agreement.json | PASS |
| data_card | 2,000 families, plus a top-up of 170 families | STATE.md P4 (2,000 + 170 families generated) | PASS |
| data_card | 36 agent roles | data/roles_v1.json | PASS |
| data_card | 74 distinct invented @gmail.com addresses (217 occurrences) and 114 distinct phone numbers (944 occurrences | data/release_sanitized_v1/SANITIZED.json | PASS |
| data_card | / 1 / invented Gmail address -> same local part at example.com (74 distinct addresses) / 217 / | SANITIZED.json v1 | PASS |
| data_card | / 1 / phone number -> unique fake, +1-555-000-NNNN or +99-000-000-NNNN (114 distinct numbers) / 944 / | SANITIZED.json v1 | PASS |
| data_card | / 2 / KPMG -> Kestrel Audit (including lowercase forms inside invented domains) / 512 / | data/release_sanitized_v2/SANITIZED.json | PASS |
| data_card | / 2 / Deloitte -> Dellmont / 310 / | data/release_sanitized_v2/SANITIZED.json | PASS |
| data_card | / 2 / DHL -> Dalton / 297 / | data/release_sanitized_v2/SANITIZED.json | PASS |
| data_card | / 2 / FedEx -> Fastway / 217 / | data/release_sanitized_v2/SANITIZED.json | PASS |
| data_card | / 2 / JPMorgan Chase, Chase Bank -> Harbor Union Bank / 25 / | data/release_sanitized_v2/SANITIZED.json | PASS |
| data_card | Wells Fargo, Bank of America, PNC Bank 2 each | SANITIZED.json v2 | PASS |
| data_card | (29 domains, e.g. okta.com, outlook.com, googleapis.com) / 1,199 / | SANITIZED.json v2 | PASS |
| data_card | (237 domains, e.g. meridian.com.test) / 8,102 / | SANITIZED.json v2 | PASS |
| data_card | every registrable domain (1,020) was checked in DNS | SANITIZED.json v2 | PASS |
| data_card | A's own list names 17 such test records, and a check that also ignores punctuation finds 28 | _known_issues_v1.json, results/a_overlap.json | PASS |
| readme | 36 agent roles | data/roles_v1.json | PASS |
| readme | 30 hand-written out-of-distribution records | data/ood/ood_v1.jsonl | PASS |
| readme | stratified sample of 20 | data/a_pro_agent_eval.jsonl | PASS |
| readme | blocks 0.74 [0.63, 0.83] at full precision and 0.41 [0.31, 0.51] in 4-bit | results/adaptive/metrics.json | PASS |
| readme | **USD 67.50**, of which Gemini calls 45.84 and managed tuning 21.66 (pilot 0.22, main run 12.51, G5 8.93) | exports/ledger.jsonl | PASS |
| readme | ledger (USD 114.10) that is USD 181.60 against USD 181.22 billed for the shared project, a gap of -0.38 (-0.2% | ledger + billing | PASS |
