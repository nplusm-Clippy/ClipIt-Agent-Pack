#!/usr/bin/env python3
"""Render a clip via AWS Lambda (Remotion). Returns a downloadable video.

Usage:
  python render_clip.py --clip-id <id> [--aspect-ratio 9:16] [--quality high]
  [--captions] [--no-captions] [--caption-style bold] [--watermark]
  [--no-auto-reframe] [--workspace-id <id>] [--profile <name>] [--wait]
"""

import argparse
from clipper_client import (
    ClipperClient,
    main_wrapper,
    print_json,
    require_enterprise_workspace_scope,
)


CAPTION_STYLES = {"bold", "minimal", "neon", "classic"}


def render_clip(
    client,
    clip_id,
    body,
    workspace_id=None,
):
    if workspace_id:
        if client.profile_name == "default":
            raise RuntimeError(
                "Enterprise workspace renders require a named ClipIt profile."
            )
        if not isinstance(body.get("includeCaptions"), bool):
            raise RuntimeError(
                "Enterprise workspace renders require an explicit caption choice."
            )
        if body.get("captionStyle") not in CAPTION_STYLES:
            raise RuntimeError(
                "Enterprise workspace renders require an explicit caption style."
            )
        if body.get("autoReframe") is not False:
            raise RuntimeError(
                "Enterprise canonical renders require auto reframing to be disabled."
            )
        require_enterprise_workspace_scope(
            client.get_agent_identity(),
            expected_workspace_id=workspace_id,
        )
    return client.post(f"/api/v1/clips/{clip_id}/render", body)


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Render a clip")
    parser.add_argument("--clip-id", required=True, help="Clip ID to render")
    parser.add_argument("--workspace-id", help="Expected enterprise workspace ID")
    parser.add_argument("--profile", help="Named ClipIt CLI profile")
    parser.add_argument("--aspect-ratio", default="9:16", choices=["16:9", "9:16", "1:1", "4:5"])
    parser.add_argument("--quality", default="high", choices=["standard", "high", "4k"])
    captions = parser.add_mutually_exclusive_group()
    captions.add_argument(
        "--captions",
        dest="include_captions",
        action="store_true",
        help="Render captions; enterprise calls must match snapshot initialization",
    )
    captions.add_argument(
        "--no-captions",
        dest="include_captions",
        action="store_false",
        help="Render without captions; enterprise calls must match initialization",
    )
    parser.set_defaults(include_captions=True)
    parser.add_argument(
        "--caption-style",
        choices=sorted(CAPTION_STYLES),
        help="Caption style; required explicitly for enterprise renders",
    )
    parser.add_argument("--watermark", action="store_true", default=False)
    reframing = parser.add_mutually_exclusive_group()
    reframing.add_argument(
        "--auto-reframe",
        dest="auto_reframe",
        action="store_true",
        help="Automatically frame the subject (personal default)",
    )
    reframing.add_argument(
        "--no-auto-reframe",
        dest="auto_reframe",
        action="store_false",
        help="Preserve canonical full-frame authority (required for enterprise)",
    )
    parser.set_defaults(auto_reframe=True)
    parser.add_argument("--wait", action="store_true", help="Wait for render to complete")
    args = parser.parse_args()

    body = {
        "aspectRatio": args.aspect_ratio,
        "quality": args.quality,
        "includeCaptions": args.include_captions,
        "watermark": args.watermark,
        "autoReframe": args.auto_reframe,
    }
    if args.caption_style:
        body["captionStyle"] = args.caption_style

    client = ClipperClient(profile=args.profile)
    response = render_clip(
        client,
        args.clip_id,
        body,
        workspace_id=args.workspace_id,
    )

    if args.wait and response.get("jobId"):
        job = client.wait_for_job(response["jobId"], timeout=600)
        print_json(job)
    else:
        print_json(response)


if __name__ == "__main__":
    main()
