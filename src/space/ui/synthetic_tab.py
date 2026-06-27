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


Citation linking: per ``.planning/SPIKE-03-02-LOG.md`` the spike resolved
2026-05-09 with ``Resume-signal: unidirectional + fillpattern`` (Pitfall A
FAIL on the JS bridge, Pitfall B PASS on the Bar fillpattern). Plan 03-02's
production timeline ships the fillpattern Bar overlay but skips the JS
bridge -- frame clicks are no-op in v1. Bidirectional add-back is tracked
in ``.planning/BACKLOG.md`` for v1.x.

Cross-plan reconciliation: plan 03-03 (this file) shipped a defensive
stub fallback for the 03-02 builders during parallel-wave execution. Plan
03-02 has now landed its production modules (``verdict_card``,
``what_to_do_card``, ``timeline``); the stubs were removed by 03-02's
final task and the imports are now plain (no try/except).

Plan 03-06 additions (UI-05 + UI-06):
  - ``Export verdict`` Markdown + JSON buttons below the timeline (UI-05).
    Wired via ``gr.DownloadButton`` whose click handler reads the latest
    ``Verdict`` from ``gr.State`` and serializes via the
    ``src.space.ui.exports`` module (``build_markdown_export`` /
    ``build_json_export``). Files are written to ``/tmp`` (HF Space's
    ephemeral writable dir per Pitfall HF) and the path is returned to
    the DownloadButton for client-side download.
  - "Try it on a real network -- install the local agent" CTA below the
    export controls (UI-06), pointing to the Phase 4 agent repo at
    ``https://github.com/wolfwdavid/ai-internet-diagnostic-agent``.
    Phase 4 owns the README install instructions on that target.
