#!/usr/bin/env python3
"""Get analytics metrics for a social post.

Usage:
  python get_post_metrics.py --post-id <id>
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get social post analytics metrics")
    parser.add_argument("--post-id", required=True, help="Social post ID")
    args = parser.parse_args()

    client = ClipperClient()
    print_json(client.get(f"/api/v1/analytics/posts/{args.post_id}/metrics"))


if __name__ == "__main__":
    main()
