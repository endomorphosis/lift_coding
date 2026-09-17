# Generated-code study preparation and finite execution plan

This folder adds a proposed LA-032 preparation task and begins read-only source
discovery. It does not change the frozen LA-030 package or native worktree,
register tasks, select the new cohort, release final cases, or call a model.

## Native stages

`LA-032.task.json` is a child of LA-031 under LA-G5. It requires actual source,
case/oracle, code-profile, model/runtime and durable-scheduler qualification,
then freezes the complete original 900-cell schedule. Its completion means
readiness, not execution of those cells. Model qualification is future work
using bounded development inputs and concrete pins.

`native_stage_plan.json` proposes 30 family-batch tasks, LA-033 through LA-062.
Each consumes one frozen source family: two paired cases × five arms × three
seeds = 30 cells, at most 3,600 scientific attempt seconds. This leaves setup,
cleanup and reporting room within the native 7,200-second worker ceiling.
There are six development, six calibration and eighteen final family batches.
The proposed LA-063 analysis-freeze task depends on all twelve development and
calibration batches. Every final batch depends on LA-063. LA-031 receives
explicit dependency edges to preparation, all thirty batches and the analysis
freeze before it can perform aggregate analysis and manuscript handoff.

The plan retains all 900 original identities and 540 final cells. No family is
assigned to a task yet. LA-032 must prospectively bind actual family IDs,
source/arm/seed identities and per-case arm rotations to these slots. It must
also document the phase/family execution order and its mapping to the original
schedule before outputs; grouping work into jobs must not silently change the
scientific protocol. Runtime limits do not authorize smaller denominators.

## Local source availability

`local_source_discovery.json` contains reproducible hashes and metadata only.
`discover_local_sources.py` reads local files and does not fetch or export
source bodies. It excludes all 30 historical families from the actual native
LA-004 manifest, including the union of 24 repository ancestry keys across
both CVE and SkillCenter populations.

| Population | Local source | Observed candidate inventory after old-family exclusions |
| --- | --- | --- |
| CVE | `papers/completion/runtime_bootstrap/la004_source_bridge/train-00000-of-00003.parquet` | 1,568 remaining canonical repository identities; original shard hash matches the retained source manifest |
| Skill | `papers/completion/runtime_bootstrap/la004_source_bridge/skillcenter-security.sqlite` | 1,163 distinct remaining GitHub repository, primary-source and normalized-body identities; original bundle hash matches |
| Legal | `/home/barberb/portland-laws.github.io/public/corpus/portland-or/current/raw/pages.parquet` and `canonical/STATE-OR.parquet` | 3,052 distinct Portland section source URLs, with original-source and canonical artifacts both present |

These counts establish availability, not eligibility or final selection.
Repository spelling alone does not establish fork/clone independence. The new
CVE and skill selections must also exclude overlap with each other. All 1,163
remaining skill rows carry model-generation metadata, so their procedures
cannot be described as independent human judgments. Bundle or dataset license
metadata does not establish permission to redistribute each upstream source.
The original source URLs, versions and applicable source terms must be checked
before release; this inventory exports no third-party bodies.

The Portland source jurisdiction differs from the six historical US Code
sections. A source lineage, cross-reference and cross-paper/model-exposure
audit remains necessary. The local `logic_proofs` derivatives are explicitly
described as generated candidates with simulated educational certificate
metadata; they are not independent utility or proof oracles and were not used
in this discovery.

The authoritative old source and split manifests are under:

```text
.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/benchmark/manifests/sources.json
.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/benchmark/manifests/splits.json
```

## Concrete next work

1. Register the additive preparation/stage dependency structure through the
   supervisor's normal source integration. Keep LA-031 blocked on actual
   children instead of relying on parent metadata or an open prose goal.
2. Define prospective inclusion criteria, verify upstream pins and lineage
   exclusions, then construct six legal, twelve CVE and twelve skill families
   with useful source-relative tasks and independent policy-relative oracles.
   Freeze all source families and splits before inspecting model outcomes.
3. Expand and qualify the actual generated-code/handler profile. A source
   reference attached to the two development sink names is insufficient to
   establish the original task distribution or useful task completion.
4. Finish model/runtime qualification. Require each response's measured
   `prompt_tokens` to equal its retained preflight `input_count`. Retain exact
   model/tokenizer/template/deployment pins and real bounded qualification
   calls. Reuse the model warm during active work under a 10,000-second total
   service wall and separate 360-second startup-readiness deadline.
5. Diagnose the native watchdog's retained v2 `resource_observation_OSError`.
   The old receipt proves termination/cleanup but does not retain errno or
   failing operation, so the exact cause is unproven. A new diagnostic path
   must retain operation/path/errno and leaf/parent identity. Any benign leaf
   disappearance handling must independently revalidate a stable, empty parent
   and monotonic counters; blanket error suppression is unacceptable.
6. Qualify a hard complete-attempt deadline and durable reservations, ownership,
   interruption/resume and reconciliation. Freeze all 900 identities and thirty
   family manifests, seal final material, and let the bounded batch tasks
   produce actual scientific receipts. Preserve every failure and unknown cost.

Outside annotations are not required for the existing automated
source-contract and policy-relative scope. Human legal validity or independent
semantic-fidelity claims remain outside that evidence.

To reproduce the discovery into a fresh output file:

```sh
python3 -B papers/revisions/law_study_preparation_20260914/discover_local_sources.py --output NEW_DISCOVERY.json
```
