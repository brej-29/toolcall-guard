# Kaggle: full-precision (fp16 on two T4s) evaluation of one guard configuration over the test sets (JOB quant=int8:
# the LoRA merged into the base, then 8-bit).
# The dataset holds tcg/prompts.py (same render, prompts and parser as the local runs), the contract examples (for
# few-shot), the test sets and the adapters. JOB below is filled in by kaggle/push_eval.py for each kernel.
# Output: /kaggle/working/preds/<testset>/<guard>.jsonl in the same format as results/preds/ (resumable per kernel run).
JOB = {}  # replaced at push time

import glob  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers", "peft", "accelerate", "bitsandbytes"], check=True)
subprocess.run([sys.executable, "-m", "pip", "uninstall", "-q", "-y", "torchao"], check=False)  # old torchao breaks peft
import torch  # noqa: E402
from safetensors.torch import load_file  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

DATA = os.path.dirname(sorted(glob.glob("/kaggle/input/**/prompts.py", recursive=True))[0])
sys.path.insert(0, DATA)
from prompts import GUARD_SYSTEM, STUDENT_SYSTEM, parse_output, render  # noqa: E402

base = os.path.dirname(sorted(glob.glob("/kaggle/input/**/gemma-4-e4b-it/**/config.json", recursive=True))[-1])
tok = AutoTokenizer.from_pretrained(base)
ad = JOB["adapter"] and os.path.dirname(sorted(glob.glob(f"/kaggle/input/**/{JOB['adapter']}/adapter_config.json", recursive=True))[0])
if JOB.get("quant") == "int8":
    # LoRA merged into the bf16 base (W += alpha/r * B @ A), saved, then loaded with LLM.int8: the variant that kept
    # full-precision recall in the quantization test (kaggle/quant_test.py)
    import gc
    from transformers import BitsAndBytesConfig
    m = AutoModelForCausalLM.from_pretrained(base, dtype=torch.bfloat16, device_map={"": "cpu"})
    cfg = json.load(open(f"{ad}/adapter_config.json"))
    sd = {k.removeprefix("base_model.model."): v.float() for k, v in load_file(f"{ad}/adapter_model.safetensors").items()}
    with torch.no_grad():
        for k in [k for k in sd if k.endswith("lora_A.weight")]:
            mod = m.get_submodule(k.removesuffix(".lora_A.weight"))
            mod.weight += (cfg["lora_alpha"] / cfg["r"] * sd[k.replace("lora_A", "lora_B")] @ sd[k]).to(mod.weight.dtype)
    m.save_pretrained("/tmp/merged", safe_serialization=True)
    del m
    gc.collect()
    model = AutoModelForCausalLM.from_pretrained("/tmp/merged", dtype=torch.float16, device_map={"": 0}, quantization_config=BitsAndBytesConfig(
        load_in_8bit=True, llm_int8_skip_modules=["lm_head", "vision_tower", "audio_tower", "embed_vision", "embed_audio", "embed_tokens_per_layer"]))
else:
    model = AutoModelForCausalLM.from_pretrained(base, dtype=torch.float16, device_map="auto")
    if ad:
        from peft import LoraConfig, inject_adapter_in_model, set_peft_model_state_dict
        inject_adapter_in_model(LoraConfig.from_pretrained(ad), model)
        sd = {k.removeprefix("base_model.model."): v.to(torch.float16) for k, v in load_file(f"{ad}/adapter_model.safetensors").items()}
        assert not set_peft_model_state_dict(model, sd).unexpected_keys
model.eval()
dev = model.get_input_embeddings().weight.device

fewshot = []
for l in open(sorted(glob.glob("/kaggle/input/**/examples_v0.jsonl", recursive=True))[0], encoding="utf-8"):
    e = json.loads(l)
    fewshot += [{"role": "user", "content": render(e)},
                {"role": "assistant", "content": json.dumps({k: e["label"][k] for k in ("verdict", "category", "reason")})}]


@torch.inference_mode()
def decide(r):
    msgs = ([{"role": "system", "content": STUDENT_SYSTEM}] if JOB["mode"] == "student"
            else [{"role": "system", "content": GUARD_SYSTEM}] + fewshot) + [{"role": "user", "content": render(r)}]
    ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True).to(dev)
    t0 = time.perf_counter()
    out = model.generate(**ids, max_new_tokens=96, do_sample=False, output_scores=True, return_dict_in_generate=True)
    lat = time.perf_counter() - t0
    gen = out.sequences[0, ids["input_ids"].shape[1]:]
    text = tok.decode(gen, skip_special_tokens=True)
    vp = None
    for step, t in enumerate(gen.tolist()):
        piece = tok.decode([t]).strip().lower()
        if piece and ("allow".startswith(piece) or "block".startswith(piece)) and len(piece) >= 2:
            vp = float(torch.softmax(out.scores[step][0].float(), -1)[t])
            break
    return {"id": r["id"], "pred": parse_output(text), "latency_ms": round(lat * 1000, 1), "cost_usd": 0.0,
            "verdict_prob": vp, "tokens": [int(ids["input_ids"].shape[1]), int(gen.shape[0])], "raw": text,
            "precision": JOB.get("quant", "fp16"), "hardware": "kaggle T4" if JOB.get("quant") else "kaggle 2x T4"}


t_start = time.time()
for ts in JOB["sets"]:
    path = sorted(glob.glob(f"/kaggle/input/**/{ts}.jsonl", recursive=True))[0]
    recs = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    out_path = f"/kaggle/working/preds/{ts}/{JOB['guard']}.jsonl"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    done = {json.loads(l)["id"] for l in open(out_path, encoding="utf-8")} if os.path.exists(out_path) else set()
    for i, r in enumerate(x for x in recs if x["id"] not in done):
        if time.time() - t_start > JOB.get("max_hours", 11.3) * 3600:  # stay inside the 12 h session limit (or the quota)
            print("stopping before the session limit"); sys.exit(0)
        row = decide(r)
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        if i % 50 == 0:
            print(ts, i, round((time.time() - t_start) / 60), "min", flush=True)
    print(ts, "done", flush=True)
