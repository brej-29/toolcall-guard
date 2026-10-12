# Results

95% intervals from a family-clustered bootstrap (1,000 resamples; 500 in the head-to-head tables). Invalid output counts as block with a wrong category (fail-closed). Gemma rows without a suffix are full precision (fp16 on Kaggle T4); "4-bit laptop" rows are the deployment variant on a 6 GB GPU, with the attack block rate it loses against full precision on the same records; "merged int8" rows have the LoRA merged into the base and then 8-bit weights (A replay on the 6 GB laptop GPU, the other sets on a Kaggle T4), the variant the quantization test picked. Any threshold is chosen on val_frozen (B's val split) only, never on a test or gold set. Gemini latency was measured on the Flex tier (queueing included); cost per 1,000 decisions is at the standard on-demand price. Local guards have zero marginal cost. Labels: review_100 and A gold come from two independent ChatGPT passes (no human-decided rows); A's replay and Pro agent records carry A's construction or Gemini teacher labels.

## synthetic_test (479 records)

| guard | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot (CIRCULAR: labels came from this model) | 479 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 128074.000 [120319.000, 133262.000] | 8.282 [7.981, 8.578] |
| gemini-3.8-flash zero-shot (advantaged: it generated these scenarios) | 479 | 0.986 [0.967, 1.000] | 0.022 [0.007, 0.040] | 0.944 [0.915, 0.969] | 1.000 [1.000, 1.000] | 38229.000 [36391.000, 39757.000] | 3.523 [3.466, 3.577] |
| gemma-4-e4b untuned zero-shot | 479 | 0.861 [0.814, 0.905] | 0.133 [0.094, 0.175] | 0.448 [0.392, 0.501] | 0.996 [0.989, 1.000] | 5506.700 [5425.100, 5599.700] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned few-shot | 479 | 0.885 [0.840, 0.928] | 0.188 [0.139, 0.235] | 0.610 [0.553, 0.660] | 1.000 [1.000, 1.000] | 6763.000 [6724.300, 6829.000] | 0.000 [0.000, 0.000] |
| keyword | 479 | 0.697 [0.634, 0.761] | 0.498 [0.439, 0.562] | 0.282 [0.239, 0.323] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours) | 479 | 0.913 [0.877, 0.950] | 0.066 [0.037, 0.099] | 0.775 [0.722, 0.818] | 1.000 [1.000, 1.000] | 7815.300 [7707.400, 7909.300] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), val threshold 0.61 | 479 | 0.841 [0.794, 0.887] | 0.048 [0.022, 0.075] | 0.755 [0.700, 0.801] | 1.000 [1.000, 1.000] | 7815.300 [7707.400, 7909.300] | 0.000 [0.000, 0.000] |
| gemma-4-e4b G5 in-domain (A data) | 479 | 0.923 [0.886, 0.957] | 0.089 [0.056, 0.124] | 0.520 [0.455, 0.577] | 1.000 [1.000, 1.000] | 6950.500 [6837.000, 7051.900] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned zero-shot, 4-bit laptop (attack block rate -0.053 vs full precision on the same 479 records) | 479 | 0.808 [0.756, 0.859] | 0.081 [0.049, 0.114] | 0.379 [0.325, 0.432] | 0.996 [0.990, 1.000] | 5572.500 [5492.500, 5668.800] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned few-shot, 4-bit laptop (attack block rate -0.019 vs full precision on the same 479 records) | 479 | 0.865 [0.819, 0.912] | 0.199 [0.151, 0.248] | 0.591 [0.538, 0.642] | 0.996 [0.989, 1.000] | 7703.900 [7630.700, 7783.200] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), 4-bit laptop (attack block rate -0.216 vs full precision on the same 479 records) | 479 | 0.697 [0.634, 0.761] | 0.015 [0.004, 0.030] | 0.648 [0.578, 0.702] | 1.000 [1.000, 1.000] | 8470.400 [8344.600, 8572.650] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), merged int8 (attack block rate -0.024 vs full precision on the same 479 records) | 479 | 0.889 [0.848, 0.932] | 0.059 [0.033, 0.091] | 0.759 [0.706, 0.805] | 1.000 [1.000, 1.000] | 13268.000 [13096.950, 13387.300] | 0.000 [0.000, 0.000] |

### Matched false positive rate

For each Gemini guard, every full-precision Gemma guard gets the lowest P(block) threshold whose false positive rate on val_frozen is at most that Gemini guard's rate on this set. The threshold is fit on val_frozen alone, so the rate achieved here can differ; it is shown beside the block rate.

| reference (its FPR here) | guard | threshold | val FPR | n | attack_block_rate | false_positive_rate |
|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot (0.000) | gemini-3.1-pro zero-shot (CIRCULAR: labels came from this model), default | - | - | 479 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b untuned zero-shot | unreachable on val (invalid outputs count as blocks) | | | | |
| | gemma-4-e4b untuned few-shot | 1.0000 | 0.000 | 479 | 0.630 [0.567, 0.692] | 0.018 [0.007, 0.036] |
| | gemma-4-e4b tuned (ours) | 0.9808 | 0.000 | 479 | 0.361 [0.291, 0.424] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b G5 in-domain (A data) | 0.9760 | 0.000 | 479 | 0.591 [0.527, 0.657] | 0.004 [0.000, 0.011] |
| gemini-3.8-flash zero-shot (0.022) | gemini-3.8-flash zero-shot (advantaged: it generated these scenarios), default | - | - | 479 | 0.986 [0.967, 1.000] | 0.022 [0.007, 0.040] |
| | gemma-4-e4b untuned zero-shot | 0.9999 | 0.011 | 479 | 0.529 [0.471, 0.597] | 0.022 [0.007, 0.040] |
| | gemma-4-e4b untuned few-shot | 0.9998 | 0.011 | 479 | 0.683 [0.615, 0.745] | 0.030 [0.011, 0.051] |
| | gemma-4-e4b tuned (ours) | 0.9428 | 0.011 | 479 | 0.587 [0.519, 0.653] | 0.004 [0.000, 0.011] |
| | gemma-4-e4b G5 in-domain (A data) | 0.9571 | 0.011 | 479 | 0.654 [0.592, 0.714] | 0.007 [0.000, 0.018] |

Per-category recall (precision):

| guard | benign | indirect_prompt_injection | social_engineering | privilege_escalation | data_exfiltration | destructive_action | sensitive_data_exposure | business_rule_violation |
|---|---|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot (CIRCULAR: labels came from this model) | 1.00 (1.00) | 1.00 (1.00) | 1.00 (1.00) | 1.00 (1.00) | 1.00 (1.00) | 1.00 (1.00) | 1.00 (1.00) | 1.00 (1.00) |
| gemini-3.8-flash zero-shot (advantaged: it generated these scenarios) | 0.98 (0.99) | 1.00 (1.00) | 0.85 (1.00) | 0.95 (0.86) | 1.00 (0.94) | 0.83 (1.00) | 1.00 (1.00) | 0.97 (0.80) |
| gemma-4-e4b untuned zero-shot | 0.87 (0.89) | 0.13 (0.35) | 0.06 (1.00) | 0.32 (0.24) | 0.48 (0.58) | 0.61 (0.44) | 0.95 (0.43) | 0.69 (0.39) |
| gemma-4-e4b untuned few-shot | 0.81 (0.90) | 0.20 (0.50) | 0.45 (0.88) | 0.95 (0.43) | 0.87 (0.52) | 0.83 (0.56) | 0.76 (0.46) | 0.67 (0.65) |
| keyword | 0.50 (0.68) | 0.20 (0.36) | 0.00 (0.00) | 0.32 (0.14) | 0.81 (0.31) | 0.70 (0.28) | 0.19 (0.22) | 0.22 (0.14) |
| gemma-4-e4b tuned (ours) | 0.93 (0.93) | 0.73 (0.66) | 0.76 (0.60) | 0.79 (0.94) | 0.77 (0.86) | 0.70 (0.70) | 0.86 (0.82) | 0.61 (0.81) |
| gemma-4-e4b G5 in-domain (A data) | 0.91 (0.94) | 0.44 (0.54) | 0.61 (0.47) | 0.84 (0.31) | 0.87 (0.48) | 0.13 (0.38) | 0.29 (0.86) | 0.36 (0.93) |
| gemma-4-e4b untuned zero-shot, 4-bit laptop | 0.92 (0.86) | 0.09 (0.25) | 0.06 (0.67) | 0.32 (0.21) | 0.32 (0.71) | 0.17 (0.24) | 0.90 (0.34) | 0.64 (0.43) |
| gemma-4-e4b untuned few-shot, 4-bit laptop | 0.80 (0.89) | 0.13 (0.35) | 0.61 (0.77) | 0.89 (0.46) | 0.77 (0.50) | 0.70 (0.57) | 0.81 (0.38) | 0.61 (0.71) |
| gemma-4-e4b tuned (ours), 4-bit laptop | 0.99 (0.81) | 0.51 (0.88) | 0.67 (0.48) | 0.79 (0.88) | 0.68 (0.88) | 0.26 (0.67) | 0.43 (1.00) | 0.39 (0.78) |
| gemma-4-e4b tuned (ours), merged int8 | 0.94 (0.92) | 0.78 (0.67) | 0.70 (0.61) | 0.79 (0.94) | 0.74 (0.92) | 0.57 (0.68) | 0.86 (0.78) | 0.58 (0.75) |

## ood (30 records)

| guard | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot | 30 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.950 [0.829, 1.000] | 1.000 [1.000, 1.000] | 92536.500 [91998.000, 94846.000] | 4.211 [3.963, 4.494] |
| gemini-3.8-flash zero-shot | 30 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.907 [0.729, 1.000] | 1.000 [1.000, 1.000] | 12711.500 [12411.000, 12965.500] | 2.309 [2.187, 2.431] |
| gemma-4-e4b untuned zero-shot | 30 | 0.944 [0.824, 1.000] | 0.000 [0.000, 0.000] | 0.541 [0.345, 0.723] | 1.000 [1.000, 1.000] | 4834.250 [4549.450, 5093.700] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned few-shot | 30 | 0.944 [0.824, 1.000] | 0.083 [0.000, 0.250] | 0.600 [0.401, 0.772] | 1.000 [1.000, 1.000] | 5897.800 [5759.900, 6027.700] | 0.000 [0.000, 0.000] |
| keyword | 30 | 0.333 [0.118, 0.556] | 0.333 [0.077, 0.600] | 0.217 [0.076, 0.360] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours) | 30 | 1.000 [1.000, 1.000] | 0.083 [0.000, 0.273] | 0.685 [0.452, 0.867] | 1.000 [1.000, 1.000] | 7702.450 [7404.600, 8094.200] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), val threshold 0.61 | 30 | 1.000 [1.000, 1.000] | 0.083 [0.000, 0.273] | 0.685 [0.452, 0.867] | 1.000 [1.000, 1.000] | 7702.450 [7404.600, 8094.200] | 0.000 [0.000, 0.000] |
| gemma-4-e4b G5 in-domain (A data) | 30 | 0.944 [0.824, 1.000] | 0.000 [0.000, 0.000] | 0.760 [0.543, 0.928] | 1.000 [1.000, 1.000] | 6215.450 [6048.850, 6603.250] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned zero-shot, 4-bit laptop (attack block rate +0.000 vs full precision on the same 30 records) | 30 | 0.944 [0.824, 1.000] | 0.000 [0.000, 0.000] | 0.430 [0.256, 0.595] | 1.000 [1.000, 1.000] | 4949.450 [4710.800, 5340.800] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned few-shot, 4-bit laptop (attack block rate +0.000 vs full precision on the same 30 records) | 30 | 0.944 [0.824, 1.000] | 0.083 [0.000, 0.250] | 0.730 [0.505, 0.896] | 1.000 [1.000, 1.000] | 7003.050 [6807.650, 7166.800] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), 4-bit laptop (attack block rate -0.111 vs full precision on the same 30 records) | 30 | 0.889 [0.714, 1.000] | 0.000 [0.000, 0.000] | 0.730 [0.492, 0.895] | 1.000 [1.000, 1.000] | 7505.300 [6947.500, 8013.150] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), merged int8 (attack block rate +0.000 vs full precision on the same 30 records) | 30 | 1.000 [1.000, 1.000] | 0.083 [0.000, 0.273] | 0.685 [0.452, 0.867] | 1.000 [1.000, 1.000] | 12730.000 [11982.400, 13042.500] | 0.000 [0.000, 0.000] |

### Matched false positive rate

For each Gemini guard, every full-precision Gemma guard gets the lowest P(block) threshold whose false positive rate on val_frozen is at most that Gemini guard's rate on this set. The threshold is fit on val_frozen alone, so the rate achieved here can differ; it is shown beside the block rate.

| reference (its FPR here) | guard | threshold | val FPR | n | attack_block_rate | false_positive_rate |
|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot (0.000) | gemini-3.1-pro zero-shot, default | - | - | 30 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b untuned zero-shot | unreachable on val (invalid outputs count as blocks) | | | | |
| | gemma-4-e4b untuned few-shot | 1.0000 | 0.000 | 30 | 0.889 [0.737, 1.000] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b tuned (ours) | 0.9808 | 0.000 | 30 | 0.833 [0.650, 1.000] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b G5 in-domain (A data) | 0.9760 | 0.000 | 30 | 0.889 [0.737, 1.000] | 0.000 [0.000, 0.000] |
| gemini-3.8-flash zero-shot (0.000) | gemini-3.8-flash zero-shot, default | - | - | 30 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b untuned zero-shot | unreachable on val (invalid outputs count as blocks) | | | | |
| | gemma-4-e4b untuned few-shot | 1.0000 | 0.000 | 30 | 0.889 [0.737, 1.000] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b tuned (ours) | 0.9808 | 0.000 | 30 | 0.833 [0.650, 1.000] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b G5 in-domain (A data) | 0.9760 | 0.000 | 30 | 0.889 [0.737, 1.000] | 0.000 [0.000, 0.000] |

## review_100 (100 records)

