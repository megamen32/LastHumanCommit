Текущий итог: PASS на corrected candidate d0c60f89fb3fea69ebcc2bfaaf07ecdb2be53487. См. REPORT-final.md. Ниже сохранён первоначальный FAIL.

# L06. Независимая сессия и продолжение Lead

Вердикт: FAIL по видимости следующего действия в public show_plan. Основной цикл назначения, исполнения и приёмки прошёл в изолированном fixture. Кандидат: 5bf8733ba00f7e681823d883688402d113cf478a, версия 1.17.0.

Проверялся standalone native/codex package. Воспроизводитель копирует package во временный /tmp/lhc-L06-* вне репозитория, удаляет inherited session IDs и PYTHONPATH, устанавливает отдельный XDG_STATE_HOME. Все HTTP RPC адресованы собственному loopback fixture. Настоящих turn/deliver/resume/send, установки и изменений shared runtime не было. Source implementation и авторские tests не читались. Публичные docs/help/tools/list использовались как потребительский интерфейс.

Команда:

    python3 .agents/tasks/20261107-lhc-execution-control/evidence/L06/reproducer.py

Все команды и точные ответы находятся в observations.json. Краткие проверяемые результаты находятся в acceptance.json. Аргументы CLI содержат временный путь package и plan, поэтому доказывают отсутствие repository fallback. Процесс MCP запускается из того же standalone package.

Пройденный сценарий:

1. assign-leaf L01 сохраняет executor_kind=session и разные author, lead, worker. Декларированный author имеет source=declared, не выдаётся за native executor.
2. dispatch-leaf L01 вызывает session_info, один deliver, повторный session_info и resume_after. Состояние running имеет точный turn-consumer-1. Wake сохраняет тот же turn и адресует продолжение Lead. Текст продолжения содержит текущий plan_dir, L01 и attempt_id.
3. Повторный dispatch-leaf того же attempt не делает второй deliver.
4. После завершения fixture reconcile-leaf даёт result_ready и wake=resumed. Leaf ещё не принят.
5. Отдельное назначение L02 зависит от L01. Dispatch до acceptance отклонён: exit 1, dispatch_not_admitted:dependencies_unmet. Для этой попытки deliver не было.
6. accept-leaf L01 делает leaf done, assignment accepted. CLI show показывает L02 следующим.
7. Повторный dispatch L02 после acceptance проходит и фиксирует assignment=running.
8. Свежий stdio MCP initialize, tools/list, tools/call show_plan читает ту же canonical plan.

Найденный дефект: после шага 7 show_plan всё ещё отвечает «Next: L02», хотя L02.assignment.state=running. В тексте show_plan нет статуса assignment/runtime/wake, который позволил бы Lead понять, что это уже запущенная работа. Сохранённый leaf.status остаётся queued. Контроль dispatch повтор не отправляет, но пользовательская подсказка следующего действия противоречит текущему исполнению. Проверка active_assignment_not_offered_as_next в acceptance.json фиксирует отказ.

Ограничения: результат доказывает public CLI/stdio control и чтение состояния с собственным HTTP MCP fixture. Он не доказывает реальный запуск самостоятельной LLM-сессии и физическую доставку продолжения Lead в установленном runtime. Эти операции были явно запрещены. Реальный Herder был только прочитан через public resume_after status для формы receipt; личные сообщения не сохранялись. AgentMemory recall в project scope вернул 0 matches.

Калибровка: первая собственная fixture-квитанция использовала произвольный wait ID и была корректно отвергнута с wake_turn_mismatch. После воспроизведения детерминированного ID существующего Herder и его public receipt shape wake прошёл waiting -> resumed. Это не заявлено как продуктовый дефект. Начальные наблюдения оставлены в fixture-calibration.json, старый run.log переименован в fixture-calibration.log. Долгий remote run имел taskId c7768882b0d47071af79200a2cf7aa04.

Рекомендация Lead: исправить public show/show_plan так, чтобы текущее назначенное исполнение было видимым и running leaf не предлагался как следующая готовая работа. Этот лист не меняет продукт и не редактирует общий план.
