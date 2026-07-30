# Release handoff

## Russian mobile review

Что изменилось:
Ключевые файлы и контракты:
Что доказали тесты:
Что не проверено:
Риски и rollback:
Commit:

Ответьте `да` для немедленной готовности к deploy или `нет`/`стоп` для отмены.
Без ответа обратимое изменение станет доступно внешнему scheduler через 30 минут.

Eligibility is not deployment. The external owner must revalidate the immutable
commit, tests, target, veto state, and rollback before acting. A new commit,
failed tests, changed target, `нет`, or `стоп` cancels this handoff.

## External adapter fields

owner:
target:
commit_or_artifact:
acceptance_proof:
rollback_reference:
review_sent_at:
eligible_not_before:
veto_state:
