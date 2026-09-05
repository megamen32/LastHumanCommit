# Authoring agent instructions

`AGENTS.md` and `CLAUDE.md` are byte-identical marker-delimited routers.
`Lead.md` owns business routing. Overseer is the supreme route controller,
Tester is the mandatory real-surface final gate, and Reviewer reviews a coherent
Full diff or is otherwise risk-triggered. Adviser is optional independent
reasoning; Critic is its compatibility alias, not another gate.

## Non-negotiable ordering

1. Latest user outcome and accepted MVP Definition of Done.
2. Actual production consumer path.
3. Shortest real business canary and cheapest sufficient proof.
4. Least-cost execution: direct Lead or delegated Worker.
5. Earliest safe canary.
6. Only observed blocker fixes and proportional direct-regression checks.
7. Full technical review and fresh independent real-use Tester, repair and
   retest; additional governance/hardening only when expected value exceeds cost.

Preserve the initial independent Overseer and Full acceptance gates. Do not add
card transitions, fixed plan counts, timers, test styles or evidence formats
that do not improve the accepted result. Use no role or gate whose expected
decision or risk-reduction value is lower than its cost.

## Role semantics

- Lead may research and implement directly when delegation costs more than the
  next proof.
- Every implementation starts from a three-line minimal path: result, shortest
  real canary, smallest YAGNI vertical slice, discard list.
- Worker receives a coherent outcome lane and an expected total range that may
  exceed 20 minutes.
- Every 20 active minutes is a reporting checkpoint. Lead continues,
  redirects/resumes the same Worker, or consults Overseer when useful.
- At every context-dependent decision boundary, Worker asks Lead through a
  proven non-blocking parent transport, supplies recommendation/default and
  parallel-safe work, and blocks only the divergent action.
- Every declared work cycle has an immutable minimum/maximum estimate. The
  business time guard produces one report per crossed wall-clock hour and one
  original-maximum overrun diagnostic.
- Use a real wait/join mechanism for required children; never finish merely
  because one wait returned no terminal result.
- Overseer runs initially before implementation, at every crossed wall-clock hour, at overruns, and before the
  Full final; its mandate is cutting security theater, secret ceremonies, and
  process work without a tangible result.
- Tester is the mandatory real-surface final gate for user-facing results; test
  files never substitute.
- Full requires coherent technical review then a fresh independent Tester.
  Outside Full, Reviewer is optional and strictly risk-triggered; never per-wave.
- One real-use Tester is enough unless independent/blind coverage has concrete
  additional value.
- Full may contain however many material options actually exist.
- Load skills on demand from `src/common/skills/README.md`. Strong Lead decisions
  precede bounded model-assigned executor work; verify dependency joins.
- Council challenges the final synthesis. Focus groups repair/retest observed
  obstacles. Workflow improvements require verified retrieval and later reuse.

## State and evidence

One compact current task record is preferred when it pays for recovery,
coordination, or audit. Durable research/result files are cost-triggered; no
elapsed-time threshold mandates files or commits. Do not duplicate task,
handoff, report, and evidence content.

Match proof to claim. Source, tests, deployment, and real-business canary are
reported separately. An accepted MVP is not silently upgraded to strict
admission, perfect atomicity, broad hardening, portability, or visual polish.

## Harness extensions and plugin delivery

For every future harness integration or change, package reusable behavior using
[Agent Plugins](https://agent-plugins.org/specification/): root `plugin.json`,
`skills/`, and optional `mcp.json`. Keep native hooks and other client-specific
behavior in supported client extensions; do not assume identical capabilities.
LHC's canonical package is `plugins/last-human-commit`, generated from source.
Install and update the versioned package through the harness's native plugin
marketplace/manager. Never use individual skill copies, installed-source edits,
or Fleet file rollout as the normal delivery route. If a loader lacks support,
report the concrete limitation and obtain an explicitly selected compatibility
route; do not silently fall back to copying files. Automatic updates depend on
the client and its configuration. Prove the installed loader discovers and uses
the expected package version before claiming harness delivery. `lhc-rollout` is
reserved for explicitly selected legacy recovery, including rollback.

## Workspace and adapters

Keep simple work in the primary checkout; Lead may allocate independent parallel
writes through the canonical worktree tool. Every harness uses the same
`lhc/<task-slug>` and primary `.worktrees/<task-slug>` assignment. Warn on
auxiliary/detached/non-default state and preserve foreign changes. Adapter syntax remains under `adapters/`; portable
behavior remains in `src/common/`. Secrets are read from an environment
variable, `.env`, or a file in one step; secret-handoff infrastructure is
forbidden.

At cycle start retrieve current inputs and relevant verified product/LHC learning
from existing indexes. Architecture work uses `architecture-design`: probe risks,
test early integration, challenge the synthesis, then simplify and dispatch.
Both product repairs and LHC method improvements need their own evidence and
applicable reuse; a retrospective entry alone does not close either loop.

When changing instructions, update the owning source and semantic validators,
then regenerate the canonical plugin package and its native metadata. Require ordering and forbidden old behavior, not mere
phrase presence. Run `git diff --check`, the business-first regression, and
`python3 tests/validate.py`.
