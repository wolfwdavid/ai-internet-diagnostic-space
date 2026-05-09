"""ISP upstream failure state machine.

Causal sequence:
  t=0..t1:        Wi-Fi all healthy; ICMP to default gateway (LAN-side) succeeds
  t1 (~40%):      upstream link to ISP fails; ICMP to public targets starts losing
  t1..end:        gateway-reachable but public-unreachable; pre-disconnect (Pitfall 2)

Distinguishing signal: RSSI / DHCP / DNS / auth all healthy yet ping continuity
to public targets degrades sharply. Modeled as packet_loss_pct rising on the
PingContinuity sub-frame (which the agent measures against a public ICMP target).
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from numpy.random import Generator

WINDOW_MS = 30000
SAMPLE_INTERVAL_MS = 1000
CLASS_SLUG = "isp_upstream_fail"


def generate(rng: Generator) -> list[dict[str, Any]]:
    """Emit one window where Wi-Fi is healthy but public ICMP loses sharply."""
    n_frames = WINDOW_MS // SAMPLE_INTERVAL_MS
    rssi_baseline = -55 + int(rng.integers(-3, 4))
    bssid = sha256(f"ap-{int(rng.integers(0, 1000))}".encode()).hexdigest()
    t0 = float(rng.uniform(1_700_000_000, 1_800_000_000))
    fail_at = int(n_frames * 0.4) + int(rng.integers(-2, 3))
    os_choice = str(rng.choice(["windows", "macos", "linux"]))
    channel = int(rng.choice([1, 6, 11, 36, 44]))

    frames: list[dict[str, Any]] = []
    for i in range(n_frames):
        t = t0 + i * (SAMPLE_INTERVAL_MS / 1000)
        rssi = rssi_baseline + int(rng.normal(0, 1.0))
        rssi = max(-100, min(0, rssi))
        bcn = max(-100, min(0, rssi - int(rng.integers(0, 2))))

        if i < fail_at:
            loss = float(max(0.0, rng.normal(0, 0.3)))
            rtt = float(rng.normal(20, 5))
        else:
            loss = float(min(100.0, max(0.0, rng.normal(60, 15))))
            rtt = float(rng.normal(150, 50))

        frames.append({
            "timestamp": t,
            "os": os_choice,
            "network_mode": "home",
            "rssi_dbm": rssi,
            "bssid": bssid,
            "bssid_mode": "hashed",
            "channel": channel,
            "ping_continuity": {
                "window_ms": SAMPLE_INTERVAL_MS,
                "avg_rtt_ms": rtt,
                "packet_loss_pct": loss,
                "jitter_ms": float(max(0.0, rng.normal(3, 1))),
            },
            "latency_jitter_ms": float(max(0.0, rng.normal(3, 1))),
            "dns_resolution_ms": float(max(0.0, rng.normal(15, 3))),
            "dhcp_event_class": "none",
            "auth_event_class": "none",
            "captive_portal_detected": False,
            "mac_randomization_state": "per_network",
            "driver_state": "normal",
            "per_packet_retry_count": int(rng.integers(0, 3)),
            "rts_cts_rate": None,
            "beacon_rssi_dbm": bcn,
            "neighbor_ap_count_5ghz": int(rng.integers(0, 4)),
            "window_ms": WINDOW_MS,
        })
    return frames
