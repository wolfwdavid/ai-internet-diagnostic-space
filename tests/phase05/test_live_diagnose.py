"""Plan 05-01: RED tests for the Space-side ``live_diagnose`` Gradio generator.

These tests are xfail-strict during Wave 0 — Task 0 ships the scaffold; Task 2
removes the xfail markers and the tests turn GREEN.

State-machine contract under test (D-STATUS-24, D-STATUS-05, D-STATUS-17, D-STATUS-26):
- First yield on compatible handshake: ``{"state": "handshake_ok", ...}``
- Major mismatch -> single yield ``{"state": "schema_mismatch", ...}`` then generator stops.
- Minor drift -> ``{"state": "handshake_ok", "schema_drift": "minor", ...}``, continues.
- Per-frame redaction yields ``{"state": "streaming", "frame_index": i+1, "total": N, ...}``.
- Redaction failure -> ``{"state": "redaction_failed", ...}`` and stop.
- Final yield is ``{"state": "complete", "verdict": <dict>, ...}``.
- ``app.py`` registers ``live_diagnose`` with ``default_concurrency_limit=2``
  (RESEARCH OQ-2 resolution).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from wifi_diag_schema import TelemetryFrame
from wifi_diag_schema.handshake import HandshakeFrame, make_handshake
from wifi_diag_schema.telemetry import PingContinuity

_SPACE_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_frames_json() -> list[str]:
    """Return 5 valid TelemetryFrame JSON strings (window-major)."""
    base_ts = 1_730_000_000.0
    frames: list[str] = []
    for i in range(5):
        tf = TelemetryFrame(
            timestamp=base_ts + float(i),
            os="windows",
            network_mode="enterprise",
            rssi_dbm=-55 - (i % 5),
            bssid="a" * 64,
            bssid_mode="hashed",
            channel=36,
            ping_continuity=PingContinuity(
                window_ms=1000,
                avg_rtt_ms=18.0 + 0.1 * i,
                packet_loss_pct=0.0,
                jitter_ms=1.0,
            ),
            dhcp_event_class="none",
            auth_event_class="none",
            captive_portal_detected=False,
            mac_randomization_state="off",
            driver_state="normal",
            window_ms=120000,
        )
        frames.append(tf.model_dump_json())
    return frames


@pytest.fixture(autouse=True)
def _enable_owner_key(monkeypatch):
    """Set OWNER_KEY env var so live_diagnose accepts session requests in tests."""
    monkeypatch.setenv("OWNER_KEY", "test-owner-key")
    monkeypatch.delenv("LIVE_DISABLED", raising=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_handshake_first_yield(synthetic_frames_json, pinned_salt):
    """First yield on compatible schema MUST be ``state=handshake_ok``."""
    from src.space.live.live_diagnose import live_diagnose

    hs = make_handshake().model_dump_json()
    gen = live_diagnose(hs, [], "test-owner-key", None)
    first = next(gen)
    assert first["state"] == "handshake_ok"
    assert "schema_version" in first
    assert "space_version" in first


def test_major_mismatch_yields_error(synthetic_frames_json):
    """Major-version mismatch MUST yield ``schema_mismatch`` and stop the generator."""
    from src.space.live.live_diagnose import live_diagnose

    hs = HandshakeFrame(schema_version="2.0.0").model_dump_json()
    gen = live_diagnose(hs, synthetic_frames_json, "test-owner-key", None)
    first = next(gen)
    assert first["state"] == "schema_mismatch"
    assert "error" in first
    with pytest.raises(StopIteration):
        next(gen)


def test_minor_drift_warns_continues(synthetic_frames_json, pinned_salt):
    """Minor-version drift MUST yield ``handshake_ok`` with ``schema_drift=minor`` and continue."""
    import warnings

    from src.space.live.live_diagnose import live_diagnose

    hs = HandshakeFrame(schema_version="1.0.0").model_dump_json()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gen = live_diagnose(hs, [], "test-owner-key", None)
        first = next(gen)
    assert first["state"] == "handshake_ok"
    assert first.get("schema_drift") == "minor"


def test_per_frame_redaction_runs(synthetic_frames_json, pinned_salt):
    """Each frame in frames_json_list MUST get a ``streaming`` yield."""
    from src.space.live.live_diagnose import live_diagnose

    hs = make_handshake().model_dump_json()
    gen = live_diagnose(hs, synthetic_frames_json, "test-owner-key", None)
    yields = list(gen)
    streaming = [y for y in yields if y.get("state") == "streaming"]
    assert len(streaming) == len(synthetic_frames_json)
    for i, y in enumerate(streaming):
        assert y["frame_index"] == i + 1
        assert y["total"] == len(synthetic_frames_json)
        assert y["redaction_passed"] is True


def test_redaction_failure_yields_red(pinned_salt):
    """A frame that fails redaction MUST yield ``redaction_failed`` and stop."""
    from src.space.live.live_diagnose import live_diagnose

    hs = make_handshake().model_dump_json()
    # A malformed payload — not valid JSON at all.
    bad_frame = "this is not json at all {{"
    gen = live_diagnose(hs, [bad_frame], "test-owner-key", None)
    yields = list(gen)
    states = [y["state"] for y in yields]
    assert "handshake_ok" in states
    assert "redaction_failed" in states
    # Generator MUST stop after redaction_failed (no streaming/computing/complete after).
    rf_idx = states.index("redaction_failed")
    assert "streaming" not in states[rf_idx:]
    assert "computing" not in states[rf_idx:]
    assert "complete" not in states[rf_idx:]


def test_final_yield_is_verdict(synthetic_frames_json, pinned_salt):
    """After streaming all frames, generator MUST yield ``computing`` then
    ``complete`` with a Verdict."""
    from src.space.live.live_diagnose import live_diagnose

    hs = make_handshake().model_dump_json()
    gen = live_diagnose(hs, synthetic_frames_json, "test-owner-key", None)
    yields = list(gen)
    states = [y["state"] for y in yields]
    assert states[-2] == "computing"
    assert states[-1] == "complete"
    final = yields[-1]
    assert "verdict" in final
    verdict = final["verdict"]
    # Verdict shape sanity check
    assert "top_class" in verdict
    assert "confidence" in verdict


def test_session_rejected_without_owner_or_pair(synthetic_frames_json, pinned_salt):
    """Neither valid owner_key nor valid pair_code -> session_rejected."""
    from src.space.live.live_diagnose import live_diagnose

    hs = make_handshake().model_dump_json()
    gen = live_diagnose(hs, synthetic_frames_json, None, None)
    yields = list(gen)
    states = [y["state"] for y in yields]
    assert "session_rejected" in states
    sr_idx = states.index("session_rejected")
    assert "streaming" not in states[sr_idx:]
    assert "complete" not in states[sr_idx:]


def test_live_disabled_kill_switch(synthetic_frames_json, pinned_salt, monkeypatch):
    """LIVE_DISABLED=1 env var -> live_disabled state (D-STATUS-30)."""
    monkeypatch.setenv("LIVE_DISABLED", "1")
    from src.space.live.live_diagnose import live_diagnose

    hs = make_handshake().model_dump_json()
    gen = live_diagnose(hs, synthetic_frames_json, "test-owner-key", None)
    yields = list(gen)
    states = [y["state"] for y in yields]
    assert "live_disabled" in states


def test_live_diagnose_registered_with_concurrency_2():
    """``app.py`` MUST register ``live_diagnose`` with ``default_concurrency_limit=2``.

    Verified via source scan (avoids loading the heavy Gradio queue object).
    """
    app_src = (_SPACE_ROOT / "app.py").read_text()
    assert "default_concurrency_limit=2" in app_src, (
        "app.py must call demo.queue(default_concurrency_limit=2) — RESEARCH OQ-2"
    )
    assert 'api_name="live_diagnose"' in app_src, (
        'app.py must register live_diagnose with api_name="live_diagnose"'
    )


def test_live_complete_verdict_is_narrated(synthetic_frames_json, pinned_salt):
    """GAP-1 regression guard (Phase 6 plan 06-01).

    Before Phase 6 the live SSE path emitted ``verdict.headline`` =
    ``"Pre-Phase-3 stub: classifier predicts ..."`` because
    ``live_diagnose.py`` skipped the narrator step that the
    agent's local-only path performs. This test asserts the live path
    now narrates the verdict before the ``state=complete`` yield --
    the marquee live-demo gap from
    .planning/v1.0.0-MILESTONE-AUDIT.md::GAP-1.

    Removing the ``narrate_templated(verdict, redacted_dicts)`` call
    from ``src/space/live/live_diagnose.py`` MUST cause this test to
    fail.

    Fixtures used (existing in this file / conftest.py):
      - ``synthetic_frames_json`` -- 5 valid TelemetryFrame JSON strings
      - ``pinned_salt`` -- pins BSSID salt so redaction is deterministic
      - autouse ``_enable_owner_key`` -- sets OWNER_KEY env var
    """
    from wifi_diag_schema.handshake import make_handshake

    from src.space.live.live_diagnose import live_diagnose

    hs = make_handshake().model_dump_json()
    yields = list(
        live_diagnose(
            handshake_json=hs,
            frames_json_list=synthetic_frames_json,
            owner_key="test-owner-key",
            pair_code=None,
        )
    )

    complete_yields = [y for y in yields if y.get("state") == "complete"]
    assert len(complete_yields) == 1, (
        f"expected exactly one state=complete yield, got "
        f"{len(complete_yields)} -- all yields: "
        f"{[y.get('state') for y in yields]}"
    )
    verdict = complete_yields[0]["verdict"]

    # 1. Headline is narrated, not stubbed.
    assert not verdict["headline"].startswith("Pre-Phase-3 stub:"), (
        f"Live path emitted Phase 2 stub headline: {verdict['headline']!r}. "
        "narrate_templated() call missing from live_diagnose.py?"
    )
    assert not verdict["headline"].startswith("Pre-narrator stub:"), (
        f"Live path emitted pre-narrator stub headline: {verdict['headline']!r}. "
        "narrate_templated() call missing from live_diagnose.py?"
    )

    # 2. suggested_fix is narrated, not stubbed.
    assert "Pre-Phase-3 stub" not in verdict["suggested_fix"], (
        f"Live path emitted stub suggested_fix: {verdict['suggested_fix']!r}"
    )
    assert "Pre-narrator stub" not in verdict["suggested_fix"], (
        f"Live path emitted pre-narrator stub suggested_fix: {verdict['suggested_fix']!r}"
    )

    # 3. Evidence list populated (LLM-02 / citation guardrail invariant).
    assert isinstance(verdict["evidence"], list), (
        f"verdict.evidence must be a list, got {type(verdict['evidence'])}"
    )
    assert len(verdict["evidence"]) >= 1, (
        "narrator returned empty evidence -- citation guardrail expects "
        "at least one citation per narrated verdict"
    )

    # 4. Every evidence item carries a telemetry_path (LLM-02).
    for i, item in enumerate(verdict["evidence"]):
        assert "telemetry_path" in item, f"evidence[{i}] missing telemetry_path: {item!r}"
