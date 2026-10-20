# Project execution-access contract

Store the completed registry at `<primary checkout>/.agents/TEST_ACCESS.md`.
Secret values MUST NOT appear here. Use approved protected references only;
this template is neither authority nor a credential store.

- Owning project, primary checkout/worktree mapping and fixture owner:
- Allowed test environment URLs and how their identity is verified:
- Explicit current user authority/source, permitted local administration/sudo,
  login/consent, account/client provisioning and exclusions/revocations:
- Approved protected reference/path, exact field names and permissions/owner
  (no values), existing secret retrieval/opaque runner-delivery mechanism:
- Supported app-native provision/reset/recovery and initial-password-change steps:
- Ordinary QA identity/role; admin preparation is separate from ordinary testing:
- OAuth owner, supported fresh disposable client/grant, existing native token
  manager, bounded lifecycle and cleanup after dependent consumers:
- Account/password rotation: atomically update the same protected reference,
  preserve permissions/unrelated fields, verify login, notify owners by ref/status:
- Cleanup/rollback, active dependents and exact unresolved external dependency:

After compaction reload this reference and latest authority, never secret values.
Keep entry rules and this registry consistent with direct user scope. Do not infer
permission from sudo, environment names, old notes or tools. Preserve HumanStop.
