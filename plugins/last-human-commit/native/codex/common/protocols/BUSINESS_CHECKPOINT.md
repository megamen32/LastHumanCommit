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

`hooks.json` registers exactly three native events, and `lhc_entry.py` routes them to
existing `lhc_time_guard.py`; no daemon, cron, background chat or timer.

| Event | Mode | What it does |
| --- | --- | --- |
| `SessionStart` | `--instructions-only` | Injects LHC instructions and the session plan context. |
| `PostCompact` | `--instructions-only` | Re-injects instructions after compaction, carrying the plan as text. |
| `PostToolUse` | `--heartbeat-only` | Time-only reminder: elapsed time and which command to call. |

`lhc_entry.py --session` is an explicit agent command, not a hook event. `UserPromptSubmit`,
`PreToolUse` and stopping are not registered; a runtime that offers them is not wired to
LHC, and no protocol promise may claim otherwise.
Every hook is **time-only**: it reports elapsed time and names the command to run. It
never reviews work, never scores it, never renders a verdict and never blocks the
message flow — a failing hook prints one line to stderr and the turn continues.
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
