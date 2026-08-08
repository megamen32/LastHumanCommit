# ZCode subagent instructions template

Before every delegated task:

Bootstrap the child with exactly `<Role> <absolute-task-file-path>`.

- Select the lowest sufficient model in the role profile frontmatter. Do not
  pass an explicit `model` key to the Agent tool when the active guard forbids
  it, and do not inherit L's model merely because it is the parent default.
- Send one compact assignment through the native fresh-agent boundary: role,
  Worker mode when applicable, root task path, goal,
  decisive evidence, allowed/excluded paths, one acceptance check,
  minimum/maximum with maximum <=20, stop conditions, and compact return format.
- The child reads only the assigned task file, appends detailed evidence and its
  result there, and returns only TL;DR to L. It never creates a second task
  card, report, ledger, or spec file.
- If ZCode exposes `send_message`, use it to correct or resume the same Worker rather than replacing it. Otherwise pass the compact Research section
  to a fresh Worker.
- Overseer and Critic are always fresh no-history children with raw user context
  and no desired verdict from L. Reviewer and Tester are fresh independent
  gates as required by their roles.
- Escalate only after `NEEDS_REDECOMPOSITION`, `NEEDS_RETHINK`, or concrete
  acceptance evidence proves a capability gap.
