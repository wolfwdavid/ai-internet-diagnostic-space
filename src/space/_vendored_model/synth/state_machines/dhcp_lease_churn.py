"""DHCP lease churn state machine.

Causal sequence:
  t=0..t1:        L2 associated, but DHCP server is misbehaving
  cycle:          DHCPDISCOVER -> no offer -> DHCPDISCOVER (retry) -> NAK on renew -> request_loop
  end:            no usable IP at window end (pre-disconnect — Pitfall 2)

Distinguishing signal: dhcp_event_class cycles through discover_no_offer,
nak_on_renew, request_loop while DNS lookups fail (no usable resolver).
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from numpy.random import Generator

WINDOW_MS = 30000
SAMPLE_INTERVAL_MS = 1000
CLASS_SLUG = "dhcp_lease_churn"

DHCP_CYCLE = ["discover_no_offer", "discover_no_offer", "nak_on_renew", "request_loop"]


def generate(rng: Generator) -> list[dict[str, Any]]:
    """Emit one window with cycling DHCP failures and no usable DNS."""
    n_frames = WINDOW_MS // SAMPLE_INTERVAL_MS
    rssi_baseline = -60 + int(rng.integers(-5, 6))
    bssid = sha256(f"ap-{int(rng.integers(0, 1000))}".encode()).hexdigest()
    t0 = float(rng.uniform(1_700_000_000, 1_800_000_000))
    cycle_offset = int(rng.integers(0, len(DHCP_CYCLE)))
    os_choice = str(rng.choice(["windows", "macos", "linux"]))
    channel = int(rng.choice([36, 44, 149, 157]))

    frames: list[dict[str, Any]] = []
    for i in range(n_frames):
        t = t0 + i * (SAMPLE_INTERVAL_MS / 1000)
        # cycle through DHCP failure modes
        dhcp_evt = DHCP_CYCLE[(i + cycle_offset) % len(DHCP_CYCLE)] if i % 3 == 0 else "none"
        rssi = rssi_baseline + int(rng.normal(0, 1.5))
        rssi = max(-100, min(0, rssi))
        bcn = max(-100, min(0, rssi - int(rng.integers(0, 3))))

        frames.append({
            "timestamp": t,
            "os": os_choice,
            "network_mode": "enterprise",
            "rssi_dbm": rssi,
            "bssid": bssid,
            "bssid_mode": "hashed",
            "channel": channel,
            "ping_continuity": {
                "window_ms": SAMPLE_INTERVAL_MS,
                "avg_rtt_ms": None,  # no IP, no ping
                "packet_loss_pct": 100.0,
                "jitter_ms": None,
            },
            "latency_jitter_ms": None,
            "dns_resolution_ms": None,  # DNS unusable without lease
            "dhcp_event_class": dhcp_evt,
            "auth_event_class": "8021x_success",
            "captive_portal_detected": False,
            "mac_randomization_state": "off",
            "driver_state": "normal",
            "per_packet_retry_count": None,
            "rts_cts_rate": None,
            "beacon_rssi_dbm": bcn,
            "neighbor_ap_count_5ghz": int(rng.integers(2, 7)),
            "window_ms": WINDOW_MS,
        })
    return frames
