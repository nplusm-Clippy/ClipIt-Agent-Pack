#!/usr/bin/env python3
"""Get fulfillment records for an API-key-owned ClipIt payment attempt."""

import argparse
from urllib.parse import quote
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get a ClipIt machine-payment receipt")
    parser.add_argument("--attempt-id", required=True)
    args = parser.parse_args()

    client = ClipperClient()
    attempt_id = quote(args.attempt_id, safe="")
    print_json(client.get(f"/api/v1/billing/agent-payments/{attempt_id}/receipt"))


if __name__ == "__main__":
    main()
