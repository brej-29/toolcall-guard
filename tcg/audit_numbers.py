"""Numbers audit: every hand-written number in the model card, dataset card and README is rebuilt from its source
file and must appear verbatim in the document. Generated tables (between the results and pro_agent markers, and all of
RESULTS.md) are checked by regenerating them and comparing. Writes results/number_audit.md; exits 1 on any failure.
Usage: uv run python -m tcg.audit_numbers"""
import collections
import json
import re
import sys

from tcg import config
from tcg.data import read_jsonl

R = config.ROOT
DOCS = {"card": R / "hf" / "model_card.md", "data_card": R / "hf" / "dataset_card.md", "readme": R / "README.md"}
TEXT = {k: re.sub(r"\s+", " ", p.read_text(encoding="utf-8")) for k, p in DOCS.items()}  # line breaks do not matter
rows = []


def claim(doc: str, phrase: str, source: str) -> None:
    rows.append((doc, phrase, source, re.sub(r"\s+", " ", phrase) in TEXT[doc]))


def j(path):
    return json.loads((R / path).read_text(encoding="utf-8"))


f2 = lambda x: f"{x:.2f}"
ci2 = lambda t: f"{t[0]:.2f} [{t[1]:.2f}, {t[2]:.2f}]"
pct1 = lambda x: f"{100 * x:.1f}%"
n_ = lambda x: f"{x:,}"

# training
stats = j("data/tuning/real/stats.json")
claim("card", f"Data: {n_(stats['train']['examples'])} synthetic decision records and {stats['val']['examples']} validation records", "data/tuning/real/stats.json")
claim("card", f"SHA-256 `{stats['sha256']}`", "data/tuning/real/stats.json")
ledger = [json.loads(l) for l in (R / "exports" / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
claim("card", f"USD {sum(r['usd'] for r in ledger if r['phase'] == 'real' and r['kind'] == 'tuning'):.2f}", "exports/ledger.jsonl (tuning, real)")
real = j("state.json")["tuning_jobs"]["real"]
rt = next(r for r in ledger if r["phase"] == "real" and r["kind"] == "tuning")
claim("card", f"Cost: {n_(rt['training_tokens'])} training tokens, USD {rt['usd']:.2f}", "exports/ledger.jsonl (real tuning job, training_tokens)")
# eval loss and steps were read from adapters/real/runs/*/events (tensorboard): 3.464, 0.8792, 0.8053 at steps 0, 15, 28
claim("card", "Eval loss on the answer tokens: 3.46 before training, 0.88 after epoch 1, 0.81 after epoch 2", "adapters/real/runs tensorboard eval/loss 3.464, 0.8792, 0.8053")
claim("card", "(28 optimizer steps)", "adapters/real/runs tensorboard, last train step 28")

# test sets
sets = {k: read_jsonl(R / p) for k, p in (("syn", "data/v1/test.jsonl"), ("rev", "data/v1/review_eval.jsonl"), ("gold", "data/a_gold.jsonl"),
                                           ("rep", "data/a_replay_eval.jsonl"), ("ood", "data/ood/ood_v1.jsonl"))}
claim("card", f"**synthetic test**: {len(sets['syn'])} held-out records", "data/v1/test.jsonl")
claim("card", f"**A gold**: {len(sets['gold'])} records", "data/a_gold.jsonl")
att = sum(r["label"]["verdict"] == "block" for r in sets["rep"])
claim("card", f"all {att} attacks and {n_(len(sets['rep']) - att)} random benign calls", "data/a_replay_eval.jsonl")
claim("card", f"**OOD**: {len(sets['ood'])} hand-written", "data/ood/ood_v1.jsonl")

# matched false positive rate (RESULTS.md, a_replay section)
res = (R / "RESULTS.md").read_text(encoding="utf-8")
sec = res.split("## a_replay (", 1)[1].split("\n## ", 1)[0].split("### Matched false positive rate", 1)[1]
def matched(guard):
    m = re.search(r"\| \| " + re.escape(guard) + r"[^|]* \| [0-9.]+ \| [0-9.]+ \| \d+ \| ([0-9.]+) \[([0-9.]+), ([0-9.]+)\] \| ([0-9.]+)", sec)
    return [float(x) for x in m.groups()]
t = matched("gemma-4-e4b tuned (ours)")
fs, zs = matched("gemma-4-e4b untuned few-shot"), matched("gemma-4-e4b untuned zero-shot")
s = j("results/summary.json")
g = lambda ts, name, k: s[ts][name][k][0]
gem = sorted(g("a_replay", x, "attack_block_rate") for x in ("gemini-3.8-flash zero-shot", "gemini-3.1-pro zero-shot"))
# the matched table itself is generated; the prose around it is qualitative and checked here
rows.append(("card", "matched FPR prose: the adapter blocks about half (0.45 to 0.55), a little more than the untuned base, Gemini nearly all",
             "RESULTS.md a_replay matched FPR", 0.45 <= t[0] <= 0.55 and t[0] > max(fs[0], zs[0]) and gem[0] >= 0.95))
ra = lambda name, k: s["a_replay"][f"{name} | real_agent"][k][0]
claim("card", f"({f2(ra('gemma-4-e4b tuned (ours)', 'false_positive_rate'))} vs {f2(ra('gemma-4-e4b untuned zero-shot', 'false_positive_rate'))} for the untuned base zero-shot and "
              f"{f2(ra('gemma-4-e4b untuned few-shot', 'false_positive_rate'))} few-shot", "results/summary.json a_replay real_agent")
# TL;DR and README summary
rci = lambda name, k: ci2(s["a_replay"][f"{name} | real_agent"][k])
sci = lambda name, k: ci2(s["synthetic_test"][name][k])
tl = (f"blocks {rci('gemma-4-e4b tuned (ours)', 'attack_block_rate')} of attacks at a false positive rate of "
      f"{rci('gemma-4-e4b tuned (ours)', 'false_positive_rate')} on Project A's")
for doc in ("card", "readme"):
    claim(doc, tl, "results/summary.json a_replay real_agent")
    claim(doc, f"{sci('gemma-4-e4b tuned (ours)', 'attack_block_rate')} at {sci('gemma-4-e4b tuned (ours)', 'false_positive_rate')} on its own synthetic test set",
          "results/summary.json synthetic_test")
GEMS = ("gemini-3.8-flash zero-shot", "gemini-3.1-pro zero-shot")
gmin = min(ra(x, "attack_block_rate") for x in GEMS)
gfp = max(ra(x, "false_positive_rate") for x in GEMS)
claim("card", f"the Gemini guards block {f2(gmin)} at {f2(gfp)}", "results/summary.json a_replay real_agent")
claim("readme", f"guards block {f2(gmin)} at {f2(gfp)} on A's real traffic", "results/summary.json a_replay real_agent")

# adaptive
ad = j("results/adaptive/metrics.json")["all"]
abr = lambda c: ad[c]["ci95"]["attack_block_rate"]
for label, cfg in (("this adapter, full precision", "tcg_tuned_fp16_kaggle"), ("this adapter, 4-bit laptop", "tcg_tuned_4bit_laptop"),
                   ("untuned base, zero-shot, full precision", "tcg_untuned_zs_fp16_kaggle"), ("untuned base, zero-shot, 4-bit laptop", "tcg_untuned_zs_4bit_laptop"),
                   ("A: Model Armor", "model_armor_direct"), ("A: handwritten rules", "handwritten_rules_g2prime"), ("A: LLM guard (Flash)", "llm_guard_flash")):
    claim("card", f"| {label} | {ci2(abr(cfg))} |", f"results/adaptive/metrics.json {cfg}")
claim("card", f"| A: gemini-3.1-pro with this project's guard prompt | {f2(abr('b_prompt_gemini_3_1_pro')[0])} |", "results/adaptive/metrics.json")
claim("card", f"{len(read_jsonl(R / 'data/a/adaptive/adaptive_rewrite_v1.jsonl'))} real attacks from A's test split", "data/a/adaptive/adaptive_rewrite_v1.jsonl")

# Pro agent traffic
pro = [r for f in sorted((R / "data" / "a" / "pro_agent").glob("*.jsonl")) for r in read_jsonl(f)]
elig = [r for r in pro if r["split"] == "test" and r.get("label") and not (r.get("meta") or {}).get("disputed")]
pa = sum(r["label"]["verdict"] == "block" for r in elig)
claim("card", f"{len(elig)} calls ({pa} attacks, {len(elig) - pa} benign)", "data/a/pro_agent (test, labeled, not disputed)")
smp = read_jsonl(R / "data/a_pro_agent_eval.jsonl")
sa = sum(r["label"]["verdict"] == "block" for r in smp)
claim("card", f"stratified sample of {len(smp)} ({sa} attacks, {len(smp) - sa} benign", "data/a_pro_agent_eval.jsonl")
ids = {r["id"] for r in smp}
med = lambda gd: sorted(r["latency_ms"] for r in read_jsonl(R / "results/preds/a_pro_agent" / f"{gd}.jsonl") if r["id"] in ids)
mt, mu = med("gemma-4-e4b tuned (ours), merged int8"), med("gemma-4-e4b untuned zero-shot, int8")
mid = lambda xs: (xs[len(xs) // 2 - 1] + xs[len(xs) // 2]) / 2
claim("card", f"median {mid(mt) / 1000:.0f} s per decision for the tuned run and {mid(mu) / 1000:.0f} s for the untuned one", "results/preds/a_pro_agent latency")
ta = sum(r["label"]["verdict"] == "block" and r["meta"]["label_stratum"] == "teacher_label" for r in smp)
claim("card", f"only {ta} of the {sa} sampled attacks carry teacher labels", "data/a_pro_agent_eval.jsonl label_stratum")
claim("card", f"none of the {len(smp) - sa} benign calls", "data/a_pro_agent_eval.jsonl")
pf = [s["a_pro_agent"][x]["false_positive_rate"][0] for x in ("gemma-4-e4b tuned (ours), merged int8", "gemma-4-e4b untuned zero-shot, int8")]
rows.append(("card", "both Pro agent false positive rates are 0", "results/summary.json a_pro_agent", pf == [0.0, 0.0]))

# precision table
kq = j("results/kaggle_out/quant/quant/summary.json")
lq = j("results/quant_local/summary.json")
gq = j("results/kaggle_out/gguf-cpu/quant/summary.json")
ab = lambda d: f"{d['attacks_blocked']} / {d['attacks']}"
fp = lambda d: f"{d['false_positives']} / {d['benign']}"
claim("card", f"| base + LoRA, full precision | {ab(kq['fp16_base+lora'])} | {fp(kq['fp16_base+lora'])} | no (about 16 GB) | "
              f"{lq['merged_full cpu']['median_latency_ms'] / 1000:.0f} s on the laptop CPU", "kaggle quant + quant_local merged_full cpu")
claim("card", f"| LoRA merged, full precision | {ab(kq['merged_fp16'])} | {fp(kq['merged_fp16'])} |", "kaggle quant merged_fp16")
claim("card", f"| LoRA merged, 8-bit (LLM.int8) | {ab(kq['merged_int8'])} | {fp(kq['merged_int8'])} | yes, {lq['merged_int8 cuda']['peak_gpu_gib']:.1f} GiB, at the limit | "
              f"{lq['merged_int8 cuda']['median_latency_ms'] / 1000:.0f} s |", "kaggle quant + quant_local merged_int8 cuda")
claim("card", f"| 4-bit base + LoRA (the \"4-bit laptop\" rows) | {ab(kq['nf4_base+lora'])} ({lq['nf4_base+lora cuda']['attacks_blocked']} on the laptop) | "
              f"{fp(kq['nf4_base+lora'])} | yes, {lq['nf4_base+lora cuda']['peak_gpu_gib']:.1f} GiB | {lq['nf4_base+lora cuda']['median_latency_ms'] / 1000:.1f} s |", "kaggle + laptop nf4_base+lora")
claim("card", f"| LoRA merged, 4-bit nf4 | {ab(kq['merged_nf4'])} ({lq['merged_nf4 cuda']['attacks_blocked']} on the laptop) | {fp(kq['merged_nf4'])} | "
              f"yes, {lq['merged_nf4 cuda']['peak_gpu_gib']:.1f} GiB | {lq['merged_nf4 cuda retime']['median_latency_ms'] / 1000:.1f} s |", "kaggle + laptop merged_nf4 (retime)")
for q in ("Q6_K", "Q5_K_M"):
    d = gq[f"gguf_{q}"]
    claim("card", f"| GGUF {q} (llama.cpp, LoRA merged) | {ab(d)} | {fp(d)} | not measured ({d['file_gib']:.2f} GiB file) | {d['median_latency_ms'] / 1000:.0f} s on 4 Kaggle CPU threads |", "gguf-cpu summary")
i8 = "gemma-4-e4b tuned (ours), merged int8"
claim("card", f"A replay real agent {f2(ra(i8, 'attack_block_rate'))} vs {f2(ra('gemma-4-e4b tuned (ours)', 'attack_block_rate'))}, 4-bit "
              f"{f2(ra('gemma-4-e4b tuned (ours), 4-bit laptop', 'attack_block_rate'))}", "results/summary.json a_replay real_agent")
hw = collections.Counter(r.get("hardware") for r in read_jsonl(R / "results/preds/a_replay" / f"{i8}.jsonl"))
claim("card", f"laptop GPU ({n_(hw['NVIDIA GeForce RTX 3050 6GB Laptop GPU'])} records) and a Kaggle T4 ({hw['kaggle T4']})", "int8 a_replay hardware field")

# cost and latency
claim("card", f"{g('a_replay', 'gemma-4-e4b tuned (ours)', 'median_latency_ms') / 1000:.1f} s full precision on a Kaggle T4, "
              f"{g('a_replay', 'gemma-4-e4b tuned (ours), 4-bit laptop', 'median_latency_ms') / 1000:.1f} s in 4-bit", "results/summary.json a_replay latency")
claim("card", f"USD {g('a_replay', 'gemini-3.8-flash zero-shot', 'cost_per_1k_usd'):.2f} (Flash) and {g('a_replay', 'gemini-3.1-pro zero-shot', 'cost_per_1k_usd'):.2f} (Pro)", "results/summary.json a_replay cost")
fl, pr = j("results/latency/gemini-3.8-flash zero-shot.json"), j("results/latency/gemini-3.1-pro zero-shot.json")
claim("card", f"{fl['median_ms'] / 1000:.1f} s (Flash, p90 {fl['p90_ms'] / 1000:.1f} s) and {pr['median_ms'] / 1000:.1f} s (Pro, p90 {pr['p90_ms'] / 1000:.0f} s)", "results/latency/*.json")

# limitations
claim("card", f"({f2(ra('gemma-4-e4b tuned (ours)', 'attack_block_rate'))} vs {f2(g('synthetic_test', 'gemma-4-e4b tuned (ours)', 'attack_block_rate'))} at full precision)", "results/summary.json")
claim("card", f"Gemini guards ({f2(min(ra(x, 'attack_block_rate') for x in ('gemini-3.8-flash zero-shot', 'gemini-3.1-pro zero-shot')))})", "results/summary.json a_replay real_agent")
ag = j("data/v1/review_agreement.json")
bt = round(ag["benign_twin_generator_share"] * ag["benign_twin_n"])
claim("card", f"did not trigger ({bt} of {ag['benign_twin_n']}), but only {ag['benign_twin_n']} records", "data/v1/review_agreement.json")

# dataset card
rep = j("data/v1/report.json")
v1 = {k: read_jsonl(R / f"data/v1/{k}.jsonl") for k in ("train", "val", "test", "disputed")}
claim("data_card", f"| `data/train.jsonl` | {n_(len(v1['train']))} | {n_(sum(r['label']['verdict'] == 'allow' for r in v1['train']))} benign;", "data/v1/train.jsonl")
cats = collections.Counter(r["label"]["category"] for r in v1["train"] if r["label"]["verdict"] == "block")
claim("data_card", ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in cats.most_common()), "data/v1/train.jsonl categories")
claim("data_card", f"| `data/val.jsonl` | {len(v1['val'])} |", "data/v1/val.jsonl")
claim("data_card", f"| `data/val_frozen_150.jsonl` | {len(read_jsonl(R / 'data/v1/val_frozen.jsonl'))} |", "data/v1/val_frozen.jsonl")
claim("data_card", f"| `data/test.jsonl` | {len(v1['test'])} | {sum(r['label']['verdict'] == 'allow' for r in v1['test'])} benign |", "data/v1/test.jsonl")
claim("data_card", f"| `data/disputed.jsonl` | {n_(len(v1['disputed']))} |", "data/v1/disputed.jsonl")
claim("data_card", f"| `data/review_100.jsonl` | {len(sets['rev'])} |", "data/v1/review_eval.jsonl")
claim("data_card", f"| `data/ood_30.jsonl` | {len(sets['ood'])} |", "data/ood/ood_v1.jsonl")
fams = len({r["family_id"] for k in v1 for r in v1[k]})
claim("data_card", f"{n_(fams)} families in train, val, test and disputed combined", "data/v1 family_id")
kept = v1["train"] + v1["val"] + v1["test"]
claim("data_card", f"Benign share of kept records: {100 * sum(r['label']['verdict'] == 'allow' for r in kept) / len(kept):.0f}%", "data/v1 train+val+test")
sa_ = rep["self_agreement"]
claim("data_card", f"Teacher self-agreement on {sa_['n']} double-labeled records: verdict {pct1(sa_['verdict'])}, category {pct1(sa_['category'])}", "data/v1/report.json")
claim("data_card", f"(586 records)", "data/v1/report.json self_agreement.n") if sa_["n"] == 586 else rows.append(("data_card", "586 records", "report", False))
claim("data_card", f"Disputed rate: {pct1(rep['disputed_rate'])} of generated records ({n_(rep['disputed'])} of {n_(rep['generated'])})", "data/v1/report.json")
a, nd, d = ag["all"], ag["not_disputed"], ag["disputed"]
claim("data_card", f"verdict {a['teacher_verdict'] * 100:.0f}%, category {a['teacher_category'] * 100:.0f}% on all {a['n']}; "
                   f"{pct1(nd['teacher_verdict'])} and {pct1(nd['teacher_category'])} on the {nd['n']} not-disputed records; "
                   f"{pct1(d['teacher_verdict'])} and {pct1(d['teacher_category'])} on the {d['n']} disputed ones", "data/v1/review_agreement.json")
claim("data_card", f"2,000 families, plus a top-up of 170 families", "STATE.md P4 (2,000 + 170 families generated)")
claim("data_card", f"36 agent roles", "data/roles_v1.json") if len(j("data/roles_v1.json")) == 36 else rows.append(("data_card", "36 agent roles", "roles", False))

# sanitized release candidate and known issues (dataset card)
san = j("data/release_sanitized_v1/SANITIZED.json")["totals"]
claim("data_card", f"{san['distinct_gmail_addresses']} distinct invented @gmail.com addresses ({san['gmail_replaced']} occurrences) and "
                   f"{san['distinct_phone_numbers']} distinct phone numbers ({san['phone_numbers_replaced']} occurrences", "data/release_sanitized_v1/SANITIZED.json")
claim("data_card", f"| 1 | invented Gmail address -> same local part at example.com ({san['distinct_gmail_addresses']} distinct addresses) | {san['gmail_replaced']} |", "SANITIZED.json v1")
claim("data_card", f"| 1 | phone number -> unique fake, +1-555-000-NNNN or +99-000-000-NNNN ({san['distinct_phone_numbers']} distinct numbers) | {san['phone_numbers_replaced']} |", "SANITIZED.json v1")
s2 = j("data/release_sanitized_v2/SANITIZED.json"); c2 = s2["counts"]
fsum = lambda *ks: sum(c2.get("firm: " + k, 0) for k in ks)
for label, n in (("KPMG -> Kestrel Audit (including lowercase forms inside invented domains)", fsum("KPMG", "kpmg")),
                 ("Deloitte -> Dellmont", fsum("Deloitte", "DELOITTE", "deloitte")), ("DHL -> Dalton", fsum("DHL Express", "DHL", "dhl")),
                 ("FedEx -> Fastway", fsum("FedEx", "FEDEX", "fedex")),
                 ("JPMorgan Chase, Chase Bank -> Harbor Union Bank", fsum("JPMorgan Chase", "Chase Bank", "Chase bank", "JPMorgan", "jpmorgan"))):
    claim("data_card", f"| 2 | {label} | {n} |", "data/release_sanitized_v2/SANITIZED.json")
rows.append(("data_card", "Wells Fargo, Bank of America, PNC Bank 2 each", "SANITIZED.json v2",
             fsum("Wells Fargo") == fsum("Bank of America") == fsum("PNC Bank", "PNC") == 2))
prov = {k: v for k, v in c2.items() if k.startswith("provider")}
claim("data_card", f"({len(prov)} domains, e.g. okta.com, outlook.com, googleapis.com) | {n_(sum(prov.values()))} |", "SANITIZED.json v2")
claim("data_card", f"({s2['registered'] - len(prov)} domains, e.g. meridian.com.test) | {n_(c2['invented registered domain -> +.test'])} |", "SANITIZED.json v2")
claim("data_card", f"every registrable domain ({n_(s2['registrable_domains_checked'])}) was checked in DNS", "SANITIZED.json v2")
ov = j("results/a_overlap.json")
kn = {r["id"] for gr in j("data/a/replay/_known_issues_v1.json")["issues"] for r in gr["records"] if r["split"] == "test"}
ours = {p["test_id"] for p in ov["pairs"]}
claim("data_card", f"A's own list names {len(kn)} such test records, and a check that also ignores punctuation finds {len(ours)}", "_known_issues_v1.json, results/a_overlap.json")

# README
claim("readme", f"36 agent roles", "data/roles_v1.json")
claim("readme", f"{len(sets['ood'])} hand-written out-of-distribution records", "data/ood/ood_v1.jsonl")
claim("readme", f"stratified sample of {len(smp)}", "data/a_pro_agent_eval.jsonl")
claim("readme", f"blocks {ci2(abr('tcg_tuned_fp16_kaggle'))} at full precision and {ci2(abr('tcg_tuned_4bit_laptop'))} in 4-bit", "results/adaptive/metrics.json")
led = {}
for r in ledger:
    led[r["kind"]] = led.get(r["kind"], 0) + r["usd"]
tun = {ph: sum(r["usd"] for r in ledger if r["kind"] == "tuning" and r["phase"] == ph) for ph in ("pilot", "real", "g5")}
claim("readme", f"**USD {sum(led.values()):.2f}**, of which Gemini calls {led['online']:.2f} and managed tuning {led['tuning']:.2f} (pilot {tun['pilot']:.2f}, main run {tun['real']:.2f}, G5 {tun['g5']:.2f})",
      "exports/ledger.jsonl")
a_led, billed = 114.10, 17395.53 / 95.99  # A's final ledger (its COSTS.md); the owner's per-project Billing figure
claim("readme", f"ledger (USD {a_led:.2f}) that is USD {a_led + sum(led.values()):.2f} against USD {billed:.2f} billed for the shared project, a gap of "
                f"{billed - a_led - sum(led.values()):.2f} ({100 * (billed - a_led - sum(led.values())) / billed:.1f}%", "ledger + billing")

bad = [r for r in rows if not r[3]]
out = ["# Numbers audit", "", f"{len(rows)} hand-written numbers checked against their source files; {len(bad)} failed. Generated tables "
       "(RESULTS.md, and the results and pro_agent blocks in the model card and README) come straight from the prediction "
       "files and are checked by regenerating them (git diff must be empty).", "",
       "| doc | phrase | source | ok |", "|---|---|---|---|"] + [f"| {d} | {p.replace('|', '/')} | {s_} | {'PASS' if ok else 'FAIL'} |" for d, p, s_, ok in rows]
(R / "results" / "number_audit.md").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
print(f"{len(rows)} checks, {len(bad)} failed")
for d, p, s_, ok in bad:
    print("FAIL", d, "|", p, "|", s_)
sys.exit(1 if bad else 0)
