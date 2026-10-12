import json, sys, torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

repo = snapshot_download("BrejBala/gemma-toolcall-guard")  # adapter, prompts.py, example_record.json
sys.path.insert(0, repo)
from prompts import STUDENT_SYSTEM, render, parse_output  # the prompt and parser used in training and evaluation

tok = AutoTokenizer.from_pretrained("google/gemma-4-E4B-it")
model = AutoModelForCausalLM.from_pretrained("google/gemma-4-E4B-it", dtype=torch.bfloat16)  # full precision, about 16 GB RAM
model = PeftModel.from_pretrained(model, repo).merge_and_unload().eval()
record = json.load(open(f"{repo}/example_record.json", encoding="utf-8"))  # agent, tools, conversation, proposed_call
msgs = [{"role": "system", "content": STUDENT_SYSTEM}, {"role": "user", "content": render(record)}]
ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt", return_dict=True)
out = model.generate(**ids, max_new_tokens=96, do_sample=False)
print(parse_output(tok.decode(out[0, ids["input_ids"].shape[1]:], skip_special_tokens=True)))
