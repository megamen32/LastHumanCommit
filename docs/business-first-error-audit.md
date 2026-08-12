# Почему LHC заменял бизнес-результат процессом

Дата аудита: 2026-08-12.

## Общий диагноз

Все приведённые истории связывает не «слишком высокая безопасность» сама по
себе, а инверсия функции управления: декларативной целью был бизнес-результат,
но исполнимой целью стала успешная проводка задачи через роли, карточки,
таймеры, reviews и доказательства. Самые жёсткие и легко проверяемые нормы
оказались процессными, поэтому агент рационально оптимизировал процессные
receipts. Фраза `shortest business canary` проигрывала более конкретным
требованиям `Lead не пишет`, `Overseer обязателен`, `maximum <=20`, `ровно три
плана`, `Reviewer после волны`, `два Tester`, `Critic перед release`, `snapshot
commit` и `result file после 10 минут`.

Ниже ошибки разделены, но образуют один feedback loop:

```text
сильный процессный инвариант
→ ранняя делегация/артефакт/гейт
→ поздний production-path и canary
→ локально правильная, но бесполезная работа
→ новый review finding
→ ещё один срез/гейт/estimate revision
→ sunk cost и ещё более поздний бизнес-результат
```

## 1. Ошибки функции цели

1. Бизнес-результат был записан как P0, но не был первой исполнимой развилкой.
2. Process compliance имел больше обязательных глаголов, чем business-first.
3. Агент измерял завершённые роли и чеки, а не изменение пользовательского
   состояния.
4. «Рабочий» молча трактовался как максимально строгий production-ready, даже
   когда пользователь выбрал грубый MVP.
5. Accepted MVP не сохранялся как текущий Definition of Done.
6. Каждая найденная техническая слабость повышала DoD задним числом.
7. Локальная корректность компонента подменяла корректность бизнес-маршрута.
8. Инженерная элегантность конкурировала с time-to-first-canary и побеждала.
9. Результат «процесс запущен и duplicate подавлен» ошибочно считался
   недостаточным без строгого downstream admission.
10. Публичная или мобильная ценность считалась финальным этапом, а не первой
    проверяемой вертикалью.
11. Проверка безопасности стала самостоятельной целью без измеримой угрозы
    текущему claim.
12. Review findings автоматически становились release blockers независимо от
    бизнес-влияния.
13. Optional hardening не отделялся от claim-blocking correctness.
14. Незавершённая идеальная версия обесценивала уже достаточный 80/20 результат.
15. Activity theatre выглядел прогрессом, потому что карточка и receipts росли.

## 2. Ошибки выбора реального маршрута

16. Production call chain трассировался после реализации, а не до выбора файла.
17. Ближайший знакомый adapter принимался за обязательную точку интеграции.
18. Предыдущая диагностика `thread/resume` создала якорь на app-server path.
19. Факт, что autopilot использует `AgentResumeClient → agent_resume.py → codex
    exec resume`, обнаружился слишком поздно.
20. Fake-CDP и fixture contracts исследовались до первой A11y-проверки живой
    вкладки.
21. Source tests использовались как разрешение продолжать неверный путь.
22. Реальный consumer, ingress, wrapper, remote output, ingestion и UI
    диагностировались разными циклами вместо одного сквозного прохода.
23. Реальный credential-backed canary откладывался до завершения внутренних
    абстракций.
24. Production path считался опасным по умолчанию даже для read-only inspection.
25. Ошибка в одном UI/state route приводила к работе над всем surrounding
    architecture.
26. Локальная marker-проверка подменяла проверку того образа, который реально
    обслуживает public.
27. Успешный build рассматривался как почти выпуск, хотя public оставался на
    rollback image.
28. Browser acceptance начинался после code correctness, хотя должен был
    определить минимальный code contract.
29. Native-input отсутствие замечалось в конце, после инвестиций в CDP/A11y
    инфраструктуру.
30. Реальная пользовательская сессия или credential boundary выявлялась после
    многочасовых protocol tests.

## 3. Ошибки route classification

