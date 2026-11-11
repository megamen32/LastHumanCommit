---
name: real-use-testing
description: Run a proportional real consumer canary after a change. Use independent testers only for explicit release, high-risk user-facing work, or when requested.
---

# Real-use testing

A real canary is the shortest path to knowing whether the changed behavior works.

For a bounded change:

1. start the intended consumer or isolated test target;
2. perform the changed user action;
3. read the observable result;
4. record the exact failure or success.

A quickfix or assigned leaf does not require a fresh independent Tester. The Lead's canary is
valid when it exercises the changed path. Use independent testers for explicit release/high
risk work or when the owner asks for them. Do not launch tester sessions merely to satisfy a
milestone, receipt or reviewer count.

Do not read secrets or private data outside the test scope. Do not repeat an external mutation
after an unknown result until the target state is checked. These effect-level rules remain
active; process gates do not.
