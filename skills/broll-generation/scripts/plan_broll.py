#!/usr/bin/env python3
"""Plan B-Roll concepts for a clip using AI.

Usage:
  python plan_broll.py --clip-id <id> [--count 3] [--theme <theme>] [--wait]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Plan B-Roll concepts")
    parser.add_argument("--clip-id", required=True, help="Clip ID")
    parser.add_argument("--count", type=int, default=3, help="Number of concepts (1-8)")
    parser.add_argument("--theme", help="Optional theme hint")
    parser.add_argument("--wait", action="store_true", help="Wait for planning to complete")
    args = parser.parse_args()

    body = {"clipId": args.clip_id, "numberOfConcepts": args.count}
    if args.theme:
        body["theme"] = args.theme

    client = ClipperClient()
    response = client.post(f"/api/v1/clips/{args.clip_id}/broll/plan", body)

    if args.wait and response.get("jobId"):
        job = client.wait_for_job(response["jobId"], timeout=120)
        print_json(job.get("result", job))
    else:
        print_json(response)


if __name__ == "__main__":
    main()
