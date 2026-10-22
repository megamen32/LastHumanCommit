# Independent council proposal — preventing premature completion of ordinary engineering/test tasks

Author: MiniMax-M3.1-Flash (independent council member, research only)
Date: 2026-10-19
Scope: proposal only. No source, config, auth, runtime or `main` change. No child sessions created.

## 0. Evidence base actually used

Source read directly in `/home/roomhacker/agents-projects/LastHumanCommit` @ `373cbd2`:

| Fact | Where | Why it matters |
|---|---|---|
| Native entry dispatch + finish gate | `src/common/tools/lhc_entry.py:108-252` | The only place that can veto a finish |
| Finish veto is codex/zcode-only | `lhc_entry.py:204` `if runtime in {"codex","zcode"} and name == "Stop" and not held and (...)` | On OpenCode there is **no** stop veto at all |
| Bounded one-shot continuation already exists | `lhc_entry.py:207-209, 243-246` | `stop_continuation` identity; second Stop → `systemMessage` "незакрытая проверка сохранена; повторное автопродолжение … не запускается" | 
| No task-type concept in source | `rg -i "task_type\|quick\|test.only" src/ templates/` → no hits in `src/`, `templates/` | "Choose the correct work type" is currently unimplemented |
| Only classifier that exists is UI-milestone detection | `src/common/tools/lhc_milestone.py:43-50` (`task_flags`, `minor`), `:28` (`READ_ONLY`), `:213` (`required =`) | Requires SURFACE+BUILD in the same sentence → backend/API/CLI/test/research tasks get **no** external obligation |
| Existing anti-fake-PASS stance | `lhc_milestone.py:219-223` comment; `goal_report` `:390`; `reconcile_feedback` `:467` | Leader prose is explicitly *not* evidence; independent tester verdict is parsed |
| Raw-artifact evidence already collected | `lhc_milestone.py:267-390` (browser commands, URLs, native surface evidence), `lhc_time_guard.py:761-830` (`record_native_action`, `running_jobs`, `scoped_failures`) | Evidence substrate exists; it is not a new store |
| "Receipt ≠ delivery" already modelled | `lhc_time_guard.py:823-941` (`action_status="decision-only"`, `action_evidence_count`, `repeated_review_without_action`) | Decision without action is detectable today |
| Original goal protected from plan/card substitution | `src/common/protocols/BUSINESS_CHECKPOINT.md:4-6`; `lhc_time_guard.py:860-876` (`original_prompt` / `latest_prompt`) | Canary-loss guard exists but is hourly-review-scoped |
| Delivery ordering + deploy≠merge | `src/common/protocols/REVIEW_TO_DELIVERY.md:45-53`; `AGENTS.md:99-120` | "Full-цикл завершён" already names the stages; nothing *checks* them for non-UI work |
| Human-question surface | `src/common/commands/askhuman.md`; `agent-herder human_request_create` + `noticeplace_ask_human` (request_id + harness + session_id + cwd) | A delivered, session-bound question already exists — no new service needed |
| No new service/registry allowed | `REVIEW_TO_DELIVERY.md:35`; contract line 15 | Rules out a dedicated verdict server, hash registry, scheduler |

Task-type in the contract: **quick fix, full cycle, testing (and bounded research/status)**. Every actionable task has a business canary; test-only is a legitimate result; every task has an applicable stage set.

## 1. The failure being prevented, stated precisely

"Premature completion" on an ordinary engineering/test task is not one bug. It is a completion claim that is accepted while at least one of these is true:

