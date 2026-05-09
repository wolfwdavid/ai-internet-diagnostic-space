"""Normal-baseline synthetic generator (RESEARCH Pattern 8b).

Emits healthy-shape pre-disconnect frames for IForest threshold calibration
(D-ANOM-02). NOT a class -- does NOT inject any failure event. Sampled from the
union of inlier distributions across the 10 existing state machines.

Pitfall 2 convention: pre-disconnect window only (still applies -- for
normal_baseline the whole window stays healthy; there is no disconnect).
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from numpy.random import Generator

BASELINE_LABEL: str = "_normal_baseline"
FRAMES_PER_WINDOW: int = 30  # mirrors Phase 1 emission rate

# Healthy ranges sampled from inlier portions of the 10 state-machine distributions.
# These are the "happy" steady-state values BEFORE any state machine starts injecting
# failures. Documented in MODEL_CARD.md Metrics section as the threshold-calibration
# source. NetworkMode distribution: weighted by the rough mix in the train set
# (enterprise dominates because most failure classes are enterprise-tagged).
_NETWORK_MODES = ("enterprise", "captive", "home", "unknown")
_NETWORK_MODE_WEIGHTS = (0.50, 0.15, 0.30, 0.05)
_OS_VALUES = ("windows", "macos", "linux")
_CHANNELS = (6, 11, 36, 40, 44, 48, 149, 157)
_WINDOW_MS_OPTIONS = (30000, 120000)


def _normal_baseline_window(rng: Generator) -> list[dict[str, Any]]:
    """Emit one ~30-frame window of healthy steady-state frames.

    All frames carry network_mode / os fixed within the window (a session is
    on one network); numerics are sampled per-frame with low variance to
    simulate "stable steady state".
    """
    # Window-fixed metadata
    window_ms = int(rng.choice(_WINDOW_MS_OPTIONS))
    n_frames = FRAMES_PER_WINDOW
    net_mode = str(rng.choice(_NETWORK_MODES, p=_NETWORK_MODE_WEIGHTS))
    os_val = str(rng.choice(_OS_VALUES))
    channel = int(rng.choice(_CHANNELS))
    bssid_hash = sha256(f"ap-normal-{int(rng.integers(0, 1000))}".encode()).hexdigest()

    # Sample interval (ms per frame) -- matches Phase 1's per-state-machine convention
    sample_interval_ms = window_ms // n_frames

    # Healthy steady-state per-frame numerics -- drawn from inlier means across
    # the 10 state machines' opening / mid-window stable phases.
    rssi_mean = float(rng.uniform(-65.0, -45.0))
    rtt_mean = float(rng.uniform(8.0, 35.0))
    jitter_mean = float(rng.uniform(1.0, 8.0))
    retry_lambda = float(rng.uniform(0.5, 2.0))

    frames: list[dict[str, Any]] = []
    # Frame timestamps = unix-epoch-shaped seconds within window (mirror Phase 1)
    t0 = float(rng.uniform(1_700_000_000, 1_800_000_000))
    for i in range(n_frames):
        ts = t0 + i * (sample_interval_ms / 1000.0)
        rssi = int(max(-100, min(0, rssi_mean + rng.normal(0.0, 1.5))))
        avg_rtt = float(max(1.0, rtt_mean + rng.normal(0.0, 2.0)))
        packet_loss = float(max(0.0, rng.normal(0.0, 0.05)))
        jitter = float(max(0.1, jitter_mean + rng.normal(0.0, 0.8)))
        dns = float(max(2.0, rng.normal(15.0, 4.0)))
        retries = int(max(0, rng.poisson(retry_lambda)))
        beacon = int(max(-100, min(0, rssi - int(rng.integers(0, 3)))))
        neighbors = int(max(0, rng.poisson(3.0)))
        rts_cts = float(min(1.0, max(0.0, rng.normal(0.05, 0.02))))

        frames.append({
            "timestamp": ts,
            "os": os_val,
            "network_mode": net_mode,
            "rssi_dbm": rssi,
            "bssid": bssid_hash,
            "bssid_mode": "hashed",
            "channel": channel,
            "ping_continuity": {
                "window_ms": int(sample_interval_ms),
                "avg_rtt_ms": avg_rtt,
                "packet_loss_pct": packet_loss,
                "jitter_ms": jitter,
            },
            "latency_jitter_ms": jitter,
            "dns_resolution_ms": dns,
            "dhcp_event_class": "none",
            "auth_event_class": "8021x_success",  # canonical "no auth event" in trained data
            "captive_portal_detected": False,
            "mac_randomization_state": "off",
            "driver_state": "normal",
            "per_packet_retry_count": retries,
            "rts_cts_rate": rts_cts,
            "beacon_rssi_dbm": beacon,
            "neighbor_ap_count_5ghz": neighbors,
            "window_ms": int(window_ms),
            "class": BASELINE_LABEL,
        })
    return frames
