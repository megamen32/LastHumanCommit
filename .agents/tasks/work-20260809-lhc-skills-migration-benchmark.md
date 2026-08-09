# LHC features-to-skills migration and matched benchmark

Status: in progress

Original user request: Зафиксировать текущий LHC как L0, затем превратить его процедурные features в skills, получить L1 и сравнить обе версии на одинаковых product-outcome задачах.

Objective: Extract reusable LHC procedures into подключаемые skills without weakening the role/capability boundary, then measure whether the resulting L1 improves or harms real task outcomes compared with frozen L0.

Business canary: The same difficult product task, run against clean L0 and L1 snapshots under the same Codex/Docker/model configuration, produces a verified product result and complete redacted transcript; quality, effective cost, and wall-clock are recorded separately.

Confirmed scope:

- L0: LastHumanCommit `main` at `44da5d9` / tag `lhc-l0-20260809`.
- Fixed model stack for both arms: smart Terra -> Luna Lead -> GPT-5.4 Mini Worker.
- Candidate procedural skills: `planning`, `bugfix-tdd`, `feature-implementation`, `real-use-testing`, `business-delivery`, and `release` only where the existing LHC procedure justifies it.
- Preserve roles (`Lead`, `Worker`, `Reviewer`, `Tester`, `Adviser`, `Overseer`, `Critic`) and harness capabilities (`AskHuman`, `AskSecret`, `notify`, `resume`); roles select skills, capabilities remain harness-owned.
- Product-outcome benchmark tasks with deterministic acceptance, not the old workflow-guard score as the headline.
- Full transcripts, redaction, per-cell effective cost, per-cell wall-clock, and separate quality/economics/time reports.

Explicit exclusions:

- Do not treat ChatGPT `compare/unified-corrected-archive` / Work3 as an already completed skills migration; it is source material only.
- Do not change Hermes/OpenCode/Codex runtime source or deploy Fleet while building L1.
- Do not use host-side harness execution for the published campaign; use pinned Docker.
- Do not run a cell after cumulative effective spend exceeds `$5.00` without explicit user approval.
- Do not collapse quality, price, and time into one acceptance score.

Cycle: Full
Harness: codex
PID:
Agent session: 019fc8be-7855-7481-bd8d-03dacc4fbdcc
PID status: alive
Last PID signal (UTC+3): 2026-08-09
Last task-file transition (UTC+3): work
Current stage: baseline and migration research
Started at (UTC+3): 2026-08-09
Initial estimate (minimum / likely / maximum active minutes): 60 / 180 / 360
Stop when: L0 is frozen, L1 is an actual validated skills snapshot, and matched product-outcome evidence exists or a concrete external blocker is recorded.
Budget stop: after every completed cell, calculate cumulative effective cost; if it exceeds `$5.00`, stop before the next cell and wait for the user.

## Parallel-work graph

- Lane A — Worker: inventory current procedures and propose the minimal skill boundaries; read-only source audit.
- Lane B — Worker: inspect harness skill packaging/materialization and benchmark injection seams; read-only.
- Lane C — Worker: build the initial skill package in disjoint `skills/` paths after the boundaries are confirmed.
- Join 1: Lead integrates the canonical skill names and role-selection contract.
- Join 2: Reviewer independently reviews the coherent L1 diff.
- Join 3: Tester runs the final only-new product-surface canary for the L1 package.
- Benchmark cells remain sequential at the budget gate; no parallel paid cells.

## Child contract

Every child receives only `<Role> <absolute task-file-path>`, reads the named role file and this task file, appends detailed evidence here, and returns L only a TL;DR. Children do not create task files or edit outside their assigned paths.

## Acceptance evidence

- `skills/*/SKILL.md` has valid frontmatter, concise trigger descriptions, and no duplicated role/capability ownership.
- L1 role prompts explicitly select the new skills or otherwise prove how the harness loads them.
- L0 and L1 snapshots have immutable commits/hashes and identical benchmark inputs.
- Each completed cell has a non-empty receipt, product acceptance result, effective cost, wall-clock, and redacted transcript.
- Campaign stops at the `$5` cumulative threshold and records the stop reason if reached.

## Resolved contract ambiguity (2026-08-09)

- User decision already recorded in the current conversation: remove the
  separate Explorer role.
- Canonical child flow is one Worker continuing from `mode=research` into
  `mode=implement` when the harness supports resume; otherwise a fresh Worker
  receives the compact research evidence. Reviewer and Tester remain fresh
  independent gates.
