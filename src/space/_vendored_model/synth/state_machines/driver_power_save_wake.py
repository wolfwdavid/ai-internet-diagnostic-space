"""Driver power-save / post-wake degradation state machine (slow event, 120s window per D-04).

Causal sequence:
  t=0..t1 (~10s):  driver_state=post_wake_init after sleep / hibernate resume;
                   RSSI drops sharply -65 -> -90 dBm
  t1..t2 (~30s):   driver_state=power_save_active; ping jitter spikes; retries climb
  t2..end:         driver_state=error; intermittent hangs (pre-disconnect — Pitfall 2)

Distinguishing signal: driver_state non-normal for the whole window combined
with sudden RSSI drop and sustained jitter spike.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from numpy.random import Generator

WINDOW_MS = 120000  # slow event per D-04
SAMPLE_INTERVAL_MS = 4000  # 30 frames per window
CLASS_SLUG = "driver_power_save_wake"


def generate(rng: Generator) -> list[dict[str, Any]]:
    """Emit one window of post-wake degradation (slow event)."""
    n_frames = WINDOW_MS // SAMPLE_INTERVAL_MS
    bssid = sha256(f"ap-{int(rng.integers(0, 1000))}".encode()).hexdigest()
    t0 = float(rng.uniform(1_700_000_000, 1_800_000_000))
    wake_init_until = int(n_frames * 0.33)
    error_after = int(n_frames * 0.85)
    os_choice = str(rng.choice(["windows", "macos", "linux"]))
    channel = int(rng.choice([36, 44, 149, 157]))

    frames: list[dict[str, Any]] = []
    for i in range(n_frames):
        t = t0 + i * (SAMPLE_INTERVAL_MS / 1000)
        if i < wake_init_until:
            driver_state = "post_wake_init"
            rssi = -65 + int(rng.normal(0, 2)) - int((wake_init_until - i) * 0)
        elif i < error_after:
            driver_state = "power_save_active"
            rssi = -90 + int(rng.normal(0, 4))
        else:
            driver_state = "error"
            rssi = -85 + int(rng.normal(0, 5))

        rssi = max(-100, min(0, rssi))
        bcn = max(-100, min(0, rssi - int(rng.integers(0, 5))))

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
                    "avg_rtt_ms": float(rng.normal(80, 30)),
                    "packet_loss_pct": float(max(0.0, rng.normal(8, 4))),
                    "jitter_ms": float(max(0.0, rng.normal(15, 5))),
                },
                "latency_jitter_ms": float(max(0.0, rng.normal(15, 5))),
                "dns_resolution_ms": float(max(0.0, rng.normal(60, 20))),
                "dhcp_event_class": "none",
                "auth_event_class": "8021x_success",
                "captive_portal_detected": False,
                "mac_randomization_state": "off",
                "driver_state": driver_state,
                "per_packet_retry_count": int(rng.integers(3, 12)),
                "rts_cts_rate": None,
                "beacon_rssi_dbm": bcn,
                "neighbor_ap_count_5ghz": int(rng.integers(2, 8)),
                "window_ms": WINDOW_MS,
            }
        )
    return frames
