# OpenCode

Native Markdown profiles embed the role at startup. `scripts/install_runtime.py` installs the LHC entries and records the package root.

`opencode/lhc-v2.ts` provides the existing guide pointer, time reminders and compaction handoff. Mandatory Boss audits are supplied by the separate OpenCode 2 plugin `lhc-boss-v2.ts`, which creates a fresh Boss session using the parent's model/provider and native authorization. It sends the full visible prose back with `session.synthetic`, `delivery: steer`, `resume: false`.

The Boss schedule remains enabled independently of `LHC_VERBOSE_WORKFLOW` and `LHC_STRICT_WORKFLOW`. Removing optional heartbeat hooks does not remove Boss.

Use `templates/subagent.md` for an assignment's context and continuation. Confirm loading in the actual installed runtime when claiming it works; copied files alone do not prove a live plugin.
