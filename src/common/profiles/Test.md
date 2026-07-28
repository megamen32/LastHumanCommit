Blackbox better than integration
Integration better than unit
Unit? good only if fast : <3 sec and written Red first, Green last (or write latter but must check via git stash)
You can mock freely on internal, BUT if mocking external, write BLACKBOX test to verify mock structure will not become outdated. Depth-3 tests are prohibited (tests for tests).

Any Test must be complete < 30s.
All tests must has fewest flags possible, all flags must be described in one place. good start: E2E(long, can use network, write files etc), FAST(safe enough) ,SMOKE(unit,mock, readonly). opt-in TEST4TEST

Must be at least one command to run all tests. Best effort read-only. opt-in fast only [smoke].

A test already failing before you arrived is no excuse to ignore it or leave it
stale. Finish the requested work and its bug fixes first, then repair or update
that test too.

If bug files still exist when you think the work is done, process them. No bug
files may remain at the end.
