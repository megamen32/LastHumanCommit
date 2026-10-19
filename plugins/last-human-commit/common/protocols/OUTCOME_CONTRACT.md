# Ordinary task → observable outcome

Every actionable engineering/testing assignment has an automatic class and a
concrete canary: scenario, actual consumer target/host, expected observation.
Classification is a hint from the full accepted scope, not a permission engine.
Quickfix needs focused RED/fix/GREEN and its real narrow canary; fullcycle also
needs applicable deployment and publication. Testing completes assigned coverage
and candid raw observations, including a product defect; it does not require code,
deploy or another tester. Research needs its verified finding, status only its
answer. A later read-only/status question never cancels earlier repair obligations.
Only an explicit direct replacement changes scope; preserve its source/lineage.

The existing native entry stores `business.outcome` in the existing learning JSON.
It survives compaction and keeps original/latest corrections, owner and clocks.
Before work, concretize the automatically captured contract (not a mode interview):

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

For testing add repeated `--coverage '<assigned scenario>'` and omit owned paths.
For fullcycle, the applicable sequence is implementation/tests → authorized deploy
→ hands-on/applicable independent acceptance → final push/PR → permitted owned
merge. Explicit original no-deploy/no-push/external PR-only boundaries make only
those operations N/A, with their scope source retained. Missing required access
is blocked, not N/A. State does not grant permission. Never merge Airlock main
under an LHC task. Local checkpoint commits may precede deployment. A genuine CI
branch-push dependency may precede deployment only as a recorded staging-push
exception (branch, reason, dependent stage, native refs); it is not final acceptance.

## Source-backed assignment close and independent milestone acceptance

A bounded quickfix with a direct no-delegation restriction and no applicable
deploy/publication/integration stages may close its own assignment with native
technical tests and actual CLI/consumer observations plus original expected-vs-
observed feedback. Export its own transcript and use the same `review --manifest`
route below; no author-supplied PASS file or weaker provenance path is added.
The stored level is `self-check`, never independent product acceptance. Preserve
raw FEEDBACK and limitations. Worker/testing/research assignment completion does
not accept the broader parent outcome. Fullcycle and pending milestone acceptance
retain their independent gates. A no-delegation restriction never authorizes a
new reviewer session: hand off finished work to the assigned coordinator when
independent acceptance remains required; do not create a review loop to close state.

Use an existing independent reviewer for the actual accepted canary, target and
owned revision. One review can cover several stages/scenarios. Pass original accepted scope/latest corrections, outcome id,
canary and current revision from `status`; preserve ordinary raw feedback and
expected-vs-observed reasoning. An unchanged ordinary native report can close the
assignment: the helper derives bindings from the accepted contract and actual
native calls, keeping the reviewer's original prose as the assessment. It needs
the actual expected result/target in that report and the covered testing scenario
names; a generic “all PASS” cannot cover missing claims. This bounded route accepts
ordinary CLI/source findings and explicit pass/defect conclusions, not arbitrary
language. Complex mapping can optionally use one compact
`LHC_OUTCOME_REVIEW <JSON>` line in the same original response. It is optional,
not another certificate file/service, and the writer cannot supply self-PASS:

```json
{"outcome_id":"from status","revision":"from status","scenario":"same scenario","target":"same target","expected":"same expected","assignment_verdict":"complete","product_verdict":"pass","comparison":"actual operation/target/revision and observed result versus expected","coverage":{},"stages":{"technical":{"evidence_calls":["native-call-id"],"expected":"focused regression passes","observed":"focused regression green"},"consumer":{"evidence_calls":["another-native-call-id"],"expected":"same consumer expectation","observed":"actual result"}}}
```

Export the original review with existing Herder `export_transcript`, then:
`python3 <package>/tools/lhc_outcome.py --cwd <project> --runtime codex --session-id <owner> review --manifest <returned manifest>`.
The helper verifies native provenance, independent identity, scope/revision,
ordered stages, assigned coverage and actual tool observations. Supported Codex
native files and OpenCode native exports reuse the existing parsers. Unknown
formats are explicit: use that existing reviewer path, not an invented PASS.
For an already independent testing/research assignment, its own raw source report
can close that assignment; no recursive hiring. It never accepts the parent
product. Testing may report `product_verdict=changes-required`, with each coverage
item mapped to an object with `verdict` (`passed` or `defect`), `expected`,
`observed`, and `evidence_calls`; engineering requires product pass. Each closed
stage/coverage claim needs its own expected→observed comparison and native refs.
One review can cover several claims only when the reviewer actually covers each;
the author's general “all PASS” or a top-level comparison cannot fill omissions.

Remote stages also need their own contract-bound readback target/expectation:
`contract ... --stage-target deploy='curl-target-or-exact-CLI' --stage-expected deploy='v2'`.
Use the actual installed-version endpoint/CLI; supported JSON version/revision/
release fields bind the readback, not health or `git rev-parse`. Publication and
merge use a bound `gh pr view <exact-URL> --json ...` readback (headRefOid or merged
mergeCommit oid); publication also supports exact `git ls-remote ... refs/heads/...`
with the expected head SHA. These are reads, not reviewer mutation rights. Unknown
readback formats stay explicit instead of being accepted as arbitrary CLI output.
Browser coverage needs action followed by snapshot/result, not open/login alone.
Navigation, action and result must share the target-bound browser session,
namespace and tab; another application's snapshot cannot close this claim.
Effective native workdir must remain in the project; relative CLI canaries run
at the bound project root, not another checkout with the same filename.
Reused review sessions are supported, but only native calls after the current
scope-bound assignment and latest owned revision/contract observation can count.
Fresh final prose cannot relabel old calls as evidence of the new revision.
Unknown source timestamps/order stay explicit instead of being guessed fresh.

This is a bounded mechanical floor. The independent reviewer owns semantic
truth: same operation, host, revision and real expected result. Native refs, echo,
generic health/HTTP 200, unit-test output and a writer's PASS are insufficient.
The helper does not prove all shell languages or understand arbitrary business
semantics. Inspect original source and review limitations, and repair/recheck
actual discrepancies rather than leaving an unresolvable mandatory schema loop.

## Stop and questions

Finish verdict is complete/pending/running/blocked/human-stopped. Only the proven
applicable stages close it. The native Stop veto (Codex/ZCode) permits one bounded
continuation per meaningful owned revision/stage/canonical answer, deduplicating
identities including A→B→A. New calls/turns/status polls/foreign WIP are not progress.
Repeated unchanged Stop preserves pending and exact next step; it is not success.
Human stop, permission, accepted/UNKNOWN external work and job IDs remain protected.
OpenCode currently observes completion and reinjects context/compaction; do not
claim an unimplemented pre-final veto. No new daemon, cron or schedule.

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