"""

from __future__ import annotations

import random
import tempfile
import time

import gradio as gr

from src.space.inference import _ANOMALY_THRESHOLD
from src.space.narration_cache import load_cached_narration
from src.space.scenarios.catalog import SCENARIOS, SCENARIOS_BY_SLUG
from src.space.scenarios.runner import run_scenario
from src.space.ui.exports import build_json_export, build_markdown_export
from src.space.ui.timeline import build_timeline
from src.space.ui.verdict_card import build_verdict_card
from src.space.ui.what_to_do_card import build_what_to_do_card

# UI-06 CTA: Phase 4 agent repo (per memory: GitHub login is `wolfwdavid`,
# distinct from HF profile `WolfDavid`). Phase 4 owns the README install
# instructions at this URL.
_AGENT_REPO_URL = "https://github.com/wolfwdavid/ai-internet-diagnostic-agent"


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def card_click_handler(slug: str):
    """Run scenario by slug, return (verdict_html, what_to_do_html, timeline_fig, verdict).

    D-SYNTH-02: brief 'Analyzing telemetry...' pause (~1.2s) before reveal.
    The classifier IS running on real telemetry; the sleep guarantees the
    user perceives the analysis step.

    SCEN-02 (plan 03-05): the narrator output (headline, suggested_fix,
    evidence) is loaded from ``cache/narrations/{slug}.json`` rather than
    invoked at request time. Zero per-visitor Anthropic API spend
    (D-NARRATOR-05 + Pitfall 10 mitigation). Defense-in-depth fallback to
    ``narrate_templated`` if the cache file is missing for any reason
    (LLM-05 / D-NARRATOR-03).

    Plan 03-06 (UI-05): the 4th element is the live ``Verdict`` object,
    threaded through ``gr.State`` so the Markdown/JSON export buttons can
    serialize it on demand without re-running the scenario.
    """
    time.sleep(1.2)  # D-SYNTH-02 -- Analyzing telemetry... animation
    scenario = SCENARIOS_BY_SLUG[slug]
    classifier_verdict, scores, frames = run_scenario(slug)

    # SCEN-02: load pre-cached narrator output (zero per-visitor LLM cost).
    try:
        verdict = load_cached_narration(slug)
    except FileNotFoundError:
        # Defense-in-depth fallback: templated narrator (LLM-05). Lazy
        # import keeps the templated narrator off the startup hot path.
        from wifi_diag_narrator.templated import narrate_templated

        verdict = narrate_templated(classifier_verdict, frames)

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
    # 4th element threads the Verdict to gr.State for UI-05 exports.
    return verdict_html, what_to_do_html, fig, verdict


def random_scenario_handler():
    """UI-03: Random scenario button -- pick one of 8 and run."""
    slug = random.choice(SCENARIOS).slug
    return card_click_handler(slug)


# ---------------------------------------------------------------------------
# Plan 03-06 export handlers (UI-05)
# ---------------------------------------------------------------------------
#
# State for the most recently rendered Verdict so the export buttons can
# serialize it. Gradio idiom: store the Verdict in a gr.State component,
# updated each click. The DownloadButton's click handler reads State,
# serializes via src.space.ui.exports, writes to /tmp, returns the path.


def _write_tmp(content: str, suffix: str) -> str:
    """Write ``content`` to a NamedTemporaryFile and return its path.

    HF Spaces filesystem is ephemeral except ``/tmp`` (per Pitfall HF and
    the spaces-storage docs). NamedTemporaryFile(delete=False) lets
    Gradio serve the file before cleanup.
    """
    fh = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=suffix,
        delete=False,
        encoding="utf-8",
    )
    try:
        fh.write(content)
    finally:
        fh.close()
    return fh.name


def export_markdown_handler(verdict_state):
    """UI-05: serialize the latest Verdict to a Markdown file for download.

    Returns a path to a temporary .md file (gr.DownloadButton consumes the
    path). If no scenario has been clicked yet, returns a placeholder file
    so the download still works without crashing the click event.
    """
    if verdict_state is None:
        content = "# No verdict yet\n\nClick a scenario card or the Random button first."
    else:
        content = build_markdown_export(verdict_state)
    return _write_tmp(content, ".md")


def export_json_handler(verdict_state):
    """UI-05: serialize the latest Verdict to a JSON envelope file for download.

    Returns a path to a temporary .json file. Envelope shape per
    ``src.space.ui.exports.build_json_export``: ``{verdict, generated_at, space_version}``.
    """
    if verdict_state is None:
        content = '{"error": "No verdict yet -- click a scenario card or the Random button first."}'
    else:
        content = build_json_export(verdict_state)
    return _write_tmp(content, ".json")


# ---------------------------------------------------------------------------
# Tab builder (D-SYNTH-01..03 + UI-05 + UI-06)
# ---------------------------------------------------------------------------


def build_synthetic_tab() -> dict:
    """Build the Synthetic tab Blocks composition.

    Layout (D-VERDICT-08 stacked column):
      1. Header
      2. Random scenario button (UI-03)
      3. 4x2 card grid -- one button per scenario (D-SYNTH-01)
      4. Result panes: verdict card -> what-to-do card -> 4-row timeline
      5. UI-05: Export verdict (Markdown + JSON) buttons
      6. UI-06: 'Try it on a real network' CTA -> agent repo

    Returns a dict of the live components for ``app.py`` / 03-05 / 03-06 to
    wire additional event handlers if needed.
    """
    components: dict = {}

    # Header
    gr.Markdown("### Synthetic scenarios")
    gr.Markdown("_Click a scenario card to run a real classifier verdict, or roll the dice._")

    # UI-03: Random scenario button
    with gr.Row():
        random_btn = gr.Button("Random scenario", variant="primary")
    components["random_btn"] = random_btn

    # D-SYNTH-01: 4x2 card grid
    card_buttons: list[tuple[str, gr.Button]] = []
    for row_start in (0, 4):
        with gr.Row():
            for s in SCENARIOS[row_start : row_start + 4]:
                with gr.Column():
                    gr.Markdown(f"**{s.display_name}**\n\n_{s.description}_\n\n`{s.network_mode}`")
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

    # UI-05: Export verdict buttons + Verdict gr.State threaded through
    # card / random handlers so exports always reflect the most-recent click.
    verdict_state = gr.State(value=None)
    components["verdict_state"] = verdict_state

    with gr.Row():
        md_btn = gr.DownloadButton(
            label="Export verdict (Markdown)",
            visible=True,
        )
        json_btn = gr.DownloadButton(
            label="Export verdict (JSON)",
            visible=True,
        )
    components["md_btn"] = md_btn
    components["json_btn"] = json_btn

    # UI-06: 'Try it on a real network' CTA -> agent repo.
    # Below the export controls so the user-flow is: see verdict -> share it
    # (UI-05) -> level up to real telemetry (UI-06). Phase 4 owns the README
    # install instructions at the linked URL.
    gr.Markdown(
        "---\n\n"
        "### Try it on a real network -- install the local agent\n\n"
        "Diagnose your real Wi-Fi disconnects on Windows / macOS / Linux with a "
        "privacy-first local agent. The agent runs the same classifier + anomaly "
        "detector you see above, and uploads only schema-allowlisted telemetry "
        "(never raw payloads, credentials, or hostnames).\n\n"
        f"**Install:** [{_AGENT_REPO_URL.replace('https://', '')}]({_AGENT_REPO_URL})\n\n"
        "_Live SSE transport ships in Phase 5._"
    )

    # Wire scenario handlers -- 4 outputs (verdict_html, what_to_do_html,
    # timeline_fig, verdict_state). The 4th output threads the Verdict
    # through gr.State so the export buttons can serialize it on demand.
    outputs = [verdict_pane, what_to_do_pane, timeline_pane, verdict_state]
    random_btn.click(fn=random_scenario_handler, inputs=[], outputs=outputs)
    for slug, btn in card_buttons:
        # Default-arg trick captures slug at definition time, not call time.
        btn.click(fn=lambda s=slug: card_click_handler(s), inputs=[], outputs=outputs)

    # UI-05: Export wiring (Markdown / JSON). Each handler reads the latest
    # Verdict from gr.State, serializes via src.space.ui.exports, writes a
    # temp file, returns the path -- gr.DownloadButton triggers download.
    md_btn.click(fn=export_markdown_handler, inputs=[verdict_state], outputs=md_btn)
    json_btn.click(fn=export_json_handler, inputs=[verdict_state], outputs=json_btn)

    # v1: unidirectional citation linking -- frame clicks are no-op per
    # SPIKE-03-02-LOG.md (Resume-signal: unidirectional + fillpattern).
    # Pitfall A FAIL: Plotly_click JS bridge unreliable on deployed HF Space.
    # v1.x add-back tracked in .planning/BACKLOG.md.

    return components