- Direct user decision in the conversation: “убираем отдельного Explorer;
  Worker получает research и затем work/implement в той же сессии, когда это
  возможно”. This is the selected L1 contract, not an L inference.

## Lane B Explorer evidence (2026-08-09)

### Finding

The smallest proven integration seam is a versioned Fleet package whose
`skills/<name>/SKILL.md` is the canonical payload, rendered into a Codex plugin
directory. The package is immutable and digest-addressed; the benchmark should
materialize that exact package into isolated L0/L1 snapshots and record the
package/revision digest alongside each cell. No repository evidence proves a
native Codex profile loader or benchmark runner, so those claims remain
unsupported.

### Exact source paths and evidence

- `LastHumanCommit/adapters/codex/adapter.yaml:1-14` defines Codex as an
  external adapter, with `role_source: ../../src/common/agents`, optional
  instructions, a subagent template, and `delivery:
  configured-profile-or-fallback-file`; native profile, fresh-child context,
  model override, and resume are explicitly `unproven`.
- `LastHumanCommit/adapters/codex/instructions.md:3-10` says configured
  profiles may embed the complete role prompt; otherwise use file fallback.
  Before each child call the adapter loads
  `templates/subagent.md`. This is the only Codex-side loading contract found;
  it does not mention a skills directory or benchmark materialization.
- `LastHumanCommit/adapters/manifest.yaml:1-17` makes
  `src/common/agents`, profiles, protocols, and capability contracts the LHC
  core sources and lists adapters separately. `LastHumanCommit/adapters/README.md:6-27`
  assigns roles/protocols/capabilities to core and delivery syntax/profile
  frontmatter/context/model/resume to adapters; it prohibits claiming
  unproven behavior without a live child event.
- `agent-harness-fleet/src/harness_fleet/compiler.py:24-60` is the universal
  package IR. It preserves manifest, skills, agents, hooks, instructions,
  models, MCP, and explicit `unsupported` records; model secrets are removed
  at `:19-21`.
- `agent-harness-fleet/src/harness_fleet/adapters/codex.py:20-72` renders the
  IR to `plugin.json`, `skills/<name>/SKILL.md`, `mcp.json`, agent/hook/
  instruction targets, warnings, and model runtime bindings. The Codex
  filesystem adapter declares `.codex` and `.config/codex` candidate roots and
  skills/plugins support at `:103-117`.
- `agent-harness-fleet/src/harness_fleet/package_model.py:40-90` validates
  `plugin.json` and `mcp.json`, requires package name/version/schema, requires
  directory version/name agreement, enumerates skills, and computes a SHA-256
  package digest. Skill traversal and symlink checks are at `:148-167`; digest
  calculation is at `:137-145`.
- `agent-harness-fleet/src/harness_fleet/registry.py:12-43` provides the
  canonical immutable registry seam: `publish(name, version, files)` stages,
  validates, and refuses an existing package version. This is suitable for an
  L1 package snapshot but is a library seam, not proof of a benchmark campaign.
- `agent-harness-fleet/catalog/skills/README.md:1-8` identifies the versioned
  `catalog/skills` directory as the shared source of truth and requires Git
  review before rollout. `catalog/skills/lhc-rollout/SKILL.md:45-52` says the
  skill remains in Fleet's catalog and is distributed by generic `skill-sync`,
  with no LHC-specific endpoint or manual cross-harness copies.
- `agent-harness-fleet/src/harness_fleet/canonical_store.py:27-75` provides
  host-local canonical storage under `~/.agent-harness-sync/canonical`, safe
  relative resource paths, content observation, and backup-before-replace.
  `agent-harness-fleet/src/harness_fleet/sync_engine.py:42-125` compares
  canonical and harness hashes/mtimes and applies a `ResourceSnapshot` only
  when the canonical copy is newer, recording sync operations and backup/error
  status. This is a materialization mechanism, but it is operational sync, not
  a frozen benchmark snapshot creator.
- `agent-harness-fleet/docs/architecture.md:3-29` states the catalog is the
  versioned source of truth, immutable revisions go to staged host cache, and
  SQLite is metadata/audit only—not a second skills source. Safety gates at
  `:57-77` require exact Git revision, backup, confirmation, and verification
  for real deployment; therefore no deployment is needed for the L0/L1 local
  benchmark materialization.

### Minimal L0/L1 benchmark materialization

1. Freeze L0 as the already named `LastHumanCommit` commit/tag and record its
   commit hash plus a deterministic tree digest of the role/protocol/adapter
   inputs used by the harness.
