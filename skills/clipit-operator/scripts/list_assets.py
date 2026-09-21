#!/usr/bin/env python3
"""List uploaded ClipIt library assets.

Usage:
  python list_assets.py [--type image] [--limit 20] [--offset 0]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="List ClipIt library assets")
    parser.add_argument("--type", choices=["image", "video", "audio", "raw"], help="Filter by asset type")
    parser.add_argument("--limit", type=int, help="Maximum assets to return (1-200)")
    parser.add_argument("--offset", type=int, help="Pagination offset")
    args = parser.parse_args()

    params = {}
    if args.type:
        params["type"] = args.type
    if args.limit is not None:
        params["limit"] = args.limit
    if args.offset is not None:
        params["offset"] = args.offset

    client = ClipperClient()
    print_json(client.get("/api/v1/assets", params=params))


if __name__ == "__main__":
    main()
