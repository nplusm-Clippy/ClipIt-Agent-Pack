import tempfile
import unittest
from pathlib import Path

from scripts.exact_caption_style_contract import (
    ExactCaptionStyleContractError,
    parse_json_object,
    set_exact_caption_style,
)
from tests.test_agent_editor_snapshot import EXACT_STYLE, WORKSPACE_ID, workspace_identity


class FakeStyleClient:
    def __init__(self, profile_name="enterprise-client", response=None):
        self.profile_name = profile_name
        self.response = response or {
            "schema": "clipit_exact_caption_style",
            "version": 1,
            "updated": True,
            "clipId": "clip-1",
            "editorVersion": 8,
            "editorStateHash": "d" * 64,
            "clipSettingsRevision": 4,
            "captionPresetId": None,
            "captionStyle": EXACT_STYLE.copy(),
            "captionStyleHash": "c" * 64,
            "renderRequired": True,
            "renderQueued": False,
            "capability": {
                "unknownFields": "rejected",
            },
        }
        self.calls = []

    def get_agent_identity(self):
        self.calls.append(("identity", None))
        return workspace_identity()

    def patch(self, path, body):
        self.calls.append((path, body))
        return self.response


class ExactCaptionStyleContractTests(unittest.TestCase):
    def test_set_style_pins_identity_and_returns_verified_hash(self):
        client = FakeStyleClient()

        result = set_exact_caption_style(
            client,
            WORKSPACE_ID,
            "clip-1",
            EXACT_STYLE,
            7,
            "a" * 64,
            3,
        )

        self.assertEqual(result["captionStyleHash"], "c" * 64)
        self.assertEqual(client.calls[-1], (
            "/api/v1/clips/clip-1/editor-snapshot/caption-style",
            {
                "expectedEditorVersion": 7,
                "expectedEditorStateHash": "a" * 64,
                "expectedClipSettingsRevision": 3,
                "captionStyle": EXACT_STYLE,
            },
        ))

    def test_style_readback_mismatch_fails_closed(self):
        response = FakeStyleClient().response
        response["captionStyle"] = {**EXACT_STYLE, "fontSizeScale": 1}
        client = FakeStyleClient(response=response)

        with self.assertRaisesRegex(
            ExactCaptionStyleContractError,
            "fontSizeScale",
        ):
            set_exact_caption_style(
                client,
                WORKSPACE_ID,
                "clip-1",
                EXACT_STYLE,
                7,
                "a" * 64,
                3,
            )

    def test_json_file_input_is_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "style.json"
            path.write_text('{"presetId":"tiktok-viral","fontSizeScale":2}', encoding="utf-8")

            parsed = parse_json_object(f"@{path}")

        self.assertEqual(parsed, {
            "presetId": "tiktok-viral",
            "fontSizeScale": 2,
        })


if __name__ == "__main__":
    unittest.main()
