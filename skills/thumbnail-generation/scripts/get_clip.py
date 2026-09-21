#!/usr/bin/env python3
"""Get details for a specific clip.

Usage:
  python get_clip.py --clip-id <id>
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get clip details")
    parser.add_argument("--clip-id", required=True, help="Clip ID")
    args = parser.parse_args()

    client = ClipperClient()
    response = client.get(f"/api/v1/clips/{args.clip_id}")
    print_json(response)


if __name__ == "__main__":
    main()
