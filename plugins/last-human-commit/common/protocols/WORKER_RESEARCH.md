# Worker research protocol

Fallback for `Worker(mode=research)` when the `worker-research` skill is not
installed. Research is read-only and finds the cheapest route to the next proof.

1. Check the project code map `.agents/shared-session/knowledge/code-map.json`
   and how fresh the hit is.
2. `rg --files` and targeted `rg -n -C`; start from the real consumer and trace
   inward.
3. Process large outputs with context-mode; use an existing Graphify graph only
   for genuinely multi-hop questions, and confirm decisive edges in source.
4. Find the existing mechanism, the first real blocker and the cheapest probe
   that discriminates. Stop when L can assign the implementation leaf.

Update the code map only with verified, likely-to-recur facts (paths, owners,
config, decisions); never secrets, raw logs or guesses. Persist research when
handoff, recovery, reuse, or the cost of rediscovery justifies it.

Return `READY_TO_IMPLEMENT`, `PROGRESS`, `NEEDS_MORE_RESEARCH` or `BLOCKED` with
evidence, the production path, the existing mechanism, what was excluded, and
the cheapest next action. No code, config changes, deploys or essays.
