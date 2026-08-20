"""Fail-closed helpers for ClipIt's exact canonical caption-style contract."""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from .clipper_client import require_enterprise_workspace_scope
except ImportError:
    from clipper_client import require_enterprise_workspace_scope


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CAPTION_STYLE_DIRECTIVE_PATTERN = re.compile(
    r"^[ \t]*[Cc][Aa][Pp][Tt][Ii][Oo][Nn][Ss]?[ \t]+[Ss][Ii][Zz][Ee][ \t]+"
    r"(?P<percent>(?:[5-9][0-9](?:\.[0-9]+)?|[12][0-9]{2}(?:\.[0-9]+)?|300(?:\.0+)?))"
    r"[ \t]*%[ \t]+"
    r"(?P<layout>(?:[Aa][Uu][Tt][Oo]|[Ss][Tt][Aa][Cc][Kk][Ee][Dd]|"
    r"[Ss][Ii][Nn][Gg][Ll][Ee](?:[ \t]*-[ \t]*[Ll][Ii][Nn][Ee]|[ \t]+[Ll][Ii][Nn][Ee])?))"
    r"\.?[ \t]*\Z",
)


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


def parse_caption_style_directive(value: str) -> Dict[str, Any]:
    match = CAPTION_STYLE_DIRECTIVE_PATTERN.fullmatch(value)
    if len(value) > 80 or not match:
        raise ExactCaptionStyleContractError(
            "Caption directive must use the exact form "
            "'caption size <50-300>% <auto|single|single-line|stacked>'."
        )
    percent = float(match.group("percent"))
    if percent < 50 or percent > 300:
        raise ExactCaptionStyleContractError(
            "Caption size percentage must be between 50% and 300%."
        )
    layout = match.group("layout").lower()
    return {
        "fontSizeScale": percent / 100,
        "captionLineMode": "single-line" if layout.startswith("single") else layout,
    }


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
    style: Optional[Dict[str, Any]],
    expected_editor_version: int,
    expected_editor_state_hash: str,
    expected_clip_settings_revision: int,
    directive: Optional[str] = None,
) -> Dict[str, Any]:
    if (style is None) == (directive is None):
        raise ExactCaptionStyleContractError(
            "Provide exactly one exact caption style object or caption directive."
        )
    if style is not None:
        requested_style = style
    else:
        assert directive is not None
        requested_style = parse_caption_style_directive(directive)
    if getattr(client, "profile_name", "default") == "default":
        raise ExactCaptionStyleContractError(
            "Enterprise workspace operations require a named ClipIt profile."
        )
    scope = require_enterprise_workspace_scope(
        client.get_agent_identity(),
        expected_workspace_id=workspace_id,
    )
    body = {
        "expectedEditorVersion": expected_editor_version,
        "expectedEditorStateHash": expected_editor_state_hash,
        "expectedClipSettingsRevision": expected_clip_settings_revision,
    }
    if style is not None:
        body["captionStyle"] = style
    else:
        body["captionDirective"] = directive
    response = client.patch(
        f"/api/v1/clips/{clip_id}/editor-snapshot/caption-style",
        body,
    )
    exact = require_exact_caption_style_readback(response, clip_id, requested_style)
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
