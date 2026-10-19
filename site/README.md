# LHC landing / auto-sync

The public site is a **build-time view of the current checked-out LHC source**, not
another copy of the role definitions. Every push to `main` runs
`.github/workflows/pages.yml`, regenerates `site/dist/data.json`, and deploys
the self-contained static site on GitHub Pages.

The build reads:
- `AGENTS.md` — canonical routing (Quick is a visual short path, not a mandatory new mode).
- `templates/FULL_CYCLE.md` — conditional material-decision path.
- **Every** `src/common/agents/*.md` — role cards and verbatim descriptions, including newly added roles.

All citations link to the exact Git commit behind the generated snapshot.
If required headings disappear, the build fails rather than publishing stale
workflow descriptions. No credentials, runtime LHC code, server process,
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
