# Независимая проверка исправлений R1/R2/R3 до final freeze

Итог: R1(P1), R2(P1), R3(P2) исправлены в отдельно указанных exact Git objects и проверены независимо локально. Это не APPROVE final integrated candidate. Открыты B4f5c63c21f044bb589a3, final integrated SHA, final package/native consumer acceptance.

## Источники и границы

- H: `b7510c301172c570688428050945c3facff75fa5` (R1/R2).
- Integration: `2bd0f541ae45562341cf0c0765cc5a24eef9e7b6` (R3/package/cache).
- Exact objects извлечены через git archive в own `REVIEW/fix-recheck/H-b7510c3` и `I-2bd0f54`; их source не изменялся. Mutable integration tree не использовался. Не смешивали эти два SHA в выдаваемый за frozen артефакт.
- Исходный `test_public_paths.py` не изменён. Копия `fix-recheck/original_public_paths_unchanged.py` побайтово та же: SHA256 `842413488641955079d517d32781279ad69c56869fbd894a711d5e0b8ccfbc81`. Для разных fixes выбирался соответствующий exact snapshot через уже существующий REVIEW_TOOLS.
- Только own REVIEW fixtures, configs и loopback HTTP server. Нет внешних доставок, реальных native сессий, изменений runtime/config/credentials, Airlock или Herder hosting. Native-format журналы в положительном тесте — явно synthetic fixture identity, с реально исполненными локальными test/canary commands; они не являются production/native consumer proof.
- Recall не повторялся. Author result/proof/review reports не использовались как evidence корректности.

## R1 — P1 → FIXED в H b7510c3, final integration pending

Код: `src/common/tools/lhc_plan_control.py:191-212`, `bind_session_plan`; `:218-246`, `confirm_plan_contract`; обычный CLI contract/review в lhc_outcome.

1. Исходный negative A→B test без правок: настоящий `activate` теперь возвращает `goal_status=unaccepted`, B не принимает COMPLETE A (`original-r1-r2.log`).
2. Независимый positive B: activate → contract B (technical/consumer pending) → actual local implementation `print(6 + 7)` → штатное обновление contract для текущего owned revision → реальные `python3 -m unittest discover -q` и `python3 total.py` (13) → обычный `review --manifest` → accepted, без ручного rebind (`h-positive-final.log`).
3. Повторная same-accepted activation сохраняет exact acceptance binding и history. Изменение только current_progress/slots/updated_at сохраняет acceptance. Старый canary A остался в private history.
4. Проверены HumanStop, permission_declined и codex_quota_guard: activation не принимает цель, native hold сохраняется, verdict blocked (`h-followup.log`, остальные 11 passing cases).

Первый positive fixture log содержал ожидаемый отказ при изменении owned bytes после contract. Это штатный revision gate, не новый product defect: исправлен только новый собственный test setup добавлением обычного refresh contract перед оценкой текущих байтов. Продукт и исходные reproductions не менялись. Начальный отказ сохранён.

## R2 — P1 → FIXED в H b7510c3, final integration pending

Код: `src/common/tools/lhc_plan_control.py:21-30`, `plan_scope`.

Исходный test changed business acceptance теперь получает unknown вместо accepted (`original-r1-r2.log`). Дополнительно независимо проверено:

- Изменение business_result, business_results, acceptance_scenarios, singular acceptance_scenario, legacy acceptance, scope, constraints меняет fingerprint.
- Singular acceptance_scenario и канонический singleton acceptance_scenarios эквивалентны; совместное присутствие alias и того же элемента не дублирует scope.
- Operational current_progress, updated_at, slots, estimate_policy fingerprint не меняют.
- Положительный сценарий R1 проверяет сохранение реальной fixture acceptance после operational changes, а не только сравнение hashes.

## R3 — P2 → FIXED в Integration 2bd0f54, final integration/native pending

Код: `src/common/tools/lhc_plan_publish.py:140-149`, `public_document`; `lhc_plan_mirror.py:271`, `goal_state_path`; `:282`, `source_stamp`; `:309`, `fingerprint`; native-state watches и Replica cache invalidation.

1. Исходный public sanitizer roundtrip без изменения assertion: completed/accepted → completed/accepted (`original-r3.log`).
2. Независимый настоящий локальный путь: canonical leaves + existing synthetic fixture outcome → capture → HTTP sync на loopback make_server → replica validation/storage → GET dashboard. Native adapter/sanitizer/HTTP/replica/catalog не mocked. Изменяли только fixture outcome; листья не менялись. Получено unaccepted/awaiting → accepted/completed → superseded; sequence вырос, source_stamp/fingerprint изменились, ранее cached completed dashboard обновился (`i-followup.log`). Это проверка передачи состояния, а не доказательство принятия seeded synthetic goal.
3. В свежем native decision evidence и private binding history был sentinel `INDEPENDENT-FIXTURE-PRIVATE-PAYLOAD`. Подтверждено, что native adapter действительно видел private decision, но sentinel отсутствует в captured public pending snapshot, сохранённой replica и dashboard HTML.
4. Проверены 20 копий пяти затронутых tools (handoff, plan_control, plan_publish, plan_mirror, plan_mcp) в tools/common/tools/native codex counterparts. Они соответствуют source с явно заданным publisher COMMON-преобразованием `src/common/` → `common/` там, где оно предусмотрено. Оба новых модуля присутствуют в TOOL_COPIES; VERSION=1.18.0 (`i-package-final.log`). Это bounded parity этих копий, не полная финальная package validation.

Первый собственный parity assertion ожидал literal equality и остановился на штатной comment/path projection в common/tools/lhc_plan_mcp.py. Сверено с exact publisher, исправлено только собственное expected projection; продукт не менялся. Начальный output сохранён, это не новый stale-generated defect.

## B4f5c63c21f044bb589a3 и финальная граница

По прямому назначению H отдельно исправляет отсутствие public pending bootstrap у fresh own native session. Его исправление не входит в эти проверенные SHA и не принималось этим review. Узкий safety test на b7510c3: `status` при отсутствующем state выдаёт явную ошибку и не создаёт/не меняет файлов (`missing-status.log`). Это сохранение fail-closed read-only поведения; это НЕ решение bootstrap gap.

Final freeze должен включить H fixes и bootstrap correction в один exact SHA с согласованными generated/native copies. До отдельного final integrated SHA, полной проверки его diff/generated readiness и packaged/native consumer evidence итогового APPROVE нет. Новых product findings в этом recheck не выявлено.

## Собственные outputs

- `fix-recheck/original-r1-r2.log`: 2 passed, 1 deselected.
- `fix-recheck/original-r3.log`: 1 passed, 2 deselected.
- `fix-recheck/h-followup.log`: 11 passed, первоначальный positive fixture setup refusal сохранён.
- `fix-recheck/h-positive-final.log`: positive B + accepted reactivation/progress passed.
- `fix-recheck/i-followup.log`: real HTTP/private exclusion/cache passed; первоначальный literal-copy expectation сохранён.
- `fix-recheck/i-package-final.log`: 20 copies/publisher/version check passed.
- `fix-recheck/missing-status.log`: no-bootstrap-on-status safety passed.
