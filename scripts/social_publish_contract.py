"""Fail-closed helpers for ClipIt's exact social publishing contract."""

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple


SUPPORTED_PLATFORMS = {
    "youtube",
    "tiktok",
    "instagram",
    "facebook",
    "linkedin",
    "twitter",
    "bluesky",
    "threads",
    "pinterest",
    "reddit",
    "telegram",
    "snapchat",
    "gmb",
}
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


class SocialPublishContractError(ValueError):
    """Raised when exact artifact or account authority cannot be proven."""


def normalize_platform(value: str) -> str:
    platform = str(value).strip().lower()
    if platform == "x":
        platform = "twitter"
    if platform not in SUPPORTED_PLATFORMS:
        raise SocialPublishContractError(f"Unsupported social platform: {value}")
    return platform


def parse_platforms(value: str) -> List[str]:
    platforms = []
    for raw_platform in str(value).split(","):
        if not raw_platform.strip():
            continue
        platform = normalize_platform(raw_platform)
        if platform not in platforms:
            platforms.append(platform)
    if not platforms:
        raise SocialPublishContractError("At least one social platform is required.")
    return platforms


def parse_account_id_pins(value: Optional[str]) -> Dict[str, str]:
    if not value or not value.strip():
        return {}
    raw = value.strip()
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SocialPublishContractError(f"Invalid --account-ids JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise SocialPublishContractError("--account-ids JSON must be an object.")
        entries = parsed.items()
    else:
        pairs: List[Tuple[str, str]] = []
        for item in raw.split(","):
            platform, separator, account_id = item.partition("=")
            if not separator:
                raise SocialPublishContractError(
                    "--account-ids must use platform=accountId pairs."
                )
            pairs.append((platform, account_id))
        entries = pairs

    pins: Dict[str, str] = {}
    for raw_platform, raw_account_id in entries:
        platform = normalize_platform(raw_platform)
        if not isinstance(raw_account_id, str) or not raw_account_id.strip():
            raise SocialPublishContractError(
                f"Account ID for {platform} must not be empty."
            )
        pins[platform] = raw_account_id.strip()
    return pins


def is_enterprise_key(agent_identity: Any) -> bool:
    if not isinstance(agent_identity, dict):
        return False
    api_key = agent_identity.get("apiKey")
    if not isinstance(api_key, dict):
        return False
    agent_info = api_key.get("agentInfo")
    return (
        isinstance(agent_info, dict)
        and agent_info.get("type") == "enterprise_hermes"
    )


def require_exact_current_delivery_state(
    delivery_state: Any,
    clip_id: str,
    requested_export_id: Optional[str] = None,
) -> Dict[str, str]:
    if not isinstance(delivery_state, dict):
        raise SocialPublishContractError("Clip delivery-state response is invalid.")
    editor = delivery_state.get("editorState")
    selection = delivery_state.get("selection")
    selected = delivery_state.get("selectedExport")
    if not all(isinstance(value, dict) for value in (editor, selection, selected)):
        raise SocialPublishContractError(
            "Clip does not have one selected exact-current export."
        )

    response_requested_export_id = selection.get("requestedExportId")
    blockers = delivery_state.get("deliveryBlockers")
    selected_blockers = selected.get("blockers")
    output_fingerprint = selected.get("outputObjectFingerprint")
    export_id = selected.get("exportId")
    editor_state_hash = editor.get("editorStateHash")
    exact = (
        delivery_state.get("schema") == "clipit_clip_delivery_state"
        and delivery_state.get("version") == 2
        and delivery_state.get("clipId") == clip_id
        and delivery_state.get("editorStateStatus") == "verified"
        and editor.get("stateSource") == "current_editor_snapshot"
        and isinstance(editor.get("snapshotId"), str)
        and bool(editor.get("snapshotId"))
        and isinstance(editor_state_hash, str)
        and bool(SHA256_RE.fullmatch(editor_state_hash))
        and selection.get("status") == "selected"
        and isinstance(export_id, str)
        and bool(export_id)
        and selection.get("selectedExportId") == export_id
        and response_requested_export_id == requested_export_id
        and (not requested_export_id or export_id == requested_export_id)
        and selected.get("snapshotId") == editor.get("snapshotId")
        and selected.get("editorVersion") == editor.get("editorVersion")
        and selected.get("editorStateHash") == editor_state_hash
        and selected.get("exactlyMatchesEditor") is True
        and selected.get("inspectionStatus") == "verified"
        and isinstance(output_fingerprint, str)
        and bool(SHA256_RE.fullmatch(output_fingerprint))
        and selected_blockers == []
        and delivery_state.get("readyToPublish") is True
        and blockers == []
    )
    if not exact:
        detail = " ".join(blockers) if isinstance(blockers, list) and blockers else ""
        raise SocialPublishContractError(
            "Clip does not have one verified exact-current export."
            + (f" {detail}" if detail else "")
        )

    return {
        "exportId": export_id,
        "expectedSnapshotId": editor["snapshotId"],
        "expectedOutputObjectFingerprint": output_fingerprint,
    }


def select_expected_account_ids(
    platforms: Iterable[str],
    accounts_response: Any,
    requested_account_ids: Optional[Dict[str, str]] = None,
    enterprise: bool = False,
) -> Dict[str, str]:
    normalized_platforms = [normalize_platform(platform) for platform in platforms]
    if enterprise and len(normalized_platforms) != 1:
        raise SocialPublishContractError(
            "Enterprise publishing requires one exact platform/account per request."
        )
    requested: Dict[str, str] = {}
    for raw_platform, raw_account_id in (requested_account_ids or {}).items():
        platform = normalize_platform(raw_platform)
        if not isinstance(raw_account_id, str) or not raw_account_id.strip():
            raise SocialPublishContractError(
                f"Account ID for {platform} must not be empty."
            )
        requested[platform] = raw_account_id.strip()
    unexpected_pins = set(requested) - set(normalized_platforms)
    if unexpected_pins:
        raise SocialPublishContractError(
            "Account pins were provided for unrequested platforms: "
            + ", ".join(sorted(unexpected_pins))
        )

    raw_accounts = (
        accounts_response.get("accounts")
        if isinstance(accounts_response, dict)
        else None
    )
    if not isinstance(raw_accounts, list):
        raise SocialPublishContractError("Social accounts response is invalid.")

    connected: Dict[str, List[str]] = {}
    for account in raw_accounts:
        if not isinstance(account, dict) or account.get("connected") is not True:
            continue
        account_id = account.get("accountId")
        if not isinstance(account_id, str) or not account_id.strip():
            continue
        try:
            platform = normalize_platform(account.get("platform", ""))
        except SocialPublishContractError:
            continue
        choices = connected.setdefault(platform, [])
        account_id = account_id.strip()
        if account_id not in choices:
            choices.append(account_id)

    expected: Dict[str, str] = {}
    for platform in normalized_platforms:
        choices = connected.get(platform, [])
        requested_account_id = requested.get(platform)
        if requested_account_id:
            if requested_account_id not in choices:
                raise SocialPublishContractError(
                    f"The selected {platform} account ID is not connected or granted."
                )
            expected[platform] = requested_account_id
            continue
        if len(choices) == 1:
            expected[platform] = choices[0]
            continue
        reason = "no connected/granted account" if not choices else "multiple connected/granted accounts"
        raise SocialPublishContractError(
            f"{platform} has {reason}. Run list_social_accounts.py and pass its exact accountId."
        )
    return expected


def prepare_social_publish_request(
    client: Any,
    *,
    clip_id: str,
    platforms: List[str],
    caption: str,
    requested_account_ids: Optional[Dict[str, str]] = None,
    requested_export_id: Optional[str] = None,
    title: Optional[str] = None,
    hashtags: Optional[List[str]] = None,
    scheduled_for: Optional[str] = None,
    enterprise_deliverable_id: Optional[str] = None,
) -> Dict[str, Any]:
    identity = client.get("/api/v1/agent/me")
    enterprise = is_enterprise_key(identity)
    normalized_platforms = [normalize_platform(platform) for platform in platforms]
    if enterprise and len(normalized_platforms) != 1:
        raise SocialPublishContractError(
            "Enterprise publishing requires one exact platform/account per request."
        )

    delivery_params = (
        {"exportId": requested_export_id} if requested_export_id else None
    )
    delivery_state = client.get(
        f"/api/v1/clips/{clip_id}/delivery-state",
        params=delivery_params,
    )
    artifact = require_exact_current_delivery_state(
        delivery_state,
        clip_id,
        requested_export_id,
    )
    accounts_response = client.get("/api/v1/social/accounts")
    expected_account_ids = select_expected_account_ids(
        normalized_platforms,
        accounts_response,
        requested_account_ids=requested_account_ids,
        enterprise=enterprise,
    )

    body: Dict[str, Any] = {
        "clipId": clip_id,
        "platforms": normalized_platforms,
        "caption": caption,
        **artifact,
        "expectedAccountIds": expected_account_ids,
        "publishExactCurrentArtifact": True,
    }
    optional_fields = {
        "title": title,
        "hashtags": hashtags,
        "scheduledFor": scheduled_for,
        "enterpriseDeliverableId": enterprise_deliverable_id,
    }
    for key, value in optional_fields.items():
        if value is not None:
            body[key] = value
    return body