1. **Wrong work type** — a test-only or research task was pushed into full-cycle (forced code/deploy that was never wanted: scope drift), or a full-cycle task was treated as quick-fix (declared done after "tests green + commit", before deploy / hands-on / final push).
2. **Canary substitution** — the original user-visible outcome was replaced by the plan, summary or task card, and "done" was judged against the substitute.
3. **Stage evidence missing** — a stage of the agreed finish sequence (implementation → relevant technical tests → permitted deploy → real hands-on/independent acceptance → final push/PR → merge-if-owned) has no artifact, but the task still closes.
4. **Unanswered human decision** — the blocker is a decision only the human can make, and the task closes with that decision still open, or "asked" only in chat.
5. **Self-attested PASS** — the thing that "proves" the canary is the implementer's own summary rather than an artifact another party can re-read.
6. **Non-termination / busy-wake** — the repair for (1)-(5) degenerates into "keep going until done" and re-wakes a session forever without progress.

Note what is *not* in the list: "the user must be asked to pick a mode" (contract line 7 forbids it), and "a new universal interpreter service" (explicitly out of scope).

## 2. Three competing approaches

### Approach A — Per-type finish contract (flat)

Classify the task once, at the first `UserPromptSubmit`, into `quick_fix | full_cycle | test_only | research_status`. Each label maps to a **fixed small set of required evidence kinds**. "Done" = all required evidence kinds present. Test-only and research legitimately carry a *narrower* set, so no new development is forced on them.

- Business value: directly delivers the contract's "explicit automatic initial task classification" and "test-only is a legitimate result". Cheap: one label + one obligation list in the existing session state.
- Complexity: lowest of the three. A mapping table plus one state field; no stage ordering, no per-stage excuses.
- Weakness: flat. It cannot express "stage 3 is not applicable because this is a source-only request" or "stage 5 is not applicable because the repo is external". Those become a fourth label or an ad-hoc override, and overrides are where gates leak.
- Weakness: type is decided *before* the work is understood. A mis-classification is therefore invisible until the end, when it is expensive.
- Falsifier: if a meaningful share of real tasks need a label combination ("full cycle but external repo", "test-only but needs a deploy of a fixture"), the flat model needs a combinatorial explosion and should be abandoned.

### Approach B — Canary-first evidence ledger (type-agnostic)

Drop the type from the finish decision. Every actionable task must carry one *observable business canary* (a concrete user-visible outcome + a place to try it by hand). "Done" requires (i) the canary, and (ii) an **observation of the canary on the real path** produced by something other than the implementer's prose. The type is used only to decide *which* observation suffices (raw test output, a real CLI/HTTP invocation, a live UI check).

- Business value: strongest fit to "retain original business canary" and to the anti-fake-PASS requirement. It attacks the real cause (self-attestation) rather than the symptom (missing checklist).
- Complexity: medium. Needs a definition of "observation" per surface and a way to bind an artifact to a canary.
- Weakness: "canary" is a phrase. An agent can satisfy it with a well-written sentence unless the observation is required to be a *re-readable raw artifact*.
- Weakness: a single canary hides ordering. A task can have a canary and still skip deploy/acceptance/push, and the ledger would not notice.
- Falsifier: if more than one obligation per task is genuinely required (deploy + acceptance + push), a one-canary ledger is insufficient and the type/stage structure must come back.

### Approach C — Ordered delivery-stage ledger with terminal excuses (recommended, with a dash of A)

Model the agreed finish sequence as an **ordered ledger of stages**, each with (a) a machine-checkable receipt kind, (b) a *terminal excuse* state with a recorded reason. Completion = every stage is either **evidenced** or **terminally excused**. The task type (from A) only selects the **default** stage set and the "expected cheapest proof"; it is not itself the gate. The human-decision branch is a first-class stage whose only legal exit is a delivered, session-bound request.

- Business value: covers the whole contract (type, canary, stages, human decision, no busy-wake) in one structure; keeps the user's explicit order (deploy → hands-on → final push) *as* the ledger order, and makes any deviation an explicitly recorded exception instead of a silent reordering.
- Complexity: medium-high but bounded — it is a small enum of stages plus a per-stage receipt kind, stored in the existing session state. No new daemon, no scheduler, no registry.
- Weakness: ceremony. On a one-line fix, a 6-stage ledger is pure overhead. The mitigation is a short per-type default: `quick_fix` = 1 stage (evidence of the original scenario), `test_only` = 2 (test artifact + raw run output), `research_status` = 1 (the finding itself), `full_cycle` = the full sequence.
- Weakness: "terminal excuse" is the leak surface. It must be narrow and recorded, and it must not silence *earlier, still-applicable* stages.

