"""RADIUS timeout state machine.

Causal sequence:
  t=0..t1:           associated, RSSI healthy (-60 ± 5)
  t1:                supplicant initiates re-auth
  t1..t1+5000ms:     3 supplicant retries with auth_event_class=radius_timeout
  t1+5000ms:         final EAP-Failure (RADIUS unreachable beyond retry budget)

Distinguishing signal: 3 consecutive radius_timeout frames followed by an
8021x_fail / eap_fail terminator (pre-disconnect only — Pitfall 2).
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from numpy.random import Generator

WINDOW_MS = 30000
SAMPLE_INTERVAL_MS = 1000
CLASS_SLUG = "radius_timeout"


def generate(rng: Generator) -> list[dict[str, Any]]:
    """Emit one window with 3 RADIUS retries then EAP failure."""
    n_frames = WINDOW_MS // SAMPLE_INTERVAL_MS
    rssi_baseline = -60 + int(rng.integers(-5, 6))
    bssid = sha256(f"ap-{int(rng.integers(0, 1000))}".encode()).hexdigest()
    t0 = float(rng.uniform(1_700_000_000, 1_800_000_000))
    retry_start = int(n_frames * 0.7) + int(rng.integers(-2, 3))
    eap_fail_at = retry_start + 3
    os_choice = str(rng.choice(["windows", "macos", "linux"]))
    channel = int(rng.choice([36, 44, 149, 157]))

    frames: list[dict[str, Any]] = []
    for i in range(n_frames):
        t = t0 + i * (SAMPLE_INTERVAL_MS / 1000)
        if i < retry_start:
            auth_evt = "8021x_success"
        elif i < eap_fail_at:
            auth_evt = "radius_timeout"
        else:
            auth_evt = "eap_fail"

        rssi = rssi_baseline + int(rng.normal(0, 1.5))
        rssi = max(-100, min(0, rssi))
        bcn = max(-100, min(0, rssi - int(rng.integers(0, 3))))

        frames.append(
            {
                "timestamp": t,
                "os": os_choice,
                "network_mode": "enterprise",
                "rssi_dbm": rssi,
                "bssid": bssid,
                "bssid_mode": "hashed",
                "channel": channel,
                "ping_continuity": {
                    "window_ms": SAMPLE_INTERVAL_MS,
                    "avg_rtt_ms": float(rng.normal(50, 15)),
                    "packet_loss_pct": float(max(0.0, rng.normal(0 if i < retry_start else 3, 1))),
                    "jitter_ms": float(max(0.0, rng.normal(5, 2))),
                },
                "latency_jitter_ms": float(max(0.0, rng.normal(5, 2))),
                "dns_resolution_ms": float(max(0.0, rng.normal(25, 5))),
                "dhcp_event_class": "none",
                "auth_event_class": auth_evt,
                "captive_portal_detected": False,
                "mac_randomization_state": "off",
                "driver_state": "normal",
                "per_packet_retry_count": int(rng.integers(0, 5)),
                "rts_cts_rate": None,
                "beacon_rssi_dbm": bcn,
                "neighbor_ap_count_5ghz": int(rng.integers(2, 7)),
                "window_ms": WINDOW_MS,
            }
        )
    return frames
