# Project (written once by the owner; agents read it first)

owner: me
# me = this is the owner's own repository: PRs go to main and merge when green.
# Otherwise the name of the external owner, e.g. "Oleg (Airlock)".

target: main
# Branch your PRs go into. In someone else's repository: the owner's own branch,
# e.g. megamen32-dev. Never the external owner's main.

dev: <how to deploy for testing, and the URL testers use>
# Agents may deploy here without asking. Production is never implied.

deploy: blue-green
# blue-green = new color beside the old one, tests pass on it, traffic switches, rollback is a switch back.
# Use simple only for what has no external clients.

notes:
# Anything the owner wants every session to know about this project.
