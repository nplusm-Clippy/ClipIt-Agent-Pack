#!/usr/bin/env python3
"""Fetch the transcript for a video (word-level timestamps + speakers).

Usage:
  python get_transcript.py --video-id <id>
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get video transcript")
    parser.add_argument("--video-id", required=True, help="Video ID")
    args = parser.parse_args()

    client = ClipperClient()
    response = client.get(f"/api/v1/videos/{args.video_id}/transcript")
    print_json(response)


if __name__ == "__main__":
    main()
