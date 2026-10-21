# 1.5.22 — the dashboard you can actually read

The HTML dashboard is rebuilt around the order a person reads a plan: the goal and the
expected business result, the progress and the status legend, the KPI strip, what to do
right now, the Gantt by waves, the leaves, and the task details. The KPI strip carries
nine metrics and no longer collapses into a tall empty column: the column count is
bounded at every width. The only element that could cover a block of the page is gone,
so the background lives on the canvas and nothing can paint over the content.

A new "Что делать сейчас" panel answers with the same logic as `lhc_parallel.py`: what
runs now, what is ready to launch, what is blocked, how many slots are free, and which
lines are still waiting for a dependency. Every row carries a text status next to its
colour, the status colours pass WCAG AA, and the phone view keeps its table inside a
local scroll instead of dragging the page sideways.

# 1.5.21 — one plan, one graph, one honest dashboard

The plan report and the task graph are now one unit with one validator. `lhc_grid.py`
gained `check-plan <report> <graph>` (exit 0/1/2) so a report whose tasks differ from
the graph leaves is caught instead of quietly rendering an empty dashboard; an
unreadable report is reported as a diagnostic, not as silence. Model classes are the
fleet's own (`glm-5.3-flash`, `minimax-3.1-flash`, `gpt-6-luna`, `glm-5.3`,
`gpt-6.1-sol`) and `⛔ blocked` is a first-class plan group.

A new tool, `lhc_parallel.py`, answers "which lines can run in parallel right now", and
the 30-minute checkpoint reminds the agent to refresh the map through the CLI, rebuild
the view and compare it against the plan. After compaction the agent receives the plan
as text; the JSON stays in the file.

`src/common/skills/` is the single canon of the 24 skills; `skills/` is a generated
projection. `CLAUDE.md` is generated from `AGENTS.md`, so the two routers can never
drift. Hooks are time-only by contract: `hooks.json` registers exactly `SessionStart`,
`PostCompact` and `PostToolUse`, and `BUSINESS_CHECKPOINT.md` now states that fact
instead of promising events that were never wired. The OpenCode V2 adapter is a real
plugin, not a stub.

# 1.5.20 — native manifest parity

All root, native harness and marketplace manifests now report version 1.5.20,
including the Hermes extension. The approved 1.5.19 instruction content is unchanged.

# 1.5.19 — business-first review and delivery

Overseer and review guidance now keeps the Lead in charge of the original business
result. Reviewers are arranged autonomously when risk warrants them; real defects and
claim-critical proof still block the affected release. LHC ledger/manifest and
identity-registration failures are bookkeeping, not delivery vetoes. Ordinary native
reviewer responses remain useful evidence without transcript-export ceremony.

Historical active-time gaps remain explicit but no longer prevent useful authorized
work. Frontier advisers and Overseer provide recommendations; the Lead owns route
choices. User stops, revocations, authorization boundaries, negative findings and
UNKNOWN external operations remain protected.

# 1.5.18 — the task graph and the plan dashboard

Every decomposed objective now keeps a machine-readable task graph next to its task
record as `plan.graph.json` and renders it with one command:

    python3 <LHC>/common/tools/lhc_grid.py render <objective>/plan.graph.json -o <objective>/plan.html

The dashboard is one self-contained HTML file: what is done, what runs now, what is
blocked, the rough finish time and how much of the work runs in parallel, plus the
owner and the session behind every leaf. It reads a task graph (schema version 2),
the canonical plan report or a free-form business-first replan with a decomposition
table, so an existing plan becomes a dashboard without being rewritten first.

The graph is now part of the method instead of an extra artifact: the plan report and
the graph are one unit, written when the objective decomposes and updated together at
every plan boundary. The plan report protocol, the task-decomposition contract, the
decompose-and-dispatch skill and the task record template all require it. The offline
graph checker accepts schema version 2 and validates the live state of a leaf.
# 1.5.17 — the owner's own review before a PR into a repository you do not own

A repository whose owner is not the requester will read the diff against the
rules of their own project, and they will read it once. That read now happens
before the PR exists: a fresh strong session plays that project's maintainer —
a senior engineer who has been in that codebase for years and loves it — reads
the project first (its instructions, conventions, tests, CI, CODEOWNERS and the
history of the touched areas) and then the diff, and returns a mountain of
specific findings instead of a verdict. The author fixes or answers every
supported finding and reviews the changed diff again; only a clean or
explicitly answered review lets the PR open. A dirty PR that reaches the owner
costs more than a later one.

New skill `maintainer-review` and new role `Maintainer`. The rule is wired into
REVIEW_TO_DELIVERY.md, Lead.md, the router and PRODUCT-PHILOSOPHY.md, and
registered in the adapter manifest, the skill catalog and the package
validator. Our own repositories do not need it.
