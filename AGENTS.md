# Maintainer instructions

This is a text-only canon. `CANON.md` is the portable base contract.

Read `ROADMAP.md` first. Preserve the user's concise meaning and keep direct
work fast. Installation, synchronization, cron, deployment, and harness-specific
adaptation belong to Agent Fleet or another external adapter.

When changing the canon:

1. Update `CANON.md` first.
2. Align only the optional roles/templates that expand the changed rule.
3. Keep validation literal, dependency-free, and readable in one sitting.
4. Run `python3 tests/validate.py` and `git diff --check`.

Do not add installers, daemons, hooks, network fetches, credentials, or runtime
dependencies to this repository.
