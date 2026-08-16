"""Fail-closed helpers for ClipIt's canonical export-start contract."""

import re
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4


SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")


class ExportContractError(ValueError):
    """Raised when a canonical editor identity cannot be proven."""


def _non_empty_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def require_verified_editor_state(delivery_state: Any, clip_id: str) -> Dict[str, Any]:
    """Return the exact current editor identity or fail without exporting."""
    if not isinstance(delivery_state, dict):
        raise ExportContractError("Clip delivery-state response is invalid.")
    if (
        delivery_state.get("schema") != "clipit_clip_delivery_state"
        or delivery_state.get("version") != 2
        or delivery_state.get("clipId") != clip_id
    ):
        raise ExportContractError(
            "Clip delivery-state does not match the requested clip contract."
        )
    if delivery_state.get("editorStateStatus") != "verified":
        raise ExportContractError(
            "Clip has no verified current editor snapshot; save the clip before exporting."
        )

    editor_state = delivery_state.get("editorState")
    if not isinstance(editor_state, dict):
        raise ExportContractError("Clip returned no canonical editor snapshot.")
    snapshot_id = _non_empty_string(editor_state.get("snapshotId"))
    editor_version = editor_state.get("editorVersion")
    editor_state_hash = _non_empty_string(editor_state.get("editorStateHash"))
    if editor_state.get("stateSource") != "current_editor_snapshot":
        raise ExportContractError("Clip editor identity is not the current snapshot.")
    if not snapshot_id:
        raise ExportContractError("Clip editor snapshot ID is missing.")
    if (
        isinstance(editor_version, bool)
        or not isinstance(editor_version, int)
        or editor_version < 1
    ):
        raise ExportContractError("Clip editor version is invalid.")
    if not editor_state_hash or not SHA256_RE.fullmatch(editor_state_hash):
        raise ExportContractError("Clip editor state hash is invalid.")

    return {
        "snapshotId": snapshot_id,
        "editorVersion": editor_version,
        "editorStateHash": editor_state_hash,
    }


def resolve_export_idempotency_key(
    requested_key: Optional[str],
    request_body: Dict[str, Any],
) -> str:
    body_key = _non_empty_string(request_body.get("idempotencyKey"))
    requested_key = _non_empty_string(requested_key)
    if requested_key and body_key and requested_key != body_key:
        raise ExportContractError(
            "--idempotency-key conflicts with options-json idempotencyKey."
        )
    idempotency_key = requested_key or body_key or f"agent-pack-export:{uuid4()}"
    if (
        len(idempotency_key) < 8
        or len(idempotency_key) > 160
        or not IDEMPOTENCY_KEY_RE.fullmatch(idempotency_key)
    ):
        raise ExportContractError(
            "Export idempotency key must be 8-160 URL-safe characters."
        )
    return idempotency_key


def prepare_export_start_request(
    client: Any,
    clip_id: str,
    request_body: Dict[str, Any],
    requested_idempotency_key: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Pin an export request to the clip's exact current editor snapshot."""
    if not isinstance(request_body, dict):
        raise ExportContractError("Export request body must be an object.")
    existing_clip_id = _non_empty_string(request_body.get("clipId"))
    if existing_clip_id and existing_clip_id != clip_id:
        raise ExportContractError("Export request clipId conflicts with --clip-id.")

    delivery_state = client.get(f"/api/v1/clips/{clip_id}/delivery-state")
    editor_state = require_verified_editor_state(delivery_state, clip_id)
    expected_fields = {
        "expectedEditorVersion": editor_state["editorVersion"],
        "expectedEditorStateHash": editor_state["editorStateHash"],
    }
    for field, expected in expected_fields.items():
        if field in request_body and request_body[field] != expected:
            raise ExportContractError(
                f"Export request {field} conflicts with the current editor snapshot."
            )

    body = dict(request_body)
    body.update({
        "clipId": clip_id,
        "idempotencyKey": resolve_export_idempotency_key(
            requested_idempotency_key,
            request_body,
        ),
        **expected_fields,
    })
    return body, editor_state
