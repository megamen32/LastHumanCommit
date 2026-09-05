# Last Human Commit plugin

This directory is a self-contained Agent Plugin package for Codex, OpenCode,
Claude Code, and Hermes. Skills, shared role/protocol sources, the Hermes
adapter, and executable tools are generated from this repository; generated
files must not be edited by hand.

The package contains no MCP server, credentials, or runtime configuration
changes. Native hooks and the Hermes adapter are included for clients that
support them. Nothing is installed or enabled by validation commands.

## Build and validate

From the `LastHumanCommit` repository:

```bash
python3 plugins/last-human-commit/scripts/sync_skills.py
python3 plugins/last-human-commit/scripts/sync_skills.py --check
python3 plugins/last-human-commit/scripts/validate.py
```

The validator checks the portable manifest, the two native manifests, skill
frontmatter, package-contained paths, symlink absence, and byte-for-byte parity
with `LastHumanCommit/skills/`.

## Runtime entrypoints

- Codex reads `.codex-plugin/plugin.json` and its `./skills/` entry.
- Claude Code reads `.claude-plugin/plugin.json` and its root `./skills/` entry.
- OpenCode can consume the same skill tree through its native `skills.paths`
  config object. Print a non-mutating fragment with:

  ```bash
  python3 plugins/last-human-commit/scripts/opencode-config.py
  ```

  The default `native` format matches the installed OpenCode 1.18.x surface.
  For the newer documented v2 array shape, use
  `--format v2`. The helper writes a file only when an explicit `--output PATH`
  is supplied; merge its `skills` value into the intended project configuration
  yourself.

Run focused read-only loader checks with:

```bash
python3 plugins/last-human-commit/scripts/loader_canary.py codex
python3 plugins/last-human-commit/scripts/loader_canary.py claude
python3 plugins/last-human-commit/scripts/loader_canary.py opencode
```

These checks validate the package loader shapes. They do not install the
package, alter user configuration, or claim a live interactive runtime session.
