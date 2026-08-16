#!/usr/bin/env python3
"""Upload an image, video, or audio file to the ClipIt asset library.

Usage:
  python upload_asset.py --file <path> [--content-type image/png]
"""

import argparse
import mimetypes
import sys
from clipper_client import ClipperClient, print_json, main_wrapper
from asset_upload_contract import (
    resolve_asset_idempotency_key,
    upload_library_asset,
)


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Upload a library asset")
    parser.add_argument("--file", required=True, help="Path to the asset file")
    parser.add_argument("--content-type", help="MIME type, guessed from file when omitted")
    parser.add_argument(
        "--idempotency-key",
        help="Stable key to reuse only when retrying this exact upload after an unknown outcome",
    )
    parser.add_argument("--duration", type=float, help=argparse.SUPPRESS)
    args = parser.parse_args()

    file_path = args.file
    content_type = args.content_type or mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    idempotency_key = resolve_asset_idempotency_key(args.idempotency_key)
    if args.duration is not None:
        print(
            "WARNING: --duration is deprecated and ignored; ClipIt derives media metadata during finalization.",
            file=sys.stderr,
        )
    print(f"Asset idempotency key: {idempotency_key}", file=sys.stderr)

    client = ClipperClient()
    print_json(upload_library_asset(
        client,
        file_path,
        content_type,
        requested_idempotency_key=idempotency_key,
    ))


if __name__ == "__main__":
    main()
