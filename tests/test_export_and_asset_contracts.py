import tempfile
import unittest
from pathlib import Path

from scripts.asset_upload_contract import (
    AssetUploadContractError,
    require_signed_asset_upload,
    upload_library_asset,
)
from scripts.export_contract import (
    ExportContractError,
    prepare_export_start_request,
)


SNAPSHOT_ID = "11111111-1111-4111-8111-111111111111"
EDITOR_HASH = "a" * 64


def editor_delivery_state(**overrides):
    state = {
        "schema": "clipit_clip_delivery_state",
        "version": 2,
        "clipId": "clip-current",
        "editorStateStatus": "verified",
        "editorState": {
            "snapshotId": SNAPSHOT_ID,
            "editorVersion": 7,
            "editorStateHash": EDITOR_HASH,
            "stateSource": "current_editor_snapshot",
        },
    }
    state.update(overrides)
    return state


class ExportClient:
    def __init__(self, delivery_state=None):
        self.delivery_state = delivery_state or editor_delivery_state()
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        return self.delivery_state


class ExportContractTests(unittest.TestCase):
    def test_export_preflight_pins_exact_current_editor_identity(self):
        client = ExportClient()

        body, editor_state = prepare_export_start_request(
            client,
            "clip-current",
            {
                "clipId": "clip-current",
                "format": "mp4",
                "qualitySettings": {"resolution": "1080p"},
                "includeAudio": True,
            },
        )

        self.assertEqual(
            client.calls,
            [("/api/v1/clips/clip-current/delivery-state", None)],
        )
        self.assertEqual(body["expectedEditorVersion"], 7)
        self.assertEqual(body["expectedEditorStateHash"], EDITOR_HASH)
        self.assertRegex(body["idempotencyKey"], r"^agent-pack-export:")
        self.assertEqual(editor_state["snapshotId"], SNAPSHOT_ID)

    def test_explicit_retry_key_is_preserved(self):
        body, _ = prepare_export_start_request(
            ExportClient(),
            "clip-current",
            {"idempotencyKey": "same-export-retry-1"},
            requested_idempotency_key="same-export-retry-1",
        )

        self.assertEqual(body["idempotencyKey"], "same-export-retry-1")

    def test_conflicting_editor_pin_fails_closed(self):
        with self.assertRaisesRegex(ExportContractError, "conflicts"):
            prepare_export_start_request(
                ExportClient(),
                "clip-current",
                {"expectedEditorStateHash": "b" * 64},
            )

    def test_unverified_editor_state_fails_before_export(self):
        client = ExportClient(editor_delivery_state(editorStateStatus="missing"))

        with self.assertRaisesRegex(ExportContractError, "verified current"):
            prepare_export_start_request(client, "clip-current", {})

        self.assertEqual(len(client.calls), 1)


class FakeUploadResponse:
    def __init__(self):
        self.raise_calls = 0

    def raise_for_status(self):
        self.raise_calls += 1


class AssetClient:
    def __init__(self, signed):
        self.signed = signed
        self.calls = []

    def post(self, path, body=None):
        self.calls.append((path, body))
        if path == "/api/v1/assets/sign-upload":
            return self.signed
        if path == "/api/v1/assets/asset-1/finalize":
            return {"id": "asset-1", "status": "ready"}
        raise AssertionError(f"Unexpected request: {path}")


class AssetUploadContractTests(unittest.TestCase):
    def test_upload_uses_durable_intent_contract_and_canonical_url_alias(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "brand.png"
            file_path.write_bytes(b"image-bytes")
            client = AssetClient({
                "url": "https://storage.example/upload",
                "intentId": "11111111-1111-4111-8111-111111111111",
                "assetId": "asset-1",
                "headers": {"Content-Type": "image/png"},
            })
            upload_response = FakeUploadResponse()
            put_calls = []

            def put(url, data, headers, timeout):
                put_calls.append({
                    "url": url,
                    "data": data.read(),
                    "headers": headers,
                    "timeout": timeout,
                })
                return upload_response

            result = upload_library_asset(
                client,
                str(file_path),
                "image/png",
                requested_idempotency_key="asset-upload-retry-1",
                put=put,
            )

        self.assertEqual(result, {"id": "asset-1", "status": "ready"})
        self.assertEqual(client.calls[0], (
            "/api/v1/assets/sign-upload",
            {
                "filename": "brand.png",
                "contentType": "image/png",
                "size": 11,
                "idempotencyKey": "asset-upload-retry-1",
            },
        ))
        self.assertEqual(client.calls[1], (
            "/api/v1/assets/asset-1/finalize",
            {"uploadIntentId": "11111111-1111-4111-8111-111111111111"},
        ))
        self.assertEqual(put_calls[0]["data"], b"image-bytes")
        self.assertEqual(put_calls[0]["headers"]["Content-Length"], "11")
        self.assertEqual(upload_response.raise_calls, 1)

    def test_documented_upload_url_is_also_accepted(self):
        resolved = require_signed_asset_upload({
            "uploadUrl": "https://storage.example/upload",
            "intentId": "intent-1",
            "assetId": "asset-1",
        })

        self.assertEqual(resolved["uploadUrl"], "https://storage.example/upload")

    def test_missing_upload_intent_fails_closed(self):
        with self.assertRaisesRegex(AssetUploadContractError, "intentId"):
            require_signed_asset_upload({
                "url": "https://storage.example/upload",
                "assetId": "asset-1",
            })


if __name__ == "__main__":
    unittest.main()
