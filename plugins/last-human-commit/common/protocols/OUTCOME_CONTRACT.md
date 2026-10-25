# Ordinary task → observable outcome

## Expected result and evidence of achievement

The plan's `goal` states the user's purpose. Its `business_result` or
`business_results` declares future tangible capabilities after the changes,
shown as «Что будет работать». Keep those storage names and accept the legacy
Markdown heading «Бизнес-результат». Optional `acceptance_scenarios` is a
`list[str]`: actor/context, actions, expected visible result. These are real
scenarios for testers, not expected verdicts. See `PLAN_REPORT.md` for examples.
For CLI/library work the user is the operator/caller and the scenario names the
actual call and observable result; a commercial benefit is not required.

`current_progress` records what is actually done or checked now. Evidence of
source/tests, commits, installation and real use retains its own scope; none
replaces the expected capability. An unfulfilled expected result is a valid plan,
while a claim of achievement requires evidence of the real affected scenario.
Use this meaning for updated/new plans; do not rewrite historical reports,
revisions or user messages. Old fields remain legacy declarations, never inferred
fulfillment. This documentation contract adds no regex classifier, runtime state
transition or gate.

## Recording the accepted assignment

The Lead may record each actionable assignment through the existing outcome CLI,
including its class and a concrete canary: scenario, actual consumer target/host,
expected observation. The Lead derives that record from the user's authority and
latest direct corrections. LHC does not classify ordinary messages or mutate the
contract, evidence floor, stages or holds from acknowledgements, status, agent
reports, tool events or hook prompts. Native startup hooks provide current
instructions and tool paths only; they do not create task state. Time-only
PostToolUse reminders may fire at 30/60 minutes. They may read elapsed time only;
they must not interpret message language, infer a task, mutate state or veto Stop.
The Lead owns task-note updates: initial/revised estimate and reason, actual active
versus wall-clock elapsed time, next ~15-minute tasks/owners/dependencies and parallel
opportunities. At 60 minutes the Lead also checks the original goal and business result.
User updates report material progress, not every timer reminder.
The Lead's plan, briefs, worker progress, decisions, blockers and result receipts
live in the owning task directory under `ORCHESTRATION_RECORDS.md`; outcome state
does not replace those human-readable records.
For authorized development, the Lead first researches enough to understand the
user's intended outcome and affected path, selects `quickfix` or `fullcycle` from
actual scope and risk, and creates the human-readable plan before implementation.
The plan states what a person will get, what changes, why it matters, and how to
check it. A quickfix still needs a proportional independent tester and real-path
proof; a fullcycle needs two independent testers of the installed consumer result.
A worker's assigned leaf narrows its execution scope but cannot select the parent
mode or waive the Lead-owned plan. The Lead may assign one named Planner exclusive
artifact writing from verified Lead decisions; this does not transfer plan
decision authority. A human-readable outcome is a separate claim
from test status, source publication, package installation, runtime state, and
consumer acceptance. Do not wait for a second plan approval when the user's
execution authority is already clear.
Quickfix needs focused RED/fix/GREEN and its real narrow canary; fullcycle also
needs applicable deployment and publication. Testing completes assigned coverage
and candid raw observations, including a product defect; it does not require code,
deploy or another tester. Research needs its verified finding, status only its
answer. A later read-only/status question never cancels earlier repair obligations.
Only an explicit direct replacement changes scope; preserve its source/lineage.
Keep administrative transport separate from task semantics. A status question,
acknowledgement, duplicate, agent report or review handoff cannot by itself clear
a stop, replace the task, advance the evidence floor or erase accepted progress.
Preserve the original observations and later negative findings. Reuse an accepted
proof only while its actual subject, candidate, scenario and relevant environment
remain valid; an administrative timestamp is not a product change. A substantive
requirement change reopens the affected checks and their dependent claims.
An evidence-format rejection requires repairing the supported binding, not
repeating a deployment, publication or other already accepted external action.

