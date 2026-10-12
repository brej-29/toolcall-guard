"""Push the Kaggle fallback: a private dataset with train/val JSONL + tcg_config.json, and the training kernel.
Usage: uv run python kaggle/push.py <dataset-slug> <train.jsonl> <val.jsonl> '{"limit": 200, "epochs": 1}'"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

USER = json.loads((Path.home() / ".kaggle" / "kaggle.json").read_text())["username"]
HERE = Path(__file__).resolve().parent


def kaggle(*args) -> str:
    r = subprocess.run([shutil.which("uvx"), "kaggle", *args], capture_output=True, text=True)
    print(r.stdout[-1500:], r.stderr[-1500:])
    return r.stdout


def main(slug: str, train: str, val: str, cfg: str) -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        shutil.copy(train, d / "train.jsonl")
        shutil.copy(val, d / "val.jsonl")
        (d / "tcg_config.json").write_text(cfg)
        (d / "dataset-metadata.json").write_text(json.dumps(
            {"title": slug, "id": f"{USER}/{slug}", "licenses": [{"name": "other"}]}))
        exists = slug in kaggle("datasets", "list", "--mine", "-s", slug)
        if exists:
            kaggle("datasets", "version", "-p", str(d), "-m", "update", "-r", "zip")
        else:
            kaggle("datasets", "create", "-p", str(d), "-r", "zip")  # private by default
    with tempfile.TemporaryDirectory() as k:
        k = Path(k)
        shutil.copy(HERE / "train_lora.py", k / "train_lora.py")
        (k / "kernel-metadata.json").write_text(json.dumps({
            "id": f"{USER}/tcg-train-lora", "title": "tcg-train-lora", "code_file": "train_lora.py",
            "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": True,
            "enable_internet": True, "dataset_sources": [f"{USER}/{slug}"],
            "model_sources": ["google/gemma-4/transformers/gemma-4-e4b-it/1"], "competition_sources": []}))
        kaggle("kernels", "push", "-p", str(k))


if __name__ == "__main__":
    main(*sys.argv[1:5])
