# Codex lifecycle delivery 1.4.5

## What was broken

The installed 1.4.4 native hooks were enabled/trusted and the affected session
already had real active-time/learning state. A transcript with manual acknowledgement
commands alone does not prove absent hooks. Confirmed defects were narrower:

* The user-level bootstrap pinned 1.4.3 independently of the native 1.4.4 package.
* Initial context only pointed to a long router, and old threads had no lazy entry
  on their first tool boundary. The concise business/three-pass/TDD/milestone contract
  was absent from that initial native message.
* Codex compact events do not deliver additionalContext. The wrapper turned the
  guard's compaction warning into that unsupported output and consumed reminders.
* SessionStart(source=compact) paused an open monotonic interval after compaction.
* Due checks were silently discarded on ordinary Stop.
* Reading only 64 KiB of native JSON could truncate a tool response, erase the exact
  session identity, and update the unrelated unknown-session clock instead.

## Repair and boundaries

SessionStart/UserPromptSubmit and the first supported tool boundary inject the
current installed root and actionable contract. Compaction only preserves state;
SessionStart(source=compact), or the next supported boundary when necessary,
rehydrates original/latest user input and last decisions. Pauses, human Stop and
permission waits never trigger auto-resume. Learning reminders are rate-limited.

An ordinary Stop with an overdue review requests one bounded native continuation
per turn/debt identity. Actual business-review/checkpoint evidence clears the debt;
merely emitting a hook or repeated Stop does not. If continuation cannot close it,
it stays pending with an explicit warning, not an endless loop or invented PASS.
This is not a prohibition on independent tool work and never bypasses approvals.

The Codex global block no longer pins a separate cache version: the current native
hook provides absolute router/tool paths. Other runtime bootstraps are unchanged.
Input accepts a bounded 8 MiB character window; malformed/oversized/unidentified
native payloads report unavailable coverage and do not modify another session.

These changes enforce delivery and bounded lifecycle transitions, not the semantic
truth of model-written reviews. Milestone quality still needs real independent
Zero Knowledge attempts with realistic goals and full feedback. No milestone is
accepted because an hour passed, because a hook ran, or because a regex matched.

## Verification

Behavioral RED: seven lifecycle failures and two large/invalid-payload failures.
Independent review then found four further issues (prompt path corruption, stale Stop snapshot, truncated late constraints, invalid command template); all reproduced RED and corrected. After repair, 231 existing/new Python tests pass. Native client acceptance is a
separate test: ordinary task with no @LHC, then resume the same thread, then controlled
elapsed-state/compaction delivery. Controlled clocks are not a real multi-hour run.

References: OpenAI hook event input/output contract and plugin packaging:
https://developers.openai.com/codex/hooks
https://developers.openai.com/plugins/build/plugins