For a research `project:<cwd>` canary, the source floor supports one direct `cat`
read of a file explicitly named in the accepted scope. Relative and absolute forms
resolve to the same source without changing clocks or evidence freshness. Foreign
cwd/files, bare stems, ambiguous files, echo and compound commands do not qualify.
An unsupported read format may use one actual direct reread; research does not
need Python execution, tests or delivery merely to close its finding.
The requested FEEDBACK output is not that source; an explicitly researched
FEEDBACK product document remains eligible. Later helper progress is not a new
assessment: preserve the actual finding's original time and evidence window.
For the bounded encoding finding, requested FEEDBACK readback and explicit limits
on proving implementation/tests → deploy → merge, an own research report may use
`review --native-self --comparison-quote '<unchanged passage>'`. This narrow typed
mapping requires the original report to name the source, actual encoding and
negative proof limits; current native source and FEEDBACK reads must precede it.
The original canary hash, report index/time and call references are recorded.
This is self-check, never independent parent acceptance or a general translation
parser. Source/revision gates remain; a newer negative finding cannot be skipped.
Unsupported or additional expected predicates stay pending; no charset blacklist
or repeated unchanged read can replace their actual comparison.
Use the existing independent reviewer for unsupported prose: its native assignment
must identify this outcome, original scope and exact case directory as
`Target CWD: <absolute path>` (line or semicolon-delimited field). A reviewer
starting in the canonical project may use explicit native tool workdirs to read
the case. Omitted or relative workdirs resolve against its actual native cwd,
never the target cwd; neighboring/ambiguous directory declarations do not match.
This is independent review of the bounded finding, not parent product acceptance
or permission to resume a held session.
For an existing Codex research or engineering reviewer whose full native journal exceeds the
bounded reader, use `review --native-reviewer CODEX_SESSION_ID`. This reads the
original native header and contiguous current-assignment tail through actual EOF;
the same size cap, source identity, original line indexes/times and later negative
findings still apply. It never creates/resumes a session or rewrites its assessment.
If the journal advances, refresh the snapshot, not the report or evidence clocks.

The existing optional outcome CLI stores `business.outcome` in the existing learning
JSON. It survives compaction and keeps the Lead's recorded scope, owner and clocks.
When useful, the Lead records a concrete contract with the existing command (this is
not a required message format or an interview):

```sh
python3 <package>/tools/lhc_outcome.py --cwd <project> --runtime codex --session-id <native-id> contract \
  --scenario 'Empty basket total' --target 'python3 total.py' --expected '0' \
  --owned-path total.py
```

Class is a hypothesis: Lead may correct it with `--task-class <class>` and
`--scope-source <exact native user source from status>`; no permission comes from
this record. Explicit `--require-stage` adds an applicable obligation;
`--not-applicable` requires an explicit original/latest exclusion, not lack of
access. Direct repair corrections add stages/target while keeping owner/lineage
and clocks; a status/read-only question cannot erase confirmed repair.

### Source-only publication

For an assignment that explicitly delivers source files, select
`contract --verification-kind source-publication` with its exact native
`--scope-source`, canonical `project:<product-root>` target and every owned path.
The flag does not turn application work into source-only work or grant access.
The native assignment must bind the actual source-only task, product and files.
Keep repository, remote and destination branch explicit; an arrow suffix in a
project label is not a Git publication contract or permission.

Bind them with the existing integration remote/branch/ownership fields and
`--stage-target 'publication=git ls-remote origin refs/heads/main'
--stage-expected publication=candidate` for the selected `origin/main` case.
The `candidate` expectation is fixed from the current remote base, repository,
destination ref and owned-file hashes. The future commit SHA is established by
the actual publication readback; it is not guessed before readiness or inserted
through a later contract edit that would reset the review floor.

In this mode, independent technical readiness means reviewing the actual current
owned source and matching its immutable candidate hashes. It does not require a
Python CLI or credit source inspection as an executed application test. Runtime
consumer/deploy stages are excluded only by that explicit source-only scope.
Byte-identical candidate files may share one complete body read, with an explicit
alias mapping and separate native hash evidence for every owned pathname. Large
bodies use ordered gapless bounded reads through EOF. Below the native persistence
cap, complete assembled candidate bytes decide completeness; source text resembling
a truncation marker is data. Missing/cropped bytes and hash mismatches still fail.
Earlier independently accepted exact-candidate readiness may be revalidated from
its original manifest and call references for a publication-only continuation.
Preserve its reviewer and observation times; recheck current publication permission,
negative findings and remote identity. Source equivalence grants no runtime proof.
Readiness leaves publication pending. Publication requires the authorized normal
Git operation and native readback linking the actual remote commit, parent/base,
owned delta and every candidate blob to the bound repository and branch. A branch
SHA alone, an author PASS or repository write access does not establish this.

