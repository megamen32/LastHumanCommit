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

## Планы

Все планы должны оставаться в подтвержденных границах задачи.

### 1. Максимально идеальный

Объем, исключения, компромиссы, риски, оценка, проверка, миграция:

### 2. Нормальный

Объем, исключения, компромиссы, риски, оценка, проверка, миграция:

### 3. YAGNI MVP

Объем, исключения, компромиссы, риски, оценка, проверка, миграция:

Рекомендация:
Выбор человека (дословно):
Краткий preview каждого варианта:

## Stage rule

Default delivery order is YAGNI -> Normal -> Ultimate, stopping at the
human-selected target. Do not start a later stage unless it is inside the exact
confirmed scope and selected target. Any skipped, reordered, or collapsed stage
requires recorded exception evidence; run an eligible Overseer audit only when
the time-and-trigger rule is met.

## Selected-plan WSFF

Call-stack tree:
File-tree diff:
Key types and method signatures:
Pseudocode and migration:
Consequential authorization boundaries:
Second approval of full preview (verbatim):

## Delivery

YAGNI MVP slice, canary, evidence:
Normal slice, canary, evidence:
Ultimate slice, canary, evidence:
Stage exceptions (evidence, risk):
Test evidence:
Review evidence:
Automatic normal/checkpoint commits:
Tag decision (explicit user or release process only):

## Финальный ответ

Финальный ответ - только на русском

Мобильный обзор релиза:
