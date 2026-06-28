"""Spike-module smoke test: figure builders construct without raising.

The spike's PASS/FAIL status is determined by visual inspection on a
deployed HF Space (Pattern 5 / Pitfall B cannot be verified from a unit
test alone). These tests exist only to keep the spike code from rotting
silently in the repo while the spike is deployed and evaluated.
"""

from __future__ import annotations

import plotly.graph_objects as go

from src.space.ui.spike_plotly import (
    _build_experiment_a_figure,
    _build_experiment_b_figure,
    _format_click_payload,
)


def test_experiment_a_figure_has_one_trace_with_10_points():
    fig = _build_experiment_a_figure()
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert len(fig.data[0].x) == 10
    assert len(fig.data[0].y) == 10


def test_experiment_b_figure_has_bar_with_diagonal_pattern():
    fig = _build_experiment_b_figure()
    assert isinstance(fig, go.Figure)
    bars = [t for t in fig.data if t.type == "bar"]
    assert len(bars) >= 1
    pattern = bars[0].marker.pattern
    assert pattern is not None
    assert pattern.shape == "/"


def test_format_click_payload_handles_empty_and_valid_json():
    # Empty payload renders the placeholder hint.
    placeholder = _format_click_payload("")
    assert "Click any point" in placeholder

    # Valid payload pulls out the curve / point fields.
    rendered = _format_click_payload('{"curve": 0, "point": 3, "x": 3, "y": 1}')
    assert "curveNumber" in rendered
    assert "`0`" in rendered
    assert "pointIndex" in rendered
    assert "`3`" in rendered
