"""Plan 03-02 SPIKE: validate two MEDIUM-LOW Plotly capabilities on HF Space.

Two experiments wrapped in a self-contained ``gr.Blocks`` demo that can be
pushed to a temporary HF Space (or PR-preview Space) on the
``spike/plotly-clicks`` branch and visually verified.

Spike scope (per 03-RESEARCH.md Pitfalls A and B + Patterns 5 and 6):

- **Experiment A -- ``Plotly_click`` JS bridge** (mitigates Pitfall A on
  D-TIMELINE-01/03/16). A 1-trace ``go.Scatter`` with 10 points hosted in
  ``gr.Plot()``. The ``js=`` argument on a ``gr.Plot.change()`` listener
  attaches a ``Plotly.on('plotly_click')`` handler that updates a hidden
  ``gr.Textbox`` with ``(curveNumber, pointIndex)`` JSON. A visible
  ``gr.Markdown`` echoes the clicked-point info via a Python ``.change()``
  callback on the hidden textbox.

- **Experiment B -- Anomaly band Bar overlay with fillpattern** (mitigates
  Pitfall B on D-TIMELINE-11). A 2-row subplot where row 1 is a Scatter of
  RSSI and row 2 is a Bar trace of width=10 with
  ``marker=dict(pattern=dict(shape="/"))``. Verify the diagonal-stripe
  pattern actually renders (not flat color) on the deployed Space.

Outcome dictates whether plan 03-02 ships bidirectional citation linking
(D-TIMELINE-01/03) or downgrades to unidirectional with a v1.x add-back, and
whether the anomaly band uses the Bar-overlay fillpattern or falls back to
plain rect + a11y text annotation.

Resume-signal recorded in ``.planning/SPIKE-03-02-LOG.md``.

This module is a SPIKE artifact: it stays in the codebase as a reference for
the chosen implementation but is NOT imported from ``app.py``. Plan 03-02
Task 3 wires the production timeline based on the spike outcome.
"""
from __future__ import annotations

import json

import gradio as gr
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# === EXPERIMENT A: Plotly_click JS bridge =================================

# JavaScript bridge: Plotly_click -> hidden gr.Textbox -> Python callback.
# Per 03-RESEARCH.md Pattern 5. The setTimeout(...100ms) gives the Plotly
# graph DOM time to mount before we attach the click listener; on slower
# free-CPU Spaces this may need bumping to 500ms (Pitfall A "Warning signs").
_PLOTLY_CLICK_JS = """
(plot_data) => {
    setTimeout(() => {
        const plot_div = document.querySelector('.gradio-plot div.plotly-graph-div');
        if (plot_div && !plot_div._click_attached) {
            plot_div.on('plotly_click', (data) => {
                const pt = data.points[0];
                const payload = JSON.stringify({
                    curve: pt.curveNumber, point: pt.pointIndex, x: pt.x, y: pt.y
                });
                const textbox = document.querySelector('input[data-testid="frame-click-state"]');
                if (textbox) {
                    textbox.value = payload;
                    textbox.dispatchEvent(new Event('input', { bubbles: true }));
                }
            });
            plot_div._click_attached = true;
        }
    }, 100);
    return plot_data;
};
"""


