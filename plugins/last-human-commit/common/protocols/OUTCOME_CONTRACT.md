> Background reference. AGENTS.md wins. The outcome contract is a canary, not ceremony.

For ordinary engineering, record the intended consumer action and the observable result. One
focused canary/readback is enough for a bounded change. Independent testers, publication
manifests, ACKs and integration receipts are required only when the owner explicitly asks for
a release/high-risk review. Unknown destructive effects still require target-state checking.
