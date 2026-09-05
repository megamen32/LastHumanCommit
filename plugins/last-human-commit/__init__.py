"""Native Hermes extension of the portable Agent Plugin package."""
import importlib.util
from pathlib import Path

def register(ctx):
    root = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location('lhc_hermes_adapter', root / 'com.nousresearch.hermes/__init__.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._root = lambda: root
    module.register(ctx)
    for skill in sorted((root / 'skills').iterdir()):
        if (skill / 'SKILL.md').is_file():
            ctx.register_skill(skill.name, skill / 'SKILL.md')
