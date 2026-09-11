# Get Shit Done Agent Plugin

This is a portable Agent Plugin wrapper for the upstream
[`get-shit-done-cc`](https://github.com/gsd-build/get-shit-done) 1.42.3 release.
It keeps the full 67-skill profile, bundled workflows, agent prompts, and SDK in
one versioned package. The wrapper only adapts install-root resolution and
named-agent fallback; upstream workflow content is copied from the release.

## Install

Codex, through the public `megamen32-public` marketplace:

```bash
codex plugin marketplace add megamen32/megamen32-public-marketplace --ref main
codex plugin add gsd@megamen32-public
```

Claude Code, through the same marketplace repository:

```bash
claude plugin marketplace add megamen32/megamen32-public-marketplace
claude plugin install gsd@megamen32-public-claude
```

OpenCode and ZCode use the portable package from a stable checkout. The small
runtime adapter only adds this checkout to each runtime's supported plugin and
skill configuration:

```bash
git clone --depth 1 https://github.com/megamen32/gsd-agent-plugin.git \
  ~/.local/share/gsd-agent-plugin
npm install --omit=dev --prefix ~/.local/share/gsd-agent-plugin
python3 ~/.local/share/gsd-agent-plugin/scripts/install_runtime.py --runtime all
```

Use `--runtime opencode` or `--runtime zcode` to configure only one runtime.
Existing JSON configuration is preserved and backed up under
`~/.local/state/gsd-agent-plugin/` before it is changed. Restart the runtime or
start a new session after installation.

Build provenance is recorded in `UPSTREAM.json`. Rebuild from an isolated
upstream Codex projection with `scripts/build_from_upstream.py`.

`scripts/emit_opencode.py` is a generic Agent Plugins 1.0 to OpenCode emitter.
It generates the native `opencode-plugin/index.js` compatibility module, the npm
`package.json`, and a static OpenCode config fragment without changing upstream
GSD or OpenCode. GSD has no MCP servers, so its generated JS module is deliberately
minimal; skills are discovered through the generated `skills.paths` entry.
