# Lead/Worker feedback and business time guard

Status: complete in source; Fleet rollout pending this snapshot

## Result

- Workers ask L at every context-dependent decision boundary instead of guessing
  a business decision.
- A question includes evidence, recommendation/proposed default, safe parallel
  work, and the exact action waiting for L.
- With a proven non-blocking parent transport, the Worker continues independent
  work valid under every plausible answer; only the divergent action blocks.
- L owns and promptly returns the decision from its broader user/session context.
- Every declared coherent work cycle has an immutable minimum/maximum estimate.
- At every crossed wall-clock hour while active, L reports real tasks closed,
  business delta, completed files, planned/actual time, blockers, delaying
  gates/instructions, control evidence, and the shortest next route.
- `src/common/tools/lhc_time_guard.py` emits persistent idempotent hourly,
  original-maximum overrun, and estimate-mutation events with the requested
  Russian business-first diagnostic.

## Safety and capability boundary

The diagnostic never authorizes weakening essential safety, secret handling,
human authority, destructive-action boundaries, or proof honesty.

The source tool and adapter invocation contract are complete. Native
non-blocking parent transports and lifecycle/scheduler hooks remain
`unproven`/`adapter-dependent` until a physical harness event attests them. In
their absence, Lead invokes the tool at observable updates; crossed hours are
reported once on the next call rather than falsely claimed as on-time wakes.

## Baseline-first installation evidence

Before these changes, source commit `e49eeeb` was previewed, applied, verified,
and physically read from active Lead files on `100`, `44`, `88`, and `mac`.

- Version: `e49eeeb`
- Digest:
  `sha256:efa3dd9aedc11712c6fe6eccc31ae09e086039101791352fcb2afce49b7b90f4`
- Rollback roots: `.local/share/last-human-commit/rollbacks/e49eeeb-lhc-rollout`

## Verification

- Regression red phase: 5 expected failures.
- Focused semantic/tool green: 11 passed.
- Business semantic contract: 8 passed.
- Stateful time-guard behavior: 3 passed.
- Full pytest: 20 passed.
- Task-state/resume, marker adapter, skill parity, plugin validation: PASS.
- CLI canary: `hourly + overrun`, crossed hours `[1, 2]`, original `30–90`,
  actual `100 active / 125 wall-clock`, completed tasks/files and full diagnostic.
- `AGENTS.md` / `CLAUDE.md`: byte-identical.
- `git diff --check`: clean.

## Time

- Started at: 2026-08-12T11:10:00+03:00
- Initial estimate: 60 / 120 active minutes
- Estimate status: within maximum at source completion
- Control: explicit 20-minute business-delta checkpoint and CLI time-guard
  canary were performed
- Next route: commit, exact Fleet preview, apply, verify, physical tool/role
  readback

## Files completed

- `src/common/tools/lhc_time_guard.py`
- `src/common/protocols/TIME_CONTROL.md`
- `docs/time-guard.md`
- `tests/test_time_guard.py`
- Lead/Worker/Planning, router, task/Full templates, shared-session docs,
  adapters/manifests/templates, canonical/generated skills, README/ROADMAP, and
  semantic validators directly supporting the contract
