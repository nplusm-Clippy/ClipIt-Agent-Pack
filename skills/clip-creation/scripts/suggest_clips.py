#!/usr/bin/env python3
"""Find clip opportunities through ClipIt's current inference route.

Usage:
  python suggest_clips.py --video-id <id> [--count N] [--platforms tiktok,youtube]
  [--min-duration 15] [--max-duration 60]

Returns JSON with clip opportunities: start/end times, titles, themes, confidence.
Always waits for the returned job; retain its ID if the wait is interrupted.
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Suggest viral clips via AI")
    parser.add_argument("--video-id", required=True, help="Video ID")
    parser.add_argument("--count", type=int, default=5, help="Number of suggestions (1-20)")
    parser.add_argument("--platforms", help="Comma-separated target platforms")
    parser.add_argument("--min-duration", type=float, help="Minimum clip duration (seconds)")
    parser.add_argument("--max-duration", type=float, help="Maximum clip duration (seconds)")
    args = parser.parse_args()

    body = {"count": args.count}
    if args.platforms:
        body["targetPlatforms"] = [p.strip() for p in args.platforms.split(",")]
    if args.min_duration:
        body["minDuration"] = args.min_duration
    if args.max_duration:
        body["maxDuration"] = args.max_duration

    client = ClipperClient()
    response = client.post(f"/api/v1/videos/{args.video_id}/suggest-clips", body)

    job = client.wait_for_job(response["jobId"], timeout=300)
    print_json(job.get("result", job))


if __name__ == "__main__":
    main()
