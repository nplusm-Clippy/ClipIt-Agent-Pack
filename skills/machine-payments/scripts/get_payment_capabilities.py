#!/usr/bin/env python3
"""Discover ClipIt machine-payment rails and safety policy."""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Discover ClipIt machine-payment capabilities")
    parser.parse_args()

    client = ClipperClient()
    print_json(client.get("/api/v1/agent/payment-capabilities"))


if __name__ == "__main__":
    main()
