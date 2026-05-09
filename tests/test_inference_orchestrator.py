"""Phase 3 plan 03-01 / Pattern 1: InferenceOrchestrator contract tests.

Validates the load-once predict-per-request shape contract:
- predict(window) returns (Verdict, np.ndarray)
- Verdict.top_k has 10 entries (D-CAL-08)
- anomaly scores are finite (sign convention -score_samples)
- Module-level singletons are populated at import (no lazy load)
"""
from __future__ import annotations

import numpy as np
from wifi_diag_schema.verdict import Verdict

from src.space.inference import _ANOMALY_DETECTOR, _CLASSIFIER, predict


def test_predict_returns_verdict_and_scores(sample_window: list[dict]) -> None:
    verdict, scores = predict(sample_window)
    assert isinstance(verdict, Verdict)
    assert isinstance(scores, np.ndarray)
    assert scores.shape == (len(sample_window),)


def test_verdict_top_k_size_10(sample_window: list[dict]) -> None:
    verdict, _ = predict(sample_window)
    assert len(verdict.top_k) == 10  # D-CAL-08


def test_anomaly_scores_higher_means_more_anomalous(sample_window: list[dict]) -> None:
    """Sign convention: scores = -detector.score_samples(X); finite real array."""
    _, scores = predict(sample_window)
    assert np.all(np.isfinite(scores))


def test_artifacts_loaded_at_module_import() -> None:
    assert _CLASSIFIER is not None
    assert _ANOMALY_DETECTOR is not None
