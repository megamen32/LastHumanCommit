# Fleet rollout 567925f

Status: complete
Original user request: roll out the latest Last Human Commit everywhere again
through Fleet and the dedicated rollout skill.
Objective: deploy committed LHC revision `567925f` through the deterministic
Fleet rollout operation to the canonical 100/44/88/Mac topology.
Business canary: Fleet verify reports one matching version and digest on every
manifest target, followed by a physical installed-router or role read.
Confirmed scope: exact skill manifest, preview, authorized apply, verify,
rollback receipts, and one physical harness canary.
Explicit exclusions: no manual SSH replacement for Fleet, no provider/secret/
DB/Grafana checks, no unrelated harness repair, and no `graphify-out/` changes.
Acceptance: every supported manifest target is `verified`; unsupported surfaces
are named explicitly and failures roll back or remain reported.
Initial estimate (optimistic / likely / pessimistic active minutes): 10 / 25 / 45.
Estimate revisions (append-only; trigger and evidence): none.
Cycle: short
Workflow: deterministic preview, exact confirmation apply, independent verify,
physical canary, task evidence, commit.
Current stage: YAGNI

## Work

Current: complete.
Next: none inside confirmed scope.
Blocked by: none.
Evidence: see below.

## Evidence

- Source: committed `567925f89cfde13b795a3b47c2b977ff17ba8e3e`.
- Initial Fleet preview stopped before apply: its 22-file payload omitted
  `adapters/`, so it would not deploy the new harness templates.
- Fleet fix: commit `7f97fba` adds `adapters -> adapters` to the canonical skill
  manifest and a red/green regression. Rollout tests `10/10`, generic
  skill-sync tests `17/17`, and naming tests `3/3` pass.
- Generic Fleet `skill-sync`: Base digest
  `sha256:3a6f4949156bedfd023d6ac54af4168a4e7cee318cd8c09caedfad19e2223278`;
  apply succeeded on 100/44/88/Mac with per-host backup roots; repeat preview is
  all `noop` across every discovered OpenCode, Codex, Claude Code, ZCode,
  Hermes, and OpenClaw copy.
- Exact LHC preview/apply/verify: version `567925f`, 42 files, digest
  `sha256:85ec617d31a8e195ffa350a0827afdbdbec88f80b8f4fa1ebd9c99d074e5cb71`.
- Host 100: verified; 7 routers, 4 projects, 1 Hermes copy; rollback receipt
  `/home/roomhacker/.local/share/last-human-commit/rollbacks/567925f-lhc-rollout`.
- Host 44: verified; 3 routers, 3 projects; same rollback receipt path.
- Host 88: verified; 3 routers, 1 project, 1 Hermes copy; same rollback receipt
  path.
- Mac: verified; 5 routers, 2 projects, 1 Hermes copy; rollback receipt
  `/Users/user/.local/share/last-human-commit/rollbacks/567925f-lhc-rollout`.
- Physical canary passed on all four hosts: `current -> versions/567925f`, Codex
  template contains `fork_context: false` and cheapest-working-class rule, and
  the installed Codex router resolves `current/common/agents/Lead.md`.

## Independent gates

- Overseer: `APPROVE`. P0 factually done on all four targets; no deployment
  blocker. Non-blocking note: Fleet fix `7f97fba` is not pushed.
- Critic initial: `RETHINK` pending original generic skill-sync JSON/API proof.
- Critic final: `PASS` after read-only verification of preview/apply/repeat
  preview JSON and Fleet SQLite audit records. Confirmed 27/27 skill copies
  `noop` after apply: 100=10, 44=4, 88=5, Mac=8.
- Questions for L: none.

## L checkpoint

- Raw `uptime`: `04:03:42 up 1 day, 6:18, 2 users, load average: 35.74, 31.00, 29.88`.
- Current P0: Fleet-wide LHC delivery.
- Business delta: skill and LHC rollouts verified with physical canaries.
- Blocker: none.
- Next action: close and commit this evidence record.

## Result

- Fleet skill sync: `succeeded`, then 27/27 discovered copies `noop`.
- LHC rollout: `verified` on 100/44/88/Mac at version `567925f`, digest
  `sha256:85ec617d31a8e195ffa350a0827afdbdbec88f80b8f4fa1ebd9c99d074e5cb71`.
- Rollback receipts and physical router/template canaries exist on every target.
- Critic: `PASS`; Overseer: `APPROVE`.
- Unresolved inside scope: none.
