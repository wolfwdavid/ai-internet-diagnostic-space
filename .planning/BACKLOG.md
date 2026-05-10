# Space repo BACKLOG -- v1.x deferred items

Items deferred from v1 plans, tracked here for follow-up after v1 ships.

## D-TIMELINE-01 / D-TIMELINE-03 -- Plotly bidirectional citation linking

- **Origin:** Plan 03-02 (Phase 3 verdict-card-and-timeline)
- **Spike:** `.planning/SPIKE-03-02-LOG.md` (2026-05-09)
- **Outcome:** `Resume-signal: unidirectional + fillpattern` -- Pitfall A
  (`Plotly_click` JS bridge) treated as FAIL on the deployed HF Space
  surface; Pitfall B (`fillpattern` Bar overlay) PASS.
- **Decision:** Downgrade D-TIMELINE-01/D-TIMELINE-03 to **unidirectional**
  citation linking in v1. Evidence-list click can still pulse the cited
  timeline frame (gr.HTML onClick -> gr.State update is reliable). Frame
  click -> citation pulse (the reverse direction) is NOT wired in v1.
- **v1.x add-back plan:** Re-spike `Plotly_click` JS bridge against a
  deployed HF Space (not just localhost). If the deployed surface allows
  the JS bridge to fire (Gradio 6.x's CSP / iframe behavior may have
  changed by then), wire `attach_bidirectional_linking(timeline_pane,
  frame_click_state)` into `build_synthetic_tab()` and add the JS payload
  to `src/space/ui/timeline.py`. The 03-RESEARCH.md "Pattern 5" snippet
  remains the canonical reference implementation.
- **Tracked since:** 2026-05-09 (continuation execution of plan 03-02 Task 3)
