"""Sanitized release v2: data/release_sanitized_v1 -> data/release_sanitized_v2. Same approach as Project A's
scripts/sanitize_release.py:
- Real firms used as scenario parties (auditors, banks, carriers) get clearly fictional names. Product names that only
  describe an item (card brands, CPU and device models, tools) are kept.
- Domains in emails, URLs and bare mentions are matched as whole host names. Every registrable domain is checked in
  DNS after the firm replacement. Registered domains of real providers and companies become <name>.example; registered
  domains that the scenarios invented get ".test" appended, so they stay visibly lookalike but cannot resolve.
  Unregistered and reserved domains are left as they are.
Labels (verdict and category), ids, families and splits are unchanged; label reasons get the same replacements.
Writes data/release_sanitized_v2/ and SANITIZED.json with counts per replacement.
Usage: uv run python -m tcg.sanitize_v2"""
import json
import re
import socket
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from tcg import config
from tcg.data import read_jsonl, write_jsonl
from tcg.publish import DATA_FILES

SRC, OUT = config.ROOT / "data" / "release_sanitized_v1", config.ROOT / "data" / "release_sanitized_v2"
# longest first, so "JPMorgan Chase" is replaced before "JPMorgan"
FIRMS = [("JPMorgan Chase", "Harbor Union Bank"), ("Chase Bank", "Harbor Union Bank"), ("Chase bank", "Harbor Union bank"), ("JPMorgan", "Harbor Union"),
         ("jpmorgan", "harborunion"), ("Wells Fargo", "Wellspring"), ("Bank of America", "Bank of Avalon"),
         ("PNC Bank", "Pinecrest Bank"), ("PNC", "Pinecrest"), ("KPMG", "Kestrel Audit"), ("kpmg", "kestrelaudit"),
         ("Deloitte", "Dellmont"), ("DELOITTE", "DELLMONT"), ("deloitte", "dellmont"), ("DHL Express", "Dalton Express"),
         ("DHL", "Dalton"), ("dhl", "dalton"), ("FedEx", "Fastway"), ("FEDEX", "FASTWAY"), ("fedex", "fastway")]
FIRM_RX = [(a, re.compile(r"(?<![A-Za-z])" + re.escape(a) + r"(?![A-Za-z])"), b) for a, b in FIRMS]
PROVIDERS = {"okta.com", "googleapis.com", "google.com", "run.app", "amazonaws.com", "outlook.com", "yahoo.com",
             "hotmail.com", "proton.me", "fastmail.com", "fastmail.es", "fastmail.it", "fastmail.ro", "pastebin.com",
             "pastebin.run", "webhook.site", "github.com", "githubusercontent.com", "dropbox.com", "dropboxapi.com",
             "verizon.net", "virgilio.it", "filebin.net", "email.com", "domain.com", "acme.com", "gmail.com", "box.com",
             "gcr.io", "pkg.dev"}
KEEP = {"knative.dev"}  # a Kubernetes API group name (serving.knative.dev/v1), a technical identifier, not a destination
TLDS = ("com", "net", "org", "io", "co", "ai", "app", "dev", "tech", "biz", "info", "us", "uk", "de", "it", "es", "fr", "in",
        "eu", "cloud", "site", "online", "xyz", "me", "mx", "ch", "ro", "health", "run", "nz", "ca", "au", "jp")
HOST = re.compile(r"(?<![A-Za-z0-9.\-])((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})(?![A-Za-z0-9\-]|\.[A-Za-z0-9])")
SEEN = re.compile(r"@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)|https?://(?:www\.)?([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
RESERVED = re.compile(r"(\.(example|test|invalid|localhost|local|internal)$)|(^|\.)example\.(com|org|net)$", re.I)


def registrable(host: str) -> str:
    p = host.lower().split(".")
    return ".".join(p[-3:]) if len(p) > 2 and p[-2] in ("co", "com", "org", "net", "gov", "ac") else ".".join(p[-2:])


def bare_host(m, any_tld: bool = False) -> bool:
    """A host-name match that is not an email local part (followed by "@") or a call (followed by "(")."""
    nxt = m.string[m.end(): m.end() + 1]
    return nxt not in ("@", "(") and (any_tld or m.group(1).lower().rsplit(".", 1)[-1] in TLDS)


def resolves(d: str) -> bool:
    try:
        socket.getaddrinfo(d, None)
        return True
    except OSError:
        return False


def main() -> dict:
    counts = Counter()

    def firms(x):
        if isinstance(x, str):
            for key, rx, rep in FIRM_RX:
                x, n = rx.subn(rep, x)
                counts[f"firm: {key}"] += n
            return x
        if isinstance(x, list):
            return [firms(v) for v in x]
        if isinstance(x, dict):
            return {k: firms(v) for k, v in x.items()}
        return x

    staged = {dst: [firms(r) for r in read_jsonl(SRC / dst)] for dst in DATA_FILES}
    text = "\n".join(json.dumps(r, ensure_ascii=False) for rows in staged.values() for r in rows)
    regs = {registrable(h) for m in SEEN.finditer(text) for h in m.groups() if h and not RESERVED.search(h)}
    # bare host names too (not email local parts, not code calls such as logger.info(...))
    regs |= {registrable(m.group(1)) for m in HOST.finditer(text) if bare_host(m) and not RESERVED.search(m.group(1))}
    regs -= KEEP
    regs = {r for r in regs if re.search(r"[A-Za-z]", r.split(".")[-1])}  # skip numeric fragments such as "100.4"
    socket.setdefaulttimeout(4)
    with ThreadPoolExecutor(32) as ex:
        live = {r for r, ok in zip(sorted(regs), ex.map(resolves, sorted(regs))) if ok}

    def host_sub(m):
        h = m.group(1)
        r = registrable(h)
        if r not in live or RESERVED.search(h) or not bare_host(m, any_tld=True):
            return h
        if r in PROVIDERS:
            name, tld = r.split(".", 1)
            new_r = (name if tld == "com" else f"{name}-{tld.replace('.', '-')}") + ".example"
            counts[f"provider domain -> .example: {r}"] += 1
            return h[: len(h) - len(r)] + new_r
        counts["invented registered domain -> +.test"] += 1
        return h + ".test"

    def domains(x):
        if isinstance(x, str):
            return HOST.sub(host_sub, x)
        if isinstance(x, list):
            return [domains(v) for v in x]
        if isinstance(x, dict):
            return {k: domains(v) for k, v in x.items()}
        return x

    OUT.mkdir(parents=True, exist_ok=True)
    report = {"registrable_domains_checked": len(regs), "registered": len(live),
              "registered_providers": sorted(live & PROVIDERS), "files": {}}
    keys = lambda r: (r["id"], r["family_id"], r["split"], (r.get("label") or {}).get("verdict"), (r.get("label") or {}).get("category"))
    for dst, rows in staged.items():
        out = [domains(r) for r in rows]
        assert [keys(o) for o in out] == [keys(r) for r in read_jsonl(SRC / dst)], f"{dst}: ids, splits or labels changed"
        write_jsonl(OUT / dst, out)
        report["files"][dst] = len(out)
    report["counts"] = dict(sorted(counts.items(), key=lambda kv: -kv[1]))
    report["counts"] = {k: v for k, v in report["counts"].items() if v}
    v1 = json.loads((SRC / "SANITIZED.json").read_text(encoding="utf-8"))["totals"]
    report["v1_totals"] = v1
    (OUT / "SANITIZED.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("registrable_domains_checked", "registered")}), json.dumps(report["counts"], indent=0)[:3000])
    return report


if __name__ == "__main__":
    main()
