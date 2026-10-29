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

    def role(self, name):
        return next(r for r in self.data["roles"] if r["name"] == name)

    def test_every_current_role_is_present(self):
        expected = {p.stem for p in (build.ROOT / "src/common/agents").glob("*.md")}
        actual = {r["name"] for r in self.data["roles"]}
        self.assertEqual(expected, actual)
        self.assertIn("Tester", actual)

    def test_canonical_roles_publish_definitions_not_language_policy(self):
        # Defect 1: Lead/Worker cards carried a reworded language-policy paragraph.
        for name in ("Lead", "Worker"):
            summary = self.role(name)["summary"]
            self.assertNotRegex(summary, r"^(Internal reasoning|Inherit the current router)")
            self.assertNotIn("Russian-speaking reader", summary)
            self.assertRegex(summary, r"\bI\b")

    def test_extractor_skips_reworded_language_policy(self):
        # Hardening: a future reworded policy paragraph must never become a role definition.
        body = "\n\n".join([
            "Internal reasoning may happen in any compact language; every user-facing answer"
            " and file stays clear in its reader's language, with natural Russian for a"
            " Russian-speaking reader, and original observations preserved.",
            "I own the user outcome and deliver the verified change.",
        ])
        self.assertEqual(
            build.first_paragraph(body, skip_policy=True),
            "I own the user outcome and deliver the verified change.",
        )

    def test_worker_is_a_canonical_role_not_a_method_reference(self):
        # Defect 2: Worker presented itself as an optional method reference.
        # Since 2026-10-27 every role file is a short canonical role.
        self.assertEqual(self.role("Worker")["kind"], "role")
        self.assertEqual(
            {r["name"] for r in self.data["roles"] if r["kind"] == "role"},
            {"Lead", "Worker", "Adviser", "Reviewer", "Tester", "Overseer",
             "Maintainer", "Critic", "Orchestrator", "Sentinel"},
        )

    def test_taxonomy_counts_are_honest(self):
        # Defect 3 support: the published counts match the role files (10 canonical roles).
        counts = {}
        for role in self.data["roles"]:
            counts[role["kind"]] = counts.get(role["kind"], 0) + 1
        self.assertEqual(
            counts, {"role": 10}
        )

    def test_maintainer_has_an_explicit_position(self):
        # Defect 4: Maintainer sorted only by the 99 fallback.
        names = [r["name"] for r in self.data["roles"]]
        self.assertEqual(
            names,
            ["Lead", "Worker", "Adviser", "Critic", "Reviewer", "Tester", "Overseer", "Maintainer", "Orchestrator", "Sentinel"],
        )
        self.assertIn("Maintainer", build.role_order)

    def test_truncation_ends_at_a_boundary_never_dangling(self):
        # Defect 5: character-boundary cuts left dangling clauses ("... no focus group is…").
        self.assertEqual(
            build.truncate_at_boundary("First sentence here. The second sentence is far longer than the limit.", 21),
            "First sentence here.",
        )
        self.assertEqual(build.truncate_at_boundary("alpha beta gamma delta", 12), "alpha beta…")
        for role in self.data["roles"]:
            summary = role["summary"]
            self.assertTrue(summary[-1] in ".!?", summary)
            self.assertNotIn("no focus group is…", summary)

    def test_published_summaries_speak_in_first_person(self):
        # Defect 6: the card summary must read consistently across roles.
        for role in self.data["roles"]:
            first_sentence = role["summary"].split(". ")[0]
            self.assertRegex(first_sentence, r"(^I |\bI \b|\bI'?m\b|\bI am\b)", role["name"])

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
