> Background reference. Load only when the task needs this mechanism. `AGENTS.md` wins on any conflict: its finish line, blocker lists, escalation chain and delivery rules override this file.

# Hourly business-result direction check

This control is mandatory every hour of observed active work, including with green
tests and a confident implementer. It is the single 60-minute direction review:
TIME_CONTROL.md names no second hourly checkpoint, and the two are the same
review described once here and referenced there. The original assignment,
attached document and
latest direct user corrections define the goal; your plan, summary or new task card
cannot replace them. A fresh zero-knowledge Overseer may read this checkpoint against
the original request to guide the Lead; it does not own the result and never gates
delivery.

## Decision, not a reading receipt

Compare the requested outcome with what the user can use now. Name the hour's result:
working behavior, necessary intermediate result, material uncertainty resolved, or
no progress. SHAs, test/file counts and launched agents alone prove no user benefit.
If recent work corrected a SHA, filename or receipt instead of delivery, distinguish
an unverified real risk from a formatting error. For known checked code, correct
metadata locally and perform the nearest authorized user step. Resolve unknown
coverage from the original verification result; never relabel PASS. Switch now,
not next hour. See REVIEW_TO_DELIVERY.md; required tests and existing gates remain.
Check new mandatory conditions/extensions: who requested them, whether the result
needs them, whether a local problem blocks independent work unnecessarily.
Decide to continue the necessary path, remove invented scope, change approach or do
an available part of the assignment. Record the decision and assign any execution to a Worker in existing
state. Promising more attention without changing the next action does not fix goal
loss. For design reconsideration use working → ideal → minimum working ~80% value.

## Direction check is not acceptance

Lead checks alignment with the original goal and chooses the next useful step;
do not launch a group every hour. Use a fresh Zero Knowledge tester at a major
milestone or final acceptance when the accepted business claim needs independent
user-path evidence. Give a ready user result and a realistic persona/goal; preserve
observed positive and negative feedback. This is an evidence choice, not an elapsed-time gate.
When useful, methods are documented in `../skills/user-testing/SKILL.md` and
`../skills/focus-groups/SKILL.md`.
Before code the goal already identifies the user, task, before/after difference and
check point. Bugs immediately use TDD RED → fix → GREEN → original scenario.
Continuous technical verification does not wait for major acceptance. If the test
runtime is unavailable, Lead continues independent work without invented tester results.

## Trigger and recording

`hooks.json` registers these events and `lhc_entry.py` handles them; no daemon, cron, background chat or timer.

| Event | Mode | What it does |
| --- | --- | --- |
| `SessionStart` | `--instructions-only` | Injects LHC instructions; shows the plan bound to the session, if any. |
| `PostCompact` | `--instructions-only` | Re-injects instructions and shows the plan bound to the session: done leaves with results, the current leaf and its last note, the next leaves. |
| `UserPromptSubmit` | `--plan-entry` | Codex package only: instructions plus the open plans of this session as candidates. |
| `PostToolUse` | `--heartbeat-only` | Time reminders and plan facts (overrun, contradicting statuses, uncut stage). |
| `PreToolUse` | `--git-guard` | Refuses `git stash` and a branch switch in the primary checkout. |
| `Stop` | `--stop-gate` | Holds a stop while the session's plan has open leaves, and once per 30 min asks for the Overseer. |

A hook never reviews work or scores it; a failing hook prints one line to stderr and the turn continues.
State, verification and verdicts live behind explicit CLI commands
(`lhc_time_guard.py hook`, `lhc_outcome.py contract|review|route|question|status`,
`lhc_entry.py --session`), never inside a hook.
Monotonic intervals close on Stop, Interrupt and permission requests;
human waiting is not active work. Unknown intervals after reconnect/reboot are not
reconstructed. With incomplete lifecycle, hourly wall-clock is an explicitly labeled
fallback signal, never measured active work.
One session state retains original input, latest correction, clock and last review.
New phases/cards/compaction do not reset clocks. A reminder is not completed review.
An overdue check reminds again on resume or at most every five active minutes,
without spamming each tool call.
After the actual check, record it in the same state:

```sh
python3 <LHC>/tools/lhc_time_guard.py business-review \
  --cwd <project> --runtime <runtime> --session-id <native-id> --review-id <hook-id> \
  --source-ref '<original assignment/document and latest correction>' \
  --business-result '<actual user-visible difference>' \
  --scope-decision '<direction decision>' --next-action '<next action>'
```

No independent tester is required for this record. `direction_reviewed` means only
a direction check; `milestone_acceptance=not_evaluated` does not accept the product.
Legacy optional tester fields may retain observations but cannot replace separate
actual milestone evidence when the claim requires it. The command checks record
completeness, not free-text truth; Lead owns references and assigns the selected action to a Worker.
Use English for new internal records. Tell the user only a material result, problem
or needed decision; mandatory internal checks do not require empty hourly reports.
## Empty frontier still needs a goal decision

Closing every card is a task fact. Acceptance of the original goal remains in
the existing native outcome, bound to the exact canonical plan, semantic goal
scope and current acceptance evidence. A status-only outcome cannot accept an
implementation goal. Explicit plan activation binds an existing native outcome
when Lead ownership is known; a legacy or unreadable outcome stays unknown.

When no useful next leaf is available and the goal is unaccepted, Lead chooses
one concrete next leaf, scoped research/decomposition, a genuine external wait
with owner, evidence and resume condition, or preserves an actual human stop or
revocation. Record decision, evidence, action, owner and uncertainty through
LhcPlan frontier or the existing outcome CLI:

```sh
python3 <LHC>/tools/lhc_outcome.py --cwd <project> --runtime <runtime> \
  --session-id <native-id> frontier --plan-dir <canonical-plan> \
  --decision need_fact --action-kind research --evidence '<observed gap>' \
  --action '<one bounded permitted investigation>' --owner '<executor>' \
  --uncertainty '<fact the investigation will resolve>'
```

Use decision `continue` with `--action-kind leaf --leaf-id <existing-ready-id>`,
or `wait_external` with `--resume-condition '<observable resumption condition>'`.
A work decision selects execution; writing the record does not perform the work.
A human-stop record requires an existing structured native stop or refusal, and
cannot create authority to stop. Unknown delivery is reconciled, never replayed.

A missing binding can be repaired by `bind-plan --plan-dir <canonical-plan>`;
`replace-plan --plan-dir <old> --replacement-plan-dir <new> --source-ref <evidence>`
records an explicit replacement, separately from ordinary binding changes.
The hook reads these facts, gives bounded advice once per changed frontier, and
does not classify prose, accept a goal, call an LLM, dispatch, or create a wake.
Admission unknown/blocked remains distinct from an exhausted frontier. Graph and
catalog goal-control snapshots are derived views with source fingerprints, never
acceptance authority. Changed goal scope or evidence invalidates stale decisions.
