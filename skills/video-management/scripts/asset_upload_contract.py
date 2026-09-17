"""Durable sign, PUT, and finalize helpers for ClipIt library assets."""

import os
import re
from typing import Any, Dict, Optional
from uuid import uuid4

import requests


IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


class AssetUploadContractError(ValueError):
    """Raised when the durable asset upload contract is incomplete."""


def _non_empty_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def resolve_asset_idempotency_key(requested_key: Optional[str]) -> str:
    idempotency_key = (
        _non_empty_string(requested_key) or f"agent-pack-asset:{uuid4()}"
    )
    if (
        len(idempotency_key) < 8
        or len(idempotency_key) > 128
        or not IDEMPOTENCY_KEY_RE.fullmatch(idempotency_key)
    ):
        raise AssetUploadContractError(
            "Asset idempotency key must be 8-128 URL-safe characters."
        )
    return idempotency_key


def require_signed_asset_upload(signed: Any) -> Dict[str, Any]:
    if not isinstance(signed, dict):
        raise AssetUploadContractError("Asset sign-upload response is invalid.")
    upload_url = _non_empty_string(signed.get("uploadUrl")) or _non_empty_string(
        signed.get("url")
    )
    intent_id = _non_empty_string(signed.get("intentId"))
    asset_id = _non_empty_string(signed.get("assetId"))
    if not upload_url or not intent_id or not asset_id:
        raise AssetUploadContractError(
            "Asset sign-upload response is missing its URL, intentId, or assetId."
        )
    raw_headers = signed.get("headers")
    if raw_headers is not None and not isinstance(raw_headers, dict):
        raise AssetUploadContractError("Asset upload headers are invalid.")
    headers = {
        str(key): str(value)
        for key, value in (raw_headers or {}).items()
        if value is not None
    }
    return {
        "uploadUrl": upload_url,
        "intentId": intent_id,
        "assetId": asset_id,
        "headers": headers,
    }


def upload_library_asset(
    client: Any,
    file_path: str,
    content_type: str,
    requested_idempotency_key: Optional[str] = None,
    put=requests.put,
) -> Any:
    """Upload exact declared bytes and finalize only by the returned intent ID."""
    filename = os.path.basename(file_path)
    size = os.path.getsize(file_path)
    if not filename or size <= 0:
        raise AssetUploadContractError("Asset file must be non-empty.")
    content_type = _non_empty_string(content_type)
    if not content_type:
        raise AssetUploadContractError("Asset content type is required.")

    signed = require_signed_asset_upload(client.post(
        "/api/v1/assets/sign-upload",
        {
            "filename": filename,
            "contentType": content_type,
            "size": size,
            "idempotencyKey": resolve_asset_idempotency_key(
                requested_idempotency_key
            ),
        },
    ))
    upload_headers = dict(signed["headers"])
    upload_headers.setdefault("Content-Type", content_type)
    upload_headers.setdefault("Content-Length", str(size))
    with open(file_path, "rb") as file_obj:
        upload_response = put(
            signed["uploadUrl"],
            data=file_obj,
            headers=upload_headers,
            timeout=600,
        )
    upload_response.raise_for_status()

    return client.post(
        f"/api/v1/assets/{signed['assetId']}/finalize",
        {"uploadIntentId": signed["intentId"]},
    )
