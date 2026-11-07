# L07 final acceptance

Verdict: PASS for exact candidate d0c60f89fb3fea69ebcc2bfaaf07ecdb2be53487.

Повторён прежний независимый journey без чтения author tests или implementation. Native package заново скопирован в отдельный .tmp/consumer-run-final/package. Старые RED receipts сохранены. 20 CLI процессов и один stdio MCP процесс прошли те же три сценария child executor: lifecycle, ambiguous delivery и quota refusal.

B14 исправлен: тот же MCP isError=true permission_denied без явного notSubmitted теперь сохраняет wake.delivery_unknown и reason=permission_denied, существующий deterministic wait_id и exact turn. Reconcile делает один resume_after(action=status) и не регистрирует второй wait. Это честно отражает неопределённый итог регистрации и исходную причину отказа.

B15 исправлен: CLI show и stdio show_plan показывают assignment/runtime/wake/reason, admission и dispatchable none. UNKNOWN и quota помечены Saved queue. Безусловного Next: больше нет. UNKNOWN сопровождается указанием reconcile existing attempt/wait и запретом автоматически повторять dispatch или регистрировать другой wait. В accepted плане сохраняется видимость unresolved wake permission_denied.

Safety/lifecycle сохранились: ровно один deliver на каждый из трёх сценариев. Normal имеет ровно одну регистрацию wait и один read-only status. Преждевременный accept отвергается, terminal exact turn остаётся queued/result_ready, отдельный accept даёт done/accepted. UNKNOWN остаётся delivery_unknown без повторной доставки; quota остаётся blocked.

acceptance-checks.json содержит проверенные критерии и счётчики. observations.json и stdio-surface.json содержат actual argv, responses и raw local HTTP MCP calls. final-reproduce.py находится на уровень выше. Synthetic renderer fixture сохранён в final-d0c60f89/synthetic-renderer-plan и в исходном L07/synthetic-renderer-plan.

Ограничения прежние: данные native runtime синтетические. Не проверялись реальные child turns, native lineage и настоящий wake. Existing sessions, сообщения людям, STOP/quota, canonical plans и продукт не менялись. Общий suite и release остаются у Lead.

Один GPTAdmin exec transport вызов завершился timeout до запуска сценария: read-first reconciliation подтвердил отсутствие final output directory. После этого staging и run выполнены отдельными подтверждёнными вызовами, без повторения неизвестных внешних эффектов.
