Проверка собственного реального native context

STOP_MISSING_REAL_NATIVE_SESSION_STATE.

Public CLI status для codex session 01a1b7a4-2eb2-7471-83fd-2edb027f38c5 с исходным cwd audit-followup-20261107 вернул exit 1: LHC session state отсутствует; новый state не создан. Это точнее предыдущей попытки с пустым fixture cwd.

Активация/bootstrap installed hooks для этой native session не проверена. Нельзя по этому выводу утверждать отсутствие или поломку hooks либо причину. Сценарии а/б/в/г остаются NOT_RUN; вручную state и receipts не создавались.

Next action для Integrator: проверить настройку installed LHC hooks в этом harness, выполнить поддерживаемый реальный lifecycle bootstrap для этой disposable session и исходного cwd, затем подтвердить наличие state той же public status командой. После этого и frozen candidate повторить goal-contract consumer.

Продукт, чужой state и планы не менялись; чужие сессии/агенты не создавались. Только preliminary source consumer, без installed/fullnative acceptance.
