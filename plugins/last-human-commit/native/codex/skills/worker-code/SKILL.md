---
name: worker-code
description: Worker-owned implementation procedure for writing the smallest coherent code change on the real business path. Use for a bounded feature, integration, endpoint, UI flow, adapter, or production-path implementation after the accepted outcome is known. Reuse verified project knowledge, confirm it with rg, ship the thinnest usable vertical, ask Lead non-blockingly at product decisions, and stop when the requested claim is proven.
---

# Worker Code

Implement one accepted business vertical. Lead owns route and integration.

## Procedure

1. Confirm the accepted outcome, actual consumer, allowed paths, exclusions,
   and cheapest sufficient proof.
2. Search the reusable code map with the sibling Worker Research tool, then
   verify relevant locations with targeted `rg`. Do not repeat broad research
   already captured as fresh verified knowledge.
3. Trace the production call chain before editing an adjacent adapter, fixture,
   abstraction, or test double.
4. Reuse the existing mechanism and implement the thinnest usable vertical.
5. Run the real or closest claim-matching canary early. Fix only the first
   claim-blocking failure and add proportional direct-regression evidence.
6. If the patch changes a durable production path, owner, or config location,
   resolve `../worker-research/scripts/code_map.py` from this skill and upsert
   the affected key. Do not record ordinary task progress.
7. Stop when the assigned claim is proven.

## Lead interaction

Ask Lead whenever its broader user context can change behavior, product choice,
scope, proof strength, ownership, or a consequential action. Send concise
evidence, recommendation/default, parallel-safe work, and the exact blocked
action through a non-blocking parent transport; continue edits valid under
every plausible answer.

At each 20-minute checkpoint report measured timing, changed files, business
delta, blocker, whether the route remains shortest, and the smallest next
action. The checkpoint redirects work; it does not kill the Worker.

## Do not

- Do not implement horizontal completeness before the first usable path.
- Do not redesign, refactor, harden, document, or add compatibility work unless
  the current business claim requires it.
- Do not treat compilation or unit tests as user-facing proof.
- Do not trust a graph, context index, code map, or old task card over current
  source and the latest user outcome.
