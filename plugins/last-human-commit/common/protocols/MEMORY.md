# MEMORY — mandatory durable knowledge preservation (degradation order)

Each cycle producing durable knowledge must save it through the degradation order.
Closing with new durable knowledge and no memory record leaves the cycle incomplete.

## Degradation order

1. **agentmemory:** shared across agents/harnesses
   (MCP `agentmemory.memory_save`: concepts, files, project, type).
2. **harness memory:** active harness persistent memory
   (zcode: `~/.zcode/cli/memories/<project>/memory/*.md` plus a `MEMORY.md` entry;
   other harnesses use their equivalent).
3. **project:** `AGENTS.md` section, `.agents/`, task file.

Write to every available level, starting with the first. Missing MCP, permission
or file access at one level does not skip the others: degradation, not replacement.
Apply the active harness's memory-write authority; never store secret values.

## What qualifies

- Working configuration: endpoints/models/key references (environment pointers,
  never secret values), timeouts, models observed hanging/responding.
- Incident root causes and prevention rules (what to do/avoid).
- Owner decisions and prohibitions, preserving the substance exactly.
- Reusable workarounds and canary procedures.

## What does not qualify

- One-off debugging, intermediate artifacts and disposable scripts.
- Facts already captured in code/commits/Git history.
- Duplicate records: search before writing.

## Format

Keep it compact: date, fact, exact paths/endpoints/field names, task/commit link.
In harness memory use one fact per file with frontmatter and index entry.
Project owner rules belong in `AGENTS.md`; investigations in `.agents/tasks/`.
New records follow the router's English operating-language policy; preserve source
quotations and original user text.

## Lead close check

The cycle's final report answers: what durable knowledge was obtained, and in which
memory does it now live?
