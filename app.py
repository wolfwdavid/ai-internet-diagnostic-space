"""AI Internet Diagnostic -- Hugging Face Space (Phase 3 verdict UI shell).

Phase 3 plan 03-01 replaces the Phase 1 hello-world with the Synthetic +
Live two-tab structure. Subsequent plans (03-02..03-06) wire the verdict
card, timeline, scenarios, narrator-cache, and exports.

The runtime version assertions below are Pitfall 7 (gradio pin drift) and
Pitfall F (python_version unquoted) mitigations. DO NOT remove.
"""
from __future__ import annotations

import sys

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

    with gr.Tabs():
        # D-SYNTH-03: Synthetic declared FIRST so Gradio renders it as the
        # default landing tab. A casual visitor with no install lands here.
        with gr.Tab("Synthetic"):
            # Plan 03-03 wires the 8 scenario cards + Random button + analyzing
            # animation (D-SYNTH-01..03, UI-03). Verdict-card / timeline
            # builders are owned by plan 03-02 (defensive imports inside
            # synthetic_tab.py fall back to inline stubs if 03-02 hasn't landed).
            build_synthetic_tab()

        # D-SYNTH-04: Live tab v1 shell -- empty state + agent install CTA
        # (Plan 03-06) + 'planned flow' preview asset (text-only Markdown
        # callout per Claude's discretion in CONTEXT.md, cheapest viable).
        with gr.Tab("Live"):
            gr.Markdown("### Live diagnosis")
            gr.Markdown(
                "Connect the local agent to diagnose your real Wi-Fi.\n\n"
                "_Plan 03-06 wires the agent install CTA. "
                "Live SSE transport ships in Phase 5._"
            )
            # D-SYNTH-04 static preview of the planned Live-mode flow.
            # Format choice (Markdown vs PNG vs GIF vs Lottie) was Claude's
            # discretion; Markdown picked as cheapest viable -- no binary
            # asset to commit, no design tool roundtrip, screen-reader
            # friendly by default. Future v1.x can swap this single block
            # for a richer asset without touching the surrounding shell.
            gr.Markdown(
                "> **Planned flow** (D-SYNTH-04 preview)\n"
                "> 1. Install the local agent on your laptop.\n"
                "> 2. Agent collects 802.1X / DHCP / RADIUS telemetry every second.\n"
                "> 3. On a disconnect, the agent uploads a 30-second window to this Space.\n"
                "> 4. Space runs the same classifier + anomaly detector you see in the Synthetic tab.\n"
                "> 5. Verdict + drill-down timeline appears here, with full evidence citations.\n"
                ">\n"
                "> _Live SSE transport ships in Phase 5; this preview honors D-SYNTH-04._"
            )


if __name__ == "__main__":
    demo.launch()
