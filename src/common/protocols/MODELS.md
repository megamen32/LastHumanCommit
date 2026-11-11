# Models

LhcPlan `list_models` reads the curated assignments in `config/models.json` and adds the live Herder catalog and quota telemetry when available. The classes are `fast`, `middle` and `frontier`. Use the cheapest suitable class for the actual task.

The current configured set contains thirteen IDs. Luna is fast; Fable, Opus, Astra and Sol are frontier families. Benchmark measurements describe performance and do not reclassify a configured assignment. Read the catalog instead of guessing a new version's API ID.

Use `model-routing` for assignment context and native execution, and `model-availability` for provider units and the 20% reserve on council, Adviser and frontier work. Preserve the user's account and provider choice.
