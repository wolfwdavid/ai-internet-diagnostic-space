"""RF sticky-client state machine (slow event, 120s window per D-04).

Causal sequence:
  t=0..t1 (~30s):  associated to AP-A, RSSI -78 dBm and gradually falling
  t1..t2 (~80s):   RSSI continues to -85 dBm; per_packet_retry_count climbs;
                   neighbor_ap_count_5ghz shows healthier neighbors at -55 dBm
                   but client never roams (BSSID never changes)
  t2..end:         RTT climbs, retries near saturation (pre-disconnect — Pitfall 2)

Distinguishing signal: BSSID constant, RSSI declining toward -85, retries
climbing, AND neighbor_ap_count_5ghz reports better candidates available.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from numpy.random import Generator

WINDOW_MS = 120000  # slow event per D-04
SAMPLE_INTERVAL_MS = 4000  # 30 frames per window
CLASS_SLUG = "rf_sticky_client"


def generate(rng: Generator) -> list[dict[str, Any]]:
    """Emit one window of gradual RSSI decline with stuck BSSID."""
    n_frames = WINDOW_MS // SAMPLE_INTERVAL_MS
    bssid = sha256(f"ap-{int(rng.integers(0, 1000))}".encode()).hexdigest()
    t0 = float(rng.uniform(1_700_000_000, 1_800_000_000))
    os_choice = str(rng.choice(["windows", "macos", "linux"]))
    channel = int(rng.choice([36, 44]))

    frames: list[dict[str, Any]] = []
    for i in range(n_frames):
        t = t0 + i * (SAMPLE_INTERVAL_MS / 1000)
        progress = i / max(1, n_frames - 1)  # 0 -> 1
        # gradual decline -78 -> -85
        rssi = int(-78 - progress * 7 + rng.normal(0, 1.5))
        rssi = max(-100, min(0, rssi))
        bcn = max(-100, min(0, rssi - int(rng.integers(0, 3))))
        retries = int(2 + progress * 13 + rng.integers(-1, 2))
        retries = max(0, retries)

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
                    "avg_rtt_ms": float(20 + progress * 80 + rng.normal(0, 5)),
                    "packet_loss_pct": float(max(0.0, progress * 5 + rng.normal(0, 1))),
                    "jitter_ms": float(max(0.0, 3 + progress * 7 + rng.normal(0, 1))),
                },
                "latency_jitter_ms": float(max(0.0, 3 + progress * 7 + rng.normal(0, 1))),
                "dns_resolution_ms": float(max(0.0, 20 + progress * 30 + rng.normal(0, 3))),
                "dhcp_event_class": "none",
                "auth_event_class": "8021x_success",
                "captive_portal_detected": False,
                "mac_randomization_state": "off",
                "driver_state": "normal",
                "per_packet_retry_count": retries,
                "rts_cts_rate": float(rng.uniform(0.05, 0.25)),
                "beacon_rssi_dbm": bcn,
                "neighbor_ap_count_5ghz": int(rng.integers(5, 10)),  # healthier neighbors visible
                "window_ms": WINDOW_MS,
            }
        )
    return frames
