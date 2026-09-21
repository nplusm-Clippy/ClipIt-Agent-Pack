#!/usr/bin/env python3
"""Delete a video from Clipper.

Usage:
  python delete_video.py --video-id <id>
"""

import argparse
from clipper_client import ClipperClient, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Delete a video")
    parser.add_argument("--video-id", required=True, help="Video ID to delete")
    args = parser.parse_args()

    client = ClipperClient()
    client.delete(f"/api/v1/videos/{args.video_id}")
    print(f"Video {args.video_id} deleted.")


if __name__ == "__main__":
    main()
