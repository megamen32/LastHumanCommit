Blackbox better than integration
Integration better than unit
Unit? good only if fast : <3 sec and written Red first, Green last (or write latter but must check via git stash)
You can mock freely on internal, BUT if you mocking external, you must wrute BLACKBOX test to verify mock structure will not outdated with reality. But depth 3 tests prohibited(tests for testing tests)

Any Test must be complete < 30s. 
All tests must has fewest flags possible, all flags must be described in one place. good start: E2E(long, can use network, write files etc), FAST(safe enough) ,SMOKE(unit,mock, readonly). opt-in TEST4TEST

Must be at least one command to run all tests. Best effort read-only. opt-in fast only [smoke].  