"""Rebuild COSTS.md from exports/ledger.jsonl. Run after every phase: uv run python -m tcg.costs"""
import json
from collections import defaultdict

from tcg import config

SOFT_STOP, HARD_CEILING = 70.0, 80.0  # soft stop raised by the user: 55 -> 65 (Wed) -> 70 (Thu 8 Oct)


def rows() -> list[dict]:
    p = config.EXPORTS / "ledger.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def total() -> float:
    return sum(r["usd"] for r in rows())


def main() -> None:
    agg = defaultdict(lambda: {"n": 0, "in": 0, "out": 0, "thoughts": 0, "train": 0, "usd": 0.0})
    for r in rows():
        a = agg[(r["phase"], r["kind"], r["model"], r["tier"])]
        a["n"] += 1
        for k in ("in", "out", "thoughts"):
            a[k] += r.get(k, 0)
        a["train"] += r.get("training_tokens", 0)
        a["usd"] += r["usd"]
    spent = sum(a["usd"] for a in agg.values())
    lines = [
        "# COSTS", "",
        "Generated from `exports/ledger.jsonl` by `uv run python -m tcg.costs`. Every online call and every batch",
        "row is logged with its `usage_metadata` tokens. Thinking tokens are billed as output.", "",
        f"**Total recorded: USD {spent:.4f}** (soft stop {SOFT_STOP:.0f}, hard ceiling {HARD_CEILING:.0f})", "",
        "## Price table (USD per 1M tokens)", "",
        "Source: Cloud Billing SKU catalog, service C7E2-9256-1C43, read 2026-10-05.", "",
        "| model | tier | input | output |", "|---|---|---|---|",
        *[f"| {m} | {t} | {pi} | {po} |" for (m, t), (pi, po) in config.PRICES.items()],
        f"| {config.TUNE_BASE_MODEL} | managed LoRA tuning | {config.TUNING_PRICE_PER_M} per 1M training tokens | |", "",
        "Note: the pricing page lists gemini-3.8-flash at 0.75 / 3.75 introductory through 2026-12-31, but the",
        "SKU list price for standard online is 1.50 / 7.50. The ledger uses the SKU price until the Billing report",
        "confirms which one is charged.", "",
        "## Spend by phase", "",
        "| phase | kind | model | tier | calls/rows | input tok | output tok | thinking tok | training tok | USD |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *[f"| {p} | {k} | {m} | {t} | {a['n']} | {a['in']} | {a['out']} | {a['thoughts']} | {a['train']} | {a['usd']:.4f} |"
          for (p, k, m, t), a in sorted(agg.items())],
        "",
    ]
    gap = config.ROOT / "billing_gap.md"  # hand-maintained comparison with the Billing report
    if gap.exists():
        lines += ["", gap.read_text(encoding="utf-8")]
    (config.ROOT / "COSTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"COSTS.md written, total USD {spent:.4f}")


if __name__ == "__main__":
    main()
