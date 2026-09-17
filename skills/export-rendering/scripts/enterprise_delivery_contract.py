"""Fail-closed helpers for exact enterprise ready-deliverable operations."""

import re
from typing import Any, Dict, Optional

try:
    from .clipper_client import ClipperError, require_enterprise_workspace_scope
except ImportError:
    from clipper_client import ClipperError, require_enterprise_workspace_scope


class EnterpriseDeliveryContractError(ValueError):
    """Raised when workspace delivery scope or response data is invalid."""


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MEDIA_DURATION_TOLERANCE_SECONDS = 0.15


def _non_empty_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def require_workspace_preflight(client: Any, expected_workspace_id: str) -> Dict[str, Any]:
    expected_workspace_id = _non_empty_string(expected_workspace_id)
    if not expected_workspace_id:
        raise EnterpriseDeliveryContractError("Expected workspace ID is required.")
    return require_enterprise_workspace_scope(
        client.get_agent_identity(),
        expected_workspace_id=expected_workspace_id,
    )


def _require_deliverable(
    value: Any,
    workspace_id: str,
    export_id: Optional[str] = None,
    required_status: Optional[str] = None,
    expectations: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise EnterpriseDeliveryContractError("Enterprise deliverable is invalid.")
    if value.get("workspaceId") != workspace_id:
        raise EnterpriseDeliveryContractError(
            "Enterprise deliverable belongs to a different workspace."
        )
    if export_id is not None and value.get("exportId") != export_id:
        raise EnterpriseDeliveryContractError(
            "Enterprise deliverable does not match the requested export."
        )
    if not _non_empty_string(value.get("id")):
        raise EnterpriseDeliveryContractError("Enterprise deliverable ID is missing.")
    if not _non_empty_string(value.get("clipId")):
        raise EnterpriseDeliveryContractError("Enterprise deliverable clip ID is missing.")
    if not _non_empty_string(value.get("exportId")):
        raise EnterpriseDeliveryContractError("Enterprise deliverable export ID is missing.")
    if value.get("status") not in ("ready", "selected"):
        raise EnterpriseDeliveryContractError(
            "Enterprise deliverable status is not ready or selected."
        )
    if required_status and value.get("status") != required_status:
        raise EnterpriseDeliveryContractError(
            f"Enterprise deliverable status is not {required_status}."
        )
    if expectations is not None:
        verification = value.get("verification")
        if not isinstance(verification, dict):
            raise EnterpriseDeliveryContractError(
                "Enterprise deliverable is missing exact verification."
            )
        exact_fields = set(expectations) - {"artifactDuration"}
        if any(verification.get(field) != expectations[field] for field in exact_fields):
            raise EnterpriseDeliveryContractError(
                "Enterprise deliverable verification does not match the exact export."
            )
        verified_duration = verification.get("artifactDuration")
        approved_duration = expectations.get("artifactDuration")
        if (
            isinstance(verified_duration, bool)
            or not isinstance(verified_duration, (int, float))
            or isinstance(approved_duration, bool)
            or not isinstance(approved_duration, (int, float))
            or abs(verified_duration - approved_duration)
            > MEDIA_DURATION_TOLERANCE_SECONDS
        ):
            raise EnterpriseDeliveryContractError(
                "Enterprise deliverable duration does not match the approved export."
            )
    return value


def _require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise EnterpriseDeliveryContractError(
            f"Completed export is missing exact {field}."
        )
    return value


def require_completed_export_expectations(
    client: Any,
    export_id: str,
) -> Dict[str, Any]:
    export = client.get(f"/api/v1/exports/{export_id}")
    if not isinstance(export, dict) or export.get("id") != export_id:
        raise EnterpriseDeliveryContractError(
            "ClipIt returned a different export than requested."
        )
    if export.get("status") != "completed":
        raise EnterpriseDeliveryContractError(
            "Only a completed export can become a ready deliverable."
        )
    enterprise_execution_id = _non_empty_string(export.get("enterpriseExecutionId"))
    snapshot_id = _non_empty_string(export.get("snapshotId"))
    editor_version = export.get("editorVersion")
    include_outro = export.get("includeOutro")
    artifact_duration = export.get("artifactDuration")
    approved_artifact_duration = export.get("approvedArtifactDuration")
    if not enterprise_execution_id:
        raise EnterpriseDeliveryContractError(
            "Completed export is missing enterprise execution lineage."
        )
    if not snapshot_id:
        raise EnterpriseDeliveryContractError(
            "Completed export is missing its canonical snapshot ID."
        )
    if isinstance(editor_version, bool) or not isinstance(editor_version, int) or editor_version < 1:
        raise EnterpriseDeliveryContractError(
            "Completed export is missing its canonical editor version."
        )
    if not isinstance(include_outro, bool):
        raise EnterpriseDeliveryContractError(
            "Completed export is missing its approved outro policy."
        )
    if (
        isinstance(artifact_duration, bool)
        or not isinstance(artifact_duration, (int, float))
        or artifact_duration <= 0
        or isinstance(approved_artifact_duration, bool)
        or not isinstance(approved_artifact_duration, (int, float))
        or approved_artifact_duration <= 0
        or abs(artifact_duration - approved_artifact_duration)
        > MEDIA_DURATION_TOLERANCE_SECONDS
    ):
        raise EnterpriseDeliveryContractError(
            "Completed export duration does not match its approved output policy."
        )
    return {
        "enterpriseExecutionId": enterprise_execution_id,
        "snapshotId": snapshot_id,
        "editorVersion": editor_version,
        "editorStateHash": _require_sha256(
            export.get("editorStateHash"), "editor-state hash"
        ),
        "outputObjectFingerprint": _require_sha256(
            export.get("outputObjectFingerprint"), "output object fingerprint"
        ),
        "captionStyleHash": _require_sha256(
            export.get("captionStyleHash"), "caption-style hash"
        ),
        "includeOutro": include_outro,
        "artifactDuration": approved_artifact_duration,
    }


def _list_params(
    status: Optional[str],
    export_id: Optional[str],
    limit: int,
    offset: int,
) -> Dict[str, Any]:
    if status not in (None, "ready", "selected"):
        raise EnterpriseDeliveryContractError("Status must be ready or selected.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise EnterpriseDeliveryContractError("Limit must be between 1 and 100.")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise EnterpriseDeliveryContractError("Offset must be zero or greater.")
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status
    if export_id:
        params["exportId"] = export_id
    return params


def _fetch_deliverables(
    client: Any,
    workspace_id: str,
    status: Optional[str] = None,
    export_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    params = _list_params(status, export_id, limit, offset)
    response = client.get("/api/v1/deliverables", params=params)
    if not isinstance(response, dict) or not isinstance(
        response.get("deliverables"), list
    ):
        raise EnterpriseDeliveryContractError(
            "Enterprise deliverables response is invalid."
        )
    deliverables = [
        _require_deliverable(
            item,
            workspace_id,
            export_id=export_id,
            required_status=status,
        )
        for item in response["deliverables"]
    ]
    total = response.get("total")
    if isinstance(total, bool) or not isinstance(total, int) or total < len(deliverables):
        raise EnterpriseDeliveryContractError(
            "Enterprise deliverables total is invalid."
        )
    return {
        "deliverables": deliverables,
        "total": total,
        "limit": response.get("limit", limit),
        "offset": response.get("offset", offset),
    }


def list_enterprise_deliverables(
    client: Any,
    expected_workspace_id: str,
    status: Optional[str] = None,
    export_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    scope = require_workspace_preflight(client, expected_workspace_id)
    return _fetch_deliverables(
        client,
        scope["workspaceId"],
        status=status,
        export_id=_non_empty_string(export_id),
        limit=limit,
        offset=offset,
    )


def deliver_export_to_client(
    client: Any,
    expected_workspace_id: str,
    export_id: str,
) -> Dict[str, Any]:
    """Create one exact ready delivery; never select or label it on the client's behalf."""
    scope = require_workspace_preflight(client, expected_workspace_id)
    workspace_id = scope["workspaceId"]
    export_id = _non_empty_string(export_id)
    if not export_id:
        raise EnterpriseDeliveryContractError("Export ID is required.")
    expectations = require_completed_export_expectations(client, export_id)
    body: Dict[str, Any] = {
        "exportId": export_id,
        "expectations": expectations,
    }
    try:
        response = client.post("/api/v1/deliverables", body)
    except ClipperError as error:
        if error.status_code != 409 or error.code != "DELIVERY_EXISTS":
            raise
        existing = _fetch_deliverables(
            client,
            workspace_id,
            export_id=export_id,
            limit=2,
            offset=0,
        )["deliverables"]
        if len(existing) != 1:
            raise EnterpriseDeliveryContractError(
                "Existing delivery could not be resolved uniquely after DELIVERY_EXISTS."
            ) from error
        _require_deliverable(
            existing[0],
            workspace_id,
            export_id=export_id,
            expectations=expectations,
        )
        return {"deliverable": existing[0], "replayed": True}

    if not isinstance(response, dict):
        raise EnterpriseDeliveryContractError(
            "Enterprise delivery creation response is invalid."
        )
    deliverable = _require_deliverable(
        response.get("deliverable"),
        workspace_id,
        export_id=export_id,
        required_status="ready",
        expectations=expectations,
    )
    return {"deliverable": deliverable, "replayed": False}
