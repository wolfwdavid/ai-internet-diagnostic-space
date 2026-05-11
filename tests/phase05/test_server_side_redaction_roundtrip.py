"""Plan 05-01: hypothesis-based property test — Space-side and agent-side ``redact_to_schema``
MUST produce byte-identical ``TelemetryFrame.model_dump_json()`` outputs on identical inputs.

This is Pitfall 6's structural guarantee made into a CI gate: if the vendored Space-side
redactor ever drifts from the agent-side single redaction boundary, this property test
fails the build.

The pattern mirrors ``../ai-internet-diagnostic-agent/tests/test_redaction_roundtrip.py``
(200 examples × 5 adversarial PII templates).

Marked xfail-strict during Wave 0; Task 1 lands the Space-side redaction module and the
test turns GREEN.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

# Wave 0 RED marker: skip the entire module if Task 1's redaction module hasn't
# landed yet. Skip (rather than xfail) because hypothesis fixture injection runs
# before pytest applies module-level xfail, raising a fixture-not-found ERROR
# that pytest counts as a hard failure.
_REDACT = (
    Path(__file__).resolve().parent.parent.parent
    / "src" / "space" / "live" / "redaction.py"
)
if not _REDACT.exists():
    pytest.skip(
        "RED -- vendored Space-side redaction lands in Task 1",
        allow_module_level=True,
    )

PII_PAYLOADS = st.fixed_dictionaries({
    "evt_xml": st.sampled_from([
        '<EventData><Data Name="Identity">student@school.edu</Data></EventData>',
        '<EventData><Data Name="Reason">RADIUS_TIMEOUT</Data><Data Name="UserCert">CN=John Doe,OU=Students</Data></EventData>',
        '<EventData><Data Name="EapMethod">25</Data><Data Name="Password">hunter2</Data></EventData>',
        '<EventData><Data Name="Identity">teacher@school.edu</Data><Data Name="MAC">aa:bb:cc:dd:ee:ff</Data></EventData>',
        '<EventData><Data Name="CertSubject">CN=root.example.com,O=ACME</Data></EventData>',
    ]),
    "ts": st.floats(min_value=1700000000.0, max_value=2000000000.0,
                    allow_nan=False, allow_infinity=False),
    "rssi": st.integers(min_value=-95, max_value=-30),
    "os": st.sampled_from(["windows", "macos", "linux"]),
    "network_mode": st.sampled_from(["enterprise", "captive", "home", "unknown"]),
    "raw_bssid": st.sampled_from(["aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66"]),
})


@given(PII_PAYLOADS)
@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_space_and_agent_redaction_byte_equal(payload, pinned_salt, agent_redact_fn):
    """Same input -> byte-identical ``model_dump_json()`` from both redactors."""
    from src.space.live.redaction import redact_to_schema as space_redact

    space_out = space_redact(dict(payload)).model_dump_json()
    agent_out = agent_redact_fn(dict(payload)).model_dump_json()
    assert space_out == agent_out, (
        "Space and agent redaction outputs diverged:\n"
        f"space: {space_out!r}\nagent: {agent_out!r}"
    )


def test_corpus_byte_equal(redaction_corpus, pinned_salt, agent_redact_fn):
    """Sanity check: every adversarial-PII case in the corpus produces byte-equal output."""
    from src.space.live.redaction import redact_to_schema as space_redact

    for case in redaction_corpus:
        payload = dict(case["raw_payload"])
        s = space_redact(dict(payload)).model_dump_json()
        a = agent_redact_fn(dict(payload)).model_dump_json()
        assert s == a, f"divergence on case {case['label']!r}:\n  space={s}\n  agent={a}"
