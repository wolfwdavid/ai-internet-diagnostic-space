"""Phase 5 plan 05-03: unit tests for the 11-state banner renderer (UI-07).

Covers:
- All 11 logical states produce HTML with the correct `conn-{state}` CSS class.
- Idle state (None / {} input) emits the install CTA copy.
- `aria-live="polite"` and `role="status"` always present (D-STATUS-27).
- Streaming state includes the privacy chip (D-STATUS-22) and frame counter.
- handshake_ok / connected / streaming / computing / complete include the
  version strip (D-STATUS-19).
- local_fallback adds the `conn-persistent` class (D-STATUS-25).
- Owner identity (owner_key / session_key raw) is never surfaced (D-STATUS-13).
- schema_mismatch surfaces the error detail.
"""
from __future__ import annotations

from pathlib import Path
import pytest

_IMPL = Path(__file__).resolve().parents[1].parent / "src" / "space" / "ui" / "banner.py"
if not _IMPL.exists():
    pytestmark = pytest.mark.xfail(
        reason="Phase 5 plan 05-03 Task 1: banner.py not yet implemented (RED).",
        strict=False,
    )

from src.space.ui.banner import render_banner  # noqa: E402


ALL_STATES = [
    "idle",
    "waking",
    "connecting",
    "handshake_ok",
    "connected",
    "streaming",
    "computing",
    "stalled",
    "reconnecting",
    "schema_mismatch",
    "local_fallback",
]


@pytest.mark.parametrize("state", ALL_STATES)
def test_each_state_renders_correct_css_class(state):
    html = render_banner(
        {
            "state": state,
            "schema_version": "1.1.0",
            "frame_index": 1,
            "total": 10,
            "stalled_for_s": 6,
            "retry_n": 1,
            "error": "demo",
            "reason": "demo",
        }
    )
    assert f"conn-{state}" in html


def test_idle_state_includes_install_cta():
    html = render_banner(None)
    assert "pip install ai-internet-diagnostic-agent" in html


def test_idle_state_from_empty_dict():
    html = render_banner({})
    assert "conn-idle" in html
    assert "pip install ai-internet-diagnostic-agent" in html


def test_aria_live_polite_always_present():
    for state in ALL_STATES:
        html = render_banner({"state": state})
        assert 'aria-live="polite"' in html, f"missing aria-live in {state}"


def test_role_status_always_present():
    for state in ALL_STATES:
        html = render_banner({"state": state})
        assert 'role="status"' in html, f"missing role=status in {state}"


def test_streaming_state_includes_privacy_chip():
    html = render_banner(
        {"state": "streaming", "frame_index": 47, "total": 120}
    )
    assert "redacted" in html
    assert "BSSIDs hashed" in html
    assert "no credentials" in html


def test_handshake_ok_includes_versions():
    html = render_banner({"state": "handshake_ok", "schema_version": "1.1.0"})
    assert "Space v1.0.0" in html
    assert "Schema v1.1.0" in html


def test_connected_includes_full_version_strip():
    """D-STATUS-19: Connected — Space vX • Agent vY • Schema vZ"""
    html = render_banner(
        {"state": "connected", "schema_version": "1.1.0", "agent_version": "1.0.0"}
    )
    assert "Space v1.0.0" in html
    assert "Agent v1.0.0" in html
    assert "Schema v1.1.0" in html


def test_local_fallback_persistent_class():
    html = render_banner({"state": "local_fallback"})
    assert "conn-persistent" in html
    assert "conn-local_fallback" in html


def test_owner_identity_not_surfaced_in_text():
    """D-STATUS-13: owner-mode is anonymous live; no identity leak."""
    html = render_banner(
        {
            "state": "handshake_ok",
            "schema_version": "1.1.0",
            "session_key": "owner:secret12",
            "owner_key": "supersecret",
        }
    )
    assert "secret12" not in html
    assert "supersecret" not in html
    assert "session_key" not in html
    assert "owner_key" not in html


def test_streaming_frame_counter_rendered():
    html = render_banner(
        {"state": "streaming", "frame_index": 47, "total": 120}
    )
    assert "47/120 frames" in html


def test_schema_mismatch_includes_error_detail():
    html = render_banner(
        {
            "state": "schema_mismatch",
            "error": "Schema major-version mismatch: local=1.1.0, remote=2.0.0",
        }
    )
    assert "Schema major-version mismatch" in html


def test_stalled_includes_seconds():
    html = render_banner({"state": "stalled", "stalled_for_s": 7})
    assert "7" in html


def test_reconnecting_includes_retry_count():
    html = render_banner({"state": "reconnecting", "retry_n": 2})
    assert "2" in html


def test_all_states_render():
    """Smoke parity: every state in ALL_STATES yields a non-empty HTML string."""
    for state in ALL_STATES:
        html = render_banner({"state": state})
        assert isinstance(html, str)
        assert len(html) > 50
        assert "<div" in html


def test_idle_does_not_emit_versions():
    """Idle has no agent connected -> no version strip noise."""
    html = render_banner(None)
    assert "Space v" not in html
    assert "Schema v" not in html


def test_unknown_state_falls_back_safely():
    """Defensive: unknown state should not crash; emits the state class verbatim."""
    html = render_banner({"state": "totally_unknown"})
    assert 'aria-live="polite"' in html
    assert "conn-totally_unknown" in html
