# Validation baseline fails

Description: The declared validation gate fails on trailing whitespace in the
current README.
Evidence: `python3 tests/validate.py` exits 1 at `README.md:11`;
`git diff --check` reports lines 11 and 13-17.
Blocks: `.agents/tasks/work-20260730-text-canon-yagni.md`

