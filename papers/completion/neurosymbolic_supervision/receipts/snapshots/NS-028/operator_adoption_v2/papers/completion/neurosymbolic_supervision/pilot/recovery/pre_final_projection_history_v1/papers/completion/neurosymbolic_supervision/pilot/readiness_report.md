# NS-016 pilot readiness and pre-final freeze

Generated at 2026-09-12T07:59:14.422006+00:00. This is a developmental/pilot readiness
record and a hashed pre-final freeze. It is **not** a Table 17 result, not a
matched A–D efficacy comparison, and not authorization to start NS-017/018.

## Population and split isolation

NS-005 recruited 16 live families against a preregistered target of 24. This
task issues versioned amendment `ns-016-prefinal-population-and-readiness/v1`
without silently relabeling ns-core-v1.

| Split | Families | Live tasks | Role in this freeze |
|---|---|---|---|
| development | 4 | ns-hist-01..04 | Developmental. Excluded from final holdouts. |
| pilot | 4 | ns-hist-05..08 | Developmental/pilot. Excluded from final holdouts. |
| final | 8 | ns-hist-09..16 | Frozen holdout. No final attempt started. |
| missing vs planned 24 | 8 | — | Not filled from leftovers. |

Pilot and development family IDs are disjoint from the eight final families.
`ns-dev-boundary-add` is an NS-006 embedded fixture, labeled developmental,
and is not a live historical repair.

Freeze SHA-256: `ce60e7aa7981bef597f9bd4704b82816412772a6d804c3c9224eaf4f8752cea4`

## What was actually run

1. Developmental fixture `ns-dev-boundary-add` for all six arms and both local
   cache profiles (12 units), each independently rescored by `score_runs.py`.
2. Interruption after provider reservation/receipt on arm A/local_cold, then
   resume of the same ledger (duplicate dispatch prevented).
3. Host-handoff import of the existing NS-026 grant
   `ns-hist-01-xmltodict` / A / local_cold / development, independently
   rescored. No new HTTP POST.
4. Host-handoff probes of the other 15 development-split A–D/local_cold cells.
   The adapter raised or returned unavailable without a grant. No new HTTP POST.
5. Grant lookup for all 48 pilot-split cells (`record_kind=pilot`). Every lookup
   returned no grant. One runner probe of `ns-hist-05-dnspython` on the
   development path confirmed live historical tasks cannot use the stub path.
6. Harness `admit_final_attempt` on `ns-hist-09-tomlkit` / final: **refused**.

Fixture solved independently scored units: 12 / 12.
Live historical independently scored solved units: 1
(expected: the single xmltodict A grant).

## Retained arms and claim updates

Each arm has a **developmental fixture** useful path with completed independent
scoring. That path uses the NS-006 deterministic stub provider. It validates
receipt completeness, oracle isolation, arm context packing, and interruption
handling. It is **not** a live residual repair and is excluded from live-repair
denominators.

Live independently scored historical useful path:

- A / ns-hist-01-xmltodict / local_cold / grok-4.6 / hidden 1 passed, visible 34 passed.

No live independently scored historical useful path exists for B, C, D,
C-no-route, or C-no-reuse. The host service still rejects pilot/final units.
This freeze therefore **removes all six arms from the executable final
comparison** and sets `final_dispatch_authorized=false`.

Claim updates recorded in the freeze:

- Table 17 A–D cells remain unfilled.
- Ablation arms are not executable.
- Abstract useful-completion / net-cost placeholders cannot be replaced.
- NS-017/018 stay blocked until a later versioned freeze restores arms after
  live independently scored useful paths, host admission, reservation, and
  deadline/cost fit.

## Receipt completeness and missing resources

Every pilot result row carries the Table 17 measurement object. Unmeasured
fields are `unavailable` with a reason and a null value. They are not zero.

Honest unavailable statuses:

| Resource / identity | Status | Reason |
|---|---|---|
| NS-004 Terra HIGH (`gpt-5.6-terra`) | unavailable | Docker/Codex absent from sealed PATH; no verified Grok quota exhaustion |
| Scientific production reservation | unavailable | No native container/CPU reservation obtained |
| Pilot/final host grants | unavailable | Adapter lookup rejects; profile has one development grant only |
| Immutable weight revision | unavailable | Fingerprint is operational metadata, not a snapshot revision |
| Settled currency charge | unavailable | API ticks are not a billing receipt |
| Aggregate remote CPU/memory for the historical grant | unavailable | Signed receipt does not include those aggregates |
| Sampling seed / temperature controls | unavailable | Not exposed; not asserted set |
| Adversarial scorer observation integrity | unqualified | NS-026 trust limit preserved |
| anyio in sealed validation | not assumed | Judge the validation environment, not this process |
| Deadline fit for 192–384 final units | does not fit | Paper due 2026-09-13 AoE; serial 420 s × 192 units exceeds remaining time even before setup |

Fixture runs do produce actual host CPU, elapsed, RSS, and independent scoring
times. Those numbers describe the stub path, not a live historical bill.

Table 18 retained boundaries (provider, translation, fixture lifecycle, restart
publication) already have NS-007–013 qualification evidence. Native/world
rows remain unavailable/out of scope (NS-014/015). This freeze does not
convert qualification into Table 17 cells.

