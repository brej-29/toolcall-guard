"""Push the full-precision Kaggle evaluation: one private dataset (prompt code, contract examples, test sets, adapters)
and one kernel per guard configuration (kaggle/eval_fp16.py with JOB filled in).
Usage: uv run python kaggle/push_eval.py dataset      (create or version the dataset)
       uv run python kaggle/push_eval.py kernel <job>  (job in JOBS below)"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER = json.loads((Path.home() / ".kaggle" / "kaggle.json").read_text())["username"]
SLUG = "tcg-guard-eval-sets-v1"
SETS = {"synthetic_test": "data/v1/test.jsonl", "review_100": "data/v1/review_eval.jsonl", "a_gold": "data/a_gold.jsonl",
        "ood": "data/ood/ood_v1.jsonl", "val_frozen": "data/v1/val_frozen.jsonl", "a_replay": "data/a_replay_eval.jsonl",
        # sample records the first tuned and untuned-zs kernels did not see (they ran on the pre-final A set)
        "a_replay_rest": "data/a_replay_rest.jsonl",
        # A's adaptive rewrites (87 attacks, evaluation only, never trained on), separate table
        "a_adaptive": "data/a/adaptive/adaptive_rewrite_v1.jsonl",
        # last 450 records of the A replay sample for the int8 scale-up (the laptop GPU takes the first 1,413)
        "a_replay_tail": "data/a_replay_tail.jsonl"}
ALL = ["ood", "review_100", "a_gold", "synthetic_test", "val_frozen", "a_replay"]
JOBS = {
    "tuned": {"guard": "gemma-4-e4b tuned (ours)", "adapter": "real", "mode": "student", "sets": ALL},
    "untuned-zs": {"guard": "gemma-4-e4b untuned zero-shot", "adapter": None, "mode": "student", "sets": ALL},
    "untuned-fs": {"guard": "gemma-4-e4b untuned few-shot", "adapter": None, "mode": "fewshot", "sets": ALL},
    "g5": {"guard": "gemma-4-e4b G5 in-domain (A data)", "adapter": "g5", "mode": "student",
           "sets": ["a_gold", "review_100", "ood", "synthetic_test", "a_replay"]},
    "g5-val": {"guard": "gemma-4-e4b G5 in-domain (A data)", "adapter": "g5", "mode": "student", "sets": ["val_frozen"]},
    "tuned-rest": {"guard": "gemma-4-e4b tuned (ours)", "adapter": "real", "mode": "student", "sets": ["a_replay_rest"]},
    "untuned-zs-rest": {"guard": "gemma-4-e4b untuned zero-shot", "adapter": None, "mode": "student", "sets": ["a_replay_rest"]},
    "tuned-adaptive": {"guard": "gemma-4-e4b tuned (ours)", "adapter": "real", "mode": "student", "sets": ["a_adaptive"]},
    "untuned-zs-adaptive": {"guard": "gemma-4-e4b untuned zero-shot", "adapter": None, "mode": "student", "sets": ["a_adaptive"]},
    "int8": {"guard": "gemma-4-e4b tuned (ours), merged int8", "adapter": "real", "mode": "student", "quant": "int8",
             "sets": ["ood", "review_100", "a_gold", "synthetic_test"]},  # a_replay runs on the laptop
    "int8-tail": {"guard": "gemma-4-e4b tuned (ours), merged int8", "adapter": "real", "mode": "student", "quant": "int8",
                  "sets": ["a_replay_tail"], "max_hours": 2.25},  # stop cleanly before the weekly GPU quota runs out
    # quantization recovery test on the 60-record precision check set (kaggle/quant_test.py)
    "quant": {"script": "quant_test.py",
              "ids": [r["id"] for r in json.loads((ROOT / "results" / "kaggle" / "precision_check.json").read_text())["rows"]]},
    # GGUF part again, CPU-only (the CUDA build failed: no libcuda stub for CMake); no GPU quota used
    "gguf-cpu": {"script": "quant_test.py", "parts": ["gguf"], "gguf_device": "cpu", "gpu": False,
                 "ids": [r["id"] for r in json.loads((ROOT / "results" / "kaggle" / "precision_check.json").read_text())["rows"]]},
}


def kaggle(*args) -> str:
    r = subprocess.run([shutil.which("uvx"), "kaggle", *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    print(r.stdout[-400:], r.stderr[-400:])
    return r.stdout


def dataset() -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        shutil.copy(ROOT / "tcg" / "prompts.py", d / "prompts.py")
        shutil.copy(ROOT / "contract" / "examples_v0.jsonl", d / "examples_v0.jsonl")
        (d / "sets").mkdir()
        for name, src in SETS.items():
            shutil.copy(ROOT / src, d / "sets" / f"{name}.jsonl")
        for ad in ("real", "g5"):
            (d / "adapters" / ad).mkdir(parents=True)
            for f in ("adapter_config.json", "adapter_model.safetensors"):
                shutil.copy(ROOT / "adapters" / ad / "adapter" / f, d / "adapters" / ad / f)
        (d / "dataset-metadata.json").write_text(json.dumps({"title": SLUG, "id": f"{USER}/{SLUG}", "licenses": [{"name": "other"}]}))
        if SLUG in kaggle("datasets", "list", "--mine", "-s", SLUG):
            kaggle("datasets", "version", "-p", str(d), "-m", "update", "-r", "zip", "--dir-mode", "zip")
        else:
            kaggle("datasets", "create", "-p", str(d), "-r", "zip", "--dir-mode", "zip")


def kernel(job: str) -> None:
    script = JOBS[job].get("script", "eval_fp16.py")
    code = (ROOT / "kaggle" / script).read_text(encoding="utf-8").replace("JOB = {}  # replaced at push time", f"JOB = {JOBS[job]!r}")
    with tempfile.TemporaryDirectory() as k:
        k = Path(k)
        (k / script).write_text(code, encoding="utf-8")
        (k / "kernel-metadata.json").write_text(json.dumps({
            "id": f"{USER}/tcg-eval-{job}", "title": f"tcg-eval-{job}", "code_file": script, "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": JOBS[job].get("gpu", True), "enable_internet": True,
            "dataset_sources": [f"{USER}/{SLUG}"], "model_sources": ["google/gemma-4/transformers/gemma-4-e4b-it/1"],
            "competition_sources": []}))
        kaggle("kernels", "push", "-p", str(k))


if __name__ == "__main__":
    dataset() if sys.argv[1] == "dataset" else kernel(sys.argv[2])