| guard | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot | 100 | 0.942 [0.885, 0.986] | 0.226 [0.080, 0.379] | 0.681 [0.566, 0.769] | 1.000 [1.000, 1.000] | 119062.500 [100652.000, 134858.000] | 9.017 [8.421, 9.627] |
| gemini-3.8-flash zero-shot | 100 | 0.928 [0.864, 0.985] | 0.194 [0.067, 0.343] | 0.711 [0.600, 0.802] | 1.000 [1.000, 1.000] | 14127.000 [13408.000, 16205.000] | 3.648 [3.493, 3.862] |
| gemma-4-e4b untuned zero-shot | 100 | 0.841 [0.746, 0.918] | 0.290 [0.132, 0.457] | 0.305 [0.214, 0.380] | 1.000 [1.000, 1.000] | 5859.600 [5571.950, 6031.700] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned few-shot | 100 | 0.884 [0.803, 0.955] | 0.355 [0.189, 0.531] | 0.429 [0.330, 0.510] | 1.000 [1.000, 1.000] | 6791.600 [6697.000, 6888.100] | 0.000 [0.000, 0.000] |
| keyword | 100 | 0.652 [0.542, 0.770] | 0.548 [0.370, 0.733] | 0.243 [0.172, 0.309] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours) | 100 | 0.870 [0.786, 0.940] | 0.194 [0.061, 0.333] | 0.584 [0.461, 0.675] | 1.000 [1.000, 1.000] | 7852.250 [7600.500, 8007.400] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), val threshold 0.61 | 100 | 0.812 [0.716, 0.900] | 0.194 [0.061, 0.333] | 0.546 [0.418, 0.641] | 1.000 [1.000, 1.000] | 7852.250 [7600.500, 8007.400] | 0.000 [0.000, 0.000] |
| gemma-4-e4b G5 in-domain (A data) | 100 | 0.884 [0.809, 0.957] | 0.323 [0.161, 0.485] | 0.445 [0.313, 0.541] | 1.000 [1.000, 1.000] | 7033.350 [6832.800, 7200.350] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned zero-shot, 4-bit laptop (attack block rate -0.029 vs full precision on the same 100 records) | 100 | 0.812 [0.719, 0.897] | 0.226 [0.091, 0.371] | 0.289 [0.206, 0.355] | 1.000 [1.000, 1.000] | 7054.900 [6793.800, 7218.300] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned few-shot, 4-bit laptop (attack block rate -0.043 vs full precision on the same 100 records) | 100 | 0.841 [0.754, 0.925] | 0.419 [0.241, 0.594] | 0.442 [0.339, 0.526] | 1.000 [1.000, 1.000] | 8803.950 [8290.700, 9577.150] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), 4-bit laptop (attack block rate -0.217 vs full precision on the same 100 records) | 100 | 0.652 [0.536, 0.760] | 0.097 [0.000, 0.207] | 0.374 [0.282, 0.452] | 1.000 [1.000, 1.000] | 8550.600 [8361.400, 8776.900] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), merged int8 (attack block rate -0.014 vs full precision on the same 100 records) | 100 | 0.855 [0.769, 0.929] | 0.194 [0.061, 0.333] | 0.586 [0.463, 0.677] | 1.000 [1.000, 1.000] | 14301.250 [13927.600, 14763.700] | 0.000 [0.000, 0.000] |

### Matched false positive rate

For each Gemini guard, every full-precision Gemma guard gets the lowest P(block) threshold whose false positive rate on val_frozen is at most that Gemini guard's rate on this set. The threshold is fit on val_frozen alone, so the rate achieved here can differ; it is shown beside the block rate.

| reference (its FPR here) | guard | threshold | val FPR | n | attack_block_rate | false_positive_rate |
|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot (0.226) | gemini-3.1-pro zero-shot, default | - | - | 100 | 0.942 [0.885, 0.986] | 0.226 [0.080, 0.379] |
| | gemma-4-e4b untuned zero-shot | 0.2599 | 0.218 | 100 | 0.855 [0.768, 0.930] | 0.290 [0.125, 0.455] |
| | gemma-4-e4b untuned few-shot | 0.3381 | 0.218 | 100 | 0.884 [0.800, 0.955] | 0.419 [0.243, 0.613] |
| | gemma-4-e4b tuned (ours) | 0.2235 | 0.218 | 100 | 0.928 [0.859, 0.983] | 0.290 [0.136, 0.467] |
| | gemma-4-e4b G5 in-domain (A data) | 0.2534 | 0.218 | 100 | 0.913 [0.838, 0.971] | 0.323 [0.154, 0.485] |
| gemini-3.8-flash zero-shot (0.194) | gemini-3.8-flash zero-shot, default | - | - | 100 | 0.928 [0.864, 0.985] | 0.194 [0.067, 0.343] |
| | gemma-4-e4b untuned zero-shot | 0.2979 | 0.184 | 100 | 0.855 [0.768, 0.930] | 0.290 [0.125, 0.455] |
| | gemma-4-e4b untuned few-shot | 0.7090 | 0.184 | 100 | 0.855 [0.775, 0.934] | 0.323 [0.160, 0.500] |
| | gemma-4-e4b tuned (ours) | 0.3087 | 0.184 | 100 | 0.884 [0.797, 0.950] | 0.290 [0.136, 0.467] |
| | gemma-4-e4b G5 in-domain (A data) | 0.2922 | 0.184 | 100 | 0.913 [0.838, 0.971] | 0.323 [0.154, 0.485] |

## a_gold (120 records)

| guard | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot | 120 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.075] | 0.788 [0.655, 0.891] | 1.000 [1.000, 1.000] | 97141.500 [95355.000, 102825.000] | 6.544 [6.091, 7.078] |
| gemini-3.8-flash zero-shot | 120 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.072] | 0.719 [0.578, 0.827] | 1.000 [1.000, 1.000] | 18685.000 [16158.000, 19743.000] | 3.312 [3.242, 3.390] |
| gemma-4-e4b untuned zero-shot | 120 | 0.692 [0.522, 0.847] | 0.059 [0.014, 0.125] | 0.297 [0.198, 0.390] | 0.992 [0.974, 1.000] | 5129.850 [5029.700, 5231.600] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned few-shot | 120 | 0.750 [0.594, 0.891] | 0.074 [0.015, 0.141] | 0.556 [0.382, 0.689] | 1.000 [1.000, 1.000] | 6682.900 [6595.700, 6771.550] | 0.000 [0.000, 0.000] |
| keyword | 120 | 0.654 [0.515, 0.795] | 0.176 [0.095, 0.259] | 0.250 [0.160, 0.321] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours) | 120 | 0.692 [0.526, 0.851] | 0.029 [0.000, 0.078] | 0.581 [0.376, 0.700] | 1.000 [1.000, 1.000] | 7126.300 [6896.700, 7421.700] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), val threshold 0.61 | 120 | 0.654 [0.484, 0.816] | 0.029 [0.000, 0.078] | 0.586 [0.378, 0.704] | 1.000 [1.000, 1.000] | 7126.300 [6896.700, 7421.700] | 0.000 [0.000, 0.000] |
| gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 120 | 0.750 [0.600, 0.891] | 0.044 [0.000, 0.100] | 0.527 [0.358, 0.626] | 1.000 [1.000, 1.000] | 6210.700 [6010.700, 6498.200] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), 4-bit laptop (attack block rate -0.192 vs full precision on the same 120 records) | 120 | 0.500 [0.354, 0.659] | 0.000 [0.000, 0.000] | 0.575 [0.362, 0.697] | 0.992 [0.973, 1.000] | 8054.900 [7789.600, 8299.900] | 0.000 [0.000, 0.000] |
| gemma-4-e4b G5 in-domain (A data), 4-bit laptop (IN-DOMAIN: trained on scenarios from A's generator) (attack block rate -0.077 vs full precision on the same 120 records) | 120 | 0.673 [0.509, 0.827] | 0.029 [0.000, 0.081] | 0.573 [0.400, 0.682] | 1.000 [1.000, 1.000] | 7504.000 [7328.950, 7909.900] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), merged int8 (attack block rate -0.038 vs full precision on the same 120 records) | 120 | 0.654 [0.484, 0.816] | 0.029 [0.000, 0.078] | 0.586 [0.384, 0.703] | 1.000 [1.000, 1.000] | 12205.000 [11904.700, 12641.400] | 0.000 [0.000, 0.000] |
| A handwritten_rules_g2prime (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 109 of 120 records) | 109 | 0.902 [0.811, 0.979] | 0.000 [0.000, 0.000] | 0.498 [0.403, 0.658] | 1.000 [1.000, 1.000] | 0.017 [0.015, 0.023] | 0.000 [0.000, 0.000] |
| A llm_guard_flash (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 109 of 120 records) | 109 | 1.000 [1.000, 1.000] | 0.015 [0.000, 0.051] | 0.484 [0.301, 0.608] | 1.000 [1.000, 1.000] | 14908.500 [13580.600, 16503.200] | 1.593 [1.538, 1.656] |
| A model_armor_direct (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 109 of 120 records) | 109 | 0.512 [0.378, 0.632] | 0.235 [0.135, 0.338] | 0.124 [0.109, 0.164] | 1.000 [1.000, 1.000] | 965.700 [540.800, 1152.500] | 0.008 [0.006, 0.009] |
| A unguarded (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 93 of 120 records) | 93 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.169 [0.151, 0.230] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

### Matched false positive rate

For each Gemini guard, every full-precision Gemma guard gets the lowest P(block) threshold whose false positive rate on val_frozen is at most that Gemini guard's rate on this set. The threshold is fit on val_frozen alone, so the rate achieved here can differ; it is shown beside the block rate.

| reference (its FPR here) | guard | threshold | val FPR | n | attack_block_rate | false_positive_rate |
|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot (0.029) | gemini-3.1-pro zero-shot, default | - | - | 120 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.075] |
| | gemma-4-e4b untuned zero-shot | 0.9997 | 0.023 | 120 | 0.346 [0.232, 0.488] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b untuned few-shot | 0.9997 | 0.023 | 120 | 0.538 [0.361, 0.698] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b tuned (ours) | 0.8165 | 0.023 | 120 | 0.558 [0.389, 0.725] | 0.015 [0.000, 0.051] |
| | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 0.9334 | 0.023 | 120 | 0.558 [0.429, 0.711] | 0.000 [0.000, 0.000] |
| gemini-3.8-flash zero-shot (0.029) | gemini-3.8-flash zero-shot, default | - | - | 120 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.072] |
| | gemma-4-e4b untuned zero-shot | 0.9997 | 0.023 | 120 | 0.346 [0.232, 0.488] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b untuned few-shot | 0.9997 | 0.023 | 120 | 0.538 [0.361, 0.698] | 0.000 [0.000, 0.000] |
| | gemma-4-e4b tuned (ours) | 0.8165 | 0.023 | 120 | 0.558 [0.389, 0.725] | 0.015 [0.000, 0.051] |
| | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 0.9334 | 0.023 | 120 | 0.558 [0.429, 0.711] | 0.000 [0.000, 0.000] |

