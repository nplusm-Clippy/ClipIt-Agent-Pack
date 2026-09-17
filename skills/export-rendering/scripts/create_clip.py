#!/usr/bin/env python3
"""Create a clip from a video with specific start/end times.

Usage:
  python create_clip.py --video-id <id> --start <seconds> --end <seconds>
  [--title <title>] [--caption <caption>]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Create a clip")
    parser.add_argument("--video-id", required=True, help="Source video ID")
    parser.add_argument("--start", type=float, required=True, help="Start time in seconds")
    parser.add_argument("--end", type=float, required=True, help="End time in seconds")
    parser.add_argument("--title", help="Clip title")
    parser.add_argument("--caption", help="Clip caption text")
    args = parser.parse_args()

    body = {
        "videoId": args.video_id,
        "startTime": args.start,
        "endTime": args.end,
    }
    if args.title:
        body["title"] = args.title
    if args.caption:
        body["caption"] = args.caption

    client = ClipperClient()
    response = client.post("/api/v1/clips", body)
    print_json(response)


if __name__ == "__main__":
    main()
