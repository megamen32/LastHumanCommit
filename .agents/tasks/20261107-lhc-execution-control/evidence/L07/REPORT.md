# L07: независимая приёмка native child executor

Кандидат: 5bf8733ba00f7e681823d883688402d113cf478a, LastHumanCommit 1.17.0. Продукт не менялся. Проверялся скопированный пакет plugins/last-human-commit/native/codex в .tmp/consumer-run/package, без импортов из source и author tests. Требования вывел из пользовательской цели: различать назначение и доказанный запуск, child и native parent, завершение и принятие; неизвестный эффект не повторять; Lead должен видеть причину невозможности продолжения.

## Результат

За один bounded сценарий запущено 20 отдельных CLI процессов и один stdio MCP процесс. HTTP MCP Herder написан независимо по public protocol/examples. Ни реальных LLM turns, ни existing native sessions, ни сообщений людям, ни изменений STOP/quota, ни canonical plans не было.

Пройдены safety и lifecycle критерии:

- Lead lead-controller, native parent native-parent, executor child-executor различаются. Assignment сохраняет все три ссылки. HTML явно подписывает parent и executor как заявленные, отдельно показывает runtime native_verified. Это доказательство честной проекции, не фактического native родства.
- До dispatch assignment не означает running. Premature accept отвергнут с exit 1. После correlated admission и наблюдения точного L07-turn-1 появляется running.
- Completion exact turn даёт result_ready при сохранённом queued. Только отдельный accept с проверенным synthetic artifact меняет leaf на done/accepted.
- Normal: один deliver и один resume_after. Повтор dispatch не добавляет эффекта. Неуспешная continuation остаётся видна как blocked, не маскируется под working wake.
- Ambiguous: fixture принимает synthetic effect и обрывает HTTP connection до response. CLI сохраняет delivery_unknown; повтор dispatch и reconcile не отправляют повтор. Всего один deliver, ноль resume_after.
- Quota: definite pre-admission not_attempted остаётся blocked/codex_quota_guard. Повтор и reconcile не увеличивают счётчик delivery. Квота реального хоста не менялась.
- Public HTML renderer содержит delivery_unknown, запрет повторения и отдельный quota blocked reason. Ни running, ни done для этих двух планов не показаны.
- stdio initialize, tools/list и show_plan работают из того же staged package. Execution tools входят в advertised schema.

## Наблюдения, требующие решения Lead

1. Compact recovery surface теряет критическое состояние. CLI show и stdio show_plan для UNKNOWN и quota выводят только Next: L01 Child delivers synthetic artifact. Нет delivery_unknown, запрета replay или codex_quota_guard. MCP structuredContent содержит только argv, returncode, stdout, stderr и не компенсирует этот пробел. В публичной schema show_plan рекомендован первым после compaction/resume. Повторный dispatch безопасен, но Lead вынужден заново читать HTML/leaf вместо восстановления из обещанного compact surface. Exact stdout и RPC сохранены.

2. Отказ continuation классифицируется неправильно. Fixture возвращает валидный MCP tools/call result с isError=true, text и structuredContent содержащими error=permission denied: synthetic continuation blocked, code=permission_denied. Пакет сохраняет wake.state=blocked, reason=wake_turn_mismatch, wait_id=null. Реальная причина permission refusal теряется. Это не доказательство ложного выполнения, но recovery reason вводит в заблуждение. Raw fixture response и полученный assignment сохранены.

## Воспроизведение и границы

Из worktree запустить python3 .agents/tasks/20261107-lhc-execution-control/evidence/L07/reproduce.py. Скрипт ожидает staged package в .tmp/consumer-run/package. Для независимого повторения сначала скопировать туда plugins/last-human-commit/native/codex целиком. Он создаёт только свои synthetic plans и локальный loopback HTTP server. Токен fixture-token является тестовым литералом. Заголовки и inherited environment не записываются. Максимальный subprocess timeout 20 секунд; фактические tool calls и argv/result сохранены в observations.json и stdio-surface.json.

safety-assertions.json фиксирует green safety критерии и отдельные effect counts. synthetic-renderer-plan содержит только synthetic accepted child plan для public renderer canary Lead. HTML проверялся как текст public renderer output, без визуального браузерного теста. Реальная native lineage, право запуска parent/child, настоящий автоматический wake и работа реального subagent не проверялись и не заявляются.

Source unit tests и implementation для expected behavior не читались. Общий suite и release выполняет Lead. Два наблюдения выше переданы Lead сразу; продукт, canonical plan и чужие leaves не менялись.

## Final narrow recheck

Exact candidate d0c60f89fb3fea69ebcc2bfaaf07ecdb2be53487: PASS. B14 and B15 corrected in the same independent fixture. Original receipts above are retained unchanged. See final-d0c60f89/REPORT.md and acceptance-checks.json for final evidence.
