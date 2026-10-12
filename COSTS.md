# COSTS

Generated from `exports/ledger.jsonl` by `uv run python -m tcg.costs`. Every online call and every batch
row is logged with its `usage_metadata` tokens. Thinking tokens are billed as output.

**Total recorded: USD 67.5024** (soft stop 70, hard ceiling 80)

## Price table (USD per 1M tokens)

Source: Cloud Billing SKU catalog, service C7E2-9256-1C43, read 2026-10-05.

| model | tier | input | output |
|---|---|---|---|
| gemini-3.8-flash | standard | 1.5 | 7.5 |
| gemini-3.8-flash | flex | 0.75 | 3.75 |
| gemini-3.8-flash | batch | 0.75 | 3.75 |
| gemini-3.1-pro-preview | standard | 2.0 | 12.0 |
| gemini-3.1-pro-preview | flex | 1.0 | 6.0 |
| gemini-3.1-pro-preview | batch | 1.0 | 6.0 |
| google/gemma4@gemma-4-e4b-it | managed LoRA tuning | 1.73 per 1M training tokens | |

Note: the pricing page lists gemini-3.8-flash at 0.75 / 3.75 introductory through 2026-12-31, but the
SKU list price for standard online is 1.50 / 7.50. The ledger uses the SKU price until the Billing report
confirms which one is charged.

## Spend by phase

| phase | kind | model | tier | calls/rows | input tok | output tok | thinking tok | training tok | USD |
|---|---|---|---|---|---|---|---|---|---|
| g5 | tuning | google/gemma4@gemma-4-e4b-it | managed_lora | 1 | 0 | 0 | 0 | 5159254 | 8.9255 |
| p0-sanity | online | gemini-3.8-flash | standard | 1 | 7 | 1 | 26 | 0 | 0.0002 |
| p2-flash-guard | online | gemini-3.8-flash | flex | 24 | 48692 | 1331 | 0 | 0 | 0.0415 |
| p2-gen | online | gemini-3.8-flash | flex | 12 | 24136 | 12715 | 0 | 0 | 0.0658 |
| p2-label | online | gemini-3.1-pro-preview | flex | 24 | 48692 | 1307 | 8394 | 0 | 0.1069 |
| p2-roles | online | gemini-3.8-flash | flex | 36 | 19198 | 40432 | 0 | 0 | 0.1660 |
| p2-roles-flextest | online | gemini-3.8-flash | flex | 1 | 532 | 1094 | 0 | 0 | 0.0045 |
| p4-gen-v1 | online | gemini-3.8-flash | flex | 2000 | 4025653 | 2127661 | 0 | 0 | 10.9980 |
| p4-gen-v1-topup | online | gemini-3.8-flash | flex | 170 | 355875 | 181296 | 0 | 0 | 0.9468 |
| p4-label-v1 | online | gemini-3.1-pro-preview | flex | 4926 | 10013525 | 263782 | 1627694 | 0 | 21.3624 |
| p5-flash-a_gold | online | gemini-3.8-flash | flex | 120 | 226608 | 6227 | 1439 | 0 | 0.1987 |
| p5-flash-a_replay | online | gemini-3.8-flash | flex | 1843 | 3628851 | 95798 | 29144 | 0 | 3.1902 |
| p5-flash-ood | online | gemini-3.8-flash | flex | 30 | 33375 | 1366 | 1195 | 0 | 0.0346 |
| p5-flash-review_100 | online | gemini-3.8-flash | flex | 100 | 204775 | 5483 | 2206 | 0 | 0.1824 |
| p5-flash-synthetic_test | online | gemini-3.8-flash | flex | 479 | 963623 | 25733 | 6528 | 0 | 0.8437 |
| p5-latency-std | online | gemini-3.1-pro-preview | standard | 60 | 66750 | 2507 | 6173 | 0 | 0.2377 |
| p5-latency-std | online | gemini-3.8-flash | standard | 30 | 33375 | 1404 | 1205 | 0 | 0.0696 |
| p5-pro-a_gold | online | gemini-3.1-pro-preview | flex | 120 | 226608 | 5568 | 22107 | 0 | 0.3927 |
| p5-pro-a_replay | online | gemini-3.1-pro-preview | flex | 1849 | 3639956 | 92639 | 455797 | 0 | 6.9306 |
| p5-pro-ood | online | gemini-3.1-pro-preview | flex | 30 | 33375 | 1358 | 3606 | 0 | 0.0632 |
| p5-pro-review_100 | online | gemini-3.1-pro-preview | flex | 1 | 1840 | 40 | 565 | 0 | 0.0055 |
| pilot | tuning | google/gemma4@gemma-4-e4b-it | managed_lora | 1 | 0 | 0 | 0 | 129446 | 0.2239 |
| real | tuning | google/gemma4@gemma-4-e4b-it | managed_lora | 1 | 0 | 0 | 0 | 7232466 | 12.5122 |


## Ledgers vs Billing report (FINAL, provisional until the owner re-pastes the Billing report on Saturday)

Billing report as given by the owner on 2026-10-09, gross usage, 13 Sep to 9 Oct morning, per project. Rate 95.99 INR
per USD, the currencyConversionRate in the Cloud Billing SKU catalog. The report lags up to a day and credits apply
with a delay.

Ledgers (token counts from usage_metadata, priced at SKU list prices; tuning at 1.73 USD per 1M training tokens):
- Project B (this repo): USD 67.50, final. Last ledger entry Thu 8 Oct 09:03 IST, last Google call 09:06 IST (the
  raw-file sync). Gemini calls 45.84 plus managed tuning 21.66 (pilot 0.22, real 12.51, G5 8.93).
- Project A (its COSTS.md): USD 114.10, final. Last Google call Fri 9 Oct 11:25 IST.

| Project | INR | USD at 95.99 | Ledgers (USD) | Gap, billed minus ledgers (USD) |
|---|---|---|---|---|
| govbench-brejesh-01 (Projects A and B) | 17,395.53 | 181.22 | A 114.10 + B 67.50 = 181.60 | -0.38 (-0.2%) |
| lecvault-brejesh-01 (a separate project, neither A nor B) | 4,531.81 | 47.21 | none | not part of this comparison |

The two ledgers match the govbench bill to within 0.2%; the bill is 0.38 USD below them. The earlier +41.18 / +42.05
gap in this file was a comparison error: that INR figure covered govbench and lecvault together and was compared with
the govbench ledgers alone.

Total gross usage on govbench-brejesh-01, USD 181.22, is under the USD 300 credit.
