#!/usr/bin/env python3
"""Get the status of a social post.

Usage:
  python get_social_post.py --post-id <id>
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get social post status")
    parser.add_argument("--post-id", required=True, help="Post ID")
    args = parser.parse_args()

    client = ClipperClient()
    response = client.get(f"/api/v1/social/posts/{args.post_id}")
    print_json(response)


if __name__ == "__main__":
    main()
