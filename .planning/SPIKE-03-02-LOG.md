# Plan 03-02 Spike Log -- Plotly point-click JS bridge + fillpattern Bar overlay

> Spike artifact for plan
> `.planning/phases/03-space-ui-real-inference/03-02-verdict-card-and-timeline-PLAN.md`
> Task 1. Validates two MEDIUM-LOW-confidence Plotly capabilities flagged in
> `03-RESEARCH.md` (Pitfalls A and B) on a deployed HF Space before plan 03-02
> Task 3 locks the timeline implementation.

## Context

| Field            | Value                                                                                  |
| ---------------- | -------------------------------------------------------------------------------------- |
| Spike date       | 2026-05-09                                                                              |
| Branch           | `spike/plotly-clicks` (HF Space remote pending; see "Deploy status" below)              |
| Spike module     | `src/space/ui/spike_plotly.py`                                                          |
| Spike smoke test | `tests/test_spike_plotly.py` (3 tests, all PASS in CI -- module construction only)    |
| Gradio version   | `6.13.0`                                                                                |
| Plotly version   | `6.7.0`                                                                                 |
| Anthropic SDK    | `0.100.0` (recorded for context; not exercised by this spike)                            |
| Python           | `3.13`                                                                                  |

## Deploy status

**Pending user action.** The Space repo (`ai-internet-diagnostic-space`) has
no `hf-space` git remote configured at the time this spike was committed.
Before the experiments below can be evaluated on a deployed Space, the user
must:

1. Configure the HF Space remote:
   ```bash
   cd ../ai-internet-diagnostic-space
   git remote add hf-space https://huggingface.co/spaces/WolfDavid/wifi-diag
   ```
   (Requires a Hugging Face access token; one-time setup.)
2. Create the spike preview branch and push it as the Space's `main`:
   ```bash
   git checkout -b spike/plotly-clicks
   # Update app.py to launch the spike demo (replace the import line):
   # from src.space.ui.spike_plotly import build_spike_demo
   # demo = build_spike_demo()
   git commit -am "chore(03-02): swap app.py to spike demo for HF deploy"
   git push hf-space spike/plotly-clicks:main --force
   ```
3. Wait ~30 seconds for HF Space cold-start, then open the Space URL.

**Local-only fallback** (if HF deploy is gated by remote setup):
```bash
cd ../ai-internet-diagnostic-space
.venv/Scripts/python.exe -c "from src.space.ui.spike_plotly import build_spike_demo; build_spike_demo().launch()"
```
Local launch validates the JS bridge against `localhost:7860`. **Per
03-RESEARCH.md Pattern 5 caveat, local PASS is necessary but NOT sufficient**
because HF Space's hosted iframe + CSP may break the DOM-querying `setTimeout`
approach. A local-only PASS should be flagged as "PASS (local), HF-Space
verification deferred to v1.x" rather than locking bidirectional in the
production code path.

## Experiment A: Plotly point-click JS bridge (Pitfall A)

**Hypothesis:** A `Plotly.on('plotly_click')` handler attached via the
`js=` argument on a `gr.Plot.change()` listener will fire a Python callback
with `(curveNumber, pointIndex)` for clicks on individual scatter points.

**Acceptance:** at least 8 / 10 clicks across two attempts must update the
visible Markdown echo with the point info.

**How to evaluate:**

1. Open the Space URL.
2. Click each of the 10 points on the Experiment A Scatter trace.
3. Verify the visible Markdown updates with `(curveNumber, pointIndex)` for
   each click.
4. If 0 clicks fire, bump the JS `setTimeout` to 500ms in
   `_PLOTLY_CLICK_JS` and re-test (per Pitfall A "Warning signs").

**Experiment A result:** FAIL -- per user resume signal `unidirectional + fillpattern` (2026-05-09). The Plotly_click JS bridge is treated as unreliable on the deployed HF Space surface; D-TIMELINE-01/03 are downgraded to unidirectional citation linking for v1. Bidirectional add-back is recorded as a v1.x backlog item (see `.planning/BACKLOG.md`).

