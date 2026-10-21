---
name: worker-research
description: Worker-owned least-cost codebase research for tracing real production paths, locating symbols and ownership, testing hypotheses, and handing Lead a decision-ready implementation route. Use for read-only repository investigation, architecture orientation, root-cause localization, the research stage of a bounded bugfix, or any task likely to repeat earlier code-location research. Search the reusable project code map first, prefer rg for fresh source truth, use Graphify only for genuinely multi-hop relationships, and use context-mode to process large outputs without flooding context.
---

# Worker Research

Find the shortest verified route to the next business proof. Do not map the
whole repository.

## Tool order

1. Search existing reusable knowledge before rediscovering it:

   ```bash
   python3 <this-skill-directory>/scripts/code_map.py \
     --root "$PWD" search <business-noun> <symbol>
   ```

   Resolve `scripts/code_map.py` from this skill directory. Treat every hit as
   a lead: run `check`, then confirm the decisive location with one targeted
   `rg` or source read.
2. Use `rg --files`, then `rg -n -C` as the default fresh search. Trace from
   the real consumer inward. Search exact endpoint names, commands, config
   keys, symbols, and user-visible strings before broad concepts.
3. Use context-mode for large files, logs, test output, or three or more related
   searches. Ask it focused questions and return only derived evidence. It is a
   context-saving processor and index, not the durable source of truth.
4. Use an existing Graphify graph when the decision depends on three or more
   components, indirect callers, ownership, or cross-language flow. Verify every
   decisive graph edge against current source with `rg`. Do not build or refresh
   a graph for a simple symbol lookup.
5. Stop when Lead has the production path, owning locations, first blocker,
   cheapest patch route, proof, and decision-relevant unknowns.

In practice: `rg` is the fastest and most authoritative locator; Graphify is
useful orientation for multi-hop structure but can be stale or over-broad;
context-mode is highly effective for preserving context on large output but
does not by itself prevent future rediscovery.

## Bugfix route

For a defect, preserve this order in the research receipt:
`telemetry -> reproduction -> smallest failing test -> root cause -> patch ->
regression`.

1. Use telemetry to locate the failing boundary; do not infer the fix from a
   stack trace, alert, or log alone.
2. Reproduce the same failure through the real consumer path with the smallest
   deterministic probe available.
3. Add or specify the smallest failing test that proves the accepted behavior,
   not an implementation detail.
4. Patch only the verified root cause when mutation is authorized.
5. Re-run the failing proof, proportional regression checks, and the cheapest
   claim-matching business canary.

For a read-only assignment, stop before mutation and return the exact test,
patch location, and regression command. If the assignment authorizes the fix,
continue through regression without starting a second broad investigation.

## Measure the result

Record a compact baseline/candidate measurement block in the returned receipt:

- `lead_time`: assignment or defect intake to accepted business proof;
- `rework`: failed or abandoned routes, repeated patch/review cycles, and
  repeated manual steps;
- `effective_cost`: known model/API/compute spend plus measured human and agent
  active time required to reach the proof;
- `latency`: end-to-end time from real request to usable result; report
  P50/P95/P99 only from a representative sample and label a single observation
  as a canary, not a benchmark;
- `quality`: the business success metric against the baseline, an explicit
  quality floor, and a non-inferiority margin when equivalence is claimed.

Include the source and confidence for every value. Write `unknown` when a value
was not measured; never manufacture precision from wall-clock, file mtimes, or
one warm run. Compare cost or latency only at the same quality floor.

## Preserve reusable findings

Upsert a code-map entry before returning when a verified finding is likely to
be asked again: where a business path lives, who owns a decision, which config
controls runtime behavior, or which false route caused a recurring failure.

```bash
python3 <this-skill-directory>/scripts/code_map.py --root "$PWD" upsert \
  --key agent-resume-production-path \
  --kind production-path \
  --summary "web/server -> AgentResumeClient -> agent_resume.py -> codex exec resume" \
  --location "web/server::caller" \
  --location "agent_resume.py::main" \
  --evidence "rg -n 'AgentResumeClient|codex exec resume' web agent_resume.py"
```

The map is one bounded, rewritable
`.agents/shared-session/knowledge/code-map.json`, not an append-only diary.
Upsert replaces the same key. Store verified locations and compact evidence;
never store secrets, raw logs, guesses as facts, temporary PIDs, or task-only
status. Use `--confidence inferred` for a useful but unproven lead. Remove
invalid knowledge with `code_map.py remove`.

Store reusable paths and failure shields in the code map. Keep per-run timing,
cost, latency, and quality measurements in the task result or research receipt;
do not turn the reusable map into an append-only metrics log.

## Lead interaction and return

Ask Lead non-blockingly when its user context can change scope, priority,
accepted proof, or product choice. Include evidence, recommendation/default,
parallel-safe work, and the exact action that must wait; continue work valid
under every answer.

Return `READY_TO_IMPLEMENT`, `PROGRESS`, `QUESTION_FOR_L`, or `BLOCKED` with:
the real path, owning files/symbols, checked hypotheses, code-map keys reused or
updated, bugfix-cycle position when applicable, the measurement block, unknowns
that change the decision, and the shortest next action.
