#!/usr/bin/env python3
"""Wait for a ClipIt export job to complete.

Usage:
  python wait_for_export.py --job-id <id> [--timeout 600] [--poll-interval 3]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Wait for a ClipIt export job to complete")
    parser.add_argument("--job-id", required=True, help="Export job ID to poll")
    parser.add_argument("--timeout", type=float, default=600, help="Max wait in seconds")
    parser.add_argument("--poll-interval", type=float, default=3, help="Poll interval in seconds")
    args = parser.parse_args()

    client = ClipperClient()
    result = client.wait_for_export(
        args.job_id,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
    )
    print_json(result)


if __name__ == "__main__":
    main()
