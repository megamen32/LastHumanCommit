# Mandatory workflow learning

Status: complete for implemented/published workflow and proven native delivery; fleet gaps explicit below. Started at: 2026-09-09T12:47:38+03:00 (clock09:47:38UTC).
Original delivery forecast:25–45 wall-clock minutes. Active time: не контролировал.
Basis: mechanics+tests and protocol+delivery inspection in parallel15–25min;
integration/package validation5–10min; native update/loader proof5–10min.
Uncertainty: native loader support and existing unrelated dirty generated files.

Результат: LHC обязательно запускает проверку метода каждые120мин незавершённой работы и не скрывает общий перерасход новыми этапами.
Канарейка: настоящий CLI/hook сохраняет due через смену этапа и compaction, требует evidence-backed закрытие; новый native harness загружает опубликованный пакет.
Минимальный срез: существующий time guard + owning protocols/roles/skill + версия плагина; без нового демона, cron, MCP и отдельной базы памяти.
Отброшено: продолжение GPTAdmin, рефакторинг всех адаптеров, обещание абсолютного подчинения любой модели, принудительные бессодержательные правки каждые2часа.

Baseline0ae9a7e pushed. Primarycheckoutmain. Foreign dirty SHARED_WORKTREE generateddelta and mini-improvement-loop projections preserved; inspect before package regeneration.
Boyle owns timeguard+tests. Faraday readonly native delivery. Root owns protocols/package/integration and acceptance.
Stop condition: verified mechanic+source+native package delivery; do not open next product feature. At maximum re-evaluate actual remaining blocker, no new cycle to resetclock.

Result:1efe47b source120min/cumulativecontrol,7f1cb0f nativefacet1.2.1, pushed.
23mechanicaltests+fullvalidator+22skillparityPASS. Oreviewaccepted correctednestedcwd/timezonecases.
ActualnativeCodex1.2.0 skillloaded buthooks0; source/pluginread nativefacetreturns5; version1.2.1 installed100/88/Mac andall5LHChooks trusted via nativeconfigAPI, noglobalbypass.
FreshCodexsession01a085b5-2e56-75a3-833a-06e129fd30af actualhookstate13:27:23 due15:27:23 advancedonrealtools. Installedskill+manifestreadcompleted; modelrun joinedtimeout124 at100sec withoutfinaltext. Onlyhook/installedreadproofclaimed, notcompletedmodelrun.
Hermes/Claude1001.2.1 installed; Hermesfreshskillproof1.2.0 SHAunchanged1.2.1; Claudefresh401pretool. Hermesgatewaynotrestarted;44NoRoute;OpenCodeordinaryloader timeout. No network/authrepair scope expansion.
Learning fromthiscycle: installedskill!=loadedhook. Existingnativehooks/list is cheapest authority; require it before modelcanary. Native facet was proved0→5 viaactualplugin/read beforepublication; durable docs/plugin-delivery.md capturesroute. Verified awaitinglaterreuse, notclaimuniversalagentbehavior.