An explicit native publish/push directive is scoped to that publication operation;
it does not become merge, force-push, deployment or foreign-source permission.
Keep HumanStop, revocations and UNKNOWN prior operations. A changed verification
contract gets its actual new evidence floor; do not backdate or rewrite an earlier
review. Source-artifact acceptance never claims runtime or parent consumer PASS.

For an assigned product in another checkout, keep `--cwd` at the native session
root and add `contract --product-root <canonical-product-checkout>
--scope-source <original-native-assignment-ref> --owned-path <product-relative-file>`.
The original assignment must bind that root and the exact owned files. An archived
brief explicitly named by the assignment may supply those files through its
original, successful, attributable native read; its current mutable content is
not a substitute. The execution report in the parent checkout is metadata, not
product ownership. One product root is supported per bounded outcome.

Owned-source hashes, target resolution and Git remote checks use the product root;
session state and native transcript identity stay at the original `--cwd`.
Actual tool workdirs must identify the product checkout. An omitted workdir keeps
the reviewer's actual native cwd and is never silently rebased to the product.
Changing roots invalidates prior acceptance normally; this does not backdate
evidence, supply missing reviewer provenance or accept a parent consumer canary.
Missing session state is an explicit error; changing `--cwd` does not move a task.

### Agent-origin task relays

Agent Herder's `new_or_resume` and `deliver` paths prefix relayed task messages
with this transport marker, followed by the caller's unchanged task text:

```text
🤖 Сообщение от ИИ через Agent Herder
<agent-herder-origin version="1" kind="agent-relay" transport="new_or_resume" />
```

The `deliver` path uses the same marker with `transport="deliver"`.

LHC detects the marker from the raw native input before applying source excerpt
bounds, records the source origin as `agent-relay`, and removes the leading prolog
only from the derived task-scope view. Native prompt evidence remains unchanged;
the full-source reference/hash is computed from the original message. The legacy
Agent Herder prefix without the XML marker remains recognized for existing relays.
An initial delegated task still creates the ordinary LHC outcome from its task
body and follows the existing mandate and permission gates.

The explicit marker or a supported leading legacy header establishes
`agent-relay`. An unmarked origin stays
`unknown`; it is not promoted to human identity. Neither value authenticates a
human or grants execution permission. The transport label does not expand task
scope or bypass existing stop, permission, ownership, or stage gates.

Native Codex children keep their logical LHC state ID distinct from the actual
native journal ID. A verified composite and bare child ID identify the same actor,
never independent reviewers. Future pre-call task capture is only an intent until
the exact parent call, successful child receipt and actual child journal header
agree. Store it in the parent's protected existing dispatch records; child readers
revalidate that source without modifying parent state. A bound initial assignment
can enter at a native work boundary without inventing a user prompt. Its source
remains `native-parent-dispatch`, with agent origin and actual call/hash/time refs.
Missing or encrypted historical text stays unavailable; inherited AGENTS, task
names, timing proximity and an old summary cannot supply the missing assignment.

### Reassigned worker and reviewer lineage

A native review stays bound to its actual current subject before observations.
The legacy assignment contains the outcome ID, full original goal and accepted
corrections. The bounded assignment instead contains the current versioned review
subject digest, outcome ID and readable exact product root, scenario and expected
result. The digest identifies the current contract and candidate; it grants no
authority and cannot authenticate the sender. Discovery and acceptance use the
same assignment check. A preview, arbitrary link or retrospective assignment is
not that binding. Missing binding names the exact fact to repair; it does not
require a replacement worker merely because the transport format was unsuitable.

When a worker's authorized mandate changes
from an earlier research assignment to implementation or publication, do not
rebind the old outcome or make an earlier reviewer report appear current. Use the
existing authorized native task-dispatch route to start a **new worker session**
with the actual current mandate, repository/root, exact owned paths, and publication
scope. Its ordinary native entry creates a fresh outcome; confirm the concrete
contract with the existing `contract` command in that new session's original
`--cwd`. There is no same-session reassignment CLI that grants authority or rewrites
outcome identity.

