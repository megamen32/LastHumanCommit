# Распределение владения листьями L01–L11

Планом и всеми его производными владеет Lead. Каждый Worker пишет только receipt в своей папке; перечисленные `write_paths` не пересекаются между листьями. Зависимости графа сериализуют листья с общими контрактами.

| Leaf | Owner / role | read_paths | write_paths | affected_files | acceptance |
|---|---|---|---|---|---|
| L01 | Lead / research | `AGENTS.md`, `PRODUCT-PHILOSOPHY.md`, `src/common/protocols/` | `research/intent.md` | research receipt | режим и исходная проблема подтверждены источниками |
| L02 | Lead / planning | `research/intent.md`, `PLAN_REPORT.md`, `TASK_GRAPH.md` | `task.md`, `progress.md` | task record | план до реализации и канарей записаны |
| L03 | Worker / human-plan contract | source: `AGENTS.md`, `PRODUCT-PHILOSOPHY.md`, `src/common/agents/Lead.md`, `src/common/skills/last-human-commit/SKILL.md`, `src/common/tools/lhc_outcome.py`; generated: `plugins/last-human-commit/{AGENTS.md,PRODUCT-PHILOSOPHY.md,skills/last-human-commit/,tools/lhc_outcome.py}` | `receipts/L03.md` (receipt only) | source router/aliases/hooks/classifier paths above | новый план объясняет пользу человеку и выбирает режим |
| L04 | Worker / graph pipeline | source: `src/common/protocols/PLAN_REPORT.md`, `src/common/protocols/TASK_GRAPH.md`, `src/common/skills/plan-artifacts/SKILL.md`, `src/common/tools/lhc_grid.py`; generated: `plugins/last-human-commit/common/{protocols,skills,tools}/...` | `receipts/L04.md` (receipt only) | source graph/schema/export/render/check paths above | длинное описание и технические доказательства roundtrip-согласованы |
| L05 | Worker / orchestration | source: `src/common/protocols/COORDINATION.md`, `src/common/protocols/SHARED_WORKTREE.md`, `src/common/skills/decompose-and-dispatch/SKILL.md`, `src/common/templates/project-router.md`; generated: `plugins/last-human-commit/common/{protocols,skills,templates}/...` | `receipts/L05.md` (receipt only) | source orchestration/protocol/template paths above | ownership, handoff и восстановление понятны |
| L06 | Reviewer / blind reader | source read-only: frozen `plan.html`, original brief and source plan; generated output: `.agents/tasks/.../plan.html` | `reviews/plan-review.md` | review receipt only; no source writes | независимый читатель перечисляет реальные препятствия |
| L07 | Worker / correction | `reviews/plan-review.md`, source diff | `receipts/L07.md` | correction-owned source paths | каждое поддержанное замечание исправлено |
| L08 | Reviewer / recheck | updated `plan.html`, `reviews/plan-review.md` | `reviews/recheck.md` | review receipt only | повторное чтение не содержит прежних препятствий |
| L09 | Tester / compatibility | graph, examples, historical plan fixtures | `receipts/L09.md` | roundtrip fixtures and compatibility examples | `affected_files` сохраняется, старые планы читаются |
| L10 | Worker / release | validated source and receipts | `receipts/L10.md` | native package/release metadata | публикация и Fleet readback совпадают |
| L11 | Tester / installed consumer | installed package readback, `plan.html` | `receipts/L11.md` | consumer receipt only | независимый оператор открывает план и понимает результат |

L01/L02 идут первой волной, остальные листья зависят от предшествующего контракта или проверки. Review/tester leaves не пишут source paths, поэтому не конфликтуют с implementation/release leaves; correction L07 зависит от review L06, а recheck L08 — от correction, что делает feedback → correction → recheck явным.
