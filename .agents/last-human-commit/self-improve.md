# Last Human Commit self-improve log

## 2026-07-31 — 5a172fc (Short)

- What slowed or confused L? Hermes learning was implemented as two bounded paths: post-response background review and explicit `/learn`; a source push also left `current` at `b32ef81`, and OpenCode retained old embedded roles until the active bundle/profile checks ran.
- Which instruction should change? Fixed now: `Lead.md` resolves companion profiles/protocols relative to its own source, and the OpenCode adapter documents that rendered profiles retain that source root.
- Which skill, MCP, or tool is missing? `none` — read-only source access and targeted search were sufficient.
- What operation or error repeated? Two release checks exposed the same gap: source Git state versus active harness state. Guard: after every LHC release, verify `current` and each configured profile, not only `origin/main`.
- State: fixed now

## 2026-08-10 — GitHub marketplace catalog (Full)

- What slowed or confused L? Codex plugin validation exposed missing native `author`/`interface` metadata; my first clean-copy `cp` command flattened directory paths.
- Which instruction should change? `plugin-creator/SKILL.md` — add a cross-format manifest check note for existing packages before marketplace publication. Proposed.
- Which skill, MCP, or tool is missing? none; local validators plus `gh api` supplied the needed evidence.
- What operation or error repeated? 1 clean-copy layout error; guard with explicit destination directories and copy commands.
- State: fixed now

## 2026-08-09 — LHC benchmark topology (Full)

- What slowed or confused L? Quorum receipts exposed the outer Codex model but not native child Worker model IDs; declared Lead→Worker routing was easy to overstate.
- Which instruction should change? Proposed: `adapters/codex/adapter.yaml` and its verification contract should require a machine-readable child model receipt before claiming `model_override: proven`.
- Which skill, MCP, or tool is missing? Proposed: a Codex/Quorum receipt normalizer that records each native child session, role, provider, and model without raw prompt history.
- What operation or error repeated? Two L0 cells needed reruns after invalid `wire_api=chat`; guard by validating harness wire mode before any paid batch.
- State: Proposed

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

## 2026-08-02 — Fleet rollout 567925f (Short)

- What slowed or confused L? The canonical Fleet manifest packaged 22 core/template files but omitted the new `adapters/` tree, so the first preview would have reported success without the requested templates.
- Which instruction should change? Fixed in Fleet commit `7f97fba`: the rollout manifest now packages `adapters -> adapters`, with a regression test.
- Which skill, MCP, or tool is missing? `none` — `$lhc-rollout` plus generic `skill-sync` exposed and repaired the gap.
- What operation or error repeated? One preview was invalidated before apply; guard by asserting required payload roots and file count before accepting every release preview.
- State: fixed now

## 2026-08-10 — governance audits and blind release testing (Short)

- What slowed or confused L? The request combined a TODO record with future runtime behavior; scope was resolved as documentation only, with scheduler/deployment explicitly deferred.
- Which instruction should change? Proposed: `src/common/agents/Lead.md` should state how a user-requested governance TODO is distinguished from activating the runtime workflow.
- Which skill, MCP, or tool is missing? `none` — repository role prompts and `lhc-rollout`/`graphify` guidance were sufficient for this text-only handoff.
- What operation or error repeated? `none` — one task card was created; pre-existing dirty task files and `.serena/`/`plugins/` were preserved.
- State: Proposed

## 2026-08-10 — corrected governance priority (Short)

- What slowed or confused L? The first TODO wording incorrectly made cost/result optimization sound primary instead of making strict invariants an absolute veto.
- Which instruction should change? Proposed: `src/common/agents/Overseer.md` should lead with hard-invariant rejection before any plan comparison.
- Which skill, MCP, or tool is missing? `none` — the task card was corrected directly.
- What operation or error repeated? One scope rewrite was needed after user correction; guard: every plan section now states fail-closed veto before optimization.
- State: fixed now

