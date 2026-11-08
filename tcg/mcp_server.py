"""MCP server (stdio) for the Toolcall Guard. Ask it before an agent runs a tool call.

GUARD_BACKEND = keyword (default, no model) | local (free, needs the 'local' group + the HF adapter)
              | gemini (needs your own GEMINI_API_KEY) | cascade (local first, Gemini only when unsure and a key exists)
GUARD_GEMINI_MODEL overrides the hosted model. The key is read from the environment only and never logged.
Run: uv run --group mcp python -m tcg.mcp_server
"""
import json
import os
from pathlib import Path

from tcg import keyword_guard
from tcg.prompts import ATTACKS, CATEGORIES, GUARD_SYSTEM, OUTPUT_SCHEMA, parse_output, render

ROOT = Path(__file__).resolve().parent.parent
_cache: dict = {}


def _record(role, policy, tools, conversation, proposed_call, session_context=""):
    return {"agent": {"role": role, "policy": policy, "session_context": session_context}, "tools": tools or [],
            "conversation": conversation or [], "proposed_call": proposed_call}


def _local(rec):
    from tcg import local_guard
    if "m" not in _cache:
        _cache["m"] = local_guard.load("BrejBala/gemma-toolcall-guard", device=os.environ.get("GUARD_DEVICE", "cuda"),
                                       precision=os.environ.get("GUARD_PRECISION", "full"))
    d = local_guard.decide(*_cache["m"], rec)
    return d["parsed"], d["verdict_prob"]


def _gemini(rec):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    from google import genai
    from google.genai import types
    resp = genai.Client(api_key=key).models.generate_content(
        model=os.environ.get("GUARD_GEMINI_MODEL", "gemini-3.8-flash"), contents=render(rec),
        config=types.GenerateContentConfig(system_instruction=GUARD_SYSTEM, response_mime_type="application/json",
                                           response_json_schema=OUTPUT_SCHEMA))
    return parse_output(resp.text) or {"verdict": "block", "category": "unspecified", "reason": "unparseable guard reply (fail closed)"}


def _bands():
    p = ROOT / "results" / "cascade_flash.json"
    s = json.loads(p.read_text(encoding="utf-8"))["selected"] if p.exists() else {"low": 0.05, "high": 1.0}
    return s["low"], s["high"]


def check(rec: dict, backend: str | None = None) -> dict:
    backend = backend or os.environ.get("GUARD_BACKEND", "keyword")
    if backend == "keyword":
        return {**keyword_guard.decide(rec), "source": "keyword", "escalated": False}
    if backend == "gemini":
        return {**_gemini(rec), "source": "gemini", "escalated": False}
    pred, prob = _local(rec)
    if backend == "local":
        return {**(pred or {"verdict": "block", "category": "unspecified", "reason": "unparseable (fail closed)"}),
                "source": "local", "escalated": False}
    from tcg.cascade import decide
    note = []
    def hosted():
        if not os.environ.get("GEMINI_API_KEY"):
            note.append("no GEMINI_API_KEY, stayed local")
            return pred or {"verdict": "block", "category": "unspecified", "reason": "unparseable (fail closed)"}
        return _gemini(rec)
    out, src = decide(pred, prob, hosted, *_bands())
    return {**out, "source": "gemini" if src == "hosted" and not note else "local", "escalated": src == "hosted", "note": note[0] if note else ""}


def build():
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("toolcall-guard")

    @mcp.tool()
    def check_tool_call(role: str, policy: str, proposed_call: dict, tools: list[dict] | None = None,
                        conversation: list[dict] | None = None, session_context: str = "") -> dict:
        """Check ONE proposed agent tool call before it runs. proposed_call = {"name": str, "arguments": {...}}.
        conversation items: {"role": "user"|"assistant"|"tool", "content": str, "name"?: str}. Returns
        {verdict: allow|block, category, reason, source, escalated}. A pre-execution check, not a security boundary."""
        return check(_record(role, policy, tools, conversation, proposed_call, session_context))

    @mcp.tool()
    def explain_categories() -> dict:
        """The 8 verdict categories and the precedence order used when several apply."""
        return {"categories": CATEGORIES, "attack_categories_in_precedence_order": ATTACKS,
                "allow_only_with": "benign"}

    @mcp.tool()
    def cascade_stats() -> dict:
        """Measured cascade results (adapter only vs hosted only vs cascade) from results/cascade_flash.json."""
        p = ROOT / "results" / "cascade_flash.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"error": "results/cascade_flash.json not found"}
    return mcp


if __name__ == "__main__":
    build().run()
