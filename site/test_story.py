"""New landing regressions: complete workflow, real source, bilingual interface."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path
import build
from story import create_story, read_section


class StoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build.build()

    def test_full_cycle_contains_actual_development_sequence(self):
        full = self.data["story"]["full"]
        self.assertEqual([s["id"] for s in full], [
            "intent", "research", "options", "ideal", "yagni", "decompose", "parallel",
            "estimate", "workers", "review", "deploy", "test", "repair", "integrate",
        ])
        self.assertEqual([s["number"] for s in full], [f"{i:02d}" for i in range(1, 15)])

    def test_quick_retains_real_verification_and_delivery(self):
        quick = self.data["story"]["quick"]
        self.assertEqual([s["id"] for s in quick], ["intent", "quick-plan", "workers", "deploy", "test", "integrate"])
        self.assertEqual(quick[-1]["source"], self.data["story"]["full"][-1]["source"])
        self.assertEqual([s["number"] for s in quick], [f"{i:02d}" for i in range(1, 7)])

    def test_every_stage_is_pinned_to_exact_canonical_source(self):
        for mode in ("full", "quick"):
            for stage in self.data["story"][mode]:
                prefix = self.data["repository"] + "/blob/" + self.data["revision"] + "/"
                self.assertTrue(stage["source"].startswith(prefix))
                path = stage["source"][len(prefix):].split("#")[0]
                original = (build.ROOT / path).read_text(encoding="utf-8")
                excerpt = stage["sourceExcerpt"].removesuffix("…")
                self.assertIn(excerpt, original)
        self.assertIn("PRODUCT-PHILOSOPHY.md#L", self.data["story"]["gapsSource"])

    def test_absent_canonical_section_fails_instead_of_publishing_stale_text(self):
        with self.assertRaisesRegex(ValueError, "Missing canonical"):
            read_section("# empty", "4.2")

    @unittest.skipUnless(shutil.which("node"), "Node required for dictionary test")
    def test_every_visible_string_and_story_stage_has_both_languages(self):
        script = r'''
const fs = require('node:fs'); const vm = require('node:vm');
const assert = require('node:assert/strict'); const sandbox = {window:{}};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
const i18n = sandbox.window.LHC_I18N;
const html = fs.readFileSync(process.argv[2], 'utf8');
const data = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const keys = [...html.matchAll(/data-(?:copy(?:-html)?|label)="([^"]+)"/g)].map(m=>m[1]);
for(const mode of ['full','quick']) for(const s of data.story[mode]) keys.push(s.titleKey,s.copyKey);
for(const key of keys) {
  assert.ok(i18n.messages[key], 'Missing UI key '+key);
  assert.match(i18n.t(key,'en'), /[A-Za-z]/, 'English missing '+key);
  assert.match(i18n.t(key,'ru'), /[А-Яа-яЁё]/, 'Russian missing '+key);
}
assert.match(i18n.t('hero.heading','ru'), /Ваш замысел/);
assert.match(i18n.t('truth.note','ru'), /не утверждает/);
console.log('All narrative and visible interface keys are bilingual.');
'''
        result = subprocess.run(["node", "-e", script, str(build.SITE / "i18n.js"),
                                 str(build.SITE / "index.html"), str(build.DIST / "data.json")],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
