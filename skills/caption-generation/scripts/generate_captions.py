#!/usr/bin/env python3
"""Generate captions for a clip (requires the parent video to be transcribed first).

Usage:
  python generate_captions.py --clip-id <id> [--preset bold|minimal|neon|classic|tiktok-viral]
  [--font Inter] [--font-size 48] [--color "#FFFFFF"] [--position bottom]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Generate captions for a clip")
    parser.add_argument("--clip-id", required=True, help="Clip ID")
    parser.add_argument("--preset", choices=["bold", "minimal", "neon", "classic", "tiktok-viral"])
    parser.add_argument("--font", help="Font name (Inter, Arial, Bangers, Oswald, Roboto)")
    parser.add_argument("--font-size", type=int, help="Font size (12-120)")
    parser.add_argument("--color", help='Text color as hex (e.g., "#FFFFFF")')
    parser.add_argument("--position", choices=["top", "center", "bottom"])
    args = parser.parse_args()

    body = {}
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
    if style:
        body["style"] = style

    client = ClipperClient()
    response = client.post(f"/api/v1/clips/{args.clip_id}/captions", body)
    print_json(response)


if __name__ == "__main__":
    main()
