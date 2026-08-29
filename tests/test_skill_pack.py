import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "agent-pack.manifest.json"
ALLOWED_FRONTMATTER_KEYS = {"name", "description", "license", "metadata", "allowed-tools"}
EXPECTED_SKILLS = {
    "account-insights",
    "audio-production",
    "blueprint-to-edit",
    "broll-generation",
    "caption-generation",
    "clip-creation",
    "clipit-operator",
    "creator-style",
    "crop-reframing",
    "delivery-qa",
    "export-rendering",
    "machine-payments",
    "project-sequence-management",
    "scene-alter",
    "social-publishing",
    "thumbnail-generation",
    "timeline-editing",
    "video-management",
}


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, flags=re.DOTALL)
    if not match:
        raise AssertionError(f"missing YAML frontmatter: {path}")
    lines = match.group(1).splitlines()
    keys = {
        line.split(":", 1)[0]
        for line in lines
        if line and not line[0].isspace() and ":" in line
    }
    name = next(line.split(":", 1)[1].strip() for line in lines if line.startswith("name:"))
    description = next(line.split(":", 1)[1].strip() for line in lines if line.startswith("description:"))
    return text, keys, name, description


class SkillPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_and_skill_directories_have_exact_parity(self):
        manifest_skills = {item["id"] for item in self.manifest["skills"]}
        directory_skills = {
            path.parent.name for path in (ROOT / "clipper").glob("*/SKILL.md")
        }
        self.assertEqual(manifest_skills, EXPECTED_SKILLS)
        self.assertEqual(directory_skills, EXPECTED_SKILLS)
        self.assertEqual(self.manifest["alwaysInstall"], ["clipit-operator"])
        self.assertEqual(self.manifest["packVersion"], "2.0.0")
        self.assertEqual(self.manifest["minimumCliVersion"], "0.3.0")
        self.assertEqual(self.manifest["capabilityContractVersion"], "clipit-agent-capabilities.v1")
        self.assertEqual(self.manifest["mediaPromptingContract"], "media-prompting-contract.v2")
        self.assertEqual(set(self.manifest["mediaModels"]), set(self.manifest["mediaProviders"]))

        for item in self.manifest["skills"]:
            self.assertEqual(item["path"], f"clipper/{item['id']}")
            self.assertTrue((ROOT / item["path"] / "SKILL.md").is_file())

    def test_every_skill_has_valid_lean_frontmatter_and_description(self):
        for skill_path in sorted((ROOT / "clipper").glob("*/SKILL.md")):
            with self.subTest(skill=skill_path.parent.name):
                text, keys, name, description = read_frontmatter(skill_path)
                self.assertTrue(keys <= ALLOWED_FRONTMATTER_KEYS, keys)
                self.assertIn("license", keys)
                self.assertIn("metadata", keys)
                self.assertTrue(name)
                self.assertGreaterEqual(len(description), 40)
                self.assertIn('version: "2.0.0"', text)
                self.assertLessEqual(len(text.splitlines()), 240)

    def test_all_markdown_reference_links_from_skills_exist(self):
        for skill_path in sorted((ROOT / "clipper").glob("*/SKILL.md")):
            text = skill_path.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)#]+\.md)\)", text):
                if target.startswith(("http://", "https://")):
                    continue
                with self.subTest(skill=skill_path.parent.name, target=target):
                    self.assertTrue((skill_path.parent / target).resolve().is_file())

    def test_operator_contains_required_execution_and_safety_contracts(self):
        operator = (ROOT / "clipper/clipit-operator/SKILL.md").read_text(encoding="utf-8")
        required = [
            "clipit tools describe",
            "clipit skills manifest",
            "clipit media-guides describe",
            "clipit ask",
            "clipit mcp stdio",
            "Python scripts",
            "exactly one owner",
            "--max-credits",
            "requiresConfirmation",
            "confirmed: true",
            "resume token",
            "source audio",
            "delivery QA",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), operator.lower())

    def test_current_media_contract_and_models_are_documented(self):
        media = (ROOT / "clipper/clipit-operator/references/media-prompting.md").read_text(encoding="utf-8")
        for model in self.manifest["mediaModels"].values():
            with self.subTest(model=model):
                self.assertIn(model, media)
        for phrase in [
            "Keep everything else the same.",
            "source audio remains authoritative",
            "Real-person continuity checklist",
            "literal spoken words",
            "mix controls separate",
        ]:
            self.assertIn(phrase.lower(), media.lower())

    def test_stale_model_and_remembered_price_attributions_are_absent(self):
        paths = [ROOT / "README.md", ROOT / "AGENTS.md"]
        paths.extend((ROOT / "clipper").rglob("*.md"))
        paths.extend((ROOT / "scripts").glob("*.py"))
        corpus = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for stale in ["Flux 2 Max", "Veo 3.1", "Nano Banana Pro", "Grok 4.20"]:
            with self.subTest(stale=stale):
                self.assertNotIn(stale.lower(), corpus.lower())
        self.assertIsNone(re.search(r"(?:~|approximately\s+)?\d+(?:\.\d+)?\s+\$CLIP", corpus, re.IGNORECASE))

    def test_shared_references_and_root_guidance_have_manifest_parity(self):
        for relative_path in self.manifest["sharedReferences"]:
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for skill_id in EXPECTED_SKILLS:
            self.assertIn(skill_id, readme)
        for phrase in [
            "one execution owner",
            "clipit skills manifest",
            "clipit media-guides describe",
            "clipit tools describe",
            "clipit mcp stdio",
            "delivery-qa",
        ]:
            self.assertIn(phrase.lower(), agents.lower())

        transport = (ROOT / "clipper/clipit-operator/references/tool-transport.md").read_text(encoding="utf-8")
        for resource in [
            "clipit://instructions",
            "clipit://manifest",
            "clipit://skills/<capabilityId>",
            "clipit://media-guides/<guideId>",
        ]:
            self.assertIn(resource, transport)


if __name__ == "__main__":
    unittest.main()
