#!/usr/bin/env python3
"""Upload a local video file to Clipper.

Usage:
  python upload_video.py --file <path> [--wait]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Upload a video file to Clipper")
    parser.add_argument("--file", required=True, help="Path to the video file")
    parser.add_argument("--wait", action="store_true", help="Wait for processing to complete")
    args = parser.parse_args()

    client = ClipperClient()
    response = client.upload_file("/api/v1/videos", args.file)

    if args.wait and response.get("jobId"):
        job = client.wait_for_job(response["jobId"])
        print_json(job)
    else:
        print_json(response)


if __name__ == "__main__":
    main()
