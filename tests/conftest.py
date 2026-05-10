"""Phase 3 plan 03-01 shared fixtures.

The ``sample_window`` fixture produces a 30-frame TelemetryFrame-shaped window
with realistic enterprise-Wi-Fi values. It is used by the InferenceOrchestrator
contract tests (test_inference_orchestrator.py) and downstream timeline /
narrator plans.

The ``sample_verdict`` fixture (added in Phase 3 plan 03-02) produces a
schema-valid Verdict with all 10 ``top_k`` entries populated. It is used by
the verdict-card / what-to-do-card unit tests (test_verdict_card.py) and the
timeline tests (test_timeline.py) for evidence-list construction.
"""
from __future__ import annotations

import pytest

from wifi_diag_schema.verdict import EvidenceItem, Verdict


@pytest.fixture
def sample_window() -> list[dict]:
    """30-frame enterprise-Wi-Fi window suitable for predict() smoke testing.

    All fields populated; bssid uses the SHA-256 hashed shape (default-off raw
    opt-in per D-03). Window is monotonically increasing in timestamp at 1 Hz
    (window_ms=30000 per Phase 1 D-04 fast-event class).
    """
    base_ts = 1_730_000_000.0
    frames: list[dict] = []
    for i in range(30):
        frames.append({
            # Core 14
            "timestamp": base_ts + float(i),
            "os": "windows",
            "network_mode": "enterprise",
            "rssi_dbm": -55 - (i % 10),  # -55..-64
            "bssid": "a" * 64,            # 64-char SHA-256 hex
            "bssid_mode": "hashed",
            "channel": 36,
            "ping_continuity": {
                "window_ms": 1000,
                "avg_rtt_ms": 18.0 + 0.1 * i,
                "packet_loss_pct": 0.0,
                "jitter_ms": 1.0 + 0.05 * i,
            },
            "latency_jitter_ms": 1.0 + 0.05 * i,
            "dns_resolution_ms": 14.0,
            "dhcp_event_class": "none",
            "auth_event_class": "none",
            "captive_portal_detected": False,
            "mac_randomization_state": "off",
            "driver_state": "normal",
            # Extended 4
            "per_packet_retry_count": 2,
            "rts_cts_rate": 0.05,
            "beacon_rssi_dbm": -57 - (i % 8),
            "neighbor_ap_count_5ghz": 5,
            # Meta
            "window_ms": 30000,
        })
    return frames


@pytest.fixture
def sample_verdict() -> Verdict:
    """A schema-valid Verdict with all 10 ``top_k`` entries (D-CAL-08).

    Top class is ``auth_8021x_eap_fail`` (the project owner's school dogfood
    case); confidence 0.85 puts it in the HIGH band (D-VERDICT-01). Used by
    verdict-card / what-to-do-card tests (plan 03-02).
    """
    return Verdict(
        top_class="auth_8021x_eap_fail",
        confidence=0.85,
        top_k=[
            ("auth_8021x_eap_fail", 0.85),
            ("ap_roam_rekey_fail", 0.07),
            ("radius_timeout", 0.04),
            ("dhcp_lease_churn", 0.02),
            ("captive_portal_expiry", 0.01),
            ("rf_sticky_client", 0.005),
            ("driver_power_save_wake", 0.003),
            ("dns_resolver_fail", 0.001),
            ("mac_randomization_reject", 0.0005),
            ("isp_upstream_fail", 0.0005),
        ],
        headline="Your network's 802.1X authentication failed during this session.",
        suggested_fix="Re-enter your school/work credentials, or contact IT.",
        evidence=[
            EvidenceItem(
                telemetry_path="auth_event_class",
                claim="Auth event recorded as 8021x_fail",
            ),
        ],
    )
