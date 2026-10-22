# 1.5.32 - the plan says two honest things: it waits, and it is deferred

The dashboard answered one question twice, and the two answers contradicted each
other: the KPI tile said "blocked: 0" while the panel below said "blocked: 2".
A leaf that waits for an answer and a leaf the owner deferred were one and the
same thing, so "deferred" meant both "we wait" and "nobody waits".

**One rule of the count of blockers.** A leaf is blocked when its status is
`blocked`, and nothing else counts. A queued leaf that carries a blocker text is
queued: it is not a blocked leaf, it does not appear in the count of blockers and
the text "блокер:" is printed only for a leaf that really is blocked.

**Two honest states of a leaf.** A leaf that waits for an answer is `waiting`,
and the report marks it with ⌛. A leaf the owner deferred is `deferred`, the
report marks it with ⏸ and the dashboard calls it "Отложено владельцем": no
answer is expected, it waits for nothing and it takes no slot. The plan report
and the task graph reconcile with both of them.

**The deferred leaf is outside the remainder of the delivery.** It does not count
into "Осталось", into the remaining time, into the forecast of the finish and
into the critical path. A deferred leaf without an estimate does not make the
horizon unknown either - the forecast of an unknown estimate is about the work
that is still owed.

**Two meanings of "deferred" cannot be confused with each other.** The group of
the lines that do not fit into a free slot is called "Ждут свободного слота" now;
the deferred state of a leaf is called "Отложено владельцем" everywhere.

The KPI strip carries ten tiles now, five to a row on a desktop, and the hint of
the "Осталось" tile says how many leaves are deferred and that they are not part
of it.

The count of blockers, the two new states and the remainder of the delivery are
covered by tests, so they cannot drift apart again.

# 1.5.31 - the plan snapshot tells the truth about time, about its own horizon and about what it is

The dashboard of a plan is read on a phone, in a hurry, by the person who owns the
work. It has to say what it knows and what it does not.

**Two numbers about time are two different questions.** `actual_minutes` is the
summed effort of the executors; the window on the clock is `started_at` to
`finished_at`. 22 minutes of effort inside an 11 minute window means two executors
worked in parallel, and one number quietly meaning the other was a defect. The
dashboard now shows "усилие" and "по часам" side by side, in the table, in the task
details and in the text summary.

**The horizon counts from the last confirmed event.** The forecast used to start at
the moment the page was opened, so an idle plan pushed its own finish further away
with every minute of silence. It is now anchored at the last confirmed event, and
the anchor and the idle time are shown. A horizon that has already passed is
reported as passed instead of being moved forward.

**One graph, one revision, generated artifacts.** `render --out-dir` writes the
dashboard and the Markdown summary of one graph revision, and both carry that
revision. Two artifacts of one plan are generated, never kept in sync by hand. The
report stays the authored source of the narrative - the plan is written first - and
the graph is the single source of everything derived from it.

**The search promises what it searches.** The searchable text of a row now holds the
owner, the session id, the harness, the model, the note and the blocker, so every
field the box offers can actually be found.

**One palette, two themes.** The light and the dark theme are defined once, the
status colors carry meaning only and are referenced through CSS variables, and a
test measures the contrast of every text and status color on every surface of both
themes. On a phone the cards become compact rows, the leaf table becomes one row
per leaf instead of a wide table, and every touch target is at least 44 CSS px.

**The dashboard says what it is.** It is a snapshot of the plan, not a control
panel: the real state of the work comes from the API of the owners, and a button in
the snapshot does not change the fleet.

Four defects of 1.5.30 are now covered by tests, so they cannot return: the
ordered forecast bounds, the counter and the done count from one layer, the owner
in the searchable text, and the change log rendered as a change log.

# 1.5.30 - the dashboard disagreed with the plan, and the owner search had no data

The generator counted two different universes at once and printed both of them.

**The counters came from a different layer than the table.** The KPI row took its
numbers from the live journal while the table below it showed the graph, so the
headline read "ready 4 / 18" above 24 rows and "remaining 7" hid fourteen
unfinished leaves. "Remaining" now means every unfinished leaf, total minus
done, and the queue keeps its own separate name instead of being printed twice
under two labels.

