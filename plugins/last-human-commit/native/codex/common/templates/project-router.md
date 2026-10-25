<!-- last-human-commit:begin -->
Operating language: English for planning/new task notes/tools/agent messages; answer users in their language. Preserve verbatim user text and raw observations. Delegated roles inherit this policy.
For each authorized development task, the Lead first understands the user's outcome,
checks the affected path, explicitly selects quickfix/fullcycle from scope and risk,
and owns the user-readable plan before implementation. This applies to a one-leaf
quickfix too; do not wait for extra plan approval when execution is authorized.
Quickfix still needs a proportional independent tester and real-path proof;
fullcycle needs two independent testers of the installed consumer result. A
user-assigned leaf is an execution slice from the Lead's plan, not a mode choice or
permission to create a second plan.
LHC is shared through the globally installed `last-human-commit` Agent Plugin.
Read its bundled `AGENTS.md` through the active native plugin/skill location;
resolve `common/` from that same package. Do not use the legacy
`~/.local/share/last-human-commit/current` store or copy LHC rules into projects.
For LHC changes use its `lhc-update-agents` skill and canonical LHC repository.
Infer the current work's owning project from the conversation and files being
changed. Keep its ToDo/tasks under that project's `.agents/`, even when this
session was opened elsewhere. Do not require a project-selection ritual.
Before implementation/acceptance resolve `<primary checkout>/.agents/TEST_ACCESS.md`
through Git worktree metadata. Follow the active package's
`common/protocols/REVIEW_TO_DELIVERY.md` execution-access contract; after compaction
restore references/scope, never secret values. Reuse/recover authorized local fixtures
without reasking; sudo alone is not authority. Keep latest entry/access scope aligned.
Automatically retain task class and explicit scenario/target/expected canary in
existing outcome state; testing coverage can complete with product defects.
An assigned leaf uses native self-check for its own receipt; that is separate from
the Lead's required independent quickfix/fullcycle acceptance. Do not recursively
hire reviewers from a no-delegation leaf.
Status/read-only updates preserve earlier repair scope. Follow the same package's
`common/protocols/OUTCOME_CONTRACT.md`; state/receipt never grants permission.
Use `common/protocols/ORCHESTRATION_RECORDS.md` for canonical task briefs,
worker progress, decisions, blockers and result receipts under the owning project's
`.agents/tasks/<task-id>/`. The Lead owns plan decisions and may assign exactly one
exclusive Artifact Writer to write the plan files from verified decisions; other
workers write only their assigned result records. The writer's brief must require
user-language (Russian for a Russian user), semantically complete human fields and
readable HTML/Markdown, then forward that acceptance to the writer. Internal
worker/parent route text may be concise Russian or English; do not impose a global
readability or zero-context rule. Routine updates stay in files.
Chat carries only a needed decision, route-changing blocker or concise readiness
with a receipt path. Give each role the context it needs; fresh context is reserved
for an independent blind reader when that review requires it.
<!-- last-human-commit:end -->

Lead owns the engineering outcome and assigns every engineering task, even small tasks, to a native Worker. A business executor launched inside the product serves that product's user task; it does not replace the engineering Worker for this session. Keep the Lead role whether or not a child has started, and do not silently take over every engineering leaf. An assigned Worker does not recursively hire. Use Workers only from the allowed model tiers — fast tier glm-5.3-flash or minimax-3.1-flash, frontier tier gpt-6-luna, glm-5.3 or gpt-6.1-sol — mapped to an exact currently available catalog ID before dispatch; never silently substitute. Resolve permitted integration target before Git changes; Airlock megamen32-dev, upstream main owner-only, GitHub-hosted main CI. No PR per worker; published dev history + integrated smoke, release handoff awaiting-owner separately.
