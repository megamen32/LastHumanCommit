Role: Explorer

# Hermes installation and Ask Secret capability implementation

Status: work
Harness: unknown (legacy; not recorded)
PID: unknown (legacy; not recorded)
Agent session: unknown (legacy; not recorded)
PID status: unknown (legacy)
Last PID signal (UTC+3): unknown (legacy; not recorded)
Last task-file transition (UTC+3): unknown (legacy; filename was todo-)
Started at (UTC+3): unknown (legacy; cannot infer from mtime)
Lifecycle provenance: legacy-missing; audited 2026-08-10
Last task-file mtime observed (UTC+3): 2026-08-07 19:22:29 +0300 (last write observed, not start)

Original request: исследовать минимальную установку LHC в Hermes и исправить
совместимость Ask Secret так, чтобы Codex и Hermes реально могли запросить
секрет через SSS.

Objective: Fleet создаёт отдельный Hermes-профиль `LHC` из default, заменяет
native `clarify` на AskHuman для обычных вопросов, а секретный flow — на LHC `Ask Secret`, подключает SSS и доводит Ask Secret до
рабочего результата минимум в Codex и Hermes.

Business canary: после установки LHC Hermes запускается с профилем
`~/.hermes/profiles/lhc`, его native prompt содержит LHC и не предлагает
AskHuman для обычных вопросов и native `clarify` отключён; Codex и Hermes имеют доступный Ask Secret путь через SSS, который
возвращает только opaque request/handle и не помещает plaintext в
prompt/output/task/argv.

Confirmed scope: read-only investigation of
`/home/roomhacker/agents-projects/LastHumanCommit/adapters/**`,
`/home/roomhacker/agents-projects/LastHumanCommit/src/common/capabilities/**`,
`/home/roomhacker/agents-projects/LastHumanCommit/docs/**`,
`/home/roomhacker/agents-projects/agent-harness-fleet/catalog/skills/lhc-rollout/**`,
and Hermes native evidence under `/home/roomhacker/.hermes/SOUL.md`,
`/home/roomhacker/.hermes/config.yaml`, and installed plugin paths.

Explicit exclusions: no Hermes core-source edits, no default-profile mutation,
no auth/session/secret-store copying, no service restart or production deploy,
no broad Notify/resume redesign beyond preserving the future callback seam.

Initial estimate (active minutes): optimistic 15 / likely 25 / pessimistic 40.
Stop when: exact native file, current capability gaps, and smallest file-level
change set are evidenced.
Abandon when: evidence requires Hermes core-source drift or a new runtime owner;
report that boundary instead of inventing an adapter.

## Explorer evidence (2026-08-07)

### Findings

- Hermes native prompt surface is `~/.hermes/SOUL.md`; it contains the base
  Hermes identity and Notify rules at lines 1-11, but no LHC block. Both the
  effective global config and the `luna` profile have `agent.system_prompt: ''`
  (`~/.hermes/config.yaml:1574-1578`, `~/.hermes/profiles/luna/config.yaml:1574-1578`).
  The selected default preset is `hermes100-omniroute`
  (`~/.hermes/config.yaml:1730`, profile config:1740), not an LHC profile.
- The Hermes LHC plugin is enabled in `~/.hermes/config.yaml:1950-1957` and
  installed at `~/.hermes/plugins/last-human-commit`. SHA-256 of the four
  installed plugin files matches `LastHumanCommit/adapters/hermes/plugin/*`.
  Its only registered hook is `tool_request`; `register()` in
  `adapters/hermes/plugin/__init__.py:128-129` registers
  `rewrite_delegate_task`, which rewrites only `delegate_task` payloads
  (`__init__.py:100-126`). Therefore plugin installation proves delegated-role
  injection only, not default-profile delivery.
- The canonical adapter explicitly records this boundary:
  `adapters/hermes/adapter.yaml:7-15` says `delivery: tool-request-middleware`,
  `native_role_profile: unsupported`, `fresh_child_context: proven`, and
  `resume_transport: adapter-dependent`. `adapters/hermes/VERIFICATION.md:5-19`
  confirms plugin discovery and middleware smoke evidence but excludes live
  child/provider/resume proof.
- Fleet rollout manifest copies only the external Hermes plugin, not a Hermes
  SOUL/profile file: `agent-harness-fleet/catalog/skills/lhc-rollout/assets/
  last-human-commit-fleet.json:17,20,76` (`copies.hermes` and target copy).
  The rollout skill requires a physical harness canary reading the installed
  router/role file (`SKILL.md:41-43`), but no Ask Secret capability attestation
  is present in the manifest.

### Ask Secret / SSS gaps

