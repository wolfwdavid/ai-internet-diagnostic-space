"""802.1X EAP failure state machine (RESEARCH Pattern 5).

Causal sequence (Microsoft + Cisco docs):
  t=0..t1:           associated, RSSI -65..-55 dBm
  t1:                re-auth timer fires
  t1..t1+200ms:      EAPOL-Start
  t1+200..+800ms:    EAP-Request/Identity exchange
  t1+800..+2000ms:   EAP-TLS handshake
  t1+2000ms:         EAP-Failure (cert expired / RADIUS reject / TLS mismatch)
  t1+2000..end:      deauth (NOT included in pre-disconnect window — Pitfall 2)
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from numpy.random import Generator

WINDOW_MS = 30000
SAMPLE_INTERVAL_MS = 1000  # 1 frame/sec; 30 frames per window
CLASS_SLUG = "auth_8021x_eap_fail"


def generate(rng: Generator) -> list[dict[str, Any]]:
    """Emit one window's worth of TelemetryFrame-shaped dicts (pre-disconnect only)."""
    n_frames = WINDOW_MS // SAMPLE_INTERVAL_MS
    rssi_baseline = int(rng.integers(-65, -54))
    bssid_hash = sha256(f"ap-{int(rng.integers(0, 1000))}".encode()).hexdigest()
    t0 = float(rng.uniform(1_700_000_000, 1_800_000_000))

    frames: list[dict[str, Any]] = []
    for i in range(n_frames):
        t = t0 + i * (SAMPLE_INTERVAL_MS / 1000)
        # auth_event_class flips to 8021x_fail at the failure event (~93% through window)
        auth_evt = "8021x_fail" if i >= int(n_frames * 0.93) else "8021x_success"
        rssi = rssi_baseline + int(rng.normal(0, 1.5))
        rssi = max(-100, min(0, rssi))
        bcn = max(-100, min(0, rssi - int(rng.integers(0, 3))))

        frames.append(
            {
                "timestamp": t,
                "os": str(rng.choice(["windows", "macos", "linux"])),
                "network_mode": "enterprise",
                "rssi_dbm": rssi,
                "bssid": bssid_hash,
                "bssid_mode": "hashed",
                "channel": int(rng.choice([36, 44, 149, 157])),
                "ping_continuity": {
                    "window_ms": SAMPLE_INTERVAL_MS,
                    "avg_rtt_ms": float(rng.normal(20, 5)),
                    "packet_loss_pct": float(max(0.0, rng.normal(0, 0.5))),
                    "jitter_ms": float(max(0.0, rng.normal(2, 0.5))),
                },
                "latency_jitter_ms": float(max(0.0, rng.normal(2, 0.5))),
                "dns_resolution_ms": float(max(0.0, rng.normal(15, 3))),
                "dhcp_event_class": "none",
                "auth_event_class": auth_evt,
                "captive_portal_detected": False,
                "mac_randomization_state": "off",
                "driver_state": "normal",
                "per_packet_retry_count": int(rng.integers(0, 5)),
                "rts_cts_rate": None,
                "beacon_rssi_dbm": bcn,
                "neighbor_ap_count_5ghz": int(rng.integers(2, 8)),
                "window_ms": WINDOW_MS,
            }
        )
    return frames