## Experiment B: anomaly band Bar overlay with fillpattern (Pitfall B)

**Hypothesis:** A `go.Bar` trace with
`marker=dict(pattern=dict(shape="/", fgcolor=..., size=8))` will render
visible diagonal stripes on the deployed Space (not flat color, which is
what `add_vrect(fillpattern=...)` and `layout.shapes` silently produce).

**Acceptance:** the row-2 Bar shows diagonal-stripe pattern on visual
inspection AND a `<pattern>` element exists in the rendered SVG (DevTools
SVG inspect).

**How to evaluate:**

1. Visually inspect row 2 of the Experiment B subplot.
2. Cross-check via browser DevTools -> Elements -> SVG inspect -> confirm a
   `<pattern>` element with `id` containing the trace UID exists in the
   rendered SVG.

**Experiment B result:** PASS -- per user resume signal `unidirectional + fillpattern` (2026-05-09). The diagonal-stripe `pattern.shape='/'` Bar overlay is treated as rendering correctly; D-TIMELINE-11 a11y intent ships as a fillpattern Bar overlay in the production timeline.

## Decisions

These decisions are recorded as a function of the experiment outcomes above.
Plan 03-02 Task 3 reads the `Resume-signal:` line below to choose the
correct timeline implementation branch.

| A      | B      | Decision                                                                        | D-TIMELINE impact                                       |
| ------ | ------ | ------------------------------------------------------------------------------- | ------------------------------------------------------- |
| PASS   | PASS   | Lock bidirectional citation linking + Bar-overlay fillpattern.                  | D-TIMELINE-01/03/11 ship as written.                    |
| PASS   | FAIL   | Lock bidirectional; fall back to plain rect + 'anomaly region' text annotation. | D-TIMELINE-11 a11y intent preserved by text fallback.   |
| FAIL   | PASS   | Downgrade to unidirectional (evidence -> frame pulse only); keep fillpattern.   | D-TIMELINE-01/03 v1.x add-back tracked.                 |
| FAIL   | FAIL   | Downgrade both: unidirectional + plain rect + text annotation.                  | Both downgrades; v1.x add-back tracked.                 |

**Decision -- citation linking:** Decision: downgrade to unidirectional citation linking; v1.x add-back tracked in `.planning/BACKLOG.md` ("Plotly bidirectional citation linking -- JS bridge requires HF Space deploy verification; downgraded to unidirectional in v1 per spike outcome 2026-05-09").

**Decision -- anomaly band:** Decision: ship Bar-overlay fillpattern (D-TIMELINE-11 ships as written -- diagonal-stripe `pattern.shape='/'` overlay).

## Resume-signal

The line below is parsed by Task 3's automated verify and consumed by
plans 03-03, 03-05, and 03-06 to wire JS bridge calls (or omit them).

> **REQUIRED:** Replace the placeholder line below with EXACTLY ONE of:
>
> - `Resume-signal: bidirectional + fillpattern`
> - `Resume-signal: unidirectional + fillpattern`
> - `Resume-signal: bidirectional + plain-rect`
> - `Resume-signal: unidirectional + plain-rect`
>
> No other text on that line. The line below is a placeholder that must be
> overwritten before plan 03-02 Task 3 runs.

Resume-signal: unidirectional + fillpattern

## After the user reports outcomes

The plan 03-02 executor (continuation invocation) will:

1. Replace the two `_PENDING_` result paragraphs with concrete
   `Experiment A result: PASS|FAIL -- ...` and `Experiment B result: ...` lines.
2. Replace the two `_PENDING_` decision paragraphs with the concrete decisions.
3. Replace the placeholder `Resume-signal: PENDING` with the canonical line. **(2026-05-09: replaced with `Resume-signal: unidirectional + fillpattern`.)**
4. Commit (`chore(03-02): spike outcomes recorded`).
5. Proceed to Task 2 (verdict-card + what-to-do-card builders, TDD) and
   Task 3 (4-row Plotly timeline, TDD) selecting the correct branch from
   the Resume-signal table in `03-02-verdict-card-and-timeline-PLAN.md`.
