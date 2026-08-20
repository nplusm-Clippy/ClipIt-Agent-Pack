import unittest

from scripts.clipper_client import ClipperError
from scripts.enterprise_delivery_contract import (
    EnterpriseDeliveryContractError,
    deliver_export_to_client,
    list_enterprise_deliverables,
)


WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"
EXPORT_ID = "44444444-4444-4444-8444-444444444444"
EXPECTATIONS = {
    "enterpriseExecutionId": "55555555-5555-4555-8555-555555555555",
    "snapshotId": "66666666-6666-4666-8666-666666666666",
    "editorVersion": 7,
    "editorStateHash": "a" * 64,
    "outputObjectFingerprint": "b" * 64,
    "captionStyleHash": "c" * 64,
    "includeOutro": False,
    "artifactDuration": 68.533,
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


def completed_export(**overrides):
    value = {
        "id": EXPORT_ID,
        "status": "completed",
        "approvedArtifactDuration": EXPECTATIONS["artifactDuration"],
        **EXPECTATIONS,
    }
    value.update(overrides)
    return value


def deliverable(status="ready", export_id=EXPORT_ID, **overrides):
    value = {
        "id": "22222222-2222-4222-8222-222222222222",
        "workspaceId": WORKSPACE_ID,
        "exportId": export_id,
        "clipId": "clip-1",
        "title": "Finished clip",
        "note": None,
        "status": status,
        "verification": EXPECTATIONS.copy(),
    }
    value.update(overrides)
    return value


class FakeDeliveryClient:
    def __init__(self, *, identity=None, page=None, created=None, post_error=None, export=None):
        self.identity = identity or workspace_identity()
        self.page = page or {
            "deliverables": [deliverable()],
            "total": 1,
            "limit": 50,
            "offset": 0,
        }
        self.created = created or {"deliverable": deliverable()}
        self.post_error = post_error
        self.export = export or completed_export()
        self.calls = []

    def get_agent_identity(self):
        self.calls.append(("identity", None))
        return self.identity

    def get(self, path, params=None):
        self.calls.append((path, params))
        if path == "/api/v1/deliverables":
            return self.page
        if path == f"/api/v1/exports/{EXPORT_ID}":
            return self.export
        raise AssertionError(f"Unexpected GET: {path}")

    def post(self, path, body=None):
        self.calls.append((path, body))
        if self.post_error:
            raise self.post_error
        if path == "/api/v1/deliverables":
            return self.created
        raise AssertionError(f"Unexpected POST: {path}")


class EnterpriseDeliveryContractTests(unittest.TestCase):
    def test_list_preflights_exact_workspace_and_preserves_filters(self):
        client = FakeDeliveryClient(page={
            "deliverables": [deliverable(status="selected")],
            "total": 1,
            "limit": 25,
            "offset": 0,
        })

        result = list_enterprise_deliverables(
            client,
            WORKSPACE_ID,
            status="selected",
            export_id=EXPORT_ID,
            limit=25,
        )

        self.assertEqual(result["deliverables"][0]["status"], "selected")
        self.assertEqual(client.calls, [
            ("identity", None),
            (
                "/api/v1/deliverables",
                {
                    "limit": 25,
                    "offset": 0,
                    "status": "selected",
                    "exportId": EXPORT_ID,
                },
            ),
        ])

    def test_create_posts_only_exact_export_expectations(self):
        client = FakeDeliveryClient()

        result = deliver_export_to_client(
            client,
            WORKSPACE_ID,
            EXPORT_ID,
        )

        self.assertFalse(result["replayed"])
        self.assertEqual(result["deliverable"]["status"], "ready")
        self.assertEqual(client.calls, [
            ("identity", None),
            (f"/api/v1/exports/{EXPORT_ID}", None),
            (
                "/api/v1/deliverables",
                {
                    "exportId": EXPORT_ID,
                    "expectations": EXPECTATIONS,
                },
            ),
        ])

    def test_duplicate_recovers_exact_existing_selected_delivery(self):
        client = FakeDeliveryClient(
            page={
                "deliverables": [deliverable(status="selected")],
                "total": 1,
                "limit": 2,
                "offset": 0,
            },
            post_error=ClipperError(
                409,
                "DELIVERY_EXISTS",
                "This exact export has already been delivered",
            ),
        )

        result = deliver_export_to_client(
            client,
            WORKSPACE_ID,
            EXPORT_ID,
        )

        self.assertTrue(result["replayed"])
        self.assertEqual(result["deliverable"]["status"], "selected")
        self.assertEqual(client.calls[-1], (
            "/api/v1/deliverables",
            {"limit": 2, "offset": 0, "exportId": EXPORT_ID},
        ))

    def test_wrong_workspace_fails_before_delivery_mutation(self):
        client = FakeDeliveryClient()

        with self.assertRaisesRegex(RuntimeError, "different workspace"):
            deliver_export_to_client(
                client,
                "33333333-3333-4333-8333-333333333333",
                EXPORT_ID,
            )

        self.assertEqual(client.calls, [("identity", None)])

    def test_new_delivery_must_be_ready_not_selected(self):
        client = FakeDeliveryClient(created={
            "deliverable": deliverable(status="selected"),
        })

        with self.assertRaisesRegex(
            EnterpriseDeliveryContractError,
            "status is not ready",
        ):
            deliver_export_to_client(
                client,
                WORKSPACE_ID,
                EXPORT_ID,
            )

    def test_missing_exact_export_lineage_fails_before_delivery_mutation(self):
        client = FakeDeliveryClient(export=completed_export(captionStyleHash=None))

        with self.assertRaisesRegex(
            EnterpriseDeliveryContractError,
            "caption-style hash",
        ):
            deliver_export_to_client(client, WORKSPACE_ID, EXPORT_ID)

        self.assertEqual(client.calls, [
            ("identity", None),
            (f"/api/v1/exports/{EXPORT_ID}", None),
        ])

    def test_artifact_duration_must_match_the_approved_output_policy(self):
        client = FakeDeliveryClient(export=completed_export(artifactDuration=72.619))

        with self.assertRaisesRegex(
            EnterpriseDeliveryContractError,
            "approved output policy",
        ):
            deliver_export_to_client(client, WORKSPACE_ID, EXPORT_ID)

        self.assertFalse(any(call[0] == "/api/v1/deliverables" for call in client.calls))

    def test_cross_workspace_list_response_fails_closed(self):
        client = FakeDeliveryClient(page={
            "deliverables": [deliverable(
                workspaceId="33333333-3333-4333-8333-333333333333"
            )],
            "total": 1,
            "limit": 50,
            "offset": 0,
        })

        with self.assertRaisesRegex(
            EnterpriseDeliveryContractError,
            "different workspace",
        ):
            list_enterprise_deliverables(client, WORKSPACE_ID)


if __name__ == "__main__":
    unittest.main()
