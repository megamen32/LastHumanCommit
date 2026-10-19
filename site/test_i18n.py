"""Translation packaging and source-preservation regressions (stdlib only)."""
import hashlib
import json
import shutil
import subprocess
import unittest
from pathlib import Path

import build


class LanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build.build()

    def test_language_assets_are_versioned_and_in_order(self):
        markup = (build.DIST / "index.html").read_text(encoding="utf-8")
        for filename in ("styles.css", "locale.css", "i18n.js", "app.js"):
            artifact = build.DIST / filename
            self.assertTrue(artifact.is_file())
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()[:12]
            self.assertIn(f'"./{filename}?v={digest}"', markup)
        self.assertLess(markup.index("./i18n.js"), markup.index("./app.js"))
        self.assertIn('data-lang="en"', markup)
        self.assertIn('data-lang="ru"', markup)

    @unittest.skipUnless(shutil.which("node"), "Node is needed for JavaScript dictionary validation")
    def test_ui_dictionary_covers_all_generated_loop_copy(self):
        script = r'''
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const sandbox = { window: {} };
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
const i18n = sandbox.window.LHC_I18N;
const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
for (const mode of Object.values(data.modes)) {
  for (const key of [mode.note, mode.tagline, ...mode.steps.flatMap(s => [s.title, s.editorial])]) {
    assert.ok(i18n.messages[key], 'Missing translation: ' + key);
    assert.equal(i18n.t(key, 'en'), key);
    assert.match(i18n.t(key, 'ru'), /[А-Яа-яЁё]/);
  }
}
for (const entry of Object.values(i18n.messages)) {
  assert.equal(entry.length, 2);
  assert.equal(typeof entry[0], 'string');
  assert.equal(typeof entry[1], 'string');
  const tokens = value => (value.match(/\{\w+\}/g) || []).sort().join(',');
  assert.equal(tokens(entry[0]), tokens(entry[1]), 'Mismatched interpolation variables');
}
assert.equal(i18n.t('step', 'ru', {number: '03'}), 'ЭТАП / 03');
assert.equal(i18n.t('unknown source text', 'ru'), 'unknown source text');
console.log('All generated loop copy has an English and Russian UI translation.');
'''
        result = subprocess.run(
            ["node", "-e", script, str(build.SITE / "i18n.js"), str(build.DIST / "data.json")],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_git_role_definitions_have_no_translated_duplicates(self):
        snapshot = json.loads((build.DIST / "data.json").read_text(encoding="utf-8"))
        for role in snapshot["roles"]:
            original = build.ROOT / "src/common/agents" / (role["name"] + ".md")
            self.assertEqual(role["details"], original.read_text(encoding="utf-8"))
        self.assertNotIn("translatedRoles", snapshot)
        self.assertFalse(list(build.SITE.glob("*.ru.md")))


if __name__ == "__main__":
    unittest.main()
