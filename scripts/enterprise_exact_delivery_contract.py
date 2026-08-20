"""Fail-closed client contract for the idempotent enterprise delivery recipe."""

import re
from typing import Any, Dict, Optional

try:
    from .clipper_client import require_enterprise_workspace_scope
except ImportError:
    from clipper_client import require_enterprise_workspace_scope


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
TOOL_NAME = "deliverEnterpriseClipExact"
MEDIA_DURATION_TOLERANCE_SECONDS = 0.15


class EnterpriseExactDeliveryContractError(ValueError):
    """Raised when a recipe plan or receipt does not prove exact delivery."""


def _require_sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise EnterpriseExactDeliveryContractError(f"Recipe {field} is invalid.")
    return value


def _require_positive_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise EnterpriseExactDeliveryContractError(f"Recipe {field} is invalid.")
    return float(value)


def _execute_recipe_tool(client: Any, parameters: Dict[str, Any]) -> Dict[str, Any]:
    response = client.post(
        "/api/v1/agent/execute",
        {
            "functionName": TOOL_NAME,
            "parameters": parameters,
            "clipId": parameters["clipId"],
        },
    )
    if not isinstance(response, dict):
        raise EnterpriseExactDeliveryContractError(
            "ClipIt returned an invalid exact-delivery tool response."
        )
    if response.get("success") is not True:
        message = response.get("error")
        raise EnterpriseExactDeliveryContractError(
            message if isinstance(message, str) else "Exact-delivery tool failed."
        )
    result = response.get("result")
    if not isinstance(result, dict):
        raise EnterpriseExactDeliveryContractError(
            "ClipIt did not return an exact-delivery result."
        )
    return result


def require_enterprise_profile(client: Any, workspace_id: str) -> Dict[str, Any]:
    if getattr(client, "profile_name", "default") == "default":
        raise EnterpriseExactDeliveryContractError(
            "Exact enterprise delivery requires a named ClipIt profile."
        )
    return require_enterprise_workspace_scope(
        client.get_agent_identity(),
        expected_workspace_id=workspace_id,
    )


def require_exact_delivery_plan(
    plan: Any,
    workspace_id: str,
    request: Dict[str, Any],
) -> Dict[str, Any]:
    if (
        not isinstance(plan, dict)
        or plan.get("schema") != "clipit_enterprise_exact_delivery_plan"
        or plan.get("version") != 1
    ):
        raise EnterpriseExactDeliveryContractError(
            "ClipIt returned an unsupported exact-delivery plan."
        )
    _require_sha256(plan.get("planHash"), "plan hash")
    target = plan.get("target")
    if not isinstance(target, dict) or any((
        target.get("workspaceId") != workspace_id,
        target.get("clipId") != request["clipId"],
        target.get("editorVersion") != request["expectedEditorVersion"],
        target.get("editorStateHash") != request["expectedEditorStateHash"],
        target.get("clipSettingsRevision") != request["expectedClipSettingsRevision"],
    )):
        raise EnterpriseExactDeliveryContractError(
            "Exact-delivery plan target does not match the approved clip identity."
        )
    _require_sha256(target.get("sourceObjectFingerprint"), "source fingerprint")
    exact_style = plan.get("exactCaptionStyle")
    normalized = exact_style.get("style") if isinstance(exact_style, dict) else None
    if not isinstance(normalized, dict):
        raise EnterpriseExactDeliveryContractError(
            "Exact-delivery plan is missing normalized caption style."
        )
    for field, expected in request["captionStyle"].items():
        if normalized.get(field) != expected:
            raise EnterpriseExactDeliveryContractError(
                f"Exact-delivery plan changed approved caption field {field}."
            )
    _require_sha256(exact_style.get("styleHash"), "caption-style hash")
    capability = exact_style.get("capability")
    if not isinstance(capability, dict) or capability.get("unknownFields") != "rejected":
        raise EnterpriseExactDeliveryContractError(
            "Exact-delivery plan did not prove strict caption capability."
        )
    output_policy = plan.get("outputPolicy")
    if (
        not isinstance(output_policy, dict)
        or output_policy.get("includeOutro") is not request["includeOutro"]
    ):
        raise EnterpriseExactDeliveryContractError(
            "Exact-delivery plan changed the approved outro policy."
        )
    main_duration = _require_positive_number(
        output_policy.get("expectedMainDuration"), "main duration"
    )
    final_duration = _require_positive_number(
        output_policy.get("expectedFinalDuration"), "final duration"
    )
    expected_final_duration = main_duration + (4 if request["includeOutro"] else 0)
    if abs(final_duration - expected_final_duration) > 1e-6:
        raise EnterpriseExactDeliveryContractError(
            "Exact-delivery plan duration does not match its approved outro policy."
        )
    usage = plan.get("usage")
    if (
        not isinstance(usage, dict)
        or usage.get("settlementMode") != "enterprise_usage_only"
        or usage.get("clientCreditChargeClip") != 0
        or usage.get("maxCredits") != request["maxCredits"]
        or not isinstance(usage.get("withinApprovalCap"), bool)
    ):
        raise EnterpriseExactDeliveryContractError(
            "Exact-delivery plan did not prove usage-only settlement and cap."
        )
    approved = plan.get("approved")
    blockers = plan.get("blockers")
    if (
        not isinstance(approved, bool)
        or not isinstance(blockers, list)
        or any(not isinstance(blocker, str) or not blocker.strip() for blocker in blockers)
        or approved
        != (
            len(blockers) == 0
            and usage["withinApprovalCap"]
            and usage.get("spendLimitViolation") is None
        )
    ):
        raise EnterpriseExactDeliveryContractError(
            "Exact-delivery plan approval does not match its blockers and cap."
        )
    return plan