31. Любая нетривиальность автоматически толкала задачу из Direct в Worker.
32. Пятиминутный потолок Direct не учитывал стоимость постановки, передачи и
    повторного чтения контекста.
33. Short определялся через обязательную оркестрацию, а не через cheapest owner.
34. Full определялся длительностью и важностью, а не реальной дорогой развилкой.
35. Уже выбранный пользователем business route повторно превращался в
    архитектурное планирование.
36. Неопределённость считалась основанием для Full ceremony до дешёвого probe.
37. Один вертикальный patch делился на research/implement/review slices без
    реальной ownership boundary.
38. «Нетривиальная задача» ошибочно означала «Lead не имеет права открыть код».
39. Стоимость дешёвого Worker считалась только по модели, без handoff latency.
40. Цена потери контекста между Worker-ами не входила в least-cost расчёт.
41. Стоимость ошибочной декомпозиции не сравнивалась со стоимостью direct Lead.
42. Параллельность выбиралась как добродетель даже при одном serial business
    bottleneck.
43. Новый Worker запускался после stale assignment вместо продолжения текущего.
44. Классификация не пересматривалась после доказательства, что задача состоит
    из двух файлов.
45. Full ceremony продолжалась после исчезновения material decision.

## 4. Ошибки 20-минутного контракта

46. `maximum <=20` смешивал checkpoint управления и максимальную жизнь агента.
47. Worker обязан был остановиться в момент, когда мог быть близок к
    discriminating result.
48. Overseer обязан был отвергнуть любой coherent package >20 минут.
49. План дробился по часам, а не по бизнес-границам и ownership.
50. Full Rust suite искусственно объявлялся отдельным slice, хотя был частью
    одного coherent proof.
51. «Уложился каждый Worker» скрывало перерасход общего stopwatch.
52. 20 минут провоцировали перезапуск и повторное чтение вместо checkpoint
    report.
53. От Worker не требовался стандартизованный report `business delta / blocker /
    shortest next action` именно на checkpoint.
54. Lead не имел явного выбора `continue same Worker` после checkpoint.
55. Redirect/resume был описан как возможность, но не как предпочтение перед
    replacement.
56. Cancellation не имела узкого перечня исключительных оснований.
57. Overrun агента путался с overrun всей задачи.
58. Полезный долгий процесс воспринимался так же, как блуждающий Worker.
59. Таймер оценивал активность, а не canary movement.
60. Искусственные 20-минутные узлы создавали больше joins и review, чем работы.

## 5. Ошибки ожидания и управления агентами

61. Lead писал «жду», но мог завершить turn без вызова настоящего wait tool.
62. Commentary создавал впечатление join, не обеспечивая lifecycle join.
63. Отсутствие terminal status ошибочно превращалось в причину завершить parent.
64. Один timeout воспринимался как событие управления жизнью агента.
65. Fixed 30-minute deadline был описан как последний join, а не одно
    observation window.
66. После истечения join window не был явно задан цикл `checkpoint → control
    action → new join window`.
67. Parent мог отдать final, сохранив Worker живым, но не получив обязательный
    результат.
68. Missing completion signal смешивался с unknown/dead lifecycle.
69. Dead PID observation мог психологически подтолкнуть replacement без
    authoritative terminal event.
70. Новый Worker создавался после timeout вместо resume существующего.
71. Course correction отправлялся поздно, после полного slice failure.
72. Lead не спрашивал Worker о shortest route до назначения нового агента.
73. Overseer использовался как stop machine, а не помощник выбора
    continue/redirect.
74. Agent killing обсуждался как штатная механика контроля, хотя должен быть
    исключением.
75. Отсутствие wait/resume capability не фиксировалось как отдельный harness
    blocker до делегирования.

## 6. Ошибки Overseer

