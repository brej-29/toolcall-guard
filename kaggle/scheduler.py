"""Keep at most 2 Kaggle GPU kernels busy (the account limit): push queued jobs when a slot frees, download each
kernel's predictions to results/kaggle_out/<job>/ when it completes, and log errors without retrying.
Run detached: python kaggle/scheduler.py  (log: results/kaggle_scheduler.log)"""
import datetime
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER = json.loads((Path.home() / ".kaggle" / "kaggle.json").read_text())["username"]
ORDER = ["tuned", "untuned-zs", "g5", "untuned-fs", "g5-val", "tuned-rest", "untuned-zs-rest", "quant", "tuned-adaptive", "untuned-zs-adaptive", "int8", "int8-tail"]
STATE = ROOT / "results" / "kaggle_scheduler.json"
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def log(msg: str) -> None:
    print(f"{datetime.datetime.now(datetime.UTC):%Y-%m-%d %H:%M} {msg}", flush=True)


def kaggle(*args) -> str:
    r = subprocess.run([shutil.which("uvx"), "kaggle", *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=ENV)
    return (r.stdout or "") + (r.stderr or "")


def status(job: str) -> str:
    out = kaggle("kernels", "status", f"{USER}/tcg-eval-{job}")
    for s in ("RUNNING", "QUEUED", "COMPLETE", "ERROR", "CANCEL"):
        if s in out.upper():
            return s
    return "UNKNOWN"


def main() -> None:
    st = json.loads(STATE.read_text()) if STATE.exists() else {"pushed": ["tuned", "untuned-zs"], "done": []}
    while True:
        running = 0
        for job in st["pushed"]:
            if job in st["done"]:
                continue
            s = status(job)
            if s in ("COMPLETE", "ERROR", "CANCEL"):
                out = ROOT / "results" / "kaggle_out" / job
                out.mkdir(parents=True, exist_ok=True)
                kaggle("kernels", "output", f"{USER}/tcg-eval-{job}", "-p", str(out))
                st["done"].append(job)
                log(f"{job}: {s}, outputs in {out}")
            elif s in ("RUNNING", "QUEUED", "UNKNOWN"):
                running += 1
        for job in ORDER:
            if running >= 2:
                break
            if job not in st["pushed"]:
                r = subprocess.run([sys.executable, str(ROOT / "kaggle" / "push_eval.py"), "kernel", job], capture_output=True,
                                   text=True, encoding="utf-8", errors="replace", env=ENV)
                ok = "successfully pushed" in (r.stdout + r.stderr)
                log(f"push {job}: {'ok' if ok else (r.stdout + r.stderr)[-300:]}")
                if ok:
                    st["pushed"].append(job)
                    running += 1
        STATE.write_text(json.dumps(st))
        if set(st["done"]) >= set(ORDER):
            log("all jobs finished")
            return
        time.sleep(300)


if __name__ == "__main__":
    main()
