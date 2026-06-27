"""Owner-key + pair-code routing + kill switch (D-LIVE-02, D-LIVE-03, D-STATUS-30).

- ``is_owner(key)``: True iff the env-var ``OWNER_KEY`` is set AND matches.
- ``is_live_disabled()``: True iff env-var ``LIVE_DISABLED == '1'``.
- ``issue_pair_code(ttl_s)`` / ``consume_pair_code(code)``: in-memory pair-code
  registry (single-use, ~10 minute expiry by default).

The pair-code registry lives in module-level state -- per RESEARCH OQ-4 this
is acceptable at v1 (single-worker Space) with the caveat that adding
worker-replicas would require an external store (Redis, etc.).
"""

from __future__ import annotations

import os
import secrets
import threading
import time

__all__ = [
    "is_owner",
    "is_live_disabled",
    "issue_pair_code",
    "consume_pair_code",
]


def is_owner(key: str | None) -> bool:
    """Return True iff ``key`` equals the ``OWNER_KEY`` env var.

    Returns False if ``OWNER_KEY`` is unset/empty -- you cannot be the owner
    of a Space that has no configured owner key.
    """
    owner = os.environ.get("OWNER_KEY")
    return bool(owner) and key == owner


def is_live_disabled() -> bool:
    """Return True iff the owner has set ``LIVE_DISABLED=1`` (D-STATUS-30)."""
    return os.environ.get("LIVE_DISABLED") == "1"


# ---------------------------------------------------------------------------
# Pair-code registry (D-LIVE-03). Single-use, 10-minute default expiry.
# ---------------------------------------------------------------------------
_PAIR_LOCK = threading.Lock()
_PAIR_CODES: dict[str, float] = {}  # code -> expiry epoch seconds


def issue_pair_code(ttl_s: int = 600) -> str:
    """Mint a single-use pair code valid for ``ttl_s`` seconds.

    Code format: 8 uppercase alphanumeric characters (URL-safe minus dashes
    and underscores -- those would confuse copy/paste in chat).
    """
    raw = secrets.token_urlsafe(12)[:8].upper()
    code = raw.replace("-", "X").replace("_", "X")
    with _PAIR_LOCK:
        _PAIR_CODES[code] = time.time() + ttl_s
    return code


def consume_pair_code(code: str) -> bool:
    """Atomically remove a pair code from the registry and return True iff valid+unexpired."""
    if not code:
        return False
    with _PAIR_LOCK:
        exp = _PAIR_CODES.pop(code, None)
    return exp is not None and exp > time.time()
