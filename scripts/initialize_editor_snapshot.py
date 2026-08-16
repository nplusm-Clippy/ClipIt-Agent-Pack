#!/usr/bin/env python3
"""Initialize a canonical editor snapshot for an enterprise workspace clip."""

import argparse

from clipper_client import (
    ClipperClient,
    main_wrapper,
    print_json,
    require_enterprise_workspace_scope,
)


def initialize_editor_snapshot(
    client,
    workspace_id,
    clip_id,
    aspect_ratio="9:16",
    fit_background="blur",
    quality="high",
    include_captions=False,
    caption_style="minimal",
):
    if client.profile_name == "default":
        raise RuntimeError(
            "Enterprise workspace operations require a named ClipIt profile."
        )
    scope = require_enterprise_workspace_scope(
        client.get_agent_identity(),
        expected_workspace_id=workspace_id,
    )
    response = client.post(
        f"/api/v1/clips/{clip_id}/editor-snapshot/initialize",
        {
            "aspectRatio": aspect_ratio,
            "fitBackground": fit_background,
            "quality": quality,
            "includeCaptions": include_captions,
            "captionStyle": caption_style,
        },
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
    caption_preset_id = response.get("captionPresetId")
    if include_captions and not isinstance(caption_preset_id, str):
        raise RuntimeError("ClipIt did not return the canonical caption preset.")
    if not include_captions and caption_preset_id is not None:
        raise RuntimeError("ClipIt unexpectedly enabled a canonical caption preset.")
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
    parser.add_argument(
        "--caption-style",
        default="minimal",
        choices=["bold", "minimal", "neon", "classic"],
        help="Canonical caption style (default: minimal)",
    )
    args = parser.parse_args()

    client = ClipperClient(profile=args.profile)
    print_json(initialize_editor_snapshot(
        client,
        args.workspace_id,
        args.clip_id,
        aspect_ratio=args.aspect_ratio,
        fit_background=args.fit_background,
        quality=args.quality,
        include_captions=args.include_captions,
        caption_style=args.caption_style,
    ))


if __name__ == "__main__":
    main()
