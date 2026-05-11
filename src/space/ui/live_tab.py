"""Phase 5 plan 05-03: Live tab body (UI-07).

Composition: reuses Phase 3's verdict-card / what-to-do-card / timeline
builders by composition rather than re-implementation, satisfying the
ROADMAP success criterion "the Live tab UI === Synthetic tab UI". The
Phase 3 builders are pure functions:

  - ``build_verdict_card(verdict: Verdict) -> str``  (HTML)
  - ``build_what_to_do_card(verdict: Verdict) -> str``  (HTML)
  - ``build_timeline(frames, scores, threshold, evidence, window_s) -> Figure``

The Live tab declares the matching Gradio panes (``gr.HTML`` for the two
HTML cards, ``gr.Plot`` for the timeline) and exposes them via the dict
returned from ``build_live_tab()``. ``app.py`` wires a ``gr.Timer`` whose
tick handler reads ``status.snapshot(session_key)`` and updates these panes
when a verdict arrives.

Layout (per D-STATUS-06):
  - ``verdict_view`` (gr.Column, visible by default)
      verdict-card pane -> what-to-do pane -> timeline pane.
  - ``local_view`` (gr.Column, visible=False by default)
      Activated when the banner state transitions to ``local_fallback``;
      the verdict view hides and the local-mode placeholder shows.

This module does NOT own the banner -- that is page-level (D-STATUS-02 /
D-STATUS-11) and instantiated in ``app.py`` above the ``gr.Tabs()`` block.
"""
from __future__ import annotations

from typing import Any

import gradio as gr

# Phase 3 builders reused by composition (UI-07 ROADMAP criterion).
from src.space.ui.verdict_card import build_verdict_card  # noqa: F401
from src.space.ui.what_to_do_card import build_what_to_do_card  # noqa: F401
from src.space.ui.timeline import build_timeline  # noqa: F401


_AGENT_REPO_URL = "https://github.com/wolfwdavid/ai-internet-diagnostic-agent"


def build_live_tab() -> dict[str, Any]:
    """Build the Live tab Blocks composition.

    Returns a dict of the live Gradio components so ``app.py`` (or future
    plans) can wire timer tick / event handlers onto them without
    re-importing this module.

    Components returned:
      - ``verdict_view``: gr.Column wrapping the verdict-card + what-to-do +
        timeline panes (visible=True by default).
      - ``local_view``: gr.Column wrapping the local-mode placeholder
        (visible=False by default, D-STATUS-06 swap target).
      - ``verdict_pane``: gr.HTML — rendered by ``build_verdict_card``.
      - ``what_to_do_pane``: gr.HTML — rendered by ``build_what_to_do_card``.
      - ``timeline_pane``: gr.Plot — figure from ``build_timeline``.
      - ``local_pane``: gr.Markdown — local-fallback message.
    """
    components: dict[str, Any] = {}

    # ----- verdict_view (default visible) ------------------------------------
    verdict_view = gr.Column(visible=True)
    with verdict_view:
        gr.Markdown("### Live diagnosis")
        gr.Markdown(
            "_Streaming a real disconnect from the project owner's laptop "
            "through this Space's `live_diagnose` endpoint. Verdict appears "
            "below as the classifier + anomaly detector + narrator finish._"
        )

        # Result panes (initially placeholder; filled by app.py's poller
        # when a complete verdict lands in OWNER_STREAM_STATE).
        verdict_pane = gr.HTML(
            value="<i>Waiting for first live drop...</i>",
            label="Verdict",
        )
        what_to_do_pane = gr.HTML(value="", label="Recommended action")
        timeline_pane = gr.Plot(value=None, label="Telemetry timeline")

        # UI-06 CTA echo (same target as Synthetic tab).
        gr.Markdown(
            "---\n\n"
            "### Try it on a real network -- install the local agent\n\n"
            f"**Install:** [{_AGENT_REPO_URL.replace('https://', '')}]"
            f"({_AGENT_REPO_URL})\n\n"
            "_The owner's stream renders here when an `agent diagnose --cloud` "
            "drop is in flight._"
        )

    # ----- local_view (D-STATUS-06 swap target, hidden by default) -----------
    local_view = gr.Column(visible=False)
    with local_view:
        gr.Markdown("### Local mode")
        gr.Markdown(
            "_The Space was sleeping when the agent attempted to connect; "
            "the verdict was computed on the owner's laptop. Live mode will "
            "resume on the next drop._"
        )
        local_pane = gr.Markdown("_Waiting for next live drop..._")

    components.update(
        verdict_view=verdict_view,
        local_view=local_view,
        verdict_pane=verdict_pane,
        what_to_do_pane=what_to_do_pane,
        timeline_pane=timeline_pane,
        local_pane=local_pane,
    )
    return components
