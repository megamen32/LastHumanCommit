"""The public example is a real renderer output with a checked, neutral DAG."""
import json
import re
import unittest
import build

class GanttDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = build.build()
        cls.graph = json.loads((build.DIST / "examples/task-plan.graph.json").read_text(encoding="utf-8"))
        cls.html = (build.DIST / "examples/task-plan.html").read_text(encoding="utf-8")

    def test_small_leaves_and_capacity(self):
        self.assertEqual(len(self.graph["tasks"]), 16)
        self.assertEqual(self.graph["slots"], 3)
        for task in self.graph["tasks"]:
            self.assertGreater(task["estimate_minutes"]["minimum"], 0)
            self.assertLessEqual(task["estimate_minutes"]["maximum"], 15)

    def test_multi_parent_joins_survive_generation(self):
        tasks = {t["id"]: t for t in self.graph["tasks"]}
        for name, parents in {"L08": ["L05", "L06"], "L09": ["L05", "L07"], "L10": ["L08", "L09"], "L14": ["L12", "L13"]}.items():
            self.assertEqual(tasks[name]["depends_on"], parents)
        fixture = json.loads((build.SITE / "examples/task-plan.graph.json").read_text(encoding="utf-8"))
        self.assertEqual([t["depends_on"] for t in self.graph["tasks"]], [t["depends_on"] for t in fixture["tasks"]])

    def test_offline_neutral_snapshot_not_live_project(self):
        self.assertIn("УЧЕБНЫЙ ПРИМЕР", self.html)
        self.assertIn("условные", self.html)
        self.assertNotRegex(self.html, r"<script[^>]+src=")
        self.assertNotIn("fetch(", self.html)
        for marker in ("telegram:", "/home/", "bezrabotnyi.com", "account_id", "account_ref", "action_db"):
            self.assertNotIn(marker, self.html)
        self.assertEqual(self.snapshot["planExample"]["kind"], "illustrative-snapshot")

    def test_open_download_and_lazy_embedded_html(self):
        page = (build.DIST / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="plan"', page)
        self.assertIn('src="./examples/task-plan.html"', page)
        self.assertIn('loading="lazy"', page)
        self.assertIn('download="lhc-example-plan.html"', page)

if __name__ == "__main__":
    unittest.main()
