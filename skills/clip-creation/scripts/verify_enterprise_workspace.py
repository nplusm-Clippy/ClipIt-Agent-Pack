#!/usr/bin/env python3
"""Fail closed unless the active named profile is the expected workspace."""

import argparse

from clipper_client import (
    ClipperClient,
    main_wrapper,
    print_json,
    require_enterprise_workspace_scope,
)


@main_wrapper
def main():
    parser = argparse.ArgumentParser(
        description="Verify an active team-operated ClipIt enterprise workspace"
    )
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="Expected enterprise workspace ID from the ClipIt admin dashboard",
    )
    parser.add_argument(
        "--profile",
        help="Named ClipIt CLI profile (or set CLIPIT_PROFILE)",
    )
    args = parser.parse_args()

    client = ClipperClient(profile=args.profile)
    if client.profile_name == "default":
        raise RuntimeError(
            "Enterprise workspace operations require a named ClipIt profile. "
            "Pass --profile or set CLIPIT_PROFILE."
        )

    scope = require_enterprise_workspace_scope(
        client.get_agent_identity(),
        expected_workspace_id=args.workspace_id,
    )
    print_json({
        "verified": True,
        "profile": client.profile_name,
        "workspaceId": scope["workspaceId"],
        "workspaceName": scope["workspaceName"],
        "workspaceStatus": scope["workspaceStatus"],
        "workspaceRole": scope["workspaceRole"],
        "billingMode": scope["billingMode"],
    })


if __name__ == "__main__":
    main()
