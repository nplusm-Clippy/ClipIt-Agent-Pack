#!/usr/bin/env python3
"""Approve, choose cheaper, or cancel a pending ClipIt workflow approval.

Usage:
  python approve_workflow.py --job-id <id> --approval-id <id> --decision approved [--wait]
"""

import argparse
import sys
import time
from clipper_client import ClipperClient, ClipperError, print_json, main_wrapper


def is_terminal(status):
    return status in ("completed", "failed", "cancelled")


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Submit a ClipIt workflow approval decision")
    parser.add_argument("--job-id", required=True, help="Workflow job ID awaiting approval")
    parser.add_argument("--approval-id", required=True, help="Pending approval ID")
    parser.add_argument("--decision", required=True, choices=["approved", "cheaper", "cancelled"])
    parser.add_argument("--wait", action="store_true", help="Wait for the continuation workflow")
    parser.add_argument("--timeout", type=float, default=900, help="Max wait in seconds")
    parser.add_argument("--poll-interval", type=float, default=3, help="Poll interval in seconds")
    args = parser.parse_args()

    client = ClipperClient()
    response = client.post(
        f"/api/v1/agent/workflows/{args.job_id}/approval",
        {
            "approvalId": args.approval_id,
            "decision": args.decision,
        },
    )

    if not args.wait:
        print_json(response)
        return

    continuation_id = response["jobId"]
    deadline = time.time() + args.timeout
    last_progress = -1
    while time.time() < deadline:
        workflow = client.get(f"/api/v1/agent/workflows/{continuation_id}")
        status = workflow.get("status")
        progress = workflow.get("progress", 0)

        if progress != last_progress:
            print(f"  [{status}] {progress}%", file=sys.stderr)
            last_progress = progress

        if status == "awaiting_approval":
            print_json(workflow)
            return

        if is_terminal(status):
            if status == "failed":
                raise ClipperError(500, "WORKFLOW_FAILED", "Workflow failed", workflow.get("error"))
            if status == "cancelled":
                raise ClipperError(500, "WORKFLOW_CANCELLED", "Workflow was cancelled")
            print_json(workflow)
            return

        time.sleep(args.poll_interval)

    raise ClipperError(500, "WORKFLOW_TIMEOUT", f"Workflow {continuation_id} did not complete within {args.timeout}s")


if __name__ == "__main__":
    main()
