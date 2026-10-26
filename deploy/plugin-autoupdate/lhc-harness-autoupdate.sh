#!/usr/bin/env bash
# Keep installed LHC adapters current without touching unrelated plugins.
set -u

PATH="${HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PATH

TAG="lhc-harness-autoupdate"
MARKETPLACE_ROOT="${HOME}/.codex/.tmp/marketplaces/megamen32-plugins"
PACKAGE_ROOT="${MARKETPLACE_ROOT}/plugins/last-human-commit"
HERMES_SOURCE="megamen32/LastHumanCommit/plugins/last-human-commit"
HERMES_REPO="https://github.com/megamen32/LastHumanCommit.git"

log() { printf '%s [%s] %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$TAG" "$*"; }
version_at() {
  python3 - "$1" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("version", ""))
except Exception:
    print("")
PY
}

if [[ ! -f "${PACKAGE_ROOT}/.claude-plugin/plugin.json" ]]; then
  log "ERROR shared LHC marketplace checkout is missing; adapters left unchanged"
  exit 1
fi

# Refresh the shared source first. OpenCode consumes this checkout directly.
if command -v codex >/dev/null 2>&1; then
  if codex plugin marketplace upgrade megamen32-plugins >/dev/null 2>&1; then
    log "refreshed shared megamen32-plugins checkout"
  else
    log "WARN Codex marketplace refresh failed; continuing with the current checkout"
  fi
fi

# ZCode keeps a native package cache, so refresh its local marketplace and use
# the native updater for this one plugin only.
if command -v zcode >/dev/null 2>&1; then
  if zcode plugins marketplace update last-human-commit >/dev/null 2>&1 && \
     zcode plugins update last-human-commit@last-human-commit >/dev/null 2>&1; then
    log "checked ZCode last-human-commit through its native updater"
  else
    log "WARN ZCode LHC update failed; it will retry on the next scheduled run"
  fi
fi

# Hermes pins Git plugin revisions and records the installed SHA in its
# provenance file (the installed subdirectory itself intentionally has no .git).
if command -v hermes >/dev/null 2>&1 && [[ -f "${HOME}/.hermes/plugins/.install-metadata.json" ]] && \
   [[ -d "${HOME}/.hermes/plugins/last-human-commit" ]]; then
  latest_sha=$(git ls-remote "$HERMES_REPO" refs/heads/main 2>/dev/null | awk 'NR == 1 {print $1}')
  current_sha=$(python3 - "${HOME}/.hermes/plugins/.install-metadata.json" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("last-human-commit", {}).get("revision", ""))
except Exception:
    print("")
PY
  )
  if [[ -z "$latest_sha" ]]; then
    log "WARN could not resolve Hermes LHC source revision"
  elif [[ "$latest_sha" == "$current_sha" ]]; then
    log "Hermes last-human-commit is current at ${current_sha:0:12}"
  elif hermes plugins install "$HERMES_SOURCE" --force --ref "$latest_sha" >/dev/null 2>&1; then
    log "updated Hermes last-human-commit to ${latest_sha:0:12}"
    if command -v systemctl >/dev/null 2>&1 && \
       systemctl --user is-active --quiet hermes-gateway.service; then
      if systemctl --user restart hermes-gateway.service; then
        log "restarted active Hermes gateway to load the updated plugin"
      else
        log "WARN Hermes gateway restart failed; installed package is current but the process may still use its prior snapshot"
      fi
    fi
  else
    log "WARN Hermes LHC install failed; it will retry on the next scheduled run"
  fi
fi

# MiniMax Code's local plugin directory is its supported third-party source.
# Replace atomically only when its installed manifest is behind the checkout;
# retain the previous copy as a rollback point.
MINIMAX_PLUGIN="${HOME}/.minimax/plugins/last-human-commit"
if [[ -d "$MINIMAX_PLUGIN" ]]; then
  desired=$(version_at "${PACKAGE_ROOT}/.claude-plugin/plugin.json")
  installed=$(version_at "${MINIMAX_PLUGIN}/.claude-plugin/plugin.json")
  if [[ -n "$desired" && "$desired" != "$installed" ]]; then
    stamp=$(date +%Y%m%dT%H%M%S)
    staging=$(mktemp -d "${HOME}/.minimax/plugins/.last-human-commit-update.XXXXXX")
    backup="${MINIMAX_PLUGIN}.bak-${installed:-unknown}-${stamp}"
    if cp -a "${PACKAGE_ROOT}/." "$staging" && \
       [[ "$(version_at "${staging}/.claude-plugin/plugin.json")" == "$desired" ]] && \
       mv "$MINIMAX_PLUGIN" "$backup" && mv "$staging" "$MINIMAX_PLUGIN"; then
      log "updated MiniMax Code local LHC plugin ${installed:-missing} -> ${desired}; previous copy kept at ${backup}"
    else
      [[ -e "$MINIMAX_PLUGIN" ]] || [[ ! -e "$backup" ]] || mv "$backup" "$MINIMAX_PLUGIN"
      rm -rf "$staging"
      log "WARN MiniMax Code LHC update failed; previous package was preserved"
    fi
  else
    log "MiniMax Code last-human-commit is current at ${installed:-unknown}"
  fi
fi

exit 0
