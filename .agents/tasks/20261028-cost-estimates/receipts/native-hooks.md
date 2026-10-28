# Native Codex readiness for LHC 1.6.3

Verified after the native install on 2026-10-28 using Codex 0.162.1
app-server over stdio. The installed package is
`/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.6.3`.

Generated the current experimental JSON protocol schema, initialized the
app-server, and called `hooks/list` for the canonical LastHumanCommit checkout.
All nine LHC hooks were enabled and trusted on the first read, with zero hook
errors. Every LHC `sourcePath` points to that installed 1.6.3 package's
`com.openai/hooks/hooks.json`.

Reviewed the exact native commands: four invoke `tools/lhc_entry.py` for
SessionStart/PostCompact instruction intake, UserPromptSubmit plan intake and
PostToolUse heartbeat. Five invoke `tools/lhc_progress_review.py` for the
PostToolUse review or SessionEnd/UserPromptSubmit/Stop/Interrupt invalidation.
The commands preserve their existing flags and fallback behavior; the latter
five now display the installed 1.6.3 fallback path.

Source and installed file hashes match:

| File | SHA-256 |
|---|---|
| `com.openai/hooks/hooks.json` | `451bfba388069d40f301ca6ac67379a9f838b2ba92a41bc9ef506e6745183910` |
| `tools/lhc_entry.py` | `1c02fc3c926146550647cb38c6edce522b186a0e53fbff9ea23a8e84d5e74608` |
| `tools/lhc_progress_review.py` | `24a7e5d6bc738abe3848160d3f4b6d7144f90dca336c50d87416c031a802dfb7` |

Native per-hook hashes (key prefix
`last-human-commit@megamen32-plugins:com.openai/hooks/hooks.json:`):

| Key suffix | Native `currentHash` |
|---|---|
| `post_tool_use:0:0` | `sha256:b15d32b2233626071dc1ea1d9aa4e4899213c7ac64b0c85ff7e5e3a2a1a3979d` |
| `post_tool_use:1:0` | `sha256:bafcd5551236988b7adabf78251f2f458a267a1bc5adc87213d861c79ae34e98` |
| `post_compact:0:0` | `sha256:35d1d7130275867cf677091e6779272ce93dd838246f404ca29571cad581c4c5` |
| `session_start:0:0` | `sha256:b8369fea20d5b36df31b94ae1cb55db9d8627c2dca051e2c2ca07e86421b1539` |
| `session_end:0:0` | `sha256:a99e9f4275d9247b1649e2a1a7bcee395c313805e9a6c84e4eb78c5f1094ac79` |
| `user_prompt_submit:0:0` | `sha256:d9f26bad06b1931d318ff6251602ba8ec4fc6e998a9c0727e5d344ff990e9deb` |
| `user_prompt_submit:1:0` | `sha256:91d01578e4c9f6e43fa3720bac1c7f0757ce4bc58336fad83a86be131d53cfc9` |
| `stop:0:0` | `sha256:50b8b07ca1e22604056d9e313be967c767ff45652b8c0605af793eee1eeea095` |
| `interrupt:0:0` | `sha256:3a19ca77cba55b44a44713980393f6ac3d10e8fa650418f01c16051c3d0e2a61` |

A second independent app-server process called `config/read` and then
`hooks/list`. All nine remained enabled and trusted, and each persisted
`trusted_hash` equals its native `currentHash`. The hook state contains 81
entries. The current hashes already match the previously reviewed hashes;
no `config/batchWrite`, unrelated configuration change, new trust grant or
hook-trust bypass was necessary or performed.

This proves installed command parity and native trust readiness. It does not
claim that a hook executed in a model turn, that a planned model actually ran,
or that this readback alone proves dashboard cost acceptance. No full Codex
configuration or secret value is included.
