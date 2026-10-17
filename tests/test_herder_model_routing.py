"""Existing Herder must be the model-selection path; no additional tool surface."""
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[1]

def test_native_entry_points_to_existing_herder_before_subagent_selection():
    spec=importlib.util.spec_from_file_location('entry_model_routing', ROOT/'src/common/tools/lhc_entry.py')
    entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
    text=entry.context_for({},ROOT)
    assert 'Agent Herder' in text and 'new_or_resume' in text and 'model' in text
    assert str(ROOT/'src/common/skills/model-routing/SKILL.md') in text
    assert 'lhc_delegate' not in text
    assert len(text)<2200

def test_model_routing_separates_role_route_and_real_model():
    text=(ROOT/'src/common/skills/model-routing/SKILL.md').read_text()
    for value in ('new_or_resume','create_session','gpt-6.1-sol','gpt-6-luna','MiniMax-M3.1-Flash-Preview','glm-5.3-flash','glm-5.3','sourceSessionId','inputId'):
        assert value in text
    assert 'no new tool' in text
    assert 'Zero Knowledge' in text and 'fresh' in text
    assert 'OpenChamber Auto' in text
    assert 'per-message' in text and 'not' in text
