"""A new Codex session gives the hook tools back to versions Codex pruned by itself."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_entry  # noqa: E402


def test_session_start_restores_pruned_versions_and_records_its_own(tmp_path):
    codex = tmp_path / ".codex"
    cache = codex / "plugins/cache/megamen32-plugins/last-human-commit"
    live = cache / "1.16.0" / "tools"
    live.mkdir(parents=True)
    (live / "lhc_entry.py").write_text("")
    market = codex / ".tmp/marketplaces/megamen32-plugins/plugins/last-human-commit/tools"
    market.mkdir(parents=True)
    (market / "lhc_entry.py").write_text("")
    state = tmp_path / "state"
    (state / "lhc").mkdir(parents=True)
    (state / "lhc/codex-plugin-versions.json").write_text(json.dumps(["1.15.0", "1.15.1"]))
    kept = cache / "1.15.1" / "tools"
    kept.mkdir(parents=True)

    restored = lhc_entry.restore_codex_routes(tools=live, codex_home=codex, state_home=state)

    assert restored == ["1.15.0"]
    assert (cache / "1.15.0/tools/lhc_entry.py").is_file()
    assert not kept.is_symlink(), "an existing tools directory is never replaced"
    assert json.loads((state / "lhc/codex-plugin-versions.json").read_text()) == ["1.15.0", "1.15.1", "1.16.0"]


def test_outside_the_codex_cache_nothing_happens(tmp_path):
    tools = tmp_path / "repo/tools"
    tools.mkdir(parents=True)
    assert lhc_entry.restore_codex_routes(tools=tools, codex_home=tmp_path / ".codex", state_home=tmp_path) == []
    assert not (tmp_path / "lhc").exists()
