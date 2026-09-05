"""Exercise portable factory skill projection and package discovery."""
from pathlib import Path
import importlib.util
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugins/last-human-commit/scripts'
sys.path.insert(0, str(SCRIPTS))
import sync_skills


class FactoryDistributionTests(unittest.TestCase):
    def test_common_native_and_plugin_parity(self):
        self.assertEqual(sync_skills.project_common_skills(
            ROOT / 'src/common', ROOT / 'skills', check=True), [])
        self.assertEqual(sync_skills.compare(
            ROOT / 'skills', ROOT / 'plugins/last-human-commit/skills'), [])

    def test_projection_is_portable_and_preserves_existing_skill(self):
        (ROOT / '.tmp').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / '.tmp') as directory:
            native = Path(directory) / 'skills'
            existing = native / 'worker-code/SKILL.md'
            existing.parent.mkdir(parents=True)
            existing.write_text('existing skill')
            self.assertEqual(sync_skills.project_common_skills(
                ROOT / 'src/common', native, check=False), [])
            self.assertEqual(existing.read_text(), 'existing skill')
            for path in native.glob('*/SKILL.md'):
                for relative in re.findall(r'`((?:\.\./|references/)[^`]+\.(?:md|json))`', path.read_text()):
                    self.assertTrue((path.parent / relative).is_file(), f'{path}: {relative}')
            config = native / 'model-routing/references/model-routing.example.json'
            self.assertEqual(config.read_bytes(),
                             (ROOT / 'src/common/config/model-routing.example.json').read_bytes())
            config.write_text('{}')
            self.assertTrue(sync_skills.project_common_skills(
                ROOT / 'src/common', native, check=True))
            self.assertEqual(config.read_text(), '{}', 'check must not repair drift')

    def test_plugin_discovers_architecture_skill_with_existing_skills(self):
        spec = importlib.util.spec_from_file_location('factory_plugin_validator', SCRIPTS / 'validate.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        discovered = module.discover_skills(ROOT / 'plugins/last-human-commit')
        self.assertIn('architecture-design', discovered)
        self.assertEqual(len(discovered), 21)


if __name__ == '__main__':
    unittest.main()
