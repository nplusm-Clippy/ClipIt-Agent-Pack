#!/usr/bin/env python3
"""List server-priced ClipIt products and available payment rails."""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="List the ClipIt machine-payment catalog")
    parser.parse_args()

    client = ClipperClient()
    print_json(client.get("/api/v1/billing/catalog"))


if __name__ == "__main__":
    main()
