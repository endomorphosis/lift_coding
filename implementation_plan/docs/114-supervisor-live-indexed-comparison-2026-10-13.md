# Fresh native and indexed supervisor benchmark

Three fresh Docker trials on Terminal-Bench `largest-eigenval` passed the original
verifier. Indexed supervision used 6.84% fewer reported native tokens than
no-index supervision, but 2.93 times native Codex's tokens. This pilot therefore
does not show an overall token advantage over the native harness.

| Harness | Reward | Reported native tokens | Agent execution | Agent setup |
| --- | ---: | ---: | ---: | ---: |
| Native Codex | 1.0 | 113,883 | 181.69 s | 99.44 s |
| No-index supervisor | 1.0 | 358,492 | 443.08 s | 333.58 s |
| Indexed supervisor | 1.0 | 333,973 | 271.76 s | 235.39 s |

All used GPT-6.1-sol, high reasoning effort, CLI 0.160.0, five CPUs, 20 GiB,
matching task inputs and outer time limits. Supervisor calls used `llm_router`;
the native arm used Harbor's Codex adapter. Grok's isolated metadata check refused
authentication, so all attempts used the explicit Codex fallback. The order was
no-index, indexed, native, with one attempt each and zero harness retries.

Cached input is already included in input. Each native session contributes its
final cumulative counters once. Auxiliary refresh accounting is incomplete, so
the table is reported native usage, not exhaustive pipeline cost or billing.
Native lacks the numerical-profile selection and separate supervisor planning
and coding budgets. Those intended differences remain explicit; the production
generic comparator still reports the numerical-profile mismatch.

The indexed arm spent 6,561 more planning tokens and 31,080 fewer coding tokens
than no-index. It hydrated three DuckLake catalogs, three links and one world
record, reused four indexed symbols, and delivered four worker capsules. Eight
pending numerical hints reached the live planner. The model made zero optional
numerical retrieval requests, and all 105 obligations remain unresolved.

The pinned Source384 checkpoint produced four unsupported candidates with zero
training steps. IntentIR had no checkpoint selected and the Doctor abstained.
Fresh numerical and Source384 successors were unavailable after code publication.
These are remaining coverage and state-maintenance gaps. Source views were
disabled; whole-codebase minification and parallel agent speedup were not tested.

## Observer repair and qualification

Both supervisor trials lacked output hashes at the allocation-event observation
stage. A valid queued native completion omits immediate lifecycle finalization;
the observer now accepts it only after joining one later resolved reconciliation
with matching identities. Settlement, owner custody, cleanup and path checks
remain mandatory. The observer does not grant execution, merge or proof authority.

**132 distinct tests passed**, including 31 new queued-event cases. The same
suite passed after integrating concurrent upstream changes. The artifact
collectors separately passed 47 test nodes and 32 additional subtests. Independent
reviews replayed the three outcomes and checked the publication's 62 sealed files.
The observer fix was made after these live trials; their missing hashes remain
unknown, and a future run must qualify actual byte capture.

The accelerator change and report are published at
[`4ea2271709`](https://github.com/endomorphosis/ipfs_accelerate_py/commit/4ea2271709bf697f175a198d3df02ac1e1a38205).
See the [implementation report](https://github.com/endomorphosis/ipfs_accelerate_py/blob/4ea2271709bf697f175a198d3df02ac1e1a38205/docs/agent_supervisor/live_indexed_baseline.md)
and [sealed evidence](https://github.com/endomorphosis/ipfs_accelerate_py/blob/4ea2271709bf697f175a198d3df02ac1e1a38205/docs/agent_supervisor/evidence/numerical-live-comparison-20261013/README.md).
The evidence-manifest SHA-256 is
`0d2db4998a0cd2e8f62628f43790594257dc11a772a48611dfdf78ffc085d9b0`.

The live runtime used accelerator `a8f57366ff4110a87f1f13d1e60992f83f689821`,
datasets `28b9ef1f0b9da51e87b1e68ee565b43681397109`, and Kit
`8ac00bb1974b1378e12091d546d8425af34049e0`. This parent update advances the
accelerator gitlink and preserves the concurrently published datasets gitlink
`7e60814a93fb81604092a0e0627fbc1996e644b7`; it does not relabel that later
datasets revision as the benchmarked runtime. Exact pins and independent reviews
are retained in the [publication bindings](../../artifacts/numerical-live-comparison-publication-20261013/bindings.json).

All four local documentation workflow checks and 12 explicit report links passed.
Hosted [documentation run 38454447599](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38454447599)
failed before executing any steps: GitHub reported an account billing lock,
with runner ID zero. The [CI receipt](../../artifacts/numerical-live-comparison-publication-20261013/hosted-ci.json)
records that external limitation separately from local validation.