2. Build L1 as a new immutable Fleet package version containing only the
   reviewed canonical skill directories plus the adapter/role-selection
   instructions needed by the cell. Validate with `PackageModel.read`; record
   `PackageModel.digest` and the package version.
3. For each arm, create a clean isolated Docker workspace from the same base
   image/model configuration and materialize only the selected arm's package
   and role files. Keep benchmark task inputs byte-identical; do not use
   host-side execution or Fleet apply for the campaign.
4. Before paid execution, emit a manifest containing arm (`L0`/`L1`), source
   commit, package version/digest (null for L0 if no package), image digest,
   model stack, task-input digest, and expected acceptance checks. After each
   cell retain a redacted transcript, non-empty receipt, product acceptance
   result, effective cost, and wall-clock. Stop before the next cell when the
   cumulative effective spend crosses `$5.00`.

### Checked and excluded

Checked the LHC Codex adapter, adapter manifest/readme, Fleet compiler,
Codex renderer, package model/registry, catalog skill contract, canonical
store/sync engine, and Fleet architecture. No benchmark Dockerfile/compose,
L0/L1 snapshot builder, transcript redactor, receipt schema, or paid-cell
runner was found in these assigned paths. The existing `graphify` token
reduction benchmark is unrelated and must not be reused as the product-outcome
benchmark. No source, deployment, or paid call was performed.

### Bounded recommendation

Use Fleet's immutable `registry.publish` + `PackageModel.read` digest as the
canonical package seam, and Codex's `adapters/codex.py:render` output as the
Codex representation (`plugin.json` plus `skills/*/SKILL.md`). Add a separate,
benchmark-only Docker snapshot/materialization harness that consumes the
recorded L0/L1 manifest; do not infer it from the production `sync_engine` or
from unproven Codex profile support. The next highest-value probe is a
read-only fixture test proving that one canonical `skills/<name>/SKILL.md`
renders, validates, and yields the same digest when reloaded in an isolated
Codex package snapshot.

## Lane A evidence — current procedure inventory (2026-08-09)

Read-only audit scope: the named task file; current role prompts under
`/home/roomhacker/.local/share/last-human-commit/current/common/agents/`;
the current planning profile and protocols; and repository templates/docs
listed below. No source was changed and no paid call was made.

### Minimal procedure-to-skill map

| Candidate skill | Existing source of truth / exact lines | Role ownership and boundary |
|---|---|---|
| `planning` | `common/agents/Lead.md:8-21` (task record, language, estimates), `Lead.md:110-137` (Full cycle, three plans, preview and approvals), `Lead.md:183-188` (Planning profile); `common/profiles/Planning.md:1-83`; `templates/FULL_CYCLE.md:1-91` | Lead owns outcome, plan menu, selection and technical preview. Adviser may advise (`Adviser.md:1-9`) but does not select. Overseer audits route only (`Overseer.md:1-26`). Skill must not own harness capabilities or human decisions. |
| `bugfix-tdd` | `common/agents/Lead.md:139-143`; `common/agents/Worker.md:24-30`; `docs/agent-authoring.md:14-16` | Worker owns the bounded bugfix slice and must produce a focused red regression/black-box canary before repair, then green proof. Lead owns scope and stop/rethink. This is behavior-fix procedure, not a general test skill. |
| `feature-implementation` | `common/agents/Worker.md:18-35` (bounded slice, scope checks, assigned paths and evidence); `templates/FULL_CYCLE.md:93-111` (vertical delivery waves and joins); `docs/agent-authoring.md:14-16` | Worker implements only assigned paths/slice. Lead sequences and integrates; Reviewer independently reviews coherent task-owned diff (`Reviewer.md:1-30`). Do not move architecture, role routing, or capability ownership into this skill. |
| `real-use-testing` | `common/agents/Tester.md:1-16` (final Full gate and `only-new`), `Tester.md:18-52` (surface selection, fresh-user workflow and evidence), `Tester.md:57-66` (black-box boundary); `templates/FULL_CYCLE.md:108-109` | Fresh Tester owns black-box real-user verification after implementation, focused checks, Reviewer and Critic. It may return `PASS`, `CHANGES_REQUIRED`, or `STOP_MISSING_REAL_SURFACE`; it does not inspect source, run synthetic checks, or implement. |
| `business-delivery` | `common/agents/Lead.md:1-4`, `Lead.md:22-34` (business canary and scope gates), `Lead.md:136-155` (complete outcome, review, Tester, commit and handoff); `templates/FULL_CYCLE.md:93-122`; `templates/RELEASE_HANDOFF.md:1-65` | Lead owns business result, integration, proof, commit and final answer. Reviewer checks diff; Critic independently gates release/irreversible action (`Critic.md:1-10`); Tester is final product gate. Skill must preserve explicit human approval boundaries. |
| `release` | `common/agents/Lead.md:144-155`, `Lead.md:191-201`; `templates/FULL_CYCLE.md:112-122`; `templates/RELEASE_HANDOFF.md:1-65` | Lead owns release action and handoff state. Critic gates release; `RELEASE_HANDOFF.md:15-18,41-58` requires explicit `да` for deploy and states wake/timer cannot authorize it. Tags are explicit release-process/user decisions only; no deployment mechanism is invented here. |

