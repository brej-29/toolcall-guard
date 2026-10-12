"""Publishable prediction files for Project A's test records: predictions/<set>/<guard>.jsonl.
Only Project B's guards (tuned full precision, merged 8-bit, 4-bit, G5 in-domain, untuned zero-shot and few-shot,
keyword, and the Flash and Pro baselines); Project A's own guard results are A's to publish. Rows are limited to the
records of each evaluation set and hold A's record id plus our output, never A's record text. Fields: id, pred
(verdict, category, reason), verdict_prob, latency_ms, cost_usd, tokens, precision, hardware; raw only when the output
did not parse. Text fields get Project A's release replacements (scripts/sanitize_release.py in agent-govbench, read
from A's local repo), so domains and names match A's public data.
Usage: uv run python -m tcg.export_predictions"""
import importlib.util
import json
import shutil
from collections import Counter

from tcg import config
from tcg.data import read_jsonl, write_jsonl

R = config.ROOT
OUT = R / "predictions"
A_SANITIZER = r"\\wsl.localhost\Ubuntu-24.04\home\brej\gcp\agent-govbench\scripts\sanitize_release.py"
SETS = {"a_gold": R / "data" / "a_gold.jsonl", "a_replay": R / "data" / "a_replay_eval.jsonl",
        "a_pro_agent": R / "data" / "a_pro_agent_eval.jsonl", "a_adaptive": R / "data" / "a" / "adaptive" / "adaptive_rewrite_v1.jsonl"}
ADAPTIVE_4BIT = {"tcg_tuned_4bit_laptop": "gemma-4-e4b tuned (ours), 4-bit laptop",
                 "tcg_untuned_zs_4bit_laptop": "gemma-4-e4b untuned zero-shot, 4-bit laptop"}
KEEP = ("id", "pred", "verdict_prob", "latency_ms", "cost_usd", "tokens", "precision", "hardware")


def main() -> None:
    spec = importlib.util.spec_from_file_location("a_sanitize", A_SANITIZER)
    a = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a)
    counts = Counter()

    def clean(x):
        if isinstance(x, str):
            for key, rx, rep in a.RULES:
                x, n = rx.subn(rep, x)
                counts[key] += n
            return x
        if isinstance(x, list):
            return [clean(v) for v in x]
        if isinstance(x, dict):
            return {k: clean(v) for k, v in x.items()}
        return x

    if OUT.exists():
        shutil.rmtree(OUT)
    index = []
    for s, path in SETS.items():
        ids = [r["id"] for r in read_jsonl(path)]
        sources = {f.stem: read_jsonl(f) for f in sorted((R / "results" / "preds" / s).glob("*.jsonl")) if not f.stem.startswith("A ")}
        if s == "a_adaptive":  # the 4-bit adaptive runs live in replay_eval.py's output
            for r in read_jsonl(R / "results" / "adaptive" / "adaptive_rewrite_v1.jsonl"):
                for g in r.get("guard_results") or []:
                    if g["config"] in ADAPTIVE_4BIT:
                        pred = {"verdict": g["verdict"], "category": g.get("category"), "reason": g.get("reason")} if g.get("json_valid") else None
                        sources.setdefault(ADAPTIVE_4BIT[g["config"]], []).append(
                            {"id": r["id"], "pred": pred, "latency_ms": g.get("latency_ms"), "cost_usd": 0.0,
                             "tokens": [g.get("input_tokens"), g.get("output_tokens")], "precision": "4bit", "hardware": g.get("hardware"),
                             "raw": g.get("raw")})
        for guard, rows in sources.items():
            by = {r["id"]: r for r in rows}
            out = []
            for i in ids:
                if i in by:
                    r = by[i]
                    row = {k: r[k] for k in KEEP if k in r}
                    if r.get("pred") is None:
                        row["raw"] = r.get("raw")
                    out.append(clean(row))
            if out:
                (OUT / s).mkdir(parents=True, exist_ok=True)
                write_jsonl(OUT / s / f"{guard}.jsonl", out)
                index.append({"set": s, "guard": guard, "rows": len(out), "records_in_set": len(ids)})
    (OUT / "index.json").write_text(json.dumps({"files": index, "a_release_replacements": {k: v for k, v in counts.items() if v}}, indent=1),
                                    encoding="utf-8")
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"{len(index)} files, {size / 1e6:.2f} MB; A release replacements: {dict(c for c in counts.items() if c[1])}")
    for x in index:
        print(f"  {x['set']:12s} {x['guard']:52s} {x['rows']:5d} / {x['records_in_set']}")


if __name__ == "__main__":
    main()
