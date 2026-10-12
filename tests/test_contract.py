import copy
import json
from pathlib import Path

import jsonschema
import pytest

from contract.split_v0 import assign_split, assign_splits, family_bucket
from tcg import leakage

C = Path(__file__).resolve().parent.parent / "contract"
SCHEMA = json.loads((C / "schema_v0.json").read_text(encoding="utf-8"))
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)
EXAMPLES = leakage.load_jsonl([C / "examples_v0.jsonl"])


def fam_in(split: str, prefix: str = "fam") -> str:
    """First family id of the form prefix-N that hashes to the wanted split."""
    return next(f"{prefix}-{i}" for i in range(10_000) if assign_split(f"{prefix}-{i}") == split)


def make(id_, fam, text, source="b_synthetic"):
    r = copy.deepcopy(EXAMPLES[0])
    r.update(id=id_, family_id=fam, source=source)
    r["conversation"] = [{"role": "user", "content": text}]
    return r


LONG = " ".join(f"word{i}" for i in range(200))


# schema ----------------------------------------------------------------------------------------------------

def test_schema_is_valid_and_examples_pass():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)
    for r in EXAMPLES:
        VALIDATOR.validate(r)


@pytest.mark.parametrize("mutate", [
    lambda r: r["label"].update(verdict="allow", category="data_exfiltration"),   # allow must be benign
    lambda r: r["label"].update(verdict="block", category="benign"),              # block must not be benign
    lambda r: r.update(source="a_gold", label_source="human", split="train"),     # gold is test only
    lambda r: r.update(label_source="none"),                                      # unlabeled needs label null
    lambda r: r["conversation"].append({"role": "tool", "content": "x"}),         # tool message needs name
    lambda r: r.update(unexpected_field=1),                                       # extras go in meta
])
def test_schema_rejects(mutate):
    r = copy.deepcopy(EXAMPLES[0])
    mutate(r)
    assert list(VALIDATOR.iter_errors(r))


# split -----------------------------------------------------------------------------------------------------

def test_split_is_stable_and_proportional():
    assert family_bucket("fam-0") == family_bucket("fam-0")
    splits = [assign_split(f"f{i}") for i in range(20_000)]
    assert abs(splits.count("test") / 20_000 - 0.15) < 0.01
    assert abs(splits.count("val") / 20_000 - 0.05) < 0.01


def test_split_ignores_everything_but_family():
    a, b = make("a", "same-fam", "one text"), make("b", "same-fam", "a completely different text")
    assign_splits([a, b])
    assert a["split"] == b["split"]


def test_gold_family_and_derivations_are_test():
    fam = fam_in("train")
    gold = make("g", fam, "gold text", source="a_gold")
    sibling = make("s", fam, "same family as gold")
    child = make("c", fam_in("train", "other"), "derived")
    child["derived_from"] = "g"
    grandchild = make("gc", fam_in("train", "third"), "derived twice")
    grandchild["derived_from"] = "c"
    recs = [gold, sibling, child, grandchild]
    assign_splits(recs)
    assert {r["split"] for r in recs} == {"test"}


# leakage ---------------------------------------------------------------------------------------------------

def clean_set():
    recs = [make("t1", fam_in("train"), "alpha " + LONG), make("t2", fam_in("train", "x"), "totally unrelated beta text"),
            make("e1", fam_in("test"), "gamma request about something else entirely")]
    assign_splits(recs)
    return recs


def test_leakage_passes_on_clean_set():
    rep = leakage.check(clean_set())
    assert rep["ok"], rep["problems"]


def test_leakage_catches_family_crossing_splits():
    recs = clean_set()
    recs[1]["family_id"] = recs[0]["family_id"]
    recs[1]["split"] = "test"
    assert "family_crosses_splits" in leakage.check(recs)["problems"]


def test_leakage_catches_split_not_from_hash():
    recs = clean_set()
    recs[0]["split"] = "test"
    assert "split_not_from_family_hash" in leakage.check(recs)["problems"]


def test_leakage_catches_exact_duplicate_across_splits():
    recs = clean_set() + [make("e2", fam_in("test", "y"), "alpha " + LONG)]
    assign_splits(recs)
    assert "exact_duplicate_scenario" in leakage.check(recs)["problems"]


def test_leakage_catches_near_duplicate_across_splits():
    near = "alpha " + LONG.replace("word100", "changed").replace("word150", "edited")
    recs = clean_set() + [make("e2", fam_in("test", "y"), near)]
    assign_splits(recs)
    probs = leakage.check(recs)["problems"]
    assert "near_duplicate_cross_split" in probs and "exact_duplicate_scenario" not in probs


def test_leakage_ignores_near_duplicates_within_a_split():
    recs = clean_set() + [make("t3", fam_in("train", "z"), "alpha " + LONG.replace("word100", "changed"))]
    assign_splits(recs)
    assert leakage.check(recs)["ok"]


def test_leakage_catches_gold_outside_test():
    recs = clean_set()
    recs[0]["source"] = "a_gold"  # stored split is still train
    probs = leakage.check(recs)["problems"]
    assert "gold_or_gold_derived_outside_test" in probs


def test_leakage_cli_exit_code(tmp_path):
    recs = clean_set()
    recs[0]["split"] = "test"
    p = tmp_path / "bad.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in recs), encoding="utf-8")
    assert leakage.main([str(p)]) == 1
