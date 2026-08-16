import unittest

from scripts.clipper_client import ClipperError
from scripts.enterprise_delivery_contract import (
    EnterpriseDeliveryContractError,
    deliver_export_to_client,
    list_enterprise_deliverables,
)


WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"


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


def deliverable(status="ready", export_id="export-1", **overrides):
    value = {
        "id": "22222222-2222-4222-8222-222222222222",
        "workspaceId": WORKSPACE_ID,
        "exportId": export_id,
        "clipId": "clip-1",
        "title": "Finished clip",
        "note": None,
        "status": status,
    }
    value.update(overrides)
    return value


class FakeDeliveryClient:
    def __init__(self, *, identity=None, page=None, created=None, post_error=None):
        self.identity = identity or workspace_identity()
        self.page = page or {
            "deliverables": [deliverable()],
            "total": 1,
            "limit": 50,
            "offset": 0,
        }
        self.created = created or {"deliverable": deliverable()}
        self.post_error = post_error
        self.calls = []

    def get_agent_identity(self):
        self.calls.append(("identity", None))
        return self.identity

    def get(self, path, params=None):
        self.calls.append((path, params))
        if path == "/api/v1/deliverables":
            return self.page
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
            export_id="export-1",
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
                    "exportId": "export-1",
                },
            ),
        ])

    def test_create_posts_only_ready_delivery_fields(self):
        client = FakeDeliveryClient()

        result = deliver_export_to_client(
            client,
            WORKSPACE_ID,
            "export-1",
            " Finished clip ",
            note=" Review this ",
        )

        self.assertFalse(result["replayed"])
        self.assertEqual(result["deliverable"]["status"], "ready")
        self.assertEqual(client.calls, [
            ("identity", None),
            (
                "/api/v1/deliverables",
                {
                    "exportId": "export-1",
                    "title": "Finished clip",
                    "note": "Review this",
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
            "export-1",
            "Finished clip",
        )

        self.assertTrue(result["replayed"])
        self.assertEqual(result["deliverable"]["status"], "selected")
        self.assertEqual(client.calls[-1], (
            "/api/v1/deliverables",
            {"limit": 2, "offset": 0, "exportId": "export-1"},
        ))

    def test_wrong_workspace_fails_before_delivery_mutation(self):
        client = FakeDeliveryClient()

        with self.assertRaisesRegex(RuntimeError, "different workspace"):
            deliver_export_to_client(
                client,
                "33333333-3333-4333-8333-333333333333",
                "export-1",
                "Finished clip",
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
                "export-1",
                "Finished clip",
            )

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
