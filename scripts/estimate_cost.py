#!/usr/bin/env python3
"""Preflight $CLIP cost and approval caps without charging credits.

Usage:
  python estimate_cost.py --operation-type transcription --provider deepgram \
    --model-id nova-3 --max-credits 2 videoSeconds=120
"""

import argparse
from clipper_client import ClipperClient, print_json, main_wrapper


def parse_metric(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("metrics must be key=value pairs")

    key, raw = value.split("=", 1)
    key = key.strip()
    if not key:
        raise argparse.ArgumentTypeError("metric key cannot be empty")

    try:
        number = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"metric {key} must be numeric") from exc

    return key, number


def preflight_cost(client, body):
    response = client.post("/api/v1/credits/preflight", body)
    if not isinstance(response, dict):
        raise RuntimeError("ClipIt returned an invalid cost preflight response.")
    if response.get("settlementMode") not in ("direct", "enterprise_usage_only"):
        raise RuntimeError("ClipIt did not return a valid credit settlement mode.")
    for field in ("internalEstimatedUsageClip", "clientCreditChargeClip"):
        value = response.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise RuntimeError(f"ClipIt did not return a valid {field}.")
    if not isinstance(response.get("affordable"), bool) or not isinstance(
        response.get("withinApprovalCap"), bool
    ):
        raise RuntimeError("ClipIt did not return a valid cost preflight decision.")
    return {
        "internalEstimatedUsageClip": response["internalEstimatedUsageClip"],
        "clientCreditChargeClip": response["clientCreditChargeClip"],
        "settlementMode": response["settlementMode"],
        "affordable": response["affordable"],
        "approvalCapClip": response.get("approvalCapClip"),
        "withinApprovalCap": response["withinApprovalCap"],
        "spendLimitViolation": response.get("spendLimitViolation"),
        "units": response.get("units", "clip"),
    }


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Preflight a $CLIP credit cost")
    parser.add_argument("--profile", help="Named ClipIt CLI profile")
    parser.add_argument("--operation-type", required=True, help="Operation type, e.g. transcription")
    parser.add_argument("--provider", required=True, help="Provider name, e.g. deepgram")
    parser.add_argument("--model-id", help="Optional provider model ID")
    parser.add_argument(
        "--max-credits",
        type=float,
        help="Optional approval cap; this does not expose the account balance",
    )
    parser.add_argument("metrics", nargs="*", type=parse_metric, help="Metric key=value pairs")
    args = parser.parse_args()

    if args.max_credits is not None and args.max_credits < 0:
        parser.error("--max-credits must be zero or greater")

    body = {
        "operationType": args.operation_type,
        "provider": args.provider,
        "metrics": dict(args.metrics),
    }
    if args.model_id:
        body["modelId"] = args.model_id
    if args.max_credits is not None:
        body["maxCredits"] = args.max_credits

    client = ClipperClient(profile=args.profile)
    print_json(preflight_cost(client, body))


if __name__ == "__main__":
    main()
