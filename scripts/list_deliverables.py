#!/usr/bin/env python3
"""List ready or client-selected deliverables in one enterprise workspace.

Usage:
  python list_deliverables.py --workspace-id <id> [--status ready|selected]
"""

import argparse

from clipper_client import ClipperClient, main_wrapper, print_json
from enterprise_delivery_contract import list_enterprise_deliverables


@main_wrapper
def main():
    parser = argparse.ArgumentParser(
        description="List exact-workspace enterprise deliverables"
    )
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="Expected workspace ID from the ClipIt admin dashboard",
    )
    parser.add_argument("--status", choices=["ready", "selected"])
    parser.add_argument("--export-id", help="Filter by exact completed export ID")
    parser.add_argument("--limit", type=int, default=50, help="Maximum rows (1-100)")
    parser.add_argument("--offset", type=int, default=0, help="Pagination offset")
    args = parser.parse_args()

    client = ClipperClient()
    print_json(list_enterprise_deliverables(
        client,
        args.workspace_id,
        status=args.status,
        export_id=args.export_id,
        limit=args.limit,
        offset=args.offset,
    ))


if __name__ == "__main__":
    main()