### Cross-cutting ownership facts

- Portable procedure text belongs in common role/profile/protocol or skill
  content; adapter syntax remains under `adapters/`, per
  `docs/agent-authoring.md:43-54`.
- `AskHuman` and `AskSecret` are harness capabilities, not skill behavior:
  `docs/human-request-capabilities.md:12-18,23-38` and
  `common/capabilities/human.ask_user.v1.yaml:1-11`,
  `human.ask_secret.v1.yaml:1-13`.
- Historical audit note (RESOLVED/SUPERSEDED): an earlier working snapshot
  described an Explorer-versus-Worker contradiction. The selected canonical
  contract is now Worker research→implement; no separate Explorer role is
  part of L1.

### Bounded recommendation

Create only the six candidate skills named by the task, extracting reusable
procedure text from the mapped sources while leaving role prompts as the
authority for ownership and leaving capabilities/adapters in their current
owners. Preserve the current sequence: Lead planning and scope -> Worker
bugfix/feature slice -> Reviewer/Critic gates -> fresh Tester real-use gate ->
Lead handoff/release. Before implementation, use the already-selected
Worker-mode contract; no broader capability or runtime redesign is justified
by this audit.

## Overseer audit (2026-08-09)

Verdict: ASK_USER.

Historical business delta (RESOLVED): Lane A identified an ownership
contradiction in the earlier snapshot; the human selected Worker research mode
and the active L1 role boundary now preserves it.

Avoidable spend: Building, reviewing, or running paid benchmark cells before
this selection risks benchmarking an invalid L1 and consuming the fixed $5.00
campaign budget without advancing the product-outcome canary.

Minimum next action (completed): use Worker research→implement and constrain
skills extraction to that selected contract.

Eligibility receipt: The task contains a material trigger but no prior
Overseer audit timestamp or attested elapsed-time source. Under
`common/agents/Overseer.md`, the required 30-minute eligibility interval
cannot be verified; this audit is therefore limited to identifying the missing
essential decision and does not authorize continuation.

## Overseer audit (2026-08-09T12:13:04Z)

Verdict: ASK_USER.

Historical business delta (RESOLVED/SUPERSEDED): the Explorer-versus-Worker-mode
choice was made in favour of Worker research→implement before implementation.

Avoidable spend (historical): proceeding before that selection would have risked
invalid L1 evidence; the selection is now recorded and implementation proceeded.

## Tester pass attempt (2026-08-09)

Surface selected: none.

Exact journey attempted: read the task scope and checked whether the benchmark had reached a final product-surface gate suitable for an `only-new` black-box canary.

Observed result: no real-use surface is available yet for testing. The task is still in baseline/migration research, and the contract selection needed to make L1 testable is still unresolved in the task history. Per Tester contract, I did not substitute shell checks, source inspection, or synthetic validation for a real-user pass.

Verdict: `STOP_MISSING_REAL_SURFACE`.

Smallest in-scope repair: finish the canonical L1 contract selection and produce a concrete benchmarked product surface, then rerun Tester as the final independent gate with a real black-box journey.

## Tester pass (2026-08-09)

Verdict: STOP_MISSING_REAL_SURFACE

Selected mode: only-new

Observed state: the task is still at baseline/migration research and does not yet expose a finished L1 package or a user-facing product surface that can be exercised black-box. The task file itself records an unresolved Explorer-versus-Worker-mode contract selection, so there is no validated L1 target to test without first returning to implementation and review.

Journey attempted: task-file read only; no implementation, no browser/app/device/CLI product surface was available to a real-user tester.

Result: I did not run a surface canary, because doing so would have meant simulating success or inspecting implementation context, both of which are outside Tester scope.

Smallest in-scope repair: complete the contract selection and L1 packaging work, then hand me a real user-facing surface for the agreed benchmark task so I can run the only-new black-box pass.

## Implementation evidence (2026-08-09)

Scope kept to `agent-workflow-benchmark` only; no LHC source, runtime source, deploy, or paid-call path was touched.

