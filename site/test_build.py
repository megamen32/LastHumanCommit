"""Regression tests for the Git-synced landing generator."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build


class LandingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build.build()

    def test_every_current_role_is_present(self):
        expected = {p.stem for p in (build.ROOT / "src/common/agents").glob("*.md")}
        actual = {r["name"] for r in self.data["roles"]}
        self.assertEqual(expected, actual)
        self.assertIn("Tester", actual)

    def test_role_text_is_exact_from_git(self):
        for role in self.data["roles"]:
            src = build.ROOT / "src/common/agents" / (role["name"] + ".md")
            self.assertEqual(role["details"], src.read_text(encoding="utf-8"))
            self.assertIn("/blob/" + self.data["revision"] + "/", role["source"])
            self.assertTrue(role["summary"])
            self.assertNotIn("Inherit the current router language policy", role["summary"])
            self.assertIn(role["kind"], {"role", "method-reference", "compatibility-alias"})

    def test_dist_contains_complete_snapshot(self):
        generated = json.loads((build.DIST / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(generated["sourceHash"], self.data["sourceHash"])
        self.assertEqual(generated["revision"], self.data["revision"])
        self.assertEqual(generated["productVersion"], self.data["productVersion"])
        for name in ("index.html", "styles.css", "app.js"):
            self.assertTrue((build.DIST / name).is_file(), name)

    def test_both_loops_derive_from_canonical_sources(self):
        self.assertEqual(set(self.data["modes"]), {"quick", "full"})
        quick = self.data["modes"]["quick"]["steps"]
        full = self.data["modes"]["full"]["steps"]
        self.assertGreater(len(quick), 0)
        self.assertEqual([step["id"] for step in quick], [step["id"] for step in full])
        self.assertEqual(len({step["id"] for step in quick}), len(quick))
        for mode in self.data["modes"].values():
            for step in mode["steps"]:
                self.assertTrue(step["titleKey"].startswith("workflow."))
                self.assertTrue(step["descriptionKey"].startswith("workflow."))
                self.assertTrue(step["source"].startswith(self.data["repository"] + "/blob/" + self.data["revision"] + "/"))
                self.assertTrue(step["sourceExcerpt"])
        self.assertEqual(self.data["decisionDepth"]["id"], "material-choice")
        self.assertIn("/templates/FULL_CYCLE.md", self.data["decisionDepth"]["source"])

    def test_full_is_conditional(self):
        self.assertEqual(self.data["modes"]["quick"]["steps"], self.data["modes"]["full"]["steps"])
        self.assertEqual(self.data["modes"]["quick"]["noteKey"], "mode.quick.note")
        self.assertEqual(self.data["modes"]["full"]["noteKey"], "mode.full.note")


if __name__ == "__main__":
    unittest.main()
