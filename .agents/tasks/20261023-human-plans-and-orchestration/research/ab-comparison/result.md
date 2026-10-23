# Фактическое сравнение маршрутов записи плана

Проверены два маршрута: прямой writer и delegated parent → единственный child writer → receipt. Приложены `direct.md` и `delegated.md`; оба отчёта содержат структуру R01–R08 и 854/875 слов.

Метрики запуска:

- direct: total 250590; input 247831; cached 202624; output 2759.
- parent: total 687338; input 683983; cached 641408; output 3355.
- child transcript: token_count 504011; input 497130; cached 446848; output 6881.
- Две ошибочно прерванные сессии: 77433 + 120461 = 197894; файлы отсутствуют и в сравнение результата не входят.
- Root usage исключён.

Сохранены cached/non-cached значения отдельно. Это сравнение фактической стоимости маршрутов, а не чистый same-model A/B: child реально использовал gpt-6-luna, direct и parent — gpt-6.1-sol. Проверяемый эффект маршрута — наличие постоянного child receipt и parent handoff; исходные direct/delegated файлы приложены рядом с этой квитанцией.
