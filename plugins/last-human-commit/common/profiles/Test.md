# Tests

Choose evidence that answers the question the change raises. Use unit tests for local behavior, integration tests for interacting components, and the actual app or CLI for a user-facing result.

For a bug, preserve a reproducible failure, make the fix and rerun the same scenario. Add or reuse a regression test at the layer where the defect occurs. A mock that only repeats the implementation is not useful coverage.

Run affected checks while editing and the project's applicable release checks before delivery. Repeat a check when the code, environment or hypothesis changed, or when investigating a flaky result. Record unrelated failures without turning them into a new project.
