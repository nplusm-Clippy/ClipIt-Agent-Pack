#!/usr/bin/env python3
"""Get effective Stripe or agent-paid ClipIt billing access."""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get effective ClipIt billing access")
    parser.parse_args()

    client = ClipperClient()
    print_json(client.get("/api/v1/billing/subscription"))


if __name__ == "__main__":
    main()