## 2026-08-10 — adviser and critic role correction (Short)

- What slowed or confused L? The role timing and stance needed another clarification: Adviser is pre-implementation and constructive; Critic is post-decision fresh/no-history and adversarial.
- Which instruction should change? Proposed: `src/common/agents/Adviser.md` and `src/common/agents/Critic.md` should encode these different context and authority boundaries.
- Which skill, MCP, or tool is missing? `none` — the TODO contract was updated directly.
- What operation or error repeated? Two task-card rewrites followed user corrections; guard: keep original request and explicit role matrix together before editing prose.
- State: fixed now

## 2026-08-10 — task lifecycle migration (Short)

- What slowed or confused L? Legacy todo/work cards mixed absent, blank, and renamed lifecycle fields; a reporting regex also initially mishandled optional UTC+3 labels.
- Which instruction should change? Fixed now: `AGENTS.md`/`CLAUDE.md` and the task template require explicit provenance and mtime-as-last-write semantics.
- Which skill, MCP, or tool is missing? `none` — context-mode batch audit plus the dependency-free validator were sufficient.
- What operation or error repeated? Two focused regressions were needed: missing fields, then empty PID; guard: validator checks presence and non-empty values for all todo/work cards.
- State: fixed now

## 2026-08-10 — shared-session abstraction (Short)

- What slowed or confused L? The existing shared-session implementation was outside LHC (`~/.claude/hooks/shared_session_register.sh`), while the requested contract spans hooks, MCP, files, human requests, and persistent Overseer state.
- Which instruction should change? Fixed now: `docs/shared-session-abstraction.md` defines file-first ownership and `src/common/agents/Overseer.md` defines continuation by durable state.
- Which skill, MCP, or tool is missing? Proposed: an attested cross-harness LHC MCP with response-stop human-request integration.
- What operation or error repeated? Existing validator assumptions required fresh Overseer wording after the role correction; guard: validator now checks persistent Overseer plus fresh Critic semantics.
- State: Proposed

## 2026-08-10 — three-minute durable research (Short)

- What slowed or confused L? The abstraction initially retained a 10-minute research threshold, while the user required file persistence from 3 minutes after orientation.
- Which instruction should change? Fixed now: `WORKER_RESEARCH.md`, `Worker.md`, and adapter templates make 3 minutes and file-first detailed findings explicit.
- Which skill, MCP, or tool is missing? Proposed: a runtime response/harness event that can surface the durable research path without injecting the full child transcript.
- What operation or error repeated? none — focused validation stayed green after the threshold update.
- State: fixed now

## 2026-08-10 — separate search/result files and `.at/` (Short)

- What slowed or confused L? The previous abstraction conflated search journal and final result, and the first validation run exposed the intentional `Code.md` SHA pin after adding the `.at/` rule.
- Which instruction should change? Fixed now: `WORKER_RESEARCH.md`, `Code.md`, and shared-session docs distinguish `search.md` from `result.md` and forbid `/tmp`/`.tmpbin` one-off scripts.
- Which skill, MCP, or tool is missing? Proposed: runtime commit enforcement when research crosses 10 active minutes.
- What operation or error repeated? One validator SHA update was required after the scoped Code profile change; guard: keep the digest update in the same reviewed diff.
- State: fixed now

## 2026-08-10 — named ignored search and tracked result trees (Short)

- What slowed or confused L? The prior abstraction used generic `search.md`/`result.md` in one folder and described “ignored” semantically rather than as Git ignore.
- Which instruction should change? Fixed now: shared-session docs and Worker adapters use named files in separate search/results trees, with `.gitignore` covering only search.
- Which skill, MCP, or tool is missing? `none` — `git check-ignore` directly proved the boundary.
- What operation or error repeated? Two validator phrase updates followed the intentional naming correction; guard: validate task-specific filename patterns and physical ignore behavior.
- State: fixed now

## 2026-08-10 — single agent-state root (Short)