**The finish time was computed from the wrong end of the range.** `eta_clock_min`
was built from the maximum duration and `eta_clock_max` from the minimum, so
the dashboard could promise a finish earlier than its own stated minimum. Both
clocks are now built from their own bound and the forecast is shown as a range
with the assumption spelled out.

**The search box promised more than it searched.** Its placeholder said "leaf,
id or owner" while the searchable text of a row held only the id and the label,
so an owner id never matched anything. Owner and session id are part of the
searchable text of every row now.

**The wave journal repeated the task names.** A graph may carry its own change
log: time, action, result, confirmation. The section renders that log and is
titled "Change log"; a graph without one falls back to the old list.

# 1.5.29 - the recheck of the council found three real defects, and they are fixed

The independent recheck of the 1.5.28 synthesis attacked the combined result, not
its parts, and it was right three times.

**The export carries more than the first draft said.** 1.5.28 named owner, session,
harness, model, note and the estimate reason as fields the agent has to add after
the export. Measured on a real report, the export copies them. What it really does
not carry is four leaf fields and two document fields, because a report has no
place for them: `role`, `read_paths`, `write_paths`, `paths` per leaf, and
`current_progress`, `external_waits` on the document. The procedure now says
exactly that.

**A refresh must not force a manual edit.** The recheck found the real leak: the
export drops the attribution, so every plan boundary asked the agent to patch the
graph JSON by hand - the very thing the procedure forbids. `lhc_grid.py export`
now takes `--merge <earlier graph>`: the attribution of every leaf survives a
refresh, matched by id and then by label, while the report still drives the
status, the estimates and the times. The procedure refreshes with that flag
instead of re-adding fields by hand.

**One tool path that resolves in every layout.** The convention `../../tools/...`
breaks in the repository-root projection of the skills tree, and a literal
`src/common/tools/...` breaks in the installed package. Every skill now uses
`<tools>` with the resolution written out: `common/tools/` in the installed
package, `src/common/tools/` in a source checkout and in the repository-root
projection.

**The umbrella pointed at a router that is not there in a source checkout.** It
said the package `AGENTS.md` is two directories above the skill; in the canonical
source checkout that is `src/common/`, where no `AGENTS.md` exists. The text now
names both layouts. The 20% allowance gate also moved into the umbrella, because
in a harness that runs no hooks the umbrella is the only always-loaded entry, and
a gate that names no source is a gate the agent has to go and look up.

The recheck also disagreed with the council about the MCP. That dissent is
retained in the record: the recheck argued for a thin wrapper because the export
had no merge mode. The merge mode now exists, as one verb of the existing tool,
so the wrapper would not remove any pain the CLI does not already remove.

Tests: 1062 passed.

The 1.5.28 procedure named owner, session, harness, model, note and the estimate
reason as fields the agent has to add after the export. That was wrong: the export
copies them, and the report parser has them. Measured on a real report, the export
carries per leaf the id, label, status, dependencies, parallelism, the estimate
bounds, the measured actual time, the start and finish, the owner, the session,
the harness, the model, the acceptance, the note and the blocker; on the document
the goal, the business result and the slot count.

What the export really does not carry is three leaf fields and two document
fields, because a report has no place for them: `role`, `read_paths`,
`write_paths` per leaf, and `current_progress`, `external_waits` on the document.
The procedure now says exactly that, and it also says that the mutable paths of
two leaves that may run at the same time must stay disjoint - the offline
checker fails on exactly that conflict, and the canary that produced this release
hit it.

Tests: 1060 passed.


# 1.5.28 - the plan artifacts are one procedure, and the council decided about the MCP

An AI session that had to produce the task record, the machine-readable graph and
the dashboard did not follow a written procedure: it read `lhc_grid.py` to find the
`check-plan` parser regexes, hunted the report regexes and the status legend, and
inferred the shape from an old task record. The protocol existed; the trigger and
the procedure did not.