## 3. The crux: how evidence closes the canary without its own fake PASS

This is the part every proposal gets wrong, so it is stated as a rule, not a hope.

> **A stage closes only on an artifact that exists outside the implementer's narration, and that another party can re-read without trusting the implementer's summary.**

Concretely, an acceptable receipt is one of:

1. a **re-readable path or locator** of a raw artifact produced by the real path — a captured browser/session artifact, an exported native transcript, a CI run record, a deployed endpoint that answers;
2. the **raw output of the real consumer invocation**, recorded as output (not summarized) — command exit status and output, an HTTP response with its status, a test runner's result;
3. an **independent session's raw feedback** — a fresh Zero-Knowledge / focus-group session's own transcript, which `lhc_milestone.reconcile_feedback` already knows how to read and whose verdict (`ACHIEVED` / `PARTIAL` / `CHANGES_REQUIRED`) it already parses;
4. a **human's answer** retrieved canonically by request id — not a paraphrase of it, and not a delivery receipt.

Not acceptable, explicitly: the implementer's own summary sentence; "I ran it and it worked"; a diff, SHA, test count or file list as a substitute for the canary; a UI login page instead of the actual test; the mere launch of a child; a fabricated PASS.

This rule is not new to LHC — `lhc_milestone.py:219-223` already states the stance ("Leader prose is not native evidence … never let a claim suppress the independent acceptance obligation"). The proposal is to extend that stance from the UI-surface path to *all* task types, and to make it the closing condition of every stage.

Two consequences that must be designed for, not discovered later:

- **Re-readability, not narration, is the test.** If the only thing that exists is prose, the stage is *not* evidenced, whatever the prose says.
- **Self-produced artifacts are a weaker class.** An artifact the implementer wrote *about* the run (a report, a summary file) is narration wearing a file extension. The receipt must be either produced *by the run* (raw output, captured trace) or produced *by someone else* (independent session, human, CI).

## 4. Testing and research as legitimate outcomes

A finish contract that only knows "ship" will force code on a task that only needed a test or an answer, and that drift is itself a premature/incorrect completion.

- `test_only` — the accepted result is a test. Obligation: the test artifact exists and the raw runner output shows the **intended** expectation (a test that passes trivially, or was never executed against the real target, does not close it). No deploy, no PR, no new product code required. If the user asked only for a test, "the test exists and behaves as specified" is a complete, non-premature completion.
- `research_status` — the accepted result is a finding. Obligation: the finding is located (file:line / command output / source reference) and reproducible by the requester. No code change is required, and a research task that concludes "no change needed" is complete.
- `quick_fix` — obligation: the *original* scenario behaves differently now, evidenced by the raw output of that scenario. A red→green pair on the real scenario is the receipt; a green unit test on a different surface is not.
- `full_cycle` — the full ordered sequence.

The rule that makes this safe: **the obligation set is derived from the task, and the task's own type is what makes a narrower set legitimate.** Narrowness must be justified by the original request, not chosen by the implementer to exit the gate.

## 5. Lack of progress is not a reason to wake forever

The repair for premature stopping must not become a spin loop. The design answers this with three rules, all reusing primitives LHC already has:

