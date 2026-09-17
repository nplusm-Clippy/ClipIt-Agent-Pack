#!/usr/bin/env python3
"""Fetch ClipIt agent instructions for a target agent framework.

Usage:
  python get_agent_instructions.py [--target generic] [--format markdown]
"""

import argparse
import requests
from clipper_client import ClipperClient, ClipperError, print_json, main_wrapper


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Get ClipIt agent instructions")
    parser.add_argument("--target", default="generic", choices=["generic", "codex", "claude", "hermes"])
    parser.add_argument("--format", default="markdown", choices=["markdown", "json"])
    args = parser.parse_args()

    client = ClipperClient()
    response = requests.get(
        f"{client.base_url}/api/v1/agent/instructions",
        headers=client._headers(),
        params={"target": args.target, "format": args.format},
        timeout=30,
    )

    if response.status_code not in (200, 201, 202, 204):
        try:
            body = response.json()
            raise ClipperError(
                response.status_code,
                body.get("code", "UNKNOWN"),
                body.get("error", "Unknown error"),
                body.get("details"),
            )
        except ValueError:
            raise ClipperError(
                response.status_code,
                "INVALID_RESPONSE",
                f"HTTP {response.status_code}: {response.text[:200]}",
            )

    if args.format == "json":
        print_json(response.json())
    else:
        print(response.text)


if __name__ == "__main__":
    main()
