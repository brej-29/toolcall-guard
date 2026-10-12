"""Validate and publish contract/ to gs://<bucket>/contract/.
Versioned files (*_v<N>.*) are immutable: skipped if identical, refused if changed, uploaded with a
no-overwrite precondition otherwise. README.md is append-only: refused unless the published text is a prefix."""
import base64
import hashlib
import json
import sys

import jsonschema

from tcg import config, leakage

C = config.ROOT / "contract"
VERSIONED = ["schema_v0.json", "taxonomy_v0.md", "split_v0.py", "examples_v0.jsonl"]


def validate() -> None:
    schema = json.loads((C / "schema_v0.json").read_text(encoding="utf-8"))
    examples = leakage.load_jsonl([C / "examples_v0.jsonl"])
    for r in examples:
        jsonschema.Draft202012Validator(schema).validate(r)
    rep = leakage.check(examples)
    assert rep["ok"], rep["problems"]


def main() -> int:
    validate()
    bucket = config.storage_client().bucket(config.BUCKET)
    for name in VERSIONED:
        data = (C / name).read_bytes()
        blob = bucket.get_blob(f"contract/{name}")
        if blob is not None:
            if blob.md5_hash != base64.b64encode(hashlib.md5(data).digest()).decode():
                print(f"REFUSED: contract/{name} is published and differs locally. Make a new version.", file=sys.stderr)
                return 1
            print(f"unchanged: contract/{name}")
            continue
        bucket.blob(f"contract/{name}").upload_from_string(data, if_generation_match=0)
        print(f"published: contract/{name}")
    readme = (C / "README.md").read_bytes()
    blob = bucket.get_blob("contract/README.md")
    if blob is not None and not readme.startswith(blob.download_as_bytes()):
        print("REFUSED: README.md is append-only and the published text is not a prefix of the local one.", file=sys.stderr)
        return 1
    bucket.blob("contract/README.md").upload_from_string(readme, content_type="text/markdown")
    print("published: contract/README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
