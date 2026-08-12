# Worker skills and reusable research map

Status: completed
Latest user request: Create Worker skills for research, coding, and bug fixing; make research prefer rg, use graph/context-mode proportionally, and stop repeated rediscovery by saving verified code-location knowledge.
Accepted business outcome / Definition of Done: Three discoverable Worker skills exist and the research skill can deterministically upsert/search a bounded project-local code map with evidence and freshness hints.
Primary acceptance check: plugin validation discovers all three skills; code-map tests prove upsert, replacement, search, and stale-file reporting.
Allowed scope: LHC canonical skills, generated plugin skills, Worker research/implementation routing, one dependency-free code-map tool, focused tests and docs needed by the contract.
Excluded scope: subagents, external database/service, Graphify or context-mode core changes, global deployment/restart, unrelated LHC cleanup.
Started at (UTC+3): 2026-08-12T13:40:35+03:00
Initial estimate (minimum / maximum active minutes): 20 / 45
Actual active minutes: unknown; hook-observed only
Lifecycle provenance: copied from completed work snapshot.
Harness: Codex desktop
PID: unknown (harness-managed)
Agent session: current Codex task
PID status: running (harness-observed)
Last PID signal: none observed
Last task-file transition: work copied to done
Last task-file mtime observed: 2026-08-12T13:54:00+03:00
Current blocker: none
Next shortest action: use the three skills on real Worker assignments and refine only from observed failures.

## Result

- Added canonical `worker-research`, `worker-code`, and `worker-bugfix` skills
  plus generated Agent Plugin copies and UI metadata.
- Worker routing loads exactly one matching primary skill and retains portable
  protocol fallbacks.
- Research order is reusable code map -> targeted `rg` -> context-mode for
  large output -> Graphify only for multi-hop orientation, with decisive graph
  edges verified against source.
- Added bounded rewritable
  `.agents/shared-session/knowledge/code-map.json` and dependency-free
  `code_map.py` with upsert/search/check/remove and file freshness evidence.
- Verified code-map behavior with 5 tests; plugin validation and Codex/Claude/
  OpenCode loader canaries discover 10 skills; core validators pass.
- Rolled out common Worker routing at committed revision `6ca39ad` with digest
  `sha256:20d19fa13665efb85579de07cdf19441ddacbc6ea95d070a4cca7a1f1e6ed2d1`.
- Installed Agent Plugin `0.3.0`; Codex cache validates 10 skills. Fresh
  OpenCode and Hermes skill discovery both expose `worker-research`,
  `worker-code`, and `worker-bugfix`.
