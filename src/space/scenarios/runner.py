"""Scenario runner -- generate telemetry from a scenario's seed and predict.

Public API consumed by the Synthetic-tab UI (synthetic_tab.py) and by plan
03-05 (cached narrations) for offline regeneration.

Determinism contract: ``run_scenario(slug)`` is a pure function of ``slug``
(plus the loaded model artifacts). Same slug -> same telemetry -> same
verdict. This is the foundation of the plan 03-05 cache: the verdict and
its top_k probabilities are reproducible given the committed scenario seeds
and the v1.0.0 model artifacts.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from wifi_diag_schema.verdict import Verdict

from src.space._vendored_model.synth.state_machines import GENERATORS
from src.space.inference import predict
from src.space.scenarios.catalog import SCENARIOS_BY_SLUG, Scenario


def _generate_frames(scenario: Scenario) -> list[dict[str, Any]]:
    """Run the scenario's class-specific state machine with its fixed seed.

    Note on signature deviation from plan: the vendored Phase 1 state machines
    take ``(rng)`` only -- the per-class WINDOW_MS / SAMPLE_INTERVAL_MS are
    baked into each module (see ``_vendored_model/synth/state_machines/*.py``).
    The ``Scenario.n_frames`` field is informational (timeline x-axis label)
    not a generator argument.

    The scenario's ``network_mode`` tag is written onto every frame so the
    D-CAL-09 mask-then-renormalize step (which keys off the LAST frame's
    ``network_mode``) sees the demo's intended framing -- e.g. ``stuck_on_weak_ap``
    is tagged ``home`` even though the underlying ``rf_sticky_client`` state
    machine emits ``enterprise``-tagged frames natively.
    """
    generator = GENERATORS[scenario.class_slug]
    rng = np.random.default_rng(scenario.seed)
    frames = list(generator(rng))
    for f in frames:
        f["network_mode"] = scenario.network_mode
    return frames


def run_scenario(slug: str) -> tuple[Verdict, np.ndarray, list[dict[str, Any]]]:
    """Generate telemetry, predict, return all three for the UI to render.

    Args:
        slug: One of the 8 scenario slugs (see SCENARIOS in catalog.py).

    Returns:
        A 3-tuple of:
          - verdict: schema-valid Verdict with top_k=10 (D-CAL-08), masked
            for the scenario's network_mode (D-CAL-09). ``headline`` and
            ``suggested_fix`` are Phase 2 stubs until plan 03-04/03-05 wires
            the narrator.
          - anomaly_scores: per-frame IForest decision_function output;
            higher = more anomalous (D-ANOM-02). Used by the timeline's
            anomaly band overlay (D-TIMELINE-02).
          - frames: the generated telemetry list -- the timeline plotter
            iterates this for RSSI / RTT / DNS / event-marker traces.

    Raises:
        KeyError: if ``slug`` is not in SCENARIOS_BY_SLUG.
    """
    scenario = SCENARIOS_BY_SLUG[slug]
    frames = _generate_frames(scenario)
    verdict, scores = predict(frames)
    return verdict, scores, frames
