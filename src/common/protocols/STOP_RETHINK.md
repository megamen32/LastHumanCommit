# STOP / RETHINK

Trigger when 30 minutes or 30 tool calls or shell commands pass without real
business delta toward an end-to-end P0 slice, after two failed independent
attempts, on conflicting evidence, when the user repeats that P0/P1 still
fails, when the target shares the failed failure domain, when scope must expand
materially, or when framework/process grows without user progress.

## Independent gate authority

The user is the only authority over Overseer and Critic. L requests their audit
but cannot frame, narrow, rewrite, or override it. Every gate decision is
binding on L. If a harness routes the report through L, L must relay the
complete report unchanged to the user before more action. L cannot override a
gate decision. `RETHINK`, `STOP`,
`STOP_SCOPE_DRIFT`, `STOP_MISSING_CONTEXT`, or
unanswered questions stop further actions and completion claims. L may answer
questions and present new business evidence to the same gate; only that gate or
the user may release the stop. Conflicting gate decisions resolve to the
stricter verdict until the user decides.

## Uptime checkpoint

After at most 30 tool calls or shell commands, or 30 elapsed minutes when
measurable, whichever comes first, every agent must run `uptime` and send a
progress checkpoint before more work. The checkpoint states current P0, real
business delta, elapsed time when available, blocker, and next action. It resets
both counters. If `uptime` is unavailable, the agent reports that fact and still
sends the checkpoint.

## Terminal scope drift

`STOP_SCOPE_DRIFT` is terminal for unauthorized scope expansion beyond the
original user request, confirmed scope, explicit exclusions, or the failed
canary's dependency chain. When it is raised:

1. Preserve the evidence without changing or cleaning the conflicting work.
2. Report the exact mismatch and required stop directly to the user and L.
3. Update the task record with the timestamp, stage, evidence, and
   `STOP_SCOPE_DRIFT` decision.
4. After plan selection, write in English; before plan selection, write in
   Russian.
5. Do not launch Explorer.
6. Do not generate alternatives.
7. Stop until explicit human scope confirmation is recorded in the task.

Do not investigate, implement, review, or otherwise resume work after this
decision until that confirmation exists.

## Architectural STOP/RETHINK

Architectural STOP/RETHINK applies to the non-scope triggers above. It may use
one bounded Explorer for external/current solution research when known tools,
projects, official documentation, or alternative components may exist. Give
the child the Explorer role; L does not load the Explorer prompt. This branch
may generate alternatives because it is choosing a path inside confirmed
scope, not seeking permission to expand scope.

The user message must contain:

1. Exact current blocker.
2. Why the selected path has not reached P0; if P0 is reached or absent, whether
   current P1/CORE is truly foundational or merely one possible, possibly worse,
   solution.
3. Concrete evidence.
4. What was checked and excluded.
5. At least two fundamentally different paths, selected from: manual/emergency
   workaround, limited vertical slice, another component or independent failure
   domain, and full long-term solution.
6. Time, risk, and expected result for each path.
7. L's recommendation.
8. One user question only when a decision is genuinely required; none when the
   answer is already clear.

Before plan selection, write in Russian. After plan selection, write in English.
Do not silently resume the same path after sending architectural STOP/RETHINK.
