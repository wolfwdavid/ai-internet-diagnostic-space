"""Phase 3 plan 03-02 Task 3: 4-row Plotly timeline tests.

Per ``.planning/SPIKE-03-02-LOG.md`` Resume-signal ``unidirectional + fillpattern``:

- Anomaly band ships as a Bar overlay with ``marker.pattern.shape='/'``
  diagonal stripes (D-TIMELINE-11 a11y treatment validated by the spike).
- Citation linking is unidirectional in v1 -- frame clicks are no-op.
  Bidirectional add-back is tracked in ``.planning/BACKLOG.md`` as v1.x.

The tests below exercise figure structure (4 rows, shared x-axis, fixed RSSI
y-range, unified hover), the anomaly-band fillpattern Bar overlay, the
lead-time annotation arrow, and the window-length title label.
"""

from __future__ import annotations

import numpy as np

from src.space.ui.timeline import build_timeline


def _mk_input(sample_window):
    """Helper: produce ``(frames, scores, threshold, evidence, window_seconds)``."""
    scores = np.random.RandomState(42).uniform(0.0, 0.3, len(sample_window))
    # Force the last 10 frames to exceed the threshold (anomalous).
    scores[20:] = 0.95
    evidence: list = []
    return sample_window, scores, 0.5, evidence, 30


def test_subplot_4_rows(sample_window):
    """D-TIMELINE-04: 4 stacked subplot panels (RSSI / Ping / DNS / Events)."""
    fig = build_timeline(*_mk_input(sample_window))
    yaxes = [k for k in fig.layout if str(k).startswith("yaxis")]
    assert len(yaxes) >= 4, f"expected >=4 y-axes, got {yaxes}"


def test_x_axis_zero_at_disconnect(sample_window):
    """D-TIMELINE-05: x-axis 0 = disconnect; pre-disconnect frames are negative."""
    fig = build_timeline(*_mk_input(sample_window))
    max_x = max(
        (max(t.x) if hasattr(t, "x") and t.x is not None and len(t.x) else -1e9 for t in fig.data),
        default=-1e9,
    )
    assert abs(max_x) < 1.0, f"disconnect should be at x~=0, got max_x={max_x}"


def test_rssi_y_axis_fixed_range(sample_window):
    """D-TIMELINE-14: row 1 RSSI y-axis fixed to [-90, -30] dBm."""
    fig = build_timeline(*_mk_input(sample_window))
    yaxis = fig.layout.yaxis
    assert tuple(yaxis.range) == (-90, -30)


def test_anomaly_band_renders(sample_window):
    """D-TIMELINE-02: anomalous run produces at least one shape OR Bar trace."""
    fig = build_timeline(*_mk_input(sample_window))
    assert len(fig.layout.shapes) > 0 or any(t.type == "bar" for t in fig.data)


def test_anomaly_band_has_fillpattern(sample_window):
    """D-TIMELINE-11 + Pitfall B (PASS): fillpattern Bar overlay present.

    Per spike Resume-signal ``unidirectional + fillpattern`` the production
    timeline ships the diagonal-stripe Bar overlay. This test asserts at
    least one ``go.Bar`` trace exists with ``marker.pattern.shape == '/'``.
    """
    fig = build_timeline(*_mk_input(sample_window))
    bars_with_pattern = [
        t
        for t in fig.data
        if t.type == "bar"
        and getattr(t.marker, "pattern", None) is not None
        and t.marker.pattern.shape == "/"
    ]
    assert len(bars_with_pattern) > 0, "Pitfall B fillpattern Bar overlay missing"


def test_lead_time_annotation(sample_window):
    """D-TIMELINE-06: lead-time arrow + label drawn from first red-band frame."""
    fig = build_timeline(*_mk_input(sample_window))
    assert any("lead-time:" in (a.text or "") for a in fig.layout.annotations), (
        "expected an annotation containing 'lead-time:'"
    )


def test_hovermode_unified(sample_window):
    """D-TIMELINE-08: unified cross-panel hover popup."""
    fig = build_timeline(*_mk_input(sample_window))
    assert fig.layout.hovermode == "x unified"


def test_window_length_label(sample_window):
    """D-TIMELINE-09: window-length label in figure title (30s vs 120s)."""
    fig = build_timeline(*_mk_input(sample_window))
    title = fig.layout.title.text or ""
    assert "30s window" in title or "120s window" in title
