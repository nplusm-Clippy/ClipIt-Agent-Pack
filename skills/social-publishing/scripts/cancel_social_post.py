#!/usr/bin/env python3
"""Cancel a scheduled or pending social post.

Usage:
  python cancel_social_post.py --post-id <id>
"""

import argparse
from clipper_client import ClipperClient, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Cancel a social post")
    parser.add_argument("--post-id", required=True, help="Post ID to cancel")
    args = parser.parse_args()

    client = ClipperClient()
    client.delete(f"/api/v1/social/posts/{args.post_id}")
    print(f"Post {args.post_id} cancelled.")


if __name__ == "__main__":
    main()
