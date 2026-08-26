# Authoring agent instructions

`AGENTS.md` and `CLAUDE.md` are byte-identical marker-delimited routers.
`Lead.md` owns business routing. Overseer is the supreme route controller and
Tester is the mandatory real-surface final gate; no other gate roles exist.

## Non-negotiable ordering

1. Latest user outcome and accepted MVP Definition of Done.
2. Actual production consumer path.
3. Shortest real business canary and cheapest sufficient proof.
4. Least-cost execution: direct Lead or delegated Worker.
5. Earliest safe canary.
6. Only observed blocker fixes and proportional direct-regression checks.
7. Optional governance/hardening only when expected value exceeds cost.

Do not encode a role, card transition, plan count, review count, timer, test
style, or evidence format as a prerequisite ahead of business movement. Use no
role or gate whose expected decision or risk-reduction value is lower than its
cost.

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
- Overseer runs at every crossed wall-clock hour, at overruns, and before the
  Full final; its mandate is cutting security theater, secret ceremonies, and
  process work without a tangible result.
- Tester is the mandatory real-surface final gate for user-facing results; test
  files never substitute.
- One real-use Tester is enough unless independent/blind coverage has concrete
  additional value.
- Full may contain however many material options actually exist.

## State and evidence

One compact current task record is preferred when it pays for recovery,
coordination, or audit. Durable research/result files are cost-triggered; no
elapsed-time threshold mandates files or commits. Do not duplicate task,
handoff, report, and evidence content.

Match proof to claim. Source, tests, deployment, and real-business canary are
reported separately. An accepted MVP is not silently upgraded to strict
admission, perfect atomicity, broad hardening, portability, or visual polish.

## Workspace and adapters

Stay in the primary checkout, warn on auxiliary/detached/non-default state, and
preserve foreign changes. Adapter syntax remains under `adapters/`; portable
behavior remains in `src/common/`. Secrets are read from an environment
variable, `.env`, or a file in one step; secret-handoff infrastructure is
forbidden.

When changing instructions, update the owning source, direct mirrors/templates,
and semantic validators. Require ordering and forbidden old behavior, not mere
phrase presence. Run `git diff --check`, the business-first regression, and
`python3 tests/validate.py`.
