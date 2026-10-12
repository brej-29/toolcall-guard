# Kaggle: quantization recovery test on the 60-record precision check set (40 attacks, 20 benign, synthetic test).
# Variants: fp16 base + LoRA (reference), nf4 base + LoRA (the laptop setup), LoRA merged into the base (rebuilt here
# from the adapter and the base, nothing from the bucket) in fp16, int8 and nf4, and GGUF Q6_K / Q5_K_M of the merged
# model through llama.cpp (built here). Same prompt, greedy decoding, 96 new tokens. JOB is filled in by push_eval.py.
# Output: /kaggle/working/quant/<variant>.jsonl and /kaggle/working/quant/summary.json
JOB = {}  # replaced at push time

import gc  # noqa: E402
import glob  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import urllib.request  # noqa: E402

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers", "peft", "accelerate", "bitsandbytes"], check=True)
subprocess.run([sys.executable, "-m", "pip", "uninstall", "-q", "-y", "torchao"], check=False)
import torch  # noqa: E402
from safetensors.torch import load_file  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig  # noqa: E402

DATA = os.path.dirname(sorted(glob.glob("/kaggle/input/**/prompts.py", recursive=True))[0])
sys.path.insert(0, DATA)
from prompts import STUDENT_SYSTEM, parse_output, render  # noqa: E402

BASE = os.path.dirname(sorted(glob.glob("/kaggle/input/**/gemma-4-e4b-it/**/config.json", recursive=True))[-1])
AD = os.path.dirname(sorted(glob.glob("/kaggle/input/**/adapters/real/adapter_config.json", recursive=True))[0])
recs = [json.loads(l) for l in open(sorted(glob.glob("/kaggle/input/**/synthetic_test.jsonl", recursive=True))[0], encoding="utf-8")]
recs = [r for r in recs if r["id"] in set(JOB["ids"])]
assert len(recs) == 60, len(recs)
OUT, MERGED = "/kaggle/working/quant", "/tmp/merged"
os.makedirs(OUT, exist_ok=True)
tok = AutoTokenizer.from_pretrained(BASE)
SKIP = ["lm_head", "vision_tower", "audio_tower", "embed_vision", "embed_audio", "embed_tokens_per_layer"]
summary = {}


def msgs(r):
    return [{"role": "system", "content": STUDENT_SYSTEM}, {"role": "user", "content": render(r)}]


def finish(name, rows, extra=None):
    with open(f"{OUT}/{name}.jsonl", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in rows)
    att = [x for x in rows if x["gold"] == "block"]
    ben = [x for x in rows if x["gold"] == "allow"]
    v = lambda x: (x["pred"] or {"verdict": "block"})["verdict"]  # invalid output = fail-closed block
    lat = sorted(x["latency_ms"] for x in rows)
    summary[name] = {"attacks_blocked": sum(v(x) == "block" for x in att), "attacks": len(att),
                     "false_positives": sum(v(x) == "block" for x in ben), "benign": len(ben),
                     "correct": sum(v(x) == x["gold"] for x in rows), "json_valid": sum(x["pred"] is not None for x in rows),
                     "median_latency_ms": lat[len(lat) // 2], **(extra or {})}
    json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
    print(name, summary[name], flush=True)


def inject(model):
    from peft import LoraConfig, inject_adapter_in_model, set_peft_model_state_dict
    inject_adapter_in_model(LoraConfig.from_pretrained(AD), model)
    sd = {k.removeprefix("base_model.model."): v.to(torch.float16) for k, v in load_file(f"{AD}/adapter_model.safetensors").items()}
    assert not set_peft_model_state_dict(model, sd).unexpected_keys


@torch.inference_mode()
def run_hf(name, model):
    dev = model.get_input_embeddings().weight.device
    torch.cuda.reset_peak_memory_stats()
    rows = []
    for r in recs:
        ids = tok.apply_chat_template(msgs(r), add_generation_prompt=True, return_tensors="pt", return_dict=True).to(dev)
        t0 = time.perf_counter()
        out = model.generate(**ids, max_new_tokens=96, do_sample=False)
        lat = (time.perf_counter() - t0) * 1000
        text = tok.decode(out[0, ids["input_ids"].shape[1]:], skip_special_tokens=True)
        rows.append({"id": r["id"], "gold": r["label"]["verdict"], "pred": parse_output(text), "latency_ms": round(lat, 1), "raw": text})
    finish(name, rows, {"peak_gpu_gib": round(max(torch.cuda.max_memory_allocated(i) for i in range(torch.cuda.device_count())) / 2**30, 2),
                        "hardware": "kaggle T4"})


def free():  # callers drop their reference first (del m)
    gc.collect()
    torch.cuda.empty_cache()


def bnb(kind):
    if kind == "nf4":
        return BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16,
                                  llm_int8_skip_modules=SKIP)
    return BitsAndBytesConfig(load_in_8bit=True, llm_int8_skip_modules=SKIP)


PARTS = JOB.get("parts", ["hf", "gguf"])
GPU = JOB.get("gguf_device", "cuda") == "cuda"

# 1) reference and the laptop setup: base + unmerged LoRA
if "hf" in PARTS:
    m = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.float16, device_map="auto")
    inject(m)
    run_hf("fp16_base+lora", m.eval())
    del m
    free()
    m = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.float16, device_map={"": 0}, quantization_config=bnb("nf4"))
    inject(m)
    run_hf("nf4_base+lora", m.eval())
    del m
    free()

