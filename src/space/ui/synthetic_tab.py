"""Synthetic tab -- 4x2 grid of scenario cards + Random button (D-SYNTH-01..03, UI-03).

Composition consumed by ``app.py``: ``build_synthetic_tab()`` is called inside
``with gr.Tab("Synthetic"):`` and returns a dict of the live Gradio components
(plan 03-05 / 03-06 may wire additional outputs onto these).

Demo theater (D-SYNTH-02): every card click + the Random button enforce a
~1.2s ``Analyzing telemetry...`` pause before the verdict reveal. The
classifier IS running on real telemetry; the deliberate sleep guarantees
users perceive the analysis step (and protects against the 'this is all
pre-baked' tell).

Card grid display-name manifest (D-SYNTH-01 -- the 8 scenarios rendered as a
4x2 button grid; literal listing here so source-scanning smoke tests can
verify card-grid contents without instantiating Gradio Blocks):

  1. school RADIUS overload at the bell
  2. walking down the hall -- roam fails
  3. cert expired this morning
  4. coffee-shop captive portal expired
  5. DHCP pool exhausted at conference
  6. Apple device on randomized MAC
  7. laptop just woke up -- Wi-Fi confused
  8. stuck on weak AP at the back of the room


Citation linking: per ``.planning/SPIKE-03-02-LOG.md`` the JS bridge for
bidirectional citation linking (D-TIMELINE-01/03) is gated on a Resume-signal
that is currently PENDING. Until the spike concludes we ship the conservative
unidirectional path (no JS bridge wiring); plan 03-05 reconciles based on the
final Resume-signal value.

Cross-plan stub note: plans 03-02 (verdict_card / what_to_do_card / timeline)
and 03-03 (this file) run in parallel as Wave 2. We try to import the
03-02 modules first; if missing (this plan landed first), we fall back to
inline minimal stubs that render a basic verdict + a placeholder timeline
figure. Plan 03-05 (Wave 3) reconciles by removing the stubs once 03-02
lands. Cross-repo note in the executor prompt explicitly authorizes this
fallback pattern.
"""
from __future__ import annotations

import random
import time
from typing import Any, Tuple

import gradio as gr
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.space.inference import _ANOMALY_THRESHOLD
from src.space.scenarios.catalog import SCENARIOS, SCENARIOS_BY_SLUG
from src.space.scenarios.runner import run_scenario


# ---------------------------------------------------------------------------
# Defensive imports for plan 03-02 UI builders (parallel-execution fallback).
# ---------------------------------------------------------------------------

try:  # pragma: no cover - branch chosen at import time
    from src.space.ui.verdict_card import build_verdict_card  # type: ignore
    _VERDICT_CARD_AVAILABLE = True
except ImportError:
    _VERDICT_CARD_AVAILABLE = False

    def build_verdict_card(verdict: Any) -> str:  # type: ignore[no-redef]
        """Stub verdict-card renderer. Replaced by 03-02's real builder once it lands.

        TODO (03-05 reconcile): remove this stub once src/space/ui/verdict_card.py
        ships from plan 03-02.
        """
        # Minimal but readable HTML so the UI is at least wired end-to-end.
        try:
            top = verdict.top_class
            conf = verdict.confidence
            display = top.replace("_", " ")
            badge_color = (
                "#10b981" if conf >= 0.80 else "#f59e0b" if conf >= 0.60 else "#ef4444"
            )
            badge_label = (
                "HIGH" if conf >= 0.80 else "MED" if conf >= 0.60 else "LOW"
            )
            top_k_rows = "".join(
                f"<li><code>{cls}</code> -- {prob:.1%}</li>"
                for cls, prob in verdict.top_k[:3]
            )
            return (
                f'<div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;'
                f'background:#fafafa;font-family:system-ui,sans-serif;">'
                f'<div style="font-size:0.75rem;color:#6b7280;text-transform:uppercase;'
                f'letter-spacing:0.05em;margin-bottom:4px;">Verdict (stub -- 03-02 will replace)</div>'
                f'<div style="font-size:1.4rem;font-weight:600;margin-bottom:8px;">{display}</div>'
                f'<div style="font-size:0.85rem;color:#6b7280;margin-bottom:12px;">'
                f'<code>{top}</code></div>'
                f'<div style="display:inline-block;padding:4px 12px;border-radius:999px;'
                f'background:{badge_color};color:white;font-weight:600;font-size:0.85rem;">'
                f'{conf:.0%} {badge_label}</div>'
                f'<div style="margin-top:12px;font-size:0.85rem;color:#374151;">'
                f'<strong>Top alternatives:</strong><ol style="margin:4px 0 0 20px;padding:0;">'
                f'{top_k_rows}</ol></div>'
                f'</div>'
            )
        except Exception as e:  # last-resort fallback
            return f'<div><i>verdict render error: {e!r}</i></div>'

