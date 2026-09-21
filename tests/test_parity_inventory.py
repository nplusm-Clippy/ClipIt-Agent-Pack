import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("parity_inventory", ROOT / "tooling/build_parity_inventory.py")
parity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parity)


class ParityInventoryTests(unittest.TestCase):
    def test_checked_in_inventory_matches_canonical_sources(self):
        self.assertEqual(parity.TARGET.read_text(), json.dumps(parity.inventory(), indent=2) + "\n")

    def test_expressions_preserve_source_without_interpreter_formatting(self):
        source = '''parser.add_argument("--title", help="Crème", choices=[
    "draft", "ready",
])
client.post(f"/api/v1/assets/{signed['assetId']}/finalize", {})
'''
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            (root / "scripts" / "sample.py").write_text(source)
            (root / "agent-pack.manifest.json").write_text(json.dumps({
                "skills": [], "packVersion": "test", "capabilityContractVersion": "test",
            }))
            with patch.object(parity, "ROOT", root), patch.object(parity.ast, "unparse", side_effect=AssertionError("Interpreter formatting must not affect inventory")):
                script = parity.inventory()["scripts"][0]
        self.assertEqual(script["arguments"][0]["options"], {
            "help": '"Crème"', "choices": '[\n    "draft", "ready",\n]',
        })
        self.assertEqual(script["requests"], [{
            "method": "POST", "pathExpression": '''f"/api/v1/assets/{signed['assetId']}/finalize"''', "line": 4,
        }])