76. Overseer был обязательным для каждой задачи независимо от цены решения.
77. Он запускался до появления достаточной конкретной business evidence.
78. Старый P0 health-remediation получил право veto новой задачи.
79. Persistent state не был достаточно task-scoped.
80. Latest raw user correction не имела безусловного приоритета над карточкой.
81. Stale UI card интерпретировалась как актуальная scope drift.
82. `RETHINK` порождал переписывание lineage вместо короткого route change.
83. После route change требовался ещё один audit даже когда новый путь был
    очевиден и дешёв.
84. 30-minute audit был дополнительным налогом без измеримого decision value.
85. `CONTINUE` receipt стоил orchestration round trip без изменения решения.
86. Binding verdict применялся к смешанному или устаревшему контексту.
87. Overseer оценивал соблюдение 20-minute package, а не coherent business lane.
88. Overrun по умолчанию означал `RETHINK`, даже когда один короткий action явно
    завершал canary.
89. Lead не мог использовать прямое доказательство для очевидного redirect.
90. Overseer вызывался после каждой implementation wave независимо от риска.

## 7. Ошибки Reviewer, Tester, Critic и Adviser

91. Reviewer был обязательным после каждой coherent wave, а wave делались
    искусственно мелкими.
92. Каждый реальный edge case автоматически становился текущим P1.
93. Finding не фильтровался вопросом «ломает ли сегодняшний accepted canary?».
94. Reviewer повысил contract до точного JSONL admission, хотя MVP требовал
    successful launch + idempotency.
95. Atomic weekly accept стал blocker до первой mobile planning канарейки.
96. Reviewer проверял идеальную транзакционность раньше реального S21 flow.
97. Исправления review снова требовали Worker, focused checks и новый review.
98. После каждого микрофикса появлялась возможность для нового unrelated edge
    case.
99. Два failed fixes запускали process rethink вместо canary-first reduction.
100. Два fresh Tester-а были обязательны без расчёта дополнительной ценности.
101. Blind Tester требовался даже для claims, где независимая слепота ничего не
     меняет.
102. Screenshot/video становились церемонией даже для невизуального contract.
103. Real Tester запускался только после review, хотя ранний canary должен был
     определять сам implementation.
104. Failure одного Tester-а повторял оба final passes.
105. Critic запускался перед release независимо от обратимости и blast radius.
106. Critic получал возможность пересмотреть уже выбранный MVP через идеальный
     long-term lens.
107. Adviser обязан был сравнивать ровно три плана, даже если реальный путь один.
108. Искусственные планы создавали ложные архитектурные альтернативы.
109. Plan-review Critic предшествовал Adviser, удваивая стоимость одной развилки.
110. Полный technical preview требовал детали, которые не влияли на выбор.

## 8. Ошибки task lifecycle и durable research

111. Каждая просьба требовала `todo → work → done` копий.
112. Каждая копия требовала отдельного commit до бизнес-работы или завершения.
113. Append-only snapshots увеличивали шум и вероятность stale context.
114. Огромная карточка содержала несколько исторических `Active assignment`.
115. Worker выбрал старый adapter slice, потому что карточка не была компактным
     current state.
116. Lead начал чинить карточку вместо реального production patch.
117. Filename воспринимался как lifecycle evidence, затем потребовались новые
     поля для компенсации.
118. PID/session/mtime поля стали обязательными даже там, где harness ими не
     управляет.
119. Mtime справедливо не доказывал жизнь, но его обязательное ведение всё равно
     создавало tax.
120. После трёх минут research требовались два отдельных файла.
121. Search journal и result дублировали часть task card.
122. После десяти минут result file и Git commit становились обязательными без
     оценки recovery value.
123. Простое исследование могло стоить дешевле, чем его durable packaging.
124. Child обязан был append подробности и отдельно вернуть TL;DR даже для
     короткого результата.
125. Handoff format оптимизировался под смерть harness-а, а не средний путь.
126. Lifecycle repair получал приоритет над stale-but-harmless артефактом.
127. Валидатор заставлял чинить legacy task metadata для новой инструкции.
128. Completion связывался с task snapshot commit, а не с business evidence.
129. Task record превращался из control surface в энциклопедию сессии.
130. Историческая полнота мешала текущему агенту понять единственный next action.

