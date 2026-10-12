"""Toolcall Guard contract v0: reference split assignment. Stdlib only, copy it as is.

Rules:
1. split depends on family_id only, through a stable salted hash. Never assign split per record.
2. A gold record (source a_gold) and everything derived from it, directly or transitively (derived_from), is
   test, and so is every other record in the same family.
3. Leakage across splits (family_id, exact duplicates, near-duplicates) is checked by tcg/leakage.py in the
   toolcall-guard repo before every upload and every tuning job.

Immutable once published. Changes go into split_v1.py with a new SALT.
"""
import hashlib

SALT = "toolcall-guard-split-v0"
TEST_FRACTION = 0.15
VAL_FRACTION = 0.05  # val families are never test families; B builds the tuning validation file from them


def family_bucket(family_id: str) -> float:
    """Uniform in [0, 1), stable across machines and Python versions."""
    return int(hashlib.sha256(f"{SALT}:{family_id}".encode("utf-8")).hexdigest()[:15], 16) / 16**15


def assign_split(family_id: str, gold_family_ids=frozenset()) -> str:
    if family_id in gold_family_ids:
        return "test"
    b = family_bucket(family_id)
    if b < TEST_FRACTION:
        return "test"
    if b < TEST_FRACTION + VAL_FRACTION:
        return "val"
    return "train"


def gold_families(records) -> set:
    """Families that contain a gold record or anything derived from one (transitively)."""
    tainted = {r["id"] for r in records if r["source"] == "a_gold"}
    grew = True
    while grew:
        new = {r["id"] for r in records if r.get("derived_from") in tainted} - tainted
        tainted |= new
        grew = bool(new)
    return {r["family_id"] for r in records if r["id"] in tainted}


def assign_splits(records, extra_gold_family_ids=frozenset()) -> None:
    """Set record["split"] in place. Pass every record you have (gold included) so derivations are seen.
    extra_gold_family_ids: gold families known from elsewhere, e.g. the gold/ folder in the bucket."""
    gold = gold_families(records) | set(extra_gold_family_ids)
    for r in records:
        r["split"] = assign_split(r["family_id"], gold)


if __name__ == "__main__":
    assert assign_split("fam-a") == assign_split("fam-a")
    assert assign_split("anything", {"anything"}) == "test"
    recs = [{"id": "g1", "family_id": "f1", "source": "a_gold"},
            {"id": "d1", "family_id": "f2", "source": "b_synthetic", "derived_from": "g1"},
            {"id": "d2", "family_id": "f3", "source": "b_synthetic", "derived_from": "d1"},
            {"id": "x", "family_id": "f3", "source": "b_synthetic"}]
    assign_splits(recs)
    assert all(r["split"] == "test" for r in recs), recs
    print("split_v0 self-check ok")
