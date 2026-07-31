# Harness adapters

The adapter layer is the boundary between the portable LastHumanCommit canon
and a host's agent API. It is intentionally modular: installing or enabling
one adapter does not install, configure, or rewrite another harness.

## Two axes

The core defines capability contracts in `src/common/agents/`, optional domain
profiles in `src/common/profiles/`, and triggered protocols in
`src/common/protocols/`. An adapter defines how one harness delivers those
contracts:

```text
role contract × harness adapter
Lead          × Codex / OpenCode / Claude Code / Hermes
Worker        × Codex / OpenCode / Claude Code / Hermes
```

Do not duplicate a role in an adapter. An adapter may add a small optional
overlay when its API needs extra syntax, file-loading, permissions, or resume
instructions. The overlay is additive and is loaded only by that adapter.

Every adapter manifest records evidence as `proven`, `unproven`, or `unsupported`.
Names in a manifest are capability claims, not promises that every model or
provider is routable on every installation.

## Delivery contract

An adapter should answer these questions without changing the core role text:

- How is one complete role delivered to a child?
- How are project marker blocks discovered without overwriting project text?
- Can a fresh child context and the actual model be proven?
- How is the 30-minute resume/wake transported?
- What does the adapter do when a capability is unavailable?

`scripts/lhc-block` remains a narrow marker utility. It is not an installer,
renderer, daemon, or adapter manager.
