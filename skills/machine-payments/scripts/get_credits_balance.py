#!/usr/bin/env python3
"""Get the current ClipIt $CLIP credits balance.

Usage:
  python get_credits_balance.py
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get $CLIP credits balance")
    parser.parse_args()

    client = ClipperClient()
    response = client.get("/api/v1/credits/balance")
    print_json(
        {
            "balanceClip": response.get("balanceClip"),
            "lifetimeDepositedClip": response.get("lifetimeDepositedClip"),
            "lifetimeConsumedClip": response.get("lifetimeConsumedClip"),
            "status": response.get("status"),
            "units": response.get("units", "clip"),
        }
    )


if __name__ == "__main__":
    main()
