"""Build site/data.json from repo results (no hand-typed numbers). Run: python site/build_data.py"""
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
from tcg.prompts import GUARD_SYSTEM, OUTPUT_SCHEMA
fig = json.loads((R / "assets/figures_data.json").read_text(encoding="utf-8"))
cas = json.loads((R / "results/cascade_flash.json").read_text(encoding="utf-8"))
ex = {json.loads(l)["id"]: json.loads(l) for l in (R / "hf/demo_examples.jsonl").read_text(encoding="utf-8").splitlines() if l}
pred = {json.loads(l)["id"]: json.loads(l) for l in (R / "results/demo_examples_8bit.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
presets = [{"id": i, "record": {k: r[k] for k in ("agent", "tools", "conversation", "proposed_call")},
            "model": pred[i]["pred"], "model_prob": pred[i]["verdict_prob"]} for i, r in ex.items() if i in pred]
(Path(__file__).parent / "data.json").write_text(json.dumps({"headline": fig["headline"], "cascade": cas, "presets": presets, "guard_system": GUARD_SYSTEM, "schema": OUTPUT_SCHEMA}, ensure_ascii=False), encoding="utf-8")
print("ok", len(presets), "presets", len(cas["curve_report_half"]), "curve points")
