"""Run Gemma 4 E4B (optionally with a LoRA adapter) locally as the guard. Free: GPU (4-bit) or CPU.
Modes: student (short student prompt, what the tuned model was trained with) or fewshot (full guard prompt plus the
four contract examples; the distillation honesty check for the untuned model).
Usage:
  uv run python -m tcg.local_guard <records.jsonl> [--adapter DIR] [--mode student|fewshot] [--device cuda|cpu]
                                   [--n N] [--out results/preds/<testset>/<guard>.jsonl]
With --out, predictions are appended and records already present are skipped (resumable)."""
import argparse
import json
import time

import torch

from tcg import config
from tcg.prompts import GUARD_SYSTEM, STUDENT_SYSTEM, parse_output, render


GPU_MODULES = ["embed_tokens", "layers", "norm", "rotary_emb", "per_layer_model_projection", "per_layer_projection_norm"]
CPU_MODULES = ["model.language_model.embed_tokens_per_layer", "model.vision_tower", "model.audio_tower",
               "model.embed_vision", "model.embed_audio"]


def _ple_on_cpu(model) -> None:
    """accelerate treats cpu-mapped modules as offloaded (weights in RAM, executed on the GPU), which would copy the
    5.6 GB per-layer table into the 6 GB GPU at every forward. Materialize it in RAM, do the lookup on CPU, and move
    only its output to the GPU."""
    from accelerate.hooks import remove_hook_from_module
    from safetensors import safe_open
    from transformers.utils import cached_file
    ple = model.model.language_model.embed_tokens_per_layer
    remove_hook_from_module(ple)
    with safe_open(cached_file(config.HF_BASE_MODEL, "model.safetensors"), "pt", device="cpu") as f:
        key = next(k for k in f.keys() if k.endswith("embed_tokens_per_layer.weight"))
        ple.weight = torch.nn.Parameter(f.get_tensor(key).to(torch.bfloat16), requires_grad=False)
    ple.embed_scale = torch.tensor(ple.scalar_embed_scale)
    ple.register_forward_pre_hook(lambda m, args: tuple(a.to("cpu") for a in args))
    ple.register_forward_hook(lambda m, args, out: out.to("cuda:0"))


def _inject_adapter(model, adapter: str) -> None:
    """Add the LoRA layers in place and load their weights. PeftModel.from_pretrained would re-dispatch the whole model,
    which breaks the GPU/CPU split above. Accepts a local folder or a Hugging Face repo id."""
    import os
    from peft import LoraConfig, inject_adapter_in_model, set_peft_model_state_dict
    from safetensors.torch import load_file
    if not os.path.isdir(adapter):
        from huggingface_hub import snapshot_download
        adapter = snapshot_download(adapter)
    inject_adapter_in_model(LoraConfig.from_pretrained(adapter), model)
    sd = {k.removeprefix("base_model.model."): v for k, v in load_file(os.path.join(adapter, "adapter_model.safetensors")).items()}
    res = set_peft_model_state_dict(model, sd)
    lora = [n for n, _ in model.named_parameters() if "lora_" in n]
    assert not res.unexpected_keys and len(lora) == len(sd), (len(res.unexpected_keys), len(lora), len(sd))


def input_device(model) -> torch.device:
    return model.get_input_embeddings().weight.device  # model.device can be "meta" with offloaded towers


def load(adapter: str | None = None, device: str = "cuda", four_bit: bool = True, precision: str | None = None,
         base: str | None = None):
    """precision: "4bit" (6 GB GPU, decoder in 4-bit, per-layer embeddings on CPU) or "full" (bf16 on one GPU with at
    least 18 GB, or on CPU). Measured on 60 synthetic records, 4-bit blocked 29 of 40 attacks where full precision
    blocked 36, so prefer "full" when the hardware allows it. "8bit" is LLM.int8 with the same GPU/CPU split.
    base: a local merged checkpoint (tcg.quant_local merge) instead of the Hugging Face base."""
    if precision == "full" and device == "cuda":
        from transformers import AutoModelForCausalLM, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(config.HF_BASE_MODEL)
        model = AutoModelForCausalLM.from_pretrained(base or config.HF_BASE_MODEL, dtype=torch.bfloat16, device_map={"": 0})
        if adapter:
            _inject_adapter(model, adapter)
        return tok, model.eval()
    bits = (4 if four_bit else None) if precision is None else {"4bit": 4, "8bit": 8}.get(precision)
    return _load(adapter, device, bits, base or config.HF_BASE_MODEL)