Changed paths:

- `agent_workflow_benchmark/runner.py`
- `agent_workflow_benchmark/snapshot.py`
- `tests/test_runner.py`

What changed:

- Added immutable per-cell snapshot materialization in the runner with these recorded fields: arm id, source commit, skill digest, task digest, Docker image digest, fixed model stack, per-cell receipt payload, transcript archive metadata, manifest hash, and cumulative effective cost.
- Added a budget-stop gate that halts before the next cell once cumulative effective cost is greater than `$5.00` by default, with a manifest override field `campaign.budget_stop_effective_cost_usd`.
- Wrote snapshot JSON to each run directory and added summary fields for cumulative cost and stop status.
- Added fixture tests proving L0/L1 snapshot digests differ and proving the budget gate stops after the threshold is crossed.

Verification:

- `PYTHONPATH=. pytest -q tests/test_runner.py`
- Result: `6 passed in 0.08s`

Notes:

- Docker pinning remains enforced by the existing runner preflight.
- No paid calls were run.
- The implementation records the per-cell snapshot and transcript archive metadata, but it does not materialize a new benchmark Docker image or alter the underlying LHC role/capability source.

## Lane A implementation evidence (2026-08-09)

Implemented only the new skill layer under `LastHumanCommit/skills/` and did not edit any existing LHC source, runtime code, benchmark files, or deployment assets.

### Created files

- `LastHumanCommit/skills/planning/SKILL.md`
- `LastHumanCommit/skills/bugfix-tdd/SKILL.md`
- `LastHumanCommit/skills/feature-implementation/SKILL.md`
- `LastHumanCommit/skills/real-use-testing/SKILL.md`
- `LastHumanCommit/skills/business-delivery/SKILL.md`
- `LastHumanCommit/skills/release/SKILL.md`

### Evidence

- Each file has valid YAML frontmatter with lowercase-hyphenated `name` and a concise `description`.
- Each body is actionable and scoped to the corresponding reusable procedure.
- Role ownership remains intact: planning stays Lead-owned, bugfix/feature procedures stay Worker-owned, real-use testing stays Tester-owned, delivery/release stay Lead-owned.
- Harness capabilities and runtime/deployment behavior were not moved into any skill.
- No README or extra docs were created.

### Verification

- Inspected the generated SKILL.md headers and procedure bodies directly after creation.
- Confirmed the target directory now contains exactly the six requested skill folders.

### Remaining risk

- The broader L1 role-contract ambiguity noted in the task remains external to this file set; this pass only extracted the requested skills and preserved the boundary in the skill text.

Minimum next action: Obtain one explicit L1 selection: retain the installed Explorer role, or replace it with the documented Worker-mode flow; then continue only within that contract.

Direct user question: Which contract should L1 use — retain the installed Explorer role, or remove Explorer and use the documented Worker `mode=research` -> `mode=implement` flow?

Eligibility receipt: A prior Overseer audit is present, but its timestamp and an attested elapsed-time source are absent from this task file. The mandatory 30-minute interval therefore cannot be verified; no implementation, benchmark cell, deployment, or further research was authorized.

## Full plans (2026-08-09)

### 1. Максимально идеальный

Создать полноценный канонический skill registry для LHC: шесть процедурных skills
в репозитории LHC, explicit role-to-skill selection, Fleet IR/registry package,
Codex/OpenCode/Hermes/Claude Code/ZCode adapters, compatibility and unsupported
records, immutable L0/L1 package digests, benchmark-only Docker snapshot builder,
product-outcome pack, full redacted transcripts, and publication-ready result
artifacts. Preserve capabilities and roles as separate contracts and add
cross-harness validation plus independent Reviewer/Tester gates.

Execution graph: procedure inventory -> canonical skills -> Fleet package/IR ->
adapter renderers -> snapshot builder -> benchmark pack -> review -> Tester ->
matched campaign. Estimate: 180-360 active minutes. Omits deployment and live
Fleet rollout until separately authorized.

### 2. Нормальный

Create the six canonical LHC skills and refactor the common Lead/Worker/Tester
selection points to use them while keeping existing roles, capabilities, and
adapter files as the ownership boundary. Use Fleet's existing immutable package
seam and Codex renderer for the L1 snapshot; record unsupported cross-harness
materialization instead of inventing it. Build only the benchmark-specific
Docker snapshot/manifest needed for Codex product-outcome comparison under the
fixed Terra -> Luna -> Mini stack, with redacted transcripts and the `$5` stop.
Run existing static validation, independent review, and final only-new Tester.

