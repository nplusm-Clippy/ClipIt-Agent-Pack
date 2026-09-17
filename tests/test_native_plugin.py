import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from clipit_plugin.client import ClipItClient, ClipItError, Settings, operation_request, redact, validate_base_url
from clipit_plugin.registration import TOOL_SCHEMAS, register
from clipit_plugin.runtime import Runtime


def response(value, status=200, headers=None):
    obj = Mock()
    obj.status_code = status
    obj.headers = {"Content-Type": "application/json", "X-Request-Id": "request-123", **(headers or {})}
    obj.iter_content.return_value = [json.dumps(value).encode()]
    obj.__enter__ = Mock(return_value=obj)
    obj.__exit__ = Mock(return_value=False)
    return obj


class NativeClientTests(unittest.TestCase):
    def setUp(self):
        self.session = Mock()
        self.client = ClipItClient(Settings("https://clipit.dev", "test-secret-not-real"), self.session)

    def test_get_retries_transport_only(self):
        self.session.request.side_effect = [requests.ConnectionError(), response({"items": []})]
        self.assertEqual(self.client.call("runs"), {"items": []})
        self.assertEqual(self.session.request.call_count, 2)
        self.assertFalse(self.session.request.call_args.kwargs["allow_redirects"])

    def test_mutation_does_not_retry_after_unknown_outcome(self):
        self.session.request.side_effect = requests.Timeout()
        with self.assertRaises(ClipItError) as caught:
            self.client.call("orchestrate", {"body": {"idempotencyKey": "stable-key", "request": {"userMessage": "make clips"}}})
        self.assertEqual(caught.exception.code, "OUTCOME_UNKNOWN")
        self.assertEqual(caught.exception.operation_key, "stable-key")
        self.assertEqual(self.session.request.call_count, 1)

    def test_malformed_mutation_response_keeps_unknown_outcome(self):
        self.session.request.return_value = response({}, headers={"Content-Type": "text/html"})
        with self.assertRaises(ClipItError) as caught:
            self.client.call("execute", {"body": {"request": {}, "idempotencyKey": "same-original-key"}})
        self.assertTrue(caught.exception.public()["error"]["outcomeUnknown"])
        self.assertEqual(caught.exception.operation_key, "same-original-key")
        self.assertEqual(self.session.request.call_count, 1)

    def test_rate_limit_retains_retry_after(self):
        self.session.request.return_value = response({"error": {"code": "RATE_LIMITED", "message": "Wait"}}, 429, {"Retry-After": "60"})
        with self.assertRaises(ClipItError) as caught:
            self.client.call("runs")
        self.assertEqual(caught.exception.retry_after, 60)
        self.assertEqual(self.session.request.call_count, 1)

    def test_html_error_preserves_read_status_without_response_content(self):
        self.session.request.return_value = response("private upstream page", 404, {"Content-Type": "text/html"})
        with self.assertRaises(ClipItError) as caught:
            self.client.call("compatibility")
        self.assertEqual(caught.exception.status, 404)
        self.assertEqual(caught.exception.request_id, "request-123")
        self.assertNotIn("private upstream page", json.dumps(caught.exception.public()))
        self.assertEqual(self.session.request.call_count, 1)

    def test_html_mutation_error_retains_unknown_outcome(self):
        self.session.request.return_value = response({}, 404, {"Content-Type": "text/html"})
        with self.assertRaises(ClipItError) as caught:
            self.client.call("execute", {"body": {"request": {}, "idempotencyKey": "original-key"}})
        self.assertEqual(caught.exception.code, "OUTCOME_UNKNOWN")
        self.assertEqual(caught.exception.operation_key, "original-key")
        self.assertEqual(self.session.request.call_count, 1)

    def test_redirect_never_forwards_credentials(self):
        self.session.request.return_value = response({}, 302, {"Location": "https://attacker.invalid"})
        with self.assertRaisesRegex(ClipItError, "redirected"):
            self.client.call("runs")
        self.assertEqual(self.session.request.call_count, 1)

    def test_response_size_is_bounded(self):
        value = response({})
        value.iter_content.return_value = [b"a" * 65536] * 33
        self.session.request.return_value = value
        with self.assertRaises(ClipItError) as caught:
            self.client.call("runs")
        self.assertEqual(caught.exception.code, "RESPONSE_TOO_LARGE")

    def test_rejects_html_and_invalid_json(self):
        for value in [response({}, headers={"Content-Type": "text/html"}), response({})]:
            value.iter_content.return_value = [b"not json"]
            self.session.request.return_value = value
            with self.assertRaises(ClipItError):
                self.client.call("runs")

    def test_public_values_redact_nested_secrets_and_transient_media(self):
        self.session.request.return_value = response({"apiKey": "abc", "nested": [{"message": "test-secret-not-real"}], "url": "https://media.invalid/a?X-Amz-Signature=secret"})
        value = self.client.call("run", {"id": "owned-run"})
        self.assertNotIn("test-secret-not-real", json.dumps(value))
        self.assertNotIn("X-Amz-Signature", json.dumps(value))
        self.assertEqual(value["apiKey"], "[redacted]")

    def test_bound_media_refresh_keeps_url_but_not_credential(self):
        self.session.request.return_value = response({"url": "https://media.invalid/a?X-Amz-Signature=signed", "token": "Bearer test-secret-not-real"})
        value = self.client.call("download", {"id": "clip-1", "query": {"exportId": "export-1"}}, media=True)
        self.assertIn("X-Amz-Signature", value["url"])
        self.assertNotIn("test-secret-not-real", json.dumps(value))

    def test_flat_server_error_preserves_machine_code_and_request_id(self):
        self.session.request.return_value = response({"code": "CURSOR_EXPIRED", "error": "Restart page", "requestId": "body-request"}, 410, {"X-Request-Id": ""})
        with self.assertRaises(ClipItError) as caught:
            self.client.call("events", {"id": "run-1"})
        self.assertEqual(caught.exception.code, "CURSOR_EXPIRED")
        self.assertEqual(caught.exception.request_id, "body-request")

    def test_cross_harness_operation_keys_preserve_colons_and_periods(self):
        key = "python:edit.v1-123"
        method, path, _query, _body = operation_request("operation", {"id": key})
        self.assertEqual(method, "GET")
        self.assertTrue(path.endswith("python%3Aedit.v1-123"))
        operation_request("execute", {"body": {"idempotencyKey": key, "request": {}}})
        with self.assertRaises(ClipItError):
            operation_request("operation", {"id": "../bad-key"})

    def test_fixed_operation_map_rejects_proxy_inputs(self):
        for operation, args in [("https://other.invalid", {}), ("run", {"id": "../me"}), ("run", {"id": "x%2Fy"}),
                                ("runs", {"headers": {}}), ("runs", {"query": {"url": "https://other.invalid"}}),
                                ("runs", {"query": {"limit": 101}}), ("events", {"id": "x", "query": {"limit": 251}}),
                                ("execute", {"body": {"request": {}}})]:
            with self.subTest(operation=operation, args=args), self.assertRaises(ClipItError):
                operation_request(operation, args)

    def test_list_cannot_silently_treat_wrong_contract_as_empty(self):
        self.session.request.return_value = response({"unexpected": []})
        with self.assertRaises(ClipItError) as caught:
            self.client.call("runs")
        self.assertEqual(caught.exception.code, "INVALID_RESPONSE")

    def test_base_url_boundaries(self):
        for url in ["http://clipit.dev", "https://user:secret@clipit.dev", "https://clipit.dev/a", "https://169.254.169.254", "https://unapproved.invalid", "https://clipit.dev?token=x"]:
            with self.subTest(url=url), self.assertRaises(ClipItError):
                validate_base_url(url)
        self.assertEqual(validate_base_url("https://staging.example.test", allowed_hosts=["staging.example.test"]), "https://staging.example.test")
        self.assertEqual(validate_base_url("http://127.0.0.1:1234", allow_local=True), "http://127.0.0.1:1234")

    def test_declines_cheaper_and_missing_digest(self):
        for decision in ["cheaper", "approved"]:
            with self.assertRaises(ClipItError):
                operation_request("approval", {"id": "run", "body": {"idempotencyKey": "approval-key", "approvalId": "id", "decision": decision}})


