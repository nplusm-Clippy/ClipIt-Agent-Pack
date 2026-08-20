#!/usr/bin/env python3
"""Preflight, approve, and resume one exact enterprise delivery recipe."""

import argparse
import sys
import time
import uuid

from clipper_client import ClipperClient, main_wrapper, print_json
from enterprise_exact_delivery_contract import (
    EnterpriseExactDeliveryContractError,
    advance_enterprise_exact_delivery,
    preflight_enterprise_exact_delivery,
    require_enterprise_profile,
)
from exact_caption_style_contract import parse_json_object


def parse_style(value):
    try:
        return parse_json_object(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


@main_wrapper
def main():
    parser = argparse.ArgumentParser(
        description="Run one exact, idempotent enterprise render/export/delivery recipe"
    )
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--clip-id", required=True)
    parser.add_argument("--profile", required=True, help="Named ClipIt CLI profile")
    parser.add_argument(
        "--style-json",
        required=True,
        type=parse_style,
        help="Exact caption style JSON object or @path/to/style.json",
    )
    parser.add_argument("--expected-editor-version", required=True, type=int)
    parser.add_argument("--expected-editor-state-hash", required=True)
    parser.add_argument("--expected-clip-settings-revision", required=True, type=int)
    parser.add_argument("--max-credits", required=True, type=float)
    outro = parser.add_mutually_exclusive_group()
    outro.add_argument("--include-outro", dest="include_outro", action="store_true")
    outro.add_argument("--no-outro", dest="include_outro", action="store_false")
    parser.set_defaults(include_outro=True)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Advance the exact plan returned by preflight",
    )
    parser.add_argument(
        "--idempotency-key",
        help="Stable first-advance key; generated when omitted",
    )
    parser.add_argument("--resume-token", help="Durable token from a processing receipt")
    parser.add_argument("--plan-hash", help="Original plan hash; required with --resume-token")
    parser.add_argument(
        "--caption-style-hash",
        help="Original approved caption-style hash; required with --resume-token",
    )
    parser.add_argument(
        "--expected-final-duration",
        type=float,
        help="Approved final duration from receipt lineage; required with --resume-token",
    )
    parser.add_argument("--wait", action="store_true", help="Resume until completed or blocked")
    parser.add_argument("--timeout", type=float, default=1200)
    parser.add_argument("--poll-interval", type=float, default=3)
    args = parser.parse_args()

    if args.max_credits < 0:
        parser.error("--max-credits must be zero or greater")
    if args.resume_token and (
        not args.plan_hash
        or not args.caption_style_hash
        or args.expected_final_duration is None
        or args.expected_final_duration <= 0
    ):
        parser.error(
            "--resume-token requires --plan-hash, --caption-style-hash, and "
            "a positive --expected-final-duration from the receipt"
        )
    if not args.resume_token and (
        args.plan_hash
        or args.caption_style_hash
        or args.expected_final_duration is not None
    ):
        parser.error(
            "plan/style hashes and expected final duration are accepted only with --resume-token"
        )

    request = {
        "clipId": args.clip_id,
        "expectedEditorVersion": args.expected_editor_version,
        "expectedEditorStateHash": args.expected_editor_state_hash,
        "expectedClipSettingsRevision": args.expected_clip_settings_revision,
        "captionStyle": args.style_json,
        "includeOutro": args.include_outro,
        "maxCredits": args.max_credits,
    }
    client = ClipperClient(profile=args.profile)

    if args.resume_token:
        require_enterprise_profile(client, args.workspace_id)
        plan = {
            "planHash": args.plan_hash,
            "exactCaptionStyle": {"styleHash": args.caption_style_hash},
            "outputPolicy": {
                "expectedFinalDuration": args.expected_final_duration,
            },
        }
        resume_token = args.resume_token
        idempotency_key = None
    else:
        plan = preflight_enterprise_exact_delivery(
            client,
            args.workspace_id,
            request,
        )
        if plan.get("approved") is not True:
            print_json(plan)
            raise EnterpriseExactDeliveryContractError(
                "Exact-delivery preflight is blocked; no provider work was started."
            )
        if not args.confirm:
            print_json(plan)
            return
        resume_token = None
        idempotency_key = args.idempotency_key or f"agent-pack-exact:{uuid.uuid4()}"
        print(f"Exact-delivery idempotency key: {idempotency_key}", file=sys.stderr)

    deadline = time.monotonic() + args.timeout
    while True:
        receipt = advance_enterprise_exact_delivery(
            client,
            plan,
            request,
            idempotency_key=idempotency_key,
            resume_token=resume_token,
        )
        if receipt["state"] != "processing" or not args.wait:
            print_json(receipt)
            if receipt["state"] == "blocked":
                raise EnterpriseExactDeliveryContractError(
                    "Exact-delivery recipe is blocked; use its typed receipt to resume safely."
                )
            return
        resume_token = receipt["resumeToken"]
        idempotency_key = None
        if time.monotonic() >= deadline:
            print_json(receipt)
            raise TimeoutError(
                "Exact-delivery wait timed out; resume with the receipt token and hashes."
            )
        time.sleep(max(0.25, args.poll_interval))


if __name__ == "__main__":
    main()
