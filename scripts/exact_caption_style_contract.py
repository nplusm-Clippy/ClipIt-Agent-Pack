"""Fail-closed helpers for ClipIt's exact canonical caption-style contract."""

import json
import re
from pathlib import Path
from typing import Any, Dict

try:
    from .clipper_client import require_enterprise_workspace_scope
except ImportError:
    from clipper_client import require_enterprise_workspace_scope


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ExactCaptionStyleContractError(ValueError):
    """Raised when an exact caption-style request or readback is invalid."""


def parse_json_object(value: str) -> Dict[str, Any]:
    source = value
    if value.startswith("@"):
        try:
            source = Path(value[1:]).read_text(encoding="utf-8")
        except OSError as exc:
            raise ExactCaptionStyleContractError(
                f"Could not read exact caption style file: {exc}"
            ) from exc
    try:
        parsed = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ExactCaptionStyleContractError(
            f"Exact caption style must be valid JSON: {exc}"
        ) from exc
    if not isinstance(parsed, dict):
        raise ExactCaptionStyleContractError(
            "Exact caption style must be a JSON object."
        )
    return parsed


def require_exact_caption_style_readback(
    response: Any,
    clip_id: str,
    requested_style: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(response, dict):
        raise ExactCaptionStyleContractError(
            "ClipIt returned an invalid exact caption-style response."
        )
    if response.get("clipId") != clip_id:
        raise ExactCaptionStyleContractError(
            "ClipIt returned exact caption style for a different clip."
        )
    normalized = response.get("captionStyle")
    if not isinstance(normalized, dict):
        raise ExactCaptionStyleContractError(
            "ClipIt did not return the normalized exact caption style."
        )
    for field, expected in requested_style.items():
        if normalized.get(field) != expected:
            raise ExactCaptionStyleContractError(
                f"ClipIt normalized caption field {field} differently than requested."
            )
    caption_style_hash = response.get("captionStyleHash")
    if not isinstance(caption_style_hash, str) or not SHA256_PATTERN.fullmatch(
        caption_style_hash
    ):
        raise ExactCaptionStyleContractError(
            "ClipIt did not return a canonical exact caption-style hash."
        )
    return response


def set_exact_caption_style(
    client: Any,
    workspace_id: str,
    clip_id: str,
    style: Dict[str, Any],
    expected_editor_version: int,
    expected_editor_state_hash: str,
    expected_clip_settings_revision: int,
) -> Dict[str, Any]:
    if getattr(client, "profile_name", "default") == "default":
        raise ExactCaptionStyleContractError(
            "Enterprise workspace operations require a named ClipIt profile."
        )
    scope = require_enterprise_workspace_scope(
        client.get_agent_identity(),
        expected_workspace_id=workspace_id,
    )
    response = client.patch(
        f"/api/v1/clips/{clip_id}/editor-snapshot/caption-style",
        {
            "expectedEditorVersion": expected_editor_version,
            "expectedEditorStateHash": expected_editor_state_hash,
            "expectedClipSettingsRevision": expected_clip_settings_revision,
            "captionStyle": style,
        },
    )
    exact = require_exact_caption_style_readback(response, clip_id, style)
    if exact.get("schema") != "clipit_exact_caption_style" or exact.get("version") != 1:
        raise ExactCaptionStyleContractError(
            "ClipIt returned an unsupported exact caption-style contract."
        )
    if exact.get("renderQueued") is not False:
        raise ExactCaptionStyleContractError(
            "Caption-style mutation unexpectedly started a render."
        )
    capability = exact.get("capability")
    if not isinstance(capability, dict) or capability.get("unknownFields") != "rejected":
        raise ExactCaptionStyleContractError(
            "ClipIt did not prove its strict exact caption-style capability."
        )
    return {
        **exact,
        "workspaceId": scope["workspaceId"],
        "workspaceName": scope["workspaceName"],
        "profile": client.profile_name,
    }
