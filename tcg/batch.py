"""Gemini batch jobs on Vertex. Each row gets the same cache key as the equivalent online request (tier "batch"),
its result is written to exports/raw/<phase>/<key>.json exactly like an online call, and its tokens go to the ledger.
Rows are matched by the key echoed in request.labels.row, never by position (output order is not input order).
Job names live in state.json, so submit/collect are idempotent and resumable."""
import datetime
import json
import time

from google.genai import types

from tcg import config, gemini

STATE = config.ROOT / "state.json"
BATCH_DIR = config.EXPORTS / "batch"


def _state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def _save_state(s: dict) -> None:
    STATE.write_text(json.dumps(s, indent=1), encoding="utf-8")


def make_request(prompt: str, *, model: str, phase: str, system: str | None = None, schema: dict | None = None,
                 thinking: str | None = "low", temperature: float | None = None, tag: str = "") -> tuple[str, dict, dict]:
    """Returns (key, cache request dict, Vertex batch request line)."""
    req = {"model": model, "system": system, "prompt": prompt, "schema": schema, "tier": "batch",
           "thinking": thinking, "temperature": temperature, "max_output_tokens": None, "tag": tag}
    key = gemini.request_key(req)
    gen = {}
    if schema:
        gen |= {"responseMimeType": "application/json", "responseJsonSchema": schema}
    if thinking:
        gen["thinkingConfig"] = {"thinkingLevel": thinking.upper()}
    if temperature is not None:
        gen["temperature"] = temperature
    line = {"request": {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": gen,
                        "labels": {**config.LABELS, "phase": phase, "row": key}}}
    if system:
        line["request"]["systemInstruction"] = {"parts": [{"text": system}]}
    return key, req, line


def submit(name: str, model: str, phase: str, rows: list[tuple[str, dict, dict]]) -> str:
    """rows from make_request. Skips rows already in the raw cache. Returns the job resource name."""
    s = _state()
    if name in s["batch_jobs"]:
        return s["batch_jobs"][name]["job"]
    todo = [(k, req, line) for k, req, line in rows if not (gemini.RAW / phase / f"{k}.json").exists()]
    d = BATCH_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "input.jsonl").write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for _, _, l in todo), encoding="utf-8")
    (d / "requests.json").write_text(json.dumps({k: req for k, req, _ in todo}, ensure_ascii=False), encoding="utf-8")
    bucket = config.storage_client().bucket(config.BUCKET)
    bucket.blob(f"batch/{name}/input.jsonl").upload_from_filename(str(d / "input.jsonl"))
    client = config.genai_client()
    job = client.batches.create(model=model, src=f"gs://{config.BUCKET}/batch/{name}/input.jsonl",
                                config=types.CreateBatchJobConfig(dest=f"gs://{config.BUCKET}/batch/{name}/output",
                                                                  display_name=f"tcg-{name}"))
    s = _state()
    s["batch_jobs"][name] = {"job": job.name, "model": model, "phase": phase, "rows": len(todo),
                             "submitted": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
                             "state": str(job.state), "collected": False}
    _save_state(s)
    return job.name


def status(name: str) -> str:
    s = _state()
    client = config.genai_client()  # keep a reference: a garbage-collected Client closes its HTTP session
    job = client.batches.get(name=s["batch_jobs"][name]["job"])
    s["batch_jobs"][name]["state"] = str(job.state)
    if job.end_time:
        s["batch_jobs"][name]["ended"] = job.end_time.isoformat()
    _save_state(s)
    return str(job.state)


def wait(name: str, every: int = 30, timeout: int = 6 * 3600) -> str:
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = status(name)
        if any(x in st for x in ("SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED", "PARTIALLY")):
            return st
        time.sleep(every)
    return status(name)


def collect(name: str) -> dict:
    """Download outputs, write raw cache files and ledger rows once. Returns {"ok": n, "errors": [...], "missing": [...]}."""
    s = _state()
    info = s["batch_jobs"][name]
    d = BATCH_DIR / name / "output"
    d.mkdir(parents=True, exist_ok=True)
    bucket = config.storage_client().bucket(config.BUCKET)
    lines = []
    for blob in bucket.list_blobs(prefix=f"batch/{name}/output"):
        local = d / blob.name.split(f"batch/{name}/output/", 1)[-1].replace("/", "__")
        blob.download_to_filename(str(local))
        if blob.name.endswith(".jsonl"):
            lines += [json.loads(l) for l in local.read_text(encoding="utf-8").splitlines() if l.strip()]
    reqs = json.loads((BATCH_DIR / name / "requests.json").read_text(encoding="utf-8"))
    ok, errors, seen = 0, [], set()
    for row in lines:
        key = row.get("request", {}).get("labels", {}).get("row")
        seen.add(key)
        resp = row.get("response") or {}
        cands = resp.get("candidates") or []
        if key not in reqs or not cands:
            errors.append({"key": key, "status": row.get("status")})
            continue
        text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []) if not p.get("thought"))
        um = resp.get("usageMetadata", {})
        usage = {"prompt_token_count": um.get("promptTokenCount", 0), "candidates_token_count": um.get("candidatesTokenCount", 0),
                 "thoughts_token_count": um.get("thoughtsTokenCount", 0),
                 "cached_content_token_count": um.get("cachedContentTokenCount", 0), "traffic_type": um.get("trafficType")}
        path = gemini.RAW / info["phase"] / f"{key}.json"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"key": key, "request": reqs[key], "text": text, "usage": usage, "latency_s": None,
                                        "ts": row.get("processed_time"), "batch": name, "response": resp},
                                       ensure_ascii=False), encoding="utf-8")
            gemini.record(info["phase"], info["model"], "batch", usage, key, kind="batch")
            ok += 1
    s = _state()
    s["batch_jobs"][name]["collected"] = True
    _save_state(s)
    return {"ok": ok, "errors": errors, "missing": sorted(set(reqs) - seen)}