Execution graph: canonical skills -> role selection -> Codex package snapshot ->
product task mapping -> review -> Tester -> sequential L0/L1 cells. Estimate:
120-240 active minutes. Omits cross-harness compiler changes and deployment.

### 3. YAGNI 80/20 — полный результат сейчас

Deliver a complete usable Codex L1 with the smallest migration: six concise
`skills/<name>/SKILL.md` files containing only the reusable procedure, a compact
role-to-skill selection contract in Lead/Worker/Tester, and a benchmark-only
Docker materializer that produces immutable L0/L1 manifests and digests. Reuse
Fleet's existing registry/package model rather than changing Fleet, preserve
all current capabilities and role gates, and mark other harnesses as
adapter-dependent. Run the same product-outcome cells sequentially, record
quality/price/time/transcripts, and stop at cumulative `$5`.

Execution graph: six skills + selection contract in parallel disjoint files ->
Codex materializer -> static validation -> Reviewer -> Tester -> L0 then L1
campaign. Estimate: 60-140 active minutes. Omits cross-harness rendering,
registry publication, and deployment, but does not omit the requested L1 or its
comparison evidence.

Recommendation: YAGNI 80/20 — полный результат сейчас.
Human plan selection (verbatim):

## Selected plan and full technical preview (2026-08-09)

Human plan selection: `3`.

### Call-stack tree

```text
L
├─ canonical skills/ (six procedure skills)
├─ role selectors
│  ├─ Lead -> planning, business-delivery, release
│  ├─ Worker -> bugfix-tdd, feature-implementation
│  └─ Tester -> real-use-testing
├─ Codex snapshot materializer
│  ├─ L0 = frozen core tree, no skills package
│  └─ L1 = skills package + role selectors + same core baseline
└─ sequential product-outcome campaign
   ├─ after each cell: receipt -> acceptance -> cost/time -> transcript
   └─ cumulative effective cost > $5 -> stop before next cell
```

### File-tree diff

LHC additions:

```text
skills/
├─ planning/SKILL.md
├─ bugfix-tdd/SKILL.md
├─ feature-implementation/SKILL.md
├─ real-use-testing/SKILL.md
├─ business-delivery/SKILL.md
└─ release/SKILL.md
```

LHC modifications are limited to the role-selection seams in
`src/common/agents/Lead.md`, `Worker.md`, and `Tester.md`, plus the canonical
skill list in `adapters/manifest.yaml`. Existing role ownership, capability
contracts, adapter transport, and Fleet production files remain unchanged.

Benchmark additions are limited to a snapshot materializer, L0/L1 manifest,
product-outcome scenario mapping, per-cell budget gate, and result/transcript
artifacts in the public benchmark repository. No runtime deployment is part of
this plan.

### Key contracts

```text
SkillManifest:
  name: lowercase-hyphenated
  source: skills/<name>/SKILL.md
  owner: Lead | Worker | Tester
  capabilities: references only; never owned by the skill

BenchmarkCell:
  arm: L0 | L1
  source_commit: immutable git revision
  model_stack: Terra -> Luna Lead -> GPT-5.4 Mini Worker
  image_digest: immutable Docker digest
  task_digest: identical across arms
  effective_cost_usd: nullable until receipt proves it
  wall_clock_seconds: measured
  transcript_archive: redacted path/hash
```

### Pseudocode

```text
for cell in randomized([L0, L1] × product_tasks):
    snapshot = materialize(cell.source_commit, cell.arm)
    receipt = docker_run(snapshot, fixed_model_stack, task)
    verdict = deterministic_product_acceptance(receipt.workspace)
    archive(redact(receipt.transcript), receipt, verdict)
    totals.cost += receipt.effective_cost_usd
    record_quality_cost_time(cell, verdict, receipt, totals)
    if totals.cost > 5.00:
        stop_before_next_cell("budget gate")
```

### Migration description

Copy only reusable procedural instructions into the six skills. Keep role
prompts as ownership/orchestration contracts. Keep AskHuman, AskSecret/SSS,
notify, resume, model routing, and adapter syntax as capabilities or harness
bindings. L0 remains byte-for-byte frozen; L1 is a separate immutable commit.

### Exact business canary

At least one complex bugfix/feature product task must be completed by both
arms from identical fixture bytes, with deterministic acceptance proving the
user-visible result. A green unit test without the product result is
insufficient.

### Consequential authorization boundaries

No deployment, restart, runtime-source edit, credential change, external
message, or destructive action. Paid model calls begin only after the materializer
and receipt checks pass. After every cell, cumulative effective cost is checked;
above `$5` blocks the next cell pending the user.

