"""Sanitized release copy of the published dataset (a public release candidate). The verbatim files, which match what
the model trained on, are never touched: this writes new files under data/release_sanitized_v1/.
- Invented Gmail addresses: local@gmail.com -> local@example.com (example.com is reserved for documentation).
- Phone numbers: each distinct number (same digits in any format count as one) -> a unique, obviously fake number,
  +1-555-000-NNNN for North American numbers and +99-000-000-NNNN for international ones (+99 is not a country code).
  Distinct numbers stay distinct, so a scenario that contrasts a verified number with an attacker's keeps its meaning.
Labels, ids, families and splits are unchanged. Writes data/release_sanitized_v1/SANITIZED.json with the counts.
Usage: uv run python -m tcg.sanitize"""
import json
import re
from collections import Counter

from tcg import config
from tcg.data import read_jsonl, write_jsonl
from tcg.publish import DATA_FILES

OUT = config.ROOT / "data" / "release_sanitized_v1"
GMAIL = re.compile(r"([A-Za-z0-9._%+-]+)@gmail\.com\b", re.I)
NANP = re.compile(r"(?<![\w+-])(?:\+1[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?![\w-])")
INTL = re.compile(r"(?<![\w+])\+(?!1[\s.-]?[\d(])\d{1,3}(?:[\s.-]?\(?\d{1,5}\)?){2,5}(?![\w-])")


def main() -> dict:
    fakes, counts = {}, Counter()

    def fake(kind: str, digits: str) -> str:
        key = (kind, digits[-10:] if kind == "nanp" else digits)
        if key not in fakes:
            n = len(fakes) + 1
            fakes[key] = f"+1-555-000-{n:04d}" if kind == "nanp" else f"+99-000-000-{n:04d}"
        return fakes[key]

    def phone(kind):
        def sub(m):
            raw = m.group(0)
            trail = ")" if raw.endswith(")") and raw.count("(") < raw.count(")") else ""  # keep an unmatched closing parenthesis
            digits = re.sub(r"\D", "", raw)
            if kind == "intl" and len(digits) < 8:  # e.g. "+34.2" is a percentage, not a phone number
                return raw
            counts[f"phone_{kind}"] += 1
            return fake(kind, digits) + trail
        return sub

    def clean(x):
        if isinstance(x, str):
            x, n = GMAIL.subn(r"\1@example.com", x)
            counts["gmail"] += n
            x = NANP.sub(phone("nanp"), x)
            return INTL.sub(phone("intl"), x)
        if isinstance(x, list):
            return [clean(v) for v in x]
        if isinstance(x, dict):
            return {k: clean(v) for k, v in x.items()}
        return x

    OUT.mkdir(parents=True, exist_ok=True)
    report = {"files": {}}
    gmail_before = set()
    for dst, src in DATA_FILES.items():
        recs = read_jsonl(config.ROOT / src)
        for r in recs:
            gmail_before |= {m.lower() for m in GMAIL.findall(json.dumps(r, ensure_ascii=False))}
        before = dict(counts)
        out = [clean(r) for r in recs]
        keys = lambda r: (r["id"], r["family_id"], r["split"], (r.get("label") or {}).get("verdict"), (r.get("label") or {}).get("category"))
        assert [keys(o) for o in out] == [keys(r) for r in recs], f"{dst}: ids, splits or labels changed"
        write_jsonl(OUT / dst, out)
        report["files"][dst] = {"records": len(out), **{k: counts[k] - before.get(k, 0) for k in ("gmail", "phone_nanp", "phone_intl")}}
    left = sum(len(GMAIL.findall((OUT / d).read_text(encoding="utf-8"))) for d in DATA_FILES)
    report["totals"] = {"gmail_replaced": counts["gmail"], "distinct_gmail_addresses": len(gmail_before),
                        "phone_numbers_replaced": counts["phone_nanp"] + counts["phone_intl"],
                        "distinct_phone_numbers": len(fakes), "gmail_left_after": left}
    (OUT / "SANITIZED.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    assert left == 0
    print(json.dumps(report["totals"]))
    return report


if __name__ == "__main__":
    main()
