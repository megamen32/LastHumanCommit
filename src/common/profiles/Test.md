# Test profile

Load only for test design, repair, or validation. Tests support the accepted
business claim; they do not define a stronger product by themselves.

## Proof selection

Choose the cheapest evidence sufficient for the exact claim:

- use the real user/business canary when the claim is user-facing;
- use a black-box check for an interface or process contract;
- use integration tests for component interaction;
- use focused unit tests for local behavior and cheap regression protection;
- use source/build/type checks only for the narrower properties they prove.

For every bugfix, mandatory TDD applies: before changing production source,
write and run a focused regression that fails for the reported behavior. Record
the exact failing command and its Red result, then rerun it Green after the
smallest fix. A real canary remains required when the claim is user-facing, but
it does not replace the regression.

Run the narrowest decisive check first, then only direct-regression checks whose
expected defect value exceeds their runtime and maintenance cost. Broad suites,
mock-contract tests, portability matrices, and exhaustive edge cases are
optional unless the changed blast radius or release claim justifies them.

An unrelated pre-existing failure does not authorize repair. Report it and keep
working only when it does not invalidate the accepted proof. Never use a green
unit/build result as a substitute for a requested real business path.
