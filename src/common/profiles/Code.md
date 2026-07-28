# Code profile

Load only for code changes.

- Use explicit types and explicit errors.
- Log errors and notify the operator:
  - S0: direct alert to the operator or webhook.
  - S1: a compact, structured log for AI review, with references (for example,
    by time) to S2 entries.
  - S2: normal traceable informational log.
- INFO/DEBUG are opt-out. Prefer structured logs and rotate them.
- Do not write code to /tmp, instead: project cwd `.bin/`; move repeated code to a permanent module.
- Do not reinvent a dependency when a proven standard solution can be used.
- Check standard libraries before adding code or dependencies.
- Ask whether external research is needed.
- Split code files over 800 lines unless generated or externally constrained.
- Use f-strings in Python.
- Document every function, including private ones: inputs, outputs, errors.
- Prefer pure functions. Use OOP when state is required.
- Build and test a concrete class before adding an abstraction.
- Use YAGNI, but remove old workarounds when the base design is wrong.
- Prefer dependency-free Python over shell scripts when practical.
- Keep project-owned config, services, environment, and logs visible in project;
  use symlinks or rsync for required OS paths.
- Check cross-OS behavior before claiming portability.
- Mark legacy or deprecated code explicitly as `LEGACY` or `DEPRECATED`, with a
  date and end-of-support target. If support has expired, create a TODO task.
