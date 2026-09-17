import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from clipit_plugin.runtime import Runtime, _clock_check, _hermes_identity, _legacy_skill_check
from clipit_plugin.registration import register
from clipit_plugin.client import Settings


class DoctorDiagnosticsTests(unittest.TestCase):
    def test_clock_estimate_reports_offset_and_network_uncertainty(self):
        result = _clock_check("2026-09-16T00:02:00+00:00", 1789516800, 1789516802, 2)
        self.assertEqual(result["status"], "skew")
        self.assertEqual(result["serverAheadMs"], 119000)
        self.assertEqual(result["uncertaintyMs"], 1000)
        self.assertEqual(_clock_check("2026-09-16T00:00:01Z", 1789516800, 1789516802, 2)["status"], "ok")

    def test_clock_unknown_for_missing_naive_invalid_and_local_clock_jump(self):
        for timestamp in (None, "invalid", "2026-09-16T00:00:00"):
            self.assertEqual(_clock_check(timestamp, 0, 1, 1)["status"], "unknown")
        result = _clock_check("2026-09-16T00:00:00Z", 0, 100, 1)
        self.assertEqual(result["status"], "unknown")
        self.assertIsNone(result["serverAheadMs"])

    def test_status_measures_only_the_compatibility_request(self):
        runtime = Runtime(lambda: Settings("https://clipit.dev", "fake-test-key"))
        runtime.call = Mock(side_effect=[{"user": {"id": "user"}, "apiKey": {}}, {"serverTime": "2026-09-16T00:02:00Z"}])
        with patch("clipit_plugin.runtime.time.time", side_effect=[1789516800, 1789516802]), patch("clipit_plugin.runtime.time.monotonic", side_effect=[10, 12]):
            result = runtime.status()
        self.assertEqual(result["clock"]["serverAheadMs"], 119000)
        self.assertEqual([call.args[0] for call in runtime.call.call_args_list], ["identity", "compatibility"])

    def test_doctor_reports_actual_identity_and_unknown_desktop_without_hermes_import(self):
        registration = {"pluginId": "clipit", "manifestVersion": "3.0.0"}
        runtime = Runtime(registration=registration)
        registration["manifestVersion"] = "mutated"
        runtime.status = Mock(return_value={"clock": {"status": "ok"}})
        with patch.dict(sys.modules, {"hermes_cli": SimpleNamespace(__version__="0.21.3"), "hermes_constants": None}):
            result = runtime.doctor()
            result["runtime"]["registration"]["manifestVersion"] = "caller-mutated"
            second = runtime.doctor()
        self.assertEqual(result["runtime"]["hermes"], {"version": "0.21.3", "source": "loaded hermes_cli"})
        self.assertEqual(second["runtime"]["registration"]["manifestVersion"], "3.0.0")
        self.assertEqual(result["runtime"]["instanceId"], second["runtime"]["instanceId"])
        self.assertEqual(result["desktop"]["status"], "unknown")
        self.assertEqual(result["topology"]["mode"], "unknown")
        self.assertEqual(result["legacySkills"]["status"], "unknown")
        self.assertEqual(result["clock"]["status"], "ok")

    def test_absent_hermes_distribution_is_an_explicit_unknown(self):
        from importlib.metadata import PackageNotFoundError
        with patch.dict(sys.modules, {"hermes_cli": None}), patch("clipit_plugin.runtime.metadata.version", side_effect=PackageNotFoundError):
            self.assertIsNone(_hermes_identity()["version"])

    def test_skill_check_reads_no_contents_and_never_follows_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            ordinary = home / "skills" / "creative" / "clipit-operator"
            ordinary.mkdir(parents=True)
            (ordinary / "SKILL.md").write_text("do-not-read-secret")
            unrelated = home / "skills" / "clipit-unknown-directory"
            unrelated.mkdir()
            outside = home / "outside" / "clipit-editor"
            outside.mkdir(parents=True)
            (outside / "SKILL.md").write_text("outside-secret")
            (home / "skills" / "linked").symlink_to(home / "outside", target_is_directory=True)
            with patch.dict(sys.modules, {"hermes_constants": SimpleNamespace(get_hermes_home=lambda: home)}), patch.object(Path, "read_text", side_effect=AssertionError("read skill contents")):
                result = _legacy_skill_check()
            self.assertEqual(result["possibleDuplicates"], ["clipit-operator"])
            self.assertNotIn(directory, json.dumps(result))
            self.assertNotIn("secret", json.dumps(result))

    def test_skill_check_is_bounded_and_skips_symlink_root(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            skills = home / "skills"
            skills.mkdir()
            for index in range(270):
                (skills / f"other-{index}").mkdir()
            with patch.dict(sys.modules, {"hermes_constants": SimpleNamespace(get_hermes_home=lambda: home)}):
                result = _legacy_skill_check()
                self.assertEqual(result["entriesChecked"], 256)
                self.assertTrue(result["truncated"])
                self.assertEqual(result["status"], "partial")
                alias = home / "alias"
                alias.mkdir()
                (alias / "skills").symlink_to(skills, target_is_directory=True)
                with patch.dict(sys.modules, {"hermes_constants": SimpleNamespace(get_hermes_home=lambda: alias)}):
                    self.assertEqual(_legacy_skill_check()["status"], "unknown")

    def test_native_registration_captures_public_context_without_scanning(self):
        context = Mock(plugin_id="clipit", manifest=SimpleNamespace(name="clipit", version="3.0.0"))
        with patch("clipit_plugin.registration.Runtime") as runtime, patch("clipit_plugin.runtime._legacy_skill_check", side_effect=AssertionError("eager scan")):
            register(context)
        runtime.assert_called_once_with(registration={"pluginId": "clipit", "manifestName": "clipit", "manifestVersion": "3.0.0"})


if __name__ == "__main__":
    unittest.main()
