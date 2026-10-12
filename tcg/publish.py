"""Publish to Hugging Face as PRIVATE repos (the user flips visibility after reading the cards). Project A data is
never uploaded: every dataset record must have a B source and a b- id, or nothing is sent.
  model    adapters/real/adapter + hf/model_card.md (README.md) + RESULTS.md, results/summary.json, error analysis
  dataset  B records + hf/dataset_card.md (README.md) + contract schema and taxonomy
Usage: uv run python -m tcg.publish model|dataset"""
import sys

from huggingface_hub import CommitOperationAdd, HfApi

from tcg import config
from tcg.data import read_jsonl

R = config.ROOT
DATA_FILES = {"train.jsonl": "data/v1/train.jsonl", "val.jsonl": "data/v1/val.jsonl",
              "val_frozen_150.jsonl": "data/v1/val_frozen.jsonl", "test.jsonl": "data/v1/test.jsonl",
              "disputed.jsonl": "data/v1/disputed.jsonl", "review_100.jsonl": "data/v1/review_eval.jsonl",
              "ood_30.jsonl": "data/ood/ood_v1.jsonl"}


def card(path: str) -> bytes:
    text = (R / path).read_text(encoding="utf-8")
    assert "\u2014" not in text, f"{path} contains an em dash"
    assert "PLACEHOLDER" not in text, f"{path} still has a placeholder"
    return text.encode("utf-8")


def push(repo: str, repo_type: str, ops: list, message: str) -> None:
    api = HfApi()
    api.create_repo(repo, repo_type=repo_type, private=True, exist_ok=True)
    assert api.repo_info(repo, repo_type=repo_type).private, f"{repo} is public; refusing to upload"
    api.create_commit(repo, ops, repo_type=repo_type, commit_message=message)
    print(f"uploaded {len(ops)} files to {repo_type} {repo} (private)")


def model() -> None:
    ad = R / "adapters" / "real" / "adapter"
    ops = [CommitOperationAdd("README.md", card("hf/model_card.md"))]
    ops += [CommitOperationAdd(f, str(ad / f)) for f in ("adapter_config.json", "adapter_model.safetensors")]
    # the exact prompt, record rendering and output parser used in training and evaluation, plus one example record,
    # so the card's quick start runs without the GitHub repo
    ops += [CommitOperationAdd("prompts.py", str(R / "tcg" / "prompts.py")),
            CommitOperationAdd("example_record.json", str(R / "hf" / "example_record.json"))]
    ops += [CommitOperationAdd(f"eval/{dst}", str(R / src)) for dst, src in
            (("RESULTS.md", "RESULTS.md"), ("summary.json", "results/summary.json"), ("error_analysis.md", "results/error_analysis.md"))]
    ops += [CommitOperationAdd(f"eval/predictions/{f.relative_to(R / 'predictions').as_posix()}", str(f))
            for f in sorted((R / "predictions").rglob("*")) if f.is_file()]
    push(config.HF_MODEL_REPO, "model", ops, "Adapter, model card and evaluation")


def dataset() -> None:
    ops = [CommitOperationAdd("README.md", card("hf/dataset_card.md"))]
    for dst, src in DATA_FILES.items():
        rows = read_jsonl(R / src)
        bad = [r["id"] for r in rows if r["source"] not in ("b_synthetic", "b_ood") or not r["id"].startswith("b-")]
        assert not bad, f"{src}: {len(bad)} records are not Project B's, e.g. {bad[:3]}"
        ops.append(CommitOperationAdd(f"data/{dst}", str(R / src)))
    ops += [CommitOperationAdd(f"contract/{f}", str(R / "contract" / f)) for f in ("schema_v0.json", "taxonomy_v0.md")]
    push(config.HF_DATA_REPO, "dataset", ops, "Toolcall Guard data v1 (Project B records only)")


def stage_release() -> None:
    """Stage the public dataset release in hf_release/dataset (git-ignored): the release card, the sanitized data files
    and the contract. Nothing is uploaded; the owner runs the move and upload commands."""
    out = R / "hf_release" / "dataset"
    san = R / "data" / "release_sanitized_v2"  # v2: contact details, real firms and registered domains replaced
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "contract").mkdir(exist_ok=True)
    (out / "README.md").write_bytes(card("hf/dataset_card.md"))
    for dst in DATA_FILES:
        rows = read_jsonl(san / dst)
        assert all(r["source"] in ("b_synthetic", "b_ood") and r["id"].startswith("b-") for r in rows), dst
        assert "@gmail.com" not in (san / dst).read_text(encoding="utf-8").replace("(@gmail.com)", "").replace("a @gmail.com", "").replace("*****@gmail.com", ""), dst
        (out / "data" / dst).write_bytes((san / dst).read_bytes())
    for f in ("schema_v0.json", "taxonomy_v0.md"):
        (out / "contract" / f).write_bytes((R / "contract" / f).read_bytes())
    (R / "hf_release" / "verbatim_README.md").write_bytes((R / "hf" / "verbatim_README.md").read_bytes())
    print("staged", sorted(str(f.relative_to(out)) for f in out.rglob("*") if f.is_file()))


def backup() -> bool:
    """Download both repos to hf_backup/ (git-ignored) and check every file against its local source by SHA-256."""
    import hashlib
    from huggingface_hub import snapshot_download
    ad = R / "adapters" / "real" / "adapter"
    sources = {"model": {"README.md": R / "hf" / "model_card.md", "adapter_config.json": ad / "adapter_config.json",
                         "prompts.py": R / "tcg" / "prompts.py", "example_record.json": R / "hf" / "example_record.json",
                         "adapter_model.safetensors": ad / "adapter_model.safetensors", "eval/RESULTS.md": R / "RESULTS.md",
                         "eval/summary.json": R / "results" / "summary.json", "eval/error_analysis.md": R / "results" / "error_analysis.md",
                         **{f"eval/predictions/{f.relative_to(R / 'predictions').as_posix()}": f
                            for f in (R / "predictions").rglob("*") if f.is_file()}},
               # the public dataset is the staged sanitized release (stage_release); the verbatim one is archived privately
               "dataset": {f.relative_to(R / "hf_release" / "dataset").as_posix(): f
                           for f in (R / "hf_release" / "dataset").rglob("*") if f.is_file()}}
    repos = {"model": config.HF_MODEL_REPO, "dataset": config.HF_DATA_REPO}
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    ok = True
    for kind, repo in repos.items():
        dest = R / "hf_backup" / kind
        snapshot_download(repo, repo_type=kind, local_dir=dest)
        remote = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file() and ".cache" not in p.parts}
        remote.discard(".gitattributes")
        for rel in sorted(remote | set(sources[kind])):
            src, got = sources[kind].get(rel), dest / rel
            same = src is not None and got.exists() and src.exists() and sha(src) == sha(got)
            ok &= same
            print(f"{kind:8s} {'MATCH' if same else 'DIFFERS'}  {rel}")
    return ok


if __name__ == "__main__":
    {"model": model, "dataset": dataset, "backup": backup, "stage-release": stage_release}[sys.argv[1]]()
