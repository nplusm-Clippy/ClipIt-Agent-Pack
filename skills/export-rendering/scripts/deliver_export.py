#!/usr/bin/env python3
"""Place one completed export in an enterprise client's Delivered Clips tab.

Usage:
  python deliver_export.py --workspace-id <id> --export-id <id> --profile <name>

ClipIt derives the title and note from the bound canonical snapshot. This creates
a ready deliverable only; the client retains publishing authority.
"""

import argparse

from clipper_client import ClipperClient, main_wrapper, print_json
from enterprise_delivery_contract import deliver_export_to_client


@main_wrapper
def main():
    parser = argparse.ArgumentParser(
        description="Deliver a completed export to an enterprise client"
    )
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="Expected workspace ID from the ClipIt admin dashboard",
    )
    parser.add_argument("--export-id", required=True, help="Completed export ID")
    parser.add_argument("--profile", required=True, help="Named ClipIt CLI profile")
    args = parser.parse_args()

    client = ClipperClient(profile=args.profile)
    print_json(deliver_export_to_client(
        client,
        args.workspace_id,
        args.export_id,
    ))


if __name__ == "__main__":
    main()