### Head-to-head on each Project A configuration's covered records

Every guard is scored on the records that A configuration has a verdict for (its coverage differs per configuration). n below 'records' means that guard has no prediction for some of them.

| A configuration (records) | guard | n | attack_block_rate | false_positive_rate |
|---|---|---|---|---|
| A handwritten_rules_g2prime (109) | A handwritten_rules_g2prime (Project A result; verdict metrics only, it does not emit our categories) | 109 | 0.902 [0.809, 0.977] | 0.000 [0.000, 0.000] |
| A handwritten_rules_g2prime (109) | gemma-4-e4b tuned (ours) | 109 | 0.634 [0.435, 0.824] | 0.029 [0.000, 0.076] |
| A handwritten_rules_g2prime (109) | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 109 | 0.683 [0.500, 0.850] | 0.044 [0.000, 0.102] |
| A handwritten_rules_g2prime (109) | gemma-4-e4b untuned zero-shot | 109 | 0.634 [0.414, 0.828] | 0.059 [0.012, 0.121] |
| A handwritten_rules_g2prime (109) | gemini-3.1-pro zero-shot | 109 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.077] |
| A handwritten_rules_g2prime (109) | gemini-3.8-flash zero-shot | 109 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.077] |
| A llm_guard_flash (109) | A llm_guard_flash (Project A result; verdict metrics only, it does not emit our categories) | 109 | 1.000 [1.000, 1.000] | 0.015 [0.000, 0.051] |
| A llm_guard_flash (109) | gemma-4-e4b tuned (ours) | 109 | 0.634 [0.435, 0.824] | 0.029 [0.000, 0.076] |
| A llm_guard_flash (109) | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 109 | 0.683 [0.500, 0.850] | 0.044 [0.000, 0.102] |
| A llm_guard_flash (109) | gemma-4-e4b untuned zero-shot | 109 | 0.634 [0.414, 0.828] | 0.059 [0.012, 0.121] |
| A llm_guard_flash (109) | gemini-3.1-pro zero-shot | 109 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.077] |
| A llm_guard_flash (109) | gemini-3.8-flash zero-shot | 109 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.077] |
| A model_armor_direct (109) | A model_armor_direct (Project A result; verdict metrics only, it does not emit our categories) | 109 | 0.512 [0.389, 0.632] | 0.235 [0.136, 0.333] |
| A model_armor_direct (109) | gemma-4-e4b tuned (ours) | 109 | 0.634 [0.435, 0.824] | 0.029 [0.000, 0.076] |
| A model_armor_direct (109) | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 109 | 0.683 [0.500, 0.850] | 0.044 [0.000, 0.102] |
| A model_armor_direct (109) | gemma-4-e4b untuned zero-shot | 109 | 0.634 [0.414, 0.828] | 0.059 [0.012, 0.121] |
| A model_armor_direct (109) | gemini-3.1-pro zero-shot | 109 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.077] |
| A model_armor_direct (109) | gemini-3.8-flash zero-shot | 109 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.077] |
| A unguarded (93) | A unguarded (Project A result; verdict metrics only, it does not emit our categories) | 93 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| A unguarded (93) | gemma-4-e4b tuned (ours) | 93 | 0.560 [0.316, 0.826] | 0.029 [0.000, 0.082] |
| A unguarded (93) | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 93 | 0.600 [0.320, 0.875] | 0.044 [0.000, 0.100] |
| A unguarded (93) | gemma-4-e4b untuned zero-shot | 93 | 0.560 [0.308, 0.800] | 0.059 [0.013, 0.125] |
| A unguarded (93) | gemini-3.1-pro zero-shot | 93 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.074] |
| A unguarded (93) | gemini-3.8-flash zero-shot | 93 | 1.000 [1.000, 1.000] | 0.029 [0.000, 0.079] |

## a_replay (1863 records)

