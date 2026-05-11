"""Phase 5 plan 05-03: integration tests for the Live-tab banner + polling.

Asserts on app.py source + live_tab.py source rather than spinning up a
Gradio Blocks instance, because (a) instantiating Blocks at test-time is
expensive and (b) Gradio 6.x's Blocks DAG isn't easy to introspect for
"is banner above tabs" without source inspection.

Covers (per plan 05-03 acceptance criteria):
- Banner is page-level: ``banner = gr.HTML(...)`` appears BEFORE
  ``with gr.Tabs():`` in app.py source (D-STATUS-02).
- 500ms timer cadence: ``gr.Timer(value=0.5)`` present (D-STATUS-29).
- CSS loaded via gr.Blocks(css=...) (Pitfall 28 banner-CSS-not-applied guard).
- Live tab's local_view defaults to visible=False (D-STATUS-06).
- live_tab.py imports the Phase 3 builders (UI-07 reuse).
- Synthetic tab is unbroken (build_synthetic_tab() still called).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
APP_PATH = _REPO / "app.py"
LIVE_TAB_PATH = _REPO / "src" / "space" / "ui" / "live_tab.py"


def test_banner_above_tabs_in_source():
    """D-STATUS-02: banner is page-level (above gr.Tabs())."""
    src = APP_PATH.read_text(encoding="utf-8")
    banner_idx = src.find("banner = gr.HTML(")
    tabs_idx = src.find("with gr.Tabs():")
    assert banner_idx > 0, "banner = gr.HTML(...) not found in app.py"
    assert tabs_idx > 0, "with gr.Tabs(): not found in app.py"
    assert banner_idx < tabs_idx, (
        f"banner ({banner_idx}) must precede tabs ({tabs_idx}) per D-STATUS-02"
    )


def test_timer_polls_at_500ms():
    """D-STATUS-29: 500ms poll cadence."""
    src = APP_PATH.read_text(encoding="utf-8")
    assert "gr.Timer(value=0.5)" in src, (
        "expected gr.Timer(value=0.5) for D-STATUS-29 cadence"
    )


def test_timer_tick_wired_to_poll_banner():
    """Timer must call _poll_banner with the right output bindings."""
    src = APP_PATH.read_text(encoding="utf-8")
    assert "_poll_timer.tick(" in src
    assert "fn=_poll_banner" in src


def test_css_loaded_at_launch():
    """Banner CSS must be passed to demo.launch(css=...) per Gradio 6.0 API."""
    src = APP_PATH.read_text(encoding="utf-8")
    assert "css=_CSS" in src, (
        "banner CSS must be loaded via demo.launch(css=...) (Gradio 6.0 idiom)"
    )
    assert "banner.css" in src, "expected banner.css read at module load"


def test_local_view_hidden_by_default():
    """D-STATUS-06: local_view defaults to visible=False (banner state-driven swap)."""
    src = LIVE_TAB_PATH.read_text(encoding="utf-8")
    m = re.search(r"local_view\s*=\s*gr\.Column\(visible=(\w+)\)", src)
    assert m is not None, "could not find local_view = gr.Column(visible=...) in live_tab.py"
    assert m.group(1) == "False", (
        f"local_view must default to visible=False (D-STATUS-06), got {m.group(1)}"
    )


def test_verdict_view_visible_by_default():
    src = LIVE_TAB_PATH.read_text(encoding="utf-8")
    m = re.search(r"verdict_view\s*=\s*gr\.Column\(visible=(\w+)\)", src)
    assert m is not None, "could not find verdict_view = gr.Column(visible=...) in live_tab.py"
    assert m.group(1) == "True", (
        f"verdict_view must default to visible=True, got {m.group(1)}"
    )


def test_live_tab_imports_phase3_builders():
    """UI-07 ROADMAP criterion: Live tab reuses Phase 3 builders (no duplication)."""
    src = LIVE_TAB_PATH.read_text(encoding="utf-8")
    assert "build_verdict_card" in src, "Live tab must reuse Phase 3 verdict-card builder"
    assert "build_timeline" in src, "Live tab must reuse Phase 3 timeline builder"
    assert "build_what_to_do_card" in src, "Live tab must reuse Phase 3 what-to-do builder"


def test_app_imports_banner_and_live_tab():
    src = APP_PATH.read_text(encoding="utf-8")
    assert "from src.space.ui.banner import render_banner" in src
    assert "from src.space.ui.live_tab import build_live_tab" in src
    assert "from src.space.live import status" in src


def test_phase3_synthetic_tab_unbroken():
    """Synthetic tab content must NOT have been modified."""
    src = APP_PATH.read_text(encoding="utf-8")
    assert "build_synthetic_tab()" in src, (
        "Synthetic tab build call must still exist (Phase 3 regression guard)"
    )


def test_pitfall_7_assertions_preserved():
    """Plan 05-03 must not regress the Pitfall 7 + F runtime version asserts."""
    src = APP_PATH.read_text(encoding="utf-8")
    assert 'gr.__version__.startswith("6.13")' in src
    assert "sys.version_info[:2] == (3, 13)" in src


def test_owner_session_key_derived_from_env_var():
    """Session key matches plan 05-01's f'owner:{owner_key[:8]}' shape."""
    src = APP_PATH.read_text(encoding="utf-8")
    assert "OWNER_KEY" in src, "expected OWNER_KEY env-var lookup"
    assert 'f"owner:{_OWNER_KEY_RAW[:8]}"' in src or "f'owner:{_OWNER_KEY_RAW[:8]}'" in src, (
        "session key shape must match plan 05-01: f'owner:{owner_key[:8]}'"
    )


def test_poll_banner_swaps_views_on_local_fallback():
    """When state is local_fallback, verdict_view hides + local_view shows."""
    src = APP_PATH.read_text(encoding="utf-8")
    assert 'show_verdict = s != "local_fallback"' in src
    assert 'show_local = s == "local_fallback"' in src


def test_app_module_imports_cleanly():
    """The whole app.py module must import without side-effecting the Gradio launch."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("app", APP_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "demo"), "app.py must export the Gradio `demo` Blocks"
    assert hasattr(mod, "render_banner"), "app.py must expose render_banner (plan 05-03)"
    assert hasattr(mod, "status"), "app.py must import status module (plan 05-03 poller)"