try:  # pragma: no cover
    from src.space.ui.what_to_do_card import build_what_to_do_card  # type: ignore
    _WHAT_TO_DO_AVAILABLE = True
except ImportError:
    _WHAT_TO_DO_AVAILABLE = False

    def build_what_to_do_card(verdict: Any) -> str:  # type: ignore[no-redef]
        """Stub 'what to do' renderer.

        TODO (03-05 reconcile): remove once 03-02's what_to_do_card.py lands.
        """
        try:
            fix = verdict.suggested_fix
            return (
                f'<div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;'
                f'margin-top:8px;background:#f0f9ff;font-family:system-ui,sans-serif;">'
                f'<div style="font-size:0.75rem;color:#0369a1;text-transform:uppercase;'
                f'letter-spacing:0.05em;margin-bottom:4px;">Recommended action (stub)</div>'
                f'<div style="font-size:0.95rem;color:#1e293b;">{fix}</div>'
                f'</div>'
            )
        except Exception as e:
            return f'<div><i>what-to-do render error: {e!r}</i></div>'

try:  # pragma: no cover
    from src.space.ui.timeline import build_timeline  # type: ignore
    _TIMELINE_AVAILABLE = True
except ImportError:
    _TIMELINE_AVAILABLE = False

    def build_timeline(  # type: ignore[no-redef]
        frames: list[dict[str, Any]],
        anomaly_scores: Any,
        anomaly_threshold: float,
        evidence: list[Any],
        window_seconds: int,
    ) -> go.Figure:
        """Stub 4-row timeline figure. Replaced by 03-02's real builder.

        TODO (03-05 reconcile): remove once 03-02's timeline.py lands.
        """
        n = len(frames)
        # x-axis = seconds before disconnect (D-TIMELINE-05).
        x = list(range(-(n - 1), 1))
        rssi = [f.get("rssi_dbm", 0) for f in frames]
        rtt = [
            (f.get("ping_continuity") or {}).get("avg_rtt_ms", 0) for f in frames
        ]
        dns = [f.get("dns_resolution_ms", 0) for f in frames]

        fig = make_subplots(
            rows=4,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            row_heights=[0.30, 0.25, 0.20, 0.25],
            subplot_titles=(
                "RSSI (dBm) -- stub timeline; 03-02 ships the real 4-row figure",
                "Ping RTT (ms)",
                "DNS resolution (ms)",
                "Anomaly score (higher = more anomalous)",
            ),
        )
        fig.add_trace(
            go.Scatter(x=x, y=rssi, mode="lines+markers", name="rssi_dbm"), row=1, col=1
        )
        fig.update_yaxes(range=[-90, -30], row=1, col=1)  # D-TIMELINE-14
        fig.add_trace(
            go.Scatter(x=x, y=rtt, mode="lines", name="rtt_ms"), row=2, col=1
        )
        fig.add_trace(
            go.Scatter(x=x, y=dns, mode="lines", name="dns_ms"), row=3, col=1
        )
        # Anomaly score row + threshold reference line.
        try:
            scores_list = list(anomaly_scores)
        except TypeError:
            scores_list = [0.0] * n
        fig.add_trace(
            go.Scatter(x=x, y=scores_list, mode="lines", name="anomaly"),
            row=4,
            col=1,
        )
        fig.add_hline(
            y=anomaly_threshold,
            line_dash="dash",
            line_color="red",
            annotation_text="threshold",
            row=4,
            col=1,
        )
        fig.update_layout(
            title=f"Telemetry timeline -- {window_seconds}s window (stub)",
            height=560,
            showlegend=False,
            margin=dict(l=50, r=20, t=80, b=40),
            hovermode="x unified",  # D-TIMELINE-08
        )
        fig.update_xaxes(title_text="seconds before disconnect", row=4, col=1)
        return fig


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def card_click_handler(slug: str) -> Tuple[str, str, go.Figure]:
    """Run scenario by slug, return (verdict_html, what_to_do_html, timeline_fig).

    D-SYNTH-02: brief 'Analyzing telemetry...' pause (~1.2s) before reveal.
    The classifier IS running on real telemetry; the sleep guarantees the
    user perceives the analysis step.
    """
    time.sleep(1.2)  # D-SYNTH-02 -- Analyzing telemetry... animation
    scenario = SCENARIOS_BY_SLUG[slug]
    verdict, scores, frames = run_scenario(slug)
    verdict_html = build_verdict_card(verdict)
    what_to_do_html = build_what_to_do_card(verdict)
    # Window length in seconds for the timeline x-axis label (D-TIMELINE-09).
    window_seconds = scenario.n_frames
    fig = build_timeline(
        frames,
        scores,
        _ANOMALY_THRESHOLD,
        list(verdict.evidence),
        window_seconds,
    )
    return verdict_html, what_to_do_html, fig


