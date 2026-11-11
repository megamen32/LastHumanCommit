import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_default_hook_bundle_only_activates_compact_instructions():
    for rel in ("plugins/last-human-commit/hooks/hooks.json",
                "plugins/last-human-commit/hooks/zcode-hooks.json"):
        data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        assert set(data["hooks"]) == {"SessionStart", "PostCompact"}
        for event in data["hooks"].values():
            command = event[0]["hooks"][0]["command"]
            assert "--instructions-only" in command
            assert "--stop-gate" not in command
            assert "--heartbeat-only" not in command
            assert "--git-guard" not in command
