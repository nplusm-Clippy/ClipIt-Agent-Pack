#!/usr/bin/env python3
"""Initialize a canonical editor snapshot for an enterprise workspace clip."""

import argparse

from clipper_client import (
    ClipperClient,
    main_wrapper,
    print_json,
    require_enterprise_workspace_scope,
)
from exact_caption_style_contract import (
    ExactCaptionStyleContractError,
    parse_json_object,
    require_exact_caption_style_readback,
)


def initialize_editor_snapshot(
    client,
    workspace_id,
    clip_id,
    aspect_ratio="9:16",
    fit_background="blur",
    quality="high",
    include_captions=False,
    caption_style=None,
    caption_preset_id=None,
):
    if client.profile_name == "default":
        raise RuntimeError(
            "Enterprise workspace operations require a named ClipIt profile."
        )
    scope = require_enterprise_workspace_scope(
        client.get_agent_identity(),
        expected_workspace_id=workspace_id,
    )
    body = {
        "aspectRatio": aspect_ratio,
        "fitBackground": fit_background,
        "quality": quality,
        "includeCaptions": include_captions,
    }
    if include_captions and caption_style is not None:
        body["captionStyle"] = caption_style
    if include_captions and caption_preset_id is not None:
        body["captionPresetId"] = caption_preset_id
    response = client.post(
        f"/api/v1/clips/{clip_id}/editor-snapshot/initialize",
        body,
    )
    if not isinstance(response, dict):
        raise RuntimeError("ClipIt returned an invalid editor snapshot response.")
    if response.get("clipId") != clip_id:
        raise RuntimeError("ClipIt initialized a different clip than requested.")
    if not isinstance(response.get("editorVersion"), int):
        raise RuntimeError("ClipIt did not return a canonical editor version.")
    if not isinstance(response.get("editorStateHash"), str):
        raise RuntimeError("ClipIt did not return a canonical editor state hash.")
    if response.get("captionsEnabled") is not include_captions:
        raise RuntimeError("ClipIt initialized different caption settings than requested.")
    returned_caption_preset_id = response.get("captionPresetId")
    if not include_captions and returned_caption_preset_id is not None:
        raise RuntimeError("ClipIt unexpectedly enabled a canonical caption preset.")
    if caption_preset_id is not None and returned_caption_preset_id != caption_preset_id:
        raise RuntimeError("ClipIt initialized a different caption preset than requested.")
    if include_captions:
        require_exact_caption_style_readback(
            response,
            clip_id,
            caption_style if isinstance(caption_style, dict) else {},
        )
    return {
        **response,
        "workspaceId": scope["workspaceId"],
        "workspaceName": scope["workspaceName"],
        "profile": client.profile_name,
    }


@main_wrapper
def main():
    parser = argparse.ArgumentParser(
        description="Initialize an enterprise clip's canonical editor snapshot"
    )
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--clip-id", required=True)
    parser.add_argument("--profile", help="Named ClipIt CLI profile")
    parser.add_argument(
        "--aspect-ratio",
        default="9:16",
        choices=["16:9", "9:16", "1:1", "4:5"],
    )
    parser.add_argument(
        "--fit-background",
        default="blur",
        choices=["black", "blur"],
    )
    parser.add_argument(
        "--quality",
        default="high",
        choices=["standard", "high", "4k"],
    )
    captions = parser.add_mutually_exclusive_group()
    captions.add_argument(
        "--captions",
        dest="include_captions",
        action="store_true",
        help="Initialize canonical captions (requires a transcript)",
    )
    captions.add_argument(
        "--no-captions",
        dest="include_captions",
        action="store_false",
        help="Initialize without captions (default)",
    )
    parser.set_defaults(include_captions=False)
    style = parser.add_mutually_exclusive_group()
    style.add_argument(
        "--caption-style",
        choices=["bold", "minimal", "neon", "classic"],
        help="Legacy coarse caption style",
    )
    style.add_argument(
        "--caption-preset-id",
        choices=[
            "hormozi",
            "mrbeast",
            "minimal-white",
            "netflix",
            "tiktok-viral",
            "podcast",
            "gaming-neon",
            "karaoke",
        ],
        help="Named canonical caption preset",
    )
    style.add_argument(
        "--caption-style-json",
        help="Exact style JSON object or @path/to/style.json",
    )
    args = parser.parse_args()

    caption_style = args.caption_style
    if args.caption_style_json:
        try:
            caption_style = parse_json_object(args.caption_style_json)
        except ExactCaptionStyleContractError as exc:
            parser.error(str(exc))
    if not args.include_captions and (
        caption_style is not None or args.caption_preset_id is not None
    ):
        parser.error("caption style options require --captions")

    client = ClipperClient(profile=args.profile)
    print_json(initialize_editor_snapshot(
        client,
        args.workspace_id,
        args.clip_id,
        aspect_ratio=args.aspect_ratio,
        fit_background=args.fit_background,
        quality=args.quality,
        include_captions=args.include_captions,
        caption_style=caption_style,
        caption_preset_id=args.caption_preset_id,
    ))


if __name__ == "__main__":
    main()
