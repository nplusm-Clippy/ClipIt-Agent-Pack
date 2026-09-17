#!/usr/bin/env python3
"""Import a video from a URL (YouTube, Vimeo, Twitch, etc.) into Clipper.

Usage:
  python import_video_from_url.py --url <url> [--title <title>] [--wait]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Import video from URL")
    parser.add_argument("--url", required=True, help="Video URL to import")
    parser.add_argument("--title", help="Optional title override")
    parser.add_argument("--wait", action="store_true", help="Wait for processing to complete")
    args = parser.parse_args()

    client = ClipperClient()
    body = {"url": args.url}
    if args.title:
        body["title"] = args.title

    response = client.post("/api/v1/videos/from-url", body)

    if args.wait and response.get("jobId"):
        job = client.wait_for_job(response["jobId"], timeout=300)
        print_json(job)
    else:
        print_json(response)


if __name__ == "__main__":
    main()