## 9. Ошибки оценки времени

131. Initial maximum фиксировался, но не управлял route в момент достижения.
132. В 07:57 overrun был известен, но не вызвал немедленную смену пути.
133. В 08:10 формальная переоценка произошла на 13 минут позднее stop signal.
134. Новый диапазон легализовал прежний тип работы под другим числом.
135. 45–150 минут превратились в 105–270 без нового business route.
136. Active minutes и wall-clock не показывались рядом с business delta.
137. Каждая роль укладывалась локально, но общий критический путь не
     контролировался.
138. Ожидания и повторные reviews выпадали из ощущения «активного времени».
139. Estimate revision описывал прошлое вместо ограничения будущего действия.
140. Не было 15-минутной falsifiable метрики «новый turn или выбрасываем route».
141. Не было ранней метрики «public marker соответствует новому image».
142. Не было ранней метрики «пять views реально открываются на S21».
143. Не было ранней метрики «list → search → export в живой вкладке».
144. Общий stopwatch уступал отдельным Worker stopwatches.
145. Overrun вызывал больше governance, увеличивая сам overrun.

## 10. Ошибки proof calibration

146. Strict admission proof требовался там, где бизнесу хватало accepted launch.
147. Durable idempotency уже решала главный бизнес-риск duplicate, но это не
     завершало MVP.
148. Authenticated protocol E2E и browser admin readback не разделялись как
     разные claims.
149. `111 events + 202 ingestion + artifact GET 200` обесценивались из-за 401
     другого consumer surface.
150. Unit tests, build, agent receipt и browser path смешивались в один score.
151. Source correctness считалась основанием отложить real-use check.
152. Deployment receipt считался почти равным public visual correctness.
153. Screenshot использовался как замена native input, хотя это другая claim.
154. Login absence блокировала итог вместо честного разделения доказанного и
     недоказанного.
155. Real canary требовал слишком много unrelated dimensions одновременно.
156. Proof строился снизу вверх по слоям, а не от конкретного пользовательского
     утверждения.
157. Mock external contract требовал дополнительный black-box test даже если
     текущий claim его не использовал.
158. TDD превращался в обязательный новый test вместо cheapest red condition.
159. Full suite запускался как acceptance ritual после каждого изменения.
160. Непрошедшая unrelated broad suite провоцировала вне-scope repair.

## 11. Ошибки hardening и качества

161. Explicit errors применялись как deliverable даже для tiny MVP patch.
162. Structured/rotated logging могло стать обязательной частью любого code
     change.
163. Требование документировать каждую private function создавало массовый diff.
164. Cross-OS check мог требоваться без portability claim.
165. 800-line split мог стать unrelated refactor blocker.
166. LEGACY date/end-of-support могло породить новую TODO task вне результата.
167. Database/schema/permissions/security rightly guarded risk, но запрет/гейт
     был шире конкретного claim.
168. Atomicity считалась абсолютной добродетелью до первого mobile canary.
169. Markdown preservation проверялась шире изменённого path.
170. UX metadata и planning views строились до подтверждения базового daily flow.
171. Global enablement обсуждался раньше disposable canary.
172. Source cleanup и removal old workarounds могли расширить tiny fix.
173. Универсальный recovery platform рисковал появиться до восстановления P0.
174. Public visual polish и immutable SHA hardening смешивались с основным
     доступом к сайту.
175. Качество не ранжировалось по влиянию на текущую бизнес-ценность.

## 12. Ошибки sunk cost и обратной связи

176. После инвестиций в adapter продолжалась его доводка, хотя он не был в
     production path.
177. После двух неверных Worker assignments процесс не был отброшен.
178. Каждый новый finding оправдывал прошлые инвестиции и ещё один цикл.
179. Green local tests снижали готовность отказаться от неверной архитектуры.
180. Review loop создавал ощущение приближения из-за уменьшающихся локальных
     дефектов.
