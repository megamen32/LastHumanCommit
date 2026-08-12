# Worker implementation protocol

Use only for `Worker(mode=implement)`. Load `../profiles/Code.md` for code and
`../profiles/Test.md` when tests add claim-relevant value.

Prefer the installed `worker-code` skill for feature/code work and
`worker-bugfix` for behavior fixes. Use this file as the portable fallback when
skills are unavailable.

## Common route

1. Confirm the latest accepted business claim and actual production consumer
   path.
2. Reuse fresh verified code-map findings, but confirm decisive locations with
   targeted `rg`; current source wins over graph/index/map history.
3. Reproduce or observe the shortest failing condition when doing so is cheap
   and discriminating.
4. Make the smallest coherent vertical change on the real path.
5. Re-run the same proof and the narrowest direct-regression checks.
6. Update a reusable code-map key only when the change affects a durable path,
   owner, config, or recurring failure shield.
7. Stop as soon as the assigned claim is proven.

For a bugfix, a focused failing regression or black-box canary is preferred but
not ceremonial. For a feature, implement a usable vertical slice before
horizontal completeness. Do not add unrelated abstractions, hardening, logging,
cleanup, docs, compatibility, or edge-case completeness.

At every 20 active minutes report progress, business delta, blocker, and the
shortest next action. The checkpoint is not a lifetime limit. Remain available
for L to continue, redirect, or resume. Stop independently only for active harm,
foreign-write collision, lost authority, unavoidable scope decision, or a
concrete unrecoverable capability failure.

Ask L at every decision boundary that needs its broader user/session context.
Use a non-blocking parent transport with evidence, recommendation, proposed
default, parallel-safe work, and the exact action that must wait. Continue only
work valid under every plausible answer until L decides.
