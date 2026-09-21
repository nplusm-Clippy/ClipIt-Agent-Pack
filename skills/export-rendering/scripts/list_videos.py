#!/usr/bin/env python3
"""List videos in the user's Clipper library.

Usage:
  python list_videos.py [--limit N] [--offset N]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="List videos")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()

    client = ClipperClient()
    response = client.get("/api/v1/videos", {"limit": args.limit, "offset": args.offset})
    print_json(response)


if __name__ == "__main__":
    main()