### Execution graph

```text
Wave 1 (parallel, disjoint):
  A: six canonical SKILL.md files in LHC/skills/
  B: benchmark snapshot/materializer + budget gate
        ↓ join: L validates manifests and role selectors
Wave 2 (sequential): static checks -> Reviewer -> fresh Tester
        ↓
Wave 3: L0 product cells, cost gate after each
        ↓ if budget remains
Wave 4: L1 product cells, cost gate after each
        ↓
result report + one combined redacted transcript archive
```

Second explicit approval (verbatim):

делай

## Execution start (2026-08-09)

Implementation of selected plan 3 is authorized. No paid benchmark cell is
authorized until the L1 snapshot, receipt schema, redaction, and `$5` budget
gate pass local validation.

## Overseer eligibility check (2026-08-09T12:15:27Z)

No new audit issued. The last recorded Overseer audit is timestamped
`2026-08-09T12:13:04Z`; only 2m23s had elapsed at this check, below the
mandatory 30-minute interval. The resolved Explorer removal decision is
already recorded, but it does not waive the eligibility gate. No continuation,
benchmark cell, implementation, deployment, or additional research is
authorized by this check.

## Worker evidence (2026-08-09)

- Implemented benchmark-only immutable per-cell snapshot materialization in
  `agent_workflow_benchmark/snapshot.py` and wired it into
  `agent_workflow_benchmark/runner.py`.
- Snapshot records now capture: source commit, arm id, skill digest, task
  digest, Docker image digest, model stack, receipt payload, redacted
  transcript archive reference, and cumulative effective-cost budget state.
- Added a budget stop gate that marks the run as stopped once cumulative
  effective cost exceeds `$5.00`, before the next cell is launched.
- Added local fixture tests proving L0/L1 snapshot digests differ and the
  budget gate stops after an over-budget cell.
- Verification: `python3 -m pytest -q /home/roomhacker/agents-projects/agent-workflow-benchmark/tests/test_runner.py`
  → `6 passed in 0.10s`.
- No paid calls, deployments, runtime-source edits, or LHC source edits were
  performed.

## LHC role-to-skill contract update (2026-08-09)

- Updated `src/common/agents/Lead.md` to explicitly select `planning`,
  `business-delivery`, and `release` while preserving the Lead role's scope and
  approval ownership.
- Updated `src/common/agents/Worker.md` to explicitly select
  `bugfix-tdd` and `feature-implementation` while preserving the Worker
  research→implement contract and the existing `mode: research` / `mode:
  implement` split.
- Updated `src/common/agents/Tester.md` to explicitly select
  `real-use-testing` while preserving Tester's fresh real-use gate.
- Updated `adapters/manifest.yaml` with a top-level `canonical_skills` list
  mapping the six canonical skills to their owning roles.
- Preserved `AskHuman`, `AskSecret`, `notify`, and `resume` as harness
  capabilities; no capability ownership was moved into skills.
- No separate Explorer contract was introduced in the touched seams; the
  existing Worker research→implement contract remains intact.
- Static validation:
  - `python - <<'PY' ... yaml.safe_load(...) ... PY`
    → manifest parsed successfully and exposed `canonical_skills`.
  - `git diff -- src/common/agents/Lead.md src/common/agents/Worker.md
    src/common/agents/Tester.md adapters/manifest.yaml`
    → only the intended four files changed.
- Remaining risk: no broader repo-wide validator was run because the requested
  scope was limited to local static validation only.

## Follow-up Lane C validator evidence (2026-08-09)

- Updated `adapters/manifest.yaml` with `core.skills: skills`, retaining the
  six `canonical_skills` name/owner entries.
- Updated `tests/validate.py` with deterministic checks for the exact six
  canonical names, safe `core.skills` path, required `name`/`description`
  frontmatter, manifest owner mapping, skill file existence, and matching
  Lead/Worker/Tester selection text.
- Clean temporary-copy baseline: `PASS: 7 roles, 5 adapters, human gates,
  one-task contract, and workspace policy`.
- Negative checks in isolated temporary copies rejected both a missing skill
  (`FAIL: missing canonical skill: skills/planning/SKILL.md`) and an owner
  mismatch (`FAIL: canonical skill planning owner mismatch: expected Lead, got
  Worker`).
- The shared worktree full validator remains blocked by the unrelated existing
  `.agents/tasks/work-20260809-benchmark-topology-generalization.md` status
  `work`; no foreign task file was changed. No deployment or paid call ran.

## Follow-up Lane B snapshot materializer evidence (2026-08-09)

