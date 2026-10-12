"""Run the local guards over the test sets in one process: each model is loaded once, every prediction is appended to
results/preds/<testset>/<guard>.jsonl, and records already there are skipped, so the queue can be stopped and resumed.
Usage: uv run python -m tcg.eval_queue [--only GUARD_SUBSTRING]"""
import argparse
import json
import time

from tcg import config
from tcg.local_guard import decide, load

SETS = {"a_gold": "data/a_gold.jsonl", "a_replay": "data/a_replay_eval.jsonl", "review_100": "data/v1/review_eval.jsonl",
        "synthetic_test": "data/v1/test.jsonl", "ood": "data/ood/ood_v1.jsonl", "val_frozen": "data/v1/val_frozen.jsonl"}
# (guard name, adapter, mode, test sets) in priority order
JOBS = [
    ("gemma-4-e4b tuned (ours)", "adapters/real/adapter", "student", ["synthetic_test", "val_frozen", "a_gold", "a_replay"]),
    ("gemma-4-e4b G5 in-domain (A data)", "adapters/g5/adapter", "student",
     ["a_gold", "a_replay", "review_100", "ood", "synthetic_test"]),
    ("gemma-4-e4b untuned zero-shot", None, "student", ["a_gold", "a_replay"]),
    ("gemma-4-e4b untuned few-shot", None, "fewshot", ["a_gold", "a_replay"]),
]


def main(only: str | None) -> None:
    for guard, adapter, mode, sets in JOBS:
        if only and only not in guard:
            continue
        todo = {}
        for ts in sets:
            recs = [json.loads(l) for l in (config.ROOT / SETS[ts]).read_text(encoding="utf-8").splitlines() if l.strip()]
            out = config.ROOT / "results" / "preds" / ts / f"{guard}, 4-bit laptop.jsonl"
            done = {json.loads(l)["id"] for l in out.read_text(encoding="utf-8").splitlines() if l.strip()} if out.exists() else set()
            todo[ts] = (out, [r for r in recs if r["id"] not in done])
        n = sum(len(v[1]) for v in todo.values())  # (files are named "<guard>, 4-bit laptop"; fp16 results come from Kaggle)
        if not n:
            continue
        t0 = time.time()
        tok, model = load(adapter, "cuda")
        print(f"{guard}: loaded in {time.time() - t0:.0f}s, {n} records to do", flush=True)
        for ts, (out, recs) in todo.items():
            out.parent.mkdir(parents=True, exist_ok=True)
            for i, r in enumerate(recs, 1):
                d = decide(tok, model, r, mode)
                row = {"id": r["id"], "pred": d["parsed"], "latency_ms": d["latency_ms"], "cost_usd": 0.0,
                       "verdict_prob": d["verdict_prob"], "tokens": [d["input_tokens"], d["output_tokens"]], "raw": d["text"]}
                with out.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                if i % 50 == 0 or i == len(recs):
                    print(f"  {guard} / {ts}: {i}/{len(recs)}", flush=True)
        del model
        import torch
        torch.cuda.empty_cache()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    main(ap.parse_args().only)
