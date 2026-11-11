---
name: worker-research
description: Find the production path, relevant evidence and next practical change for a repository investigation.
---

# Research a code path

Start with the question the Lead needs answered. Search the existing project code map when there is likely reusable knowledge, then confirm relevant locations in current source.

```sh
python3 <this-skill-directory>/scripts/code_map.py --root "$PWD" search <business-noun> <symbol>
```

Use `rg --files` and targeted `rg -n -C` for names, commands, endpoints and user-visible strings. Follow the caller inward. An existing graph can help with indirect relationships; large-output tools can help read a log or file without losing the useful evidence. Choose them for the question rather than as mandatory stages.

For a defect, reproduce the failure, locate its cause and identify the smallest repair and a discriminating regression. In a read-only assignment, return that route. If fixing is part of the assignment, continue through the repair and its checks.

Stop researching when the next decision is supported. Return the path, owning files, what you established, consequential unknowns and a practical next step. Measure cost or latency only when the question calls for it; label an estimate or missing measurement honestly.

## Reusable findings

Save facts likely to be needed again: which path serves the feature, which configuration controls it, or which misleading route wasted time.

```sh
python3 <this-skill-directory>/scripts/code_map.py --root "$PWD" upsert \
  --key agent-resume-production-path --kind production-path \
  --summary "web/server -> AgentResumeClient -> agent_resume.py -> codex exec resume" \
  --location "web/server::caller" --location "agent_resume.py::main" \
  --evidence "rg -n 'AgentResumeClient|codex exec resume' web agent_resume.py"
```

The map is `.agents/shared-session/knowledge/code-map.json`. `upsert` updates the existing key; `remove` retires obsolete knowledge. Use `--confidence inferred` for an unverified lead. Keep raw logs, secrets and one-run progress out of this reusable index.
