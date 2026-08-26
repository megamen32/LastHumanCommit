#!/usr/bin/env bash
# LHC time anchor: ZCode SessionStart hook.
# Reads the hook JSON payload from stdin, then writes the durable session start
# anchor <cwd>/.agents/shared-session/time/zcode-<session_id>.json exactly once.
# TIME_CONTROL.md start anchors cite this file; Overseer treats a missing anchor
# as a redirect-level finding.
set -euo pipefail
payload="$(head -c 4096 || true)"
printf '%s' "$payload" | python3 -c '
import datetime
import json
import os
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    data = {}
sid = str(data.get("session_id") or data.get("sessionID") or "unknown").strip() or "unknown"
cwd = str(data.get("cwd") or "").strip() or os.getcwd()
target = os.path.join(cwd, ".agents", "shared-session", "time", f"zcode-{sid}.json")
os.makedirs(os.path.dirname(target), exist_ok=True)
if not os.path.exists(target):
    utc3 = datetime.timezone(datetime.timedelta(hours=3))
    now = datetime.datetime.now(utc3)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "session_id": sid,
                "started_at": now.isoformat(timespec="seconds"),
                "source": "zcode SessionStart hook (real clock)",
                "harness": "zcode",
            },
            handle,
            indent=2,
            sort_keys=True,
        )
        handle.write("\n")
' || true
exit 0
