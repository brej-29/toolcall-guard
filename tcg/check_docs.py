"""Docs checks for README.md and the two Hugging Face cards, run before publishing. Exits 1 on any failure.
  numbers       tcg.audit_numbers passes; regenerating the card blocks (tcg.evaluate card) and the figures
                (tcg.figures) changes nothing, images included; every two-decimal number in an image's alt text is a number drawn in
                that image (assets/figures_data.json); the Replication block equals hf/replication.md
  links         relative links and images exist; with --online, http(s) links answer below 400
  placeholders  no [NAME], <<<...>>>, FILL IN, TODO, TBD, [PASTE ...]
  em dashes     none in the docs, the figure sources, the SVGs or the demo records
  sizes         no added or changed file over 1 MB (against --base, default HEAD)
  secrets       no keys, tokens, private keys, emails other than example.com and noreply, phone numbers, local paths
                or user names, in the docs, assets (SVG text included) and the demo records
  private       no link to the private archive or the verbatim dataset
  yaml          the card metadata parses
Usage: uv run --group docs python -m tcg.check_docs [--online] [--base <git ref>]"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from tcg import config

R = config.ROOT
DOCS = [R / "README.md", R / "hf" / "model_card.md", R / "hf" / "dataset_card.md"]
SCAN = DOCS + sorted((R / "assets").glob("*.svg")) + [R / "assets" / "figures_data.json", R / "hf" / "demo_examples.jsonl",
                                                       R / "results" / "demo_examples_8bit.jsonl", R / "tcg" / "figures.py",
                                                       R / "tcg" / "check_docs.py"]
FIG_KEYS = {"chart_headline": ["headline"], "chart_precision": ["precision"], "chart_matched_fpr": ["matched"],
            "chart_adaptive": ["adaptive"], "diagram_precision": ["diagrams"], "diagram_pipeline": ["diagrams"],
            "diagram_split": [], "diagram_guard_replay": [], "guard_demo": []}
fails = []


def fail(check: str, msg: str) -> None:
    fails.append(f"{check}: {msg}")


def run(*args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", *args], cwd=R, capture_output=True, text=True, encoding="utf-8")


def numbers() -> None:
    p = run("tcg.audit_numbers")
    if p.returncode:
        fail("numbers", "tcg.audit_numbers failed:\n" + p.stdout[-2000:])
    before = {f: f.read_bytes() for f in DOCS[:2] + sorted((R / "assets").iterdir())}
    for step in (("tcg.evaluate", "card"), ("tcg.figures",)):
        p = run(*step)
        if p.returncode:
            fail("numbers", f"{' '.join(step)} failed: {p.stderr[-1000:]}")
    for f, b in before.items():
        if f.read_bytes() != b:
            fail("numbers", f"{f.relative_to(R)} changed when regenerated from the result files")
    data = json.loads((R / "assets" / "figures_data.json").read_text(encoding="utf-8"))
    for doc in DOCS:
        for alt, path in re.findall(r"!\[([^\]]*)\]\(assets/([\w-]+)\.\w+\)", doc.read_text(encoding="utf-8")):
            drawn = {f"{x:.2f}" for k in FIG_KEYS[path] for x in flat(data.get(k))}
            for num in re.findall(r"\b\d\.\d\d\b", alt):
                if num not in drawn:
                    fail("numbers", f"{doc.name}: alt text of {path} says {num}, not a number drawn in it")
    rep = (R / "hf" / "replication.md").read_text(encoding="utf-8").strip()
    for doc in DOCS[:2]:
        t = doc.read_text(encoding="utf-8")
        block = t.split("<!-- replication:start -->", 1)[1].split("<!-- replication:end -->", 1)[0].strip()
        if block != rep:
            fail("numbers", f"{doc.name}: the Replication block differs from hf/replication.md")


def flat(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from flat(v)
    elif isinstance(x, list):
        for v in x:
            yield from flat(v)
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        yield x


def links(online: bool) -> None:
    import urllib.request
    token = None
    if online:
        from huggingface_hub import get_token
        token = get_token()
    for doc in DOCS:
        t = re.sub(r"```.*?```", "", doc.read_text(encoding="utf-8"), flags=re.S)
        for target in re.findall(r"\]\(([^)\s]+)\)", t) + re.findall(r'src="([^"]+)"', t):
            if target.startswith("#"):
                continue
            if not target.startswith("http"):
                # cards: assets/ is uploaded next to the card; other relative paths resolve against the GitHub repo
                if not (R / target.split("#")[0]).exists():
                    fail("links", f"{doc.name}: {target} does not exist")
                continue
            if online:
                req = urllib.request.Request(target, method="GET", headers={"User-Agent": "check-docs"})
                if token and target.startswith("https://huggingface.co/"):
                    req.add_header("Authorization", f"Bearer {token}")
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        code = resp.status
                except Exception as e:  # HTTPError carries the code; anything else is a failure too
                    code = getattr(e, "code", str(e))
                if not isinstance(code, int) or code >= 400:
                    fail("links", f"{doc.name}: {target} -> {code}")


PLACEHOLDER = re.compile(r"\[NAME\]|<<<|>>>|FILL IN|\bTODO\b|\bTBD\b|\bFIXME\b|\[PASTE|lorem ipsum", re.I)
SECRET = {
    "API key or token": re.compile(r"AIza[0-9A-Za-z_-]{20,}|\bsk-[A-Za-z0-9]{20,}|\bghp_[A-Za-z0-9]{20,}|\bhf_[A-Za-z0-9]{20,}|xox[bp]-[A-Za-z0-9-]{10,}|ya29\.[A-Za-z0-9_-]{20,}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "email": re.compile(r"[\w.+-]+@(?!example\.com\b|anthropic\.com\b|users\.noreply\.github\.com\b)[\w-]+(\.[\w-]+)+"),
    "phone number": re.compile(r"(?<![\w.])\+?\d{1,3}[ -]\(?\d{3}\)?[ -]\d{3}[ -]\d{4}\b"),
    # the local account name comes from the home folder, so no name is written into this file
    "local path or user name": re.compile(r"[A-Za-z]:\\Users\\|/Users/|/home/\w|AppData|\b" + re.escape(Path.home().name) + r"\b", re.I),
}
PRIVATE = re.compile(r"toolcall-guard-archive|toolcall-guard-data-verbatim")


def text_checks() -> None:
    for f in SCAN:
        t = f.read_text(encoding="utf-8")
        name = f.relative_to(R).as_posix()
        if f.name != "check_docs.py":
            for m in PLACEHOLDER.finditer(t):
                fail("placeholders", f"{name}: {m.group(0)!r}")
            for kind, rx in SECRET.items():
                for m in rx.finditer(t):
                    fail("secrets", f"{name}: {kind} {m.group(0)!r}")
            for m in PRIVATE.finditer(t):
                fail("private", f"{name}: {m.group(0)!r}")
        if chr(0x2014) in t:
            fail("em dashes", f"{name}: {t.count(chr(0x2014))}")


def sizes(base: str) -> None:
    out = subprocess.run(["git", "diff", "--name-only", base], cwd=R, capture_output=True, text=True).stdout.split()
    out += subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=R, capture_output=True, text=True).stdout.split()
    for rel in sorted(set(out)):
        p = R / rel
        if p.is_file() and p.stat().st_size > 1_000_000:
            fail("sizes", f"{rel}: {p.stat().st_size / 1e6:.1f} MB")


def yaml_meta() -> None:
    from huggingface_hub.repocard import metadata_load
    for f in DOCS[1:]:
        try:
            meta = metadata_load(f)
            if not meta or "license" not in meta:
                fail("yaml", f"{f.name}: no metadata or no license")
        except Exception as e:
            fail("yaml", f"{f.name}: {e}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true", help="also fetch every http(s) link")
    ap.add_argument("--base", default="HEAD", help="git ref the size check compares against")
    a = ap.parse_args()
    numbers()
    links(a.online)
    text_checks()
    sizes(a.base)
    yaml_meta()
    print("docs checks:", "PASS" if not fails else f"{len(fails)} failed", *fails, sep="\n  ")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
