import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_runtime.py"


def run_installer(tmp_path: Path, runtime: str) -> dict:
    home = tmp_path / "home"
    home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(home)
    result = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            "--plugin-root",
            str(ROOT),
            "--runtime",
            runtime,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(result.stdout)


def test_opencode_install_creates_native_plugin_and_skill_paths(tmp_path: Path) -> None:
    receipt = run_installer(tmp_path, "opencode")
    config_path = tmp_path / "home" / ".config" / "opencode" / "opencode.json"
    config = json.loads(config_path.read_text())

    assert config["plugin"] == [str(ROOT / "opencode-plugin" / "index.js")]
    assert config["skills"]["paths"] == [str(ROOT / "skills")]
    assert receipt["configured"] == ["opencode"]


def test_zcode_install_creates_enabled_inline_plugin(tmp_path: Path) -> None:
    receipt = run_installer(tmp_path, "zcode")
    config_path = tmp_path / "home" / ".zcode" / "cli" / "config.json"
    config = json.loads(config_path.read_text())

    assert config["plugins"]["dirs"] == [str(ROOT)]
    assert config["plugins"]["enabledPlugins"]["gsd@inline"] is True
    assert receipt["configured"] == ["zcode"]


def test_runtime_updates_preserve_unrelated_configuration(tmp_path: Path) -> None:
    home = tmp_path / "home"
    opencode_path = home / ".config" / "opencode" / "opencode.json"
    opencode_path.parent.mkdir(parents=True)
    opencode_path.write_text(json.dumps({"model": "example/model", "plugin": ["other"]}))
    zcode_path = home / ".zcode" / "cli" / "config.json"
    zcode_path.parent.mkdir(parents=True)
    zcode_path.write_text(
        json.dumps(
            {
                "theme": "dark",
                "plugins": {"dirs": ["/other"], "enabledPlugins": {"other@inline": True}},
            }
        )
    )
    env = os.environ.copy()
    env["HOME"] = str(home)

    subprocess.run(
        [sys.executable, str(INSTALLER), "--plugin-root", str(ROOT), "--runtime", "all"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    opencode = json.loads(opencode_path.read_text())
    zcode = json.loads(zcode_path.read_text())
    assert opencode["model"] == "example/model"
    assert opencode["plugin"] == ["other", str(ROOT / "opencode-plugin" / "index.js")]
    assert zcode["theme"] == "dark"
    assert zcode["plugins"]["dirs"] == ["/other", str(ROOT)]
    assert zcode["plugins"]["enabledPlugins"]["other@inline"] is True

