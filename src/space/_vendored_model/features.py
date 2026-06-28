"""Feature matrix assembly from Phase 1 Parquet (RESEARCH Pattern 0).

Vendored from ai-internet-diagnostic-model v1.0.0 -- DO NOT edit; resync via
`make resync-model` (Phase 5). The only modification from the source is the
relative-import rewrite below (`model.synth.state_machines` -> `.synth.state_machines`).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from .synth.state_machines import GENERATORS

# Canonical class label order — MUST match Phase 1's GENERATORS insertion order.
CLASSES: list[str] = list(GENERATORS.keys())  # 10 entries, fixed order

# D-ANOM-04 features list (used by anomaly detector; numerics-only)
ANOMALY_FEATURES: tuple[str, ...] = (
    "rssi_dbm",
    "ping_continuity_avg_rtt_ms",
    "ping_continuity_packet_loss_pct",
    "ping_continuity_jitter_ms",
    "latency_jitter_ms",
    "dns_resolution_ms",
    "per_packet_retry_count",
    "beacon_rssi_dbm",
    "neighbor_ap_count_5ghz",
)

# Categoricals — integer-coded for LightGBM (Pitfall 5: confirm Phase 1 emits no None
# for these via tests/test_synth_class_coverage.py — fields are non-Optional in schema).
CATEGORICAL_FEATURES: tuple[str, ...] = (
    "os",
    "network_mode",
    "dhcp_event_class",
    "auth_event_class",
    "mac_randomization_state",
    "driver_state",
    "captive_portal_detected",  # bool — integer-coded
    "bssid_mode",
)

# 9 anomaly numerics + 8 categoricals + 3 misc numerics = 20 features.
# `bssid` excluded (high-cardinality, sub-leakage-prone).
# `timestamp` excluded (trivially correlated with disconnect_ts — Pitfall 2).
# `ping_continuity_window_ms` excluded (constant per row inside a window).
CLASSIFIER_FEATURES: tuple[str, ...] = (
    ANOMALY_FEATURES + CATEGORICAL_FEATURES + ("window_ms", "channel", "rts_cts_rate")
)


def load_split(parquet_path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Load a Parquet split into (X, y, feature_names).

    X is column-aligned to CLASSIFIER_FEATURES; categoricals are integer-encoded.
    y is integer-encoded against CLASSES (consistent with sklearn label encoding).
    """
    tbl = pq.read_table(parquet_path)
    df = tbl.to_pandas()

    for col in CATEGORICAL_FEATURES:
        df[col] = df[col].astype("category").cat.codes  # int8/int16; NaN -> -1

    X = df[list(CLASSIFIER_FEATURES)].to_numpy(dtype=np.float64)
    y = np.array([CLASSES.index(c) for c in df["class"].tolist()], dtype=np.int64)
    return X, y, list(CLASSIFIER_FEATURES)


def load_anomaly_features(
    parquet_path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For IForest: numerics-only X + per-row class label + per-row timestamp.

    Returns (X_anom, y_int, ts) where ts drives lead-time computation (Pattern 9).
    Rows where `class` is not in CLASSES (e.g., normal-split baseline) are encoded as -1.
    """
    tbl = pq.read_table(parquet_path)
    df = tbl.to_pandas()
    X_anom = df[list(ANOMALY_FEATURES)].to_numpy(dtype=np.float64)

    class_lookup = {slug: i for i, slug in enumerate(CLASSES)}
    y_int = np.array([class_lookup.get(c, -1) for c in df["class"].tolist()], dtype=np.int64)
    ts = df["timestamp"].to_numpy()
    return X_anom, y_int, ts
