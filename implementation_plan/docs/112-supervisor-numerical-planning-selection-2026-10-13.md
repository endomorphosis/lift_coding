# Supervisor numerical planning hints and selective retrieval

The v3 numerical planning summary now retains eight compact obligation hints
within the existing 8 KiB budget. Previously the public `largest-eigenval`
summary retained no inline pending rows. The new hints span four functions,
both files, both loops and all four loop proof phases. Exact-ID retrieval carries
those references through the supervisor owner, isolated worker client and shared
datasets pager, returning the unchanged complete pending row.

| Repository | Published revision |
| --- | --- |
| `ipfs_accelerate_py` | `a8f57366ff4110a87f1f13d1e60992f83f689821` |
| `ipfs_datasets_py` | `28b9ef1f0b9da51e87b1e68ee565b43681397109` |
| `ipfs_kit_py` (preserved) | `8ac00bb1974b1378e12091d546d8425af34049e0` |

The accelerator revision includes the previously published role-context
integration at `5ad92f61bb`. Both fresh Docker runs qualify the named production
snapshot against 514 source pins and four fixture pins. The datasets change adds
an exact optional filter without modifying grammar, logic, training or checkpoint
implementation files. Old v1/v2 summaries and captured unfiltered pages across
all three profiles replayed byte-for-byte; all public formalization reports are
unchanged. Changed consumer pins require normal context rebuilding.

See the published
[implementation report](https://github.com/endomorphosis/ipfs_accelerate_py/blob/a8f57366ff4110a87f1f13d1e60992f83f689821/docs/agent_supervisor/numerical_planning_selection.md)
and
[sealed evidence](https://github.com/endomorphosis/ipfs_accelerate_py/blob/a8f57366ff4110a87f1f13d1e60992f83f689821/docs/agent_supervisor/evidence/numerical-planning-selection-20261013/README.md).
The seal contains 72 files including its manifest, whose SHA-256 is
`df734a5b592b097b8e91da5bf476004c4cd67968d5046fc8be378630ac128659`.

## Measured delivery costs

| Scenario | Requests | Returned row instances | Request + response JSON bytes | Including one common summary |
| --- | ---: | ---: | ---: | ---: |
| Five authored inspections with function/kind filters | 7 | 8 | 42,008 | 50,072 |
| Same five complete rows with exact IDs | 5 | 5 | 26,954 | 35,018 |
| Separate exhaustive inventory | 56 | 105 | 404,290 | 412,354 |

The first two rows show a **30.1% reduction** including one 8,064-byte summary,
or 35.8% for request/response JSON alone. The summary itself grew from 7,614 to
8,064 bytes to retain useful references. IPC framing and CLI newlines have
separate recorded totals. This is neither total model-prompt cost nor a token
measurement. The exhaustive scan has a different coverage objective.

Selection reads only the public instruction and planner-visible hints. It
chooses one target-entrypoint hint and one per loop proof phase; unavailable
residual hints remain explicitly unselectable. These examples establish
transport behavior, not task relevance, proof sufficiency or benchmark success.
Existing-filter paging stops as soon as the desired row appears. Every selected
case is retained, and each scenario is independent without a response cache.

Both network-disabled containers exercised real DuckLake hydration (three
catalogs, three links and one world record), owner/worker UID separation,
`llm_router`, IPC, source freshness checks and cleanup. Complete numerical
summary bytes survived compiled worker and model-prompt transport. The production
planner request compiler separately accepted the same staged summary; Docker
planning and provider replies were authored. Full supervisor START, live model
selection, learned IR inference and the official verifier were not exercised.

All 105 obligations remain pending. Full rows retain guards, CFG occurrences and
proof phases; compact hints require retrieval before interpretation. No generated
source formula or checkpoint was changed, and no new Lake build was needed for
this retrieval-only change. The earlier loop-grammar qualification remains the
source for generated declaration checks.

## Validation and publication

**849 distinct tests passed**: 77 datasets pager tests and 772 accelerator
regressions. Two explicit checkpoint/GTE-dependent integration tests were skipped.
All 34 focused consumer tests are already included in that total. Independent
reviews checked omission accounting, source and cursor fences, complete-row
identity, actual owner-ledger request hashes, byte totals and public claims.

The first selected fixture attempt failed before worker dispatch because its
summary assertion treated an existing textual constraint as a mapping. The
fixture was corrected; selected02 and full01 then completed with unchanged
production quotas. Raw prompts, private databases, session descriptors and raw
broker/router logs remain outside the published seal.

Local documentation gates and explicit report/evidence links passed. Hosted
[documentation run 38372818362](https://github.com/endomorphosis/ipfs_accelerate_py/actions/runs/38372818362)
for the exact accelerator revision failed before running any steps: GitHub
reported an account billing lock, with runner ID zero. The
[CI receipt](../../artifacts/numerical-planning-selection-publication-20261013/hosted-ci.json)
and [publication bindings](../../artifacts/numerical-planning-selection-publication-20261013/bindings.json)
record that limitation and the qualified dependencies.

The next comparison should run the live supervisor with the same public task,
model and work budget, charge indexing, planning, retrieval and retries, and
check task success. These offline bytes alone cannot establish total token
savings or replace the earlier native benchmark scores.
