"""AP roam + rekey failure state machine.

Causal sequence:
  t=0..t1:        associated to AP-A, RSSI -75..-78 dBm and falling
  t1 (~50% through window): roam to AP-B (BSSID changes)
  t1..t1+1500ms:  EAPOL 4-way handshake on new BSSID
  t1+1500..+2500ms: M3 timeout — pairwise key never installed
  t1+2500..end:   stuck (no traffic) — pre-disconnect window only (Pitfall 2)

Distinguishing signal: BSSID change mid-window + auth_event_class flips to
eapol_m3_timeout near end.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from numpy.random import Generator

WINDOW_MS = 30000
SAMPLE_INTERVAL_MS = 1000
CLASS_SLUG = "ap_roam_rekey_fail"


def generate(rng: Generator) -> list[dict[str, Any]]:
    """Emit one window with a BSSID change + EAPOL M3 timeout near the end."""
    n_frames = WINDOW_MS // SAMPLE_INTERVAL_MS
    bssid_a = sha256(f"ap-a-{int(rng.integers(0, 1000))}".encode()).hexdigest()
    bssid_b = sha256(f"ap-b-{int(rng.integers(0, 1000))}".encode()).hexdigest()
    roam_at = int(n_frames * 0.5) + int(rng.integers(-2, 3))
    m3_at = int(n_frames * 0.85) + int(rng.integers(-2, 3))
    t0 = float(rng.uniform(1_700_000_000, 1_800_000_000))
    channel_a = int(rng.choice([36, 44]))
    channel_b = int(rng.choice([149, 157]))
    os_choice = str(rng.choice(["windows", "macos", "linux"]))

    frames: list[dict[str, Any]] = []
    for i in range(n_frames):
        t = t0 + i * (SAMPLE_INTERVAL_MS / 1000)
        if i < roam_at:
            rssi = -75 + int(rng.normal(0, 2))
            bssid = bssid_a
            channel = channel_a
        else:
            rssi = -65 + int(rng.normal(0, 2))
            bssid = bssid_b
            channel = channel_b

        rssi = max(-100, min(0, rssi))
        bcn = max(-100, min(0, rssi - int(rng.integers(0, 3))))
        # auth class
        if i < roam_at:
            auth_evt = "8021x_success"
        elif i < m3_at:
            auth_evt = "8021x_success"
        else:
            auth_evt = "eapol_m3_timeout"

        avg_rtt = float(rng.normal(30, 10)) if i >= roam_at else float(rng.normal(20, 5))
        loss_baseline = 5 if i >= m3_at else 0
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
                    "avg_rtt_ms": avg_rtt,
                    "packet_loss_pct": float(max(0.0, rng.normal(loss_baseline, 1))),
                    "jitter_ms": float(max(0.0, rng.normal(4, 1))),
                },
                "latency_jitter_ms": float(max(0.0, rng.normal(4, 1))),
                "dns_resolution_ms": float(max(0.0, rng.normal(20, 5))),
                "dhcp_event_class": "none",
                "auth_event_class": auth_evt,
                "captive_portal_detected": False,
                "mac_randomization_state": "off",
                "driver_state": "normal",
                "per_packet_retry_count": int(rng.integers(1, 8)),
                "rts_cts_rate": None,
                "beacon_rssi_dbm": bcn,
                "neighbor_ap_count_5ghz": int(rng.integers(3, 9)),
                "window_ms": WINDOW_MS,
            }
        )
    return frames
