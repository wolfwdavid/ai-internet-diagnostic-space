"""Captive-portal session-expiry state machine.

Causal sequence:
  t=0..t1:        L2/L3 healthy, RSSI strong (-55 ± 3), DNS works, no portal
  t1 (~90%):      portal session expires — outbound HTTP/HTTPS gets HTTP 302
                  to portal URL; captive_portal_detected flips True
  t1..end:        portal-detected frames (pre-disconnect window only — Pitfall 2)

Distinguishing signal: network_mode=captive AND captive_portal_detected flips
to True near end while RF and DNS remain healthy.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from numpy.random import Generator

WINDOW_MS = 30000
SAMPLE_INTERVAL_MS = 1000
CLASS_SLUG = "captive_portal_expiry"


def generate(rng: Generator) -> list[dict[str, Any]]:
    """Emit one window where portal detection flips True near the end."""
    n_frames = WINDOW_MS // SAMPLE_INTERVAL_MS
    rssi_baseline = -55 + int(rng.integers(-3, 4))
    bssid = sha256(f"ap-{int(rng.integers(0, 1000))}".encode()).hexdigest()
    t0 = float(rng.uniform(1_700_000_000, 1_800_000_000))
    portal_at = int(n_frames * 0.9) + int(rng.integers(-2, 3))
    os_choice = str(rng.choice(["windows", "macos", "linux"]))
    channel = int(rng.choice([1, 6, 11]))

    frames: list[dict[str, Any]] = []
    for i in range(n_frames):
        t = t0 + i * (SAMPLE_INTERVAL_MS / 1000)
        portal_flipped = i >= portal_at
        rssi = rssi_baseline + int(rng.normal(0, 1.0))
        rssi = max(-100, min(0, rssi))
        bcn = max(-100, min(0, rssi - int(rng.integers(0, 2))))

        frames.append(
            {
                "timestamp": t,
                "os": os_choice,
                "network_mode": "captive",
                "rssi_dbm": rssi,
                "bssid": bssid,
                "bssid_mode": "hashed",
                "channel": channel,
                "ping_continuity": {
                    "window_ms": SAMPLE_INTERVAL_MS,
                    "avg_rtt_ms": float(rng.normal(15, 3)),
                    "packet_loss_pct": float(max(0.0, rng.normal(0, 0.3))),
                    "jitter_ms": float(max(0.0, rng.normal(1.5, 0.5))),
                },
                "latency_jitter_ms": float(max(0.0, rng.normal(1.5, 0.5))),
                "dns_resolution_ms": float(max(0.0, rng.normal(12, 2))),
                "dhcp_event_class": "none",
                "auth_event_class": "none",
                "captive_portal_detected": portal_flipped,
                "mac_randomization_state": "per_network",
                "driver_state": "normal",
                "per_packet_retry_count": int(rng.integers(0, 3)),
                "rts_cts_rate": None,
                "beacon_rssi_dbm": bcn,
                "neighbor_ap_count_5ghz": int(rng.integers(0, 4)),
                "window_ms": WINDOW_MS,
            }
        )
    return frames
