"""Managed LoRA tuning of Gemma 4 E4B on Vertex (location from .env, global).
  build    write messages-format JSONL (student prompt + teacher label) for train and val, upload to gs://<bucket>/tuning/<name>/
  launch   run the leakage check, refuse if another tuning job is running (quota is 1), launch, save the job to state.json
  status   refresh and print the job state, data stats and any endpoint (there must be none)
  download copy <output>/postprocess/node-0/checkpoints/final to adapters/<name>/ and record the cost in the ledger
Usage: uv run python -m tcg.tune <step> <name> [--epochs 2] [--adapter-size 16]"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys

from tcg import config, gemini, leakage
from tcg.prompts import STUDENT_SYSTEM, render

STATE = config.ROOT / "state.json"
TDIR = config.ROOT / "data" / "tuning"


def example(r: dict) -> dict:
    target = {k: r["label"][k] for k in ("verdict", "category", "reason")}
    return {"messages": [{"role": "system", "content": STUDENT_SYSTEM}, {"role": "user", "content": render(r)},
                         {"role": "assistant", "content": json.dumps(target, ensure_ascii=False)}]}


def gemma_tokens(examples: list[dict]) -> list[int]:
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(config.HF_BASE_MODEL)
    return [len(tok(tok.apply_chat_template(e["messages"], tokenize=False), add_special_tokens=False).input_ids)
            for e in examples]


def build(name: str, train: list[dict], val: list[dict]) -> dict:
    """train/val are labeled contract records. Refuses records outside the train/val splits."""
    assert all(r["split"] == "train" for r in train) and all(r["split"] == "val" for r in val), "split mismatch"
    rep = leakage.check(train + val)
    assert rep["ok"], rep["problems"]
    d = TDIR / name
    d.mkdir(parents=True, exist_ok=True)
    stats = {}
    for part, recs in (("train", train), ("val", val)):
        exs = [example(r) for r in recs]
        toks = gemma_tokens(exs)
        assert max(toks) <= 8192, f"{part}: example over 8192 tokens"
        (d / f"{part}.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in exs),
                                         encoding="utf-8", newline="\n")
        (d / f"{part}_ids.json").write_text(json.dumps([r["id"] for r in recs]), encoding="utf-8")
        config.storage_client().bucket(config.BUCKET).blob(f"tuning/{name}/{part}.jsonl").upload_from_filename(
            str(d / f"{part}.jsonl"))
        stats[part] = {"examples": len(exs), "gemma_tokens": sum(toks), "max_tokens": max(toks)}
    (d / "stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    return stats


def freeze(version: str, name: str, val_cap: int = 150) -> dict:
    """Freeze the tuning dataset: train = data/<version>/train.jsonl, val = up to val_cap records from val-split families
    (stable choice by id hash). Writes the files, uploads them, and records a SHA-256 of the frozen files."""
    import hashlib
    from tcg.data import read_jsonl
    d = config.ROOT / "data" / version
    # review_100 stays evaluation-only: drop every family that contains a reviewed record (twins included)
    rl = d / "review_labels.json"
    review_ids = set(json.loads(rl.read_text(encoding="utf-8"))) if rl.exists() else set()
    everything = [r for f in ("train", "val", "test", "disputed") for r in read_jsonl(d / f"{f}.jsonl")]
    review_fams = {r["family_id"] for r in everything if r["id"] in review_ids}
    train = [r for r in read_jsonl(d / "train.jsonl") if r["family_id"] not in review_fams]
    val = sorted((r for r in read_jsonl(d / "val.jsonl") if r["family_id"] not in review_fams),
                 key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())[:val_cap]
    print(f"review families excluded: {len(review_fams)}; train {len(train)}, val {len(val)}")
    stats = build(name, train, val)
    h = hashlib.sha256()
    for part in ("train", "val"):
        h.update((TDIR / name / f"{part}.jsonl").read_bytes())
    stats["sha256"] = h.hexdigest()
    stats["frozen_at"] = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")
    (TDIR / name / "stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(json.dumps(stats, indent=1))
    return stats


def _state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def _save(s: dict) -> None:
    STATE.write_text(json.dumps(s, indent=1), encoding="utf-8")


def _job(resource_name: str):
    from vertexai.tuning import sft
    config.vertex_init(re.search(r"/locations/([^/]+)/", resource_name).group(1))
    return sft.SupervisedTuningJob(resource_name)


def launch(name: str, epochs: int, adapter_size: int | None, learning_rate: float | None) -> str:
    s = _state()
    if name in s["tuning_jobs"]:
        return s["tuning_jobs"][name]["job"]
    for other, info in s["tuning_jobs"].items():
        if not _job(info["job"]).has_ended:  # quota: 1 concurrent OSS tuning job per project
            sys.exit(f"REFUSED: tuning job {other} is still running and the quota is 1 concurrent job.")
    d = TDIR / name
    stats = json.loads((d / "stats.json").read_text(encoding="utf-8"))
    est = stats["train"]["gemma_tokens"] * epochs * config.TUNING_PRICE_PER_M / 1e6
    print(f"estimated training cost: {stats['train']['gemma_tokens']} tokens x {epochs} epochs = USD {est:.2f}")
    from vertexai.tuning import SourceModel, sft
    config.vertex_init(config.TUNING_LOCATION)
    uri = f"gs://{config.BUCKET}/tuning/{name}"
    job = sft.train(source_model=SourceModel(base_model=config.TUNE_BASE_MODEL), tuning_mode="PEFT_ADAPTER",
                    train_dataset=f"{uri}/train.jsonl",
                    validation_dataset=f"{uri}/val.jsonl" if stats["val"]["examples"] else None,
                    epochs=epochs, adapter_size=adapter_size, learning_rate=learning_rate,
                    tuned_model_display_name=f"tcg-{name}", labels={**config.LABELS, "run": name},
                    output_uri=f"{uri}/output")
    s = _state()
    s["tuning_jobs"][name] = {"job": job.resource_name, "base_model": config.TUNE_BASE_MODEL, "epochs": epochs,
                              "adapter_size": adapter_size, "learning_rate": learning_rate, "output_uri": f"{uri}/output",
                              "stats": stats, "estimated_usd": round(est, 4),
                              "launched": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
                              "state": str(job.state), "cost_recorded": False}
    _save(s)
    return job.resource_name


def status(name: str) -> dict:
    s = _state()
    info = s["tuning_jobs"][name]
    job = _job(info["job"])
    g = job._gca_resource
    info.update(state=getattr(job.state, "name", str(job.state)), endpoint=g.tuned_model.endpoint or None, tuned_model=g.tuned_model.model or None,
                error=str(job.error) if job.error and job.error.code else None,
                ended=g.end_time.isoformat() if g.end_time else None, started=g.create_time.isoformat())
    info["data_stats"] = str(g.tuning_data_stats)[:2000]
    _save(s)
    return info


def download(name: str) -> str:
    info = status(name)
    assert "SUCCEEDED" in info["state"], info["state"]
    # final/ holds the LoRA adapter (about 140 MB) and a merged 16 GB model.safetensors; only the adapter, the
    # training curves and the logs are downloaded.
    out = config.ROOT / "adapters" / name
    out.mkdir(parents=True, exist_ok=True)
    final = f"{info['output_uri']}/postprocess/node-0/checkpoints/final"
    gcloud = shutil.which("gcloud")
    subprocess.run([gcloud, "storage", "cp", "-r", f"{final}/adapter", str(out), f"--project={config.PROJECT}"], check=True)
    subprocess.run([gcloud, "storage", "cp", "-r", f"{final}/runs", f"{final}/debug.log", f"{final}/managed_oss_fine_tuning_marker.json",
                    f"{info['output_uri']}/oss_tuning_job_logs.txt", str(out), f"--project={config.PROJECT}"], check=False)
    s = _state()
    if not s["tuning_jobs"][name]["cost_recorded"]:
        tokens = info["stats"]["train"]["gemma_tokens"] * info["epochs"]
        with gemini._lock, gemini.LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"), "phase": name,
                                "kind": "tuning", "model": config.TUNE_BASE_MODEL, "tier": "managed_lora", "key": info["job"],
                                "in": 0, "out": 0, "thoughts": 0, "cached": 0, "traffic_type": None,
                                "training_tokens": tokens, "usd": round(tokens * config.TUNING_PRICE_PER_M / 1e6, 6)}) + "\n")
        s["tuning_jobs"][name]["cost_recorded"] = True
        _save(s)
    return str(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["freeze", "launch", "status", "download"])
    ap.add_argument("name")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--adapter-size", type=int, default=None)
    ap.add_argument("--learning-rate", type=float, default=None)
    ap.add_argument("--version", default="v1")
    a = ap.parse_args()
    if a.step == "freeze":
        freeze(a.version, a.name)
    elif a.step == "launch":
        print(launch(a.name, a.epochs, a.adapter_size, a.learning_rate))
    elif a.step == "status":
        print(json.dumps(status(a.name), indent=1))
    else:
        print(download(a.name))
