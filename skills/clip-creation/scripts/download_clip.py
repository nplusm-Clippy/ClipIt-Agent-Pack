#!/usr/bin/env python3
"""Get a signed download URL for a rendered clip.

Usage:
  python download_clip.py --clip-id <id>
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get clip download URL")
    parser.add_argument("--clip-id", required=True, help="Clip ID (must be rendered)")
    args = parser.parse_args()

    client = ClipperClient()
    response = client.get(f"/api/v1/clips/{args.clip_id}/download")
    print_json(response)


if __name__ == "__main__":
    main()
