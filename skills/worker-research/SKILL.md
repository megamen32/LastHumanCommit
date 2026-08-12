---
name: worker-research
description: Worker-owned least-cost codebase research for tracing real production paths, locating symbols and ownership, testing hypotheses, and handing Lead a decision-ready implementation route. Use for read-only repository investigation, architecture orientation, root-cause localization, or any task likely to repeat earlier code-location research. Search the reusable project code map first, prefer rg for fresh source truth, use Graphify only for genuinely multi-hop relationships, and use context-mode to process large outputs without flooding context.
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

## Lead interaction and return

Ask Lead non-blockingly when its user context can change scope, priority,
accepted proof, or product choice. Include evidence, recommendation/default,
parallel-safe work, and the exact action that must wait; continue work valid
under every answer.

Return `READY_TO_IMPLEMENT`, `PROGRESS`, `QUESTION_FOR_L`, or `BLOCKED` with:
the real path, owning files/symbols, checked hypotheses, code-map keys reused or
updated, unknowns that change the decision, and the shortest next action.
