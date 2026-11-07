# Изолированный native пакет 1.18.0

Проверенный version commit: 6544797b0435c30ed4b8329cb1ededcfbe00d468. Version snapshot проверен, final freeze ожидает H R1/R2 и независимые gates.

Codex0.167 native local marketplace add → plugin add once → plugin list exact ID/version. Использован git archive точного SHA, отдельный CODEX_HOME и собственный marketplace lhc-candidate-6544797b0435, без копирования auth/config/history. Все package bytes совпали; hashes в evidence/integration/isolated-6544797b0435/input.json и package-bytes.json. Native hooks/list прочитал определения; trust states: {'untrusted': 11}. Trust не менялся, hook effect не заявлен. MCP initialize подтвердил1.18.0, tools/list содержит existing и новые read_goal_control/record_frontier_decision. Model sessions created:0.

Installed root: /home/roomhacker/agents-projects/LastHumanCommit/.worktrees/audit-followup-20261107/.tmp/integration-01a1b7ae/isolated-6544797b0435/codex-home/plugins/cache/lhc-candidate-6544797b0435/last-human-commit/1.18.0

Квитанции сохранены без изменений в canonical evidence/integration/isolated-6544797b0435/. Shared config/installed record/personal marketplace проверены stat до/после: unchanged=true; protected credential content не читался. Isolated package сохранён для следующего consumer.

Parent delivery exit2: error: commit scoped changes and preserve foreign work before delivery. Root lock status при readback: 'D downloaded_files/dashboard.lock'. Удаление в worker source commits не переносилось; текущее root deletion сохранено и не stage/не восстановлено. Canonical root/H/Q1 records остаются вне I1 scoped commits. Product paths clean: True.

Не доказаны: native LLM-turn, lifecycle hook effect, physical parent wake. Native QA не PASS. Main merge/tag/shared install/mirror/runtime не выполнялись.
