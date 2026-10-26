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
