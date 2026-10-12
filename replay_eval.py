"""Replay evaluation of the distilled guard on Project A's saved decision records (contract schema_v0).

Reads every *.jsonl under --src (a local folder or a gs:// prefix), runs the guard locally (free: GPU or CPU),
appends one guard_results entry per record (stage "replay", cost 0), writes the records to --out with the same
file names, and writes metrics.json and metrics.md comparing every guard configuration found in the records.
Resumable: records that already have a result for --config in --out are skipped.

Limitation: replay has no adaptive agent behaviour after a block. Block rate here is the share of malicious calls
the guard would have stopped at that step; a live agent might retry another way or succeed at a later step.

Examples:
  uv run python replay_eval.py --src gs://govbench-brejesh-01-data/replay/ --adapter adapters/real/final
  uv run python replay_eval.py --src ./replay --adapter BrejBala/gemma-toolcall-guard --device cpu
"""
import argparse
import datetime
import json
import platform
from collections import defaultdict
from pathlib import Path

import jsonschema

from tcg import metrics

ROOT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / "contract" / "schema_v0.json").read_text(encoding="utf-8"))


def read_src(src: str) -> dict[str, list[dict]]:
    files = {}
    if src.startswith("gs://"):
        from google.cloud import storage
        bucket, _, prefix = src[5:].partition("/")
        for b in storage.Client().bucket(bucket).list_blobs(prefix=prefix):  # A runs this after the credit: any project
            if b.name.endswith(".jsonl"):
                files[b.name[len(prefix):].lstrip("/")] = [json.loads(l) for l in b.download_as_text().splitlines() if l.strip()]
    else:
        for p in sorted(Path(src).rglob("*.jsonl")):
            files[str(p.relative_to(src))] = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return files


def hardware(device: str) -> str:
    import torch
    if device == "cuda" and torch.cuda.is_available():
        return torch.cuda.get_device_name(0)
    return f"cpu {platform.processor() or platform.machine()}"


def summarize(records: list[dict]) -> dict:
    """Metrics per guard configuration, on all labeled records and on split=test only."""
    out = {}
    for subset, recs in (("all", records), ("test", [r for r in records if r.get("split") == "test"])):
        by_cfg, has_cat = defaultdict(list), defaultdict(bool)
        for r in recs:
            if not r.get("label"):
                continue
            for g in r.get("guard_results") or []:
                if g.get("verdict") in ("allow", "block"):
                    has_cat[g["config"]] |= bool(g.get("category"))
                    pred = {"verdict": g["verdict"], "category": g.get("category") or ("benign" if g["verdict"] == "allow" else "unknown")}
                else:
                    continue  # error / not_evaluated are counted below, not scored
                by_cfg[g["config"]].append({"family_id": r["family_id"], "label": r["label"], "pred": pred,
                                            "latency_ms": g.get("latency_ms"), "cost_usd": g.get("cost_usd")})
        errors = defaultdict(int)
        for r in recs:
            for g in r.get("guard_results") or []:
                if g.get("verdict") in ("error", "not_evaluated"):
                    errors[g["config"]] += 1
        out[subset] = {cfg: {"ci95": metrics.with_ci(rows, iters=500), "unscored": errors[cfg], "has_category": has_cat[cfg]}
                       for cfg, rows in by_cfg.items()}
    return out