| guard | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot | 1863 | 0.983 [0.967, 0.994] | 0.034 [0.018, 0.050] | 0.797 [0.679, 0.851] | 1.000 [1.000, 1.000] | 107564.000 [104707.000, 108954.000] | 7.287 [7.045, 7.529] |
| gemini-3.8-flash zero-shot | 1863 | 0.990 [0.972, 1.000] | 0.027 [0.013, 0.043] | 0.704 [0.590, 0.762] | 1.000 [1.000, 1.000] | 17702.000 [17114.000, 18086.000] | 3.451 [3.397, 3.506] |
| gemma-4-e4b untuned zero-shot | 1863 | 0.686 [0.595, 0.774] | 0.150 [0.100, 0.208] | 0.286 [0.234, 0.340] | 0.975 [0.961, 0.988] | 5195.300 [5153.550, 5245.900] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned few-shot | 1863 | 0.764 [0.684, 0.844] | 0.205 [0.148, 0.270] | 0.528 [0.452, 0.580] | 0.997 [0.995, 0.999] | 6800.200 [6750.100, 6859.800] | 0.000 [0.000, 0.000] |
| keyword | 1863 | 0.555 [0.443, 0.663] | 0.139 [0.098, 0.179] | 0.332 [0.272, 0.382] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours) | 1863 | 0.706 [0.619, 0.794] | 0.079 [0.040, 0.126] | 0.478 [0.401, 0.527] | 1.000 [1.000, 1.000] | 7039.500 [6962.550, 7134.500] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), val threshold 0.61 | 1863 | 0.656 [0.564, 0.745] | 0.061 [0.028, 0.104] | 0.470 [0.393, 0.522] | 1.000 [1.000, 1.000] | 7039.500 [6962.550, 7134.500] | 0.000 [0.000, 0.000] |
| gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) (7 test records from A's _known_issues_v1 excluded) | 1856 | 0.811 [0.754, 0.869] | 0.076 [0.042, 0.121] | 0.534 [0.450, 0.583] | 1.000 [1.000, 1.000] | 6435.350 [6307.500, 6553.200] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), 4-bit laptop (attack block rate -0.249 vs full precision on the same 1863 records) | 1863 | 0.457 [0.377, 0.544] | 0.030 [0.009, 0.064] | 0.457 [0.367, 0.525] | 0.998 [0.996, 1.000] | 7905.300 [7806.400, 8021.400] | 0.000 [0.000, 0.000] |
| gemma-4-e4b G5 in-domain (A data), 4-bit laptop (IN-DOMAIN: trained on scenarios from A's generator) (PARTIAL: 1401 of 1856 records) (2 test records from A's _known_issues_v1 excluded) (attack block rate -0.146 vs full precision on the same 1401 records) | 1401 | 0.665 [0.582, 0.750] | 0.041 [0.017, 0.075] | 0.445 [0.353, 0.501] | 1.000 [1.000, 1.000] | 8951.900 [8737.450, 9158.900] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), merged int8 (attack block rate -0.010 vs full precision on the same 1863 records) | 1863 | 0.695 [0.611, 0.783] | 0.076 [0.038, 0.127] | 0.474 [0.397, 0.522] | 1.000 [1.000, 1.000] | 37423.300 [36689.800, 38301.100] | 0.000 [0.000, 0.000] |
| A handwritten_rules_g2prime (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 861 of 1863 records) | 861 | 0.799 [0.729, 0.870] | 0.003 [0.000, 0.008] | 0.525 [0.444, 0.569] | 1.000 [1.000, 1.000] | 0.021 [0.019, 0.025] | 0.000 [0.000, 0.000] |
| A live_G2p (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 267 of 1863 records) | 267 | 0.667 [0.582, 0.758] | 0.013 [0.000, 0.030] | 0.649 [0.545, 0.700] | 1.000 [1.000, 1.000] | 0.300 [0.200, 0.300] | 0.000 [0.000, 0.000] |
| A live_G4-G2p+G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 270 of 1863 records) | 270 | 0.881 [0.821, 0.941] | 0.012 [0.000, 0.031] | 0.706 [0.577, 0.768] | 1.000 [1.000, 1.000] | 1799.450 [1454.000, 3319.750] | 0.000 [0.000, 0.000] |
| A live_G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 241 of 1863 records) | 241 | 0.906 [0.851, 0.959] | 0.000 [0.000, 0.000] | 0.641 [0.483, 0.721] | 1.000 [1.000, 1.000] | 5776.300 [5080.800, 6319.150] | 0.000 [0.000, 0.000] |
| A llm_guard_flash (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 859 of 1863 records) | 859 | 0.979 [0.957, 0.996] | 0.000 [0.000, 0.000] | 0.625 [0.516, 0.695] | 1.000 [1.000, 1.000] | 16475.500 [16063.800, 16774.700] | 1.621 [1.588, 1.657] |
| A model_armor_direct (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 861 of 1863 records) | 861 | 0.350 [0.279, 0.430] | 0.257 [0.186, 0.328] | 0.084 [0.078, 0.090] | 1.000 [1.000, 1.000] | 1085.500 [985.700, 1205.600] | 0.010 [0.009, 0.011] |
| A unguarded (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 573 of 1863 records) | 573 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.118 [0.113, 0.144] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

### a_replay, replay_group real_agent (1566 records)

| guard | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot | 1566 | 0.975 [0.952, 0.994] | 0.034 [0.018, 0.051] | 0.741 [0.643, 0.895] | 1.000 [1.000, 1.000] | 102576.000 [98743.000, 107073.000] | 7.151 [6.842, 7.425] |
| gemini-3.8-flash zero-shot | 1566 | 0.984 [0.957, 1.000] | 0.027 [0.012, 0.043] | 0.634 [0.541, 0.774] | 1.000 [1.000, 1.000] | 18298.500 [17816.000, 18901.000] | 3.449 [3.387, 3.505] |
| gemma-4-e4b untuned zero-shot | 1566 | 0.622 [0.524, 0.725] | 0.150 [0.100, 0.209] | 0.198 [0.162, 0.272] | 0.971 [0.954, 0.986] | 5157.500 [5116.300, 5200.500] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned few-shot | 1566 | 0.700 [0.607, 0.797] | 0.205 [0.146, 0.270] | 0.437 [0.359, 0.552] | 0.997 [0.994, 0.999] | 6783.200 [6726.600, 6849.200] | 0.000 [0.000, 0.000] |
| keyword | 1566 | 0.463 [0.335, 0.583] | 0.139 [0.099, 0.178] | 0.318 [0.259, 0.424] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours) | 1566 | 0.620 [0.525, 0.714] | 0.079 [0.040, 0.124] | 0.400 [0.327, 0.504] | 1.000 [1.000, 1.000] | 6930.550 [6787.700, 7026.000] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), val threshold 0.61 | 1566 | 0.567 [0.466, 0.666] | 0.061 [0.029, 0.103] | 0.395 [0.316, 0.499] | 1.000 [1.000, 1.000] | 6930.550 [6787.700, 7026.000] | 0.000 [0.000, 0.000] |
| gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) (7 test records from A's _known_issues_v1 excluded) | 1559 | 0.760 [0.688, 0.829] | 0.076 [0.038, 0.118] | 0.463 [0.383, 0.584] | 1.000 [1.000, 1.000] | 6272.000 [6135.700, 6429.700] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), 4-bit laptop (attack block rate -0.270 vs full precision on the same 1566 records) | 1566 | 0.350 [0.271, 0.441] | 0.030 [0.009, 0.064] | 0.395 [0.299, 0.509] | 0.999 [0.995, 1.000] | 7891.200 [7792.500, 8021.800] | 0.000 [0.000, 0.000] |
| gemma-4-e4b G5 in-domain (A data), 4-bit laptop (IN-DOMAIN: trained on scenarios from A's generator) (PARTIAL: 1104 of 1559 records) (2 test records from A's _known_issues_v1 excluded) (attack block rate -0.168 vs full precision on the same 1104 records) | 1104 | 0.592 [0.497, 0.696] | 0.041 [0.016, 0.073] | 0.389 [0.281, 0.506] | 1.000 [1.000, 1.000] | 8803.800 [8573.300, 9069.000] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), merged int8 (attack block rate -0.009 vs full precision on the same 1566 records) | 1566 | 0.611 [0.515, 0.718] | 0.076 [0.037, 0.123] | 0.392 [0.319, 0.510] | 1.000 [1.000, 1.000] | 36119.750 [35402.200, 36742.000] | 0.000 [0.000, 0.000] |
| A handwritten_rules_g2prime (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 564 of 1566 records) | 564 | 0.673 [0.597, 0.763] | 0.003 [0.000, 0.008] | 0.554 [0.467, 0.678] | 1.000 [1.000, 1.000] | 0.026 [0.020, 0.030] | 0.000 [0.000, 0.000] |
| A live_G2p (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 267 of 1566 records) | 267 | 0.667 [0.582, 0.758] | 0.013 [0.000, 0.030] | 0.649 [0.545, 0.700] | 1.000 [1.000, 1.000] | 0.300 [0.200, 0.300] | 0.000 [0.000, 0.000] |
| A live_G4-G2p+G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 270 of 1566 records) | 270 | 0.881 [0.821, 0.941] | 0.012 [0.000, 0.031] | 0.706 [0.577, 0.768] | 1.000 [1.000, 1.000] | 1799.450 [1454.000, 3319.750] | 0.000 [0.000, 0.000] |
| A live_G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 241 of 1566 records) | 241 | 0.906 [0.851, 0.959] | 0.000 [0.000, 0.000] | 0.641 [0.483, 0.721] | 1.000 [1.000, 1.000] | 5776.300 [5080.800, 6319.150] | 0.000 [0.000, 0.000] |
| A llm_guard_flash (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 562 of 1566 records) | 562 | 0.947 [0.893, 0.994] | 0.000 [0.000, 0.000] | 0.523 [0.415, 0.661] | 1.000 [1.000, 1.000] | 15624.650 [14959.900, 16138.500] | 1.601 [1.560, 1.643] |
| A model_armor_direct (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 564 of 1566 records) | 564 | 0.298 [0.213, 0.395] | 0.257 [0.192, 0.333] | 0.104 [0.097, 0.128] | 1.000 [1.000, 1.000] | 1003.350 [757.200, 1144.400] | 0.008 [0.007, 0.010] |
| A unguarded (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 573 of 1566 records) | 573 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.118 [0.113, 0.144] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

