"""Phase 3 plan 03-01 shared fixtures.

The ``sample_window`` fixture produces a 30-frame TelemetryFrame-shaped window
with realistic enterprise-Wi-Fi values. It is used by the InferenceOrchestrator
contract tests (test_inference_orchestrator.py) and downstream timeline /
narrator plans.
"""
from __future__ import annotations

import pytest


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
