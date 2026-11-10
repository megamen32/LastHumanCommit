# Models

Three classes. Name the class in every assignment; take the cheapest class that passes acceptance.

| Class | Use it for |
|---|---|
| fast | routine: research, search, reading, polling, waiting, mechanical edits |
| middle | code written by a ready plan |
| frontier | architecture, hard problems, work that dragged on past its estimate |

The live catalog is classified by the coding benchmark manifest configured in
`config/models.json`. The four named frontier anchors are Astra, Sol, Fable and
Opus; the frontier cut is the lowest coding score among those anchors. The fast
cut is the highest coding score among fast-named families (Fast and Haiku), with
the explicitly named Flash anchors added when they have a score. Scores at or
above the frontier cut are frontier, scores at or below the fast cut are fast,
and scores between the cuts are middle. Fable and Opus remain explicit frontier
families when a benchmark row is absent. Luna is an explicit policy exception:
it is never frontier; a measured Luna score can place it in fast or middle, but
never above that policy boundary. `list_models` returns the
resolved cuts, score and `classification_source` for every live model.

Read the list with the LhcPlan MCP tool `list_models` (CLI `lhc_model_list.py`). When Agent Herder answers it adds Herder's live catalog and provider quota states; without Herder it works from the configured examples.

Workers only from these classes. Map the class to an exact catalog ID
before dispatch (`lhc_models.py suggest`); never substitute silently. A provider with under 20% allowance
left is not used for council, frontier work or an Adviser unless the owner says
so. A Worker does not delegate unless L authorizes a bounded child; a
no-delegation leaf hires no reviewers.
