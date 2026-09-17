#!/usr/bin/env python3
"""Get a signed download URL for a completed export.

Usage:
  python download_export.py --job-id <id>
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get export download URL")
    parser.add_argument("--job-id", required=True, help="Export job ID")
    args = parser.parse_args()

    client = ClipperClient()
    print_json(client.get(f"/api/v1/exports/{args.job_id}/download"))


if __name__ == "__main__":
    main()
