from pathlib import Path
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "src/common/agents/Boss.md"
PLUGIN = ROOT / "plugins/last-human-commit/opencode/lhc-boss-v2.ts"


def test_boss_is_the_only_business_critic_role():
    text = ROLE.read_text()
    assert "# Boss" in text
    assert "бесконечные проверки" in text
    assert "безопасность ради видимости безопасности" in text
    assert "планы вместо работы" in text
    assert "первоначальное поручение пользователя" in text
    assert not (ROOT / "src/common/agents/Overseer.md").exists()
    assert not (ROOT / "src/common/tools/lhc_overseer_ack.py").exists()
    assert not (ROOT / "src/common/tools/lhc_progress_review.py").exists()


def test_boss_responds_in_prose_without_a_shape_or_length_cap():
    text = ROLE.read_text()
    assert "Разговаривай как человек с человеком" in text
    assert "ограничение длины" in text
    assert "не выдумывай нарушения" in text
    assert '"verdict"' not in text
    assert '"next_action"' not in text
    assert "Верни **только один JSON-объект**" not in text


def test_boss_injects_the_whole_native_reply_without_json_parsing():
    source = PLUGIN.read_text()
    assert "const advice=bossSpokenText(answer)" in source
    assert "text:advice" in source
    assert 'delivery:"steer"' in source
    assert "verdict(" not in source
    assert "JSON.parse(raw.trim())" not in source
    assert "advice.next_action" not in source
    assert "Ответ только JSON" not in source


def test_opencode2_uses_native_session_and_inherits_current_model():
    text = PLUGIN.read_text()
    for fragment in ('id:"last-human-commit-boss"', 'ctx.session.create(',
                     'ctx.session.switchModel(', 'ctx.session.context(',
                     'ctx.session.wait(', 'ctx.session.synthetic(', 'resume:false',
                     'historyComplete:false', 'ctx.session.hook("context"'):
        assert fragment in text
    assert 'event?.data?.sessionID' in text, 'V2 event payloads use data'
    assert 'codex exec' not in text
    assert 'gpt-6.1-sol' not in text


def test_native_boss_installs_to_opencode_v2_plugin_dir(tmp_path):
    path = ROOT / "plugins/last-human-commit/scripts/install_runtime.py"
    spec = importlib.util.spec_from_file_location("boss_install_runtime", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    home = tmp_path / "user"
    home.mkdir()
    package = ROOT / "plugins/last-human-commit"
    response = module.configure(home, package, "opencode")
    installed = home / ".config/opencode/plugins/lhc-boss-v2.ts"
    assert installed.read_text() == PLUGIN.read_text()
    assert response["plugin"]["files"]["lhc-boss-v2.ts"] == str(installed)
    state = json.loads((home / ".local/state/last-human-commit/opencode.json").read_text())
    assert state["packageRoot"] == str(package.resolve())


def test_retired_codex_boss_sidecar_is_not_invoked():
    for name in ("plugins/last-human-commit/com.openai/hooks/hooks.json",
                 "plugins/last-human-commit/native/codex/com.openai/hooks/hooks.json"):
        assert "lhc_progress_review.py" not in (ROOT / name).read_text()
    assert "lhc_overseer_ack" not in (ROOT / "src/common/tools/lhc_entry.py").read_text()
