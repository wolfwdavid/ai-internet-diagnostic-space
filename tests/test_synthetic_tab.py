"""Phase 3 plan 03-03 -- Synthetic-tab UI surface tests.

Tests the 4x2 scenario card grid (D-SYNTH-01), the Random scenario button
(UI-03), and the 'Analyzing telemetry...' demo theater (D-SYNTH-02).
"""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from src.space.scenarios.catalog import SCENARIOS
from src.space.ui.synthetic_tab import (
    build_synthetic_tab,
    card_click_handler,
    random_scenario_handler,
)

_REPO = Path(__file__).parent.parent
_SYN_TAB = _REPO / "src" / "space" / "ui" / "synthetic_tab.py"


def test_random_button() -> None:
    """random_scenario_handler returns (verdict_html, what_to_do_html, fig)."""
    verdict_html, what_to_do_html, fig = random_scenario_handler()
    assert isinstance(verdict_html, str) and len(verdict_html) > 0
    assert isinstance(what_to_do_html, str)
    assert isinstance(fig, go.Figure)


def test_card_handler_dispatches_by_slug() -> None:
    """Every scenario slug runs successfully through card_click_handler."""
    for s in SCENARIOS:
        verdict_html, what_to_do_html, fig = card_click_handler(s.slug)
        assert isinstance(verdict_html, str), f"{s.slug}: verdict_html not str"
        assert isinstance(what_to_do_html, str), f"{s.slug}: what_to_do_html not str"
        assert isinstance(fig, go.Figure), f"{s.slug}: fig not go.Figure"


def test_grid_has_8_cards() -> None:
    """All 8 scenario display_names appear in the synthetic_tab.py source
    (D-SYNTH-01: 4x2 grid renders one card per scenario)."""
    blob = _SYN_TAB.read_text(encoding="utf-8")
    for s in SCENARIOS:
        assert s.display_name in blob, f"missing scenario card: {s.display_name}"


def test_random_button_label_present() -> None:
    """UI-03 button label + D-SYNTH-02 'Analyzing telemetry' string in source."""
    blob = _SYN_TAB.read_text(encoding="utf-8")
    assert "Random scenario" in blob, "UI-03: 'Random scenario' button label missing"
    assert "Analyzing telemetry" in blob, "D-SYNTH-02: 'Analyzing telemetry' string missing"


def test_synthetic_tab_has_analyzing_pause() -> None:
    """D-SYNTH-02: a deliberate 1.0-2.0s pause enforces the demo-theater feel."""
    blob = _SYN_TAB.read_text(encoding="utf-8")
    # Look for time.sleep(<float between 1.0 and 2.0>) in the source.
    import re
    matches = re.findall(r"time\.sleep\(\s*(\d+(?:\.\d+)?)\s*\)", blob)
    assert matches, "D-SYNTH-02: no time.sleep() call found in synthetic_tab.py"
    # At least one pause must be in the [1.0, 2.0] band.
    floats = [float(m) for m in matches]
    in_band = [f for f in floats if 1.0 <= f <= 2.0]
    assert in_band, (
        f"D-SYNTH-02: expected at least one time.sleep(1.0..2.0); found sleeps: {floats}"
    )


def test_build_synthetic_tab_does_not_raise() -> None:
    """Smoke: build_synthetic_tab() executes inside a Blocks context without error."""
    import gradio as gr
    with gr.Blocks() as _demo:
        components = build_synthetic_tab()
    assert isinstance(components, dict)
    # Required components for downstream wiring (03-05 / 03-06).
    assert "random_btn" in components
    assert "card_buttons" in components
    assert "verdict_pane" in components
    assert "timeline_pane" in components
    # 8 card buttons (D-SYNTH-01 4x2 grid).
    assert len(components["card_buttons"]) == 8


def test_card_click_handler_is_deterministic() -> None:
    """Same slug -> same verdict_html (the underlying run_scenario is deterministic)."""
    h1 = card_click_handler("school_radius_overload")
    h2 = card_click_handler("school_radius_overload")
    # verdict_html string equality is the strongest deterministic check the
    # UI surface allows (Verdict object comparison hidden behind HTML).
    assert h1[0] == h2[0]
