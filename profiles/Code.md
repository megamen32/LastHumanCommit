# Code profile

Load only for code changes.

- In Python, use f-strings instead of percent formatting.
- Split code files that exceed 800 lines unless they are generated, vendored, or
  constrained by an external format.
- Check syntax and prefer an integration test that exercises the changed
  behavior; unit tests alone are insufficient when the behavior crosses a real
  boundary.