class NativeRuntimeTests(unittest.TestCase):
    def test_old_server_html_404_reports_connected_upgrade_required(self):
        session = Mock()
        session.request.side_effect = [
            response({"user": {"id": "user"}, "apiKey": {"id": "key-id"}, "scope": {"enterprise": True}}),
            response({}, 404, {"Content-Type": "text/html"}),
        ]
        settings = Settings("https://clipit.dev", "test-secret")
        runtime = Runtime(lambda: settings, lambda current: ClipItClient(current, session))
        result = runtime.status()
        self.assertTrue(result["connected"])
        self.assertTrue(result["compatibility"]["upgradeRequired"])
        self.assertIsNone(result["compatibility"]["contractVersion"])
        self.assertTrue(result["scope"]["enterprise"])
        self.assertEqual(result["credentialId"], "key-id")

    def test_real_identity_metadata_survives_redaction(self):
        session = Mock()
        session.request.side_effect = [response({"user": {"id": "user"}, "apiKey": {"id": "key-id", "permissions": {"clippy_agent": True}}, "scope": {"enterprise": False}}),
                                       response({"contractVersion": "2026-09-16", "features": {}})]
        settings = Settings("https://clipit.dev", "test-secret")
        runtime = Runtime(lambda: settings, lambda current: ClipItClient(current, session))
        result = runtime.status()
        self.assertEqual(result["credentialId"], "key-id")
        self.assertTrue(result["permissions"]["clippy_agent"])
        self.assertNotIn("test-secret", json.dumps(result))

    def test_named_workspace_and_credential_labels_are_bounded_and_private(self):
        runtime = Runtime(lambda: Settings("https://clipit.dev", "test-secret"))
        runtime.call = Mock(side_effect=[{"user": {"id": "user", "username": "Personal name", "email": "private@example.test"},
            "apiKey": {"id": "key", "keyName": "  QA   connection  "}, "scope": {"workspaceName": " Studio   Équipe "}},
            {"contractVersion": "2026-09-16"}])
        value = runtime.status()
        self.assertEqual(value["accountLabel"], "Studio Équipe")
        self.assertEqual(value["credentialLabel"], "QA connection")
        self.assertNotIn("private@example.test", json.dumps(value))
        runtime.call = Mock(side_effect=[{"user": {"username": "x" * 300}, "apiKey": {}, "scope": {}}, {}])
        self.assertEqual(len(runtime.status()["accountLabel"]), 240)
        runtime.call = Mock(side_effect=[{"user": {}, "apiKey": {}, "scope": {}}, {}])
        self.assertEqual(runtime.status()["accountLabel"], "Personal workspace")

    def test_resource_search_remains_a_bounded_portable_read(self):
        method, path, query, body = operation_request("resources", {"query": {"kind": "clip", "search": "Interview", "limit": 25}})
        self.assertEqual((method, path), ("GET", "/api/v1/agent/platform/resources"))
        self.assertEqual(query, {"kind": "clip", "search": "Interview", "limit": 25})
        self.assertEqual(body, {})
        with self.assertRaises(ClipItError):
            operation_request("resources", {"url": "https://unapproved.invalid"})

    def test_registration_is_inert_and_complete(self):
        context = Mock()
        with patch.object(requests.Session, "request", side_effect=AssertionError("registration performed network IO")):
            register(context)
        self.assertEqual(context.register_tool.call_count, 8)
        self.assertEqual(context.register_skill.call_count, 18)
        self.assertEqual(context.register_command.call_count, 3)
        self.assertEqual(context.register_cli_command.call_args.kwargs["name"], "clipit")
        self.assertTrue(all(call.kwargs["override"] is False for call in context.register_tool.call_args_list))
        self.assertEqual(len({schema["name"] for schema in TOOL_SCHEMAS}), 8)
        context.on_unload.call_args.args[0]()

    def test_native_cli_doctor_dispatches_the_same_runtime(self):
        import argparse
        import io
        from contextlib import redirect_stdout
        context = Mock()
        with patch("clipit_plugin.registration.Runtime") as runtime:
            runtime.return_value.tool_json.return_value = '{"pluginVersion":"3.0.0"}'
            register(context)
            command = context.register_cli_command.call_args.kwargs
            parser = argparse.ArgumentParser()
            command["setup_fn"](parser)
            output = io.StringIO()
            with redirect_stdout(output):
                command["handler_fn"](parser.parse_args(["doctor"]))
            self.assertEqual(json.loads(output.getvalue())["pluginVersion"], "3.0.0")
            runtime.return_value.tool_json.assert_called_once_with("clipit_status", {"doctor": True})

    def test_unload_clears_same_package_gateway_pool(self):
        bridge = SimpleNamespace(__file__=str(ROOT / "dashboard/plugin_api.py"), runtime=Mock())
        context = Mock()
        with patch.dict(sys.modules, {"hermes_dashboard_plugin_clipit": bridge}):
            register(context)
            context.on_unload.call_args.args[0]()
        bridge.runtime.reset.assert_called_once()

    def test_rotation_closes_old_client_and_clears_authority(self):
        old, new = Settings("https://clipit.dev", "first"), Settings("https://clipit.dev", "second")
        clients = [Mock(), Mock()]
        runtime = Runtime(Mock(side_effect=[old, new]), Mock(side_effect=clients))
        runtime.call("runs")
        runtime.call("runs")
        clients[0].close.assert_called_once()
        self.assertEqual(runtime._scope, new.scope)
        runtime.close()
        clients[1].close.assert_called_once()

    def test_stale_connection_refuses_mutation_before_network(self):
        factory = Mock()
        runtime = Runtime(lambda: Settings("https://clipit.dev", "new"), factory)
        with self.assertRaises(ClipItError) as caught:
            runtime.call("execute", {}, connection_id=Settings("https://clipit.dev", "old").scope)
        self.assertEqual(caught.exception.code, "CONNECTION_CHANGED")
        factory.assert_not_called()

    def test_disabled_runtime_cannot_send(self):
        runtime = Runtime(lambda: Settings("https://clipit.dev", "key"), Mock())
        runtime.close()
        with self.assertRaises(ClipItError):
            runtime.call("runs")

    def test_unexpected_exception_does_not_leak(self):
        runtime = Runtime(lambda: (_ for _ in ()).throw(RuntimeError("secret-token")))
        value = runtime.tool_json("clipit_status", {})
        self.assertNotIn("secret-token", value)
        self.assertEqual(json.loads(value)["error"]["code"], "PLUGIN_ERROR")


