# Get Shit Done Agent Plugin

This is a portable Agent Plugin wrapper for the upstream
[`get-shit-done-cc`](https://github.com/gsd-build/get-shit-done) 1.42.3 release.
It keeps the full 67-skill profile, bundled workflows, agent prompts, and SDK in
one versioned package. The wrapper only adapts install-root resolution and
named-agent fallback; upstream workflow content is copied from the release.

Build provenance is recorded in `UPSTREAM.json`. Rebuild from an isolated
upstream Codex projection with `scripts/build_from_upstream.py`.

`scripts/emit_opencode.py` is a generic Agent Plugins 1.0 to OpenCode emitter.
It generates the native `opencode-plugin/index.js` compatibility module, the npm
`package.json`, and a static OpenCode config fragment without changing upstream
GSD or OpenCode. GSD has no MCP servers, so its generated JS module is deliberately
minimal; skills are discovered through the generated `skills.paths` entry.
