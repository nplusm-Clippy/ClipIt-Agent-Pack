#!/usr/bin/env python3
"""Trigger transcription for a video (Deepgram Nova-3).

Usage:
  python transcribe_video.py --video-id <id> [--wait]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Transcribe a video")
    parser.add_argument("--video-id", required=True, help="Video ID to transcribe")
    parser.add_argument("--wait", action="store_true", help="Wait for transcription to complete")
    args = parser.parse_args()

    client = ClipperClient()
    response = client.post(f"/api/v1/videos/{args.video_id}/transcribe")

    if args.wait and response.get("jobId"):
        job = client.wait_for_job(response["jobId"], timeout=600)
        print_json(job)
    elif response.get("jobId"):
        print_json(response)
    else:
        print_json(response)


if __name__ == "__main__":
    main()
