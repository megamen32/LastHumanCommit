# From a change to a working result

Keep three facts clear: the source was checked, the candidate was installed, and the user's actual client can do the requested thing. A source smoke or healthy process may support diagnosis without proving the client path.

When source is ready and the client still fails, repair the installation, dependency or routing boundary and try that path again. Reuse the context of the Worker who knows it. Keep a healthy build running in its existing job while doing independent work. Follow the user's requested delivery order.

## Review

Review the coherent change and its affected interfaces. Recheck behavior after a substantive change; reuse evidence for unchanged parts. A wrong filename or hash in a report can be corrected from the original record without rerunning a deployment. If coverage is unclear, recover the original result or check the missing portion.

## Test access

Find the primary checkout with `git worktree list --porcelain` and read its `.agents/TEST_ACCESS.md`. It records allowed environments, QA identities, protected credential references, login and recovery steps. The template is `common/templates/test-access.md`.

Prepare or recover test users, data, QA memberships and test clients within the approved environment through the application's supported admin tools. Use an ordinary QA identity for the user journey. Keep reusable accounts and their protected references; clean transient data when the fixture no longer needs it.

When credentials change, update the same protected reference and tell dependent owners which reference changed. Keep values out of prompts, task notes, logs and published packages. Use the existing OAuth manager for test grants and tokens.

A missing access note is not a reason to request authorization already given: recover verified project facts and record them. A genuinely missing external secret, declined access, human stop, third-party account or unapproved real payment holds that operation. Continue independent work.

## Bugs

Record a reproducible error and its impact. Fix regressions from the change and defects blocking the requested result. Preserve unrelated findings for separate work. Use the plan's bug tools for tracked findings; `bug_check` reports their current state. Mark fixed only after the relevant check passes, and explain duplicate or false-positive resolutions.

## Integration and deployment

Use the target in `.agents/PROJECT.md` and the user's mandate. Publish the task branch as work progresses. When `pr_stage=on`, open or update its PR; when off, use the permitted integration route. `lhc_worktree.py delivery` checks publication and matching PR state where applicable.

Deploy to the agreed dev or user environment when the result requires installation. The user's existing scoped request covers the steps needed to deliver their own service; honor explicit exclusions and the repository's actual approval rules. Complete the authorized merge instead of leaving a branch for the user to finish.

For a shared live switch, use the project's existing coordination. When it uses a release lease, acquire it and compare the expected live revision before mutation. Release the lease after the client check, in `finally`. The exact operations and fallback are in `SHARED_WORKTREE.md`. Preserve a newer deployment.

A recovery target should be known to work. An old artifact with unknown provenance can be rebuilt from the verified source; repeated provenance paperwork does not repair it. Report what actually ran after deployment.

## External contributions

Follow the target project's contribution policy. Use `maintainer-review` when its policy or integration risk warrants that review. Fix concrete findings and keep preferences separate. The repository owner's required approval remains their decision.