- Scope stayed inside `agent-workflow-benchmark`; no LHC source, runtime,
  Docker pin, deployment, or paid-call path was changed.
- Added `agent_workflow_benchmark/snapshot.py` with `snapshot-v1` materializer:
  it accepts an L0 source root and optional L1 skills root, copies only
  declared relative files into isolated `source/`, `skills/`, and `task/`
  directories, rejects absolute/`..`/Windows traversal, missing or directory
  inputs, symlinks, duplicates, and non-empty destinations, and computes
  deterministic `source_digest`, `skill_digest`, and `task_digest` from sorted
  relative paths plus file digests.
- Added optional `arm.snapshot` manifest validation and runner integration.
  Each cell receipt now exposes the materialization record and digests; the
  archived campaign manifest exposes one path-free materialization record per
  arm. Existing pinned Docker execution remains unchanged.
- Added fixture tests for exact declared-file copying (including source,
  skills, and task), digest change after input mutation, path traversal
  rejection, L0/L1 snapshot digest difference, receipt exposure, and the
  cumulative effective-cost gate stopping before the next cell.
- Verification: `PYTHONPATH=. pytest -q` in
  `/home/roomhacker/agents-projects/agent-workflow-benchmark` -> `9 passed in
  0.11s`; `git diff --check` passed.
- No harness or paid model call was run for this follow-up; the receipt test
  uses a local fake adapter only. No deploy or Docker pin weakening occurred.

## Product campaign preparation (2026-08-09)

- Replaced the stale campaign configuration that lacked `manifest_version` and
  still compared the rejected MiniMax topology. The planned product campaign
  now declares one stack for both arms: Terra mentor, Luna Lead, and GPT-5.4
  Mini Worker.
- Added a self-contained product-outcome fixture for the unknown-discount bug:
  the acceptance check requires the producer to return a numeric zero, the
  checkout total to remain correct for unknown and known codes, and a runnable
  regression test to exist.
- Reworked the public benchmark README so the result table is the second
  paragraph and quality, effective price, and wall-clock time remain separate.
- Product campaign dry-run passes. The image digest and L1 source revision are
  intentionally still placeholders; no paid cell may start until both are
  frozen and the materializer is wired to the actual workflow package.

## Superseding decision: Explorer removal (2026-08-09)

The earlier Lane A note and the two historical Overseer `ASK_USER` entries
recorded an already-resolved choice. The human selected the documented
Worker-mode model: there is no separate Explorer role. The active L1 contract
is therefore `Worker(mode: research) -> Worker(mode: implement)` when the same
session can continue; Reviewer and Tester remain fresh independent gates.
The historical contradiction is closed and must not block review,
materialization, or the paid benchmark. No `Explorer.md` or Explorer adapter
was added.

## Current Tester surface (2026-08-09)

The L1 user-facing surface for this gate is the repository's documented local
validation/install contract, not the future paid benchmark: from the LHC root,
run `python3 tests/validate.py`, `sh tests/test_task_states.sh`, and the six
skill `quick_validate.py` commands. These are black-box entry points for the
published instruction package; the Tester must use only their exit status and
reported output, not inspect implementation files. The paid product-outcome
cell remains a separate later gate after the L1 source snapshot and Docker
image are frozen.

## Tester gate evidence (2026-08-09)

- Surface attempted: real-user black-box product canary for the migrated L1
  skills package.
- Journey attempted: none, because the task is still in baseline/migration
  research and the task file shows an unresolved Explorer-versus-Worker-mode
  contract conflict plus no validated L1 snapshot to exercise.
- Observed result: no real L1 user surface was available to test, so a
  genuine only-new product-outcome pass could not be performed without
  simulating the result.
- Verdict: `STOP_MISSING_REAL_SURFACE`.
- Smallest in-scope blocker: L must first freeze a validated L1 contract and
  snapshot, then hand Tester the finished user-facing surface for the matched
  product-outcome canary.

## Additional Tester pass (2026-08-09T12:34:00+03:00)

Verdict: `STOP_MISSING_REAL_SURFACE`

Selected mode: `only-new`

Surface selected: none.

Exact journey attempted: fresh black-box read of the task file to determine whether a real user-facing benchmark surface had been handed off for final validation.

Observed result: no usable real-use surface is available yet for Tester. The task is still centered on L1 migration/materialization and does not present a finished surface I can exercise without simulating success or inspecting implementation context.

Smallest in-scope repair: finish L1 freezing/materialization, then provide the concrete benchmark surface so Tester can run the only-new black-box journey.
