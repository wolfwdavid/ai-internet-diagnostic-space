"""Module-level owner-stream state, polled by the Live-tab banner (RESEARCH OQ-4).

Plan 05-03's Live-tab banner reads ``snapshot(session_key)`` on a ``gr.Timer``
tick to render the 9-state machine. Plan 05-01's ``live_diagnose`` generator
calls ``update(session_key, payload)`` on every yield.

Thread-safe via a single module-level ``Lock`` -- writes from the generator
thread, reads from the banner-poller thread. The state dict is intentionally
in-process (not Redis-backed): RESEARCH OQ-4 documents that v1 ships
single-worker on free CPU; multi-worker would require an external store.
"""
from __future__ import annotations

import threading
from typing import Any

__all__ = ["OWNER_STREAM_STATE", "update", "snapshot", "clear"]

_LOCK = threading.Lock()
OWNER_STREAM_STATE: dict[str, dict[str, Any]] = {}  # session_key -> latest yield


def update(session_key: str, state: dict[str, Any]) -> None:
    """Replace the latest state for ``session_key`` with a copy of ``state``."""
    with _LOCK:
        OWNER_STREAM_STATE[session_key] = dict(state)


def snapshot(session_key: str) -> dict[str, Any] | None:
    """Return a defensive copy of the latest state for ``session_key`` (or None)."""
    with _LOCK:
        s = OWNER_STREAM_STATE.get(session_key)
        return dict(s) if s else None


def clear(session_key: str) -> None:
    """Remove the state entry for ``session_key`` (idempotent)."""
    with _LOCK:
        OWNER_STREAM_STATE.pop(session_key, None)
