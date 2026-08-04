# Code profile

Load only for code changes. This supplements the assigned role and never changes
agent identity.

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

- Use explicit types and explicit errors.
- Do not write code to /tmp, instead: project cwd `.bin/`; move repeated code to a permanent module.
- Do not reinvent a dependency when a proven standard solution can be used.
- Check standard libraries before adding code or dependencies.
- Use f-strings in Python.
- Prefer pure functions. Use OOP when state is required.
- Use YAGNI; change an existing workaround only when required by the confirmed
  outcome or canary.
- Prefer dependency-free Python over shell scripts when practical.
- Check cross-OS behavior only when the confirmed outcome claims portability.
