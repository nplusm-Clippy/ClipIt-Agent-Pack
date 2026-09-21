import argparse
import ast
import contextlib
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import typing
import unittest
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from tooling import build_portable_skills as builder


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/compatibility"


def upstream_functions(filename, names, namespace):
    path = FIXTURES / filename
    provenance = json.loads((FIXTURES / "hermes-source.json").read_text())
    expected = provenance["files"][filename]["sha256"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise AssertionError(f"Pinned upstream fixture changed: {filename}")
    tree = ast.parse(path.read_text())
    tree.body = [node for node in tree.body if (
        isinstance(node, ast.FunctionDef) and node.name in names
    ) or (
        isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in names
            for target in node.targets
        )
    )]
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace


class PortableSkillBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = builder.build_pack()
        cls.manifest = json.loads(cls.files["manifest.json"])
        cls.support_parser = upstream_functions("hermes-skills-hub-models.py", {
            "_normalize_bundle_path", "_validate_bundle_rel_path",
            "_query_is_concrete", "_referenced_support_paths",
            "_ALLOWED_SUPPORT_DIRS", "_LOCAL_LINK_RE", "_SUSPICIOUS_LOCAL_REF_RE",
            "_VALUELESS_QUERY_FLAG_RE", "_SAMEDIR_LINK_RE", "_SAMEDIR_NAME_RE",
        }, {
            "re": re, "urlsplit": urlsplit, "unquote": unquote,
            "PurePosixPath": PurePosixPath, "Optional": typing.Optional,
        })["_referenced_support_paths"]

    def copy_sources(self, root):
        for name in ["clipper", "scripts"]:
            shutil.copytree(ROOT / name, root / name, ignore=shutil.ignore_patterns("__pycache__"))
        for name in ["agent-pack.manifest.json", "requirements.txt", "LICENSE"]:
            shutil.copyfile(ROOT / name, root / name)

    def test_checked_in_bundles_are_complete_and_current(self):
        self.assertEqual(builder.verify_output(ROOT / "skills", self.files), [])
        source = json.loads((ROOT / "agent-pack.manifest.json").read_text())
        self.assertEqual({item["id"] for item in self.manifest["skills"]}, {item["id"] for item in source["skills"]})
        self.assertEqual(len(self.manifest["skills"]), 18)

    def test_relocated_sources_generate_identical_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_sources(root)
            self.assertEqual(builder.build_pack(root), self.files)

    def test_real_released_hermes_parser_fetches_every_support_file(self):
        for item in self.manifest["skills"]:
            skill_id = item["id"]
            with self.subTest(skill=skill_id):
                support = type(self).support_parser(self.files[f"{skill_id}/SKILL.md"].decode())
                self.assertIsNotNone(support)
                expected = {
                    name.removeprefix(f"{skill_id}/") for name in self.files
                    if name.startswith(f"{skill_id}/") and not name.endswith("/SKILL.md")
                }
                self.assertEqual(support, expected)

    def test_released_hermes_accepts_one_full_identifier_per_command(self):
        parser_namespace = upstream_functions("hermes-skills-parser.py", {
            "_flag", "_SOURCE_CHOICES", "build_skills_parser",
        }, {
            "Callable": typing.Callable,
            "add_json_flag": lambda parser, *args: parser.add_argument("--json", action="store_true"),
            "add_yes_flag": lambda parser, *args: parser.add_argument("--yes", action="store_true"),
        })
        parser = argparse.ArgumentParser(prog="hermes")
        parser_namespace["build_skills_parser"](parser.add_subparsers(), cmd_skills=lambda args: None)
        split = upstream_functions("hermes-skills-hub-github.py", {"_split_repo_id"}, {
            "Optional": typing.Optional, "Tuple": typing.Tuple,
        })["_split_repo_id"]
        for item in self.manifest["skills"]:
            identifier = f"nplusm-Clippy/ClipIt-Agent-Pack/skills/{item['id']}"
            parser.parse_args(["skills", "install", identifier])
            self.assertEqual(split(identifier), ("nplusm-Clippy/ClipIt-Agent-Pack", f"skills/{item['id']}"))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as rejected:
            parser.parse_args(["skills", "install", "clipper/clipit-operator", "clipper/video-management"])
        self.assertEqual(rejected.exception.code, 2)

    def test_all_markdown_links_resolve_inside_their_bundle(self):
        for name, content in self.files.items():
            if not name.endswith(".md"):
                continue
            for target in re.findall(r"\]\(([^)]+)\)", content.decode()):
                parsed = urlsplit(target)
                if parsed.scheme or not parsed.path:
                    continue
                with self.subTest(document=name, target=target):
                    self.assertNotIn("..", PurePosixPath(parsed.path).parts)
                    destination = str(PurePosixPath(name).parent / unquote(parsed.path))
                    self.assertIn(destination, self.files)
                    self.assertEqual(PurePosixPath(destination).parts[0], PurePosixPath(name).parts[0])

    def test_all_documented_scripts_and_local_imports_are_bundled_unchanged(self):
        sources = {path.relative_to(ROOT).as_posix() for path in (ROOT / "scripts").glob("*.py")}
        for item in self.manifest["skills"]:
            prefix = f"{item['id']}/"
            manifest_name = prefix + "references/bundle-manifest.json"
            record = json.loads(self.files[manifest_name])
            self.assertEqual(builder.digest(self.files[manifest_name]), item["manifestSha256"])
            for name, provenance in record["files"].items():
                with self.subTest(skill=item["id"], file=name):
                    data = self.files[prefix + name]
                    self.assertEqual(builder.digest(data), provenance["sha256"])
                    source_bytes = (ROOT / provenance["source"]).read_bytes()
                    self.assertEqual(builder.digest(source_bytes), provenance["sourceSha256"])
                    if name.endswith(".py"):
                        self.assertEqual(data, source_bytes)
                        for dependency in builder.script_imports(data.decode(), sources):
                            self.assertIn(prefix + dependency, self.files)
                    if name.endswith(".md"):
                        for match in builder.FILE_REFERENCE.finditer(data.decode()):
                            if match.group(0).endswith(".py"):
                                self.assertIn(prefix + "scripts/" + PurePosixPath(match.group(0)).name, self.files)

    def test_python_fallback_imports_work_from_isolated_installed_bundles(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "installed"
            builder.write_output(output, self.files)
            code = """
import pathlib, runpy, socket, sys
def deny_network(*args, **kwargs):
    raise AssertionError('Offline imports cannot contact providers')
socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.socket.sendto = deny_network
scripts = pathlib.Path(sys.argv[1]) / 'scripts'
sys.path.insert(0, str(scripts))
for script in sorted(scripts.glob('*.py')):
    runpy.run_path(str(script), run_name='portable_import_check')
assert not any(name.startswith('hermes') for name in sys.modules)
"""
            for item in self.manifest["skills"]:
                directory = output / item["id"]
                with self.subTest(skill=item["id"]):
                    result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(directory)], cwd=temporary, capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_script_hashes_remain_at_frozen_baseline(self):
        baseline = json.loads((FIXTURES / "agent-pack-2.0.0-baseline.json").read_text())
        self.assertEqual(baseline["validation"]["tests"], 75)
        self.assertEqual(sum(item["hasMainGuard"] for item in baseline["scripts"].values()), 52)
        for name, record in baseline["scripts"].items():
            self.assertEqual(builder.digest((ROOT / name).read_bytes()), record["sha256"], name)

    def test_no_secret_config_or_unreferenced_files_are_copied(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_sources(root)
            (root / ".env").write_text("PRIVATE_TEST_SECRET=do-not-package")
            (root / "clipper/clipit-operator/references/unreferenced.md").write_text("do-not-package")
            self.assertEqual(builder.build_pack(root), self.files)

    def test_referenced_missing_or_outside_files_fail_closed(self):
        for target in ["../../../outside.md", "references/missing.md", "../../.env.txt"]:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self.copy_sources(root)
                skill = root / "clipper/clipit-operator/SKILL.md"
                skill.write_text(skill.read_text() + f"\n[required]({target})\n")
                with self.assertRaises(ValueError):
                    builder.build_pack(root)

    def test_symlink_inputs_and_outputs_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.copy_sources(root)
            script = root / "scripts/clipper_client.py"
            script.unlink()
            script.symlink_to(ROOT / "scripts/clipper_client.py")
            with self.assertRaises(ValueError):
                builder.build_pack(root)
            output = root / "output"
            output.symlink_to(ROOT / "skills", target_is_directory=True)
            with self.assertRaises(ValueError):
                builder.write_output(output, self.files)

    def test_bundle_check_detects_tampering_and_preserves_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            builder.write_output(output, self.files)
            target = output / "clipit-operator/SKILL.md"
            target.write_text("local edit")
            self.assertEqual(builder.verify_output(output, self.files), ["clipit-operator/SKILL.md"])
            unrelated = output / "owner-notes.txt"
            unrelated.write_text("preserve me")
            with self.assertRaises(ValueError):
                builder.write_output(output, self.files)
            self.assertEqual(unrelated.read_text(), "preserve me")

    def test_size_bounds_keep_bundles_small(self):
        self.assertLess(sum(len(value) for value in self.files.values()), 1024 * 1024)
        self.assertLess(max(item["bytes"] for item in self.manifest["skills"]), 256 * 1024)


if __name__ == "__main__":
    unittest.main()
