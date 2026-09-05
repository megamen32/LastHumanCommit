# Infrastructure profile

Load only for infrastructure, networking, ingress, host access, service
recovery, deployment, or reliability work. This supplements the assigned role
and never changes agent identity.

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

1. When the confirmed objective is recovery from a reported outage or an
   inaccessible critical host/service, treat that recovery as P0 and interrupt
   architectural expansion within the confirmed scope.
2. Inspect live state and the canonical source of truth in parallel before
   changing anything. Live files are deployment targets, not a second source.
3. Restore the smallest safe user-visible path first. For resilience, use an
   independent failure domain, not another endpoint on the failed path.
4. Prove P0 end-to-end from an external or user-relevant source. Record source,
   ingress, backend, expected response, failed domain, and proof that the request
   bypassed it. Config validation, listeners, local curl, and service status are
   insufficient alone.
5. Prefer forward-fix. Before a risky live change, define its verification gate.
   Do not design a rollback, backup, or recovery mechanism unless the user
   explicitly requests it; if a rollback, restart, or destructive action is
   necessary, ask the user directly at that boundary.
6. Break-glass changes must be minimal and immediately verified, then moved into
   the canonical source and committed.
7. Do not build a universal recovery platform before the concrete P0 service is
   restored and proven.
