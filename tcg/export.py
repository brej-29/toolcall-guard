"""Everything worth keeping after teardown, under exports/:
  bucket     B's bucket prefixes (batch/, contract/, data/, tuning/ without the 16 GB merged model.safetensors copies)
             -> exports/bucket/  (a Google call: run before "no Google calls left")
  local      adapters/, the frozen dataset (data/v1, data/tuning, data/ood, A sets we scored on), state.json, COSTS.md,
             results/ (every baseline and guard output) -> exports/  (raw/ and ledger.jsonl are already written there)
  inventory  file count and size per exports/ folder, as a markdown table
  manifest   write exports/SHA256SUMS.txt (sha256, size, path for every file but itself)
  verify     re-hash every file listed in exports/SHA256SUMS.txt and report mismatches or missing files
Usage: uv run python -m tcg.export bucket|local|inventory|manifest|verify"""
import hashlib
import shutil
import sys

from tcg import config

E = config.EXPORTS
B_PREFIXES = ("batch/", "contract/", "data/", "tuning/")  # gold/ replay/ scenarios/ traces/ belong to Project A


def bucket() -> None:
    n = 0
    for b in config.storage_client().bucket(config.BUCKET).list_blobs():
        if not b.name.startswith(B_PREFIXES) or b.name.endswith("/") or b.name.split("/")[-1] == "model.safetensors":
            continue
        dest = E / "bucket" / b.name
        if dest.exists() and dest.stat().st_size == b.size:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        b.download_to_filename(str(dest))
        n += 1
    print(n, "objects downloaded to", E / "bucket")


def local() -> None:
    R = config.ROOT
    for src, dst in (("adapters", "adapters"), ("data/v1", "dataset/v1"), ("data/tuning", "dataset/tuning"),
                     ("data/ood", "dataset/ood"), ("data/a", "dataset/project_a_fetched"), ("results", "results"),
                     ("contract", "contract"), ("review", "review"), ("data/a/adaptive", "project_a_adaptive"),
                     ("data/a/pro_agent", "project_a_pro_agent"), ("data/release_sanitized_v1", "dataset_release_sanitized_v1"),
                     ("data/release_sanitized_v2", "dataset_release_sanitized_v2"),
                     ("hf", "hf_cards"), ("predictions", "predictions")):
        shutil.copytree(R / src, E / dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("laptop_int8.log"))  # 1.9 GB of warnings
    for f in ("state.json", "COSTS.md", "STATE.md", "RESULTS.md", "billing_gap.md"):
        if (R / f).exists():
            shutil.copy2(R / f, E / f)
    for p in R.glob("data/a_*.jsonl"):  # A records as scored here (gold, replay sample, full replay test)
        shutil.copy2(p, E / "dataset" / p.name)
    print("copied to", E)


def inventory() -> str:
    rows = ["| exports/ folder | files | size MB |", "|---|---|---|"]
    for d in sorted(p for p in E.iterdir() if p.is_dir()):
        files = [f for f in d.rglob("*") if f.is_file()]
        rows.append(f"| {d.name} | {len(files)} | {sum(f.stat().st_size for f in files) / 2**20:,.1f} |")
    top = [f for f in E.iterdir() if f.is_file()]
    rows.append(f"| (top level: {', '.join(f.name for f in top)}) | {len(top)} | {sum(f.stat().st_size for f in top) / 2**20:,.1f} |")
    print("\n".join(rows))
    return "\n".join(rows)


SUMS = E / "SHA256SUMS.txt"


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def manifest() -> None:
    files = sorted(f for f in E.rglob("*") if f.is_file() and f != SUMS)
    SUMS.write_text("".join(f"{sha256(f)}  {f.stat().st_size}  {f.relative_to(E).as_posix()}\n" for f in files), encoding="utf-8")
    print(f"{len(files)} files, {sum(f.stat().st_size for f in files) / 2**20:,.1f} MB -> {SUMS}")


def verify() -> bool:
    bad, n = [], 0
    for line in SUMS.read_text(encoding="utf-8").splitlines():
        digest, size, rel = line.split("  ", 2)
        f, n = E / rel, n + 1
        if not f.exists() or f.stat().st_size != int(size) or sha256(f) != digest:
            bad.append(rel)
    print(f"{n} files checked, {len(bad)} mismatched or missing", *bad[:10], sep="\n  ")
    return not bad


if __name__ == "__main__":
    {"bucket": bucket, "local": local, "inventory": inventory, "manifest": manifest, "verify": verify}[sys.argv[1]]()
