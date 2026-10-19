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

    def test_dist_contains_complete_snapshot(self):
        generated = json.loads((build.DIST / "data.json").read_text(encoding="utf-8"))
        self.assertEqual(generated["sourceHash"], self.data["sourceHash"])
        for name in ("index.html", "styles.css", "app.js"):
            self.assertTrue((build.DIST / name).is_file(), name)

    def test_both_loops_derive_from_canonical_sources(self):
        self.assertEqual(set(self.data["modes"]), {"quick", "full"})
        for mode in self.data["modes"].values():
            self.assertEqual(len(mode["steps"]), 5)
            for step in mode["steps"]:
                self.assertTrue(step["source"].startswith(self.data["repository"] + "/blob/"))
                self.assertTrue(step["sourceExcerpt"])
                self.assertTrue(step["editorial"])

    def test_full_is_conditional(self):
        self.assertIn("conditional", self.data["modes"]["full"]["note"])
        self.assertIn("not a separately mandated", self.data["modes"]["quick"]["note"])


if __name__ == "__main__":
    unittest.main()
