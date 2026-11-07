# LHC 1.17.1: продолжение после завершения исполнителя

Исправлены два разрыва существующего пути assign → dispatch → Herder completion wait → reconcile → acceptance.

- Точный активный native turn теперь сохраняет выполнение при отставшем session.status=idle; проверка совпадения turn остаётся обязательной. Stopped, неизвестный/чужой turn не создают пробуждение.
- HTTP ожидание ответа deliver отделено от коротких чтений: 60 секунд для admission, 10 для initialize, session_info и resume_after. Это socket I/O timeout, не общий wall-clock deadline. Повторы при UNKNOWN не добавлены.
- Parity-тест MCP/CLI использует одинаковый контекст без наследования CODEX_THREAD_ID; отдельные тесты attribution сохранены.

При выдаче новых задач руководитель использует assign_leaf и dispatch_leaf. Последний сохраняет wait; после его события reconcile_leaf читает конкретную попытку, acceptance остаётся отдельной. Stop/PostToolUse сами по себе не могут разбудить уже остановленного родителя. Дополнительный scheduler и сетевой обход всех задач в коротких hooks не вводились.

Проверки: RED 3 failed → GREEN 11 passed для stale idle; RED 2 failed → GREEN 6 passed для transport. Независимый review двух изменений PASS. Полный validator: 1045 passed, 6 skipped; пакет и генерируемые проекции согласованы.

Живой потребитель на LHC1.17.0 подтвердил второй дефект: единственная отправка reviewer была принята Herder после timeout, exactturn 01a1b732-02d8-7923-99eb-854b79210939 завершил review. Приёмная квитанция восстановлена чтением существующего ledger, без повтора. Это не доказательство автоматического wake.

Остающийся consumer gate: установленный Herder session_info на controller100 возвращает только sourceRoute без nativeLastTurn; точный read-contract исправляет назначенный Herder исполнитель QLHCNATIVEOBS. До проверки настоящего completion wait и продолжения родителя общий результат не принят. Каноническая работа — Herder plan 20261107-herder-native-mcp-breaking, QLHCCONTINUE.
