# Megamen32 Plugins

This repository is the curated GitHub marketplace for the author's Codex
plugins. The first entry is `last-human-commit`; more plugins can be appended to
`.agents/plugins/marketplace.json` without creating a separate marketplace per
package.

The repository marketplace is intentionally source-only. It does not install or
enable anything on a user's machine. The catalog points at plugin directories
inside this repository, and each plugin owns its own Codex manifest, commands, skills,
optional Claude/OpenCode projections, and optional MCP companion files.

## Current catalog

| Plugin | Version | Contents | Source |
| --- | --- | --- | --- |
| `last-human-commit` | `1.0.0` | Codex, OpenCode, Claude Code workflow + LHC operator skills (lhc-update-agents, lhc-rollout) | `./plugins/last-human-commit` |
| `ask-human` | `0.2.0` | Important-info channel to the human (AskHuman/notify MCP) | `./plugins/ask-human` |

## Validate

From the repository root:

```bash
python3 .agents/plugins/validate_marketplace.py
python3 plugins/last-human-commit/scripts/validate.py
```

The marketplace validator checks JSON shape, unique names, required policy
fields, package-local source paths, and the plugin manifest name. It does not
modify Codex configuration.

## Add the next package

1. Add a self-contained directory under `plugins/<lowercase-name>/`.
2. Include `.codex-plugin/plugin.json` and keep all referenced files inside that
   package.
3. Put portable skills under the package's `skills/` directory.
4. If the package includes MCP, keep its `.mcp.json` or `.app.json` next to the
   manifest and exclude credentials from Git.
5. Append one entry to `marketplace.json` and rerun both validators.

To register this GitHub marketplace locally in Codex, use the documented
command only when you explicitly want to change local Codex state:

```bash
codex plugin marketplace add megamen32/LastHumanCommit --ref main
```
