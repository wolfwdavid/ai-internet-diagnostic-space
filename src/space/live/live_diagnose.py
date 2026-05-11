"""Phase 5 plan 05-01: ``live_diagnose`` Gradio generator (UI-07 server half).

Yields a sequence of status dicts over SSE that the agent transport (plan
05-02) and Live-tab banner (plan 05-03) both consume. State machine matches
D-STATUS-01..32 / D-STATUS-24 / D-STATUS-26 / D-STATUS-30 (CONTEXT.md):

  (handshake first)
    schema_mismatch          -- major version mismatch (terminal)
    handshake_failed         -- malformed handshake payload (terminal)
  (session gate)
    session_rejected         -- no valid owner_key and no valid pair_code (terminal)
    live_disabled            -- owner kill-switch set (terminal)
  (success-path stream)
    handshake_ok             -- first wire confirmation (D-STATUS-24)
    streaming (per frame)    -- one yield per frame; redaction_passed=True
    redaction_failed         -- defense-in-depth tripped (terminal, D-STATUS-26)
    computing                -- inference running (D-STATUS-17)
    complete                 -- final yield with full Verdict

Every yield ALSO updates ``OWNER_STREAM_STATE[session_key]`` so the Live-tab
banner's ``gr.Timer`` poller (plan 05-03) has the freshest state.

Module-level imports (Gotcha 7): ``InferenceOrchestrator`` instantiates at
import to load the classifier + anomaly joblib artifacts once per Space
process. ``redact_to_schema`` is imported at module load (not per-call) so
the regex compile cost is paid once.
"""
from __future__ import annotations

import json
from typing import Any, Iterator

from pydantic import ValidationError
from wifi_diag_schema import TelemetryFrame  # noqa: F401  (kept for type clarity)
from wifi_diag_schema.handshake import IncompatibleSchemaError

from src.space.inference import InferenceOrchestrator
from src.space.live import status
from src.space.live.handshake import server_handshake
from src.space.live.owner_session import (
    consume_pair_code,
    is_live_disabled,
    is_owner,
)
from src.space.live.redaction import redact_to_schema

__all__ = ["live_diagnose", "_ORCH", "_SPACE_VERSION"]


# Load classifier + anomaly detector once per Space process (Gotcha 7).
_ORCH = InferenceOrchestrator()
_SPACE_VERSION = "1.0.0"


def live_diagnose(
    handshake_json: str,
    frames_json_list: list[str],
    owner_key: str | None,
    pair_code: str | None,
) -> Iterator[dict[str, Any]]:
    """SSE generator: handshake -> session-gate -> per-frame redaction -> inference -> verdict.

    Args:
        handshake_json: JSON-encoded ``HandshakeFrame`` payload. First-wire
            schema-version check happens here (D-STATUS-24).
        frames_json_list: List of JSON-encoded TelemetryFrame-shaped dicts to
            run through the inference pipeline. Each is passed through
            ``redact_to_schema()`` server-side as Pitfall 6 defense-in-depth.
        owner_key: Caller-supplied owner key. Compared against the ``OWNER_KEY``
            env var (HF Space secret) by ``is_owner()``.
        pair_code: Caller-supplied pair code (D-LIVE-03). Single-use; consumed
            on first valid call.

    Yields:
        Status dicts with a ``state`` key matching the 9-state machine.
    """
    # ------------------------------------------------------------------
    # 1. Schema handshake -- first thing on the wire (D-STATUS-24).
    # ------------------------------------------------------------------
    try:
        compat, remote_ver = server_handshake(handshake_json)
    except IncompatibleSchemaError as e:
        yield {"state": "schema_mismatch", "error": str(e)}
        return
    except (ValidationError, ValueError, json.JSONDecodeError) as e:
        yield {"state": "handshake_failed", "error": f"malformed handshake: {e}"}
        return

    # ------------------------------------------------------------------
    # 2. Session gate: owner_key wins; else pair_code; else reject.
    # ------------------------------------------------------------------
    session_key: str
    if owner_key and is_owner(owner_key):
        session_key = f"owner:{owner_key[:8]}"
    elif pair_code and consume_pair_code(pair_code):
        session_key = f"pair:{pair_code}"
    else:
        yield {
            "state": "session_rejected",
            "reason": "no valid owner key or pair code",
        }
        return

    # ------------------------------------------------------------------
    # 3. Kill switch (D-STATUS-30).
    # ------------------------------------------------------------------
    if is_live_disabled():
        payload = {"state": "live_disabled", "session_key": session_key}
        status.update(session_key, payload)
        yield payload
        return

    # ------------------------------------------------------------------
    # 4. Handshake-OK yield (D-STATUS-24).
    # ------------------------------------------------------------------
    drift = "minor" if compat == "minor_drift" else "match"
    hs_payload: dict[str, Any] = {
        "state": "handshake_ok",
        "schema_version": remote_ver,
        "space_version": _SPACE_VERSION,
        "schema_drift": drift,
        "session_key": session_key,
    }
    status.update(session_key, hs_payload)
    yield hs_payload

    # ------------------------------------------------------------------
    # 5. Per-frame redaction + streaming yields (D-STATUS-26).
    # ------------------------------------------------------------------
    redacted: list[Any] = []
    n = len(frames_json_list)
    for i, fj in enumerate(frames_json_list):
        try:
            raw = json.loads(fj)
            tf = redact_to_schema(raw)
            redacted.append(tf)
        except Exception as e:  # noqa: BLE001 — surface ANY redaction failure
            failure = {
                "state": "redaction_failed",
                "frame_index": i,
                "error": str(e),
                "session_key": session_key,
            }
            status.update(session_key, failure)
            yield failure
            return
        streaming = {
            "state": "streaming",
            "frame_index": i + 1,
            "total": n,
            "redaction_passed": True,
            "session_key": session_key,
        }
        status.update(session_key, streaming)
        yield streaming

    # ------------------------------------------------------------------
    # 6. Inference (D-STATUS-17 Computing).
    # ------------------------------------------------------------------
    computing = {"state": "computing", "session_key": session_key}
    status.update(session_key, computing)
    yield computing

    verdict, anomaly_scores = _ORCH.diagnose(redacted)

    # ------------------------------------------------------------------
    # 7. Final verdict (terminal).
    # ------------------------------------------------------------------
    complete: dict[str, Any] = {
        "state": "complete",
        "verdict": verdict.model_dump(),
        "anomaly_scores": list(anomaly_scores),
        "session_key": session_key,
    }
    status.update(session_key, complete)
    yield complete
