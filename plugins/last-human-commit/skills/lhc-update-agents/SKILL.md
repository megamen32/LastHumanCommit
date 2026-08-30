---
name: lhc-update-agents
description: Rewrite or update Last Human Commit itself. Sources live at ~/agents-projects/LastHumanCommit. Requires a baseline push before edits when anything is dirty or unpushed, commit+push after, validators green, then rollout to every installed harness (zcode, codex, opencode, hermes minimum) via the lhc-rollout skill and the fleet manifest. Use when the user asks to change LHC prompts, roles, protocols, commands, skills, or deployment.
---

# Rewrite Last Human Commit

Sources: `/home/roomhacker/agents-projects/LastHumanCommit` (git, main).
This skill and `lhc-rollout` live canonically in the repo under `skills/`
and ship inside the LHC agent plugin. Never edit deployed copies under
`~/.local/share/last-human-commit/` or project marker blocks directly —
change the source, then roll out.

## 1. Baseline push — mandatory before edits

Make this bot's future changes identifiable as one commit range:

```bash
cd ~/agents-projects/LastHumanCommit
git status --porcelain   # must be empty; if dirty: review every path, repair blockers, commit the complete result
git log @{u}..HEAD       # must be empty; if not: push
git push origin main
```

The pushed HEAD is the baseline; everything after it belongs to this bot.

## 2. Edit sources and validate

- Roles, protocols, templates, commands: `src/common/`; harness adapters:
  `adapters/`; skills: `skills/` (keep the mirror under
  `plugins/last-human-commit/skills/` byte-identical; sync harness-local
  copies such as `~/.zcode/skills/<name>`).
- Run `python3 tests/validate.py` and fix until green; never delete checks.

## 3. Commit and push after — unified history

Commit task-owned files at each completed step; at the end absorb reviewed
foreign edits, leave the tree clean, and `git push origin main`.

## 4. Apply to every installed harness

Minimum set: **zcode, codex, opencode, hermes** (claude-code routers ride
along). One machine-wide store per host:
`~/.local/share/last-human-commit/current` — no per-project
`.last-human-commit/` runtimes.

```bash
SKILL=~/agents-projects/LastHumanCommit/skills/lhc-rollout   # or ~/.zcode/skills/lhc-rollout
python3 $SKILL/scripts/lhc_rollout.py preview --manifest $SKILL/assets/last-human-commit-fleet.json > PREVIEW.json
confirmation=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["confirmation"])' PREVIEW.json)
python3 $SKILL/scripts/lhc_rollout.py apply  --manifest $SKILL/assets/last-human-commit-fleet.json --confirm "$confirmation"
python3 $SKILL/scripts/lhc_rollout.py verify --manifest $SKILL/assets/last-human-commit-fleet.json
```

One apply per version: a rollback receipt for version X blocks re-applying
X; push a new commit to create a new version instead. A freshness window
(~5 min) protects files a rollout just touched — wait it out, don't force.

Finish with one physical harness canary: read an installed router or role
file on each harness and confirm it resolves. End state: clean tree,
pushed, deployed, real-surface tested.

## 5. Install on a harness that is missing LHC

- zcode: router `~/.zcode/AGENTS.md`; roles resolve through the machine
  store; time-anchor hook `~/.zcode/hooks/lhc_time_start.sh` registered in
  `~/.zcode/cli/config.json` SessionStart; `/secret` skill in
  `~/.zcode/skills/secret/`; LHC operator skills copied to
  `~/.zcode/skills/`.
- codex: router `~/.codex/AGENTS.md`; `/secret` prompt in `~/.codex/prompts/`.
- opencode: router `~/.config/opencode/AGENTS.md`.
- hermes: plugin copy `~/.hermes/plugins/last-human-commit`.

Add the target to the fleet manifest (see
`skills/lhc-rollout/references/manifest.md`), then preview/apply/verify.