## Feasibility versus remaining deadline

Preregistered final load at 16 families × 6 arms × 2 repetitions × 2 cache
profiles is 384 units. The recruited freeze has 8 final families (192 units if
later authorized). Upper-tail fixture elapsed is under one second because the
stub does not call a model. The one live development proposal used 75.348 s
provider elapsed plus 0.919 s scoring, excluding operator review. Scaling 75 s
× 192 units is about 4 serial hours of provider time alone, plus scoring,
setup, and the missing 15 live development and 48 pilot cells that still need
grants. Remaining workshop time (paper 2026-09-13 AoE, today 2026-09-12) does
**not** fit a complete live A–D campaign, host-service rewrite, and
independent analysis. Readiness is **not ready**.

## Immutable pins (hashed before any final attempt)

No final attempt was started. Pins:

- `e1e3403feafa0eb5c8bbda4b95e14e3415a92d2036182725784f30788d4e5e54` `papers/completion/neurosymbolic_supervision/protocol/preregistered_protocol.md`
- `5d0bd610005cfd68e67f6f1dc4224a83bd9773b72d8e2aaf700fdec53883b649` `papers/completion/neurosymbolic_supervision/protocol/experiment_manifest.json`
- `e20f70ba7c055e9fdbbcd1540ce13213733dd3f3810d44a23c1f9f0b24064e03` `papers/completion/neurosymbolic_supervision/protocol/measurement_schema.json`
- `00f4fc0512506510dfbf2433c48d029b74a8207015a55c24094bcf5d11205029` `papers/completion/neurosymbolic_supervision/protocol/development_provider_amendment.json`
- `5fe9f2d4e65938c5404f6ed3880144906f6212c05a72c85d078f34dbb4870dc4` `papers/completion/neurosymbolic_supervision/protocol/scope.md`
- `b4bc032e96abdde60bd9545e91ac866b72249c12992b4c00444f8350c3d9aba5` `papers/completion/neurosymbolic_supervision/protocol/deadline_plan.md`
- `3bec8e71f4da8f545a5a39d170c0646f3a3dfbc248295ff54fd2e6a06fd0fbb6` `papers/completion/neurosymbolic_supervision/benchmark/tasks.jsonl`
- `10017366a0e7e02304eac7146adf9fb98ae60f0902d44d4f2cd1be031f837f60` `papers/completion/neurosymbolic_supervision/benchmark/splits.json`
- `37057f559b36f48633b2fb2275aaf2d8d8cbbf267104a5833424d883943c4043` `papers/completion/neurosymbolic_supervision/benchmark/oracle_manifest.json`
- `fbee22fde5261b19e3816e9908a23087f7708b2f915dcc86f002278efd140207` `papers/completion/neurosymbolic_supervision/benchmark/provenance.md`
- `c2fab2dc40fe54b58a14002872214cc7acd8297a7d2aeee1ea43a18c20e7564a` `papers/completion/neurosymbolic_supervision/artifacts/source_forest.json`
- `6bc348d5f56ac32ea68704a10a478293786cf53da3a8371fbb534d75cd4df509` `papers/completion/neurosymbolic_supervision/experiments/run_comparison.py`
- `5e80572e51e0609d06fd1842694da5a0753ebdd66aa6c27bb3c50eca9abab158` `papers/completion/neurosymbolic_supervision/experiments/score_runs.py`
- `1314986d2798253ca4ec23da067acb68a2b13dcc4b1daee9cb1426fc30697fe3` `papers/completion/neurosymbolic_supervision/experiments/production_gateway.py`
- `b07b2aea54bfd81cb3a0f8ac7d876216632cc1907e69586848b7226ccb86ec12` `papers/completion/neurosymbolic_supervision/experiments/production_profile.json`
- `1170a73efe8256cef0cf3ed841c328c81d84eb2df555e27f7b8ccadc840dbde0` `papers/completion/neurosymbolic_supervision/experiments/receipt_schema.json`
- `aa635c70eb1a45338d5cdc229d6f42e03f05cf88a93ff6553faf11d8eb56f874` `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py`

Final-run manifest SHA-256: `8d9bcd2d41e4fd966ad4be719569a827431b6bcf541a3e5f90e1802f3eaee9de`

## Harness freeze gate

`semantic_state.harness.admit_final_attempt` now refuses final dispatch unless
the freeze hash matches, developmental tasks are excluded, retained arms have
independently scored useful paths, resources are reserved, and
`final_dispatch_authorized` is true. This freeze leaves that flag false.

Interrupt/resume: `{"crash_returncode": 75, "duplicate_dispatch_prevented": true, "replayed": false, "resume_exists": true, "resume_returncode": 0, "resumed": true, "schema": "paper-ns-pilot-interruption/v1", "terminal_state": "solved"}`

Provider probe production.admitted=True
admission_scope=operator_historical_development_only
final_admitted=False

## Limitations

- Fixture useful paths are not live historical repairs.
- The xmltodict result is one AI-operator-reviewed development candidate.
- This process did not rewrite the host adapter (outside NS-016 edit scope).
- Validation must be judged on the sealed PATH `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin`.
