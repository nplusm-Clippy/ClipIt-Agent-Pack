#!/usr/bin/env python3
"""Post a rendered clip to social media platforms immediately.

Usage:
  python post_to_social.py --clip-id <id> --platform linkedin
  --account-id <accountId> --caption "My caption" [--export-id <id>] [--wait]

The clip MUST have one completed exact-current export.
YouTube requires --title.
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper
from social_publish_contract import (
    SocialPublishContractError,
    parse_account_id_pins,
    parse_platforms,
    prepare_social_publish_request,
)


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Post clip to social media")
    parser.add_argument("--clip-id", required=True, help="Rendered clip ID")
    platform_group = parser.add_mutually_exclusive_group(required=True)
    platform_group.add_argument("--platform", help="One exact target platform (required for enterprise keys)")
    platform_group.add_argument("--platforms", help="Comma-separated platforms for ordinary keys")
    account_group = parser.add_mutually_exclusive_group()
    account_group.add_argument("--account-id", help="Exact accountId for a single --platform")
    account_group.add_argument("--account-ids", help="platform=accountId pairs or a JSON object")
    parser.add_argument("--caption", required=True, help="Post caption")
    parser.add_argument("--title", help="Title (required for YouTube)")
    parser.add_argument("--hashtags", help="Comma-separated hashtags")
    parser.add_argument("--export-id", help="Exact completed export ID (required if delivery-state is ambiguous)")
    parser.add_argument("--enterprise-deliverable-id", help="Optional selected enterprise deliverable ID")
    parser.add_argument("--wait", action="store_true", help="Wait for posting to complete")
    args = parser.parse_args()

    platforms = parse_platforms(args.platform or args.platforms)
    requested_account_ids = parse_account_id_pins(args.account_ids)
    if args.account_id:
        if len(platforms) != 1:
            raise SocialPublishContractError("--account-id requires one --platform.")
        account_id = args.account_id.strip()
        if not account_id:
            raise SocialPublishContractError("--account-id must not be empty.")
        requested_account_ids[platforms[0]] = account_id

    if "youtube" in platforms and not args.title:
        print("ERROR: --title is required when posting to YouTube.", file=__import__("sys").stderr)
        __import__("sys").exit(1)

    client = ClipperClient()
    body = prepare_social_publish_request(
        client,
        clip_id=args.clip_id,
        platforms=platforms,
        caption=args.caption,
        requested_account_ids=requested_account_ids,
        requested_export_id=args.export_id,
        title=args.title,
        hashtags=[h.strip().lstrip("#") for h in args.hashtags.split(",") if h.strip()] if args.hashtags else None,
        enterprise_deliverable_id=args.enterprise_deliverable_id,
    )
    response = client.post("/api/v1/social/post", body)

    if args.wait and response.get("jobId"):
        job = client.wait_for_job(response["jobId"], timeout=120)
        print_json(job)
    else:
        print_json(response)


if __name__ == "__main__":
    main()
