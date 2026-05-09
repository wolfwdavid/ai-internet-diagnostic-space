"""Phase 3 plan 03-03 -- 8-scenario catalog + deterministic runner contract.

Tests the SCEN-01 surface: 8 named scenarios mapped 1:1 to DisconnectClass
slugs (the 2 unmapped classes are dns_resolver_fail and isp_upstream_fail).
The runner produces deterministic verdicts from each scenario's fixed seed.
"""
from __future__ import annotations

from typing import get_args

import numpy as np
import pytest
from wifi_diag_schema.enums import DisconnectClass, NetworkMode
from wifi_diag_schema.verdict import Verdict

from src.space.scenarios.catalog import SCENARIOS, Scenario
from src.space.scenarios.runner import run_scenario

_ALL_CLASSES = set(get_args(DisconnectClass))
_MAPPED_CLASSES = {
    "radius_timeout",
    "ap_roam_rekey_fail",
    "auth_8021x_eap_fail",
    "captive_portal_expiry",
    "dhcp_lease_churn",
    "mac_randomization_reject",
    "driver_power_save_wake",
    "rf_sticky_client",
}
_UNMAPPED = _ALL_CLASSES - _MAPPED_CLASSES  # {dns_resolver_fail, isp_upstream_fail}


def test_eight_scenarios() -> None:
    """SCEN-01: exactly 8 named scenarios."""
    assert len(SCENARIOS) == 8


def test_class_mapping() -> None:
    """SCEN-01: scenarios cover the 8 demo classes; 2 classes intentionally unmapped."""
    class_slugs = {s.class_slug for s in SCENARIOS}
    assert class_slugs == _MAPPED_CLASSES
    assert _UNMAPPED == {"dns_resolver_fail", "isp_upstream_fail"}


def test_all_scenario_slugs_unique() -> None:
    """No two scenarios share a slug or class_slug."""
    slugs = [s.slug for s in SCENARIOS]
    class_slugs = [s.class_slug for s in SCENARIOS]
    assert len(set(slugs)) == 8
    assert len(set(class_slugs)) == 8


def test_network_mode_valid() -> None:
    """Every scenario.network_mode is a valid NetworkMode literal."""
    valid = set(get_args(NetworkMode))
    for s in SCENARIOS:
        assert s.network_mode in valid, f"{s.slug}: invalid network_mode {s.network_mode!r}"


def test_scenarios_have_stable_seeds() -> None:
    """Every scenario carries an int seed (used by 03-05 cache regen)."""
    for s in SCENARIOS:
        assert isinstance(s.seed, int)
        assert s.seed > 0


def test_scenarios_have_display_metadata() -> None:
    """Card grid (D-SYNTH-01) needs display_name + description per scenario."""
    for s in SCENARIOS:
        assert s.display_name and isinstance(s.display_name, str)
        assert s.description and isinstance(s.description, str)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.slug)
def test_all_8_load(scenario: Scenario) -> None:
    """Every scenario runs and returns (Verdict, scores, frames) with matching shapes."""
    verdict, scores, frames = run_scenario(scenario.slug)
    assert isinstance(verdict, Verdict)
    assert isinstance(scores, np.ndarray)
    assert scores.shape[0] == len(frames)
    assert len(frames) > 0


def test_runner_is_deterministic() -> None:
    """Same seed -> same telemetry -> same prediction (D-CAL-01 reproducibility)."""
    for s in SCENARIOS:
        v1, _, _ = run_scenario(s.slug)
        v2, _, _ = run_scenario(s.slug)
        assert v1.top_class == v2.top_class, f"{s.slug}: nondeterministic top_class"
        assert abs(v1.confidence - v2.confidence) < 1e-9, (
            f"{s.slug}: nondeterministic confidence ({v1.confidence} vs {v2.confidence})"
        )


def test_runner_produces_expected_top_class_for_clear_cases() -> None:
    """Sanity check: synth telemetry the classifier recognizes for >=5/8 scenarios.

    Allow up to 3 misses for noisy classes -- this test guards the synth/classifier
    handshake without forcing perfect agreement (the calibration ECE on synthetic
    eval is 0.28 per Phase 2; some classes are harder to distinguish).
    """
    hits = 0
    misses: list[tuple[str, str]] = []
    for s in SCENARIOS:
        verdict, _, _ = run_scenario(s.slug)
        if verdict.top_class == s.class_slug:
            hits += 1
        else:
            misses.append((s.slug, verdict.top_class))
    assert hits >= 5, (
        f"Only {hits}/8 scenarios produced expected top_class -- "
        f"synth/classifier mismatch? Misses: {misses}"
    )
