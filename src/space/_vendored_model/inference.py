"""Inference adapter: predict_verdict + mask-then-renormalize (D-MASK-01..04).

Vendored from ai-internet-diagnostic-model v1.0.0 -- DO NOT edit; resync via
`make resync-model` (Phase 5). The only modification from the source is the
relative-import rewrite below (`model.features` -> `.features`).
"""

from __future__ import annotations

from typing import Any

import joblib
import numpy as np
import pandas as pd
from wifi_diag_schema.enums import DisconnectClass, NetworkMode
from wifi_diag_schema.verdict import Verdict

from .features import CATEGORICAL_FEATURES, CLASSES, CLASSIFIER_FEATURES

# D-MASK-02 mask table (frozen at v1; mirrored in MODEL_CARD.md)
MASK_TABLE: dict[NetworkMode, frozenset[DisconnectClass]] = {
    "enterprise": frozenset(
        [
            "auth_8021x_eap_fail",
            "ap_roam_rekey_fail",
            "radius_timeout",
            "mac_randomization_reject",
            "dhcp_lease_churn",
            "dns_resolver_fail",
            "driver_power_save_wake",
            "rf_sticky_client",
        ]
    ),
    "captive": frozenset(
        [
            "captive_portal_expiry",
            "dns_resolver_fail",
            "isp_upstream_fail",
            "dhcp_lease_churn",
            "mac_randomization_reject",
        ]
    ),
    "home": frozenset(
        [
            "dhcp_lease_churn",
            "dns_resolver_fail",
            "driver_power_save_wake",
            "rf_sticky_client",
            "isp_upstream_fail",
        ]
    ),
    "unknown": frozenset(CLASSES),  # D-MASK-03: all 10 enabled
}


def apply_mask_and_renormalize(probs: np.ndarray, network_mode: NetworkMode) -> np.ndarray:
    """D-CAL-09: zero masked classes, renormalize remainder to sum to 1.

    probs: shape (10,) calibrated probabilities, ordered per CLASSES.
    Returns shape (10,); masked entries are 0.0; remainder sums to 1.0.
    """
    applicable = MASK_TABLE[network_mode]
    mask = np.array([slug in applicable for slug in CLASSES], dtype=np.bool_)
    masked = np.where(mask, probs, 0.0)
    total = masked.sum()
    if total <= 0.0:
        # Degenerate fallback (shouldn't happen at v1 — every mode has >=5 enabled).
        return np.full_like(probs, 1.0 / len(CLASSES))
    return masked / total


def _frames_to_array(frames: list[dict[str, Any]]) -> np.ndarray:
    """Convert a list of TelemetryFrame-shaped dicts into the classifier's input matrix.

    Mirrors model.features.load_split logic:
      - flattens nested ping_continuity into the 4 sub-fields if present
      - integer-encodes categoricals via pandas Categorical
      - aligns columns to CLASSIFIER_FEATURES
    """
    flat: list[dict[str, Any]] = []
    for f in frames:
        row = dict(f)
        pc = row.pop("ping_continuity", None)
        if isinstance(pc, dict):
            row["ping_continuity_window_ms"] = pc.get("window_ms")
            row["ping_continuity_avg_rtt_ms"] = pc.get("avg_rtt_ms")
            row["ping_continuity_packet_loss_pct"] = pc.get("packet_loss_pct")
            row["ping_continuity_jitter_ms"] = pc.get("jitter_ms")
        flat.append(row)

    df = pd.DataFrame(flat)
    for col in CATEGORICAL_FEATURES:
        if col not in df.columns:
            df[col] = pd.Series([None] * len(df))
        df[col] = df[col].astype("category").cat.codes
    # Fill missing numeric columns with 0.0 (defensive — schema enforces presence,
    # but partial frames during streaming may omit fields)
    for col in CLASSIFIER_FEATURES:
        if col not in df.columns:
            df[col] = 0.0
    return df[list(CLASSIFIER_FEATURES)].to_numpy(dtype=np.float64)


def predict_verdict(
    classifier_path: str,
    frames: list[dict[str, Any]],
) -> Verdict:
    """Run a window through the classifier and produce a schema-valid Verdict.

    Aggregation: per-frame predict_proba, then average across the window.
    Mask uses the LAST frame's network_mode (most-recent semantics).
    Emits full top_k ranking (D-CAL-08, K=10) post-mask.
    """
    clf = joblib.load(classifier_path)
    X = _frames_to_array(frames)

    proba_per_frame = clf.predict_proba(X)  # (n_frames, 10)
    proba_window = proba_per_frame.mean(axis=0)  # (10,)

    network_mode: NetworkMode = frames[-1]["network_mode"]
    proba_masked = apply_mask_and_renormalize(proba_window, network_mode)

    order = np.argsort(-proba_masked)
    top_k: list[tuple[DisconnectClass, float]] = [
        (CLASSES[i], float(proba_masked[i])) for i in order
    ]
    top_class = top_k[0][0]
    confidence = top_k[0][1]

    return Verdict(
        top_class=top_class,
        confidence=confidence,
        top_k=top_k,
        # Phase 2 produces structurally valid Verdicts; Phase 3 fills these
        # with LLM narrator output. Stub strings keep the schema valid here.
        headline=(f"Pre-Phase-3 stub: classifier predicts {top_class} ({confidence:.0%})"),
        suggested_fix="Pre-Phase-3 stub: see Phase 3 narrator integration.",
        evidence=[],
    )
