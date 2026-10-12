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
