# Native milestone acceptance gate

Assignment: fix the native substantial UI finish defect, only in this assigned worktree.
Result: persist missing independent user acceptance; one bounded native finish request,
real raw tester attempts only, honest blocked/changes-required/pending/accepted states.
No push, deploy, runtime edits, other projects or additional coding workers. Coordinator
owns independent review and live fresh UI/browser acceptance. Version target 1.4.9.

Design: working = durable debt; ideal = automatic task/surface/result correlation;
practical = canonical native gate using actual Git surface change, native task context
and existing Herder raw transcripts. No scheduler, new delegation service or signatures.

Budget: current host available RAM 34 GiB, disk 313 GiB; enclosing managed Codex
cgroup currently ~4.3 GiB, CPU 4 cores, TasksMax1536. This task runs one suite at a
time, <=2 workers (Python serial), NODE_OPTIONS=--max-old-space-size=2048;
test child RAM/address-space ceiling 4 GiB, CPU affinity <=2 existing cores,
no requested swap allocation (same 4 GiB address ceiling), <=128 child processes,
temp/output <=512 MiB, no GPU, emergency wall limit 1200s for expected <=120s suite.
Existing outer cgroup/runner guard stays intact; no daemons or browser launches.

State: source/package/native fixture checks complete; scoped local commit ready.
No push/deploy. Coordinator owns independent review and actual fresh UI acceptance.
Existing GSD documents describe completed TASK-01..05; this assignment extends the
same native continuity path, without reopening that roadmap or unrelated work.

RED: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_native_milestone_gate.py`
failed both initial cases: ordinary major UI finish and leader-written PASS both
returned `{}`. The exact reproducer passed after the native gate was integrated.
Subsequent focused suite: 48 passed including all original lifecycle regressions.
Review-driven RED: `... pytest -q tests/test_native_milestone_gate.py -k generic_or_partial`
failed 2 cases: generic and explicitly partial reports with incidental PASS were
accepted. Added goal/steps/result floor and partial-attempt rejection; final full-suite rerun GREEN.

Method checkpoint after concrete reviewer corrections: initial probes simplified
real browser argv and Herder archive ownership too far. Owning fix is in
`src/common/tools/lhc_milestone.py`: actual option-bearing/separate native browser
operations, generated HTML, late tasks, exact returned Herder manifest path and
native-source checks. Concrete regression fixtures cover those shapes, not just
author-written PASS fields. No new workflow skill, grader, receipt subsystem or
memory write is justified. This is the authorized defect itself; independent real
UI reuse remains coordinator-owned, not yet verified. One fixture construction
error lacked `git init` and was corrected; assertions were retained.

## Final verification and handoff

- Base: `8d6c92244ca3fde64b68c4d8d61cf929c8f53d63`; existing assigned branch/worktree retained.
- `python3 tests/validate.py`: PASS, 283 passed in 69.02s (0:01:09); package/parity/block adapter PASS.
- Final broad run: CPU affinity2, address-space ceiling4GiB, emergency1200s; observed70.83s, maximum single-child RSS40768KiB. Temp after checks8KiB.
- `NODE_OPTIONS=--max-old-space-size=2048 bun test --max-concurrency 2 tests/opencode-v2.test.ts tests/opencode-checkpoint.test.ts tests/opencode-review-delivery.test.ts tests/opencode-milestone.test.ts`: 11 pass, 0 fail, 61 expectations, 7.86s.
- `sync_skills.py` generated all projections; all manifests aligned at 1.4.9.
- Exact Stop reason roundtrip and permission-success native-edge RED: 2 failed/2 passed before fixes; included in final GREEN suite. Manual late tool completion cannot release Interrupt/SessionEnd.
- Incidental technical PASS with blocked login RED: 1 failed/1 passed before fix; final GREEN. Confirmed acceptance survives source archive unavailability for the same surface.
- Initial full validation exposed one missed Claude version field, corrected locally; assertions were not weakened. One test-created empty clock from the fixture that lacked git init was verified by its exact creation time/native source root and removed; the fixture is now isolated.
- Native event/API/browser data here are isolated regression fixtures. No coordinator UI fixture, live browser attempt, installed runtime, user session, credential, system config, push or deploy was operated.
- Limits: mechanical independent-source/attempt floor, not arbitrary UX semantic proof; Lead interprets raw coverage and repairs. OpenCode cannot veto native completion or autonomously schedule another turn. See docs/V1.4.9.md.
- Method correction verified in owning source tests; real user-path reuse remains coordinator-owned and unclaimed. No new agent, grader, memory store, report signature or scheduler.
