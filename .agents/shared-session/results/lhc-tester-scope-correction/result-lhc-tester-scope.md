# Result: Full Tester scope correction

Full now requires two final passes: an informed `blast-radius` pass and a
`zero-knowledge` blind typical-user pass. Only the second pass is blind.

Verification: `python3 tests/validate.py` and `cmp -s AGENTS.md CLAUDE.md` passed.
