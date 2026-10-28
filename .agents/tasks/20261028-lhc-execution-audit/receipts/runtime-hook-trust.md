# Native Codex hook trust readback

This receipt covers only the server-100 Codex plugin hooks for LHC 1.6.2. It
records trusted configuration and app-server readback; it does not claim that
the hooks executed in a model turn or that the independent repair canary passed.

## Source and installed package

- Installed package: `/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.6.2`.
- Effective manifest: `com.openai/hooks/hooks.json`.
- SHA-256 of source and installed manifest both equals
  `451bfba388069d40f301ca6ac67379a9f838b2ba92a41bc9ef506e6745183910`.
- Source and installed file bytes therefore match for the effective Codex hook
  manifest. This check does not establish parity of every package file.

## Reviewed commands and current hashes

The native `hooks/list` response identified nine hooks with plugin ID
`last-human-commit@megamen32-plugins`, source path under the installed 1.6.2
package, `handlerType=command`, and the following command/event pairs. Each
command resolves to one of the package's reviewed `tools/lhc_entry.py` or
`tools/lhc_progress_review.py` entrypoints. The native hashes below are the
current per-hook hashes returned by `hooks/list` after inspecting those exact
commands; they are not hashes copied from the earlier manifest namespace.

| Hook key suffix | Event | Installed command | `currentHash` |
|---|---|---|---|
| `post_tool_use:0:0` | `postToolUse` | `python3 "${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${PLUGIN_ROOT:-${ZCODE_PLUGIN_ROOT:-$HOME/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit}}}}/tools/lhc_entry.py" --event PostToolUse --heartbeat-only || { printf '%s\\n' 'LHC entry unavailable; message processing continues.' >&2; :; }` | `sha256:b15d32b2233626071dc1ea1d9aa4e4899213c7ac64b0c85ff7e5e3a2a1a3979d` |
| `post_tool_use:1:0` | `postToolUse` | `python3 "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.6.2}}/tools/lhc_progress_review.py"` | `sha256:bafcd5551236988b7adabf78251f2f458a267a1bc5adc87213d861c79ae34e98` |
| `post_compact:0:0` | `postCompact` | `python3 "${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${PLUGIN_ROOT:-${ZCODE_PLUGIN_ROOT:-$HOME/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit}}}}/tools/lhc_entry.py" --event PostCompact --instructions-only || { printf '%s\\n' 'LHC entry unavailable; message processing continues.' >&2; :; }` | `sha256:35d1d7130275867cf677091e6779272ce93dd838246f404ca29571cad581c4c5` |
| `session_start:0:0` | `sessionStart` | `python3 "${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${PLUGIN_ROOT:-${ZCODE_PLUGIN_ROOT:-$HOME/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit}}}}/tools/lhc_entry.py" --event SessionStart --instructions-only || { printf '%s\\n' 'LHC entry unavailable; message processing continues.' >&2; :; }` | `sha256:b8369fea20d5b36df31b94ae1cb55db9d8627c2dca051e2c2ca07e86421b1539` |
| `session_end:0:0` | `sessionEnd` | `python3 "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.6.2}}/tools/lhc_progress_review.py" --invalidate` | `sha256:a99e9f4275d9247b1649e2a1a7bcee395c313805e9a6c84e4eb78c5f1094ac79` |
| `user_prompt_submit:0:0` | `userPromptSubmit` | `python3 "${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${PLUGIN_ROOT:-${ZCODE_PLUGIN_ROOT:-$HOME/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit}}}}/tools/lhc_entry.py" --event UserPromptSubmit --plan-entry || { printf '%s\\n' 'LHC local plan entry unavailable; message processing continues.' >&2; :; }` | `sha256:d9f26bad06b1931d318ff6251602ba8ec4fc6e998a9c0727e5d344ff990e9deb` |
| `user_prompt_submit:1:0` | `userPromptSubmit` | `python3 "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.6.2}}/tools/lhc_progress_review.py" --invalidate` | `sha256:91d01578e4c9f6e43fa3720bac1c7f0757ce4bc58336fad83a86be131d53cfc9` |
| `stop:0:0` | `stop` | `python3 "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.6.2}}/tools/lhc_progress_review.py" --invalidate` | `sha256:50b8b07ca1e22604056d9e313be967c767ff45652b8c0605af793eee1eeea095` |
| `interrupt:0:0` | `interrupt` | `python3 "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.6.2}}/tools/lhc_progress_review.py" --invalidate` | `sha256:3a19ca77cba55b44a44713980393f6ac3d10e8fa650418f01c16051c3d0e2a61` |

## Native configuration write and readback

Used Codex CLI 0.162.1 app-server over stdio, initialized with the generated
protocol schema. The calls were:

1. `hooks/list` with the repository cwd to identify effective plugin hooks,
   their exact commands, `currentHash`, and `trustStatus`.
2. `config/batchWrite` with one edit at `hooks.state`, merge strategy `upsert`,
   containing only the nine IDs above, each with `enabled=true` and that same
   entry's `trusted_hash=currentHash`. `reloadUserConfig=true`.
3. `config/read` followed by `hooks/list` to verify persisted state and effective
   runtime status.

Before the write all nine hooks were enabled but `untrusted`; the state keys
used the legacy `hooks/hooks.json` namespace and did not authorize the active
`com.openai/hooks/hooks.json` definitions. The write returned status `ok` with
config receipt version
`sha256:5caf91fad4bc43bf4cd20e57b4839924bc70a9a4dbf78fe38a06c55ad973d201`.
The readback found all nine hooks `enabled=true` and `trustStatus=trusted`, with
the same current hashes as before the write. It also found all 72 previously
present hook-state entries unchanged; only the nine new LHC keys were added.

No unrelated plugin was enabled or trusted. No STOP policy was changed, no
legacy hash was reused, and no hook-trust bypass was used. This receipt includes
no full Codex configuration and no sensitive values.