class SharedServerFixtureTests(unittest.TestCase):
    def test_actual_server_shapes_pass_through_harness_independent_client(self):
        fixtures = json.loads((ROOT / "tests/fixtures/platform-responses.json").read_text())
        mappings = {"identity": ("identity", {}), "compatibility": ("compatibility", {}), "overview": ("overview", {}),
                    "catalog": ("catalog", {}), "tool": ("tool", {"id": fixtures["tool"]["body"]["tool"]["name"]}),
                    "runs": ("runs", {}), "run": ("run", {"id": fixtures["run"]["body"]["id"]}),
                    "events": ("events", {"id": fixtures["run"]["body"]["id"]}), "artifacts": ("artifacts", {"id": fixtures["run"]["body"]["id"]}),
                    "poll": ("poll_budget", {"body": {"runIds": []}}),
                    "source_import": ("import_url", {"body": {"idempotencyKey": "fixture-import", "url": "https://example.test/source"}})}
        for fixture, (operation, arguments) in mappings.items():
            with self.subTest(fixture=fixture):
                saved = fixtures[fixture]
                session = Mock()
                session.request.return_value = response(saved["body"], saved["status"], saved["headers"])
                client = ClipItClient(Settings("https://clipit.dev", "fake-fixture-key"), session)
                value = client.call(operation, arguments)
                self.assertIsInstance(value, dict)
                if fixture != "identity":
                    self.assertEqual(value["contractVersion"], "2026-09-16")
                client.close()

    def test_actual_server_identity_negotiates_connection_without_hermes(self):
        fixtures = json.loads((ROOT / "tests/fixtures/platform-responses.json").read_text())
        session = Mock()
        session.request.side_effect = [response(fixtures[key]["body"]) for key in ("identity", "compatibility")]
        runtime = Runtime(lambda: Settings("https://clipit.dev", "fake-fixture-key"), lambda settings: ClipItClient(settings, session))
        value = runtime.status()
        self.assertEqual(value["accountId"], "owner")
        self.assertEqual(value["credentialId"], "key-a")
        self.assertTrue(value["compatibility"]["features"]["coordinatedPolling"])
        runtime.close()


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        spec = importlib.util.spec_from_file_location("clipit_bridge_test", ROOT / "dashboard" / "plugin_api.py")
        cls.bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.bridge)
        app = FastAPI()
        app.include_router(cls.bridge.router)
        cls.http = TestClient(app)

    def setUp(self):
        self.bridge.runtime = Mock()
        self.bridge.runtime.call.return_value = {"items": []}

    def test_no_arbitrary_proxy_and_connection_required(self):
        for path, body in [("runs", {}), ("unknown", {"connectionId": "a" * 64}), ("runs", {"connectionId": "a" * 64, "url": "https://other.invalid"})]:
            result = self.http.post('/operations/' + path, json=body)
            self.assertGreaterEqual(result.status_code, 400)
        self.bridge.runtime.call.assert_not_called()

    def test_body_limit_and_content_type(self):
        result = self.http.post('/operations/runs', content=b' ' * 65537, headers={"Content-Type": "application/json"})
        self.assertEqual(result.status_code, 413)
        self.assertEqual(self.http.post('/operations/runs', content='{}').status_code, 415)

    def test_upstream_retry_after_survives_desktop_http_error_transport(self):
        self.bridge.runtime.call.side_effect = self.bridge._client.ClipItError("RATE_LIMITED", "Wait", 429, retry_after=45)
        result = self.http.post('/operations/poll_budget', json={"connectionId": "a" * 64, "body": {}})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["error"]["retryAfter"], 45)
        self.assertEqual(result.json()["error"]["status"], 429)

    def test_no_store_and_scoped_dispatch(self):
        result = self.http.post('/operations/runs', json={"connectionId": "a" * 64, "query": {"limit": 50}})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers['cache-control'], 'private, no-store')
        self.bridge.runtime.call.assert_called_once_with('runs', {'query': {'limit': 50}}, media=False, connection_id='a' * 64)


if __name__ == '__main__':
    unittest.main()
