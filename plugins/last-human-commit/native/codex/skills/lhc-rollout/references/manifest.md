# Manifest

Use JSON schema version 1. Paths inside a source repository or target home must
be relative. `source.revision` resolves to an immutable Git commit before any
host work.

```json
{
  "schemaVersion": 1,
  "source": {
    "repo": "/home/roomhacker/agents-projects/LastHumanCommit",
    "revision": "main",
    "versionLength": 7,
    "version": [
      {"source": "src/common", "destination": "common"},
      {"source": "templates", "destination": "templates"},
      {"source": "adapters", "destination": "adapters"}
    ],
    "routers": {
      "AGENTS.md": "AGENTS.md",
      "CLAUDE.md": "CLAUDE.md"
    },
    "copies": {
      "hermes": "adapters/hermes/plugin"
    }
  },
  "install": {
    "store": ".local/share/last-human-commit",
    "projectRuntime": null,
    "rollback": "rollbacks/{version}-lhc-rollout",
    "markerBegin": "<!-- last-human-commit:begin -->",
    "markerEnd": "<!-- last-human-commit:end -->",
    "freshSeconds": 300,
    "globalReplace": {
      "src/common/": "{current}/common/"
    }
  },
  "targets": [
    {
      "name": "100",
      "transport": "ssh",
      "sshTarget": "100",
      "port": 22104,
      "python": "python3",
      "home": "/home/roomhacker",
      "projectRoot": "gptadmin",
      "routers": [
        {"path": ".codex/AGENTS.md", "template": "AGENTS.md"},
        {"path": ".claude/CLAUDE.md", "template": "CLAUDE.md"},
        {"path": ".config/opencode/AGENTS.md", "template": "AGENTS.md"}
      ],
      "projects": [
        {
          "path": "gptadmin",
          "routers": [
            {"path": "AGENTS.md", "template": "AGENTS.md"},
            {"path": "CLAUDE.md", "template": "CLAUDE.md"}
          ]
        }
      ],
      "copies": [
        {"source": "hermes", "path": ".hermes/plugins/last-human-commit"}
      ]
    }
  ]
}
```

`transport` is `local` or `ssh`. For `local`, omit SSH fields. For macOS, set
`python` to the actual Python 3 path when `python3` is unavailable in a remote
non-login shell.

Every target requires `projectRoot`, a safe path relative to `home` naming the
exact Git project used for temporary rollout staging. Its `.tmp/` must be
Git-ignored and must not be a symlink. SSH upload staging is created only below
`<home>/<projectRoot>/.tmp/lhc-rollout/incoming/`; a missing project, path escape,
different Git top-level, unignored `.tmp/`, or symlink fails before upload.

Set `install.projectRuntime` to `null` for machine-wide mode: no per-project `.last-human-commit/` copy is created or verified, and project routers reference the machine store (`{current}`) through `globalReplace`. A string value keeps the legacy per-project runtime mode.

The script exports only committed Git bytes, generates `VERSION`, hashes the
complete version tree, and binds apply to the preview confirmation. Router
updates replace only the managed marker block. Project and copy replacements
retain sibling `.prev-VERSION` directories. `install.rollback` is relative to
the configured store, must include `{version}`, is previewed and
confirmation-bound, and is verified together with the retained copies.
