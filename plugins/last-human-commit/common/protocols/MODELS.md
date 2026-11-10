# Models

Three classes. Name the class in every assignment; take the cheapest class that passes acceptance.

| Class | Use it for |
|---|---|
| fast | routine: research, search, reading, polling, waiting, mechanical edits |
| middle | code written by a ready plan |
| frontier | architecture, hard problems, work that dragged on past its estimate |

The authoritative assignment set is exactly the curated twelve IDs in
`config/models.json`: four fast, four middle and four frontier. Fable and Opus
remain frontier families, and Astra and Sol are explicit frontier families for
new versions. Luna is not in the curated set and is never frontier. The coding
benchmark manifest supplies measurements only; it does not promote an unknown
live catalog entry into a tier. `list_models` returns the curated assignment,
the measured score when available, and the resolved benchmark cuts separately.

Read the list with the LhcPlan MCP tool `list_models` (CLI `lhc_model_list.py`). When Agent Herder answers it adds Herder's live catalog and provider quota states; without Herder it works from the configured examples.

Workers only from these classes. Map the class to an exact catalog ID
before dispatch (`lhc_models.py suggest`); never substitute silently. A provider with under 20% allowance
left is not used for council, frontier work or an Adviser unless the owner says
so. A Worker does not delegate unless L authorizes a bounded child; a
no-delegation leaf hires no reviewers.
