# Generalize workflow benchmark topology

Status: complete
Original user request: Do not force every workflow into the LHC five-role topology. Support zero, one, two, or three model levels and judge each workflow by its declared topology; if model selection is unspecified, choose the best available models for the test run and record the choice.
Objective: Make the public benchmark compare workflow topology as declared, including the user's smart Adviser -> medium Lead -> cheap Worker design, without requiring parallelism or extra models.
Business canary: The public protocol and campaign config can describe and score 0/1/2/3-level workflows without silently adding roles.
Confirmed scope: `/home/roomhacker/agents-projects/agent-workflow-benchmark/README.md`, `docs/PROTOCOL.md`, `docs/RESULT_SCHEMA.md`, `configs/campaign.yaml`.
Explicit exclusions: no LHC source changes, no new paid model runs, no Superpowers rerun, no Sol generation.
Initial estimate (minimum / maximum active minutes): 10 / 20.
Acceptance: protocol, schema, and campaign config agree on topology cardinality, fallback model selection, and separate quality/time/cost metrics; public repo is pushed.

## Role

Role: Worker. Read and edit only the assigned public benchmark paths. Append detailed evidence and result here; return L only TL;DR.

## Evidence and result

- Replaced the mandatory five-role topology with a declared ordered topology of zero to three model tiers.
- Explicitly preserved one-model and two-model workflows; no synthetic Worker, Adviser, or parallel lane is added.
- Separated topology from parallelism: sequential delegation uses `mode: sequential` and `max_concurrent_children: 1`; actual child count is recorded independently.
- Added fallback policy: when the workflow has no model-selection rule, use the strongest available model inside the selected cheap/normal budget profile and record the fallback.
- Added pricing precedence: provider-effective cost, official provider price, dated `models.dev` snapshot, then `null`; missing price is never `$0.00`.
- Updated `README.md`, `docs/PROTOCOL.md`, `docs/RESULT_SCHEMA.md`, and `configs/campaign.yaml`. YAML parsing and `git diff --check` pass.
- Shortened README to a workflow-first product statement and added `docs/WHY-BENCHMARKS.md` with the source chat and rationale.
- Selected scoring pack: Quorum/Superpowers Evals for primary behavioral coverage, AI Workflow Benchmark for independent real-repo confirmation, and SkillsBench for features→skills migration. ECC is methodology; gstack and Spec Kit/GSD/OpenSpec/BMAD/wshobson are surveyed references, not scoring corpora.
- Primary ranking is quality plus cost per successful task; speed is secondary, tokens diagnostic. Zero successes produce no price ranking.
- The public pilot report now lists all five behavior scenarios and states that local full artifacts are preserved but not yet published until redaction and release-asset publication; no fake transcript URL was added.
- Read-only size check: pilot result directories are about 1.0 GiB uncompressed; one 259,134-byte JSON transcript compressed to 63,046 bytes (24.3%).
