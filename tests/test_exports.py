"""Plan 03-06 -- verdict export (Markdown + JSON envelope) tests (UI-05).

Validates the IT-ticket-friendly Markdown formatter (4-section layout) and
the JSON envelope shape `{verdict, generated_at, space_version}` that
external tooling can round-trip through `Verdict.model_validate`.
"""

from __future__ import annotations

import json
import tomllib
from datetime import datetime
from pathlib import Path

from wifi_diag_schema.verdict import Verdict

from src.space.ui.exports import build_json_export, build_markdown_export

_PYP = Path(__file__).parent.parent / "pyproject.toml"


# --- Markdown export tests --------------------------------------------------


def test_markdown_template(sample_verdict):
    """All four IT-ticket section headings present (CONTEXT Discretion)."""
    md = build_markdown_export(sample_verdict)
    assert "## Diagnosis" in md
    assert "## Confidence" in md
    assert "## Recommended action" in md
    assert "## Evidence" in md


def test_markdown_includes_display_name_and_slug(sample_verdict):
    """Display name (large) + slug subtitle (small) per D-VERDICT-04 ethos."""
    md = build_markdown_export(sample_verdict)
    assert "802.1X authentication failure" in md
    assert "auth_8021x_eap_fail" in md


def test_markdown_includes_band_label(sample_verdict):
    """Confidence band label HIGH (sample_verdict.confidence=0.85 >= 0.80)."""
    md = build_markdown_export(sample_verdict)
    assert "HIGH" in md  # 0.85 >= 0.80 per D-VERDICT-01


def test_markdown_includes_top3_alternatives(sample_verdict):
    """Top-3 alternatives' display names appear in the export."""
    md = build_markdown_export(sample_verdict)
    assert "Access-point roam re-key failure" in md
    assert "RADIUS server timeout" in md


def test_markdown_evidence_bullets(sample_verdict):
    """Each EvidenceItem rendered as `- **{telemetry_path}**: {claim}`."""
    md = build_markdown_export(sample_verdict)
    for e in sample_verdict.evidence:
        assert f"**{e.telemetry_path}**" in md
        assert e.claim in md


# --- JSON envelope tests ----------------------------------------------------


def test_json_envelope_keys(sample_verdict):
    """Envelope has exactly 3 top-level keys: verdict / generated_at / space_version."""
    envelope = json.loads(build_json_export(sample_verdict))
    assert set(envelope.keys()) == {"verdict", "generated_at", "space_version"}


def test_json_roundtrip(sample_verdict):
    """Verdict round-trips: model_validate(envelope['verdict']) == original."""
    envelope = json.loads(build_json_export(sample_verdict))
    roundtripped = Verdict.model_validate(envelope["verdict"])
    assert roundtripped == sample_verdict


def test_json_generated_at_iso8601(sample_verdict):
    """generated_at parses as ISO 8601 (Z-suffix or +00:00 form)."""
    envelope = json.loads(build_json_export(sample_verdict))
    ts = envelope["generated_at"].replace("Z", "+00:00")
    datetime.fromisoformat(ts)  # raises if invalid


def test_json_space_version_matches_pyproject(sample_verdict):
    """envelope['space_version'] reflects the Space repo's pyproject.toml version."""
    envelope = json.loads(build_json_export(sample_verdict))
    pyp = tomllib.loads(_PYP.read_text(encoding="utf-8"))
    assert envelope["space_version"] == pyp["project"]["version"]
