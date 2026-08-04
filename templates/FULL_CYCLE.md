# Full cycle

## Language contract

- Планы - только на русском
- Execution updates - English only
- Финальный ответ - только на русском

## Confirmed outcome and boundary

Outcome (exact):
Acceptance canary (exact):
Confirmed scope (exact):
Exclusions (exact):
Constraints:
Scope changes with verbatim human confirmation:
Stop when:
Abandon when:
Forbidden without explicit user request:

## Scope scenarios

- Failed canary + unrelated secondary work -> STOP_SCOPE_DRIFT
- Green canary + direct regression -> review the direct regression
- User-confirmed secondary objective -> in scope

## Estimate history

Initial estimate (UTC+3, range, assumptions):
Revisions (UTC+3, previous -> new, evidence/reason, scope impact):

## Eligible Overseer audit receipts

Eligibility source and trigger:
Business delta:
Avoidable spend:
Next minimal action:
Direct user question:
Decision: CONTINUE | ASK_USER | STOP_DRIFT

## Mandatory Critic release decision

Raw user context supplied (location):
Current user P0 reconstructed by Critic:
Business delta and P0 distance:
Questions for L:
Release verdict (evidence, independent decision):

L preserves the complete receipt in the task record. `CONTINUE` is silent;
`ASK_USER` is shown only as its direct question; `STOP_DRIFT` stops the extra
branch.

## Audit eligibility

An attested harness or Fleet clock may make Overseer eligible no more often than
once in 30 minutes after material progress, plateau, repeat failure, budget
pressure, scope drift, or a consequential user question. No `uptime` ritual.

## Research

Repository/request meaning:
Evidence:
Unknowns:
Bounded subagents (scope, model class, reason, result):

## Решение

Полный desired outcome, business canary, scope, exclusions, constraints:
Material human trade-off: yes | no

Если `no`, один рекомендуемый полный путь, его preview и подтверждение:

Если `yes`, покажи ровно три полных варианта с кратким preview:

1. Максимально идеальный — объем, исключения, компромиссы, риски, оценка,
   проверка, миграция:
2. Нормальный — объем, исключения, компромиссы, риски, оценка, проверка,
   миграция:
3. YAGNI 80/20 — полный результат; исключения только низкоценной работы,
   компромиссы, риски, оценка, проверка, миграция:

Рекомендация и выбор человека (дословно):

## Delivery-slice rule

Delivery slices do not reduce or relabel the selected complete outcome. Sequence
them by least cost to canary; do not start a later slice outside exact confirmed
scope. Any skipped, reordered, or collapsed slice requires recorded exception
evidence; run an eligible Overseer audit only when the time-and-trigger rule is
met.

## Selected-plan WSFF

Call-stack tree:
File-tree diff:
Key types and method signatures:
Pseudocode and migration:
Consequential authorization boundaries:
Second approval of full preview (verbatim):

## Delivery

Least-cost slice, canary, evidence:
Later slices, canary, evidence:
Slice exceptions (evidence, risk):
Test evidence:
Review evidence:
Automatic normal/checkpoint commits:
Tag decision (explicit user or release process only):

## Final real-use test (Full only; after Reviewer and Critic)

Tester task and fresh surface:
User journey and observed evidence:
Usability critique (website/app/CLI as applicable):
Verdict: PASS | CHANGES_REQUIRED | STOP_MISSING_REAL_SURFACE
Repair/retest loop, if needed:

## Финальный ответ

Финальный ответ - только на русском

Мобильный обзор релиза:
