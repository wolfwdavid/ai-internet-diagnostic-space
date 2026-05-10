"""SCEN-02 + D-NARRATOR-12 + Pitfall E: cached narration validation.

Five gates per scenario:
1. ``test_cached_narration_loads`` -- file exists at ``cache/narrations/{slug}.json``
   and parses as a Verdict (Pydantic schema-valid).
2. ``test_cached_narration_citations_valid`` -- every EvidenceItem.telemetry_path
   resolves against regenerated telemetry (D-NARRATOR-12 + Pitfall E mitigation).
3. ``test_cached_narration_top_class_matches_classifier`` -- cached top_class
   equals the live classifier output for the same scenario seed (catches
   "stale verdict" drift; Pitfall E values-mismatch defense).
4. ``test_cached_narration_evidence_uses_evidence_rules`` -- every cited path
   is in EVIDENCE_RULES[verdict.top_class] (D-NARRATOR-04 contract).
5. ``test_cached_narration_headline_within_max_length`` -- headline <=140 chars
   (D-VERDICT-06 schema constraint; defensive belt-and-suspenders).

CI hard-fails on any failure here per D-NARRATOR-06 -- ci.yml runs this file
as an explicit gate step.
"""

from __future__ import annotations

import pytest
from wifi_diag_narrator.citation_validator import is_valid_citation
from wifi_diag_narrator.evidence_rules import EVIDENCE_RULES
from wifi_diag_schema.verdict import Verdict

from src.space.narration_cache import load_cached_narration
from src.space.scenarios.catalog import SCENARIOS
from src.space.scenarios.runner import _generate_frames, run_scenario


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_cached_narration_loads(scenario):
    v = load_cached_narration(scenario.slug)
    assert isinstance(v, Verdict)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_cached_narration_citations_valid(scenario):
    """Every cited path resolves to non-null in the regenerated telemetry."""
    v = load_cached_narration(scenario.slug)
    frames = _generate_frames(scenario)
    for e in v.evidence:
        assert is_valid_citation(e, frames), (
            f"{scenario.slug}: {e.telemetry_path} fails validation against "
            f"regenerated telemetry. Run `make cache-narrations` to refresh."
        )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_cached_narration_top_class_matches_classifier(scenario):
    """Pitfall E mitigation: detect cached verdict drift vs. live classifier."""
    cached = load_cached_narration(scenario.slug)
    live, _scores, _frames = run_scenario(scenario.slug)
    assert cached.top_class == live.top_class, (
        f"Stale cache: {scenario.slug} cached={cached.top_class} "
        f"live={live.top_class}. Run `make cache-narrations` to refresh."
    )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_cached_narration_evidence_uses_evidence_rules(scenario):
    """D-NARRATOR-04: every cited path must be in the per-class rule set."""
    v = load_cached_narration(scenario.slug)
    allowed = set(EVIDENCE_RULES[v.top_class])
    for e in v.evidence:
        assert e.telemetry_path in allowed, (
            f"{scenario.slug}: evidence path {e.telemetry_path!r} not in "
            f"EVIDENCE_RULES[{v.top_class!r}] = {sorted(allowed)}"
        )


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_cached_narration_headline_within_max_length(scenario):
    """D-VERDICT-06: headline max_length=140 (Pydantic-enforced, but defense in depth)."""
    v = load_cached_narration(scenario.slug)
    assert len(v.headline) <= 140, (
        f"{scenario.slug}: headline length {len(v.headline)} > 140"
    )
