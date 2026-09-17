#!/usr/bin/env python3
"""Update caption styling on a clip.

Usage:
  python update_captions.py --clip-id <id> [--preset neon] [--font Bangers]
  [--font-size 60] [--color "#00FF00"] [--position center]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Update caption style")
    parser.add_argument("--clip-id", required=True, help="Clip ID")
    parser.add_argument("--preset", choices=["bold", "minimal", "neon", "classic", "tiktok-viral"])
    parser.add_argument("--font")
    parser.add_argument("--font-size", type=int)
    parser.add_argument("--color")
    parser.add_argument("--position", choices=["top", "center", "bottom"])
    args = parser.parse_args()

    style = {}
    if args.preset:
        style["preset"] = args.preset
    if args.font:
        style["font"] = args.font
    if args.font_size:
        style["fontSize"] = args.font_size
    if args.color:
        style["color"] = args.color
    if args.position:
        style["position"] = args.position

    if not style:
        print("Nothing to update. Provide at least one style option.")
        return

    client = ClipperClient()
    response = client.patch(f"/api/v1/clips/{args.clip_id}/captions", {"style": style})
    print_json(response)


if __name__ == "__main__":
    main()
