# Check the direction of the work

Compare the original request and latest correction with what the user can use now. If the last work only repaired a report, or repeated an unchanged check, choose the next action that advances the actual result. When the route is useful, continue it.

The hourly reminder concerns direction. Independent testing is selected for an actual user-path or release question, not merely because an hour passed. Boss's independent feedback can help; another supervisory session is unnecessary for a known repair.

## Record through the existing tool when needed

The guard retains one session's goal, corrections and timing. Observed active intervals pause on explicit idle, permission and stop events. Missing coverage uses a labeled wall-clock fallback.

```sh
python3 <LHC>/tools/lhc_time_guard.py business-review \
  --cwd <project> --runtime <runtime> --session-id <native-id> --review-id <hook-id> \
  --source-ref '<original request and latest correction>' \
  --business-result '<observed result>' \
  --scope-decision '<route decision>' --next-action '<next action>'
```

`direction_reviewed` records this check. Product acceptance still depends on the relevant result. Keep the note useful; a routine unchanged state needs no separate user message.

## Hooks

| Event | Mode | Effect |
| --- | --- | --- |
| SessionStart / PostCompact | `--instructions-only` | Restore guide and bound-plan context |
| UserPromptSubmit, Codex package | `--plan-entry` | Guide and current session's candidate plans |
| PostToolUse | `--heartbeat-only` | Observed time and plan reminders |
| PreToolUse | `--git-guard` | Existing shared-checkout protections |
| Stop | `--stop-gate` | Existing bounded reminder for open plan work |

These portable hooks are distinct from the OpenCode 2 native Boss plugin. A failed optional hook does not establish a result or permission.

## No available task

Completed cards and the original goal are separate facts. Use `read_goal_control` for the session-bound native outcome. If no executable work remains and the goal is unfinished, choose remaining work, a focused investigation, or a genuine external wait with its owner and resume condition.

```sh
python3 <LHC>/tools/lhc_outcome.py --cwd <project> --runtime <runtime> \
  --session-id <native-id> frontier --plan-dir <canonical-plan> \
  --decision need_fact --action-kind research --evidence '<observed gap>' \
  --action '<investigation>' --owner '<executor>' --uncertainty '<question>'
```

Use `continue` with `--action-kind leaf --leaf-id <id>` for an existing ready task, or `wait_external` with `--resume-condition`. Preserve an actual human stop. Reconcile uncertain external effects through their original operation.

## Goal handoff

Record a real Lead handoff with the existing `update-plan` operation and a revision:

```sh
python3 <LHC>/tools/lhc_plan_json.py update-plan <canonical-plan> \
  --fields '{"current_goal_lead":{"host_id":"<host>","harness":"codex","session_id":"<native-id>","source_ref":"records/<handoff>.md"}}' \
  --revision '{"reason":"Explicit Lead handoff","summary":"Current role transferred"}'
```

Use the verified identities from the handoff. Historical authors and attempts stay in history. The new role does not inherit an old acceptance for different work. Conflicting current assignments and unreadable native state remain unknown until resolved. `ORCHESTRATION_RECORDS.md` covers binding and acceptance details.
