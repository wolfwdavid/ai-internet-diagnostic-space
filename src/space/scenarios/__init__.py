"""Phase 3 plan 03-03: 8 named scenarios mapped 1:1 to DisconnectClass slugs (SCEN-01).

Public API consumed by plan 03-05 (cached narrations) and the Synthetic tab UI:
    - SCENARIOS: list[Scenario]
    - SCENARIOS_BY_SLUG: dict[str, Scenario]
    - run_scenario(slug) -> (Verdict, np.ndarray, list[dict])
"""
from __future__ import annotations

from .catalog import SCENARIOS, SCENARIOS_BY_SLUG, Scenario
from .runner import run_scenario

__all__ = ["SCENARIOS", "SCENARIOS_BY_SLUG", "Scenario", "run_scenario"]
