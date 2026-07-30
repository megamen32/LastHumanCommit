# Local environment file is exposed to accidental staging

Description: `.env` exists untracked and is not ignored. Its contents were not
read.
Evidence: `git status --short` lists `?? .env`; `git check-ignore .env`
returns no match.
Blocks: `.agents/tasks/work-20260730-text-canon-yagni.md`