def _build_experiment_a_figure() -> go.Figure:
    """Single-trace Scatter with 10 clickable points."""
    x = list(range(10))
    y = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers+lines",
            marker=dict(size=18, color="steelblue"),
            name="experiment-a",
        )
    )
    fig.update_layout(
        title="Experiment A: click any point and verify the Markdown below updates",
        height=320,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def _format_click_payload(payload: str) -> str:
    """Render the click payload as Markdown in the visible echo."""
    if not payload:
        return "_Click any point on the scatter above. The clicked-point info will appear here._"
    try:
        info = json.loads(payload)
    except json.JSONDecodeError:
        return f"**(unparseable payload)**: `{payload}`"
    return (
        f"**Last click:**\n\n"
        f"- curveNumber: `{info.get('curve')}`\n"
        f"- pointIndex: `{info.get('point')}`\n"
        f"- x: `{info.get('x')}`\n"
        f"- y: `{info.get('y')}`\n\n"
        f"_If this updates on click, the JS bridge works on this deployed Space._"
    )


# === EXPERIMENT B: Anomaly band Bar overlay with fillpattern ==============


def _build_experiment_b_figure() -> go.Figure:
    """2-row subplot: row 1 RSSI, row 2 Bar with diagonal-stripe pattern."""
    rng = np.random.RandomState(42)
    n = 40
    x = list(range(n))
    rssi = (-55 - 5 * np.sin(np.array(x) / 5) + rng.normal(0, 1.5, n)).tolist()

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.10,
        row_heights=[0.65, 0.35],
        subplot_titles=("Row 1: RSSI scatter (control)", "Row 2: Bar with pattern.shape='/'"),
    )

    fig.add_trace(
        go.Scatter(x=x, y=rssi, mode="lines+markers", name="RSSI"),
        row=1,
        col=1,
    )
    fig.update_yaxes(range=[-90, -30], row=1, col=1)

    # The Bar: width=10 spans 10 x-units centered at x=20.
    # If the pattern.shape='/' fillpattern renders as diagonal stripes
    # (not flat red), Pitfall B workaround is validated.
    fig.add_trace(
        go.Bar(
            x=[20],
            y=[1],
            width=[10],
            marker=dict(
                color="rgba(255, 0, 0, 0.25)",
                pattern=dict(
                    shape="/",
                    fgcolor="rgba(255, 0, 0, 0.85)",
                    size=8,
                ),
            ),
            name="anomaly-band-overlay",
            showlegend=True,
        ),
        row=2,
        col=1,
    )
    fig.update_yaxes(range=[0, 1], row=2, col=1, showticklabels=False)

    fig.update_layout(
        title="Experiment B: row 2 Bar should show diagonal stripes, not flat color",
        height=420,
        margin=dict(l=40, r=20, t=70, b=40),
        showlegend=True,
    )
    return fig


# === DEMO BLOCKS ==========================================================


def build_spike_demo() -> gr.Blocks:
    """Self-contained spike demo for HF Space deployment."""
    with gr.Blocks(title="Plan 03-02 spike: Plotly clicks + fillpattern") as demo:
        gr.Markdown(
            "# Plan 03-02 spike: Plotly point-click JS bridge + fillpattern Bar overlay\n\n"
            "Two experiments validate the two MEDIUM-LOW-confidence Plotly capabilities "
            "flagged in `03-RESEARCH.md` (Pitfalls A and B). **The outcome dictates whether "
            "plan 03-02 ships bidirectional citation linking and the Bar-overlay fillpattern.**"
        )

        # Experiment A.
        gr.Markdown("---\n## Experiment A: `Plotly_click` JS bridge")
        gr.Markdown(
            "Click any point on the scatter below. If the Markdown echo updates with "
            "`(curveNumber, pointIndex)` for at least 8/10 points, the JS bridge works "
            "and bidirectional linking (D-TIMELINE-01/03) is feasible on a deployed Space."
        )
        plot_a = gr.Plot(value=_build_experiment_a_figure(), label="Experiment A scatter")
        # Hidden textbox that the JS bridge writes into; .change() fires the
        # Python callback. ``elem_id`` selector hook is the data-testid in the
        # JS query selector (Gradio 6.x sets data-testid from elem_id).
        click_state = gr.Textbox(
            value="",
            visible=False,
            elem_id="frame-click-state",
        )
        click_echo = gr.Markdown(_format_click_payload(""))

        # Wire the JS bridge: when plot_a renders/changes, run the JS to
        # attach the click listener. The Python identity fn (lambda x: x) is
        # the no-op required by Gradio to allow `js=...`.
        plot_a.change(
            fn=lambda x: x,
            inputs=plot_a,
            outputs=plot_a,
            js=_PLOTLY_CLICK_JS,
        )
        click_state.change(
            fn=_format_click_payload,
            inputs=click_state,
            outputs=click_echo,
        )

        # Experiment B.
        gr.Markdown("---\n## Experiment B: anomaly band Bar overlay with fillpattern")
        gr.Markdown(
            "Inspect row 2 below. **PASS** if the red region shows diagonal stripes "
            "(`pattern.shape='/'` renders correctly). **FAIL** if it shows flat red "
            "(fillpattern silently ignored). Cross-check via browser DevTools: "
            "look for a `<pattern>` element in the rendered SVG."
        )
        gr.Plot(value=_build_experiment_b_figure(), label="Experiment B subplot")

        gr.Markdown(
            "---\n"
            "## Recording results\n"
            "Update `.planning/SPIKE-03-02-LOG.md` with PASS/FAIL for each experiment "
            "and one of the four `Resume-signal:` lines listed in plan 03-02."
        )
    return demo


if __name__ == "__main__":
    build_spike_demo().launch()
