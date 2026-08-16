"""Fail-closed helpers for enterprise ready-deliverable operations."""

from typing import Any, Dict, Optional

try:
    from .clipper_client import ClipperError, require_enterprise_workspace_scope
except ImportError:
    from clipper_client import ClipperError, require_enterprise_workspace_scope


class EnterpriseDeliveryContractError(ValueError):
    """Raised when workspace delivery scope or response data is invalid."""


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
    return value


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
    title: str,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a ready delivery; never select on the client's behalf."""
    scope = require_workspace_preflight(client, expected_workspace_id)
    workspace_id = scope["workspaceId"]
    export_id = _non_empty_string(export_id)
    title = _non_empty_string(title)
    if not export_id:
        raise EnterpriseDeliveryContractError("Export ID is required.")
    if not title or len(title) > 255:
        raise EnterpriseDeliveryContractError("Title must be 1-255 characters.")
    if note is not None:
        note = note.strip()
        if len(note) > 2000:
            raise EnterpriseDeliveryContractError(
                "Note must not exceed 2,000 characters."
            )
        note = note or None

    body: Dict[str, Any] = {"exportId": export_id, "title": title}
    if note is not None:
        body["note"] = note
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
    )
    return {"deliverable": deliverable, "replayed": False}