# 2) merge: W += (alpha / r) * B @ A on the bf16 base in system RAM, then save the merged checkpoint
cfg = json.load(open(f"{AD}/adapter_config.json"))
scale = cfg["lora_alpha"] / cfg["r"]
m = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.bfloat16, device_map={"": "cpu"})
sd = {k.removeprefix("base_model.model."): v.float() for k, v in load_file(f"{AD}/adapter_model.safetensors").items()}
n = 0
with torch.no_grad():
    for k in [k for k in sd if k.endswith("lora_A.weight")]:
        mod = m.get_submodule(k.removesuffix(".lora_A.weight"))
        mod.weight += (scale * sd[k.replace("lora_A", "lora_B")] @ sd[k]).to(mod.weight.dtype)
        n += 1
print("merged", n, "LoRA pairs, scale", scale, flush=True)
m.save_pretrained(MERGED, safe_serialization=True)
tok.save_pretrained(MERGED)
del m
free()

for name, kw in [] if "hf" not in PARTS else (("merged_fp16", {"dtype": torch.float16, "device_map": "auto"}),
                 ("merged_int8", {"dtype": torch.float16, "device_map": {"": 0}, "quantization_config": bnb("int8")}),
                 ("merged_nf4", {"dtype": torch.float16, "device_map": {"": 0}, "quantization_config": bnb("nf4")})):
    try:
        m = AutoModelForCausalLM.from_pretrained(MERGED, **kw)
        run_hf(name, m.eval())
        del m
        free()
    except Exception as e:  # noqa: BLE001
        summary[name] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
        print(name, summary[name], flush=True)

# 3) GGUF through llama.cpp (CUDA build for the T4, sm_75); any failure is recorded, not fatal
try:
    assert "gguf" in PARTS, "gguf not requested in this run"
    L = "/tmp/llama.cpp"
    sh = lambda c: subprocess.run(c, shell=True, check=True)
    t0 = time.time()
    sh(f"git clone --depth 1 https://github.com/ggml-org/llama.cpp {L}")
    cuda = "-DGGML_CUDA=ON -DGGML_CUDA_NO_VMM=ON -DCMAKE_CUDA_ARCHITECTURES=75" if GPU else ""  # NO_VMM: no libcuda stub needed
    sh(f"cmake -S {L} -B {L}/build {cuda} -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release > /tmp/cmake.log 2>&1 || (tail -30 /tmp/cmake.log; exit 1)")
    sh(f"cmake --build {L}/build -j {os.cpu_count()} --target llama-quantize llama-server > /tmp/build.log 2>&1 || (tail -30 /tmp/build.log; exit 1)")
    sh(f"{sys.executable} -m pip install -q {L}/gguf-py sentencepiece protobuf")
    sh(f"{sys.executable} {L}/convert_hf_to_gguf.py {MERGED} --outtype f16 --outfile /tmp/m-f16.gguf")
    sh(f"rm -rf {MERGED}")  # disk: keep at most two 15 GB copies
    print("llama.cpp built and converted in", round(time.time() - t0), "s", flush=True)
    for q in ("Q6_K", "Q5_K_M"):
        sh(f"{L}/build/bin/llama-quantize /tmp/m-f16.gguf /tmp/m-{q}.gguf {q}")
    os.remove("/tmp/m-f16.gguf")  # disk: the f16 GGUF is about 15 GB
    for q in ("Q6_K", "Q5_K_M"):
        size = round(os.path.getsize(f"/tmp/m-{q}.gguf") / 2**30, 2)
        srv = subprocess.Popen([f"{L}/build/bin/llama-server", "-m", f"/tmp/m-{q}.gguf", "-ngl", "99" if GPU else "0", "-t", str(os.cpu_count()), "-c", "8192",
                                "--port", "8080", "-np", "1"], stdout=open(f"/tmp/server-{q}.log", "w"), stderr=subprocess.STDOUT)
        for _ in range(180):
            try:
                urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=2)
                break
            except Exception:  # noqa: BLE001
                time.sleep(2)
        rows = []
        for r in recs:
            # the exact HF prompt text; llama.cpp adds BOS itself, so the template's leading <bos> is dropped
            prompt = tok.apply_chat_template(msgs(r), add_generation_prompt=True, tokenize=False).removeprefix(tok.bos_token)
            body = json.dumps({"prompt": prompt, "n_predict": 96, "temperature": 0, "top_k": 1, "cache_prompt": False}).encode()
            t0 = time.perf_counter()
            resp = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8080/completion", body,
                                                                            {"Content-Type": "application/json"}), timeout=300))
            lat = (time.perf_counter() - t0) * 1000
            text = resp["content"]
            rows.append({"id": r["id"], "gold": r["label"]["verdict"], "pred": parse_output(text), "latency_ms": round(lat, 1), "raw": text})
        srv.terminate()
        srv.wait()
        finish(f"gguf_{q}", rows, {"file_gib": size, "hardware": "kaggle T4, llama.cpp all layers on GPU" if GPU else
                                   f"kaggle CPU ({os.cpu_count()} threads), llama.cpp"})
except Exception as e:  # noqa: BLE001
    summary["gguf"] = {"error": f"{type(e).__name__}: {str(e)[:300]}"}
    json.dump(summary, open(f"{OUT}/summary.json", "w"), indent=1)
    print("gguf", summary["gguf"], flush=True)
print(json.dumps(summary, indent=1))