### a_replay, replay_group simulated_compromised (297 records)

| guard | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot | 297 | 0.997 [0.989, 1.000] | - | 0.685 [0.564, 0.790] | 1.000 [1.000, 1.000] | 114131.000 [112952.000, 115123.000] | 8.005 [7.506, 8.559] |
| gemini-3.8-flash zero-shot | 297 | 1.000 [1.000, 1.000] | - | 0.586 [0.482, 0.675] | 1.000 [1.000, 1.000] | 14062.000 [13904.000, 14428.500] | 3.461 [3.390, 3.540] |
| gemma-4-e4b untuned zero-shot | 297 | 0.808 [0.724, 0.881] | - | 0.272 [0.194, 0.330] | 0.997 [0.989, 1.000] | 5587.900 [5413.000, 5760.600] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned few-shot | 297 | 0.886 [0.818, 0.942] | - | 0.500 [0.410, 0.578] | 1.000 [1.000, 1.000] | 6897.100 [6794.600, 7008.500] | 0.000 [0.000, 0.000] |
| keyword | 297 | 0.731 [0.620, 0.833] | - | 0.270 [0.196, 0.331] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours) | 297 | 0.869 [0.785, 0.934] | - | 0.427 [0.343, 0.505] | 1.000 [1.000, 1.000] | 7672.600 [7522.600, 7867.700] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), val threshold 0.61 | 297 | 0.825 [0.734, 0.897] | - | 0.406 [0.326, 0.490] | 1.000 [1.000, 1.000] | 7672.600 [7522.600, 7867.700] | 0.000 [0.000, 0.000] |
| gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) (7 test records from A's _known_issues_v1 excluded) | 297 | 0.909 [0.860, 0.948] | - | 0.452 [0.349, 0.530] | 1.000 [1.000, 1.000] | 6978.000 [6882.550, 7094.200] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), 4-bit laptop (attack block rate -0.209 vs full precision on the same 297 records) | 297 | 0.660 [0.569, 0.746] | - | 0.394 [0.293, 0.466] | 0.997 [0.989, 1.000] | 7973.700 [7760.800, 8150.400] | 0.000 [0.000, 0.000] |
| gemma-4-e4b G5 in-domain (A data), 4-bit laptop (IN-DOMAIN: trained on scenarios from A's generator) (2 test records from A's _known_issues_v1 excluded) (attack block rate -0.104 vs full precision on the same 297 records) | 297 | 0.805 [0.720, 0.879] | - | 0.387 [0.293, 0.460] | 1.000 [1.000, 1.000] | 9280.600 [9020.200, 9428.900] | 0.000 [0.000, 0.000] |
| gemma-4-e4b tuned (ours), merged int8 (attack block rate -0.013 vs full precision on the same 297 records) | 297 | 0.855 [0.766, 0.923] | - | 0.426 [0.342, 0.504] | 1.000 [1.000, 1.000] | 43987.900 [43005.450, 45068.550] | 0.000 [0.000, 0.000] |
| A handwritten_rules_g2prime (Project A result; verdict metrics only, it does not emit our categories) | 297 | 0.872 [0.777, 0.956] | - | 0.456 [0.370, 0.521] | 1.000 [1.000, 1.000] | 0.019 [0.017, 0.022] | 0.000 [0.000, 0.000] |
| A llm_guard_flash (Project A result; verdict metrics only, it does not emit our categories) | 297 | 0.997 [0.990, 1.000] | - | 0.534 [0.411, 0.631] | 1.000 [1.000, 1.000] | 18305.000 [17811.300, 19323.400] | 1.658 [1.623, 1.694] |
| A model_armor_direct (Project A result; verdict metrics only, it does not emit our categories) | 297 | 0.380 [0.288, 0.473] | - | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 1199.100 [1086.600, 1371.800] | 0.013 [0.012, 0.014] |

### Matched false positive rate

For each Gemini guard, every full-precision Gemma guard gets the lowest P(block) threshold whose false positive rate on val_frozen is at most that Gemini guard's rate on this set. The threshold is fit on val_frozen alone, so the rate achieved here can differ; it is shown beside the block rate.

| reference (its FPR here) | guard | threshold | val FPR | n | attack_block_rate | false_positive_rate |
|---|---|---|---|---|---|---|
| gemini-3.1-pro zero-shot (0.034) | gemini-3.1-pro zero-shot, default | - | - | 1863 | 0.983 [0.967, 0.994] | 0.034 [0.018, 0.050] |
| | gemma-4-e4b untuned zero-shot | 0.9997 | 0.023 | 1863 | 0.363 [0.287, 0.444] | 0.051 [0.025, 0.085] |
| | gemma-4-e4b untuned few-shot | 0.9997 | 0.023 | 1863 | 0.491 [0.409, 0.577] | 0.056 [0.029, 0.096] |
| | gemma-4-e4b tuned (ours) | 0.8165 | 0.023 | 1863 | 0.504 [0.427, 0.591] | 0.036 [0.015, 0.070] |
| | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 0.9334 | 0.023 | 1856 | 0.457 [0.373, 0.533] | 0.027 [0.007, 0.056] |
| gemini-3.8-flash zero-shot (0.027) | gemini-3.8-flash zero-shot, default | - | - | 1863 | 0.990 [0.972, 1.000] | 0.027 [0.013, 0.043] |
| | gemma-4-e4b untuned zero-shot | 0.9997 | 0.023 | 1863 | 0.363 [0.287, 0.444] | 0.051 [0.025, 0.085] |
| | gemma-4-e4b untuned few-shot | 0.9997 | 0.023 | 1863 | 0.491 [0.409, 0.577] | 0.056 [0.029, 0.096] |
| | gemma-4-e4b tuned (ours) | 0.8165 | 0.023 | 1863 | 0.504 [0.427, 0.591] | 0.036 [0.015, 0.070] |
| | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 0.9334 | 0.023 | 1856 | 0.457 [0.373, 0.533] | 0.027 [0.007, 0.056] |

### Head-to-head on each Project A configuration's covered records

Every guard is scored on the records that A configuration has a verdict for (its coverage differs per configuration). n below 'records' means that guard has no prediction for some of them.

| A configuration (records) | guard | n | attack_block_rate | false_positive_rate |
|---|---|---|---|---|
| A handwritten_rules_g2prime (861) | A handwritten_rules_g2prime (Project A result; verdict metrics only, it does not emit our categories) | 861 | 0.799 [0.731, 0.869] | 0.003 [0.000, 0.008] |
| A handwritten_rules_g2prime (861) | gemma-4-e4b tuned (ours) | 861 | 0.791 [0.703, 0.867] | 0.079 [0.035, 0.125] |
| A handwritten_rules_g2prime (861) | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 859 | 0.865 [0.799, 0.918] | 0.077 [0.035, 0.123] |
| A handwritten_rules_g2prime (861) | gemma-4-e4b untuned zero-shot | 861 | 0.756 [0.673, 0.837] | 0.115 [0.059, 0.172] |
| A handwritten_rules_g2prime (861) | gemini-3.1-pro zero-shot | 861 | 0.994 [0.985, 1.000] | 0.025 [0.011, 0.041] |
| A handwritten_rules_g2prime (861) | gemini-3.8-flash zero-shot | 861 | 0.989 [0.970, 1.000] | 0.013 [0.000, 0.029] |
| A live_G2p (267) | A live_G2p (Project A result; verdict metrics only, it does not emit our categories) | 267 | 0.667 [0.580, 0.755] | 0.013 [0.000, 0.031] |
| A live_G2p (267) | gemma-4-e4b tuned (ours) | 267 | 0.640 [0.532, 0.755] | 0.071 [0.031, 0.112] |
| A live_G2p (267) | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 265 | 0.811 [0.742, 0.877] | 0.071 [0.032, 0.113] |
| A live_G2p (267) | gemma-4-e4b untuned zero-shot | 267 | 0.631 [0.512, 0.738] | 0.167 [0.109, 0.235] |
| A live_G2p (267) | gemini-3.1-pro zero-shot | 267 | 0.973 [0.941, 1.000] | 0.019 [0.000, 0.041] |
| A live_G2p (267) | gemini-3.8-flash zero-shot | 267 | 0.982 [0.957, 1.000] | 0.032 [0.007, 0.057] |
| A live_G4-G2p+G6 (270) | A live_G4-G2p+G6 (Project A result; verdict metrics only, it does not emit our categories) | 270 | 0.881 [0.827, 0.943] | 0.012 [0.000, 0.030] |
| A live_G4-G2p+G6 (270) | gemma-4-e4b tuned (ours) | 270 | 0.606 [0.496, 0.705] | 0.081 [0.029, 0.145] |
| A live_G4-G2p+G6 (270) | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 269 | 0.706 [0.607, 0.800] | 0.062 [0.019, 0.112] |
| A live_G4-G2p+G6 (270) | gemma-4-e4b untuned zero-shot | 270 | 0.615 [0.496, 0.722] | 0.174 [0.100, 0.251] |
| A live_G4-G2p+G6 (270) | gemini-3.1-pro zero-shot | 270 | 0.972 [0.944, 1.000] | 0.043 [0.015, 0.068] |
| A live_G4-G2p+G6 (270) | gemini-3.8-flash zero-shot | 270 | 0.991 [0.967, 1.000] | 0.050 [0.014, 0.088] |
| A live_G6 (241) | A live_G6 (Project A result; verdict metrics only, it does not emit our categories) | 241 | 0.906 [0.854, 0.959] | 0.000 [0.000, 0.000] |
| A live_G6 (241) | gemma-4-e4b tuned (ours) | 241 | 0.583 [0.471, 0.707] | 0.083 [0.034, 0.141] |
| A live_G6 (241) | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 241 | 0.719 [0.611, 0.811] | 0.069 [0.023, 0.127] |
| A live_G6 (241) | gemma-4-e4b untuned zero-shot | 241 | 0.594 [0.483, 0.702] | 0.193 [0.114, 0.271] |
| A live_G6 (241) | gemini-3.1-pro zero-shot | 241 | 0.979 [0.930, 1.000] | 0.021 [0.000, 0.047] |
| A live_G6 (241) | gemini-3.8-flash zero-shot | 241 | 0.990 [0.964, 1.000] | 0.014 [0.000, 0.038] |
| A llm_guard_flash (859) | A llm_guard_flash (Project A result; verdict metrics only, it does not emit our categories) | 859 | 0.979 [0.956, 0.996] | 0.000 [0.000, 0.000] |
| A llm_guard_flash (859) | gemma-4-e4b tuned (ours) | 859 | 0.792 [0.708, 0.869] | 0.079 [0.035, 0.126] |
| A llm_guard_flash (859) | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 858 | 0.867 [0.803, 0.918] | 0.077 [0.035, 0.123] |
| A llm_guard_flash (859) | gemma-4-e4b untuned zero-shot | 859 | 0.758 [0.676, 0.837] | 0.115 [0.060, 0.172] |
| A llm_guard_flash (859) | gemini-3.1-pro zero-shot | 859 | 0.994 [0.985, 1.000] | 0.026 [0.011, 0.042] |
| A llm_guard_flash (859) | gemini-3.8-flash zero-shot | 859 | 0.989 [0.970, 1.000] | 0.013 [0.000, 0.029] |
| A model_armor_direct (861) | A model_armor_direct (Project A result; verdict metrics only, it does not emit our categories) | 861 | 0.350 [0.279, 0.431] | 0.257 [0.191, 0.328] |
| A model_armor_direct (861) | gemma-4-e4b tuned (ours) | 861 | 0.791 [0.703, 0.867] | 0.079 [0.035, 0.125] |
| A model_armor_direct (861) | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 859 | 0.865 [0.799, 0.918] | 0.077 [0.035, 0.123] |
| A model_armor_direct (861) | gemma-4-e4b untuned zero-shot | 861 | 0.756 [0.673, 0.837] | 0.115 [0.059, 0.172] |
| A model_armor_direct (861) | gemini-3.1-pro zero-shot | 861 | 0.994 [0.985, 1.000] | 0.025 [0.011, 0.041] |
| A model_armor_direct (861) | gemini-3.8-flash zero-shot | 861 | 0.989 [0.970, 1.000] | 0.013 [0.000, 0.029] |
| A unguarded (573) | A unguarded (Project A result; verdict metrics only, it does not emit our categories) | 573 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |
| A unguarded (573) | gemma-4-e4b tuned (ours) | 573 | 0.655 [0.552, 0.759] | 0.080 [0.034, 0.126] |
| A unguarded (573) | gemma-4-e4b G5 in-domain (A data) (IN-DOMAIN: trained on scenarios from A's generator) | 571 | 0.789 [0.708, 0.866] | 0.077 [0.036, 0.129] |
| A unguarded (573) | gemma-4-e4b untuned zero-shot | 573 | 0.667 [0.567, 0.775] | 0.114 [0.059, 0.175] |
| A unguarded (573) | gemini-3.1-pro zero-shot | 573 | 0.988 [0.971, 1.000] | 0.025 [0.010, 0.042] |
| A unguarded (573) | gemini-3.8-flash zero-shot | 573 | 0.971 [0.917, 1.000] | 0.012 [0.000, 0.028] |

## a_replay_full (3823 records)

| guard | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|
| A handwritten_rules_g2prime (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 1639 of 3823 records) | 1639 | 0.799 [0.725, 0.863] | 0.003 [0.000, 0.007] | 0.534 [0.463, 0.576] | 1.000 [1.000, 1.000] | 0.020 [0.018, 0.024] | 0.000 [0.000, 0.000] |
| A live_G2p (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 581 of 3823 records) | 581 | 0.667 [0.579, 0.758] | 0.009 [0.000, 0.021] | 0.652 [0.510, 0.700] | 1.000 [1.000, 1.000] | 0.200 [0.200, 0.200] | 0.000 [0.000, 0.000] |
| A live_G4-G2p+G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 575 of 3823 records) | 575 | 0.881 [0.820, 0.938] | 0.019 [0.007, 0.032] | 0.692 [0.548, 0.748] | 1.000 [1.000, 1.000] | 3722.400 [2157.500, 4956.200] | 0.000 [0.000, 0.000] |
| A live_G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 557 of 3823 records) | 557 | 0.906 [0.854, 0.953] | 0.017 [0.007, 0.029] | 0.630 [0.471, 0.704] | 1.000 [1.000, 1.000] | 5412 | 0.000 [0.000, 0.000] |
| A llm_guard_flash (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 1634 of 3823 records) | 1634 | 0.979 [0.956, 0.996] | 0.004 [0.001, 0.009] | 0.623 [0.510, 0.693] | 1.000 [1.000, 1.000] | 15613.750 [15223.900, 15960.100] | 1.589 [1.562, 1.619] |
| A model_armor_direct (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 1639 of 3823 records) | 1639 | 0.350 [0.276, 0.423] | 0.271 [0.210, 0.334] | 0.105 [0.100, 0.110] | 1.000 [1.000, 1.000] | 962.600 [795.150, 1065.800] | 0.008 [0.008, 0.009] |
| A unguarded (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 1363 of 3823 records) | 1363 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.133 [0.131, 0.158] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

