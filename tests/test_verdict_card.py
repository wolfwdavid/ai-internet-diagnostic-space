"""Phase 3 plan 03-02 Task 2: verdict card + 'what to do' card builders.

Tests cover D-VERDICT-01 (confidence-band thresholds + colored badge),
D-VERDICT-02 (top-3 alternatives always-visible + 'Show all 10' expander),
D-VERDICT-03 (what-to-do card renders suggested_fix), D-VERDICT-04 (display
name + slug subtitle), and D-VERDICT-07 (HIGH/MED/LOW text labels).
"""
from __future__ import annotations

from src.space.ui.verdict_card import _confidence_band, build_verdict_card
from src.space.ui.what_to_do_card import build_what_to_do_card


# --- D-VERDICT-01: confidence-band badge color thresholds -------------------


def test_high_confidence_green_badge(sample_verdict):
    v = sample_verdict.model_copy(update={"confidence": 0.85})
    html = build_verdict_card(v)
    assert "HIGH" in html
    # green color: word "green" OR a green hex.
    assert "green" in html.lower() or "#22c55e" in html


def test_med_confidence_amber_badge(sample_verdict):
    v = sample_verdict.model_copy(update={"confidence": 0.70})
    html = build_verdict_card(v)
    assert "MED" in html
    assert "amber" in html.lower() or "#f59e0b" in html or "orange" in html.lower()


def test_low_confidence_red_badge(sample_verdict):
    v = sample_verdict.model_copy(update={"confidence": 0.45})
    html = build_verdict_card(v)
    assert "LOW" in html
    assert "red" in html.lower() or "#ef4444" in html


# --- D-VERDICT-04: display name + slug subtitle -----------------------------


def test_display_name_and_slug_both_shown(sample_verdict):
    html = build_verdict_card(sample_verdict)
    assert "802.1X authentication failure" in html  # display name
    assert "auth_8021x_eap_fail" in html            # slug


# --- D-VERDICT-02: top-3 alternatives always-visible + 'Show all 10' --------


def test_top_3_alternatives_visible(sample_verdict):
    html = build_verdict_card(sample_verdict)
    # Rank 2 + 3 always visible (display names).
    assert "Access-point roam re-key failure" in html
    assert "RADIUS server timeout" in html
    # The remaining 7 are gated behind the literal 'Show all 10' expander.
    assert "Show all 10" in html


# --- D-VERDICT-01: confidence-band threshold logic --------------------------


def test_confidence_band_thresholds():
    assert _confidence_band(0.80) == "HIGH"
    assert _confidence_band(0.79) == "MED"
    assert _confidence_band(0.60) == "MED"
    assert _confidence_band(0.59) == "LOW"


# --- D-VERDICT-03: what-to-do card renders suggested_fix --------------------


def test_what_to_do_card_renders_suggested_fix(sample_verdict):
    html = build_what_to_do_card(sample_verdict)
    assert sample_verdict.suggested_fix in html
