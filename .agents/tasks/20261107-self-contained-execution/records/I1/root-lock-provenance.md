# ROOT downloaded_files/dashboard.lock

Tracked path добавлен release commitc0036a4be293c4d630c7c8850f5bd8c9f1085183 (LHC1.6.0), blob e69de29bb2d1d6434b8b29ae775ad8c2e48c5391, mode100644, нулевые bytes. В ROOT текущая запись — unstaged deletion. H/F/V integration commits этот path не меняют; source commit не переносил deletion. Точный unlink actor/момент по имеющимся receipts не установлен, ownership не выдумывается.

У установленного SeleniumBase pytest_plugin вызывает download_helper.reset_downloads_folder; constants объявляют downloaded_files/dashboard.lock, helper очищает downloads folder при test startup. Это возможный механизм, не доказанная атрибуция ROOT unlink. Файл не восстановлен, не stage и не скрыт ignore.

По прямому разрешению владельца создан отдельный clean owned Git worktree self-contained-release-118-20261108, branchlhc/release-self-contained-118-20261108 из точного checked commit. Там tracked empty lock — checkout bytes Git, не восстановление чужогоROOT path. Read-only delivery gate PASS на подготовительном089ac703; после финального snapshot ветка fast-forward и gate повторяется. ROOTWIP сохранён.
