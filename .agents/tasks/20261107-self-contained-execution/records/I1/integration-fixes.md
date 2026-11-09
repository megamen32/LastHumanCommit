# I1: интеграционные исправления

H final c31f702b1fca54f5e10d132ea698612ec35813a9 интегрирован merge 1ae641272980f9aacc8acd4c7244762fe2af0692. Source F/V/H доступны в одном checkout без соседнего PYTHONPATH.

Первый полный validator: 9 failed, 1095 passed, 7 skipped; RED сохранён evidence/integration/validator-initial.log. Исправления source+package опубликованы b102b250.

1. B0dc7460e6941463984b6: curated tools не включали lhc_handoff.py и lhc_plan_control.py. Обе зависимости включены publisher-ом во все tools/common/native projections. Пять packaged hook/publish failures; RED полного validator, GREEN 19 passed.
2. Ba9bd5a4ee21645f29db6: exact tool sets standalone MCP не обновлены после добавления documented read_goal_control/record_frontier_decision. Два варианта regression сохранены целиком, добавлены только новые API в expected set.
3. Bc3ad2338a0b14757a239: dashboard fixture ожидал accepted completion из done cards. Deliberate new expectation: legacy goal unknown → awaiting, все security/sorting assertions сохранены. Это отдельная причина от cache.
4. B0fc5504fcdd6492ab0dc: Replica считала awaiting/superseded активными и повторно считала всю историю. Неактивные summaries теперь ожидают source event. Дополнительные RED показали, что изменения bound outcome не входили в fingerprint и не наблюдались observer-ом. Включены derived fingerprint и watch ровно existing native state явно bound goal; повторное вычисление и загрузка происходят через прежние cache/invalidation/capture. Новый store/timer/scheduler не добавлен. Regression покрывает 105 планов, изменение только одного bound goal, quiet archives, capture seq и немедленное обновление summary по новой outcome projection.
5. B081d703e49df496a835c: public_document отбрасывал goal_control, и новое accepted evidence не доходило до replica. Добавлена allowlist display metadata/source; decision/private fields исключены. RED KeyError goal_control сохранён; GREEN включает отсутствие PRIVATE-SOURCE/PRIVATE-DECISION в public snapshot.

Релевантная итоговая регрессия: 89 passed, 2 skipped in 27.37s; dashboard-mcp-final-green.log. Сценарии actual native install/LLM turn этой регрессией не заявлены. Canonical bug_check после source fixes: 15 total, 0 unresolved. Full validator повторно запущен; результат будет записан отдельно.

Native Q1 read-only observation: metadata 1.17.1 installed/enabled; 11 hooks trustStatus=modified; source и installed learning_path и SHA256 guard совпадают, dedicated QA state path отсутствует. Это не доказательство отсутствия hook invocations и не причина, установленная по event trace. Новых threads/LLM turns, state/bootstrap, trust/config/runtime mutations не было. Дальнейший диагноз поручен владельцем H author; native-Q1-diagnostic.json хранится в evidence/integration, Q1 reader evidence не менялась.