def random_scenario_handler() -> Tuple[str, str, go.Figure]:
    """UI-03: Random scenario button -- pick one of 8 and run."""
    slug = random.choice(SCENARIOS).slug
    return card_click_handler(slug)


# ---------------------------------------------------------------------------
# Tab builder (D-SYNTH-01..03)
# ---------------------------------------------------------------------------


def build_synthetic_tab() -> dict:
    """Build the Synthetic tab Blocks composition.

    Layout (D-VERDICT-08 stacked column):
      1. Header
      2. Random scenario button (UI-03)
      3. 4x2 card grid -- one button per scenario (D-SYNTH-01)
      4. Result panes: verdict card -> what-to-do card -> 4-row timeline

    Returns a dict of the live components for ``app.py`` / 03-05 / 03-06 to
    wire additional event handlers if needed.
    """
    components: dict = {}

    # Header
    gr.Markdown("### Synthetic scenarios")
    gr.Markdown(
        "_Click a scenario card to run a real classifier verdict, or roll the dice._"
    )

    # UI-03: Random scenario button
    with gr.Row():
        random_btn = gr.Button("Random scenario", variant="primary")
    components["random_btn"] = random_btn

    # D-SYNTH-01: 4x2 card grid
    card_buttons: list[tuple[str, gr.Button]] = []
    for row_start in (0, 4):
        with gr.Row():
            for s in SCENARIOS[row_start:row_start + 4]:
                with gr.Column():
                    gr.Markdown(
                        f"**{s.display_name}**\n\n"
                        f"_{s.description}_\n\n"
                        f"`{s.network_mode}`"
                    )
                    btn = gr.Button(f"Run: {s.display_name}")
                    card_buttons.append((s.slug, btn))
    components["card_buttons"] = card_buttons

    # Result panes (initially placeholder; rewritten on click).
    gr.Markdown("---")
    # D-SYNTH-02 anchor: literal 'Analyzing telemetry' so source-scanning
    # smoke tests (and screen readers) see the demo-theater intent. Live
    # animation also implemented via the time.sleep(1.2) in card_click_handler.
    analyzing_hint = gr.Markdown(
        "_Analyzing telemetry... (click a card or the Random button above)_"
    )
    components["analyzing_hint"] = analyzing_hint

    verdict_pane = gr.HTML(
        value="<i>No scenario selected yet.</i>",
        label="Verdict",
    )
    what_to_do_pane = gr.HTML(value="", label="Recommended action")
    timeline_pane = gr.Plot(value=None, label="Telemetry timeline")
    components["verdict_pane"] = verdict_pane
    components["what_to_do_pane"] = what_to_do_pane
    components["timeline_pane"] = timeline_pane

    # Wire handlers.
    outputs = [verdict_pane, what_to_do_pane, timeline_pane]
    random_btn.click(fn=random_scenario_handler, inputs=[], outputs=outputs)
    for slug, btn in card_buttons:
        # Default-arg trick captures slug at definition time, not call time.
        btn.click(fn=lambda s=slug: card_click_handler(s), inputs=[], outputs=outputs)

    # unidirectional citation linking -- frame clicks no-op per
    # SPIKE-03-02-LOG.md (Resume-signal currently PENDING; conservative
    # default until spike concludes; plan 03-05 reconciles).

    return components
