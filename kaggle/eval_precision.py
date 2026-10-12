# Kaggle check: does running the LoRA on a 4-bit base (as done locally on a 6 GB GPU) change the tuned model's verdicts
# compared with a full-precision base? Loads Gemma 4 E4B in fp16 across two T4s (no bf16 on T4), applies the adapter,
# and answers the records in records.jsonl (which carry the local 4-bit prediction in "local_pred").
# Output: /kaggle/working/precision_check.json
import glob
import json
import os
import subprocess
import sys
import time

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers", "peft", "accelerate"], check=True)
# Kaggle's image ships torchao 0.10, which current peft rejects while dispatching LoRA layers; it is not needed here
subprocess.run([sys.executable, "-m", "pip", "uninstall", "-q", "-y", "torchao"], check=False)
import torch  # noqa: E402
from peft import LoraConfig, inject_adapter_in_model, set_peft_model_state_dict  # noqa: E402
from safetensors.torch import load_file  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

base = os.path.dirname(sorted(glob.glob("/kaggle/input/**/gemma-4-e4b-it/**/config.json", recursive=True))[-1])
data_dir = os.path.dirname(sorted(glob.glob("/kaggle/input/**/records.jsonl", recursive=True))[0])
adapter = os.path.dirname(sorted(glob.glob("/kaggle/input/**/adapter_config.json", recursive=True))[0])
recs = [json.loads(l) for l in open(f"{data_dir}/records.jsonl", encoding="utf-8") if l.strip()]
print("base", base, "adapter", adapter, "records", len(recs), "gpus", torch.cuda.device_count())

tok = AutoTokenizer.from_pretrained(base)
model = AutoModelForCausalLM.from_pretrained(base, dtype=torch.float16, device_map="auto")
inject_adapter_in_model(LoraConfig.from_pretrained(adapter), model)
sd = {k.removeprefix("base_model.model."): v.to(torch.float16) for k, v in load_file(f"{adapter}/adapter_model.safetensors").items()}
res = set_peft_model_state_dict(model, sd)
assert not res.unexpected_keys, res.unexpected_keys[:5]
model.eval()

out, agree, valid = [], 0, 0
for r in recs:
    ids = tok.apply_chat_template(r["messages"], add_generation_prompt=True, return_tensors="pt", return_dict=True).to("cuda:0")
    t0 = time.time()
    with torch.inference_mode():
        g = model.generate(**ids, max_new_tokens=96, do_sample=False)
    text = tok.decode(g[0, ids["input_ids"].shape[1]:], skip_special_tokens=True)
    try:
        pred = json.loads(text[text.index("{"): text.rindex("}") + 1])
        valid += 1
    except ValueError:
        pred = None
    same = bool(pred) and pred.get("verdict") == (r["local_pred"] or {}).get("verdict")
    agree += same
    out.append({"id": r["id"], "fp16_pred": pred, "local_4bit_pred": r["local_pred"], "label": r["label"],
                "same_verdict": same, "seconds": round(time.time() - t0, 2), "raw": text[:300]})
report = {"n": len(recs), "fp16_json_valid": valid, "verdict_agreement_4bit_vs_fp16": agree,
          "fp16_verdict_correct": sum(bool(o["fp16_pred"]) and o["fp16_pred"].get("verdict") == o["label"]["verdict"] for o in out),
          "local_4bit_verdict_correct": sum(bool(o["local_4bit_pred"]) and o["local_4bit_pred"].get("verdict") == o["label"]["verdict"] for o in out),
          "rows": out}
json.dump(report, open("/kaggle/working/precision_check.json", "w"), indent=1)
print(json.dumps({k: v for k, v in report.items() if k != "rows"}))
