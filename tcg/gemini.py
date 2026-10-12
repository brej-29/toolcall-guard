"""Single entry point for online Gemini calls. Every call is cached by content hash,
its raw request and response are saved to exports/raw/<phase>/<key>.json (synced to
gs://<bucket>/raw/ by sync_raw), and its tokens go to exports/ledger.jsonl."""
import datetime
import hashlib
import json
import shutil
import subprocess
import threading
import time

from google.genai import types

from tcg import config

RAW = config.EXPORTS / "raw"
LEDGER = config.EXPORTS / "ledger.jsonl"
FLEX_HEADERS = {"X-Vertex-AI-LLM-Request-Type": "shared", "X-Vertex-AI-LLM-Shared-Request-Type": "flex"}
_lock = threading.Lock()
_clients = {}


def _client():
    with _lock:
        if "c" not in _clients:
            _clients["c"] = config.genai_client()
        return _clients["c"]


def cost(model: str, tier: str, usage: dict) -> float:
    pin, pout = config.PRICES[(model, tier)]
    out = usage.get("candidates_token_count", 0) + usage.get("thoughts_token_count", 0)
    return (usage.get("prompt_token_count", 0) * pin + out * pout) / 1e6


def record(phase: str, model: str, tier: str, usage: dict, key: str, kind: str = "online") -> None:
    row = {"ts": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"), "phase": phase,
           "kind": kind, "model": model, "tier": tier, "key": key,
           "in": usage.get("prompt_token_count", 0), "out": usage.get("candidates_token_count", 0),
           "thoughts": usage.get("thoughts_token_count", 0), "cached": usage.get("cached_content_token_count", 0),
           "traffic_type": usage.get("traffic_type"), "usd": round(cost(model, tier, usage), 8)}
    with _lock, LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def request_key(req: dict) -> str:
    return hashlib.sha256(json.dumps(req, sort_keys=True).encode()).hexdigest()[:24]


def generate(prompt: str, *, phase: str, model: str = config.GEN_MODEL, system: str | None = None,
             schema: dict | None = None, tier: str = "standard", thinking: str | None = "low",
             temperature: float | None = None, max_output_tokens: int | None = None, tag: str = "",
             cache_only: bool = False) -> dict | None:
    """tag only changes the cache key, e.g. tag='pass2' for an independent second labeling pass.
    cache_only=True returns the cached entry or None and never calls the API."""
    req = {"model": model, "system": system, "prompt": prompt, "schema": schema, "tier": tier,
           "thinking": thinking, "temperature": temperature, "max_output_tokens": max_output_tokens, "tag": tag}
    key = request_key(req)
    path = RAW / phase / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if cache_only:
        return None
    cfg = types.GenerateContentConfig(
        system_instruction=system, temperature=temperature, max_output_tokens=max_output_tokens,
        response_mime_type="application/json" if schema else None, response_json_schema=schema,
        thinking_config=types.ThinkingConfig(thinking_level=thinking.upper()) if thinking else None,
        # Vertex selects Flex PayGo by headers (service_tier="flex" is rejected with 400). Flex can be slow: 15 min timeout.
        http_options=types.HttpOptions(headers=FLEX_HEADERS, timeout=900_000) if tier == "flex" else None,
        labels={**config.LABELS, "phase": phase})
    t0 = time.perf_counter()
    resp = _client().models.generate_content(
        model=model, contents=[types.Content(role="user", parts=[types.Part(text=prompt)])], config=cfg)
    latency = time.perf_counter() - t0
    usage = resp.usage_metadata.model_dump(mode="json", exclude_none=True) if resp.usage_metadata else {}
    out = {"key": key, "request": req, "text": resp.text, "usage": usage, "latency_s": round(latency, 3),
           "ts": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
           "response": resp.model_dump(mode="json", exclude_none=True)}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    record(phase, model, tier, usage, key)
    return out


def sync_raw() -> None:
    """Mirror exports/raw and the ledger to gs://<bucket>/raw (additive, never deletes)."""
    gcloud = shutil.which("gcloud")
    subprocess.run([gcloud, "storage", "cp", str(LEDGER), f"gs://{config.BUCKET}/raw/ledger.jsonl",
                    f"--project={config.PROJECT}"], check=True)
    subprocess.run([gcloud, "storage", "rsync", str(RAW), f"gs://{config.BUCKET}/raw", "--recursive",
                    f"--project={config.PROJECT}"], check=True)
