"""MAC randomization reject state machine.

Causal sequence:
  t=0..t1:        association attempt with randomized MAC; RSSI healthy
  t1..end:        RADIUS Access-Reject because MAC isn't on the allowlist;
                  mac_randomization_state="rejected" persists; auth_event_class
                  reaches 8021x_fail near window end.

Distinguishing signal: mac_randomization_state="rejected" throughout the window
combined with 8021x_fail terminator (pre-disconnect — Pitfall 2).
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from numpy.random import Generator

WINDOW_MS = 30000
SAMPLE_INTERVAL_MS = 1000
CLASS_SLUG = "mac_randomization_reject"


def generate(rng: Generator) -> list[dict[str, Any]]:
    """Emit one window with mac_randomization_state='rejected' + 8021x_fail near end."""
    n_frames = WINDOW_MS // SAMPLE_INTERVAL_MS
    rssi_baseline = -60 + int(rng.integers(-5, 6))
    bssid = sha256(f"ap-{int(rng.integers(0, 1000))}".encode()).hexdigest()
    t0 = float(rng.uniform(1_700_000_000, 1_800_000_000))
    fail_at = int(n_frames * 0.8) + int(rng.integers(-2, 3))
    os_choice = str(rng.choice(["windows", "macos", "linux"]))
    channel = int(rng.choice([36, 44, 149, 157]))

    frames: list[dict[str, Any]] = []
    for i in range(n_frames):
        t = t0 + i * (SAMPLE_INTERVAL_MS / 1000)
        rssi = rssi_baseline + int(rng.normal(0, 1.5))
        rssi = max(-100, min(0, rssi))
        bcn = max(-100, min(0, rssi - int(rng.integers(0, 3))))
        auth_evt = "8021x_fail" if i >= fail_at else "none"

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
                    "avg_rtt_ms": None,
                    "packet_loss_pct": 100.0,  # never associated successfully
                    "jitter_ms": None,
                },
                "latency_jitter_ms": None,
                "dns_resolution_ms": None,
                "dhcp_event_class": "none",
                "auth_event_class": auth_evt,
                "captive_portal_detected": False,
                "mac_randomization_state": "rejected",
                "driver_state": "normal",
                "per_packet_retry_count": None,
                "rts_cts_rate": None,
                "beacon_rssi_dbm": bcn,
                "neighbor_ap_count_5ghz": int(rng.integers(2, 7)),
                "window_ms": WINDOW_MS,
            }
        )
    return frames
