"""Local Gradio demo (not deployed anywhere): paste one tool call with its context and get the guard's verdict.
The input is a decision record in the contract shape (contract/schema_v0.json); only agent, tools, conversation and
proposed_call are read. Pick an example to start from.
  uv run --group demo python demo.py                          # 6 GB GPU, 4-bit base (misses more attacks)
  uv run --group demo python demo.py --precision 8bit --base merged/real   # 6 GB GPU, 8-bit, matches full precision
  uv run --group demo python demo.py --device cpu             # CPU, full precision bf16, about 16 GB RAM
  uv run --group demo python demo.py --adapter BrejBala/gemma-toolcall-guard
Gradio serves on 127.0.0.1 only."""
import argparse
import json

import gradio as gr

from tcg import config
from tcg.local_guard import decide, load

NEEDED = {"agent": dict, "tools": list, "conversation": list, "proposed_call": dict}
EXAMPLES = [json.loads(l) for l in (config.ROOT / "contract" / "examples_v0.jsonl").read_text(encoding="utf-8").splitlines() if l]


def as_input(r: dict) -> str:
    return json.dumps({k: r[k] for k in NEEDED}, indent=1, ensure_ascii=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="adapters/real/adapter", help="local folder or Hugging Face repo id")
    ap.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    ap.add_argument("--precision", choices=["4bit", "8bit", "full"], help="default: full on CPU, 4bit on GPU")
    ap.add_argument("--base", help="merged checkpoint for 8-bit (uv run python -m tcg.quant_local merge); then omit --adapter")
    a = ap.parse_args()
    precision = a.precision or ("full" if a.device == "cpu" else "4bit")
    tok, model = load(None if a.base else a.adapter, a.device, precision=precision, base=a.base)

    def judge(text: str):
        try:
            r = json.loads(text)
        except json.JSONDecodeError as e:
            return {"error": f"not valid JSON: {e}"}, ""
        bad = [k for k, t in NEEDED.items() if not isinstance(r.get(k), t)]
        if bad or not {"role", "policy"} <= set(r["agent"]) or "name" not in r["proposed_call"]:
            return {"error": f"need {', '.join(NEEDED)}; agent needs role and policy; proposed_call needs name (missing or wrong: {bad})"}, ""
        d = decide(tok, model, r)
        out = d["parsed"] or {"verdict": "block", "category": "invalid", "reason": "invalid guard output, fail-closed"}
        return out, f"{d['latency_ms'] / 1000:.1f} s, {d['input_tokens']} prompt tokens, raw: {d['text']}"

    with gr.Blocks(title="Toolcall Guard demo") as ui:
        gr.Markdown("## Toolcall Guard (Gemma 4 E4B + LoRA)\nA second opinion before an agent runs a tool call. "
                    "Not a security boundary: it misses attacks.")
        pick = gr.Dropdown([f"{i}: {e['label']['category']}" for i, e in enumerate(EXAMPLES)], label="Example")
        box = gr.Code(as_input(EXAMPLES[0]), language="json", label="Decision record (agent, tools, conversation, proposed_call)")
        go = gr.Button("Judge", variant="primary")
        verdict, info = gr.JSON(label="Verdict"), gr.Textbox(label="Latency and raw output")
        pick.change(lambda p: as_input(EXAMPLES[int(p.split(":")[0])]), pick, box)
        go.click(judge, box, [verdict, info])
    ui.launch(server_name="127.0.0.1")


if __name__ == "__main__":
    main()
