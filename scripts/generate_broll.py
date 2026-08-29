#!/usr/bin/env python3
"""Generate B-Roll through ClipIt's GPT Image 2 + H3 Max pipeline.

Usage:
  python generate_broll.py --clip-id <id> --start <s> --end <s>
  [--prompt <prompt>] [--mode single_image|start_end_frame]
  [--end-frame-description <desc>] [--transition-description <desc>]
  [--duration 5..15] [--resolution 480p|768p]
  [--image-quality low|medium|high|auto] [--wait]

ClipIt preserves the source clip audio; generated provider audio is not used.
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Generate B-Roll")
    parser.add_argument("--clip-id", required=True, help="Clip ID")
    parser.add_argument("--start", type=float, required=True, help="B-Roll start time within clip (seconds)")
    parser.add_argument("--end", type=float, required=True, help="B-Roll end time within clip (seconds)")
    parser.add_argument("--prompt", help="Custom visual prompt (overrides plan concepts)")
    parser.add_argument("--concept-index", type=int, help="Index from plan_broll output to use")
    parser.add_argument("--mode", default="single_image", choices=["single_image", "start_end_frame"])
    parser.add_argument("--end-frame-description", help="Required for start_end_frame mode: how the end frame differs")
    parser.add_argument("--transition-description", help="Optional: describes motion between start and end frames")
    parser.add_argument("--duration", type=int, default=6, help="Generated video duration in seconds (5-15)")
    parser.add_argument("--resolution", default="768p", choices=["480p", "768p"])
    parser.add_argument("--image-quality", default="high", choices=["low", "medium", "high", "auto"])
    parser.add_argument("--wait", action="store_true", help="Wait for generation to finish")
    args = parser.parse_args()

    if not 5 <= args.duration <= 15:
        parser.error("--duration must be between 5 and 15 seconds")
    if args.start < 0:
        parser.error("--start must be zero or greater")
    if args.end <= args.start:
        parser.error("--end must be greater than --start")
    if args.end - args.start > args.duration:
        parser.error("B-Roll placement (--end - --start) cannot exceed --duration")
    if args.mode == "start_end_frame" and not args.end_frame_description:
        parser.error("--end-frame-description is required for start_end_frame mode")

    body = {
        "clipId": args.clip_id,
        "startTimeInClip": args.start,
        "endTimeInClip": args.end,
        "mode": args.mode,
        "durationSeconds": args.duration,
        "resolution": args.resolution,
        "imageQuality": args.image_quality,
    }
    if args.prompt:
        body["promptOverride"] = args.prompt
    if args.concept_index is not None:
        body["conceptIndex"] = args.concept_index
    if args.end_frame_description:
        body["endFrameDescription"] = args.end_frame_description
    if args.transition_description:
        body["transitionDescription"] = args.transition_description

    client = ClipperClient()
    response = client.post(f"/api/v1/clips/{args.clip_id}/broll/generate", body)

    if args.wait and response.get("jobId"):
        job = client.wait_for_job(response["jobId"], timeout=600)
        print_json(job)
    else:
        print_json(response)


if __name__ == "__main__":
    main()
