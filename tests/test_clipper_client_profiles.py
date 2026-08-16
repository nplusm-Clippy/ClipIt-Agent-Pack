import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.clipper_client import (
    ClipperClient,
    require_enterprise_workspace_scope,
)


WORKSPACE_ID = "11111111-1111-4111-8111-111111111111"


def workspace_scope(**overrides):
    scope = {
        "identityType": "workspace_api_key",
        "enterprise": True,
        "workspaceId": WORKSPACE_ID,
        "workspaceName": "Client Workspace",
        "workspaceStatus": "active",
        "workspaceRole": "team_operator",
        "resourceOwnerUserId": "22222222-2222-4222-8222-222222222222",
        "billingMode": "enterprise_usage_only",
    }
    scope.update(overrides)
    return {"scope": scope}


class ClipperClientProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.config_dir = Path(self.temp_dir.name)
        self.env = patch.dict(
            os.environ,
            {"CLIPIT_CONFIG_DIR": str(self.config_dir)},
            clear=True,
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def write_config(self, config):
        (self.config_dir / "config.json").write_text(
            json.dumps(config),
            encoding="utf-8",
        )

    def test_explicit_api_key_has_highest_precedence(self):
        self.write_config({
            "currentProfile": "enterprise-client",
            "profiles": {
                "enterprise-client": {
                    "apiKey": "workspace-profile-key",
                }
            },
        })
        os.environ["CLIPPER_API_KEY"] = "ambient-personal-key"

        client = ClipperClient(api_key="explicit-key")

        self.assertEqual(client.api_key, "explicit-key")
        self.assertEqual(client.profile_name, "enterprise-client")

    def test_explicit_named_profile_ignores_ambient_personal_settings(self):
        self.write_config({
            "profiles": {
                "enterprise-client": {
                    "apiKey": "workspace-profile-key",
                    "baseUrl": "https://workspace.example/",
                }
            },
        })
        os.environ["CLIPIT_PROFILE"] = "enterprise-client"
        os.environ["CLIPPER_API_KEY"] = "ambient-personal-key"
        os.environ["CLIPPER_BASE_URL"] = "https://ambient-staging.example"

        client = ClipperClient()

        self.assertEqual(client.api_key, "workspace-profile-key")
        self.assertEqual(client.base_url, "https://workspace.example")
        self.assertEqual(client.profile_name, "enterprise-client")

    def test_named_profile_without_base_url_ignores_ambient_url(self):
        self.write_config({
            "profiles": {
                "enterprise-client": {"apiKey": "workspace-profile-key"},
            },
        })
        os.environ["CLIPIT_PROFILE"] = "enterprise-client"
        os.environ["CLIPPER_BASE_URL"] = "https://ambient-staging.example"

        client = ClipperClient()

        self.assertEqual(client.base_url, "https://clipit.dev")

    def test_explicit_base_url_beats_named_profile_url(self):
        self.write_config({
            "profiles": {
                "enterprise-client": {
                    "apiKey": "workspace-profile-key",
                    "baseUrl": "https://workspace.example",
                },
            },
        })
        os.environ["CLIPPER_BASE_URL"] = "https://ambient-staging.example"

        client = ClipperClient(
            profile="enterprise-client",
            base_url="https://explicit.example/",
        )

        self.assertEqual(client.base_url, "https://explicit.example")

    def test_active_non_default_profile_ignores_ambient_personal_key(self):
        self.write_config({
            "currentProfile": "enterprise-client",
            "profiles": {
                "enterprise-client": {"apiKey": "workspace-profile-key"},
            },
        })
        os.environ["CLIPPER_API_KEY"] = "ambient-personal-key"

        client = ClipperClient()

        self.assertEqual(client.api_key, "workspace-profile-key")
        self.assertEqual(client.profile_name, "enterprise-client")

    def test_profile_argument_beats_environment_and_current_profile(self):
        self.write_config({
            "currentProfile": "current-client",
            "profiles": {
                "current-client": {"apiKey": "current-profile-key"},
                "environment-client": {"apiKey": "environment-profile-key"},
                "explicit-client": {"apiKey": "explicit-profile-key"},
            },
        })
        os.environ["CLIPIT_PROFILE"] = "environment-client"

        client = ClipperClient(profile="explicit-client")

        self.assertEqual(client.api_key, "explicit-profile-key")
        self.assertEqual(client.profile_name, "explicit-client")

    def test_named_profile_missing_key_fails_without_env_fallback(self):
        self.write_config({
            "currentProfile": "enterprise-client",
            "profiles": {"enterprise-client": {}},
        })
        os.environ["CLIPPER_API_KEY"] = "ambient-personal-key"

        with self.assertRaisesRegex(RuntimeError, "ambient CLIPPER_API_KEY was not used"):
            ClipperClient()

    def test_default_profile_keeps_environment_fallback(self):
        self.write_config({
            "profiles": {
                "default": {
                    "apiKey": "default-profile-key",
                    "baseUrl": "https://default-profile.example",
                }
            },
        })
        os.environ["CLIPPER_API_KEY"] = "ambient-personal-key"
        os.environ["CLIPPER_BASE_URL"] = "https://ambient-personal.example/"

        client = ClipperClient()

        self.assertEqual(client.api_key, "ambient-personal-key")
        self.assertEqual(client.base_url, "https://ambient-personal.example")
        self.assertEqual(client.profile_name, "default")

    def test_default_profile_supports_legacy_cli_config(self):
        self.write_config({
            "apiKey": "legacy-default-key",
            "baseUrl": "https://legacy.example/",
        })

        client = ClipperClient()

        self.assertEqual(client.api_key, "legacy-default-key")
        self.assertEqual(client.base_url, "https://legacy.example")

    @patch("scripts.clipper_client.requests.get")
    def test_agent_identity_uses_the_expected_endpoint_without_real_network(self, get):
        response = Mock()
        response.status_code = 200
        response.json.return_value = workspace_scope()
        get.return_value = response
        self.write_config({
            "profiles": {
                "enterprise-client": {"apiKey": "workspace-profile-key"},
            },
        })

        client = ClipperClient(profile="enterprise-client")
        identity = client.get_agent_identity()

        self.assertEqual(identity, workspace_scope())
        get.assert_called_once_with(
            "https://clipit.dev/api/v1/agent/me",
            headers={
                "X-API-Key": "workspace-profile-key",
                "Accept": "application/json",
                "User-Agent": "ClipItAgentPack/1.0",
            },
            params=None,
            timeout=30,
        )


class EnterpriseWorkspaceScopeTests(unittest.TestCase):
    def test_valid_scope_matches_expected_workspace(self):
        scope = require_enterprise_workspace_scope(
            workspace_scope(),
            expected_workspace_id=WORKSPACE_ID,
        )

        self.assertEqual(scope["workspaceId"], WORKSPACE_ID)
        self.assertEqual(scope["workspaceRole"], "team_operator")

    def test_legacy_agent_info_is_not_enough_for_workspace_preflight(self):
        with self.assertRaisesRegex(RuntimeError, "authoritative workspace scope"):
            require_enterprise_workspace_scope({
                "apiKey": {"agentInfo": {"type": "enterprise_hermes"}},
            })

    def test_personal_scope_fails_workspace_preflight(self):
        with self.assertRaisesRegex(RuntimeError, "identityType=workspace_api_key"):
            require_enterprise_workspace_scope({
                "scope": {
                    "identityType": "personal_api_key",
                    "enterprise": False,
                    "workspaceId": None,
                    "workspaceName": None,
                    "workspaceStatus": None,
                    "workspaceRole": None,
                    "resourceOwnerUserId": "owner-user-id",
                    "billingMode": "direct",
                }
            })

    def test_paused_workspace_fails_workspace_preflight(self):
        with self.assertRaisesRegex(RuntimeError, "workspaceStatus=active"):
            require_enterprise_workspace_scope(
                workspace_scope(workspaceStatus="paused")
            )

    def test_wrong_workspace_id_fails_without_disclosing_the_actual_id(self):
        wrong_workspace_id = "33333333-3333-4333-8333-333333333333"

        with self.assertRaisesRegex(RuntimeError, "different workspace") as raised:
            require_enterprise_workspace_scope(
                workspace_scope(),
                expected_workspace_id=wrong_workspace_id,
            )

        self.assertNotIn(WORKSPACE_ID, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
