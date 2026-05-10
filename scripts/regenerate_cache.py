"""Regenerate cached narrations (D-NARRATOR-05, D-NARRATOR-09).

Two modes:
- **Default (Anthropic):** invokes ``wifi_diag_narrator.anthropic_narrator.narrate``
  for each scenario. Requires ``ANTHROPIC_API_KEY`` env var. This is the
  production path -- ``regenerate-narrations.yml`` GHA workflow_dispatch
  invokes this with the repo-secret key (D-NARRATOR-09 -- key never lives
  on a developer machine).
- **--templated:** invokes ``wifi_diag_narrator.templated.narrate_templated``
  -- no network, no API key. Used for the initial cache bootstrap and as
  an offline fallback (LLM-05 / D-NARRATOR-03).

Each cache file is annotated with its source (``"anthropic"`` or
``"templated"``) via the verdict's structure -- the templated narrator's
output is deterministic and structurally indistinguishable from LLM
output, so downstream consumers (tests, UI) treat them the same.

Usage::

    # Bootstrap with templated narrator (no API key required):
    uv run python scripts/regenerate_cache.py --scenarios all --templated

    # Anthropic Haiku 4.5 regeneration (requires ANTHROPIC_API_KEY):
    uv run python scripts/regenerate_cache.py --scenarios all

    # Single scenario:
    uv run python scripts/regenerate_cache.py --scenarios school_radius_overload
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add the Space repo root to sys.path so ``from src.space...`` works whether
# this script is invoked directly or via ``uv run python scripts/...``.
sys.path.insert(0, str(Path(__file__).parent.parent))

from wifi_diag_narrator.templated import narrate_templated  # noqa: E402

from src.space.inference import predict  # noqa: E402
from src.space.scenarios.catalog import SCENARIOS, SCENARIOS_BY_SLUG  # noqa: E402
from src.space.scenarios.runner import _generate_frames  # noqa: E402

_CACHE_DIR = Path(__file__).parent.parent / "cache" / "narrations"


def regen_one(slug: str, *, templated: bool) -> str:
    """Regenerate one cache file. Returns the source label ('templated'/'anthropic').

    Always re-derives telemetry from the scenario seed and re-runs the
    classifier so the cached top_class always matches the live classifier
    (Pitfall E mitigation -- ensures
    ``test_cached_narration_top_class_matches_classifier`` passes after
    every regen).
    """
    scenario = SCENARIOS_BY_SLUG[slug]
    frames = _generate_frames(scenario)
    classifier_verdict, _scores = predict(frames)
    if templated:
        narrated = narrate_templated(classifier_verdict, frames)
        source = "templated"
    else:
        # Lazy import -- the anthropic SDK is only required on the LLM path
        # (Pitfall C). The Phase 4 agent's local-only mode never imports
        # this script and therefore never pulls anthropic transitively.
        from wifi_diag_narrator.anthropic_narrator import narrate  # noqa: PLC0415

        narrated = narrate(classifier_verdict, frames)
        source = "anthropic"

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _CACHE_DIR / f"{slug}.json"
    out_path.write_text(narrated.model_dump_json(indent=2), encoding="utf-8")
    return source


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--scenarios",
        default="all",
        help="Comma-separated scenario slugs, or 'all' for every scenario.",
    )
    ap.add_argument(
        "--templated",
        action="store_true",
        help=(
            "Use narrate_templated (offline, no API key) instead of "
            "the Anthropic narrator. Used for the initial cache bootstrap "
            "and as a fallback when ANTHROPIC_API_KEY is not available."
        ),
    )
    args = ap.parse_args()

    if args.scenarios == "all":
        slugs = [s.slug for s in SCENARIOS]
    else:
        slugs = [s.strip() for s in args.scenarios.split(",") if s.strip()]

    unknown = [s for s in slugs if s not in SCENARIOS_BY_SLUG]
    if unknown:
        sys.exit(
            f"ERROR: unknown scenario slug(s): {unknown}. "
            f"Valid slugs: {[s.slug for s in SCENARIOS]}"
        )

    if not args.templated and "ANTHROPIC_API_KEY" not in os.environ:
        sys.exit(
            "ERROR: ANTHROPIC_API_KEY not set. Either:\n"
            "  - set the env var (default Anthropic Haiku 4.5 path), or\n"
            "  - pass --templated for the offline bootstrap path."
        )

    sources_used: set[str] = set()
    for slug in slugs:
        print(f"Regenerating narration: {slug}")
        src = regen_one(slug, templated=args.templated)
        sources_used.add(src)

    src_label = "/".join(sorted(sources_used))
    print(f"Done. Wrote {len(slugs)} narration(s) ({src_label}) to {_CACHE_DIR}.")


if __name__ == "__main__":
    main()
