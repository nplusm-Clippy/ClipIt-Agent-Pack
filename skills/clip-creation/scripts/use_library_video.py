#!/usr/bin/env python3
"""Use a finalized enterprise library video as a processing source.

Usage:
  python use_library_video.py --asset-id <id>
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(
        description="Use a ClipIt enterprise library video as a processing source"
    )
    parser.add_argument(
        "--asset-id",
        required=True,
        help="Video asset ID returned by list_assets.py",
    )
    args = parser.parse_args()

    client = ClipperClient()
    print_json(client.post(f"/api/v1/assets/{args.asset_id}/video"))


if __name__ == "__main__":
    main()
