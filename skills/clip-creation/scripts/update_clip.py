#!/usr/bin/env python3
"""Update a clip's metadata (timing, title, caption).

Usage:
  python update_clip.py --clip-id <id> [--start <s>] [--end <s>] [--title <t>] [--caption <c>]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Update clip")
    parser.add_argument("--clip-id", required=True, help="Clip ID")
    parser.add_argument("--start", type=float, help="New start time (seconds)")
    parser.add_argument("--end", type=float, help="New end time (seconds)")
    parser.add_argument("--title", help="New title")
    parser.add_argument("--caption", help="New caption")
    args = parser.parse_args()

    body = {}
    if args.start is not None:
        body["startTime"] = args.start
    if args.end is not None:
        body["endTime"] = args.end
    if args.title is not None:
        body["title"] = args.title
    if args.caption is not None:
        body["caption"] = args.caption

    if not body:
        print("Nothing to update. Provide at least one of --start, --end, --title, --caption.")
        return

    client = ClipperClient()
    response = client.patch(f"/api/v1/clips/{args.clip_id}", body)
    print_json(response)


if __name__ == "__main__":
    main()