1. **One bounded native continuation per distinct obligation set.** `lhc_entry.py:207-209` already stores a `stop_continuation` identity; the second attempt degrades to an honest `systemMessage` instead of another block. The stage ledger reuses that exact shape. No new schedule, no cron, no timer (contract line 15; `BUSINESS_CHECKPOINT.md:48-53` — the existing `lhc_time_guard` is reused, not duplicated).
2. **A stage may be terminally excused, but only with a recorded reason and only for genuinely non-applicable stages.** A stage that is *applicable but blocked* is not excused: it stays pending, and the correct outcome is a delivered question or an exact recorded external dependency — which is what `REVIEW_TO_DELIVERY.md:58-61` already says.
3. **A pending stage is not a completed stage.** If a gate cannot be satisfied, the honest terminal state is "pending, named blocker, work not finished" — never a reclassified PASS. `lhc_entry.py:246` already words this correctly: "Незакрытая проверка сохранена; … Не объявляй её выполненной."

The operational reading: *no progress* is a legitimate reason to **stop and report**, not to keep waking. A session that has made no canary movement and has no available action should reach "pending + exact blocker + (if a human decision is needed) one delivered request", and then be quiet.

## 6. Human decision: delivered and bound, not mentioned in chat

Contract line 4: "unresolved human decisions become one delivered Notify/AskHuman request bound to the same native session."

The machinery exists: `agent-herder human_request_create` produces a binding (`request_id` + `harness` + `session_id` + `cwd` + optional `choices` + optional `notify` block) and creates exactly one Notice card; `noticeplace_ask_human` sends the question text against that binding; the answer is retrieved canonically with `noticeplace_question_result` by `request_id`. The response resumes that exact session once, through a durable receipt.

Rules this proposal adds:

- **One request per distinct open decision**, with a stable `request_id` → idempotent re-asks are impossible; a second attempt is a duplicate, not a new question.
- **Delivery ≠ answer.** A sent request leaves the stage *pending*, not satisfied. The stage closes only when the canonical answer is retrieved.
- **The question is bound to the session**, so the answer returns to the session that asked, rather than to a chat that may have compacted.
- **A question is not a substitute for available work.** If independent work remains, it continues (contract line 14, `AGENTS.md:86-96`).

## 7. Ordering conflict to resolve explicitly: deploy → hands-on → final push vs. real CI needing a branch push

The user's order is: implementation + relevant technical tests → permitted deployment → real hands-on / independent focus acceptance → final push / PR → merge only in a user-owned repository.

Real deployments frequently need the artifact built first, and CI typically builds **from a pushed branch**. If the ledger is read literally, "final push" comes *after* deploy, so the deploy has nothing to deploy — and the agent is pushed into either skipping the deploy or pushing early and calling it done.

Resolution adopted here, as a rule rather than a preference:

- A **staging push** (a branch push made *only* to obtain a buildable/CI-runnable artifact) is an **explicitly recorded exception**, not a reordering and not a completion. It is recorded with: the branch, the commit, the reason, and the fact that the final push/PR obligation is still outstanding.
- A staging push **does not** satisfy the final-push stage, **does not** satisfy the hands-on acceptance stage, and **does not** count as publication.
- Acceptance of that exception requires the *technical* necessity to be shown (CI/deploy requires a pushed branch), not merely convenience.
- The same rule covers the inverse: when a push *is* the deploy (e.g. a plugin update applied from a branch), the hands-on evidence must still come from the *selected installed plugin* on the real surface, not from the source tree.

This keeps the user's order intact where it is meaningful and names the one place where reality forces a different order, instead of letting the agent quietly pick an order and report success.

## 8. External repository, no main merge

"External, no merge" is a legitimate terminal state — but it must be *recorded and scoped*, not used as a blanket excuse:

- The merge stage is **not applicable** for an external repository. It is terminally excused with the reason "external repository, main push/merge/auto-merge not permitted".
- The excuse applies to the **merge stage only**. The earlier stages (implementation, relevant tests, permitted deploy, hands-on acceptance, final push/PR into the permitted branch) **still apply**. "External" must not become a universal skip.
- The recorded terminal state is precise: "PR #N into the permitted branch exists; main was not pushed, not merged, no auto-merge" — and, if the user asked for a live user-visible result, that result is still owed via deploy + hands-on.

## 9. Recommendation

**Approach C, with the narrow dash of A that makes it usable.**