181. Плохой public image оставался неизменным, пока внутренний diff улучшался.
182. Невыпущенные 126 тестов создавали иллюзию почти готового mobile продукта.
183. A11y parser 7/7 создавал иллюзию прогресса без подключения к реальной
     вкладке.
184. Protocol canary создавал иллюзию полного E2E без admin consumer session.
185. Смена названия route не сопровождалась сменой falsifiable hypothesis.
186. Estimate expansion маскировала sunk cost как новый план.
187. Retrospective происходил после часов, а не на первом no-delta checkpoint.
188. Business delta не был обязательным полем каждого control decision.
189. Первый real failure не запускал единую diagnosis всей dependency chain.
190. Не было правила «один failure → один сквозной diagnosis → один fix».

## 13. Ошибки валидаторов и текстовой архитектуры

191. `validate.py` требовал presence старых process phrases.
192. Validator закреплял `Overseer is mandatory for every task`.
193. Validator закреплял `maximum <=20` как admission gate.
194. Validator закреплял ровно три plan headings.
195. Validator закреплял два fresh Tester-а.
196. Validator закреплял Reviewer после каждой wave и Critic после Testers.
197. Validator защищал byte hash строгого Code profile вместо business order.
198. Validator проверял lifecycle completeness всех legacy cards при любом
     instruction change.
199. Phrase presence не доказывалось semantic ordering.
200. Business-first текст мог сосуществовать с более сильным противоположным
     workflow и тест всё равно был зелёным.
201. README, authoring docs, adapter templates и skills тиражировали старую
     семантику независимо.
202. Generated plugin skills могли отстать от source и возвращать старые gates.
203. Runtime source и установленный `current` могли расходиться.
204. Установка/rollout могла выглядеть current без проверки resolved project
     route.
205. Тесты чаще ловили отсутствие фразы, чем нежелательное поведение.

## 14. Ошибки коммуникации и управления человеком

206. Пользователю показывали процесс ожидания вместо текущего business delta.
207. «Worker внутри 20 минут» сообщалось чаще, чем «canary стал ближе/нет».
208. Длинные отчёты перечисляли завершённые файлы, скрывая отсутствие public
     результата.
209. Формально честный список тестов мог затмить главный факт «не выпущено».
210. Неверифицированная public версия не ставилась первой строкой handoff.
211. Плановый диапазон сообщался, но его нарушение не меняло поведения.
212. Техническая причина blocker объяснялась лучше, чем минимальный следующий
     бизнес-шаг.
213. Гейт представлялся внешним препятствием, хотя его применение было выбором
     Lead.
214. Безопасность обвинялась шире, чем реально ограничивала mutation/release.
215. «approve all» не интерпретировался как сигнал убрать повторные технические
     preview gates в уже выбранном scope.
216. User correction не всегда немедленно становилась высшим приоритетом над
     старой карточкой.
217. Новая просьба могла сосуществовать со stale P0 в общей shared-session.
218. Parent final мог скрывать живого незавершённого Worker.
219. Capability gap wait/resume не сообщался до делегирования.
220. Итог говорил «почти готово», когда exact user claim оставалась false.

## Новый обязательный порядок

1. Последняя пользовательская цель и принятый MVP DoD.
2. Реальный production consumer path.
3. Самый короткий реальный canary.
4. Самое дешёвое достаточное доказательство именно текущего claim.
5. Direct Lead или least-cost Worker с учётом handoff/latency, а не только цены
   модели.
6. Через каждые 20 активных минут — отчёт о business delta и управленческое
   решение; Worker продолжает жить.
7. Обязательный child ждётся через настоящий wait/join; final до terminal result
   запрещён.
8. Первый реальный failure запускает один сквозной diagnosis dependency chain.
9. Исправляется только первый claim-blocking failure и его прямые регрессии.
10. Overseer/Reviewer/Tester/Critic/Adviser подключаются только при конкретной
    ожидаемой выгоде выше стоимости.
11. Source/test, deployment и real business proof всегда сообщаются раздельно.
12. После доказательства принятого claim работа завершается; hardening остаётся
    отдельным осознанным выбором.
