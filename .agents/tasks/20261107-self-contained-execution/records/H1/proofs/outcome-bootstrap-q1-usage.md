# Q1: public pending bootstrap

Запускать **из самой Q1 native Codex session** `01a1b7a4-2eb2-7471-83fd-2edb027f38c5`. Source entry ниже — H cumulative SHA `8a344996712891ffe41b6c28c7e00632fb28259c`; после интеграции можно заменить только путь к tool на принятый root-source tool. Installed 1.17.1 этим source change не обновлялся.

Обычный публичный mutating contract, без state JSON seed и без hook replay:

```sh
python3 /home/roomhacker/agents-projects/LastHumanCommit/.worktrees/self-contained-handoff-20261107/src/common/tools/lhc_outcome.py \
  --cwd /home/roomhacker/agents-projects/LastHumanCommit/.worktrees/audit-followup-20261107 \
  --runtime codex --session-id 01a1b7a4-2eb2-7471-83fd-2edb027f38c5 \
  contract --task-class testing \
  --scenario 'Проверить изолированные goal-control случаи в своей native QA-сессии' \
  --target 'project:/home/roomhacker/agents-projects/LastHumanCommit/.worktrees/audit-followup-20261107' \
  --expected 'Bootstrap остаётся pending; принятие другой цели не переносится, текущие требования сохраняют свою привязку' \
  --coverage 'pending bootstrap' --coverage 'goal binding' --coverage 'semantic scope change'
```

Естественный `CODEX_THREAD_ID`, переданный harness самой Q1, обязан совпасть с этим ID. Не подставлять искусственный export для обхода проверки. Header native journal должен подтверждать standalone identity и тот же original cwd; неподтверждённый child, другой runtime/cwd, отсутствующий native input или held/closed state дают явный отказ. Новый bootstrap пока поддержан для verified standalone Codex; другие harness сохраняют прежний observed-state route.

Та же read surface после contract:

```sh
python3 /home/roomhacker/agents-projects/LastHumanCommit/.worktrees/self-contained-handoff-20261107/src/common/tools/lhc_outcome.py \
  --cwd /home/roomhacker/agents-projects/LastHumanCommit/.worktrees/audit-followup-20261107 \
  --runtime codex --session-id 01a1b7a4-2eb2-7471-83fd-2edb027f38c5 status
```

Ожидается собственный outcome owner/cwd, `finish_verdict=pending`, consumer pending, `bootstrap.source_kind=explicit-contract`, `scope_origin=unknown`; ни одного PASS/execution receipt от bootstrap. Original input берётся из существующего state либо bounded собственного native journal, не заменяется текстом scenario. Дальше — фактический QA consumer и обычный `review`; manual rebind/init/seed не нужен. Повтор идентичного contract сохраняет ID/start/evidence, уже принятое/UNKNOWN не переигрывается.

Эти команды H автор **не запускал на Q1**: документ — usage для независимого consumer, не consumer receipt и не installed acceptance.
