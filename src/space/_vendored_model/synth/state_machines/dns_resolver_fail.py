"""DNS resolver failure state machine.

Causal sequence:
  t=0..t1:        L2/L3 fully healthy, DNS resolves in ~10-20 ms
  t1 (~50%):      resolver hangs / NXDOMAIN spike — dns_resolution_ms climbs to 5000+
  t1..end:        ICMP ping continuity stays healthy (proving non-DNS path works)
                  while DNS keeps failing — pre-disconnect window only (Pitfall 2)

Distinguishing signal: ping_continuity stays healthy WHILE dns_resolution_ms
spikes — isolates DNS layer from RF / association issues.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from numpy.random import Generator

WINDOW_MS = 30000
SAMPLE_INTERVAL_MS = 1000
CLASS_SLUG = "dns_resolver_fail"


def generate(rng: Generator) -> list[dict[str, Any]]:
    """Emit one window with DNS spike but healthy ICMP."""
    n_frames = WINDOW_MS // SAMPLE_INTERVAL_MS
    rssi_baseline = -55 + int(rng.integers(-3, 4))
    bssid = sha256(f"ap-{int(rng.integers(0, 1000))}".encode()).hexdigest()
    t0 = float(rng.uniform(1_700_000_000, 1_800_000_000))
    spike_at = int(n_frames * 0.5) + int(rng.integers(-2, 3))
    os_choice = str(rng.choice(["windows", "macos", "linux"]))
    channel = int(rng.choice([1, 6, 11, 36, 44]))

    frames: list[dict[str, Any]] = []
    for i in range(n_frames):
        t = t0 + i * (SAMPLE_INTERVAL_MS / 1000)
        rssi = rssi_baseline + int(rng.normal(0, 1.0))
        rssi = max(-100, min(0, rssi))
        bcn = max(-100, min(0, rssi - int(rng.integers(0, 2))))

        if i < spike_at:
            dns_ms = float(max(0.0, rng.normal(12, 2)))
        else:
            # NXDOMAIN spike or DNS timeout
            dns_ms = float(rng.uniform(5000, 8000))

        frames.append(
            {
                "timestamp": t,
                "os": os_choice,
                "network_mode": "home",
                "rssi_dbm": rssi,
                "bssid": bssid,
                "bssid_mode": "hashed",
                "channel": channel,
                "ping_continuity": {
                    "window_ms": SAMPLE_INTERVAL_MS,
                    "avg_rtt_ms": float(rng.normal(18, 3)),
                    "packet_loss_pct": float(max(0.0, rng.normal(0, 0.3))),
                    "jitter_ms": float(max(0.0, rng.normal(2, 0.5))),
                },
                "latency_jitter_ms": float(max(0.0, rng.normal(2, 0.5))),
                "dns_resolution_ms": dns_ms,
                "dhcp_event_class": "none",
                "auth_event_class": "none",
                "captive_portal_detected": False,
                "mac_randomization_state": "per_network",
                "driver_state": "normal",
                "per_packet_retry_count": int(rng.integers(0, 3)),
                "rts_cts_rate": None,
                "beacon_rssi_dbm": bcn,
                "neighbor_ap_count_5ghz": int(rng.integers(0, 5)),
                "window_ms": WINDOW_MS,
            }
        )
    return frames
