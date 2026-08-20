import unittest

from scripts.enterprise_exact_delivery_contract import (
    EnterpriseExactDeliveryContractError,
    advance_enterprise_exact_delivery,
    preflight_enterprise_exact_delivery,
)
from tests.test_agent_editor_snapshot import EXACT_STYLE, WORKSPACE_ID, workspace_identity


CLIP_ID = "22222222-2222-4222-8222-222222222222"
PLAN_HASH = "d" * 64
STYLE_HASH = "c" * 64
REQUEST = {
    "clipId": CLIP_ID,
    "expectedEditorVersion": 7,
    "expectedEditorStateHash": "a" * 64,
    "expectedClipSettingsRevision": 3,
    "captionStyle": EXACT_STYLE,
    "includeOutro": False,
    "maxCredits": 15,
}


def plan(**overrides):
    value = {
        "schema": "clipit_enterprise_exact_delivery_plan",
        "version": 1,
        "planHash": PLAN_HASH,
        "approved": True,
        "blockers": [],
        "target": {
            "workspaceId": WORKSPACE_ID,
            "clipId": CLIP_ID,
            "editorVersion": 7,
            "editorStateHash": "a" * 64,
            "clipSettingsRevision": 3,
            "sourceObjectFingerprint": "b" * 64,
        },
        "exactCaptionStyle": {
            "style": EXACT_STYLE.copy(),
            "styleHash": STYLE_HASH,
            "capability": {"unknownFields": "rejected"},
        },
        "outputPolicy": {
            "includeOutro": False,
            "expectedMainDuration": 68.533,
            "expectedFinalDuration": 68.533,
        },
        "usage": {
            "settlementMode": "enterprise_usage_only",
            "clientCreditChargeClip": 0,
            "maxCredits": 15,
            "withinApprovalCap": True,
            "spendLimitViolation": None,
        },
    }
    value.update(overrides)
    return value


def receipt(state="processing", **overrides):
    value = {
        "schema": "clipit_enterprise_exact_delivery_receipt",
        "version": 1,
        "state": state,
        "stage": "render" if state == "processing" else "completed",
        "planHash": PLAN_HASH,
        "resumeToken": "journal-1" if state != "completed" else None,
        "clipId": CLIP_ID,
        "captionStyleHash": STYLE_HASH,
        "includeOutro": False,
        "renderJobId": "render-1" if state == "processing" else None,
        "exportJobId": None if state == "processing" else "export-1",
        "deliveryId": None if state == "processing" else "delivery-1",
        "lineage": {
            "expectedFinalDuration": 68.533,
            "editorStateHash": "e" * 64 if state == "completed" else None,
            "outputObjectFingerprint": "f" * 64 if state == "completed" else None,
            "artifactDuration": 68.533 if state == "completed" else None,
        },
        "error": None,
    }
    value.update(overrides)
    return value


class FakeRecipeClient:
    def __init__(self, results):
        self.profile_name = "enterprise-client"
        self.results = list(results)
        self.calls = []

    def get_agent_identity(self):
        self.calls.append(("identity", None))
        return workspace_identity()

    def post(self, path, body):
        self.calls.append((path, body))
        return {"success": True, "result": self.results.pop(0)}


class EnterpriseExactDeliveryContractTests(unittest.TestCase):
    def test_preflight_is_one_read_only_tool_call_with_exact_target(self):
        client = FakeRecipeClient([plan()])

        result = preflight_enterprise_exact_delivery(
            client,
            WORKSPACE_ID,
            REQUEST,
        )

        self.assertEqual(result["planHash"], PLAN_HASH)
        payload = client.calls[-1][1]
        self.assertEqual(payload["functionName"], "deliverEnterpriseClipExact")
        self.assertEqual(payload["parameters"]["action"], "preflight")
        self.assertNotIn("confirmed", payload)

    def test_first_advance_binds_plan_and_idempotency_key(self):
        client = FakeRecipeClient([receipt()])

        result = advance_enterprise_exact_delivery(
            client,
            plan(),
            REQUEST,
            idempotency_key="same-exact-operation",
        )

        self.assertEqual(result["resumeToken"], "journal-1")
        parameters = client.calls[-1][1]["parameters"]
        self.assertEqual(parameters["planHash"], PLAN_HASH)
        self.assertEqual(parameters["idempotencyKey"], "same-exact-operation")

    def test_resume_accepts_completed_receipt_with_current_render(self):
        client = FakeRecipeClient([receipt(state="completed")])

        result = advance_enterprise_exact_delivery(
            client,
            plan(),
            REQUEST,
            resume_token="journal-1",
        )

        self.assertEqual(result["state"], "completed")
        self.assertIsNone(result["renderJobId"])
        self.assertEqual(
            client.calls[-1][1]["parameters"]["resumeToken"],
            "journal-1",
        )

    def test_changed_style_plan_fails_before_approval(self):
        changed = plan()
        changed["exactCaptionStyle"]["style"]["fontSizeScale"] = 1
        client = FakeRecipeClient([changed])

        with self.assertRaisesRegex(
            EnterpriseExactDeliveryContractError,
            "fontSizeScale",
        ):
            preflight_enterprise_exact_delivery(client, WORKSPACE_ID, REQUEST)

    def test_plan_duration_must_match_explicit_outro_policy(self):
        changed = plan()
        changed["outputPolicy"]["expectedFinalDuration"] = 72.533
        client = FakeRecipeClient([changed])

        with self.assertRaisesRegex(
            EnterpriseExactDeliveryContractError,
            "duration",
        ):
            preflight_enterprise_exact_delivery(client, WORKSPACE_ID, REQUEST)

    def test_blocked_receipt_requires_typed_error_and_resume_token(self):
        client = FakeRecipeClient([receipt(state="blocked")])

        with self.assertRaisesRegex(
            EnterpriseExactDeliveryContractError,
            "typed error",
        ):
            advance_enterprise_exact_delivery(
                client,
                plan(),
                REQUEST,
                resume_token="journal-1",
            )

        blocked = receipt(
            state="blocked",
            error={"code": "RENDER_DISABLED", "message": "Rendering is disabled."},
        )
        client = FakeRecipeClient([blocked])
        result = advance_enterprise_exact_delivery(
            client,
            plan(),
            REQUEST,
            resume_token="journal-1",
        )

        self.assertEqual(result["state"], "blocked")

    def test_completed_receipt_duration_must_match_approved_output(self):
        changed = receipt(state="completed")
        changed["lineage"]["artifactDuration"] = 72.618
        client = FakeRecipeClient([changed])

        with self.assertRaisesRegex(
            EnterpriseExactDeliveryContractError,
            "artifact duration",
        ):
            advance_enterprise_exact_delivery(
                client,
                plan(),
                REQUEST,
                resume_token="journal-1",
            )


if __name__ == "__main__":
    unittest.main()