**One skill, report-first.** The new `plan-artifacts` skill is the procedure. The
report is the only format a person reads, and the graph is derived from it: the
tool assigns the ids, the statuses, the dependencies and the estimate bounds, so
the agent writes one format instead of two and never hand-writes the graph JSON.
What the report cannot carry - owner, session, harness, model, role, acceptance,
read_paths, write_paths, note, the estimate reason, the blocker details - is added
to the exported graph afterwards. `check-plan` stays the gate: it exits non-zero
when the report and the graph are not one set of leaves. Verified on two live
records: 23 and 32 leaves, export and check-plan green.

**The description is the trigger.** No skill description carried "plan", "graph",
"dashboard" or "check-plan", so nothing was selected when a task was decomposed.
The new description carries them, and the umbrella skill and the router point at
the skill by name.

**A broken path, fixed.** The tool path convention was `../../tools/...`, which
resolves in the package projections and breaks in the repository-root projection
of the skills tree. Every skill now uses `<package root>/tools/...`, the same form
the umbrella skill already used.

**The council said no to the MCP, and said why.** Two independent strong models
were asked to argue the owner's proposal of an LHC-owned MCP server against the
skill. Both landed on the same verdict: the incident was a format-discovery
failure, not a transport failure, and an MCP schema would carry the same field
list in another syntax. The package therefore ships no MCP server; the CLI stays
the source of truth, and an MCP surface, if it ever appears, is a thin wrapper
over the same CLI. The reasoning is recorded in the product philosophy.

**The 20% allowance gate.** A provider with less than 20% of its applicable
allowance left is not used for a council, a frontier model or an adviser, unless
the owner says so directly. The gate reads the units before it applies: GLM
reports usage, MiniMax reports what is left, Codex reports usage.

Tests: 1060 passed.

# 1.5.27 - a queued message is not a result, and a supervisor decides

The coordinator session that became the cluster's supervisor found the cause of a
four-hour stall in its own instructions: it had told six sessions to write with
`sync: false`. That is a queue. The runtime holds the message until the peer's
current turn ends, so a worker that held the whole build window sat idle from 09:50
while its instructions waited, and the cluster's own reports read "done or queued".

**A plain send to a busy peer is a queue.** The contract now says it: use
`force_steer: true` for a peer that is running, keep a plain send for a peer that
should start a fresh turn, and never count "queued" as a result - a peer is done when
its own answer appears in `session messages`. A peer that holds the critical path and
stands idle is a defect to repair, not a thing to wait for. The rule is in the
umbrella skill and in the router, because that is where a hook-less session reads it.

**Supervision is a mode too.** A session that watches other sessions decides inside
the protocol instead of asking the owner, wakes a peer that holds a contour and
stands idle, and reports only what the owner cannot decide from the record: a change
of the owner's rules, a risk of losing or reverting another session's work, and a
deadlock that did not close in two cycles. It does not merge, rebuild, restart,
publish, or touch the live runtime and the public production.

Tests: 1051 passed.

# 1.5.26 — a Lead can address a peer session without discovering the channel

A coordinator session was asked to steer six peer sessions, divide ownership between
them and explain how they write back. It did the work correctly — it loaded the
umbrella skill, read the package router, played the Lead and answered the owner in
his own language — but it spent its discovery turns rediscovering how a peer is
reached at all, and it had no mode that matched its own scope.

