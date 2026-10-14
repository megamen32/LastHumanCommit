# Requirements: GSD task continuity

**Defined:** 2026-10-14
**Core Value:** Своё поручение до проверенной приёмки.

## v1 Requirements
- [x] **TASK-01**: Сохраняются исходное поручение, уточнения, мандат, outcome, project/boundaries, acceptance.
- [x] **TASK-02**: Entry/reentry/resume/compaction/direction-change сверяются с PROJECT/REQUIREMENTS/ROADMAP/STATE и current SPEC/PLAN.
- [x] **TASK-03**: Обычный чужой message не заменяет поручение; разрешённый handoff принимается и связывается с планом.
- [x] **TASK-04**: Коллизия блокирует конкретный ресурс; совместимая независимая работа продолжается.
- [x] **TASK-05**: Native install, focused regressions и настоящий Codex consumer подтверждают поведение.

## Out of Scope
| Feature | Reason |
|---|---|
| Новый workflow/scheduler/supervisor | Прямой запрет |
| Exmanager/UserIO/Airlock/runtime/phones | Чужая ownership |

## Traceability
| Requirement | Phase | Status |
|---|---|---|
| TASK-01 | Phase 1 | Complete |
| TASK-02 | Phase 1 | Complete |
| TASK-03 | Phase 1 | Complete |
| TASK-04 | Phase 1 | Complete |
| TASK-05 | Phase 1 | Complete |