Assign the already-selected independent reviewer anew in its native task session.
That assignment must bind the fresh outcome with the current subject or legacy
full-goal assignment described above. The reviewer
must make a fresh source assessment from current native reads and hash comparisons
after the new evidence floor. This bounded source review does not replay product,
provider, or deployment work and does not establish a product canary, publication,
or C2 PASS. Native source pairing, source-call cutoff, assessment time, later
negative findings, and stage gates remain unchanged.

The predecessor outcome and any older reviewer report stay in history with their
original pending state. Do not rewrite or backdate them, carry their PASS/evidence/
permission into the new task, clear UNKNOWN work or existing native holds, or reset
the session clocks. The new reviewer assignment does not broaden the mandate or
remove no-code, ownership, or scope restrictions. The historical H32 research
outcome and reviews that lack its exact assignment binding remain pending; a fresh
task cannot retroactively accept H32.

Before the first testing consumer call, confirm repeated `--coverage '<assigned scenario>'`;
name the exact expected/observed result and each assigned scenario in the native report.
Use owned paths only when they bind the product bytes under review; they grant no write permission.
Keep previous receipts as history. One fresh harmless read-only check may verify
corrected setup; never repeat deployments, sends or UNKNOWN operations merely to refresh a timestamp.
For fullcycle, the applicable sequence is implementation/tests → authorized deploy
→ hands-on/applicable independent acceptance → publication/integration into the
configured permitted dev branch → integrated smoke. PR per worker is optional;
one published dev history is mandatory. Explicit original no-deploy/no-push/external PR-only boundaries make only
those operations N/A, with their scope source retained. Missing required access
is blocked, not N/A. State does not grant permission. Airlock converges on
`megamen32-dev`; Oleg owns final upstream main integration for those projects.
That rule does not apply to the owner-controlled `megamen32/LastHumanCommit` repo:
the user's direct scoped instruction authorizes an ordinary fast-forward of its
`main`, after the relevant checks. External/shared upstream main remains owner-only.
Main CI stays GitHub-hosted,
not ARC/K3s; do not change GitHub App privileges, checks or branch protection. Local checkpoint commits may precede deployment. A genuine CI
branch-push dependency may precede deployment only as a recorded staging-push
exception (branch, reason, dependent stage, native refs); it is not final acceptance.

## Review and delivery

Use review when it can find a real defect, missing check, or release risk. The Lead
arranges any needed independent reviewer or tester autonomously; do not wait for a
human to appoint one unless a real human decision is missing. Scale review to the
risk and claim. A concrete defect blocks the affected release until fixed and
rechecked. An absent review receipt, manifest, identity registration, or LHC ledger
record is not itself a delivery blocker.

An ordinary native reviewer response is usable evidence when it identifies the
scope/revision examined, observations, findings, and limits. Record that evidence
in the existing task notes or optional outcome ledger when useful. Do not require
transcript exports, full-file captures, literal task/session ID pairing, fresh
sessions, or replay solely to repair metadata chronology. Preserve the original
reviewer response and any negative finding; never promote missing or ambiguous
coverage to PASS. The existing `review --manifest` command remains an optional
ledger import path, not a release veto.

A bounded assignment may report its own work and observations, but this does not
accept a broader parent outcome. Independent review or user-path testing remains
appropriate where the size, ambiguity, or release risk warrants it. Verify only
the affected scope after a change. Preserve source/revision limits, actual canary
requirements, and unknown evidence honestly.

The optional outcome record remains useful for scope, owner, canary, clocks,
stages and honest complete/pending/running/blocked/human-stopped status. It does
not create authority or permission. A status question cannot erase confirmed
repair obligations. Keep HumanStop, revocation, unauthorized actions, and accepted
or UNKNOWN external operations protected. Never replay an accepted or uncertain
send, purchase, deployment, or other external action to refresh evidence.

## Stop and questions

The optional outcome record uses complete/pending/running/blocked/human-stopped
verdicts; only proven applicable stages support a recorded completion. LHC hooks do
not infer a Stop veto, continuation, hold or permission from ordinary messages, tool
events or status. Obey the harness/platform's actual stop and permission decisions.
The Lead decides whether user authority permits continuation and records task
progress through the existing CLI. Human stops, permission limits, accepted/UNKNOWN
external work and job IDs remain protected. No new daemon, cron or schedule.

