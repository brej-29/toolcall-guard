"""Error analysis for one guard: the 20 most confident misses (attacks allowed) and the 20 most confident false
positives (benign calls blocked), with a pattern summary. Writes results/error_analysis.md.
Usage: uv run python -m tcg.errors [--guard "gemma-4-e4b tuned (ours)"] [--sets synthetic_test review_100 a_gold ood]"""
import argparse
from collections import Counter

from tcg import config
from tcg.data import read_jsonl
from tcg.evaluate import PRED, p_block, testsets


def short(text: str, n: int = 140) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 3] + "..."


def main(guard: str, sets: list[str]) -> None:
    ts_all = testsets()
    misses, fps = [], []
    for ts in sets:
        recs = {r["id"]: r for r in ts_all.get(ts, [])}
        path = PRED / ts / f"{guard}.jsonl"
        if not recs or not path.exists():
            continue
        for p in read_jsonl(path):
            r = recs.get(p["id"])
            if not r:
                continue
            gold, pred = r["label"], p["pred"] or {"verdict": "block", "category": "invalid"}
            pb = p_block(p)
            notes = r.get("attack_notes") or {}
            row = {"set": ts, "id": r["id"], "gold": gold["category"], "pred": pred["category"], "p_block": pb,
                   "role": r["agent"]["role"], "technique": notes.get("technique", ""), "surface": notes.get("surface", ""),
                   "call": f"{r['proposed_call']['name']}", "reason": short(pred.get("reason", "")),
                   "gold_reason": short(gold.get("reason", ""))}
            if gold["verdict"] == "block" and pred["verdict"] == "allow":
                misses.append(row)
            elif gold["verdict"] == "allow" and pred["verdict"] == "block":
                fps.append(row)
    misses.sort(key=lambda x: (x["p_block"] if x["p_block"] is not None else 1))   # most confident allow first
    fps.sort(key=lambda x: -(x["p_block"] if x["p_block"] is not None else 0))      # most confident block first
    lines = [f"# Error analysis: {guard}", "", f"Test sets: {', '.join(sets)}. Misses: {len(misses)}. False positives: {len(fps)}.",
             "Ordered by confidence in the wrong verdict (P(block) at the verdict token).", ""]
    for title, rows in (("20 most confident misses (attacks allowed)", misses[:20]),
                        ("20 most confident false positives (benign blocked)", fps[:20])):
        lines += [f"## {title}", "", "| set | id | gold | P(block) | role | technique or hard-negative type | call | model reason |",
                  "|---|---|---|---|---|---|---|---|"]
        for x in rows:
            pb = "-" if x["p_block"] is None else f"{x['p_block']:.3f}"
            lines.append(f"| {x['set']} | {x['id']} | {x['gold']} | {pb} | {x['role']} | {short(x['technique'], 60)} | "
                         f"{x['call']} | {x['reason']} |")
        lines.append("")
    lines += ["## Patterns", ""]
    for title, rows in (("Misses", misses), ("False positives", fps)):
        lines.append(f"**{title}** by gold category: " + ", ".join(f"{k} {v}" for k, v in Counter(x["gold"] for x in rows).most_common()))
        lines.append(f"**{title}** by technique or hard-negative type (top 8): "
                     + ", ".join(f"{short(k, 50)} {v}" for k, v in Counter(x["technique"] for x in rows).most_common(8)))
        lines.append(f"**{title}** by surface (top 6): " + ", ".join(f"{k or '-'} {v}" for k, v in Counter(x["surface"] for x in rows).most_common(6)))
        lines.append("")
    (config.ROOT / "results" / "error_analysis.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("\n".join(lines[:6]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--guard", default="gemma-4-e4b tuned (ours)")
    ap.add_argument("--sets", nargs="+", default=["synthetic_test", "review_100", "a_gold", "ood"])
    a = ap.parse_args()
    main(a.guard, a.sets)
