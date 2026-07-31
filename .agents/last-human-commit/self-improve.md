# LastHumanCommit self-improve log

## 2026-07-31 — 5a172fc (Short)

- What slowed or confused L? Hermes learning was implemented as two bounded paths: post-response background review and explicit `/learn`; a source push also left `current` at `b32ef81`, and OpenCode retained old embedded roles until the active bundle/profile checks ran.
- Which instruction should change? Fixed now: `Lead.md` resolves companion profiles/protocols relative to its own source, and the OpenCode adapter documents that rendered profiles retain that source root.
- Which skill, MCP, or tool is missing? `none` — read-only source access and targeted search were sufficient.
- What operation or error repeated? Two release checks exposed the same gap: source Git state versus active harness state. Guard: after every LHC release, verify `current` and each configured profile, not only `origin/main`.
- State: fixed now

## 2026-07-31 — 9901949 (Short)

- What slowed or confused L? A source push does not prove that global marker routers, native profiles, and remote Hermes' `current` use the new canon.
- Which instruction should change? Fixed now: `SHARED_WORKTREE.md` requires start/pre-stage inspection, a five-minute hands-off gate, and final integration review.
- Which skill, MCP, or tool is missing? `none` — marker checks, mtime-aware procedure, and focused plugin tests were sufficient.
- What operation or error repeated? One source-versus-active-installation gap; guard: verify each configured harness and remote `current` before declaring release complete.
- State: fixed now