For optional Notice Place/UserIO ownership, follow `COORDINATION.md` and
`commands/askhuman.md`: one policy request, account-scoped universal transport,
canonical confirmed answer and exact-session resume. The existing delivery/answer
source floors below describe supported receipt forms, not migration or interactive
voice/question support across every provider. Quiet hours and declared account/channel
capabilities remain; agents must not invent direct bot/ADB/socket/SIP fallbacks.

A real unresolved human decision uses `lhc_outcome.py ... question --message '...'`:
this persists one question identity and selects existing Herder binding → bound
Notice question → actual sent receipt → canonical answer in the same native
session. Repeated calls inspect the same pending request. No network side effect
runs in a Stop hook. Follow `commands/askhuman.md`; queued/unknown is not delivered,
delivered is not answered, answered is not permission. The official HTTP response
uses ask_human.response.v1 with native_harness/native_session_id/native_cwd and
nested telegram.status/message_id; both it and MCP require the exact binding.
Flat status/receipt strings are not supported delivery proofs. Missing configured actors
or project is a scoped blocker. Never invent an incident/recipient, autoaccept,
store secret answers, or promise unproved standalone phone escalation.

The Notify MCP uses flattened harness/session_id/cwd arguments (HTTP instead
uses native_target). MCP card=sent is source-backed send status but omits the
provider message ID; preserve that limitation. Canonical ask_human.result.v1 has
state=resolved plus exact native target/result_ref. Never store its answer value
in the outcome ledger or interpret that state as permission.

The HTTP floor supports direct native curl POST and exact request-result GET at
the endpoint from existing ASK_HUMAN_URL or LHC_ASKHUMAN_MCP_URL configuration,
captured before the attempt. Echo/printf, shell wrappers/compound commands,
write-out JSON, redirects and foreign endpoints are not Notify provenance.
Unknown HTTP clients/configuration use the existing native MCP path; schema text
alone cannot establish delivery or a human answer. No live roundtrip is implied.


## Explicit dev target and separate release handoff

Lead resolves the permitted integration branch, remote and ownership against the
native user scope/project rules before Git mutations. Unknown target/ownership
never means main. Record this mapping with the existing contract, not a second
Git controller; the record itself grants no permission:

`contract ... --scope-source <native-user-source> --integration-branch megamen32-dev --integration-remote origin --integration-ownership shared --release-owner Oleg`

For an owned LHC repository, a direct owner instruction to integrate its `main`
is valid authorization; do not turn the Oleg/Airlock owner rule into a prohibition
against the repository owner. When using the integration helper, record the exact
native user clause with `--integration-permission-quote`; `owned` or GH write access
alone is not consent. The helper resolves the actual remote repository, binds it to
this scope and rejects changed remotes. Missing/ambiguous consent stays pending/owner handoff;
this is a bounded source floor plus independent semantic review, not a universal
intent/permission parser. Only GitHub remotes are currently supported for this
automatic integration close. Dev branch names must be confirmed by native scope;
unknown targets never inherit main. Shared/external main is rejected. Airlock worktrees
branch from and converge on megamen32-dev; that route and Oleg's ownership do not
override direct owner authorization in LastHumanCommit itself. Final upstream main PR
is only the agreed handoff for Airlock work. Lead owns the engineering outcome and
assigns every engineering step, including small tasks, to a native Worker. A
business executor inside the product being built handles that product's user task;
it is not the engineering Worker for this session. The Lead role does not depend on
whether a child has started and must not silently switch into doing every engineering
step personally. Add an independent Reviewer only when the claim and risk warrant it. An
already assigned leaf does not recursively hire and its self-check remains separate
from parent acceptance.

Integration readback must bind the configured branch/head: `git ls-remote origin
refs/heads/megamen32-dev`, with the expected SHA, or a merged PR readback including
`baseRefName`. Publication can use branch history without a per-worker PR. Every non-main dev
integration requires actual integrated consumer smoke after that readback,
whether or not the optional release-owner name was supplied,
covered in the same original review's integration evidence calls. Canary and
permitted dev delivery can then be complete while `release_handoff.status` is
`awaiting-owner`; Oleg's future Airlock main action is not an unmet dev task.
Missing dev publication/smoke stays pending. Neither refs nor handoff bypass
independent milestone, human-stop, external-action or authorization gates.
Use the existing HQ workspace validation (`go run ./automation/cmd/hq validate
workspace --root "$PWD"`) only in its actual owning checkout after inspecting
scripts/ownership; local green never guarantees GitHub approval.
