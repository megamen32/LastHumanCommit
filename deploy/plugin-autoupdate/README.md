# Daily native LHC plugin refresh

`lhc-harness-autoupdate.sh` refreshes the shared `megamen32-plugins` checkout,
updates only the installed `last-human-commit` entry in ZCode, updates the
Hermes package by its pinned `main` commit, and atomically refreshes MiniMax
Code's existing local LHC plugin while keeping its previous copy as a backup.
OpenCode uses the same shared checkout directly, so new sessions pick up that
refresh without a second package cache.

Install the script as `~/.local/bin/lhc-harness-autoupdate.sh`. Linux uses the
included systemd user service and daily timer. On a headless macOS host without
a logged-in launchd user domain, schedule it in the user's crontab; on a GUI
login, the included LaunchAgent plist is available instead. Run the script once
after installation and inspect its journal/log for adapter-specific warnings.
The updater does not update unrelated plugins and preserves prior MiniMax Code
packages as rollback copies.

## Codex post-install hook readiness

Installing or enabling the plugin does not establish hook trust. After a Codex
LHC install or update, use the native app-server `hooks/list` readback for the
active Codex session and verify each effective hook for
`last-human-commit@megamen32-plugins` reports `enabled=true` and
`trustStatus=trusted`. Review the exact current commands and `currentHash` from
that readback against the installed package before writing trust state with
`config/batchWrite` (`hooks.state`, `upsert`). Trust only those reviewed current
hashes; never reuse hashes from an older manifest or use a broad trust bypass.
The Codex hook key includes its manifest namespace: trust for legacy
`hooks/hooks.json` does not authorize
`com.openai/hooks/hooks.json`. Record the native readback separately from the
package-install result; if a hook is untrusted or modified, report
`NEEDS_REVIEW` and keep the exact command/hash evidence for an authorized review.
