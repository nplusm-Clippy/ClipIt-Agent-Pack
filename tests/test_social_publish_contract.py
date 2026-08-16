import unittest

from scripts.social_publish_contract import (
    SocialPublishContractError,
    is_enterprise_key,
    parse_account_id_pins,
    parse_platforms,
    prepare_social_publish_request,
    require_exact_current_delivery_state,
)


SNAPSHOT_ID = "11111111-1111-4111-8111-111111111111"
EDITOR_HASH = "a" * 64
OUTPUT_FINGERPRINT = "b" * 64


def exact_delivery_state(requested_export_id=None):
    editor_state = {
        "snapshotId": SNAPSHOT_ID,
        "editorVersion": 4,
        "editorStateHash": EDITOR_HASH,
        "stateSource": "current_editor_snapshot",
    }
    selected_export = {
        "exportId": "export-current",
        "snapshotId": SNAPSHOT_ID,
        "editorVersion": 4,
        "editorStateHash": EDITOR_HASH,
        "outputObjectFingerprint": OUTPUT_FINGERPRINT,
        "exactlyMatchesEditor": True,
        "inspectionStatus": "verified",
        "blockers": [],
    }
    return {
        "schema": "clipit_clip_delivery_state",
        "version": 2,
        "clipId": "clip-current",
        "editorStateStatus": "verified",
        "editorState": editor_state,
        "selection": {
            "requestedExportId": requested_export_id,
            "status": "selected",
            "selectedExportId": "export-current",
        },
        "selectedExport": selected_export,
        "readyToPublish": True,
        "deliveryBlockers": [],
    }


def identity(enterprise=False):
    return {
        "apiKey": {
            "agentInfo": (
                {"type": "enterprise_hermes", "version": "1.0"}
                if enterprise
                else {"type": "generic", "version": "1.0"}
            )
        }
    }


class FakeClient:
    def __init__(self, *, enterprise=False, accounts=None, delivery_state=None):
        self.enterprise = enterprise
        self.accounts = accounts or []
        self.delivery_state = delivery_state or exact_delivery_state()
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        if path == "/api/v1/agent/me":
            return identity(self.enterprise)
        if path == "/api/v1/social/accounts":
            return {"accounts": self.accounts}
        if path == "/api/v1/clips/clip-current/delivery-state":
            return self.delivery_state
        raise AssertionError(f"Unexpected request: {path}")


