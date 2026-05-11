"""AI Internet Diagnostic -- Hugging Face Space (Phase 3 verdict UI shell).

Phase 3 plan 03-01 replaces the Phase 1 hello-world with the Synthetic +
Live two-tab structure. Subsequent plans (03-02..03-06) wire the verdict
card, timeline, scenarios, narrator-cache, and exports.

The runtime version assertions below are Pitfall 7 (gradio pin drift) and
Pitfall F (python_version unquoted) mitigations. DO NOT remove.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import gradio as gr

# Pitfall 7 + Pitfall F: runtime version assertions (DO NOT remove).
assert gr.__version__.startswith("6.13"), (
    f"Expected Gradio 6.13.x, got {gr.__version__}"
)
assert sys.version_info[:2] == (3, 13), (
    f"Expected Python 3.13, got {sys.version_info}"
)

from src.space.ui.cold_start import COLD_START_MARKDOWN  # noqa: E402
from src.space.ui.synthetic_tab import build_synthetic_tab  # noqa: E402
from src.space.live.live_diagnose import live_diagnose  # noqa: E402  # plan 05-01
from src.space.ui.banner import render_banner  # noqa: E402  # plan 05-03
from src.space.ui.live_tab import build_live_tab  # noqa: E402  # plan 05-03
from src.space.live import status  # noqa: E402  # plan 05-03 poller source

# Plan 05-03: load banner CSS once at module load -- gr.Blocks(css=...)
# applies it page-wide so the banner + transition fade (D-STATUS-28) work
# regardless of which tab the visitor is on (D-STATUS-11).
_BANNER_CSS_PATH = Path(__file__).parent / "src" / "space" / "ui" / "banner.css"
_CSS = _BANNER_CSS_PATH.read_text(encoding="utf-8") if _BANNER_CSS_PATH.exists() else ""


with gr.Blocks(title="AI Internet Diagnostic") as demo:
    # UI-04 cold-start banner: top-of-page so it's visible during the first
    # request after a wake-from-sleep cycle. Banner copy ("Space is waking up
    # -- first request takes ~30s.") lives in src/space/ui/cold_start.py so
    # plan 03-02 can swap to a `gr.Status()` skeleton without re-touching app.py.
    gr.Markdown(COLD_START_MARKDOWN)

    gr.Markdown("# AI Internet Diagnostic")
    gr.Markdown(
        "_Tells you the specific reason your Wi-Fi just dropped -- "
        "evidence-grounded, confidence-scored attribution._"
    )

    # Plan 05-03: page-level connection-status banner (D-STATUS-02 /
    # D-STATUS-11). Sits ABOVE gr.Tabs() so it is visible on both the
    # Synthetic and Live tabs. Polled by the gr.Timer below (500ms cadence,
    # D-STATUS-29). The connection_state gr.State threads the latest snap
    # dict through tick handlers so the timer can compare deltas if needed.
    connection_state = gr.State({})
    banner = gr.HTML(value=render_banner(None), elem_id="conn-banner")

    with gr.Tabs():
        # D-SYNTH-03: Synthetic declared FIRST so Gradio renders it as the
        # default landing tab. A casual visitor with no install lands here.
        with gr.Tab("Synthetic"):
            # Plan 03-03 wires the 8 scenario cards + Random button + analyzing
            # animation (D-SYNTH-01..03, UI-03). Verdict-card / timeline
            # builders are owned by plan 03-02 (defensive imports inside
            # synthetic_tab.py fall back to inline stubs if 03-02 hasn't landed).
            #
            # D-VERDICT-08 stacked column layout order anchor (read by
            # tests/test_smoke.py::test_layout_order):
            #   1. build_verdict_card -> verdict + colored confidence badge
            #   2. build_what_to_do_card -> recommended action
            #   3. build_timeline -> 4-row Plotly drill-down timeline
            build_synthetic_tab()

        # Plan 05-03: replace the Phase 3 D-SYNTH-04 static shell with the
        # composition from src/space/ui/live_tab.py. The Live tab now reuses
        # Phase 3's verdict-card / what-to-do-card / timeline builders so the
        # Live tab UI === Synthetic tab UI by composition (ROADMAP UI-07
        # success criterion). The page-level banner above gr.Tabs() reflects
        # transport state in real time.
        with gr.Tab("Live"):
            live_components = build_live_tab()

    # ------------------------------------------------------------------
    # Plan 05-01: register live_diagnose as a named Gradio API endpoint
    # (consumed by agent transport via gradio_client.Client.submit,
    # api_name="live_diagnose"). NOT shown in the Tabs UI; pure API
    # surface for the agent. Hidden components carry the four args.
    # ------------------------------------------------------------------
    live_handshake = gr.Textbox(visible=False, label="handshake_json")
    live_frames = gr.JSON(visible=False, label="frames_json_list")
    live_owner = gr.Textbox(visible=False, label="owner_key")
    live_pair = gr.Textbox(visible=False, label="pair_code")
    live_output = gr.JSON(visible=False, label="live_diagnose_output")
    _live_trigger = gr.Button(visible=False)
    _live_trigger.click(
        fn=live_diagnose,
        inputs=[live_handshake, live_frames, live_owner, live_pair],
        outputs=[live_output],
        api_name="live_diagnose",
    )

    # ------------------------------------------------------------------
    # Plan 05-03: 500ms-cadence banner poller (D-STATUS-29). Reads
    # status.snapshot(session_key) for the owner-key session derived from
    # the OWNER_KEY env var (matching plan 05-01's session_key shape
    # f"owner:{owner_key[:8]}"). On state=local_fallback, swap the Live
    # tab's verdict_view for local_view (D-STATUS-06).
    # ------------------------------------------------------------------
    _OWNER_KEY_RAW = os.environ.get("OWNER_KEY", "")
    _OWNER_SESSION_KEY = f"owner:{_OWNER_KEY_RAW[:8]}" if _OWNER_KEY_RAW else ""

    def _poll_banner(prev_state):
        """gr.Timer tick handler — reads OWNER_STREAM_STATE, returns updates.

        Returns a 4-tuple matching the timer outputs:
          1. new connection_state dict (passed back into the next tick)
          2. banner HTML (re-rendered every tick)
          3. verdict_view visibility update (visible unless local_fallback)
          4. local_view visibility update (visible only on local_fallback)
        """
        if not _OWNER_SESSION_KEY:
            # No OWNER_KEY env -- banner stays Idle, both views as default.
            return (
                {},
                render_banner(None),
                gr.update(visible=True),
                gr.update(visible=False),
            )
        snap = status.snapshot(_OWNER_SESSION_KEY)
        banner_html = render_banner(snap)
        s = (snap or {}).get("state")
        show_verdict = s != "local_fallback"
        show_local = s == "local_fallback"
        return (
            snap or {},
            banner_html,
            gr.update(visible=show_verdict),
            gr.update(visible=show_local),
        )

    _poll_timer = gr.Timer(value=0.5)
    _poll_timer.tick(
        fn=_poll_banner,
        inputs=[connection_state],
        outputs=[
            connection_state,
            banner,
            live_components["verdict_view"],
            live_components["local_view"],
        ],
    )

# RESEARCH OQ-2: Gradio generator streams require `demo.queue()`; concurrency
# limit of 2 caps simultaneous live_diagnose sessions on the free-CPU tier
# (the owner's dogfood session + at most one pair-code visitor in parallel).
demo.queue(default_concurrency_limit=2, api_open=True)

if __name__ == "__main__":
    # Plan 05-03: in Gradio 6.0, `css` moved from gr.Blocks(...) to launch(...).
    # The banner CSS (banner.css; loaded at module top) must be applied here
    # for D-STATUS-08 traffic-light + diagonal-stripe rendering to take effect.
    demo.launch(css=_CSS)
