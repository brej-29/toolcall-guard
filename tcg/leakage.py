"""Leakage check across splits. Fails loudly (exit 1) on any of:
- duplicate ids
- a stored split that differs from contract/split_v0.py (split assigned per record, or a family that became gold)
- a family_id present in more than one split
- a gold record, or anything derived from one, outside test
- an exact duplicate (normalized text hash) across splits, on the full record or on the scenario text alone
- a near duplicate across splits (MinHash LSH candidates confirmed by word 5-gram Jaccard >= threshold)

Usage: uv run python -m tcg.leakage data/a.jsonl data/b.jsonl [--threshold 0.8]
Run it before every upload and before every tuning job.
"""
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations

import numpy as np

from contract.split_v0 import assign_split, gold_families

NUM_PERM, BANDS = 64, 16  # 16 bands x 4 rows: candidate threshold about 0.5, confirmed by exact Jaccard
_rng = np.random.default_rng(20261005)
_A = _rng.integers(1, 2**63, NUM_PERM, dtype=np.uint64) | np.uint64(1)
_B = _rng.integers(0, 2**63, NUM_PERM, dtype=np.uint64)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def scenario_text(r: dict) -> str:
    """The part that distinguishes scenarios: conversation and proposed call. Policy and tool schemas are
    left out because many families legitimately share the same role template."""
    parts = [m["content"] + " " + json.dumps(m.get("tool_calls", []), sort_keys=True) for m in r["conversation"]]
    parts.append(r["proposed_call"]["name"] + " " + json.dumps(r["proposed_call"]["arguments"], sort_keys=True))
    return normalize("\n".join(parts))


def full_text(r: dict) -> str:
    return normalize(r["agent"]["policy"] + " " + (r["agent"].get("session_context") or "") + " "
                     + json.dumps(r["tools"], sort_keys=True) + " " + scenario_text(r))


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def shingles(text: str, n: int = 5) -> set:
    w = text.split()
    return {" ".join(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


def minhash(sh: set) -> np.ndarray:
    hs = np.fromiter((hash(s) & 0xFFFFFFFFFFFFFFFF for s in sh), dtype=np.uint64, count=len(sh))
    with np.errstate(over="ignore"):
        return (np.outer(hs, _A) + _B).min(axis=0)


def near_duplicate_pairs(texts: list[str], threshold: float = 0.8, groups: list | None = None) -> list:
    """Pairs (i, j, jaccard) with jaccard >= threshold. If groups is given, only pairs with different groups."""
    sh = [shingles(t) for t in texts]
    sigs = np.stack([minhash(s) for s in sh]) if sh else np.zeros((0, NUM_PERM), np.uint64)
    rows = NUM_PERM // BANDS
    cand = set()
    for b in range(BANDS):
        buckets = defaultdict(list)
        for i, sig in enumerate(sigs):
            buckets[sig[b * rows:(b + 1) * rows].tobytes()].append(i)
        for idx in buckets.values():
            for i, j in combinations(idx, 2):
                if groups is None or groups[i] != groups[j]:
                    cand.add((i, j))
    out = []
    for i, j in sorted(cand):
        jac = len(sh[i] & sh[j]) / len(sh[i] | sh[j])
        if jac >= threshold:
            out.append((i, j, round(jac, 3)))
    return out


def check(records: list[dict], threshold: float = 0.8) -> dict:
    problems = defaultdict(list)
    problems["duplicate_id"] = sorted(i for i, n in Counter(r["id"] for r in records).items() if n > 1)

    gold = gold_families(records)
    for r in records:
        want = assign_split(r["family_id"], gold)
        if r["split"] != want:
            problems["split_not_from_family_hash"].append(f'{r["id"]}: stored {r["split"]}, expected {want}')
        if r["family_id"] in gold and r["split"] != "test":
            problems["gold_or_gold_derived_outside_test"].append(r["id"])

    fam_splits = defaultdict(set)
    for r in records:
        fam_splits[r["family_id"]].add(r["split"])
    problems["family_crosses_splits"] = sorted(f for f, s in fam_splits.items() if len(s) > 1)

    for name, fn in (("exact_duplicate_full", full_text), ("exact_duplicate_scenario", scenario_text)):
        seen = defaultdict(set)
        for r in records:
            seen[text_hash(fn(r))].add((r["split"], r["id"]))
        for group in seen.values():
            if len({s for s, _ in group}) > 1:
                problems[name].append(sorted(i for _, i in group))

    texts = [scenario_text(r) for r in records]
    for i, j, jac in near_duplicate_pairs(texts, threshold, groups=[r["split"] for r in records]):
        problems["near_duplicate_cross_split"].append(f'{records[i]["id"]} ({records[i]["split"]}) ~ '
                                                      f'{records[j]["id"]} ({records[j]["split"]}) jaccard {jac}')
    report = {k: v for k, v in problems.items() if v}
    return {"ok": not report, "n_records": len(records), "n_families": len(fam_splits),
            "splits": {s: sum(r["split"] == s for r in records) for s in ("train", "val", "test")},
            "problems": report}


def load_jsonl(paths) -> list[dict]:
    out = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            out += [json.loads(line) for line in f if line.strip()]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--threshold", type=float, default=0.8)
    a = ap.parse_args(argv)
    rep = check(load_jsonl(a.paths), a.threshold)
    print(json.dumps({k: v for k, v in rep.items() if k != "problems"}))
    for k, v in rep["problems"].items():
        print(f"LEAKAGE {k}: {len(v)}", *v[:10], sep="\n  ")
    if not rep["ok"]:
        print("LEAKAGE CHECK FAILED", file=sys.stderr)
        return 1
    print("leakage check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
