"""All settings come from .env. Project, location and bucket are always passed
explicitly: the machine's gcloud default project and ADC quota project point at a
different project, so nothing here may fall back to them."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "exports"


def _load_env() -> dict:
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"')
    os.environ.update(env)  # .env wins over anything inherited
    return env


ENV = _load_env()
PROJECT = ENV["GOOGLE_CLOUD_PROJECT"]
BUCKET = ENV["GCS_BUCKET"]
GEMINI_LOCATION = ENV["GEMINI_LOCATION"]
TUNING_LOCATION = ENV["TUNING_LOCATION"]
GEN_MODEL = ENV["GEN_MODEL"]
TEACHER_MODEL = ENV["TEACHER_MODEL"]
TUNE_BASE_MODEL = ENV["TUNE_BASE_MODEL"]
HF_BASE_MODEL = ENV["HF_BASE_MODEL"]
HF_MODEL_REPO = ENV["HF_MODEL_REPO"]
HF_DATA_REPO = ENV["HF_DATA_REPO"]
LABELS = {"project": ENV["RESOURCE_LABEL"]}

# USD per 1M tokens, from the Cloud Billing SKU catalog (service C7E2-9256-1C43) on 2026-10-05.
# 3.8 Flash SKU list price is 1.50/7.50; the pricing page advertises 0.75/3.75 "introductory"
# through 2026-12-31. The ledger uses the SKU price (conservative) until the Billing report shows otherwise.
PRICES = {
    (GEN_MODEL, "standard"): (1.50, 7.50),
    (GEN_MODEL, "flex"): (0.75, 3.75),
    (GEN_MODEL, "batch"): (0.75, 3.75),
    (TEACHER_MODEL, "standard"): (2.00, 12.00),
    (TEACHER_MODEL, "flex"): (1.00, 6.00),
    (TEACHER_MODEL, "batch"): (1.00, 6.00),
}
TUNING_PRICE_PER_M = 1.73  # Gemma 4 E4B managed OSS fine tuning, per 1M training tokens (dataset tokens x epochs)


def credentials():
    """ADC with the quota project forced to PROJECT (ADC file says otherwise)."""
    import google.auth
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds = creds.with_quota_project(PROJECT)
    assert creds.quota_project_id == PROJECT
    return creds


def genai_client(location: str = GEMINI_LOCATION):
    from google import genai
    from google.genai import types
    c = genai.Client(vertexai=True, project=PROJECT, location=location, credentials=credentials(),
                     http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=2)))  # user rule: at most one retry
    assert c._api_client.project == PROJECT and c._api_client.location == location
    return c


def storage_client():
    from google.cloud import storage
    c = storage.Client(project=PROJECT, credentials=credentials())
    assert c.project == PROJECT
    return c


def vertex_init(location: str = TUNING_LOCATION):
    import vertexai
    vertexai.init(project=PROJECT, location=location, credentials=credentials(),
                  staging_bucket=f"gs://{BUCKET}/staging")
