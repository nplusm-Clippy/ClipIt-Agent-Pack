import tempfile
import unittest
from pathlib import Path

from scripts.exact_caption_style_contract import (
    ExactCaptionStyleContractError,
    parse_caption_style_directive,
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

    def test_caption_directive_maps_percentage_and_single_line_layout(self):
        for directive, expected in (
            ("caption size 200% single", {
                "fontSizeScale": 2,
                "captionLineMode": "single-line",
            }),
            ("\tCAPTION\tSIZE\t200%\tSINGLE-LINE.\t", {
                "fontSizeScale": 2,
                "captionLineMode": "single-line",
            }),
            ("  CAPTIONS   SIZE  150%  SINGLE LINE  ", {
                "fontSizeScale": 1.5,
                "captionLineMode": "single-line",
            }),
            ("caption size 50% single-line", {
                "fontSizeScale": 0.5,
                "captionLineMode": "single-line",
            }),
            ("caption size 125% single - line.", {
                "fontSizeScale": 1.25,
                "captionLineMode": "single-line",
            }),
            ("caption size 100% auto", {
                "fontSizeScale": 1,
                "captionLineMode": "auto",
            }),
            ("caption size 300% stacked", {
                "fontSizeScale": 3,
                "captionLineMode": "stacked",
            }),
        ):
            with self.subTest(directive=directive):
                self.assertEqual(parse_caption_style_directive(directive), expected)

    def test_caption_directive_rejects_out_of_range_or_ambiguous_text(self):
        for directive in (
            "caption size 301% single",
            "caption size 49% single",
            "single clip caption size 200%",
            "caption size 200% single word",
            "caption size 200% single--line",
            "caption size 200% single---line",
            "caption size ٢٠٠% single",
            "caption size 050% single",
            "caption size 050.0% single",
            "caption ſize 200% single",
            "captıon size 200% single",
            "caption size 200% ſingle",
            "caption size 200% stacKed",
            "caption\u00a0size 200% single",
            "caption\u2003size 200% single",
            "caption\u0085size 200% single",
            "\ufeffcaption size 200% single",
            "caption\nsize 200% single",
        ):
            with self.subTest(directive=directive):
                with self.assertRaises(ExactCaptionStyleContractError):
                    parse_caption_style_directive(directive)

    def test_caption_directive_grammar_error_lists_single_line(self):
        with self.assertRaisesRegex(
            ExactCaptionStyleContractError,
            "single-line",
        ):
            parse_caption_style_directive("caption size 200% single--line")

    def test_set_directive_pins_identity_and_verifies_canonical_patch(self):
        client = FakeStyleClient()

        result = set_exact_caption_style(
            client,
            WORKSPACE_ID,
            "clip-1",
            None,
            7,
            "a" * 64,
            3,
            directive="caption size 200% single",
        )

        self.assertEqual(result["captionStyle"]["wordsPerLine"], 2)
        self.assertEqual(client.calls[-1], (
            "/api/v1/clips/clip-1/editor-snapshot/caption-style",
            {
                "expectedEditorVersion": 7,
                "expectedEditorStateHash": "a" * 64,
                "expectedClipSettingsRevision": 3,
                "captionDirective": "caption size 200% single",
            },
        ))

    def test_directive_line_layout_readback_mismatch_fails_closed(self):
        response = FakeStyleClient().response
        response["captionStyle"] = {**EXACT_STYLE, "captionLineMode": "auto"}
        client = FakeStyleClient(response=response)

        with self.assertRaisesRegex(
            ExactCaptionStyleContractError,
            "captionLineMode",
        ):
            set_exact_caption_style(
                client,
                WORKSPACE_ID,
                "clip-1",
                None,
                7,
                "a" * 64,
                3,
                directive="caption size 200% single",
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
