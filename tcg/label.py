"""Teacher labeling (gemini-3.1-pro-preview) and Gemini zero-shot guard calls. Same prompt for both."""
from tcg import batch, config, gemini
from tcg.prompts import GUARD_SYSTEM, OUTPUT_SCHEMA, parse_output, render


def guard_online(record: dict, *, phase: str, model: str = config.TEACHER_MODEL, tier: str = "flex",
                 thinking: str | None = "low", tag: str = "", cache_only: bool = False) -> dict | None:
    """Returns {"parsed": {...} or None, "raw": cache entry}; with cache_only, None when not cached yet."""
    r = gemini.generate(render(record), phase=phase, model=model, system=GUARD_SYSTEM, schema=OUTPUT_SCHEMA,
                        tier=tier, thinking=thinking, tag=tag, cache_only=cache_only)
    return {"parsed": parse_output(r["text"]), "raw": r} if r else None


def guard_batch_row(record: dict, *, phase: str, model: str = config.TEACHER_MODEL, thinking: str | None = "low",
                    tag: str = ""):
    return batch.make_request(render(record), model=model, phase=phase, system=GUARD_SYSTEM, schema=OUTPUT_SCHEMA,
                              thinking=thinking, tag=tag)
