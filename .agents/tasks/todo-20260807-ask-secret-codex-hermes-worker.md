Role: Worker

# Worker: Ask Secret capability contract and harness instructions

Status: todo
Harness: unknown (legacy; not recorded)
PID: unknown (legacy; not recorded)
Agent session: unknown (legacy; not recorded)
PID status: unknown (legacy)
Last PID signal (UTC+3): unknown (legacy; not recorded)
Last task-file transition (UTC+3): unknown (legacy; filename was todo-)
Started at (UTC+3): unknown (legacy; cannot infer from mtime)
Lifecycle provenance: legacy-missing; audited 2026-08-10
Last task-file mtime observed (UTC+3): 2026-08-07 19:00:12 +0300 (last write observed, not start)

Goal: make Ask Secret an explicit required agent behavior for Codex and Hermes,
with SSS as the named transport and fail-closed opaque-handoff semantics.

Known facts: `human.ask_secret.v1` is currently planned; Codex has SSS MCP;
Hermes profile will receive SSS separately. SSS `get_secret` without
`agent_id` has a base64 fallback and must not be accepted for this flow.

Allowed write paths: `/home/roomhacker/agents-projects/LastHumanCommit/src/common/capabilities/**`,
`/home/roomhacker/agents-projects/LastHumanCommit/src/common/agents/Lead.md`,
`/home/roomhacker/agents-projects/LastHumanCommit/adapters/codex/**`, and
focused tests/docs directly covering those files. Do not edit Hermes adapter
profile files or Fleet code.

Acceptance: exact concise instruction says when a secret/password is needed,
call Ask Secret/SSS, never Clarify or ordinary user question; require the
opaque/registered-agent path and reject plaintext/base64 fallback. The
capability descriptor and Codex adapter must reflect the live contract without
claiming unproven attestation. Append evidence here and return L only TL;DR.

Excluded: SSS server source, secrets, runtime config, deployment, restart,
Notify/resume implementation, and unrelated security architecture.

Estimate active minutes: 10 / 20 / 35. Stop if the contract cannot honestly
claim live support; state the remaining Fleet attestation boundary.

Progress:
- Updated `src/common/capabilities/human.ask_secret.v1.yaml` to make Ask Secret
  required in the contract text, require a registered-agent SSS opaque
  handoff, and explicitly reject plaintext/base64 fallback for LLM-facing
  flows.
- Updated `adapters/codex/instructions.md` so Codex routes secret/password
  requests through Ask Secret/SSS instead of Clarify or an ordinary user
  question.
- Updated `adapters/codex/adapter.yaml` with an explicit
  `ask_secret_transport: sss-opaque-registered-agent` contract note while
  leaving the proof fields unclaimed.
- Updated `src/common/agents/Lead.md` with the same Ask Secret / SSS / no
  fallback instruction for the root agent path.

Verification:
- `python` + `yaml.safe_load` parsed both edited YAML files successfully.
- Reviewed the diff for scope drift; no Hermes adapter profile files, Fleet
  code, secrets, runtime config, or deployment paths were touched.

Remaining boundary:
- Fleet/runtime attestation for live Ask Secret rendering is still not proven
  here; `human.ask_secret.v1` remains `planned` and must not be rendered as a
  live capability until Fleet attests it.
