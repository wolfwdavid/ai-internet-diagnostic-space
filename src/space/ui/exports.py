"""Verdict export -- Markdown (IT-ticket-friendly) + JSON (envelope) -- UI-05.

Two pure-function exporters consumed by ``synthetic_tab.py``'s
``gr.DownloadButton`` wiring (plan 03-06):

  - ``build_markdown_export(verdict)`` -- 4-section IT-ticket-friendly
    Markdown (Diagnosis / Confidence / Recommended action / Evidence).
    Per CONTEXT.md "Claude's Discretion" -- pasted into a help-desk
    ticket or a chat message it should read like a complete diagnosis.

  - ``build_json_export(verdict)`` -- 3-key envelope
    ``{verdict, generated_at, space_version}``. The ``verdict`` key holds
    ``Verdict.model_dump()`` so external tooling can call
    ``Verdict.model_validate(envelope["verdict"])`` and round-trip back to
    the canonical Pydantic shape. ``generated_at`` is ISO 8601 UTC
    (Z-suffix). ``space_version`` is read from the Space repo's
    ``pyproject.toml`` at runtime so the envelope's provenance is honest.

Both functions are pure (no I/O on call after the cached pyproject read);
``gr.DownloadButton`` consumes the returned string via its ``value``
attribute or the ``click(fn=...)`` event handler.
"""
from __future__ import annotations

import json
import tomllib
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from wifi_diag_schema.enums import DISPLAY_NAMES
from wifi_diag_schema.verdict import Verdict

from .verdict_card import _confidence_band

# Resolve the Space repo's pyproject.toml relative to this module:
#   src/space/ui/exports.py -> repo root
_PYPROJECT = Path(__file__).parent.parent.parent.parent / "pyproject.toml"


@lru_cache(maxsize=1)
def _read_space_version() -> str:
    """Cached read of ``[project] version`` from the Space's pyproject.toml."""
    return tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]


# IT-ticket-friendly Markdown template (Claude's discretion in CONTEXT).
# Sections: Diagnosis / Confidence / Recommended action / Evidence -- the
# four headings a help-desk technician needs to skim a ticket fast.
_MARKDOWN_TEMPLATE = """# Wi-Fi Diagnosis: {display_name}

## Diagnosis

**{display_name}** (`{slug}`)

{headline}

## Confidence

**{pct}%** -- {band}

Other possibilities:
{alternatives}

## Recommended action

{suggested_fix}

## Evidence

{evidence_bullets}
"""


def build_markdown_export(verdict: Verdict) -> str:
    """Render the verdict as IT-ticket-friendly Markdown (UI-05).

    4-section layout:
      1. ``## Diagnosis`` -- display name (large) + slug subtitle + headline
      2. ``## Confidence`` -- percentage + band (HIGH/MED/LOW) + top-3 alts
      3. ``## Recommended action`` -- suggested_fix
      4. ``## Evidence`` -- bulleted list of ``EvidenceItem`` claims
    """
    display = DISPLAY_NAMES[verdict.top_class]
    band = _confidence_band(verdict.confidence)
    pct = int(round(verdict.confidence * 100))

    # Top-3 alternatives (rank 2 + rank 3 of the top_k=10 list).
    top3 = verdict.top_k[1:3]
    alternatives = "\n".join(
        f"- {int(round(p * 100))}% -- {DISPLAY_NAMES[c]} (`{c}`)"
        for c, p in top3
    )

    # Evidence bullets -- preserve EvidenceItem.telemetry_path + claim shape so
    # the IT ticket reader can grep for a field-path quickly.
    if verdict.evidence:
        evidence_bullets = "\n".join(
            f"- **{e.telemetry_path}**: {e.claim}"
            for e in verdict.evidence
        )
    else:
        evidence_bullets = "_(no evidence -- citation guardrail stripped all claims)_"

    return _MARKDOWN_TEMPLATE.format(
        display_name=display,
        slug=verdict.top_class,
        headline=verdict.headline,
        pct=pct,
        band=band,
        alternatives=alternatives,
        suggested_fix=verdict.suggested_fix,
        evidence_bullets=evidence_bullets,
    )


def build_json_export(verdict: Verdict) -> str:
    """Render the verdict as a JSON envelope (UI-05).

    Envelope shape::

        {
          "verdict": <Verdict.model_dump()>,
          "generated_at": "<ISO 8601 UTC, e.g. 2026-05-08T14:23:00Z>",
          "space_version": "<pyproject.toml [project] version>"
        }

    The ``verdict`` field round-trips through
    ``Verdict.model_validate(envelope["verdict"])`` so external tooling
    (e.g. Phase 4 agent) can ingest it without bespoke parsing.
    """
    envelope = {
        "verdict": verdict.model_dump(),
        # Z-suffix form (UTC, ISO 8601). Strict format for stable diffs.
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "space_version": _read_space_version(),
    }
    # default=str handles Decimal / datetime / etc. that may sneak into Pydantic
    # model_dump output across schema bumps; safer than crashing on encode.
    return json.dumps(envelope, indent=2, default=str)