def _load(adapter: str | None, device: str, bits: int | None, base: str):
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    tok = AutoTokenizer.from_pretrained(config.HF_BASE_MODEL)
    kw = {"dtype": torch.bfloat16}
    if device == "cuda":
        # 6 GB RTX 3050: decoder layers in 4-bit plus the tied embeddings go to the GPU (about 3.7 GB). The 2.8B-parameter
        # per-layer embedding table (a lookup, cheap on CPU) and the unused vision/audio towers stay in system RAM.
        kw["device_map"] = {**{f"model.language_model.{m}": 0 for m in GPU_MODULES}, "lm_head": 0,
                            **{m: "cpu" for m in CPU_MODULES}}
        if bits:
            q = {"load_in_4bit": True, "bnb_4bit_quant_type": "nf4", "bnb_4bit_compute_dtype": torch.bfloat16} if bits == 4 else {"load_in_8bit": True}
            kw["quantization_config"] = BitsAndBytesConfig(**q, llm_int8_enable_fp32_cpu_offload=True,
                                                           llm_int8_skip_modules=["lm_head", *CPU_MODULES])
    model = AutoModelForCausalLM.from_pretrained(base, **kw)
    if device == "cuda":
        _ple_on_cpu(model)
    if adapter:
        _inject_adapter(model, adapter)
    model.eval()
    return tok, model


def fewshot_messages() -> list[dict]:
    exs = [json.loads(l) for l in (config.ROOT / "contract" / "examples_v0.jsonl").read_text(encoding="utf-8").splitlines() if l]
    msgs = []
    for e in exs:
        msgs += [{"role": "user", "content": render(e)},
                 {"role": "assistant", "content": json.dumps({k: e["label"][k] for k in ("verdict", "category", "reason")})}]
    return msgs


@torch.inference_mode()
def decide(tok, model, record: dict, mode: str = "student", max_new_tokens: int = 96) -> dict:
    if mode == "student":
        msgs = [{"role": "system", "content": STUDENT_SYSTEM}]
    else:
        msgs = [{"role": "system", "content": GUARD_SYSTEM}] + fewshot_messages()
    msgs.append({"role": "user", "content": render(record)})
    ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True).to(input_device(model))
    t0 = time.perf_counter()
    out = model.generate(**ids, max_new_tokens=max_new_tokens, do_sample=False, output_scores=True,
                         return_dict_in_generate=True)
    latency = time.perf_counter() - t0
    gen = out.sequences[0, ids["input_ids"].shape[1]:]
    text = tok.decode(gen, skip_special_tokens=True)
    verdict_prob = None  # probability of the first generated allow/block token: confidence for error analysis
    for step, t in enumerate(gen.tolist()):
        piece = tok.decode([t]).strip().lower()
        if piece and ("allow".startswith(piece) or "block".startswith(piece)) and len(piece) >= 2:
            verdict_prob = float(torch.softmax(out.scores[step][0].float(), -1)[t])
            break
    return {"text": text, "parsed": parse_output(text), "latency_ms": round(latency * 1000, 1), "verdict_prob": verdict_prob,
            "input_tokens": int(ids["input_ids"].shape[1]), "output_tokens": int(gen.shape[0])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("records")
    ap.add_argument("--adapter")
    ap.add_argument("--mode", default="student", choices=["student", "fewshot"])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--n", type=int, default=0)
    ap.add_argument("--out")
    ap.add_argument("--precision", choices=["4bit", "8bit", "full"], default="4bit")
    ap.add_argument("--base", help="local merged checkpoint (tcg.quant_local merge) instead of the Hugging Face base")
    a = ap.parse_args()
    recs = [json.loads(l) for l in open(a.records, encoding="utf-8") if l.strip()]
    recs = recs[: a.n] if a.n else recs
    done = set()
    if a.out:
        from pathlib import Path
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        if Path(a.out).exists():
            done = {json.loads(l)["id"] for l in open(a.out, encoding="utf-8") if l.strip()}
    t0 = time.time()
    tok, model = load(a.adapter, a.device, precision=a.precision, base=a.base)
    print(f"loaded in {time.time() - t0:.0f}s on {a.device}",
          f"gpu mem {torch.cuda.max_memory_allocated() / 2**30:.1f} GiB" if a.device == "cuda" else "", flush=True)
    for r in recs:
        if r["id"] in done:
            continue
        d = decide(tok, model, r, a.mode)
        row = {"id": r["id"], "pred": d["parsed"], "latency_ms": d["latency_ms"], "cost_usd": 0.0,
               "verdict_prob": d["verdict_prob"], "tokens": [d["input_tokens"], d["output_tokens"]], "raw": d["text"],
               "precision": a.precision, "hardware": torch.cuda.get_device_name(0) if a.device == "cuda" else "cpu"}
        if a.out:
            with open(a.out, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(json.dumps({"id": r["id"], "label": r["label"], **{k: row[k] for k in ("pred", "latency_ms", "verdict_prob")},
                          "raw": d["text"][:160]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
