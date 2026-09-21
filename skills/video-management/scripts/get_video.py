#!/usr/bin/env python3
"""Get details for a specific video.

Usage:
  python get_video.py --video-id <id>
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get video details")
    parser.add_argument("--video-id", required=True, help="Video ID")
    args = parser.parse_args()

    client = ClipperClient()
    response = client.get(f"/api/v1/videos/{args.video_id}")
    print_json(response)


if __name__ == "__main__":
    main()
