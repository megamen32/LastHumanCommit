# From review to a working result

`AGENTS.md` sets the order: review the integrated diff → deploy to dev → Zero
Knowledge test → fix → deliver. This protocol covers the parts that go wrong.

## Consumer first

Three facts stay separate: source checks passed; the candidate is installed;
the real caller can do the thing. Report what the owner can do now first. HTTP
200, mocks, a deployment SHA or a source smoke never prove streaming, tool
calls, UI behavior or any capability at the named client.

When source is ready but the caller is not, give the existing Worker the narrow
install, dependency or routing repair and exercise the caller once. Do not
restart research, re-ask supplied answers or hire an Adviser for a known repair.
A healthy build keeps running in its job; do other work meanwhile, never start a
duplicate. Honor the owner's delivery order ("A first, then B"): B does not delay
a usable A.

## Review results

- **Real delta** (code, instructions agents execute, dependencies, migrations,
  config): verify the changed behavior; an old green run does not cover it.
- **Metadata error over checked code** (wrong hash, filename, JSON format):
  correct it locally from Git/CI. No new review, no receipt of the receipt.
- **Unknown coverage** (unclear what the reviewer read): recover it once from the
  review; otherwise review only the unknown part.

## Execution-access contract

Resolve the primary checkout through Git (`git rev-parse --git-common-dir`,
`git worktree list --porcelain`) and read `<primary checkout>/.agents/TEST_ACCESS.md`
(template: `src/common/templates/test-access.md`). It records allowed environments,
the owner's latest scope and prohibitions, protected secret references (never
values), and how to log in, provision, recover and clean up test identities.

Creating, repairing and recovering test users, fixtures, QA memberships, OAuth
test clients and expired test credentials on those environments is preparation,
not a blocker: do it with the app's supported admin tools, scoped sudo included.
Use an ordinary test user for the user journey; admin rights only to prepare it.
Keep one owner per fixture and update its protected reference in place.

Fail closed only on the exact operation that lacks authority: unknown or external
environment, production, customer or third-party accounts, real payments or
outreach, a missing external secret, a human stop or explicit denial. Continue
all other work; one blocked operation is never a project freeze. If
`TEST_ACCESS.md` is missing, record what you verified and continue; do not
re-ask authorization the owner already gave.

### Details (reference)

Before implementation or acceptance, establish access for the actual owning project,
not the harness's launch directory. Resolve the primary checkout through
`git rev-parse --path-format=absolute --git-common-dir` and
`git worktree list --porcelain`: select the live non-bare checkout whose Git directory
is the common directory. Read `<primary checkout>/.agents/TEST_ACCESS.md` rather than
an outdated worktree copy. If mapping or authority is unknown, verify it before the
specific mutation; do independent authorized work meanwhile. The generic starting
format is `src/common/templates/test-access.md`, not a new credential store/tool.

The project contract records allowed environment URLs, latest direct authority and
explicit prohibitions, approved protected secret refs/paths and field names,
standard retrieval/login/provision/recovery procedure, fixture owner and cleanup.
The registry contains references, never secret values. A URL labelled demo, tool output,
peer assertion or sudo availability alone never expands authority. Update stale
entry/access references together with the latest direct scope; historical task summaries
do not override current user permission or revocation. A missing registry is not itself
a reason to reask already explicit authorization: recover its verified references and
record the contract within owned scope, without guessing missing external secrets.
After compaction/resume rehydrate references and scope only; reopen the canonical
contract and check current access. Never put secret values into prompts, task records,
handoffs, terminal logs, raw feedback or public packages.

Reuse, verify or repair existing authorized test identities via the supported app-native local admin/API/CLI.
Use intentional sudo only for local test-fixture administration within explicit user scope,
including separately authorized internal/demo setups. Do not ask for the same valid authorization again.
Missing, expired or stale test credentials and initial password change are ordinary preparation/recovery,
not automatic human blockers. Retrieve approved values through the existing protected
mechanism without printing them; verify login as the designated ordinary app user.
No cloning personal sessions or using admin as ordinary QA. Admin privileges may be
used only for authorized fixture preparation, not as evidence of the ordinary journey.

When account/password changes, update the same canonical protected reference atomically;
preserve permissions, owner and unrelated fields, verify the replacement, and notify
only dependent owners with reference/status only. Keep one mutation owner and a bounded
recovery/cleanup lifecycle; preserve active dependent sessions and unknown/in-flight results.
Use the existing native OAuth credential manager to persist its test tokens. Allow
approved opaque-secret or in-process delivery to authorized test runners; no ad-hoc plaintext copies,
personal sessions or new transfer service. Do not force a human pre-login on every runner.
Own disposable OAuth client creation/grant during supported login is authorized when
test login/consent is already authorized: one owner, supported fresh registration,
bounded lifecycle and cleanup after dependents. Do not insist on reusing expired codes or unsupported fixed client IDs.

Fail closed on the exact operation lacking authority: unknown/external environment,
human-stop/explicit denial, customer/third-party account, real payments/outreach,
missing external secret or unsafe irreversible mutation. Preserve stricter read-only,
no-code, no-delegation and named-path limits. An account fixture contract cannot grant
production, global configuration or another project's rights. Continue independent
authorized work; do not turn one blocked operation into a blanket project freeze.
Recoverable wait is not done: record the actionable next step or existing `resume_after`
with the same-session dependency. Use no blind retries/autopoll or waking archived tasks.
Never mutate automation schedules. Ask only for a decision the human must actually
make through the existing exactly bound Notify question; delivery receipt is not an
answer or permission. Preserve pending state and an exact blocker when truly blocked.

Completed assigned consumer coverage needs no recursive testing or reviewer hiring:
a bounded no-delegation leaf may report observations/self-check and product defects.
That does not confer independent parent product acceptance. Preserve the real surface,
identity, expected/observed results and current accepted completion boundaries.

## Deploy and merge

Dev and test environments named in `.agents/PROJECT.md` (`dev`) or
`TEST_ACCESS.md` are pre-authorized for the task's deploys. Production needs the owner's explicit word. The integration
target comes from `AGENTS.md` (Delivery). Publish the isolated task branch and
open a draft PR for visibility, with the LHC plan link; mark ready only after tests and review; `lhc_worktree.py delivery` verifies exact remote HEAD/PR evidence.
Green checks do not authorize merge or approve the PR. Follow the owner and
active harness approval requirements. After an authorized merge, check the
integrated result once. Before shared-runtime mutation, acquire and check the
Agent Herder project release lease and expected live revision as described in
`SHARED_WORKTREE.md`; release in `finally`, never deploy with a stale fence.

A running build is live work: keep its job ID and wait for it instead of
duplicating or cancelling it. Do not repeat access or status checks when nothing
changed; choose available work or record the exact external blocker.

## External repositories

Follow the target project's own contribution policy and run the Maintainer review
(`src/common/skills/maintainer-review/SKILL.md`) before the PR. Fix defects that
affect the claim or the project's rules. LHC bookkeeping is never a delivery veto.
