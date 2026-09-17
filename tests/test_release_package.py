import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_packager", ROOT / "tooling/package_release.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class ReleasePackageTests(unittest.TestCase):
    def test_release_versions_agree_across_plugin_surfaces(self):
        import yaml
        from clipit_plugin.version import VERSION
        manifest = json.loads((ROOT / "agent-pack.manifest.json").read_text())
        self.assertEqual(manifest["packVersion"], VERSION)
        self.assertEqual(manifest["nativePlugin"]["version"], VERSION)
        self.assertEqual(json.loads((ROOT / "dashboard/manifest.json").read_text())["version"], VERSION)
        self.assertEqual(yaml.safe_load((ROOT / "plugin.yaml").read_text())["version"], VERSION)
        self.assertIn("export const VERSION = '" + VERSION + "'", (ROOT / "desktop/plugin.js").read_text())

    def test_reproducible_and_preserves_every_legacy_entrypoint(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = packager.build(Path(temporary) / "one")
            second = packager.build(Path(temporary) / "two")
            self.assertEqual(first["sha256"], second["sha256"])
            with zipfile.ZipFile(first["archive"]) as archive:
                names = set(archive.namelist())
                for path in (ROOT / "scripts").glob("*.py"):
                    self.assertEqual(archive.read("clipit/scripts/" + path.name), path.read_bytes())
                self.assertEqual(sum(name.endswith('/SKILL.md') and '/clipper/' in name for name in names), 18)
                self.assertEqual(sum(name.endswith('/SKILL.md') and '/skills/' in name for name in names), 18)
                self.assertFalse(any('/.env' in name or '/node_modules/' in name or '__pycache__' in name for name in names))
                manifest = json.loads(archive.read('clipit/release-manifest.json'))
                self.assertEqual(manifest['fileCount'], len(names) - 1)

    def test_symlinks_cannot_escape_selected_package_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'scripts').mkdir()
            (root / 'secret').write_text('must not package')
            (root / 'scripts' / 'bad.py').symlink_to(root / 'secret')
            with self.assertRaises(ValueError):
                packager.release_files(root)
