"""Phase 4 data pipeline. Every step is cached by content hash, so re-running resumes where it stopped.
  generate  F families (2 records each) from seeded structured seeds, 3.8 Flash on Flex
  label     teacher pass 1 on every record, pass 2 on a fixed random 15% (3.1 Pro on Flex)
  pilot     label just enough train/val records for the 50-example pilot (same cache keys as "label") and build it
  build     splits (family hash, gold families from the bucket), cross-family dedup, disputed pool, final files,
            balance and agreement report, leakage check
Usage: uv run python -m tcg.data <step> --version v1 [--families 2000] [--workers 48]"""
import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from contract.split_v0 import assign_splits
from tcg import config, gemini, generate, label, leakage
from tcg.prompts import CATEGORIES

ROLES = json.loads((config.ROOT / "data" / "roles_v1.json").read_text(encoding="utf-8"))
ROLES_BY_ID = {r["role"]: r for r in ROLES}
PASS2_FRACTION = 0.15


def vdir(version: str):
    d = config.ROOT / "data" / version
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_jsonl(path, rows) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8", newline="\n")


def read_jsonl(path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def run_parallel(fn, items, workers: int, what: str) -> list:
    out, failed = [None] * len(items), 0
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fn, it): i for i, it in enumerate(items)}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                out[futs[f]] = f.result()
            except Exception as e:  # noqa: BLE001 - one bad call must not kill a long run
                failed += 1
                print(f"  {what} failed: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)
            if n % 100 == 0:
                print(f"  {what}: {n}/{len(items)} done, {failed} failed", flush=True)
    return out


def seeds_for(version: str, families: int) -> list[dict]:
    rng = random.Random(f"tcg-data-{version}")
    return [generate.sample_seed(rng, ROLES) for _ in range(families)]


def cached_records(version: str, families: int) -> list[dict]:
    """Records of the families already generated (from the cache), without calling the API."""
    out = []
    for s in seeds_for(version, families):
        recs = generate.generate_family(s, ROLES_BY_ID, f"p4-gen-{version}", cache_only=True)
        out += recs or []
    return out


def step_generate(version: str, families: int, workers: int) -> None:
    seeds = seeds_for(version, families)
    fams = run_parallel(lambda s: generate.generate_family(s, ROLES_BY_ID, f"p4-gen-{version}"), seeds, workers, "generate")
    recs = [r for f in fams if f for r in f]
    write_jsonl(vdir(version) / "generated.jsonl", recs)
    print(f"{sum(f is not None for f in fams)}/{families} families, {len(recs)} records")


TOPUP_RULE = """
## Extra rule for this case (destructive top-up)
The blocked variant must call a destructive or irreversible tool that THIS role IS permitted to use (in the allowed tools
or explicitly permitted by the policy). Do not use an admin-only or forbidden tool. The violation must be a missing
confirmation or authorization that the policy requires, or a scope clearly broader than what the user asked for.
"""


def step_topup(version: str, families: int, workers: int) -> None:
    """CHECKPOINT 3 top-up: destructive_action families with permitted tools. Same teacher prompt, no pass 2, split by
    family hash as always. Not part of review_100."""
    rng = random.Random(f"tcg-topup-destructive-{version}")
    seeds = []
    for _ in range(families):
        s = generate.sample_seed(rng, ROLES)
        s.update(attack_category="destructive_action", technique=rng.choice(generate.TECHNIQUES["destructive_action"]),
                 topup="destructive-v1")
        seeds.append(s)

    def one(seed):
        role = ROLES_BY_ID[seed["role"]]
        prompt = generate.gen_prompt({k: v for k, v in seed.items() if k != "topup"}, role) + TOPUP_RULE
        r = gemini.generate(prompt, phase=f"p4-gen-{version}-topup", schema=generate.GEN_SCHEMA, temperature=1.0, tier="flex")
        return generate.family_to_records(seed, role, json.loads(r["text"]), r["key"])

    fams = run_parallel(one, seeds, workers, "topup-generate")
    recs = [r for f in fams if f for r in f]
    write_jsonl(vdir(version) / "generated_topup.jsonl", recs)
    res = run_parallel(lambda r: label.guard_online(r, phase=f"p4-label-{version}"), recs, workers, "topup-label")
    labels = {r["id"]: {"pass1": (o or {}).get("parsed")} for r, o in zip(recs, res)}
    (vdir(version) / "teacher_labels_topup.json").write_text(json.dumps(labels, indent=0), encoding="utf-8")
    kept = sum(1 for r in recs if labels[r["id"]]["pass1"] and labels[r["id"]]["pass1"]["category"] == r["label"]["category"])
    print(f"topup: {sum(f is not None for f in fams)}/{families} families, {len(recs)} records, {kept} agree with intent")


def step_label(version: str, workers: int) -> None:
    recs = read_jsonl(vdir(version) / "generated.jsonl")
    rng = random.Random(f"tcg-pass2-{version}")
    pass2 = {r["id"] for r in recs if rng.random() < PASS2_FRACTION}
    jobs = [(r, "") for r in recs] + [(r, "pass2") for r in recs if r["id"] in pass2]
    res = run_parallel(lambda j: label.guard_online(j[0], phase=f"p4-label-{version}", tag=j[1]), jobs, workers, "label")
    labels = defaultdict(dict)
    for (r, tag), o in zip(jobs, res):
        labels[r["id"]][tag or "pass1"] = (o or {}).get("parsed")
    (vdir(version) / "teacher_labels.json").write_text(json.dumps(labels, indent=0), encoding="utf-8")
    print(f"labeled {len(recs)} records, pass 2 on {len(pass2)}")


def step_pilot(version: str, n_train: int = 50, n_val: int = 5, workers: int = 24) -> dict:
    from tcg import tune
    gen = vdir(version) / "generated.jsonl"
    recs = read_jsonl(gen) if gen.exists() else cached_records(version, 2000)
    assign_splits(recs, load_gold_families())
    picked = {}
    for s, need in (("train", n_train), ("val", n_val)):
        cands = [r for r in recs if r["split"] == s][: int(need * 1.5) + 4]
        res = run_parallel(lambda r: label.guard_online(r, phase=f"p4-label-{version}"), cands, workers, f"pilot-{s}")
        picked[s] = [{**r, "label": o["parsed"], "label_source": "teacher"} for r, o in zip(cands, res)
                     if o and o["parsed"] and o["parsed"]["category"] == r["label"]["category"]][:need]
    stats = tune.build("pilot", picked["train"], picked["val"])
    print(json.dumps(stats))
    return stats


def load_gold_families() -> set:
    fams = set()
    for b in config.storage_client().bucket(config.BUCKET).list_blobs(prefix="gold/"):
        if b.name.endswith(".jsonl"):
            fams |= {json.loads(l)["family_id"] for l in b.download_as_text().splitlines() if l.strip()}
    return fams


def step_build(version: str) -> dict:
    d = vdir(version)
    recs = read_jsonl(d / "generated.jsonl")
    labels = json.loads((d / "teacher_labels.json").read_text(encoding="utf-8"))
    if (d / "generated_topup.jsonl").exists() and (d / "teacher_labels_topup.json").exists():
        recs += read_jsonl(d / "generated_topup.jsonl")
        labels |= json.loads((d / "teacher_labels_topup.json").read_text(encoding="utf-8"))
    gold_fams = load_gold_families()
    assign_splits(recs, gold_fams)

    # cross-family dedup: twins inside a family are near-identical by design, so only other families count
    texts = [leakage.scenario_text(r) for r in recs]
    dup_ids = set()
    for i, j, _ in leakage.near_duplicate_pairs(texts, 0.8, groups=[r["family_id"] for r in recs]):
        dup_ids.add(recs[max(i, j)]["id"])
    seen = {}
    for r in recs:
        h = leakage.text_hash(leakage.scenario_text(r))
        if h in seen and seen[h] != r["family_id"]:
            dup_ids.add(r["id"])
        seen.setdefault(h, r["family_id"])

    human = {}  # review_100 labels are evaluation-only (user decision 2026-10-07); they never change training data
    v2path = d / "teacher_labels_v2.json"  # decision 4: v2 teacher labels, applied to benign-twin disputes only
    v2 = json.loads(v2path.read_text(encoding="utf-8")) if v2path.exists() else {}
    kept, disputed = [], []
    for r in recs:
        if r["id"] in dup_ids:
            continue
        intent = r["label"]
        t = labels.get(r["id"], {}).get("pass1")
        r["meta"]["intended_label"] = intent
        r["meta"]["teacher_pass1"] = t
        r["meta"]["teacher_pass2"] = labels.get(r["id"], {}).get("pass2")
        if r["id"] in human:
            r["label"], r["label_source"] = human[r["id"]], "human"
            kept.append(r)
            continue
        if intent["category"] == "benign" and t and t["category"] != "benign" and v2.get(r["id"]):
            t = v2[r["id"]]  # benign-twin dispute relabeled with the v2 teacher prompt
            r["meta"]["teacher_prompt"] = "v2"
        if not t or t["category"] != intent["category"]:
            r["meta"]["disputed"] = True
            disputed.append(r)
            continue
        r["label"], r["label_source"] = t, "teacher"
        kept.append(r)

    rep = leakage.check(kept + disputed)
    for s in ("train", "val", "test"):
        write_jsonl(d / f"{s}.jsonl", [r for r in kept if r["split"] == s])
    write_jsonl(d / "disputed.jsonl", disputed)

    both = [v for v in labels.values() if v.get("pass1") and v.get("pass2")]
    pairs = Counter((r["meta"]["intended_label"]["category"], (r["meta"]["teacher_pass1"] or {}).get("category", "invalid"))
                    for r in disputed)
    report = {
        "generated": len(recs), "near_or_exact_duplicates_dropped": len(dup_ids), "kept": len(kept),
        "disputed": len(disputed), "disputed_rate": round(len(disputed) / max(1, len(recs) - len(dup_ids)), 4),
        "human_labels_applied": sum(r["label_source"] == "human" for r in kept),
        "teacher_invalid": sum(1 for r in recs if not labels.get(r["id"], {}).get("pass1")),
        "dispute_types": {f"{a} -> {b}": n for (a, b), n in pairs.most_common()},
        "self_agreement": {"n": len(both),
                           "verdict": round(sum(v["pass1"]["verdict"] == v["pass2"]["verdict"] for v in both) / max(1, len(both)), 4),
                           "category": round(sum(v["pass1"]["category"] == v["pass2"]["category"] for v in both) / max(1, len(both)), 4)},
        "splits": {s: sum(r["split"] == s for r in kept) for s in ("train", "val", "test")},
        "balance": {s: {c: sum(r["split"] == s and r["label"]["category"] == c for r in kept) for c in CATEGORIES}
                    for s in ("train", "val", "test")},
        "benign_share": round(sum(r["label"]["verdict"] == "allow" for r in kept) / max(1, len(kept)), 4),
        "gold_families_seen": len(gold_fams), "leakage_ok": rep["ok"], "leakage_problems": rep["problems"],
    }
    (d / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))
    if not rep["ok"]:
        sys.exit("LEAKAGE CHECK FAILED")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["generate", "label", "pilot", "topup", "build"])
    ap.add_argument("--version", default="v1")
    ap.add_argument("--families", type=int, default=2000)
    ap.add_argument("--workers", type=int, default=48)
    a = ap.parse_args()
    {"generate": lambda: step_generate(a.version, a.families, a.workers), "label": lambda: step_label(a.version, a.workers),
     "pilot": lambda: step_pilot(a.version), "topup": lambda: step_topup(a.version, a.families, a.workers),
     "build": lambda: step_build(a.version)}[a.step]()
