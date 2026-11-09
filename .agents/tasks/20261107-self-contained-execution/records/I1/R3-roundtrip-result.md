# R3 — публичный roundtrip и privacy

Canonical defect: B081d703e49df496a835c (тот же sanitizer defect, отдельный duplicate bug не создавался). Source fix уже включён в b102b250. Ранее RED KeyError goal_control и GREEN89 сохранены в canonical resolution.

Дополнительная запрошенная проверка проходит реальный pipeline: done leaf + bound-unaccepted display projection → capture → replica ingest → awaiting; новая accepted source evidence → capture seq+1 → replica ingest → completed/Цель принята по исходному снимку. Private source/decision sentinels не попадают ни в pending snapshot, ни в replica stored document, ни в rendered page.

RED r3-roundtrip-red.log на source1ae64127 подтвердил прежнюю ошибку fingerprint/cache. Discriminating RED r3-sanitizer-roundtrip-red.log использует тот же старый sanitizer и текущий исправленный mirror/cache: публичный roundtrip теряет accepted projection. Точная композиция/hashes в r3-sanitizer-red-provenance.json. Source root не менялся для RED.
GREEN r3-roundtrip-green.log: 1 passed in0.62s на текущем product source. Это source regression, не independent native acceptance. Graph/snapshot не стали lifecycle authority; интерфейсы native verdict/plan_scope/F/H не редактировались.

R1/R2 назначены отдельному H source operator владельцем. Version snapshot6544797b имеет1.18.0 и full1107passed/7skipped, но НЕ является окончательным frozen candidate до включения P1 fixes и повторной полной проверки. Native isolated readback snapshot сохранён отдельно; trust=untrusted и observed hook effect NOT_RUN.
