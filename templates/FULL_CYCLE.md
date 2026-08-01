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

## Scope scenarios

- Failed canary + unrelated secondary work -> STOP_SCOPE_DRIFT
- Green canary + direct regression -> review the direct regression
- User-confirmed secondary objective -> in scope

## Estimate history

Initial estimate (UTC+3, range, assumptions):
Revisions (UTC+3, previous -> new, evidence/reason, scope impact):

## Mandatory Overseer decisions

Raw user context supplied (location):
Current user P0 reconstructed by Overseer:
Business delta and P0 distance:
Questions for L:
Scope and acceptance decision (evidence, independent decision):
Plan-readiness decision (evidence, independent decision):
Stage-transition decisions (stage, evidence, independent decision):
Release-readiness decision (evidence, independent decision):

## Mandatory Critic release decision

Raw user context supplied (location):
Current user P0 reconstructed by Critic:
Business delta and P0 distance:
Questions for L:
Release verdict (evidence, independent decision):

L cannot prescribe, narrow, rewrite, or override either gate. A stop, rethink,
missing-context verdict, or unanswered question remains binding until the same
gate or the user releases it.

## Progress checkpoints

After at most 30 tool calls or shell commands, or 30 elapsed minutes when
measurable, whichever comes first, every agent runs `uptime` and records the
project-wide P0, real business delta, elapsed time, blocker, and next action.

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

## Stage rule

Default delivery order is YAGNI -> Normal -> Ultimate, stopping at the
human-selected target. Do not start a later stage unless it is inside the exact
confirmed scope and selected target. Any skipped, reordered, or collapsed stage
requires recorded exception evidence and a mandatory Overseer decision.

## Selected-plan WSFF

Call-stack tree:
File-tree diff:
Key types and method signatures:

## Delivery

YAGNI MVP slice, canary, evidence, Overseer decision:
Normal slice, canary, evidence, Overseer decision:
Ultimate slice, canary, evidence, Overseer decision:
Stage exceptions (evidence, risk, Overseer decision):
Test evidence:
Review evidence:
Commit:
L-owned release handoff and wake:

## Финальный ответ

Финальный ответ - только на русском

Мобильный обзор релиза:
