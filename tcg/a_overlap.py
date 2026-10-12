"""Exact-content overlap between Project A's train and val records and every evaluation set.
Key: SHA-256 of the normalized conversation context plus proposed call (leakage.scenario_text). A's train and val
records = the scenario files G5 trained on plus the replay records with split train or val in A's final files.
Writes results/a_overlap.json. Usage: uv run python -m tcg.a_overlap"""
import json
from collections import defaultdict

from tcg import config, leakage
from tcg.data import read_jsonl

D = config.ROOT / "data"


def a_final_replay() -> list[dict]:
    final = json.loads((D / "a" / "replay" / "_final.json").read_text(encoding="utf-8"))
    recs = {}
    for f in final["files"]:
        if not f.get("superseded_by"):
            for r in read_jsonl(D / "a" / f["file"]):
                recs[r["id"]] = r  # later file wins, as in evaluate.fetch_a
    return list(recs.values())


def main() -> dict:
    replay = a_final_replay()
    g5_ids = set(json.loads((D / "tuning" / "g5" / "train_ids.json").read_text())) | set(
        json.loads((D / "tuning" / "g5" / "val_ids.json").read_text()))
    sources = {"A scenarios (G5 training data)": read_jsonl(D / "a" / "scenarios" / "a_generated_v1_train.jsonl")
               + read_jsonl(D / "a" / "scenarios" / "a_generated_v1_val.jsonl"),
               "A replay train+val": [r for r in replay if r["split"] in ("train", "val")]}
    targets = {"B synthetic_test": read_jsonl(D / "v1" / "test.jsonl"), "review_100": read_jsonl(D / "v1" / "review_eval.jsonl"),
               "ood": read_jsonl(D / "ood" / "ood_v1.jsonl"), "a_gold": read_jsonl(D / "a_gold.jsonl"),
               "A replay test (all, incl. unlabeled)": [r for r in replay if r["split"] == "test"]}
    eval_ids = {r["id"] for r in read_jsonl(D / "a_replay_eval.jsonl")}
    index = defaultdict(list)
    for s, recs in sources.items():
        for r in recs:
            index[leakage.text_hash(leakage.scenario_text(r))].append((s, r))
    report = {"key": "sha256(normalized conversation + proposed call)", "sources": {s: len(v) for s, v in sources.items()},
              "targets": {t: len(v) for t, v in targets.items()}, "matches": {}, "pairs": []}
    for t, recs in targets.items():
        for r in recs:
            for s, x in index.get(leakage.text_hash(leakage.scenario_text(r)), []):
                report["pairs"].append({"target": t, "test_id": r["id"], "test_family": r["family_id"], "source": s,
                                        "train_id": x["id"], "train_family": x["family_id"], "train_split": x["split"],
                                        "in_g5_training": x["id"] in g5_ids, "in_a_replay_eval_sample": r["id"] in eval_ids,
                                        "same_label": (r.get("label") or {}).get("verdict") == (x.get("label") or {}).get("verdict")})
    for t in targets:
        for s in sources:
            p = [x for x in report["pairs"] if x["target"] == t and x["source"] == s]
            report["matches"][f"{t} vs {s}"] = {"pairs": len(p), "test_records": len({x["test_id"] for x in p}),
                                               "in_a_replay_eval_sample": len({x["test_id"] for x in p if x["in_a_replay_eval_sample"]})}
    (config.ROOT / "results" / "a_overlap.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "pairs"}, indent=1))
    return report


if __name__ == "__main__":
    main()
