# Last Human Commit self-improve log

## 2026-07-31 — 5a172fc (Short)

- What slowed or confused L? Hermes learning was implemented as two bounded paths: post-response background review and explicit `/learn`; a source push also left `current` at `b32ef81`, and OpenCode retained old embedded roles until the active bundle/profile checks ran.
- Which instruction should change? Fixed now: `Lead.md` resolves companion profiles/protocols relative to its own source, and the OpenCode adapter documents that rendered profiles retain that source root.
- Which skill, MCP, or tool is missing? `none` — read-only source access and targeted search were sufficient.
- What operation or error repeated? Two release checks exposed the same gap: source Git state versus active harness state. Guard: after every LHC release, verify `current` and each configured profile, not only `origin/main`.
- State: fixed now

## 2026-07-31 — 9901949 (Short)

- What slowed or confused L? A source push does not prove that global marker routers, native profiles, and remote Hermes' `current` use the new LHC release.
- Which instruction should change? Fixed now: `SHARED_WORKTREE.md` requires start/pre-stage inspection, a five-minute hands-off gate, and final integration review.
- Which skill, MCP, or tool is missing? `none` — marker checks, mtime-aware procedure, and focused plugin tests were sufficient.
- What operation or error repeated? One source-versus-active-installation gap; guard: verify each configured harness and remote `current` before declaring release complete.
- State: fixed now

## 2026-08-01 — outcome-first LHC review (Full, planning gate)

- What slowed or confused L? `Lead.md:12-21` says canary first, while `Lead.md:52-54` and `tests/validate.py:209` mandate and protect unbounded whole-repository review.
- Which instruction should change? `Lead.md`, `Reviewer.md`, profiles, templates, docs, and validator need one explicit precedence rule; exact breadth awaits human plan selection.
- Which skill, MCP, or tool is missing? `context-mode` was bound to TelegramAuto and blocked Last Human Commit file analysis; fallback was bounded local reads.
- What operation or error repeated? Two context-mode shell loops were rewritten into invalid `NODE_OPTIONS=... for`; guard by using direct commands without shell loops.
- State: needs human decision

## 2026-08-01 — Graphify OmniRoute best-free backend (Short)

- What slowed or confused L? “All global copies” was inferred from three local paths; Fleet later proved 44/88/Mac lacked the CLI/config and most harness copies were stale or missing.
- Which instruction should change? Fixed now: cross-host completion requires a host-by-harness matrix; one discovered copy can no longer stand in for a global skill claim.
- Which skill, MCP, or tool is missing? Fixed now in Agent Fleet as generic `skill-inventory`, not a Graphify-specific API: it preserves duplicate harness instances, compares full skill-directory digests with Base, and fingerprints conventional per-skill env values without returning them.
- What operation or error repeated? Three assumptions failed live: stale key `401`, SSE-vs-JSON response, and local-only proof presented as fleet-global; the live 100/44/88/Mac inventory now exposes missing copies, digest drift, and configuration fingerprint drift directly.
- State: fixed now

## 2026-08-01 — 214e592 fleet rollout (Short)

- What slowed or confused L? Agent Fleet's legacy LHC apply path still expects the older `VERSION` plus `src/global`/`src/project` layout, so the current 23-file LHC release required a one-off rollback-safe installer.
- Which instruction should change? `none` — the current outcome-first and shared-worktree gates correctly forced commit-object packaging, exact target preview, and a physical harness canary.
- Which skill, MCP, or tool is missing? Proposed: a generic Fleet versioned-directory rollout action with per-host target overrides, marker-only router updates, immutable digest verification, and rollback receipts.
- What operation or error repeated? Four hosts repeated the same preview/apply/verify transport; guard by making that exact matrix an idempotent Fleet action instead of another product-specific endpoint.
- State: Proposed
