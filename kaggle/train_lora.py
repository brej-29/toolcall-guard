# Kaggle fallback: the same LoRA on Gemma 4 E4B IT, trained with TRL + peft on Kaggle's free GPU (T4 or P100).
# Input: a private Kaggle dataset with train.jsonl and val.jsonl in the same "messages" format used for Vertex
# managed tuning (system = student prompt, user = rendered decision record, assistant = teacher JSON label).
# Output: /kaggle/working/adapter (peft LoRA) + /kaggle/working/train_report.json
# Base weights: the attached Kaggle model google/gemma-4/transformers/gemma-4-e4b-it, else Hugging Face
# (then a Kaggle secret HF_TOKEN is needed).
import glob
import json
import os
import subprocess
import sys
import time

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers", "peft", "trl", "bitsandbytes", "accelerate"],
               check=True)

import torch  # noqa: E402
from datasets import Dataset  # noqa: E402
from peft import LoraConfig  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig  # noqa: E402
from trl import SFTConfig, SFTTrainer  # noqa: E402

# Settings: tcg_config.json next to train.jsonl in the dataset (Kaggle kernels take no env vars), else defaults.
_cfg_path = sorted(glob.glob("/kaggle/input/**/tcg_config.json", recursive=True))
CFG = json.load(open(_cfg_path[0])) if _cfg_path else {}
LIMIT = int(CFG.get("limit", 0))       # e.g. 200 for the smoke test, 0 = all
EPOCHS = float(CFG.get("epochs", 2))
RANK = int(CFG.get("rank", 16))
LR = float(CFG.get("lr", 2e-4))
MAX_LEN = int(CFG.get("max_len", 2048))
# Prefer the attached Kaggle model (google/gemma-4, transformers, gemma-4-e4b-it; Apache 2.0, no token needed).
_kaggle = sorted(glob.glob("/kaggle/input/**/gemma-4-e4b-it/**/config.json", recursive=True))
BASE = os.environ.get("BASE_DIR") or (os.path.dirname(_kaggle[-1]) if _kaggle else "google/gemma-4-E4B-it")
print("base weights:", BASE)

if not os.path.isdir(BASE):
    try:
        from kaggle_secrets import UserSecretsClient
        os.environ["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
    except Exception as e:  # running outside Kaggle, or no secret attached
        print("no Kaggle HF_TOKEN secret:", e)

data_dir = os.path.dirname(sorted(glob.glob("/kaggle/input/**/train.jsonl", recursive=True) or ["./train.jsonl"])[0])
read = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
train_rows = read(f"{data_dir}/train.jsonl")
val_rows = read(f"{data_dir}/val.jsonl") if os.path.exists(f"{data_dir}/val.jsonl") else []
if LIMIT:
    train_rows, val_rows = train_rows[:LIMIT], val_rows[: max(10, LIMIT // 10)]
print(f"train {len(train_rows)} val {len(val_rows)} from {data_dir}")

tok = AutoTokenizer.from_pretrained(BASE)
EOT = "<turn|>"  # Gemma 4 end of turn


def to_pc(row):
    m = row["messages"]
    return {"prompt": tok.apply_chat_template(m[:-1], tokenize=False, add_generation_prompt=True),
            "completion": m[-1]["content"] + EOT}


cap = torch.cuda.get_device_capability(0) if torch.cuda.is_available() else (0, 0)
bf16 = cap[0] >= 8  # T4 (7.5) and P100 (6.0) have no bf16
dtype = torch.bfloat16 if bf16 else torch.float16
model = AutoModelForCausalLM.from_pretrained(
    BASE, dtype=dtype, device_map="auto",
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=dtype,
                                           llm_int8_skip_modules=["vision_tower", "audio_tower", "embed_vision",
                                                                  "embed_audio", "lm_head"]))
print("gpu", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none", "bf16", bf16)

# Same targets as the Vertex managed job (language-model layers only; short names would also hit the vision tower),
# so a Kaggle adapter has the same keys and loads with the same code.
peft_cfg = LoraConfig(r=RANK, lora_alpha=2 * RANK, lora_dropout=0.0, task_type="CAUSAL_LM",
                      target_modules=r"model.language_model.layers.[\d]+.(mlp|self_attn).(up|down|gate|q|k|v|o)_proj")
args = SFTConfig(output_dir="/kaggle/working/run", num_train_epochs=EPOCHS, per_device_train_batch_size=1,
                 gradient_accumulation_steps=8, learning_rate=LR, lr_scheduler_type="cosine", warmup_steps=0.03,
                 logging_steps=10, eval_strategy="epoch" if val_rows else "no", save_strategy="no",
                 bf16=bf16, fp16=not bf16, gradient_checkpointing=True, max_length=MAX_LEN,
                 completion_only_loss=True, report_to="none", seed=20261005)
trainer = SFTTrainer(model=model, args=args, peft_config=peft_cfg, processing_class=tok,
                     train_dataset=Dataset.from_list([to_pc(r) for r in train_rows]),
                     eval_dataset=Dataset.from_list([to_pc(r) for r in val_rows]) if val_rows else None)
# fp16 AMP (T4/P100 have no bf16) needs fp32 trainable weights for the gradient scaler; LoRA came out bf16.
for prm in trainer.model.parameters():
    if prm.requires_grad:
        prm.data = prm.data.float()
print("trainable params:", sum(p.numel() for p in trainer.model.parameters() if p.requires_grad))
t0 = time.time()
result = trainer.train()
train_s = time.time() - t0
trainer.model.save_pretrained("/kaggle/working/adapter")
tok.save_pretrained("/kaggle/working/adapter")

# quick check on val: JSON validity and exact verdict/category match
trainer.model.eval()
ok = valid = 0
lat = []
for r in val_rows[:50]:
    m = r["messages"]
    ids = tok.apply_chat_template(m[:-1], add_generation_prompt=True, return_tensors="pt", return_dict=True).to(model.device)
    t1 = time.time()
    with torch.inference_mode():
        out = trainer.model.generate(**ids, max_new_tokens=96, do_sample=False)
    lat.append(time.time() - t1)
    text = tok.decode(out[0, ids["input_ids"].shape[1]:], skip_special_tokens=True)
    gold = json.loads(m[-1]["content"])
    try:
        pred = json.loads(text[text.index("{"): text.rindex("}") + 1])
        valid += 1
        ok += pred.get("verdict") == gold["verdict"] and pred.get("category") == gold["category"]
    except ValueError:
        pass
report = {"train_examples": len(train_rows), "epochs": EPOCHS, "rank": RANK, "lr": LR, "train_seconds": round(train_s),
          "train_loss": result.training_loss, "log": trainer.state.log_history,
          "val_checked": min(50, len(val_rows)), "val_json_valid": valid, "val_exact_match": ok,
          "val_median_latency_s": sorted(lat)[len(lat) // 2] if lat else None}
json.dump(report, open("/kaggle/working/train_report.json", "w"), indent=1)
print(json.dumps({k: v for k, v in report.items() if k != "log"}))
