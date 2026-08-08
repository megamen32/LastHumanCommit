# Test profile

Load only for test design, test repair, or validation work. This supplements the
assigned role and never changes agent identity.

## Scope gate

- This profile constrains work inside the exact user-confirmed objective and
  acceptance canary; it never adds deliverables, audits, repairs, migrations,
  hardening, or follow-up work.
- Apply a rule below only when it is necessary for that objective or is the
  minimal safe prerequisite for running its confirmed canary.
- Do not initiate security, secrets, PII, permissions, ACL, database, schema,
  Grafana, dashboard, observability, log, or provider work unless the user
  confirmed it or it is that minimal safe-canary prerequisite. Record and keep
  any prerequisite exception as narrow as possible.

Blackbox better than integration
Integration better than unit
Unit? good only if fast : <3 sec and written Red first, Green last (or write later but verify the failing condition first)
You can mock freely on internal, BUT if mocking external, write BLACKBOX test to verify mock structure will not become outdated. Depth-3 tests are prohibited (tests for tests).

Any Test must be complete < 30s.
All tests must has fewest flags possible, all flags must be described in one place. good start: E2E(long, can use network, write files etc), FAST(safe enough) ,SMOKE(unit,mock, readonly). opt-in TEST4TEST

Must be at least one command to run all tests. Best effort read-only. opt-in fast only [smoke].

An unrelated failure that existed before this work does not authorize repair or
scope expansion. Repair it only when the owned change directly regressed it or
when it blocks acceptance of the confirmed objective or canary. Otherwise,
report the exact failure and leave it untouched.

At release completion, close resolved task files. Retain unresolved `todo-*` or
`work-*` files with their exact blocker; do not hide them to make the task appear
complete.
