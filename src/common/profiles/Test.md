# Test profile

Load only for test design, test repair, or validation work. This supplements the
assigned role and never changes agent identity.

Blackbox better than integration
Integration better than unit
Unit? good only if fast : <3 sec and written Red first, Green last (or write later but verify the failing condition first)
You can mock freely on internal, BUT if mocking external, write BLACKBOX test to verify mock structure will not become outdated. Depth-3 tests are prohibited (tests for tests).

Any Test must be complete < 30s.
All tests must has fewest flags possible, all flags must be described in one place. good start: E2E(long, can use network, write files etc), FAST(safe enough) ,SMOKE(unit,mock, readonly). opt-in TEST4TEST

Must be at least one command to run all tests. Best effort read-only. opt-in fast only [smoke].

A test already failing before you arrived is no excuse to ignore it or leave it
stale. Finish the requested work and its bug fixes first, then repair or update
that test too.

At release completion, close resolved bug files. Retain unresolved bug files
with their exact blocker; do not hide them to make the task appear complete.