- What slowed or confused L? The instructions had introduced a top-level `.at/` alongside `.agents/`, making the documented state model more fragmented than necessary.
- Which instruction should change? Fixed now: routers, Code/Worker rules, and shared-session docs require one `.agents/` root and `.agents/at/` for Agent Tools.
- Which skill, MCP, or tool is missing? `none` — local tree inspection and validator were sufficient.
- What operation or error repeated? One Code SHA update was required after relocating the documented path; guard: keep the digest change with the instruction change.
- State: fixed now

## 2026-08-10 — core specification consistency audit (Short)

- What slowed or confused L? The core spec mixes one task-file ownership with shared-session result/handoff artifacts and mixes read-only research with a later mandatory commit.
- Which instruction should change? Needs human decision: do not edit until the user chooses the intended ownership and commit model.
- Which skill, MCP, or tool is missing? `none` — targeted indexed excerpts were sufficient; plugin directories were excluded.
- What operation or error repeated? none — read-only audit only; no specification source was modified.
- State: needs human decision

## 2026-08-11 — copy-and-commit lifecycle snapshots (Short)

- What slowed or confused L? Existing lifecycle prose required renaming the same task file, conflicting with the requested preserved `todo/work/done` history.
- Which instruction should change? Fixed now: routers, Lead, templates, Test profile, README, and task template define copy+commit snapshots and latest committed state.
- Which skill, MCP, or tool is missing? Proposed: a regression harness that kills a Worker and resumes from committed `work-*` without repeating research.
- What operation or error repeated? Three validator wording mismatches appeared after replacing rename semantics; guard: run the full validator after lifecycle prose changes.
- State: fixed now

## 2026-08-12 — compaction continuity and plugin update (Short)

- Friction: Codex compacted before LHC had a counter; plugin upgrade twice left a stale 0.1.0 hook path, and the first handoff required a task-card.
- Owning correction: fixed now in native compaction hooks with atomic current handoff, bounded count history, and prompt fallback; package bumped to 0.2.1.
- Missing tool: Codex PreCompact cannot inject compaction context directly; SessionStart restore is the supported fallback, while OpenCode injects output.context.
- Repetition/evidence: stale-path error repeated twice; installed Codex/OpenCode prompt-only canaries now pass and five Codex hooks are trusted.
- State: fixed now

## 2026-08-12 — benchmark research routing (Short)

- Friction: three context-mode batches hung on broad multi-repository or scenario scans; exact `rg`/bounded reads were faster and unblocked the Arena run.
- Owning correction: Proposed for `worker-research`: after one repeated context-mode timeout on the same route, cut scope and return to exact `rg`/source reads instead of a third broad batch.
- Missing tool: none; existing `rg`, Graphify fast-path, and context-mode are sufficient when each is used at the right granularity.
- Repetition/evidence: 3 terminated context-mode cells; route change then produced 40/40 terminal benchmark receipts.
- State: Proposed

## 2026-08-26 — LHC v2: restore core vision (Full)

- What slowed or confused L? Agent-era commits built secret-handoff theater (AskSecret/AskHuman HTTP capabilities, plugins, marketplace) against the maintainer contract "No harness hooks, plugins, network fetches", plus Reviewer/Critic/Adviser ceremony, and Overseer was effectively never invoked without a hard start-time anchor.
- Which instruction should change? Fixed now: canon v2 — Secrets are not work (env/.env/file in one step), minimal-path-first, Overseer supreme with mandatory hourly/overrun consults, Tester as mandatory real-surface final gate, SELF_IMPROVE became a bounded patch loop with reviewed commits.
- Which skill, MCP, or tool is missing? none — existing chrome-devtools/browser MCPs cover real-surface testing.
- What operation or error repeated? GPT-era drift into security infrastructure repeated across 77629a5/059bc8d/898c901/64290f2; guard: validate.py forbids AskSecret/SSS, opaque registered-agent, base64 fallback, NoticePlace capability phrases and fails if secret-theater paths reappear.
- State: fixed now