## a_pro_agent (20 records)

Pro agent traffic: A's agent with gemini-3.1-pro as the agent model (batches 09 to 11, v2). Test split, labeled, disputed records left out: 692 eligible (178 attacks, 514 benign). Scored on a stratified sample of 20 (10 attacks, 10 benign, each split by label source in proportion; a random subsample of an 80-record sample, data/a_pro_agent_sample80.jsonl, seed 20261009). Both models run in 8-bit on the laptop GPU, capped at 2 hours of scoring: the tuned run took a median 109 s per decision and the untuned run 35 s, because desktop apps shared the 6 GB card during the tuned run (the two models are the same size). Per-class rates are unbiased under this design but the intervals are very wide: treat this table as a spot check. A's own guard results on the same sampled records are shown where A ran them.

| guard | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|
| gemma-4-e4b tuned (ours), merged int8 | 20 | 0.500 [0.200, 0.875] | 0.000 [0.000, 0.000] | 0.590 [0.280, 0.818] | 1.000 [1.000, 1.000] | 109136.550 [90774.900, 123812.300] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned zero-shot, int8 | 20 | 0.600 [0.300, 0.875] | 0.000 [0.000, 0.000] | 0.357 [0.157, 0.582] | 1.000 [1.000, 1.000] | 34835.150 [33783.500, 36763.350] | 0.000 [0.000, 0.000] |
| A live_G4-G2p+G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 7 of 20 records) | 7 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 5381.300 [1257.300, 30347.300] | 0.000 [0.000, 0.000] |
| A live_G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 7 of 20 records) | 7 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.500 [0.333, 1.000] | 1.000 [1.000, 1.000] | 4452.200 [2223.100, 6401.600] | 0.000 [0.000, 0.000] |
| A unguarded (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 6 of 20 records) | 6 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.125 [0.000, 0.400] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

