# LHC landing / auto-sync

The public site is a **build-time view of the current checked-out LHC source**, not
another copy of the role definitions. Every push to `main` runs
`.github/workflows/pages.yml`, regenerates `site/dist/data.json`, and deploys
the self-contained static site on GitHub Pages.

The build reads:
- `docs/PRODUCT_CONCEPT.md` — canonical product concept and stable-ID lifecycle sections used by both Quick and Full.
- `templates/FULL_CYCLE.md` — the conditional material-decision method shown as a depth inside Full.
- `plugins/last-human-commit/plugin.json` — displayed product version.
- **Every** `src/common/agents/*.md` — role cards, classifications, summaries and verbatim definitions.

All citations link to the exact Git revision used for the generated snapshot. Workflow
labels are translated by stable lifecycle IDs; source excerpts and role documents
remain in their original language. No credentials, runtime LHC code, server process,
third-party UI libraries or extra package manager are needed.

Run locally from the repository root:

```sh
python3 -m unittest discover -s site -p 'test_*.py' -v
python3 site/build.py
python3 -m http.server --directory site/dist 8000
```

Open http://localhost:8000. The output directory `site/dist/` is generated
and ignored by Git. The Pages environment must be configured to use **GitHub
Actions** as its build/deployment source once in repository settings. An
optional manual `workflow_dispatch` can deploy a verified preview branch;
ordinary pushes to main automatically keep the site in sync.

## English / Russian interface

The header language switch updates the whole UI without reloading. The initial
language is an explicit `?lang=en` / `?lang=ru` URL choice, then the locally saved
preference, then the browser language (Russian or English fallback). The switch
still works if browser storage is disabled; it also preserves the selected cycle,
current stage and expanded role cards.

`site/i18n.js` contains site copy, stable-ID workflow labels and accessibility translations.
Canonical agent names, Markdown role definitions and Git source excerpts are
shown in their original language, explicitly labeled, and never translated or
duplicated into language-specific documentation. Git continues to provide one
source of truth. `locale.css` accommodates the longer Russian UI labels.
The build fingerprints CSS/JavaScript assets to avoid mixing cached versions.

`python3 -m unittest discover -s site -p 'test_*.py' -v` includes checks for source
preservation, language-asset packaging and every generated loop label/description
having both translations. Dictionary validation uses Node when available.

## Landing v2: the complete development cycle

`site/story.py` reads `PRODUCT-PHILOSOPHY.md` at build time. Full Cycle unfolds
into 14 source-backed stages; Quick Loop keeps a short plan, execution, real-use
verification and integration. Each stage links to the exact commit and source
lines. Missing canonical sections fail the build instead of publishing stale
content. The existing five-stage lifecycle metadata remains available.

The landing distinguishes intended method from implementation status and links
to the canonical list of remaining gaps. Agent branches and task timelines are
illustrations, not live telemetry. Role names, summaries and full definitions
are preserved from Git in their original language; the interface is EN/RU.
No LHC runtime or canonical product-document changes are needed.

Optional interactive verification (Node 22+, Chrome; no npm dependencies):

```sh
python3 site/build.py
node site/browser-check.mjs
```

This checks both languages and both routes across 320–1440 px, exact source
content, keyboard controls, selected-stage and role-card preservation, stored
language, disabled storage and honest translated data failures. Screenshots
are written to ignored `.tmp/`, not included in the published site.
