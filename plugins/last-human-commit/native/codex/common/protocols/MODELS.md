# Models

Three classes. Name the class in every assignment; take the cheapest class that passes acceptance.

| Class | Use it for |
|---|---|
| fast | routine: research, search, reading, polling, waiting, mechanical edits |
| middle | code written by a ready plan; while no model is listed, use fast, and frontier only after a measured fast failure |
| frontier | architecture, hard problems, work that dragged on past its estimate |

The model list lives in `config/models.json`; read it with the LhcPlan MCP tool `list_models` (CLI `lhc_model_list.py`).

Workers only from these classes. Map the class to an exact catalog ID
before dispatch (`lhc_models.py suggest`); never substitute silently. A provider with under 20% allowance
left is not used for council, frontier work or an Adviser unless the owner says
so. A Worker does not delegate unless L authorizes a bounded child; a
no-delegation leaf hires no reviewers.
