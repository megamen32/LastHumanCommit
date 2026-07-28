# Infrastructure profile

Load only for infrastructure, networking, ingress, host access, service
recovery, deployment, or reliability work.

1. A reported outage or inaccessible critical host/service becomes P0 and
   interrupts architectural expansion.
2. Inspect live state and the canonical source of truth in parallel before
   changing anything. Live files are deployment targets, not a second source.
3. Restore the smallest safe user-visible path first. For resilience, use an
   independent failure domain, not another endpoint on the failed path.
4. Prove P0 end-to-end from an external or user-relevant source. Record source,
   ingress, backend, expected response, failed domain, and proof that the request
   bypassed it. Config validation, listeners, local curl, and service status are
   insufficient alone.
5. Prefer forward-fix. Before risky live changes preserve current state, define
   the verification gate, and retain an emergency recovery command. Roll back
   only to stop active damage, data loss, or a security event.
6. Break-glass changes must be minimal and immediately verified, then moved into
   the canonical source and committed.
7. Do not build a universal recovery platform before the concrete P0 service is
   restored and proven.
