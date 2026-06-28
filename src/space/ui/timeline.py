"""4-row stacked Plotly timeline with anomaly band overlay (D-TIMELINE-04..15).

Per .planning/SPIKE-03-02-LOG.md Resume-signal ``unidirectional + fillpattern``
(spike outcome 2026-05-09):

- Anomaly band uses ``go.Bar`` with ``marker.pattern.shape='/'`` diagonal
  stripes (Pitfall B PASS; D-TIMELINE-11 a11y intent ships as written).
- Citation linking is unidirectional in v1 -- frame clicks are no-op.
  Bidirectional add-back tracked in ``.planning/BACKLOG.md`` as v1.x.

# v1: unidirectional citation linking -- frame clicks are no-op.
# Spike SPIKE-03-02-LOG.md found Plotly_click JS bridge unreliable on
# deployed HF Space. Evidence-item click -> frame pulse still works
# (gr.HTML onClick -> gr.State update). Bidirectional add-back tracked
# in v1.x roadmap (.planning/BACKLOG.md).

Layout:
  Row 1 (30%) -- RSSI dBm + beacon RSSI dBm; y-range fixed [-90, -30]
                 (D-TIMELINE-14)
  Row 2 (30%) -- Ping RTT / jitter / packet loss
  Row 3 (20%) -- DNS resolution ms
  Row 4 (20%) -- Event-class markers (auth=blue, dhcp=orange, dns=green,
                 captive=purple per D-TIMELINE-07)

X-axis (D-TIMELINE-05): seconds before disconnect; disconnect at right edge.
Hover (D-TIMELINE-08): ``hovermode='x unified'`` cross-panel popup.
Theme (D-TIMELINE-15): default ``plotly`` (light grid, blue palette).
Title (D-TIMELINE-09): includes window-length label (``30s window`` /
                       ``120s window``).
Anomaly band (D-TIMELINE-02 + D-TIMELINE-11): contiguous runs where
  scores > threshold get a translucent red ``add_shape`` rect plus a
  diagonal-stripe ``go.Bar`` overlay on row 1 (a11y treatment).
Lead-time arrow (D-TIMELINE-06): ``add_annotation`` from the first
  red-band frame to the disconnect with ``lead-time: Xs`` label.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Event-class -> color (D-TIMELINE-07).
_EVENT_COLORS: dict[str, str] = {
    "auth": "#3b82f6",  # blue
    "dhcp": "#f59e0b",  # orange
    "dns": "#10b981",  # green
    "captive": "#8b5cf6",  # purple
}


def _find_runs(mask: Sequence[bool]) -> list[tuple[int, int]]:
    """Find contiguous True runs in ``mask``.

    Returns a list of ``(start_idx, end_idx)`` tuples (end_idx is INCLUSIVE).
    """
    runs: list[tuple[int, int]] = []
    n = len(mask)
    i = 0
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            runs.append((i, j))
            i = j + 1
        else:
            i += 1
    return runs


def _x_axis(timestamps: Sequence[float]) -> list[float]:
    """D-TIMELINE-05: x = ``timestamps - timestamps[-1]`` (negative pre-disconnect)."""
    if not len(timestamps):
        return []
    last = timestamps[-1]
    return [float(t) - float(last) for t in timestamps]


def _safe_get(frame: dict[str, Any], path: str, default: Any = None) -> Any:
    """Resolve a dotted path against a frame dict; return ``default`` if missing."""
    cur: Any = frame
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return default
        if cur is None:
            return default
    return cur if cur is not None else default


def build_timeline(
    frames: list[dict[str, Any]],
    anomaly_scores: Iterable[float],
    anomaly_threshold: float,
    evidence: list[Any],
    window_seconds: int,
) -> go.Figure:
    """Build the 4-row drill-down timeline figure.

    Parameters
    ----------
    frames
        List of TelemetryFrame-shaped dicts (length N == window length in
        samples).
    anomaly_scores
        Per-frame anomaly scores from ``InferenceOrchestrator.predict`` (
        higher = more anomalous per D-ANOM-02).
    anomaly_threshold
        95p-of-normal threshold (``_ANOMALY_THRESHOLD`` from
        ``src.space.inference``).
    evidence
        Narrator evidence list (currently unused in unidirectional v1; the
        signature is preserved for the v1.x bidirectional add-back).
    window_seconds
        Window length in seconds for the title label (D-TIMELINE-09).

    Returns
    -------
    plotly.graph_objects.Figure
        4-row stacked subplot with shared x-axis, anomaly band overlay,
        lead-time arrow, and event markers.
    """
    n = len(frames)
    timestamps: list[float] = [float(f.get("timestamp", i)) for i, f in enumerate(frames)]
    x = _x_axis(timestamps)

    rssi = [_safe_get(f, "rssi_dbm", 0.0) for f in frames]
    beacon_rssi = [_safe_get(f, "beacon_rssi_dbm", 0.0) for f in frames]
    rtt = [_safe_get(f, "ping_continuity.avg_rtt_ms", 0.0) for f in frames]
    jitter = [_safe_get(f, "ping_continuity.jitter_ms", 0.0) for f in frames]
    loss = [_safe_get(f, "ping_continuity.packet_loss_pct", 0.0) for f in frames]
    dns = [_safe_get(f, "dns_resolution_ms", 0.0) for f in frames]

    # D-TIMELINE-04: 4 stacked subplot panels (RSSI / Ping / DNS / Events).
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.30, 0.30, 0.20, 0.20],
        subplot_titles=(
            "RSSI (dBm)",
            "Ping (RTT / jitter / loss)",
            "DNS resolution (ms)",
            "Events",
        ),
    )

    # -- Row 1: RSSI + beacon RSSI; fixed y-range [-90, -30] (D-TIMELINE-14).
    fig.add_trace(
        go.Scatter(
            x=x,
            y=rssi,
            mode="lines+markers",
            name="rssi_dbm",
            line=dict(color="#1f77b4"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=beacon_rssi,
            mode="lines",
            name="beacon_rssi_dbm",
            line=dict(color="#1f77b4", dash="dot"),
        ),
        row=1,
        col=1,
    )
    fig.update_yaxes(range=[-90, -30], row=1, col=1)  # D-TIMELINE-14

    # -- Row 2: Ping RTT / jitter / packet loss.
    fig.add_trace(
        go.Scatter(x=x, y=rtt, mode="lines", name="rtt_ms", line=dict(color="#ff7f0e")),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=x, y=jitter, mode="lines", name="jitter_ms", line=dict(color="#ffbb78", dash="dash")
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=loss,
            mode="lines",
            name="loss_pct",
            line=dict(color="#d62728", dash="dot"),
            yaxis="y2",
        ),
        row=2,
        col=1,
    )

    # -- Row 3: DNS resolution.
    fig.add_trace(
        go.Scatter(x=x, y=dns, mode="lines", name="dns_ms", line=dict(color="#2ca02c")),
        row=3,
        col=1,
    )

    # -- Row 4: event markers (D-TIMELINE-07).
    # Render an invisible scatter so row 4 has y-range; vertical lines are
    # drawn via add_vline (visible) per event class.
    fig.add_trace(
        go.Scatter(
            x=x,
            y=[0.0] * n,
            mode="lines",
            line=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
            name="events_baseline",
        ),
        row=4,
        col=1,
    )
    for i, frame in enumerate(frames):
        auth = _safe_get(frame, "auth_event_class", "none")
        dhcp = _safe_get(frame, "dhcp_event_class", "none")
        captive = bool(_safe_get(frame, "captive_portal_detected", False))
        dns_class = (
            "fail" if ((_safe_get(frame, "dns_resolution_ms", 0.0) or 0.0) > 200.0) else "none"
        )
        # auth (blue)
        if auth and auth != "none":
            fig.add_vline(
                x=x[i],
                line=dict(color=_EVENT_COLORS["auth"], width=2),
                row=4,
                col=1,
                annotation_text=str(auth),
                annotation_position="top",
                annotation_font=dict(color=_EVENT_COLORS["auth"], size=10),
            )
        # dhcp (orange)
        if dhcp and dhcp != "none":
            fig.add_vline(
                x=x[i],
                line=dict(color=_EVENT_COLORS["dhcp"], width=2),
                row=4,
                col=1,
                annotation_text=str(dhcp),
                annotation_position="top",
                annotation_font=dict(color=_EVENT_COLORS["dhcp"], size=10),
            )
        # dns (green)
        if dns_class == "fail":
            fig.add_vline(
                x=x[i],
                line=dict(color=_EVENT_COLORS["dns"], width=2),
                row=4,
                col=1,
                annotation_text="dns_fail",
                annotation_position="top",
                annotation_font=dict(color=_EVENT_COLORS["dns"], size=10),
            )
        # captive (purple)
        if captive:
            fig.add_vline(
                x=x[i],
                line=dict(color=_EVENT_COLORS["captive"], width=2),
                row=4,
                col=1,
                annotation_text="captive",
                annotation_position="top",
                annotation_font=dict(color=_EVENT_COLORS["captive"], size=10),
            )

    # -- Anomaly band (D-TIMELINE-02 + D-TIMELINE-11 fillpattern).
    scores_arr = np.asarray(list(anomaly_scores), dtype=float)
    if scores_arr.shape[0] != n:
        # Defensive: if the score series is the wrong length, zero-pad/truncate
        # so the plotting doesn't index out of bounds.
        if scores_arr.shape[0] > n:
            scores_arr = scores_arr[:n]
        else:
            scores_arr = np.concatenate([scores_arr, np.zeros(n - scores_arr.shape[0])])
    mask = (scores_arr > anomaly_threshold).tolist()
    runs = _find_runs(mask)

    first_anom_x: float | None = None
    for start, end in runs:
        x0 = x[start]
        x1 = x[end]
        # Translucent red rect spanning the full figure (paper y-coords).
        fig.add_shape(
            type="rect",
            x0=x0,
            x1=x1,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            fillcolor="rgba(255, 0, 0, 0.15)",
            line_width=0,
            layer="below",
        )
        # Diagonal-stripe Bar overlay on row 1 for color-blind a11y
        # (D-TIMELINE-11; Pitfall B PASS per spike).
        center = (x0 + x1) / 2.0
        width = max(x1 - x0, 1.0)
        fig.add_trace(
            go.Bar(
                x=[center],
                y=[1.0],
                width=[width],
                marker=dict(
                    color="rgba(0, 0, 0, 0)",
                    # D-TIMELINE-11 (Pitfall B PASS): diagonal-stripe a11y overlay.
                    pattern=dict(shape="/", fgcolor="rgba(255, 0, 0, 0.4)", size=8),
                ),
                name="anomaly band",
                showlegend=(first_anom_x is None),  # only legend the first
                hoverinfo="skip",
                yaxis="y",
            ),
            row=1,
            col=1,
        )
        if first_anom_x is None:
            first_anom_x = x0

    # -- Lead-time arrow (D-TIMELINE-06).
    if first_anom_x is not None:
        # Disconnect is at x ~= 0; lead-time = -first_anom_x seconds.
        # Plotly only accepts ``ayref='pixel'`` or a y-axis ref for arrow tails;
        # ``ayref='paper'`` is rejected. We use a y-axis-anchored arrow on
        # row 1 (yref='y') at the top of the RSSI panel (-32 dBm, just inside
        # the [-90, -30] D-TIMELINE-14 fixed range) -- visually reads as
        # "above the data" without escaping the panel.
        lead_seconds = -float(first_anom_x)
        arrow_y = -32.0
        fig.add_annotation(
            x=0.0,
            y=arrow_y,
            xref="x",
            yref="y",
            ax=first_anom_x,
            ay=arrow_y,
            axref="x",
            ayref="y",
            text=f"lead-time: {lead_seconds:.0f}s",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.2,
            arrowwidth=2,
            arrowcolor="#dc2626",
            font=dict(color="#dc2626", size=11),
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#dc2626",
            borderwidth=1,
            borderpad=3,
        )

    # -- Layout (D-TIMELINE-08 unified hover, D-TIMELINE-15 plotly theme,
    #    D-TIMELINE-09 window-length title label).
    fig.update_layout(
        title=dict(text=f"Telemetry timeline -- {window_seconds}s window"),
        hovermode="x unified",
        template="plotly",
        height=620,
        margin=dict(l=50, r=20, t=80, b=40),
        showlegend=True,
    )
    fig.update_xaxes(title_text="seconds before disconnect", row=4, col=1)

    return fig
