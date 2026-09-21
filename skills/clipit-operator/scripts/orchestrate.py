#!/usr/bin/env python3
"""Start a ClipIt agent orchestration workflow and poll it.

Usage:
  python orchestrate.py "Find the strongest clip in this video" --video-id <id>
"""

import argparse
import shlex
import sys
import time
from clipper_client import ClipperClient, ClipperError, print_json, main_wrapper


def is_terminal(status):
    return status in ("completed", "failed", "cancelled")


def approval_command(job_id, approval_id, decision="approved"):
    return (
        "python scripts/approve_workflow.py "
        f"--job-id {shlex.quote(job_id)} "
        f"--approval-id {shlex.quote(approval_id)} "
        f"--decision {shlex.quote(decision)} "
        "--wait"
    )


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Run a ClipIt agent orchestration workflow")
    parser.add_argument("goal", nargs="+", help="Free-text goal for the ClipIt agent")
    parser.add_argument("--conversation-id", help="Optional conversation/session ID")
    parser.add_argument("--video-id", help="Optional video context ID")
    parser.add_argument("--clip-id", help="Optional clip context ID")
    parser.add_argument("--project-id", help="Optional project context ID")
    parser.add_argument("--sequence-id", help="Optional sequence context ID")
    parser.add_argument("--quick-mode", action="store_true", help="Ask the orchestrator for a faster workflow")
    parser.add_argument("--max-subagent-calls", type=int, help="Maximum subagent calls, 1-10")
    parser.add_argument("--trace", dest="trace_enabled", action="store_true", help="Enable trace output server-side")
    parser.add_argument("--timeout", type=float, default=900, help="Max wait in seconds")
    parser.add_argument("--poll-interval", type=float, default=3, help="Poll interval in seconds")
    args = parser.parse_args()

    body = {"userMessage": " ".join(args.goal)}
    optional_fields = {
        "conversationId": args.conversation_id,
        "videoId": args.video_id,
        "clipId": args.clip_id,
        "projectId": args.project_id,
        "sequenceId": args.sequence_id,
        "quickMode": True if args.quick_mode else None,
        "maxSubagentCalls": args.max_subagent_calls,
        "traceEnabled": True if args.trace_enabled else None,
    }
    for key, value in optional_fields.items():
        if value is not None:
            body[key] = value

    client = ClipperClient()
    response = client.post("/api/v1/agent/orchestrate", body)
    job_id = response["jobId"]
    deadline = time.time() + args.timeout
    last_progress = -1

    while time.time() < deadline:
        workflow = client.get(f"/api/v1/agent/workflows/{job_id}")
        status = workflow.get("status")
        progress = workflow.get("progress", 0)

        if progress != last_progress:
            print(f"  [{status}] {progress}%", file=sys.stderr)
            last_progress = progress

        if status == "awaiting_approval":
            pending = workflow.get("pendingApproval") or {}
            approval_id = pending.get("approvalId")
            print_json(workflow)
            if approval_id:
                print()
                print("Approval required. Pending tasks:")
                for task in pending.get("tasks", []):
                    title = task.get("title", task.get("id", "task"))
                    cost = task.get("estimatedCost")
                    if cost is None:
                        print(f"- {title}")
                    else:
                        print(f"- {title} ({cost} $CLIP estimated)")
                print()
                print("Rerun after approval:")
                print(approval_command(job_id, approval_id))
            sys.exit(12)

        if is_terminal(status):
            if status == "failed":
                raise ClipperError(500, "WORKFLOW_FAILED", "Workflow failed", workflow.get("error"))
            if status == "cancelled":
                raise ClipperError(500, "WORKFLOW_CANCELLED", "Workflow was cancelled")
            print_json(workflow)
            return

        time.sleep(args.poll_interval)

    raise ClipperError(500, "WORKFLOW_TIMEOUT", f"Workflow {job_id} did not complete within {args.timeout}s")


if __name__ == "__main__":
    main()
