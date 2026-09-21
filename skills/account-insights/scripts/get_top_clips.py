#!/usr/bin/env python3
"""Get top clips or social posts by performance metric.

Usage:
  python get_top_clips.py [--days 30] [--limit 10] [--metric views]
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get top ClipIt clips by analytics metric")
    parser.add_argument("--days", type=int, help="Lookback window in days (1-365)")
    parser.add_argument("--limit", type=int, help="Maximum results (1-100)")
    parser.add_argument(
        "--metric",
        choices=[
            "views",
            "likes",
            "comments",
            "shares",
            "saves",
            "reach",
            "impressions",
            "watchTimeSeconds",
            "revenueCents",
        ],
        help="Metric to rank by",
    )
    args = parser.parse_args()

    params = {}
    if args.days is not None:
        params["days"] = args.days
    if args.limit is not None:
        params["limit"] = args.limit
    if args.metric:
        params["metric"] = args.metric

    client = ClipperClient()
    print_json(client.get("/api/v1/analytics/top-clips", params=params))


if __name__ == "__main__":
    main()
