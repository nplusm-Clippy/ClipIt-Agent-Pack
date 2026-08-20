import unittest

from scripts.initialize_editor_snapshot import initialize_editor_snapshot
from scripts.render_clip import render_clip


WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"
EXACT_STYLE = {
    "fontFamily": "Inter",
    "fontSize": 44,
    "fontSizeScale": 2,
    "fontWeight": 800,
    "color": "#ffffff",
    "backgroundColor": "transparent",
    "position": "bottom",
    "wordsPerLine": 2,
    "animation": "pop",
}


def workspace_identity(workspace_id=WORKSPACE_ID):
    return {
        "scope": {
            "identityType": "workspace_api_key",
            "enterprise": True,
            "workspaceId": workspace_id,
            "workspaceName": "Client Workspace",
            "workspaceStatus": "active",
            "workspaceRole": "team_operator",
            "resourceOwnerUserId": "owner-user-id",
            "billingMode": "enterprise_usage_only",
        }
    }


class FakeClient:
    def __init__(self, profile_name="enterprise-client", identity=None):
        self.profile_name = profile_name
        self.identity = identity or workspace_identity()
        self.calls = []

    def get_agent_identity(self):
        self.calls.append(("identity", None))
        return self.identity

    def post(self, path, body=None):
        self.calls.append((path, body))
        if path.endswith("/editor-snapshot/initialize"):
            captions_enabled = body.get("includeCaptions") is True
            caption_style = body.get("captionStyle")
            if captions_enabled and not isinstance(caption_style, dict):
                caption_style = EXACT_STYLE.copy()
            return {
                "schema": "clipit_agent_editor_snapshot",
                "version": 1,
                "created": True,
                "clipId": "clip-1",
                "editorVersion": 1,
                "editorStateHash": "a" * 64,
                "clipSettingsRevision": 3,
                "sourceObjectFingerprint": "b" * 64,
                "aspectRatio": "9:16",
                "fitBackground": "blur",
                "quality": "1080p",
                "captionsEnabled": captions_enabled,
                "captionPresetId": (
                    body.get("captionPresetId")
                    or ("gaming-neon" if body.get("captionStyle") == "neon" else None)
                ),
                "captionStyle": caption_style if captions_enabled else None,
                "captionStyleHash": "c" * 64 if captions_enabled else None,
            }
        if path.endswith("/render"):
            return {"jobId": "job-1", "status": "queued"}
        raise AssertionError(f"Unexpected POST: {path}")


class AgentEditorSnapshotTests(unittest.TestCase):
    def test_initialization_preflights_workspace_and_posts_only_bounded_fields(self):
        client = FakeClient()

        result = initialize_editor_snapshot(
            client,
            WORKSPACE_ID,
            "clip-1",
            aspect_ratio="9:16",
            fit_background="blur",
            quality="high",
        )

        self.assertTrue(result["created"])
        self.assertEqual(result["workspaceId"], WORKSPACE_ID)
        self.assertEqual(client.calls, [
            ("identity", None),
            (
                "/api/v1/clips/clip-1/editor-snapshot/initialize",
                {
                    "aspectRatio": "9:16",
                    "fitBackground": "blur",
                    "quality": "high",
                    "includeCaptions": False,
                },
            ),
        ])

    def test_initialization_sends_explicit_caption_style_when_enabled(self):
        client = FakeClient()
        result = initialize_editor_snapshot(
            client,
            WORKSPACE_ID,
            "clip-1",
            include_captions=True,
            caption_style="neon",
        )

        self.assertTrue(result["captionsEnabled"])
        self.assertEqual(result["captionPresetId"], "gaming-neon")
        self.assertEqual(client.calls[-1][1]["includeCaptions"], True)
        self.assertEqual(client.calls[-1][1]["captionStyle"], "neon")

    def test_initialization_round_trips_exact_caption_style_and_hash(self):
        client = FakeClient()

        result = initialize_editor_snapshot(
            client,
            WORKSPACE_ID,
            "clip-1",
            include_captions=True,
            caption_style=EXACT_STYLE,
        )

        self.assertEqual(result["captionStyle"], EXACT_STYLE)
        self.assertEqual(result["captionStyleHash"], "c" * 64)
        self.assertEqual(client.calls[-1][1]["captionStyle"], EXACT_STYLE)

    def test_initialization_rejects_default_personal_profile_before_network(self):
        client = FakeClient(profile_name="default")

        with self.assertRaisesRegex(RuntimeError, "named ClipIt profile"):
            initialize_editor_snapshot(client, WORKSPACE_ID, "clip-1")

        self.assertEqual(client.calls, [])

    def test_enterprise_direct_render_is_blocked_before_mutation(self):
        client = FakeClient()
        body = {
            "aspectRatio": "9:16",
            "quality": "high",
            "includeCaptions": False,
            "captionStyle": "minimal",
            "watermark": False,
            "autoReframe": False,
        }

        with self.assertRaisesRegex(RuntimeError, "exact caption settings"):
            render_clip(
                client,
                "clip-1",
                body,
                workspace_id=WORKSPACE_ID,
            )

        self.assertEqual(client.calls, [
            ("identity", None),
        ])

    def test_enterprise_no_caption_render_preserves_legacy_capability(self):
        client = FakeClient()
        body = {
            "aspectRatio": "9:16",
            "quality": "high",
            "includeCaptions": False,
            "watermark": False,
            "autoReframe": False,
        }

        result = render_clip(
            client,
            "clip-1",
            body,
            workspace_id=WORKSPACE_ID,
        )

        self.assertEqual(result["jobId"], "job-1")
        self.assertEqual(client.calls[-1], ("/api/v1/clips/clip-1/render", body))

    def test_wrong_workspace_fails_before_snapshot_or_render_mutation(self):
        client = FakeClient()
        wrong_workspace = "22222222-2222-4222-8222-222222222222"

        with self.assertRaisesRegex(RuntimeError, "different workspace"):
            initialize_editor_snapshot(client, wrong_workspace, "clip-1")

        self.assertEqual(client.calls, [("identity", None)])


if __name__ == "__main__":
    unittest.main()
