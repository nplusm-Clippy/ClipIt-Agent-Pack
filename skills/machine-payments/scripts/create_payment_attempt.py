#!/usr/bin/env python3
"""Create an owned ClipIt machine-payment attempt after explicit approval."""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Create a ClipIt machine-payment attempt")
    parser.add_argument("--product-key", required=True, help="Product key from get_billing_catalog.py")
    parser.add_argument(
        "--provider",
        required=True,
        choices=["x402_direct", "stripe_x402", "stripe_mpp"],
        help="Ready payment rail selected from the live catalog",
    )
    parser.add_argument("--idempotency-key", help="Stable retry key, maximum 160 characters")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirm that the human approved the product, amount, rail, and budget",
    )
    args = parser.parse_args()

    if not args.confirm:
        parser.error("creating a payable attempt requires --confirm after human or budget-policy approval")

    body = {
        "productKey": args.product_key,
        "providerPreference": args.provider,
    }
    if args.idempotency_key:
        body["idempotencyKey"] = args.idempotency_key

    client = ClipperClient()
    print_json(client.post("/api/v1/billing/agent-payments", body))


if __name__ == "__main__":
    main()