def preflight_enterprise_exact_delivery(
    client: Any,
    workspace_id: str,
    request: Dict[str, Any],
) -> Dict[str, Any]:
    require_enterprise_profile(client, workspace_id)
    plan = _execute_recipe_tool(client, {**request, "action": "preflight"})
    return require_exact_delivery_plan(plan, workspace_id, request)


def require_exact_delivery_receipt(
    receipt: Any,
    plan: Dict[str, Any],
    request: Dict[str, Any],
) -> Dict[str, Any]:
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema") != "clipit_enterprise_exact_delivery_receipt"
        or receipt.get("version") != 1
        or receipt.get("clipId") != request["clipId"]
        or receipt.get("planHash") != plan["planHash"]
        or receipt.get("captionStyleHash") != plan["exactCaptionStyle"]["styleHash"]
        or receipt.get("includeOutro") is not request["includeOutro"]
    ):
        raise EnterpriseExactDeliveryContractError(
            "ClipIt returned a receipt for a different exact-delivery plan."
        )
    state = receipt.get("state")
    if state not in ("processing", "completed", "blocked"):
        raise EnterpriseExactDeliveryContractError(
            "Exact-delivery receipt state is invalid."
        )
    lineage = receipt.get("lineage")
    if not isinstance(lineage, dict):
        raise EnterpriseExactDeliveryContractError(
            "Exact-delivery receipt is missing lineage proof."
        )
    expected_final_duration = _require_positive_number(
        lineage.get("expectedFinalDuration"), "receipt final duration"
    )
    if abs(expected_final_duration - plan["outputPolicy"]["expectedFinalDuration"]) > 1e-6:
        raise EnterpriseExactDeliveryContractError(
            "Exact-delivery receipt changed the approved final duration."
        )
    if state == "processing" and (
        not isinstance(receipt.get("resumeToken"), str)
        or receipt.get("error") is not None
    ):
        raise EnterpriseExactDeliveryContractError(
            "Processing receipt is missing its durable resume token."
        )
    if state == "blocked":
        error = receipt.get("error")
        if (
            not isinstance(receipt.get("resumeToken"), str)
            or not isinstance(error, dict)
            or not isinstance(error.get("code"), str)
            or not error["code"].strip()
            or not isinstance(error.get("message"), str)
            or not error["message"].strip()
        ):
            raise EnterpriseExactDeliveryContractError(
                "Blocked receipt is missing its durable token and typed error."
            )
    if state == "completed":
        if (
            receipt.get("stage") != "completed"
            or receipt.get("resumeToken") is not None
            or receipt.get("error") is not None
            or (
                receipt.get("renderJobId") is not None
                and not isinstance(receipt.get("renderJobId"), str)
            )
            or not isinstance(receipt.get("exportJobId"), str)
            or not isinstance(receipt.get("deliveryId"), str)
        ):
            raise EnterpriseExactDeliveryContractError(
                "Completed receipt is missing render, export, delivery, or lineage proof."
            )
        for field in (
            "editorStateHash",
            "outputObjectFingerprint",
        ):
            _require_sha256(lineage.get(field), field)
        duration = _require_positive_number(
            lineage.get("artifactDuration"), "verified artifact duration"
        )
        if abs(duration - expected_final_duration) > MEDIA_DURATION_TOLERANCE_SECONDS:
            raise EnterpriseExactDeliveryContractError(
                "Completed receipt artifact duration differs from the approved output."
            )
    return receipt


def advance_enterprise_exact_delivery(
    client: Any,
    plan: Dict[str, Any],
    request: Dict[str, Any],
    idempotency_key: Optional[str] = None,
    resume_token: Optional[str] = None,
) -> Dict[str, Any]:
    parameters = {
        **request,
        "action": "advance",
        "planHash": plan["planHash"],
    }
    if resume_token:
        parameters["resumeToken"] = resume_token
    elif idempotency_key:
        parameters["idempotencyKey"] = idempotency_key
    else:
        raise EnterpriseExactDeliveryContractError(
            "First advance requires an idempotency key; resume requires a token."
        )
    receipt = _execute_recipe_tool(client, parameters)
    return require_exact_delivery_receipt(receipt, plan, request)
