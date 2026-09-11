import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EMITTER = ROOT / "scripts/emit_opencode.py"
CONFIGURATOR = ROOT / "scripts/configure_runtime.py"


def make_agent_plugin(tmp_path: Path) -> Path:
    plugin = tmp_path / "demo-plugin"
    (plugin / "skills/demo").mkdir(parents=True)
    (plugin / "runtime").mkdir()
    (plugin / "skills/demo/SKILL.md").write_text(
        "---\nname: demo\ndescription: Demo skill\n---\n"
    )
    (plugin / "runtime/helper.txt").write_text("runtime payload\n")
    (plugin / "plugin.json").write_text(
        json.dumps(
            {
                "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                "name": "demo",
                "version": "2.3.4",
                "description": "Demo portable plugin",
                "skills": "./skills/",
            }
        )
    )
    (plugin / "mcp.json").write_text(
        json.dumps(
            {
                "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
                "mcpServers": {
                    "remote-docs": {
                        "type": "streamable-http",
                        "url": "https://example.test/mcp",
                        "headers": {"X-Demo": "yes"},
                    },
                    "local-tool": {
                        "type": "stdio",
                        "command": "demo-mcp",
                        "args": ["--stdio"],
                        "env": {"DEMO_MODE": "1"},
                    },
                },
            }
        )
    )
    return plugin


def test_generic_emitter_builds_opencode_npm_projection(tmp_path: Path):
    plugin = make_agent_plugin(tmp_path)
    subprocess.run(
        [
            sys.executable,
            str(EMITTER),
            str(plugin),
            "--package-name",
            "@example/demo-opencode-plugin",
            "--include",
            "runtime",
        ],
        check=True,
    )

    package = json.loads((plugin / "package.json").read_text())
    assert package["name"] == "@example/demo-opencode-plugin"
    assert package["version"] == "2.3.4"
    assert package["main"] == "opencode-plugin/index.js"
    assert package["exports"] == {".": "./opencode-plugin/index.js"}
    assert set(package["files"]) >= {
        "opencode-plugin/",
        "skills/",
        "plugin.json",
        "mcp.json",
        "runtime/",
    }

    fragment = json.loads((plugin / "opencode-plugin/opencode.json").read_text())
    assert fragment["plugin"] == ["@example/demo-opencode-plugin"]
    assert fragment["skills"]["paths"] == [
        "node_modules/@example/demo-opencode-plugin/skills"
    ]

    probe = """
      const mod = await import(process.argv[1]);
      if (Object.keys(mod).join(',') !== 'default') throw new Error('named exports');
      const hooks = await mod.default({});
      const config = {mcp: {"remote-docs": {type: "remote", url: "override"}}};
      await hooks.config(config);
      console.log(JSON.stringify(config));
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", probe, (plugin / "opencode-plugin/index.js").as_uri()],
        check=True,
        capture_output=True,
        text=True,
    )
    config = json.loads(result.stdout)
    assert config["mcp"]["remote-docs"]["url"] == "override"
    assert config["mcp"]["local-tool"] == {
        "type": "local",
        "command": ["demo-mcp", "--stdio"],
        "environment": {"DEMO_MODE": "1"},
        "enabled": True,
    }

    subprocess.run(
        [
            sys.executable,
            str(EMITTER),
            str(plugin),
            "--package-name",
            "@example/demo-opencode-plugin",
            "--include",
            "runtime",
            "--check",
        ],
        check=True,
    )


def test_runtime_configures_native_opencode_shim(tmp_path: Path):
    home = tmp_path / "home"
    config_dir = home / ".config/opencode"
    config_dir.mkdir(parents=True)
    (config_dir / "opencode.json").write_text(
        json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "plugin": ["foreign-plugin"],
                "skills": {"paths": ["/foreign/skills"]},
            }
        )
    )
    env = os.environ.copy()
    env["HOME"] = str(home)
    subprocess.run(
        [sys.executable, str(CONFIGURATOR), "--plugin-root", str(ROOT)],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )

    config = json.loads((config_dir / "opencode.json").read_text())
    assert "foreign-plugin" in config["plugin"]
    assert str(ROOT / "opencode-plugin/index.js") in config["plugin"]
    assert "/foreign/skills" in config["skills"]["paths"]
    assert str(ROOT / "skills") in config["skills"]["paths"]


def test_generic_emitter_accepts_mcp_only_agent_plugin(tmp_path: Path):
    plugin = tmp_path / "mcp-only"
    plugin.mkdir()
    (plugin / "plugin.json").write_text(
        json.dumps(
            {
                "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                "name": "mcp-only",
                "version": "1.0.0",
            }
        )
    )
    (plugin / "mcp.json").write_text(
        json.dumps(
            {
                "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
                "mcpServers": {
                    "docs": {
                        "type": "streamable-http",
                        "url": "https://example.test/mcp",
                    }
                },
            }
        )
    )

    subprocess.run(
        [
            sys.executable,
            str(EMITTER),
            str(plugin),
            "--package-name",
            "@example/mcp-only",
        ],
        check=True,
    )
    package = json.loads((plugin / "package.json").read_text())
    fragment = json.loads((plugin / "opencode-plugin/opencode.json").read_text())
    assert "skills/" not in package["files"]
    assert "skills" not in fragment
