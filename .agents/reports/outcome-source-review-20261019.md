# TEST_ACCESS 3993773 — one packaging correction required

Recorded 2026-10-20T09:10:06+00:00. Exact clean HEAD **39937730d30262f38d65051000576f00df921b5c**, tree **964552c674e09e7e91f77814d95511740b7753fd**; comparison base origin/main **eb88c1160d63c3b243643c6718c7262d0898bbcd**. Scope only English1.5.4 execution-access instructions/templates/projections over the accepted1.5.2 executable runtime. Original native sole implementation-owner assignment was independently found in the owner's actual journal; current Herder metadata matches assigned worktree/session. Message prefix alone was not used as authority.

## B14: installed tester skills point to an absent source-tree path

The new policy line9 in these four installed SKILL files says to follow `src/common/protocols/REVIEW_TO_DELIVERY.md`:

- `plugins/last-human-commit/skills/user-testing/SKILL.md`
- `plugins/last-human-commit/skills/focus-groups/SKILL.md`
- `plugins/last-human-commit/native/codex/skills/user-testing/SKILL.md`
- `plugins/last-human-commit/native/codex/skills/focus-groups/SKILL.md`

Neither installed facet contains that literal target. Both contain **`common/protocols/REVIEW_TO_DELIVERY.md`**. The generated router and common/skills copies already use that correct path; the actual loaded skill copies retain the source-only prefix. Existing policy tests assert a filename/pointer is present and check common copies, so they miss this installed-skill resolution defect.

Minimal local correction: normalize the new pointer to the active package's common/protocols path in these generated/installed skill surfaces; preserve the canonical source route as appropriate. Add/run a focused pointer-resolution check across both skills/facets. This is a path correction, not a new semantic review/council or native auth gate. No executable change or live credential operation is needed. Policy semantics otherwise have no blocking finding in this scope; correct the pointer before claiming installed policy readiness.

## Delivery receipt reconciliation

Owner reports PR19 merged as **d63667f7affb9c449ad01d5843a6cd5a8f357a78**, full552PASS and normal Codex1.5.4 activation. Independently read Git confirms its tree is the exact reviewed **964552c674e09e7e91f77814d95511740b7753fd**. Direct read of normal installed cache `/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.5.4` confirms **both tester skills still contain the B14 source-only pointer**, whose target is absent; common/protocols exists. Thus publication/cache equality does not resolve B14. Correct this local installed-policy pointer through the owner; no new general review or auth actions are needed.

INSTALLED_READBACK.json/ACTIVATION_PROOF.json were read at the named evidence location. The activation receipt describes a naturally ended ordinary read-only policy explanation using1.5.4 hook/paths, with no account recovery/admin mutation. Its unchanged fullcycle/pending classification is explicitly retained as a runtime limitation, not an engineering terminal PASS. Other reported cache/config/harness proofs were not substituted for this review's own checks. OpenCode/ZCode acceptance remains unclaimed.

## Meaning and authority checks

Router148lines, Lead, project route, five implementation/acceptance/deploy skills and user-testing/focus-groups route to the primary project TEST_ACCESS contract. Git common-dir/worktree metadata correctly identifies the canonical checkout; one nonexistent historical worktree record was skipped under the specified live-checkout rule without pruning or mutation.

The contract is a registry of refs/scope, not a permission grant or credential store. Supported local fixture administration and intentional scoped sudo reuse existing authority without asking again. Unknown/revoked/customer/external/payment/outreach/irreversible operations fail closed individually; stricter read-only/no-code/no-delegation/named-path limits remain. Sudo, demo labels, tool output or peer claims do not supply authorization.

Same-ref atomic account/password update preserves owner/permissions/unrelated fields and dependent sessions; notices carry ref/status only. Native OAuth credential-manager persistence and approved opaque/in-process runner delivery are allowed. Initial password change/disposable DCR require supported authorized login/consent, one owner, bounded cleanup; no ad-hoc plaintext copies, personal sessions or new transfer service. Compaction restores refs/scope, not values. Existing bound Notify receipt is not an answer. No schedules, private instance refs, recursive leaf testers or independent-parent PASS are introduced. These are instruction semantics, not demonstrated account rotation/login/model autonomy.

## Own validation and executable separation

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -B -m pytest -p no:cacheprovider -q tests/test_test_access_policy.py tests/test_language_policy.py --tb=short
# 16 passed / 1.90s
```

This includes policy/projection checks and a synthetic protected-value native-entry/compaction preservation shield. It is not live credential testing. Read-only Git comparisons independently confirm **all** canonical/generated/native Python tools and OpenCode executable trees are byte-identical to released eb88c11. RUNTIME_PARITY.json agrees. Five checked plugin manifests declare1.5.4. Router/Lead/project template/protocol/generic test-access template common projections match; five implementation/deploy skill pairs match. Only the four tester skill pointers above require correction. No whole validator duplicated; its running receipt is not borrowed as our acceptance.

Unaccepted1.5.3 executable changes are deferred by f8466eb and preserved in a769c3a ancestry/artifacts; earlier B1–B13 source verdicts do not describe current1.5.4 executable behavior. Previously accepted Codex1.5.2 consumer evidence remains separate. No OpenCode/ZCode native acceptance, publication or installed activation is claimed by this source review.

Only this report edited. No source/runtime/auth/main/actual state edits, children, stopped-case resume, live secret reads/transfers or account actions. GrepMesh local index was interrupted; exact known source files were read directly. Unrelated memory ignored. Sole owner retains correction/publication/installation; no waiting on unrelated runtime work is requested.
