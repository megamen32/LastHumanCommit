# Hourly business-result direction check

This control is mandatory every hour of observed active work, including with green
tests and a confident implementer. The original assignment, attached document and
latest direct user corrections define the goal; your plan, summary or new task card
cannot replace them.

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
an available part of the assignment. Record and execute that decision in existing
state. Promising more attention without changing the next action does not fix goal
loss. For design reconsideration use working → ideal → minimum working ~80% value.

## Direction check is not acceptance

Lead checks alignment with the original goal and chooses the next useful step;
do not launch a group every hour. Fresh Zero Knowledge testers belong at major
milestones (~3 hours of coherent work) and final acceptance: ready user result,
varied realistic personas/goals, independent attempts and detailed positive/negative
feedback. This is an outcome boundary, not a strict timer or every-commit check.
Methods: `../skills/user-testing/SKILL.md`, `../skills/focus-groups/SKILL.md`.
Before code the goal already identifies the user, task, before/after difference and
check point. Bugs immediately use TDD RED → fix → GREEN → original scenario.
Continuous technical verification does not wait for major acceptance. If the test
runtime is unavailable, Lead continues independent work without invented tester results.

## Trigger and recording

`lhc_entry.py` connects native SessionStart/UserPromptSubmit/PreToolUse/PostToolUse,
compaction and stopping to existing `lhc_time_guard.py`; no daemon, cron, background
chat or timer. Monotonic intervals close on Stop, Interrupt and permission requests;
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
actual milestone acceptance results. The command checks record completeness, not
free-text truth; Lead owns the source references and execution of the selected action.
Use English for new internal records. Tell the user only a material result, problem
or needed decision; mandatory internal checks do not require empty hourly reports.
