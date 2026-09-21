#!/usr/bin/env python3
"""Get aggregate or by-platform social analytics.

Usage:
  python get_analytics_overview.py [--days 30] [--by-platform]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get ClipIt analytics overview")
    parser.add_argument("--days", type=int, help="Lookback window in days (1-365)")
    parser.add_argument("--by-platform", action="store_true", help="Group analytics by platform")
    args = parser.parse_args()

    params = {}
    if args.days is not None:
        params["days"] = args.days

    path = "/api/v1/analytics/by-platform" if args.by_platform else "/api/v1/analytics/aggregate"
    client = ClipperClient()
    print_json(client.get(path, params=params))


if __name__ == "__main__":
    main()
