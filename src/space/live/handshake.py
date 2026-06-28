"""Server-side schema handshake wrapper (D-STATUS-24 + D-STATUS-05).

Thin facade around ``wifi_diag_schema.handshake.check_compatibility``: validates
the incoming HandshakeFrame, runs the version compatibility check, and returns
``(result, remote_schema_version)`` on success. On major-version mismatch,
``check_compatibility`` raises ``IncompatibleSchemaError`` -- the caller
(``live_diagnose``) catches it and yields ``state=schema_mismatch``.
"""

from __future__ import annotations

from typing import Literal

from wifi_diag_schema.handshake import (
    HandshakeFrame,
    IncompatibleSchemaError,
    check_compatibility,
)
from wifi_diag_schema.version import SCHEMA_VERSION

__all__ = [
    "server_handshake",
    "HandshakeFrame",
    "IncompatibleSchemaError",
    "SCHEMA_VERSION",
]


def server_handshake(payload_json: str) -> tuple[Literal["match", "minor_drift"], str]:
    """Validate handshake JSON and compare schema versions.

    Args:
        payload_json: JSON-encoded ``HandshakeFrame`` from the agent.

    Returns:
        ``(compat_result, remote_schema_version)`` where ``compat_result`` is
        either ``"match"`` (compatible) or ``"minor_drift"`` (compatible with
        a UserWarning emitted by ``check_compatibility``).

    Raises:
        IncompatibleSchemaError: major-version mismatch.
        pydantic.ValidationError: malformed handshake JSON.
    """
    hs = HandshakeFrame.model_validate_json(payload_json)
    result = check_compatibility(SCHEMA_VERSION, hs.schema_version)
    return result, hs.schema_version
