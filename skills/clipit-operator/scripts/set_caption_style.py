#!/usr/bin/env python3
"""Persist one exact caption style into the canonical editor snapshot."""

import argparse

from clipper_client import ClipperClient, main_wrapper, print_json
from exact_caption_style_contract import (
    ExactCaptionStyleContractError,
    parse_json_object,
    set_exact_caption_style,
)


def parse_style(value):
    try:
        return parse_json_object(value)
    except ExactCaptionStyleContractError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


@main_wrapper
def main():
    parser = argparse.ArgumentParser(
        description="Persist and verify a clip's exact canonical caption style"
    )
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--clip-id", required=True)
    parser.add_argument("--profile", required=True, help="Named ClipIt CLI profile")
    style_input = parser.add_mutually_exclusive_group(required=True)
    style_input.add_argument(
        "--style-json",
        type=parse_style,
        help="Exact style JSON object or @path/to/style.json",
    )
    style_input.add_argument(
        "--directive",
        help="Strict shorthand such as 'caption size 200%% single'",
    )
    parser.add_argument("--expected-editor-version", required=True, type=int)
    parser.add_argument("--expected-editor-state-hash", required=True)
    parser.add_argument("--expected-clip-settings-revision", required=True, type=int)
    args = parser.parse_args()

    client = ClipperClient(profile=args.profile)
    print_json(set_exact_caption_style(
        client,
        args.workspace_id,
        args.clip_id,
        args.style_json,
        args.expected_editor_version,
        args.expected_editor_state_hash,
        args.expected_clip_settings_revision,
        directive=args.directive,
    ))


if __name__ == "__main__":
    main()
