"""Phase 5 plan 05-03: connection-status banner renderer (UI-07).

Pure function ``render_banner(state_dict) -> str`` that produces the HTML
string the page-level banner displays. Reads the latest yield payload from
``src.space.live.status.OWNER_STREAM_STATE`` (kept by plan 05-01's
``live_diagnose`` generator on every yield). No state of its own.

Rendering rules:
- 11 logical states (idle, waking, connecting, handshake_ok, connected,
  streaming, computing, stalled, reconnecting, schema_mismatch,
  local_fallback) each map to a CSS class ``conn-{state}`` in
  ``banner.css``. Additional terminal red states from plan 05-01's machine
  (handshake_failed, session_rejected, redaction_failed, live_disabled,
  complete) also have CSS classes; they share the red/green palettes.
- D-STATUS-22: streaming state appends a privacy chip
  ``redacted • BSSIDs hashed • no credentials``.
- D-STATUS-19: handshake_ok / connected / streaming / computing / complete
  append a version strip ``Space vX • Agent vY • Schema vZ``.
- D-STATUS-25: ``local_fallback`` gets an extra ``conn-persistent`` class
  so CSS can render a visible border indicating it does not auto-hide.
- D-STATUS-27: every banner has ``role="status"`` and ``aria-live="polite"``.
- D-STATUS-13: owner-mode is anonymous live — owner_key / session_key are
  NEVER surfaced in the rendered HTML even when present in ``state_dict``.

The shape of ``state_dict`` is the chunk shape plan 05-01 yields:
``{"state": "...", "schema_version": "1.1.0", "frame_index": int,
"total": int, "error": str, "reason": str, "session_key": str (NOT
rendered), "owner_key": str (NOT rendered), "agent_version": str (optional)}``.
"""
from __future__ import annotations

import html
from typing import Any

__all__ = ["render_banner"]


_SPACE_VERSION = "1.0.0"
_SCHEMA_VERSION = "1.1.0"
_DEFAULT_AGENT_VERSION = "1.0.0"

# D-STATUS-15: idle state copy + install CTA, inline.
_IDLE_COPY = (
    "No agent connected. Install: pip install ai-internet-diagnostic-agent"
    "[&lt;your-os&gt;]. After install, run `agent diagnose --cloud` to "
    "stream a verdict here."
)

# Map state -> (human-readable label, detail-string-template).
# Detail templates use Python's str.format() with allowlisted fields only.
_STATE_TEXT: dict[str, tuple[str, str]] = {
    "idle": ("Idle — waiting for agent", _IDLE_COPY),
    "waking": ("Space waking up", "first request takes ~30s after a sleep window"),
    "connecting": ("Connecting", "TCP/SSE handshake in progress"),
    "handshake_ok": ("Handshake OK", "Schema v{schema_version}"),
    "connected": ("Connected", "ready for next drop"),
    "streaming": ("Streaming", "{frame_index}/{total} frames received"),
    "computing": (
        "Analyzing telemetry",
        "classifier + anomaly + narrator running",
    ),
    "stalled": ("Stream stalled", "no frames received for ~{stalled_for_s}s"),
    "reconnecting": ("Reconnecting", "retry {retry_n}/3 — backing off"),
    "schema_mismatch": ("Schema version mismatch", "{error}"),
    "handshake_failed": ("Handshake failed", "{error}"),
    "session_rejected": ("Session rejected", "{reason}"),
    "redaction_failed": ("Redaction failed", "frame {frame_index}: {error}"),
    "live_disabled": (
        "Live mode paused by owner",
        "the owner has temporarily disabled live mode",
    ),
    "local_fallback": (
        "Local mode",
        "verdict computed on owner's laptop (Space was sleeping)",
    ),
    "complete": ("Connected — verdict delivered", "ready for next drop"),
}

# D-STATUS-22: privacy chip text shown during state=streaming.
_PRIVACY_CHIP = "redacted • BSSIDs hashed • no credentials"

# States that get the version strip (D-STATUS-19).
_VERSION_STATES = frozenset(
    {"handshake_ok", "connected", "streaming", "computing", "complete"}
)

# Allowlist of fields safe to format into the detail template. Anything not
# in this set is dropped — keeps owner_key / session_key out of rendered HTML
# (D-STATUS-13) even if the caller accidentally includes them.
_DETAIL_FIELDS = frozenset(
    {
        "schema_version",
        "frame_index",
        "total",
        "stalled_for_s",
        "retry_n",
        "error",
        "reason",
    }
)


def _safe_format(template: str, fields: dict[str, Any]) -> str:
    """Format ``template`` with ``fields``; on missing keys return the literal.

    HTML-escapes the formatted output so error / reason strings can't smuggle
    HTML into the banner. The template itself is trusted (defined above).
    """
    safe = {k: v for k, v in fields.items() if k in _DETAIL_FIELDS}
    try:
        rendered = template.format(**safe)
    except (KeyError, IndexError, ValueError):
        rendered = template
    return html.escape(rendered, quote=False)


def render_banner(state_dict: dict[str, Any] | None) -> str:
    """Render the connection-status banner HTML (UI-07).

    Parameters
    ----------
    state_dict
        Latest yield payload from ``src.space.live.status.OWNER_STREAM_STATE``
        for the active session. ``None`` or empty dict → renders the Idle
        state with the install CTA.

    Returns
    -------
    str
        HTML string with ``role="status"`` and ``aria-live="polite"``
        (D-STATUS-27). Never emits ``owner_key`` or ``session_key`` raw
        (D-STATUS-13).
    """
    if not state_dict:
        state = "idle"
        label, _detail_tpl = _STATE_TEXT["idle"]
        # Idle detail is the install CTA -- already-escaped HTML entities for
        # the placeholder angle brackets; don't double-escape.
        detail_html = _IDLE_COPY
        versions_html = ""
        privacy_html = ""
        extra_classes = ""
    else:
        state = str(state_dict.get("state") or "idle")
        label, detail_tpl = _STATE_TEXT.get(state, (state.replace("_", " ").title(), ""))
        detail_html = _safe_format(detail_tpl, state_dict) if detail_tpl else ""

        versions_html = ""
        if state in _VERSION_STATES:
            agent_v = html.escape(
                str(state_dict.get("agent_version", _DEFAULT_AGENT_VERSION))
            )
            schema_v = html.escape(
                str(state_dict.get("schema_version", _SCHEMA_VERSION))
            )
            versions_html = (
                f'<span class="conn-versions">'
                f"Space v{_SPACE_VERSION} • Agent v{agent_v} • Schema v{schema_v}"
                f"</span>"
            )

        privacy_html = ""
        if state == "streaming":
            privacy_html = f'<span class="conn-privacy">{_PRIVACY_CHIP}</span>'

        extra_classes = " conn-persistent" if state == "local_fallback" else ""

    state_class = html.escape(state)
    label_html = html.escape(label)
    return (
        f'<div class="conn-banner conn-{state_class}{extra_classes}" '
        f'role="status" aria-live="polite">'
        f'<span class="conn-state">{label_html}</span>'
        f'<span class="conn-detail">{detail_html}</span>'
        f"{versions_html}{privacy_html}"
        f"</div>"
    )
