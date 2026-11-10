# Models

Three classes. Name the class in every assignment; take the cheapest class that passes acceptance.

| Class | Use it for |
|---|---|
| fast | routine: research, search, reading, polling, waiting, mechanical edits |
| middle | code written by a ready plan |
| frontier | architecture, hard problems, work that dragged on past its estimate |

Classes go by model family, not by version: any Fable, Opus or Luna is frontier. frontier = Astra, Sol, Fable, Opus, Luna; middle = GLM 5.3, Terra, Sonnet, Grok 4.7; fast = GLM 5.3 Flash, MiniMax 3.1 Flash, Haiku and Grok 4.7 Fast. The rules live in `config/models.json` (`families`, first match wins).

Read the list with the LhcPlan MCP tool `list_models` (CLI `lhc_model_list.py`). When Agent Herder answers it adds Herder's live catalog and provider quota states; without Herder it works from the configured examples.

Workers only from these classes. Map the class to an exact catalog ID
before dispatch (`lhc_models.py suggest`); never substitute silently. A provider with under 20% allowance
left is not used for council, frontier work or an Adviser unless the owner says
so. A Worker does not delegate unless L authorizes a bounded child; a
no-delegation leaf hires no reviewers.