def to_markdown(summary: dict) -> str:
    keys = ["n", "attack_block_rate", "false_positive_rate", "macro_f1", "json_valid_rate", "median_latency_ms", "cost_per_1k_usd"]
    fmt = lambda t: "" if t[0] is None else (f"{t[0]:.3f} [{t[1]:.3f}, {t[2]:.3f}]" if t[1] is not None else f"{t[0]:.3g}")
    lines = []
    for subset, cfgs in summary.items():
        lines += [f"## Records: {subset}", "", "| config | " + " | ".join(keys) + " | unscored |", "|---" * (len(keys) + 2) + "|"]
        for cfg, m in sorted(cfgs.items()):
            # a guard without categories (e.g. Project A's) has no macro F1
            cells = [fmt(m["ci95"][k]) if k != "macro_f1" or m.get("has_category", True) else "-" for k in keys]
            lines.append(f"| {cfg} | " + " | ".join(cells) + f" | {m['unscored']} |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", default="replay_results")
    ap.add_argument("--adapter", help="local adapter folder or Hugging Face repo id; omit for the untuned base model")
    ap.add_argument("--config", default="tcg_gemma4_e4b_lora_v1")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--precision", choices=["auto", "full", "4bit"], default="auto",
                    help="auto: full precision on a GPU with at least 18 GB or on CPU, else 4-bit (measured to miss more attacks)")
    ap.add_argument("--import-preds", help="instead of running a model, append predictions already made elsewhere (one JSON "
                    "per line: id, pred, latency_ms, hardware, precision, raw; e.g. the Kaggle full-precision kernel)")
    a = ap.parse_args()
    imported = None
    if a.import_preds:
        imported = {x["id"]: x for x in map(json.loads, Path(a.import_preds).read_text(encoding="utf-8").splitlines()) if x}
    import torch
    if a.precision == "auto" and not imported:
        big = a.device == "cuda" and torch.cuda.is_available() and torch.cuda.get_device_properties(0).total_memory >= 18 * 2**30
        a.precision = "full" if (big or a.device == "cpu") else "4bit"
    if a.precision == "4bit" and not imported:
        print("WARNING: 4-bit base. On 60 synthetic records it blocked 29 of 40 attacks vs 36 at full precision.")

    from tcg.local_guard import decide, load
    files = read_src(a.src)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if not imported:
        tok, model = load(a.adapter, a.device, precision=a.precision)
        hw = f"{hardware(a.device)} {a.precision}"
    validator = jsonschema.Draft202012Validator(SCHEMA)
    all_records, done = [], 0
    for name, recs in files.items():
        dest = out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        prev = {}
        if dest.exists():
            prev = {r["id"]: r for r in map(json.loads, dest.read_text(encoding="utf-8").splitlines()) if r}
        results = []
        for r in recs:
            r = prev.get(r["id"], r)
            todo = not any(g.get("config") == a.config for g in r.get("guard_results") or []) and (not a.limit or done < a.limit)
            if todo and imported is not None and r["id"] not in imported:
                todo = False  # no imported prediction for this record
            if todo:
                errs = list(validator.iter_errors(r))
                if errs:
                    g = {"config": a.config, "verdict": "not_evaluated", "reason": f"schema: {errs[0].message[:200]}"}
                elif imported is not None:
                    x, p = imported[r["id"]], imported[r["id"]]["pred"]
                    g = {"config": a.config, "verdict": p["verdict"] if p else "block", "category": p["category"] if p else None,
                         "reason": p["reason"] if p else "invalid guard output, fail-closed", "stage": "replay",
                         "latency_ms": x.get("latency_ms"), "cost_usd": 0.0, "hardware": f"{x.get('hardware', '')} {x.get('precision', '')}".strip(),
                         "json_valid": p is not None, "raw": x.get("raw"), "imported_from": Path(a.import_preds).name}
                    done += 1
                else:
                    d = decide(tok, model, r)
                    p = d["parsed"]
                    g = {"config": a.config, "verdict": p["verdict"] if p else "block", "category": p["category"] if p else None,
                         "reason": p["reason"] if p else "invalid guard output, fail-closed", "stage": "replay",
                         "latency_ms": d["latency_ms"], "cost_usd": 0.0, "input_tokens": d["input_tokens"],
                         "output_tokens": d["output_tokens"], "hardware": hw, "json_valid": p is not None, "raw": d["text"]}
                    done += 1
                g["evaluated_at"] = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
                r.setdefault("guard_results", []).append(g)
            results.append(r)
            all_records.append(r)
        dest.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results), encoding="utf-8")
        print(f"{name}: {len(results)} records")
    summary = summarize(all_records)
    (out / "metrics.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    (out / "metrics.md").write_text("# Replay metrics (95% family-clustered bootstrap intervals)\n\n" + to_markdown(summary),
                                    encoding="utf-8")
    print((out / "metrics.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