- LHC's descriptor is explicitly planned: `src/common/capabilities/
  human.ask_secret.v1.yaml:2-14` has `state: planned` and says rendering is
  allowed only after exact Fleet/harness attestation. The policy repeats that
  Ask User/Ask Secret is not installed (`docs/human-request-capabilities.md:5-8`)
  and Fleet owns resolution, transport, and attestation (`:11-18,40-42`).
- Codex has an SSS MCP registration at `~/.codex/config.toml:148-150`, plus
  `agent_resume` at `:136-142`; this is an available transport surface, but
  `adapters/codex/adapter.yaml:7-15` still marks native role, fresh context,
  model, and resume as unproven. There is no LHC Ask Secret renderer or
  attestation in the Codex adapter.
- Hermes has `notify` MCP (`~/.hermes/config.yaml:1888-1892`),
  `agent-resume`/`wait-for-user-notify` plugins (`:1950-1965`), and
  `wait_for_user_notify` config (`:2017-2020`), but no `sss` MCP entry anywhere
  in its config. Thus Hermes cannot currently invoke SSS through its native
  agent-facing tool surface.
- SSS itself has a `get_secret` MCP tool (`simple-secret-storage/src/server.ts:
  73-130`) and supports a pending human-entry URL plus opaque `request_id`
  (`:84-100`). However, if `agent_id` is omitted it intentionally returns a
  base64 delivery path and warns that SSS sees plaintext (`:104-127`). The SSS
  documentation says this is not acceptable for LLM-facing Ask Secret and
  requires registered-agent encrypted delivery or safe non-LLM handoff
  (`simple-secret-storage/docs/human-request.md:7-14,24-34,64-75`).
- SSS completion callback is only optional best-effort metadata POST to the
  fixed Agent Herder endpoint, with UUID `request_id` and `result_ref` and no
  secret (`simple-secret-storage/src/completion-callback.ts:6-17,20-39`; docs
  `human-request.md:44-62`). The docs explicitly call Notify, agent-resume,
  and Herder integration proposed orchestration, not current SSS behavior
  (`:36-42`). Existing Herder resume tests prove opaque `sss://` refs can be
  forwarded, including Hermes locator validation, but this is test/transport
  support, not an Ask Secret request entrypoint (`agent-herder/tests/
  resume-transport.test.ts:4-20,50-86`).

### Minimal bounded implementation scope

1. Fleet/runtime owner: add a fail-closed Ask Secret capability adapter and
   live attestation for both Codex and Hermes. The adapter must create/correlate
   an opaque request, call SSS with a registered agent identity, and expose only
   `request_id/state/opaque_handle`; it must not return SSS base64/plaintext.
2. Hermes integration: register the existing SSS MCP endpoint in Hermes through
   supported config/plugin seams and add only a small agent-facing Ask Secret
   instruction fragment to the native/default profile delivery path, or prove
   an equivalent supported profile seam. Do not edit Hermes core source or
   pretend the existing LHC middleware changes the default prompt.
3. Codex integration: retain the existing SSS MCP registration but add the
   capability fragment/attestation and a registered `agent_id`/opaque handoff;
   the current LHC adapter file alone cannot provide this.
4. Orchestration: wire the already-existing fixed SSS completion event to the
   selected Notify and agent-resume owner only after request ownership and
   correlated opaque `result_ref` are attested. This is outside LHC core and
   should remain Fleet/Agent Herder-owned.

### Red/green canary for implementation

- Red (current): from a fresh default Hermes session, ask for an LHC role rule
  and inspect the effective native prompt: no LHC text; ask Hermes to invoke
  `get_secret`: no SSS tool exists. In Codex, the SSS server is configured but
  no `human.ask_secret.v1` attestation/renderer exists; an unregistered-agent
  call must be rejected rather than accepting the base64 fallback.
- Green: fresh default Hermes and Codex sessions each render the current,
  attested Ask Secret fragment; a named-secret request yields only opaque
  request metadata/handle, human completion reaches the fixed callback, and
  resume/notification uses the correlated opaque ref. Assert no secret value
  occurs in prompt, tool output, task file, argv, environment, or logs; assert
  Hermes delegated LHC role injection and existing Codex behavior remain intact.

### Exclusions / risks / next probe

Checked only the task-confirmed LHC, Hermes, Fleet rollout, and SSS/Herder
evidence; did not inspect secret values, restart services, deploy, or modify
runtime/source. Main risk is source ownership: capability resolution,
registered-agent cryptographic delivery, Notify timing, and resume transport
cannot be implemented safely inside LHC or by editing Hermes core. Highest-value
next probe is a read-only inventory of the actual SSS MCP `register_agent`/key
and Agent Herder human-request endpoints, followed by a focused plugin-only
canary to determine whether Hermes can load SSS through config without core
changes.
Forbidden without explicit user request: restart, deployment, rollback,
credential changes, secret inspection, or modifying runtime files.

Acceptance/report: append detailed evidence to this file; return L only a TL;DR.
Include exact files, current behavior, missing edges, and a minimal red/green
canary for the eventual implementation. Do not create plans or edit files.

## Implementation correction and evidence (2026-08-07)

User clarified the final semantics: native Hermes `clarify` is replaced by
AskHuman for ordinary questions; AskSecret/SSS is a separate path for secrets.
The LHC bundle and Fleet overlay were corrected accordingly. AskSecret remains
fail-closed and only accepts opaque registered-agent delivery; no plaintext or
base64 fallback is claimed. Hermes profile rollout is implemented in Fleet but
has not been applied to a live host in this pass.
