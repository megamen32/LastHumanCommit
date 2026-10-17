# LHC OpenCode review-to-delivery — 2026-10-17

User outcome: OpenCode 2 on server-100, including OpenChamber's shared backend, must automatically load current LHC without @LHC, preserve original/latest goals through compaction and steer from a completed code review to permitted release/real result instead of repeated review receipts. Maintain TDD, honest uncertainty, hourly direction/120m self-improvement and milestone Zero Knowledge. Never restart a user's running session or TGC/AFC production and do not change unrelated model/MCP/auth settings.

Isolation: own worktree / branch lhc/opencode-review-delivery. Start with RED regression on native OpenCode v2 hooks; implement minimal adapter/source changes, run full Python and Bun suites, then PR/merge and versioned installation; real new native OpenCode canary is final acceptance.
