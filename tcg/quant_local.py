"""Laptop side of the quantization recovery test; kaggle/quant_test.py measures the same variants on the same 60
records (40 attacks, 20 benign from the synthetic test set) at full speed on a T4.
  merge          rebuild the merged checkpoint from the adapter and the base (W += alpha/r * B @ A in bf16, on CPU)
                 into merged/real; the merged copies in the bucket are not used
  run <variant>  load the variant on the 6 GB GPU (per-layer embeddings in RAM, as tcg.local_guard does); if it does not
                 fit, say so and run it on CPU instead (--device cpu). Writes results/quant_local/<variant> <device>.jsonl
                 and results/quant_local/summary.json
Variants: nf4_base+lora (the current laptop setup), merged_nf4, merged_int8, merged_full (bf16, CPU only)
Usage: uv run python -m tcg.quant_local merge | run <variant> [--device cuda|cpu] [--n N]"""
import argparse
import json
import statistics

import torch

from tcg import config
from tcg.data import read_jsonl
from tcg.local_guard import decide, load

MERGED = config.ROOT / "merged" / "real"
ADAPTER = str(config.ROOT / "adapters" / "real" / "adapter")
OUT = config.ROOT / "results" / "quant_local"
VARIANTS = {"nf4_base+lora": {"adapter": ADAPTER, "precision": "4bit"}, "merged_nf4": {"precision": "4bit", "base": str(MERGED)},
            "merged_int8": {"precision": "8bit", "base": str(MERGED)}, "merged_full": {"precision": "full", "base": str(MERGED)}}


def records() -> list[dict]:
    ids = [r["id"] for r in json.loads((config.ROOT / "results" / "kaggle" / "precision_check.json").read_text(encoding="utf-8"))["rows"]]
    by_id = {r["id"]: r for r in read_jsonl(config.ROOT / "data" / "v1" / "test.jsonl")}
    return [by_id[i] for i in ids]


def merge() -> None:
    from safetensors.torch import load_file
    from transformers import AutoModelForCausalLM, AutoTokenizer
    cfg = json.loads((config.ROOT / "adapters" / "real" / "adapter" / "adapter_config.json").read_text())
    scale = cfg["lora_alpha"] / cfg["r"]
    m = AutoModelForCausalLM.from_pretrained(config.HF_BASE_MODEL, dtype=torch.bfloat16, device_map={"": "cpu"})
    sd = {k.removeprefix("base_model.model."): v.float() for k, v in load_file(f"{ADAPTER}/adapter_model.safetensors").items()}
    pairs = [k for k in sd if k.endswith("lora_A.weight")]
    with torch.no_grad():
        for k in pairs:
            mod = m.get_submodule(k.removesuffix(".lora_A.weight"))
            mod.weight += (scale * sd[k.replace("lora_A", "lora_B")] @ sd[k]).to(mod.weight.dtype)
    m.save_pretrained(MERGED, safe_serialization=True)
    AutoTokenizer.from_pretrained(config.HF_BASE_MODEL).save_pretrained(MERGED)
    print(f"merged {len(pairs)} LoRA pairs (scale {scale}) into {MERGED}")


def run(variant: str, device: str, n: int, label: str = "") -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summary_path = OUT / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    key = f"{variant} {device}" + (f" {label}" if label else "")
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    try:
        tok, model = load(device=device, **VARIANTS[variant])
        recs = records()[: n or None]
        rows = []
        for r in recs:
            d = decide(tok, model, r)
            rows.append({"id": r["id"], "gold": r["label"]["verdict"], "pred": d["parsed"], "latency_ms": d["latency_ms"], "raw": d["text"]})
            print(r["id"], (d["parsed"] or {}).get("verdict"), d["latency_ms"], flush=True)
    except torch.OutOfMemoryError as e:
        summary[key] = {"fits": False, "error": str(e)[:200]}
        summary_path.write_text(json.dumps(summary, indent=1))
        print(key, "does not fit:", str(e)[:200])
        return
    (OUT / f"{key}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
    v = lambda x: (x["pred"] or {"verdict": "block"})["verdict"]
    summary[key] = {"fits": True, "n": len(rows), "attacks_blocked": sum(v(x) == "block" for x in rows if x["gold"] == "block"),
                    "attacks": sum(x["gold"] == "block" for x in rows),
                    "false_positives": sum(v(x) == "block" for x in rows if x["gold"] == "allow"),
                    "benign": sum(x["gold"] == "allow" for x in rows), "json_valid": sum(x["pred"] is not None for x in rows),
                    "median_latency_ms": statistics.median(x["latency_ms"] for x in rows),
                    "peak_gpu_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2) if device == "cuda" else None,
                    "hardware": torch.cuda.get_device_name(0) if device == "cuda" else "laptop CPU (i5-13450HX)"}
    summary_path.write_text(json.dumps(summary, indent=1))
    print(key, summary[key])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["merge", "run"])
    ap.add_argument("variant", nargs="?", choices=list(VARIANTS))
    ap.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--label", default="", help="suffix for the summary key, e.g. a re-timing run")
    a = ap.parse_args()
    merge() if a.step == "merge" else run(a.variant, a.device, a.n, a.label)
