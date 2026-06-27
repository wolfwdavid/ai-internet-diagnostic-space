"""Phase 5 plan 05-01 shared fixtures.

- ``handshake_compat_corpus``: load handshake compatibility cases from fixture JSON.
- ``redaction_corpus``: load adversarial-PII redaction cases from fixture JSON.
- ``agent_redact_fn``: patch sys.path to import ``agent.redaction.redact_to_schema``
  from the sibling ``ai-internet-diagnostic-agent`` repo for byte-equality tests
  (Pitfall 6 server/agent parity).
- ``pinned_salt``: pin both Space-side and agent-side BSSID salt providers to the
  same 32 deterministic bytes so cross-repo byte-equality tests can compare
  ``model_dump_json()`` outputs without spurious salt mismatch.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_FIXTURES = Path(__file__).parent / "fixtures"
_AGENT_REPO = Path(__file__).resolve().parent.parent.parent.parent / "ai-internet-diagnostic-agent"


@pytest.fixture
def handshake_compat_corpus() -> list[dict]:
    """Load handshake compatibility cases (local/remote/expected) from JSON."""
    return json.loads((_FIXTURES / "handshake_compat.json").read_text())


@pytest.fixture
def redaction_corpus() -> list[dict]:
    """Load redaction adversarial-PII cases from JSON.

    Each entry: ``{"label": str, "raw_payload": dict, "must_strip": list[str]}``.
    """
    return json.loads((_FIXTURES / "redaction_corpus.json").read_text())


@pytest.fixture
def pinned_salt(monkeypatch) -> bytes:
    """Pin the BSSID salt across both Space and agent redaction modules.

    Returns the 32 fixed bytes. After this fixture runs:
      - Space-side ``_load_space_salt()`` returns these bytes.
      - Agent-side ``load_or_create_salt()`` returns these bytes.

    This is required for the cross-repo byte-equality property test — both
    redactors must hash BSSIDs with the same salt for ``model_dump_json()``
    output to be identical.
    """
    salt = bytes(range(32))  # 32 deterministic bytes

    # Patch Space-side salt loader (lazy — module may not yet exist in Wave 0)
    try:
        from src.space.live import redaction as _space_red  # noqa: F401

        monkeypatch.setattr(
            "src.space.live.redaction._load_space_salt",
            lambda: salt,
            raising=False,
        )
    except ImportError:
        pass

    # Patch agent-side salt loader if importable.
    agent_repo = str(_AGENT_REPO)
    if agent_repo not in sys.path:
        sys.path.insert(0, agent_repo)
    try:
        import agent.salt as _agent_salt  # noqa: F401

        monkeypatch.setattr("agent.salt.load_or_create_salt", lambda: salt, raising=False)
        # agent.redaction imports load_or_create_salt at the top; patch the bound name too.
        import agent.redaction as _agent_red  # noqa: F401

        monkeypatch.setattr("agent.redaction.load_or_create_salt", lambda: salt, raising=False)
    except ImportError:
        pass

    return salt


@pytest.fixture
def agent_redact_fn(pinned_salt):
    """Import the agent-side ``redact_to_schema`` for cross-repo parity tests.

    Patches sys.path with the sibling agent repo and returns the callable.
    Depends on ``pinned_salt`` so any BSSID hashing uses the deterministic salt.
    """
    agent_repo = str(_AGENT_REPO)
    if agent_repo not in sys.path:
        sys.path.insert(0, agent_repo)
    from agent.redaction import redact_to_schema as _AGENT_REDACT

    return _AGENT_REDACT