- Use a **type label** to select a *default* obligation set: `quick_fix` (1 stage) / `test_only` (2) / `research_status` (1) / `full_cycle` (ordered, 5-6 stages). The label is advisory, re-derivable, and one-line overridable — it never decides completion by itself.
- Use the **ordered stage ledger** as the actual finish condition, with a narrow, recorded terminal-excuse per stage.
- Use **A-style evidence rules** (§3) as the closing condition of every stage: re-readable artifact, not narration.
- Reuse the **existing bounded continuation** (`stop_continuation`) for non-termination; no new schedule, no daemon, no registry, no new service.
- Reuse **existing** session-bound human-question machinery for the decision stage; one request per decision, delivery ≠ answer.

Minimum viable slice (bounded, honest, ~80% value):

1. Add the type label + per-type default obligation set to the existing session state, with a visible one-line override.
2. Add the stage ledger to the same state, and expose *pending stages* (not a verdict) in the existing reminder/Stop paths.
3. Add the evidence rule to the text that already exists (`BUSINESS_CHECKPOINT.md`, `REVIEW_TO_DELIVERY.md`) and to the agent profile that already owns it — not to a new file.
4. Reuse `human_request_create` + `noticeplace_ask_human` for the decision stage, bound and idempotent.
5. Keep the "no stop-veto on OpenCode" limitation explicit and honest in the output.

Deferred on purpose: a new verdict service, a durable evidence store, automatic type classification by a separate model, per-stage scheduling, and any hard stop-veto on OpenCode.

## 10. Falsifiers and risks

| # | Risk / falsifier | Cheap discriminating check |
|---|---|---|
| R1 | Type mis-classification (test-only treated as full-cycle, or vice versa) | Replay N real prompts; count how often the default obligation set is overridden within the first 10 minutes. If > ~1/3, the label is noise and the ledger must default to the *stronger* set. |
| R2 | Ceremony cost on small tasks | Measure tokens/latency delta for `quick_fix` before/after. If the overhead is not clearly below the value of not mis-finishing, shrink `quick_fix` to a single prose canary + one raw output. |
| R3 | Fake PASS via self-produced artifact | Have an independent session try to *re-read* each receipt without the implementer's summary. If the artifact cannot be re-read, the stage must not have closed. |
| R4 | OpenCode has no stop veto | Verify in a live OpenCode session that an overdue obligation produces a *reminder*, not a block. Any claim of "blocked until done" on OpenCode is false. |
| R5 | Busy-wake | Confirm the second Stop emits `systemMessage`, not another block, and that no timer re-arms the gate. |
| R6 | Terminal excuse leaks | Audit closed stages: every excuse must name a stage that is genuinely non-applicable; check that "external" excuses never appear on stages before the merge stage. |
| R7 | Question ≠ answer | Verify a stage stays pending after delivery, and closes only on a canonically retrieved answer. |
| R8 | Staging-push exception becomes the norm | Count staging pushes that were not technically required; require the reason to be shown. |

## 11. What I will look for in the plan (cross-challenge checklist)

- Does the plan distinguish **four** work types (quick fix, full cycle, test-only, research/status) and make narrow sets legitimate rather than a violation?
- Is there a single place where "done" is decided, and is it a *check* rather than prose?
- Is the closing evidence a **re-readable artifact**, and is self-produced narration explicitly rejected?
- Is the human decision delivered, **bound to the session**, and idempotent — and is delivery ≠ answer?
- Is the "no infinite loop" property implemented by the existing bounded continuation rather than a new timer?
- Is the deploy → hands-on → final push order preserved, with the CI branch-push case as a **recorded exception** that does not count as completion?
- Is "external, no merge" scoped to the merge stage only, with earlier stages still owed?
- Is the OpenCode stop-veto limitation stated honestly instead of papered over?
- Does the plan avoid a new universal interpreter, service, registry, daemon or scheduler?
- Are the proposed checks runnable as cheap discriminating experiments, not as ceremony?
