# Native Codex hook readiness after LHC 1.6.5 install

Verified on 2026-10-28 with Codex 0.162.1 native app-server over stdio,
using the canonical LastHumanCommit checkout as `hooks/list` cwd. This receipt
covers the newly installed definitions and persisted trust, not a reload of an
already running chat's cached hook commands.

Installed root:
`/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.6.5`.

Compared source and installed bytes before reviewing trust:

| Installed file | Matching SHA-256 |
|---|---|
| `com.openai/hooks/hooks.json` | `966dde4447f5b5a0e541b85d6323a36c11167afffa0b6d0cc93fccd34844c7d5` |
| `tools/lhc_entry.py` | `1c02fc3c926146550647cb38c6edce522b186a0e53fbff9ea23a8e84d5e74608` |
| `tools/lhc_progress_review.py` | `24a7e5d6bc738abe3848160d3f4b6d7144f90dca336c50d87416c031a802dfb7` |

Native `hooks/list` returned nine enabled LHC hooks, all with source paths in
the installed 1.6.5 package. Reviewed their exact commands: four existing entry
hooks remain unchanged; five progress-review hooks now select the package-root
script when it exists, otherwise use the official marketplace tools path.
The normal PostToolUse progress command keeps its asynchronous setting. The
other four keep `--invalidate`. No command restarts Codex or replays a user turn.

Before the trust write, four hooks were trusted and the five modified commands
were marked `modified`. Their new native hashes are:

| Key suffix after `com.openai/hooks/hooks.json:` | `currentHash` |
|---|---|
| `post_tool_use:1:0` | `sha256:4e39bc5ae169e16f6ed3957ea6ce3dc29a11bd7672760da29e0689c2bbd1a46b` |
| `session_end:0:0` | `sha256:fa9fb732fbaf4cdca83622b7f998ea32d897751846ffa3e0c92d5a0952dc4d96` |
| `user_prompt_submit:1:0` | `sha256:6bc7d06a7a31deba8c146c8e4fc70a1fe787315f2b31f2e5bea5f10e4edca230` |
| `stop:0:0` | `sha256:c1560dae0f9ca072afda1466d314143f8d982f8e6b11be846c94975c9e1eed15` |
| `interrupt:0:0` | `sha256:81319707735540d362b8c63bd255630795d3c2d2a982fe281d5a27c5bfed160d` |

Used the generated native `ConfigBatchWriteParams` schema to check the scoped
request shape and enum, then called `config/batchWrite` with one `hooks.state`
`upsert` containing only the nine reviewed current LHC keys, each with
`enabled=true` and `trusted_hash=currentHash`; `reloadUserConfig=true`.
The first local validation attempt stopped before a write because the optional
`jsonschema` module was absent; the subsequent request used the schema's direct
required-field, type and merge-strategy checks without installing dependencies.

Native write returned `status=ok`, receipt version
`sha256:6783eda037d29ba4c9d1fcd4cdcea0020bfb72c6ebe93197d0a5a567b8562b38`.
Follow-up `config/read` and `hooks/list` verified all nine hooks enabled and
trusted, with every persisted hash matching its current native hash. The state
entry count stayed 81; all 72 entries outside the selected LHC keys remained
byte-for-value identical. Only the five reviewed LHC trust hashes changed.

No hook-trust bypass, app restart, user-message replay, unrelated plugin grant
or full-config output was used. Existing cached commands in an old chat depend
on the separately verified compatibility-path repair; this fresh app-server
readback alone does not establish that old chat's runtime behavior.

After the final native-install wrapper canary from source `da943d1`, a fresh
app-server process repeated only initialization and `hooks/list`. All nine
hooks remained enabled and trusted, with zero hook errors and source paths in
the installed 1.6.5 package. The three source/installed hashes above still
matched. This final check performed no configuration write, started no model
turn, and sent no message to an existing chat.
