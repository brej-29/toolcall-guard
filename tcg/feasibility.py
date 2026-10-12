"""Phase 2 measurements. Steps are idempotent (cached), run them in order:
  gen     generate N families online (Flex) and measure tokens
  label   teacher-label those records online (Flex) and measure tokens and agreement with generation intent
  batch   submit 5 generation rows (3.8 Flash) and 5 label rows (3.1 Pro) as batch jobs in location global
  collect wait for both batch jobs and collect them
  gemma   count Gemma training tokens per example and write the 10-row tuning format test file
Usage: uv run python -m tcg.feasibility <step> [n]"""
import json
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from tcg import batch, config, gemini, generate, label
from tcg.prompts import STUDENT_SYSTEM, render

D = config.ROOT / "data" / "feasibility"
ROLES = json.loads((config.ROOT / "data" / "roles_v1.json").read_text(encoding="utf-8"))
ROLES_BY_ID = {r["role"]: r for r in ROLES}


def seeds(n: int, salt: str) -> list[dict]:
    rng = random.Random(f"feasibility-{salt}")
    return [generate.sample_seed(rng, ROLES) for _ in range(n)]


def usage_stats(phase: str) -> dict:
    rows = [json.loads(l) for l in gemini.LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r["phase"] == phase]
    if not rows:
        return {}
    f = lambda k: round(statistics.mean(r[k] for r in rows), 1)
    return {"calls": len(rows), "in": f("in"), "out": f("out"), "thoughts": f("thoughts"), "cached": f("cached"),
            "usd_per_call": round(statistics.mean(r["usd"] for r in rows), 6), "tiers": sorted({r["traffic_type"] or "" for r in rows})}


def step_gen(n: int) -> None:
    t0 = time.time()
    with ThreadPoolExecutor(16) as ex:
        fams = list(ex.map(lambda s: generate.generate_family(s, ROLES_BY_ID, "p2-gen"), seeds(n, "gen")))
    recs = [r for f in fams for r in f]
    D.mkdir(parents=True, exist_ok=True)
    (D / "gen_records.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs), encoding="utf-8")
    print(f"{len(fams)} families, {len(recs)} records in {time.time() - t0:.0f}s", usage_stats("p2-gen"))


def step_label() -> None:
    recs = [json.loads(l) for l in (D / "gen_records.jsonl").read_text(encoding="utf-8").splitlines()]
    t0 = time.time()
    with ThreadPoolExecutor(16) as ex:
        out = list(ex.map(lambda r: label.guard_online(r, phase="p2-label"), recs))
    agree_v = sum(o["parsed"] and o["parsed"]["verdict"] == r["label"]["verdict"] for o, r in zip(out, recs))
    agree_c = sum(o["parsed"] and o["parsed"]["category"] == r["label"]["category"] for o, r in zip(out, recs))
    for o, r in zip(out, recs):
        if not o["parsed"] or o["parsed"]["category"] != r["label"]["category"]:
            print(f'  disputed {r["id"]}: intent {r["label"]["category"]} | teacher {o["parsed"]}')
    print(f"{len(recs)} labels in {time.time() - t0:.0f}s, verdict agreement {agree_v}/{len(recs)}, "
          f"category agreement {agree_c}/{len(recs)}", usage_stats("p2-label"))


def step_batch() -> None:
    rows = []
    for s in seeds(5, "batch"):
        role = ROLES_BY_ID[s["role"]]
        rows.append(batch.make_request(generate.gen_prompt(s, role), model=config.GEN_MODEL, phase="p2-batch-gen",
                                       schema=generate.GEN_SCHEMA, temperature=1.0))
    print("gen job:", batch.submit("p2-batch-gen-5", config.GEN_MODEL, "p2-batch-gen", rows))
    recs = [json.loads(l) for l in (D / "gen_records.jsonl").read_text(encoding="utf-8").splitlines()][:5]
    rows = [label.guard_batch_row(r, phase="p2-batch-label") for r in recs]
    print("label job:", batch.submit("p2-batch-label-5", config.TEACHER_MODEL, "p2-batch-label", rows))


def step_collect() -> None:
    for name in ("p2-batch-gen-5", "p2-batch-label-5"):
        t0 = time.time()
        st = batch.wait(name)
        info = json.loads(batch.STATE.read_text())["batch_jobs"][name]
        print(name, st, f"waited {time.time() - t0:.0f}s", "submitted", info["submitted"], "ended", info.get("ended"))
        if "SUCCEEDED" in st or "PARTIALLY" in st:
            print("  ", batch.collect(name))
    print("batch gen", usage_stats("p2-batch-gen"), "\nbatch label", usage_stats("p2-batch-label"))


def student_example(r: dict, target: dict) -> dict:
    return {"messages": [{"role": "system", "content": STUDENT_SYSTEM}, {"role": "user", "content": render(r)},
                         {"role": "assistant", "content": json.dumps(target, ensure_ascii=False)}]}


def step_gemma() -> None:
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(config.HF_BASE_MODEL)
    recs = [json.loads(l) for l in (D / "gen_records.jsonl").read_text(encoding="utf-8").splitlines()]
    exs = [student_example(r, r["label"]) for r in recs]
    n = [len(tok(tok.apply_chat_template(e["messages"], tokenize=False), add_special_tokens=False).input_ids) for e in exs]
    print(f"Gemma tokens per training example: mean {statistics.mean(n):.0f}, median {statistics.median(n):.0f}, "
          f"min {min(n)}, max {max(n)} (limit 8192)")
    assert max(n) <= 8192
    for e in exs[:10]:
        assert [m["role"] for m in e["messages"]] == ["system", "user", "assistant"] and all(m["content"] for m in e["messages"])
    p = D / "tuning_format_test_10.jsonl"
    p.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in exs[:10]), encoding="utf-8")
    config.storage_client().bucket(config.BUCKET).blob("tuning/format_test/train_10.jsonl").upload_from_filename(str(p))
    print(f"wrote {p} and gs://{config.BUCKET}/tuning/format_test/train_10.jsonl")


if __name__ == "__main__":
    step = sys.argv[1]
    {"gen": lambda: step_gen(int(sys.argv[2]) if len(sys.argv) > 2 else 12), "label": step_label, "batch": step_batch,
     "collect": step_collect, "gemma": step_gemma}[step]()
