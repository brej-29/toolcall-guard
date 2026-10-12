"""Build the public GitHub release copy with a fresh, single-commit history in ../toolcall-guard-release.
Starts from the tracked files and leaves out: prediction files and Kaggle outputs, run logs and scripts, the verbatim
training data and review files (invented contact details), Project A's records, the project log and state, the
teardown script and copied documentation. As a safety net, any remaining file that contains an invented Gmail address
is left out too. Nothing is pushed: the owner creates the GitHub repo and pushes.
Usage: uv run python -m tcg.release_copy"""
import fnmatch
import os
import re
import stat
import shutil
import subprocess

from tcg import config

R = config.ROOT
DEST = R.parent / "toolcall-guard-release"
EXCLUDE = ["results/preds/*", "results/kaggle_out/*", "results/kaggle/*", "results/quant_local/*.jsonl",
           "results/adaptive/*.jsonl", "results/*.log", "results/*.err", "results/*.pid", "results/*.sh",
           "results/kaggle_scheduler.json", "results/sanitized_scan.json", "data/a/*", "data/a_*.jsonl",
           "data/tuning/*.jsonl", "data/release_sanitized_v*/*.jsonl", "data/feasibility/*", "data/v1/teacher_labels*.json", "review/*", "STATE.md",
           "state.json", "teardown.ps1", "docs_ref/*"]
AUTHOR = ["-c", "user.name=brej-29", "-c", "user.email=94220710+brej-29@users.noreply.github.com"]
GMAIL = re.compile(rb"[A-Za-z0-9._%+-]+@gmail\.com", re.I)


def main() -> None:
    files = subprocess.run(["git", "ls-files"], cwd=R, capture_output=True, text=True, check=True).stdout.split("\n")
    files = [f for f in files if f and not any(fnmatch.fnmatch(f, p) for p in EXCLUDE)]
    allow = {"tcg/sanitize.py"}  # its docstring shows the Gmail pattern it replaces; it holds no address
    dropped = [f for f in files if f not in allow and GMAIL.search((R / f).read_bytes())]
    files = [f for f in files if f not in dropped]
    if DEST.exists():
        shutil.rmtree(DEST, onexc=lambda fn, path, _: (os.chmod(path, stat.S_IWRITE), fn(path)))  # git objects are read-only on Windows
    for f in files:
        (DEST / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(R / f, DEST / f)
    git = lambda *a: subprocess.run(["git", *AUTHOR, *a], cwd=DEST, check=True, capture_output=True, text=True)
    git("init", "-b", "main")
    git("add", "-A")
    git("commit", "-m", "Toolcall Guard: code, contract, cards and results (public release)\n\n"
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    big = sorted(((DEST / f).stat().st_size, f) for f in files)[-3:]
    print(f"{len(files)} files in {DEST}; dropped for invented Gmail addresses: {dropped or 'none'}; largest: {big}")


if __name__ == "__main__":
    main()
