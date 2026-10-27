# Worker implementation protocol

Fallback for `Worker(mode=implement)` when the `worker-code` or `worker-bugfix`
skill is not installed. `src/common/agents/Worker.md` applies.

1. Confirm the accepted claim and the real consumer path.
2. Locate the code with targeted `rg`; current source beats any map or index.
3. Bugfix: write a focused test that fails for the reported behavior (RED), make
   the smallest fix, rerun it (GREEN), then the original scenario.
4. Feature: build a usable vertical slice before horizontal completeness.
5. Rerun the proof and the narrowest regression checks. Stop when the claim is
   proven; no unrelated abstractions, hardening, logging, docs or edge cases.
6. Report by minute 20 and at handoff as `Worker.md` says. One cheap attempt at
   another route, then return blockers to L with a recommended default.

Load `src/common/profiles/Code.md` for code and `Test.md` when tests matter.
