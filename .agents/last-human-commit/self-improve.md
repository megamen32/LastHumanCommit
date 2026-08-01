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

## 2026-08-02 — restore README image (Direct)

- What slowed or confused L? Git history contained two removals, but live PushEvent range proof isolated `fc97d68` as the lasting deletion.
- Which instruction should change? `none` — existing memory already says to preserve the README's concise intent and image.
- Which skill, MCP, or tool is missing? `none` — Git history plus GitHub PushEvent data identified the regression.
- What operation or error repeated? The image was removed twice and restored once; guard: review the README's first screen when rewriting it.
- State: fixed now

## 2026-08-02 — independent user gates and task state (Full)

- What slowed or confused L? Overseer and Critic could inherit L's framing, while duplicate kanban state and completed `work-*` files obscured the real project priority.
- Which instruction should change? Fixed now: both gates independently reconstruct user P0 from raw context, bind L, and one `work-*`/`done-*` task file is the only task state.
- Which skill, MCP, or tool is missing? `none` — existing subagents and repository validation cover the contract.
- What operation or error repeated? A full-history subagent fork rejected an explicit `agent_type`; guard: omit `agent_type` when `fork_context: true` inherits the parent type.
- State: fixed now

## 2026-08-02 — harness subagent templates (Short)

- What slowed or confused L? No-history gates lacked parent git provenance, mistook pre-existing `graphify-out/` for scope drift, and initially missed their own Codex calls as live proof.
- Which instruction should change? `none` — the new explicit Task Card and per-harness template contract already carries the needed facts without history forks.
- Which skill, MCP, or tool is missing? `none` — `spawn_agent` accepted `fork_context:false`, Luna, and low reasoning and returned both role reports.
- What operation or error repeated? Two gates made the same provenance/proof mistake; guard by putting pre-task foreign paths and exact spawn parameters in every no-history audit card.
- State: fixed now
