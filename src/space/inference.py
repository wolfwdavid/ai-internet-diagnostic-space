"""InferenceOrchestrator -- loads Phase 2 artifacts once at module import.

Pattern 1 from .planning/phases/03-space-ui-real-inference/03-RESEARCH.md:
the load cost (sklearn deserialization, LightGBM booster materialization,
PyOD IForest reconstruction) happens exactly once per Space process. Each
Gradio request calls predict() with a telemetry window and gets back a
schema-valid Verdict + the per-frame anomaly score series for the timeline.

The vendored Phase 2 model code lives under ``_vendored_model/`` so the
Space can compute real classifier output without round-tripping the Hub.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from wifi_diag_schema.verdict import Verdict

from ._vendored_model.features import CLASSIFIER_FEATURES  # noqa: F401  (re-export anchor)
from ._vendored_model.inference import predict_verdict as _predict_verdict

# Resolve from this file: src/space/inference.py -> repo_root/artifacts/
_ARTIFACTS = Path(__file__).resolve().parent.parent.parent / "artifacts"

# Load-once singletons (Phase 2 D-PUB-05 filenames).
_CLASSIFIER = joblib.load(_ARTIFACTS / "classifier.joblib")
_ANOMALY_BUNDLE = joblib.load(_ARTIFACTS / "anomaly.joblib")
_ANOMALY_DETECTOR = _ANOMALY_BUNDLE["detector"]
_ANOMALY_THRESHOLD = float(_ANOMALY_BUNDLE["threshold"])

# Anomaly numerics (D-ANOM-04 mirror; the only fields the IForest was trained on).
_ANOMALY_FEATURE_COLS: tuple[str, ...] = (
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


def _build_anomaly_features(frames: list[dict[str, Any]]) -> np.ndarray:
    """Match the D-ANOM-04 feature subset used at Phase 2 anomaly training.

    Flattens nested ping_continuity into the four sub-fields the model was
    trained on. Missing values are zero-filled (matches Phase 2 D-NaN policy
    for anomaly EVAL: zero-fill to preserve the window-major layout from
    Pitfall 11).
    """
    flat: list[dict[str, Any]] = []
    for f in frames:
        row = dict(f)
        pc = row.pop("ping_continuity", None) or {}
        row["ping_continuity_avg_rtt_ms"] = pc.get("avg_rtt_ms") or 0.0
        row["ping_continuity_packet_loss_pct"] = pc.get("packet_loss_pct") or 0.0
        row["ping_continuity_jitter_ms"] = pc.get("jitter_ms") or 0.0
        flat.append(row)
    df = pd.DataFrame(flat).fillna(0.0)
    cols = [c for c in _ANOMALY_FEATURE_COLS if c in df.columns]
    return df[cols].fillna(0.0).to_numpy(dtype=np.float64)


def predict(frames: list[dict[str, Any]]) -> tuple[Verdict, np.ndarray]:
    """Run Phase 2 classifier + anomaly detector on a window of telemetry.

    Returns:
        verdict: Schema-valid Verdict with top_k=10 (D-CAL-08), masked +
            renormalized for the window's network_mode (D-CAL-09).
            ``headline`` / ``suggested_fix`` are still Phase 2 stubs;
            Phase 3 narrator (plans 03-04 / 03-05) replaces them.
        scores: Per-frame anomaly scores. Sign convention follows Phase 2
            train_anomaly.py: ``detector.decision_function(X)`` -- higher
            output means MORE anomalous (D-ANOM-02). The timeline red-band
            overlay threshold is ``_ANOMALY_THRESHOLD`` (95th percentile of
            normal-split decision_function output).
    """
    verdict = _predict_verdict(str(_ARTIFACTS / "classifier.joblib"), frames)
    x_anom = _build_anomaly_features(frames)
    # PyOD 2.x IForest uses `decision_function` (NOT sklearn's `score_samples`);
    # higher = more anomalous, matching the Phase 2 D-ANOM-02 threshold convention.
    scores = _ANOMALY_DETECTOR.decision_function(x_anom)
    return verdict, scores