class SocialPublishContractTests(unittest.TestCase):
    def test_authoritative_workspace_scope_wins_over_generic_agent_info(self):
        self.assertTrue(is_enterprise_key({
            "scope": {
                "identityType": "workspace_api_key",
                "enterprise": True,
            },
            "apiKey": {"agentInfo": {"type": "generic"}},
        }))

    def test_authoritative_personal_scope_prevents_legacy_enterprise_fallback(self):
        self.assertFalse(is_enterprise_key({
            "scope": {
                "identityType": "personal_api_key",
                "enterprise": False,
            },
            "apiKey": {"agentInfo": {"type": "enterprise_hermes"}},
        }))

    def test_legacy_agent_info_is_used_only_when_scope_is_absent(self):
        self.assertTrue(is_enterprise_key({
            "apiKey": {"agentInfo": {"type": "enterprise_hermes"}},
        }))
        self.assertFalse(is_enterprise_key({
            "scope": None,
            "apiKey": {"agentInfo": {"type": "enterprise_hermes"}},
        }))

    def test_enterprise_schedule_pins_delivery_and_one_granted_account(self):
        client = FakeClient(
            enterprise=True,
            accounts=[{
                "platform": "linkedin",
                "connected": True,
                "accountId": "linkedin-company-42",
                "accountName": "Client Company",
            }],
            delivery_state=exact_delivery_state("export-current"),
        )

        body = prepare_social_publish_request(
            client,
            clip_id="clip-current",
            platforms=["linkedin"],
            caption="Approved caption",
            requested_account_ids={"linkedin": "linkedin-company-42"},
            requested_export_id="export-current",
            scheduled_for="2026-08-20T14:00:00Z",
            enterprise_deliverable_id="22222222-2222-4222-8222-222222222222",
        )

        self.assertEqual(
            client.calls,
            [
                ("/api/v1/agent/me", None),
                (
                    "/api/v1/clips/clip-current/delivery-state",
                    {"exportId": "export-current"},
                ),
                ("/api/v1/social/accounts", None),
            ],
        )
        self.assertEqual(body["exportId"], "export-current")
        self.assertEqual(body["expectedSnapshotId"], SNAPSHOT_ID)
        self.assertEqual(
            body["expectedOutputObjectFingerprint"], OUTPUT_FINGERPRINT
        )
        self.assertEqual(
            body["expectedAccountIds"], {"linkedin": "linkedin-company-42"}
        )
        self.assertIs(body["publishExactCurrentArtifact"], True)
        self.assertEqual(body["platforms"], ["linkedin"])
        self.assertEqual(body["scheduledFor"], "2026-08-20T14:00:00Z")
        self.assertEqual(
            body["enterpriseDeliverableId"],
            "22222222-2222-4222-8222-222222222222",
        )

    def test_enterprise_rejects_multiple_platforms_before_artifact_lookup(self):
        client = FakeClient(enterprise=True)

        with self.assertRaisesRegex(
            SocialPublishContractError,
            "one exact platform/account",
        ):
            prepare_social_publish_request(
                client,
                clip_id="clip-current",
                platforms=["linkedin", "twitter"],
                caption="Caption",
            )

        self.assertEqual(client.calls, [("/api/v1/agent/me", None)])

    def test_ordinary_key_keeps_multi_platform_support_with_exact_pins(self):
        client = FakeClient(
            accounts=[
                {
                    "platform": "linkedin",
                    "connected": True,
                    "accountId": "linkedin-personal",
                },
                {
                    "platform": "twitter",
                    "connected": True,
                    "accountId": "x-personal",
                },
            ]
        )

        body = prepare_social_publish_request(
            client,
            clip_id="clip-current",
            platforms=["linkedin", "twitter"],
            caption="Caption",
        )

        self.assertEqual(body["platforms"], ["linkedin", "twitter"])
        self.assertEqual(
            body["expectedAccountIds"],
            {"linkedin": "linkedin-personal", "twitter": "x-personal"},
        )

    def test_multiple_connected_accounts_require_an_explicit_account_id(self):
        client = FakeClient(
            accounts=[
                {
                    "platform": "linkedin",
                    "connected": True,
                    "accountId": "linkedin-one",
                },
                {
                    "platform": "linkedin",
                    "connected": True,
                    "accountId": "linkedin-two",
                },
            ]
        )

        with self.assertRaisesRegex(
            SocialPublishContractError,
            "multiple connected/granted accounts",
        ):
            prepare_social_publish_request(
                client,
                clip_id="clip-current",
                platforms=["linkedin"],
                caption="Caption",
            )

    def test_delivery_state_fails_closed_for_a_stale_output(self):
        state = exact_delivery_state()
        state["selectedExport"] = {
            **state["selectedExport"],
            "exactlyMatchesEditor": False,
        }

        with self.assertRaisesRegex(
            SocialPublishContractError,
            "verified exact-current export",
        ):
            require_exact_current_delivery_state(state, "clip-current")

    def test_cli_parsers_normalize_x_and_exact_account_pairs(self):
        self.assertEqual(parse_platforms("linkedin,X,linkedin"), ["linkedin", "twitter"])
        self.assertEqual(
            parse_account_id_pins("linkedin=company-page,x=x-account"),
            {"linkedin": "company-page", "twitter": "x-account"},
        )


if __name__ == "__main__":
    unittest.main()