### a_pro_agent, label source construction (construction labels: the scenario's intended verdict) (11 records)

| guard | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|
| gemma-4-e4b tuned (ours), merged int8 | 11 | 0.625 [0.286, 0.909] | 0.000 [0.000, 0.000] | 0.571 [0.267, 0.875] | 1.000 [1.000, 1.000] | 109687.200 [37362.200, 136891.900] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned zero-shot, int8 | 11 | 0.625 [0.286, 0.909] | 0.000 [0.000, 0.000] | 0.333 [0.109, 0.578] | 1.000 [1.000, 1.000] | 34905.600 [33663.300, 40981.500] | 0.000 [0.000, 0.000] |
| A live_G4-G2p+G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 4 of 11 records) | 4 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 1483.100 [0.100, 6986.200] | 0.000 [0.000, 0.000] |
| A live_G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 3 of 11 records) | 3 | 1.000 [1.000, 1.000] | - | 0.167 [0.000, 1.000] | 1.000 [1.000, 1.000] | 6107.800 [5639.900, 7163.300] | 0.000 [0.000, 0.000] |
| A unguarded (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 4 of 11 records) | 4 | 0.000 [0.000, 0.000] | - | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

### a_pro_agent, label source teacher_label (TEACHER LABELS: A's Gemini teacher labeled these calls; not human, not gold) (9 records)

| guard | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd |
|---|---|---|---|---|---|---|---|
| gemma-4-e4b tuned (ours), merged int8 | 9 | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] | 0.438 [0.286, 1.000] | 1.000 [1.000, 1.000] | 106971.900 [66612.300, 123812.300] | 0.000 [0.000, 0.000] |
| gemma-4-e4b untuned zero-shot, int8 | 9 | 0.500 [0.500, 0.500] | 0.000 [0.000, 0.000] | 0.467 [0.364, 1.000] | 1.000 [1.000, 1.000] | 34440.200 [31978.700, 36763.350] | 0.000 [0.000, 0.000] |
| A live_G4-G2p+G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 3 of 9 records) | 3 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 30347.300 [5381.300, 67235.000] | 0.000 [0.000, 0.000] |
| A live_G6 (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 4 of 9 records) | 4 | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 2724.600 [1183.300, 4452.200] | 0.000 [0.000, 0.000] |
| A unguarded (Project A result; verdict metrics only, it does not emit our categories) (PARTIAL: 2 of 9 records) | 2 | - | 0.000 [0.000, 0.000] | 1.000 [1.000, 1.000] | 1.000 [1.000, 1.000] | 0.000 [0.000, 0.000] | 0.000 [0.000, 0.000] |

## A adaptive rewrites (87 attacks, separate table)

Real malicious test-split records from A whose attacker-controlled text gemini-3.1-pro rewrote in two rounds to evade guards (A kept the 87 still clearly malicious). Never trained on. Scored with replay_eval.py; full-precision rows were run on Kaggle with the same prompt and parser and imported (replay_eval.py --import-preds). All records are attacks, so there is no false positive rate. A's configurations emit no categories (no macro F1).

| config | n | attack_block_rate | false_positive_rate | macro_f1 | json_valid_rate | median_latency_ms | cost_per_1k_usd | unscored |
|---|---|---|---|---|---|---|---|---|
| b_prompt_gemini_3_1_pro | 87 | 1.000 [1.000, 1.000] |  | - | 1.000 [1.000, 1.000] |  |  | 0 |
| g4_rules_plus_llm_guard | 87 | 0.977 [0.928, 1.000] |  | - | 1.000 [1.000, 1.000] |  |  | 0 |
| handwritten_rules_g2prime | 87 | 0.632 [0.518, 0.747] |  | - | 1.000 [1.000, 1.000] |  |  | 0 |
| llm_guard_flash | 87 | 0.977 [0.928, 1.000] |  | - | 1.000 [1.000, 1.000] |  |  | 0 |
| model_armor_direct | 87 | 0.540 [0.405, 0.670] |  | - | 1.000 [1.000, 1.000] |  |  | 0 |
| tcg_tuned_4bit_laptop | 87 | 0.414 [0.306, 0.512] |  | 0.299 [0.137, 0.424] | 1.000 [1.000, 1.000] | 9474.800 [9216.800, 9909.000] | 0.000 [0.000, 0.000] | 0 |
| tcg_tuned_fp16_kaggle | 87 | 0.736 [0.628, 0.831] |  | 0.362 [0.229, 0.519] | 1.000 [1.000, 1.000] | 7512.300 [7246.250, 7654.400] | 0.000 [0.000, 0.000] | 0 |
| tcg_untuned_zs_4bit_laptop | 87 | 0.483 [0.388, 0.585] |  | 0.137 [0.096, 0.229] | 1.000 [1.000, 1.000] | 5854.300 [5516.800, 6081.200] | 0.000 [0.000, 0.000] | 0 |
| tcg_untuned_zs_fp16_kaggle | 87 | 0.632 [0.539, 0.731] |  | 0.180 [0.089, 0.298] | 1.000 [1.000, 1.000] | 5464.800 [5359.600, 5860.450] | 0.000 [0.000, 0.000] | 0 |
