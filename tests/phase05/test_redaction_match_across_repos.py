"""Plan 05-01: structural cross-repo guard — Space-side and agent-side
``redaction.py`` MUST keep their DENY_PATTERNS list byte-equal.

This is a defense-in-depth check above the property test: even if the property
test happens to pass on a small sample, this test forces the regex lists to
stay literally identical so the privacy posture cannot silently drift between
repos.

Marked xfail-strict during Wave 0; Task 1 lands the Space-side redaction.py
and this test turns GREEN.
"""

from __future__ import annotations

import re
from pathlib import Path

_SPACE_REDACT = (
    Path(__file__).resolve().parent.parent.parent / "src" / "space" / "live" / "redaction.py"
)
_AGENT_REDACT = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "ai-internet-diagnostic-agent"
    / "agent"
    / "redaction.py"
)

# Match the DENY_PATTERNS list body across newlines.
_DENY_RE = re.compile(
    r"DENY_PATTERNS:\s*list\[re\.Pattern\]\s*=\s*\[(.*?)\]",
    re.DOTALL,
)


def _normalize(s: str) -> str:
    """Collapse whitespace for tolerant equality."""
    return " ".join(s.split())


def test_deny_patterns_byte_equal():
    """The DENY_PATTERNS list in both redaction modules MUST be byte-equal modulo whitespace."""
    assert _SPACE_REDACT.exists(), f"missing: {_SPACE_REDACT}"
    assert _AGENT_REDACT.exists(), f"missing: {_AGENT_REDACT}"

    space_src = _SPACE_REDACT.read_text()
    agent_src = _AGENT_REDACT.read_text()

    sm = _DENY_RE.search(space_src)
    am = _DENY_RE.search(agent_src)
    assert sm is not None, "Space redaction.py missing DENY_PATTERNS list"
    assert am is not None, "Agent redaction.py missing DENY_PATTERNS list"

    assert _normalize(sm.group(1)) == _normalize(am.group(1)), (
        "DENY_PATTERNS divergence between Space and agent — "
        "single-redaction-boundary invariant violated."
    )


def test_space_redaction_has_vendor_marker():
    """Space ``redaction.py`` MUST contain a ``# Vendored from .* @ <commit>`` marker."""
    assert _SPACE_REDACT.exists(), f"missing: {_SPACE_REDACT}"
    src = _SPACE_REDACT.read_text()
    assert re.search(r"# Vendored from .* @ [0-9a-f]{7,}", src), (
        "Space redaction.py must declare its agent-repo vendor source + commit hash "
        "(see plan 05-01 task 1)"
    )


def test_schema_allowlist_present_in_both():
    """Both modules MUST define ``SCHEMA_ALLOWLIST: frozenset[str]``."""
    space_src = _SPACE_REDACT.read_text()
    agent_src = _AGENT_REDACT.read_text()
    pat = re.compile(r"SCHEMA_ALLOWLIST:\s*frozenset\[str\]\s*=")
    assert pat.search(space_src), "Space redaction missing SCHEMA_ALLOWLIST"
    assert pat.search(agent_src), "Agent redaction missing SCHEMA_ALLOWLIST"
