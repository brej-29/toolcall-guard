# MCP server

`tcg/mcp_server.py` runs over stdio and uses the official `mcp` Python SDK (1.x).

```bash
uv run --no-project --with "mcp<2" python -m tcg.mcp_server
```

| env var | meaning |
|---|---|
| `GUARD_BACKEND` | `keyword` (default, no model, a floor), `local` (adapter, needs the `local` group and GPU or RAM), `gemini`, `cascade` |
| `GEMINI_API_KEY` | your own key, for `gemini` and `cascade`; never logged. Without it `cascade` stays local |
| `GUARD_GEMINI_MODEL` | hosted model, default `gemini-3.8-flash` |
| `GUARD_DEVICE`, `GUARD_PRECISION` | local backend: `cuda` or `cpu`, `full`, `8bit`, `4bit` (4-bit blocks far fewer attacks) |

Client config (shape of the common MCP format; the server starting and listing its three tools was verified, use inside each client was not tested):

```json
{"mcpServers": {"toolcall-guard": {"command": "uv",
  "args": ["run", "--no-project", "--with", "mcp<2", "python", "-m", "tcg.mcp_server"],
  "cwd": "/path/to/toolcall-guard", "env": {"GUARD_BACKEND": "keyword"}}}}
```

Tools: `check_tool_call(role, policy, proposed_call, tools?, conversation?, session_context?)` returns `{verdict, category, reason, source, escalated}`; `explain_categories()`; `cascade_stats()`.

This is a pre-execution check, not a security boundary. The `local` and `cascade` backends were not run end to end in this release (no GPU run after the MCP code was added).