**The channel is in the package now.** Agent Herder keys sessions by its own native
ids and does not know a native `mvs_...` id, so a coordinator that trusts only Herder
probes for a channel that cannot work. `common/protocols/COORDINATION.md` states that
a peer is addressed through the runtime that owns it: the runtime's session interface
carries the message (`session send` with `force_steer` to merge into a running turn,
`session messages` to read the peer's answer). The receipt is an admission receipt —
`status: accepted` with `mode: activated` or `mode: steered` — not delivery
evidence. A steered message gets no separate answer, and a resend is a second message
that runs the work twice.

**Delivery is proved once, through the runtime.** The coordinator verified six
deliveries by grepping the filesystem and then a stale runtime sqlite copy of session
messages. The contract now says to verify with `session messages`, that the on-disk
session directory name is an encoded id whose mapping sits in `manifest.json`, and
that a partial sqlite store is not evidence.

**The chat directory may not exist yet.** The coordinator told six peers to write to
`.agents/shared-session/chat/` and learned afterwards that the directory had never
been created. `lhc_chat.py send` creates it on its first publish, so an instruction
naming it must not claim that it exists.

**Coordination is a mode.** Ownership, handoffs and steering messages are not a code
change, not research and not a read-only status answer. The mode table names that
scope: read the peers, publish the ownership registry, hand the work over, prove the
delivery — no research cycle and no council. One task, one file and one runtime have
exactly one owner, the registry is published before the handoff, and a handoff is
complete only when the receiver acknowledged it and the sender recorded it in the
canonical task note.

Tests: 1049 passed.

# 1.5.25 — the skill decides the mode, the language and the Lead, not the description

A session in a hook-less harness loads the umbrella skill and nothing else, so that
skill has to carry the first three decisions. It did not.

**Who the Lead is.** The skill mentioned the Lead in passing. The role now opens the
skill: you are the Lead, you orchestrate only, every inspection, edit, check,
deployment, commit, push and install belongs to a Worker, and Workers do not hire
other agents. The full role description is one path away.

**Which mode the scope calls for.** There was no table, so an audit's defect list
matched the mini improvement loop's catalog line and a session ran a fix loop over
work that also creates a new service, a repository and an architecture decision. The
skill now carries the mode table — quickfix, fullcycle, testing, research, status —
with the rule that the mode comes from the accepted scope and never from a skill's
description. The mini improvement loop says in its own catalog line and in a scope
check that design work is Full: research Workers, one working→ideal→YAGNI plan, an
optional quota-aware frontier council, then bounded dispatch.

**Which language the user reads.** The policy reserved English for internal
reasoning, planning, new task records and agent coordination, so leaf labels ended
up in English inside a dashboard the owner reads. English is now for internal
reasoning and agent coordination only. The answers, the task record, the plan
report, the task graph and the dashboard — leaf labels and field wording included —
are written in the user's language.

# 1.5.24 — a fresh session in a hook-less harness finally knows what a Lead is

The umbrella skill said "read the active package's `AGENTS.md` once". In a harness
that runs plugin hooks, the SessionStart hook hands the agent the exact path to the
package router, so the phrase never mattered. A harness without hooks has no such
pointer: the agent read the phrase, opened the `AGENTS.md` of the project it happened
to be working in, considered the router read, and continued without the Lead
contract, the routing, the time boxes or the language policy. It answered a Russian
user in English.

The skill now names the file it means — the LHC package's own `AGENTS.md`, two
directories above the skill, never the project's — and says what to do when the
harness injects nothing: call the package's own `lhc_entry.py --session` once for the
session pointer and state, and `--heartbeat-only` after each significant step to
keep the 30-minute time-only checkpoint alive. Both commands only report elapsed
time and name the next command.

Four regression tests pin the pointer, the file it resolves to inside the delivered
package, the Lead contract that file must still carry, and the no-hook fallback.

The same release also fixes a plan-graph leak: `find_plan_graph` walked up past the
project and could hand a nested project the task graph of the project that contained
it. A checkout, a service inside a monorepo or a test workspace then rendered the
outer project's plan — the compaction handoff carried another project's leaves and
the 30-minute reminder named another project's lanes. The lookup now stops at the
repository boundary: a task graph never comes from outside the repository you are in.

# 1.5.23 — the task template ships what the method says

The task template still asked for 30-minute leaves and described the Overseer as
a reader that only returns a correction. The method it belongs to says a leaf is
about 15 minutes, that the 20-minute mark is the worker's reporting checkpoint, and
that the Overseer is the Lead's guide while the Lead owns the decision. The template
now says the same thing, so a new task card is written against the real contract
instead of the old one.

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
