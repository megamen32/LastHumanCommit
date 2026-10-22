# Независимый semantic review Herder quota QUICKFIX

**Вердикт: CHANGES_REQUIRED для exact commit `13379b669ff1b4ad52f8a4e60b88dea11bbd187c`.** Два воспроизведённых несоответствия заданным критериям. Это review source candidate, не приёмка релиза/installed Herder.

Владелец source: Codex `01a155c7-a3a1-7d33-817f-8e7419dd152d`; draft [PR10](https://github.com/megamen32/agent-herder/pull/10). Reviewer: Codex `01a155b4-5105-7cb0-ab1c-9274abc05b7e`. Проверка 19.10.2026. Worktree: `/home/roomhacker/agents-projects/agent-herder/.worktrees/lhc-quota-readonly-20261019`.

## Граница проверки

Прочитаны исходное LHC outcome-поручение, research `council-quota-design-20261019.md` §2, author handoff `herder-quota-fix-20261019.md`, полный diff шести source/test файлов и соседний production caller. HEAD worktree уже **14f5f23**, поэтому для требуемого объекта использованы **Git blobs 13379b6**, без checkout/reset/создания копии.

Детерминированные проверки выполнены непосредственно над этими blobs: TypeScript `transpileModule` → in-memory data URL imports. Provider fetch заменён синтетическими Response; default fetch запрещён исключением; Codex usage dependency заменена заглушкой/явной fixture. Source/runtime/canonical WIP не менялись; auth не читался; сетевых provider/MCP/inference-запросов, запусков сессий и сообщений не было. Записан только этот отчёт.

## Blocking findings

### B1 / P1 — произвольный provider code попадает в публичный details

Exact `13379b6:src/model-quota.ts:31,39–41,101`: ключ `code` разрешён; строковое значение пропускается до120 символов. Ограничение numeric code применяется только при сборке `error`, не к `details`.

Воспроизведение: синтетический HTTP500 payload:
```json
{"code":"review-private-sentinel","model_remains":[{"model_name":"general","current_interval_remaining_percent":50,"current_weekly_remaining_percent":69}]}
```

Actual: `state=unknown,error=provider_http_500`, но `details.code=review-private-sentinel`. Поле может нести произвольный ошибочный текст/credential echo; ни реального секрета, ни реальной утечки в проверке не было. Это подтверждённый канал возврата неразрешённого значения, нарушающий explicit no-secret-leakage критерий; не утверждаю, что он впервые появился в этом diff.

**Уже исправлено поздним 14f5f23:** повтор с тем же синтетическим sentinel над этим Git blob не возвращает значение. Его diff ограничивает строковый code цифровым форматом и добавляет регрессии. Поэтому не прошу автора повторно делать этот fix; **13379b6 отдельно** всё ещё не проходит.

### B2 / P2 — известный истёкший snapshot возвращается как available

Exact `13379b6:src/automation/minimax-quota-preflight.ts:19,25,28–30,42`: cache хранит только время получения и verdict; `reported` без проверки provider end/reset преобразуется в `available`. `src/model-quota.ts:55–68` сохраняет reset metadata, но не учитывает его при положительном verdict.

Fake-clock evidence, миллисекунды:
```text
general: interval=50, weekly=69, end_time=11000, weekly_end_time=999999
now=10000, cacheMs=30000 → available, fetch calls=1
now=12000                 → available, fetch calls=1
новый preflight, now=40000, тот же expired payload → available, fetch calls=1
```

Первый ответ до reset допустим; второй уже использует snapshot за пределами известного применимого окна, третий ошибочно освежает его только временем GET. Это конкретное нарушение критерия «expired snapshot не становится availability», **не требование атомарной резервации и не претензия к обычному concurrent spending**. В 14f5f23 эти функции не менялись.

Минимум: положительную applicability/freshness ограничить известными interval/weekly deadlines; после их истечения — новый read, а если ответ сам описывает уже истёкшее окно — unknown, без синтеза нового reset. Не увеличивать allowance по таймеру. Добавить fake-clock regressions именно для положительного cache crossing reset и expired positive GET. Сохранять исходные единицы/null. Caller сейчас блокирует только confirmed exhaustion; его policy менять в этом bounded fix не требуется.

## Что прошло; дополнительных blocking findings нет

Offline assertions над **13379b6** подтвердили:

- general interval0 и weekly0 независимо дают exhausted; exact text-row0 также блокирует при positive general; video0 не влияет на text;
- unknown pool, missing weekly и missing auth не дают reported/available; missing auth не вызывает fetch; HTTP401/403/generic429/500 дают unknown;
- GLM `unit=3,number=5,nextResetTime=null` и Codex `604800 seconds,reset_at=1792874442,secondary_window=null` сохранены;
- zero snapshot после TTL/reset не повышается до positive: повторный mock GET оставляет exhausted;
- все11 записанных mock provider requests — allowance **GET без body**. Q3 messages/inference POST удалён; exact-model guard, single in-flight slot, deadline/abort сохранены.

Полный diff не меняет named-session, admission, fallback или HumanStop implementation. Соседний `project-launch-dispatch.ts:386–405` по-прежнему пропускает unknown к native admission; это прежняя policy, не «quota unknown=available». Соответствующие guard tests прочитаны, assertions не ослаблены.

Заявленные автором **7 suites /91 tests/typecheck** независимо не перезапускались: текущий HEAD другой, приписывать его результат13379b6 некорректно; адресные exact-blob проверки выше выполнены самостоятельно.

## Canary и следующая граница

Прочитаны `.tmp/quota-fix/live-canary.mjs` и JSON evidence. Canary автора честно различает GLM/Codex live GET и **MiniMax actual singleton payload, injected в candidate без второго provider GET**; interval97/weekly69 относятся к его снимку, не к текущей доступности. Я запросы не повторял. Это не installed singleton acceptance, не reserve и не модельный inference test.

Рекомендация координатору: не выпускать exact13379b6; сохранить уже готовый B1 follow-up и закрыть B2 с указанными регрессиями, затем оценивать новый точный SHA и отдельно выполнять разрешённую installed canary. Релиз этим review не принят. Окно прежнего active-session аудита не расширялось.