## 2026-08-27 — unified history rule (Short)

- What slowed or confused L? L repeatedly left unpushed commits and untracked dirt, and canon told L to stage only task-owned paths, leaving foreign edits to rot — the opposite of the user's standing expectation.
- Which instruction should change? Fixed now: "Unified history" section in AGENTS.md/Lead.md/SHARED_WORKTREE.md/task template — commit each completed step, absorb reviewed-safe foreign edits and report them, every cycle ends clean; Full cycles end pushed, deployed, real-surface tested. .agents/at/ ignored so "clean" is achievable.
- Which skill, MCP, or tool is missing? none.
- What operation or error repeated? Fragmented end states across cycles (4 unpushed commits, 63 untracked files at rule time); guard: validate.py now forbids "Stage and commit only task-owned paths" and requires the unified-history phrases.
- State: fixed now

## 2026-08-28 — nested time-guard flake (Short)

- What slowed or confused L? tests/validate.py intermittently fails its nested `pytest tests/test_time_guard.py` subprocess (3 occurrences over 2 days) while the same suite always passes standalone and via `pytest -q tests/`.
- Which instruction should change? none yet — not reproducible on demand (3/3 green).
- Which skill, MCP, or tool is missing? none.
- What operation or error repeated? Suspected fcntl lock contention between the nested test run and live time-guard hooks from other harness sessions on `.agents/shared-session/time/`; guard candidate: make time-guard tests use an isolated tmp lock dir.
- State: Proposed

## 2026-08-28 — AskHuman rehabilitation (Short)

- What slowed or confused L? The v2 purge deleted the AskHuman channel along with the confirmation ceremony; the user corrected: AskHuman was an excellent, appropriately-used way to deliver important info to the human. Only forced routine confirmations were the pain.
- Which instruction should change? Fixed now: "AskHuman — the human channel" section in AGENTS.md/Lead.md (important info = yes; routine confirmations = never; secrets = only /secret); lean plugins/ask-human 0.2.0 restored with marketplace entry; /askhuman skill + canonical command; validator forbids ceremony ("confirmation for every") instead of the tool.
- Which skill, MCP, or tool is missing? none — AskHuman/notify MCP already connected.
- What operation or error repeated? Overcorrection pendulum: delete-everything vs keep-everything; guard: validators now name the exact ceremony patterns, not the tools.
- State: fixed now

## 2026-08-28 — endpoint-agnostic MCP (Short)

- What slowed or confused L? The AskHuman/AskSecret plumbing assumed the author's personal endpoints; public consumers need their own, and marketplace installs cannot take parameters (no env-at-install).
- Which instruction should change? Fixed now: endpoints are BYO via LHC_ASKHUMAN_MCP_URL / LHC_ASKSECRET_MCP_URL (+optional ..._MCP_TOKEN) read from env/.env; plugins/ask-human/scripts/setup_mcp.py registers the MCP (codex config.toml, dry-run default, --apply with backup, snippet for others); ask-human marketplace policy AVAILABLE so keeping only one plugin is valid.
- Which skill, MCP, or tool is missing? none.
- What operation or error repeated? 4th nested time-guard flake in validate.py; guard partially applied: nested validators now print full output on failure for one-look diagnosis; root cause (suspected live-hook fcntl contention) still unconfirmed.
- State: fixed now

## 2026-08-28 — universal manifest drift (Short)

- What slowed or confused L? The version bump touched per-harness projections but missed the root universal plugin.json (agent-plugins.org 1.0.0) — the canonical manifest drifted to 0.3.0 vs 1.0.0.
- Which instruction should change? Fixed now: plugin validator checks version parity root + projections; negative test confirms drift detection.
- Which skill, MCP, or tool is missing? none.
- What operation or error repeated? Manual multi-manifest bumps drift; guard: parity check in the plugin validator.
- State: fixed now
