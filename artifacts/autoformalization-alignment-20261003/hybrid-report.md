# Source/formal candidate discovery — 2026-10-03

All **12 frozen checkpoint pairs, 60 paired comparisons, and the raw control completed**. Both fixed hybrid policies recover all **47 missing formal-retrieval outcomes** at the same final shortlist and demonstration budgets. Source-only discovery with the formal selector achieves the same coverage. The result supports the candidate-discovery diagnosis; it supplies no additional coverage benefit specific to fusion on this panel.

Across the 1,440 repeated paired query outcomes, support for complementary examples matching the authored core facets rises from **96.7% under formal-only to 100%** under each new discovery policy. Their mean nDCG is about **.8832**, compared with **.8798** for formal-only, **.8934** for source-only, and **.9013** for the raw hard-joint control. Keep coverage and relevance separate. Independent source fidelity, formalization generation, and native proof success remain unmeasured.

The [machine report](hybrid-01/report.json) contains all group/style summaries and bindings to 13 detailed artifacts. The [runbook](../../external/ipfs_datasets/docs/autoencoders/alignment_hybrid_retrieval_experiment.md) explains the fixed policies, and [hybrid-validation.json](hybrid-validation.json) records exact commands and evidence identities. The separate [richer-material inventory](richer-material-inventory.md) identifies available regression material and its admission limits.

## Controlled comparison

The study retains 360 training rows, 120 exposed development rows, the same 90 training candidates, frozen raw-384D facet predictions, and all 12 projection generations. No model, probe, or calibration is fitted. Every paired policy selects five examples from a final shortlist of 20.

| Policy | Candidate discovery | Selection relevance |
| --- | --- | --- |
| Source only | Source cosine top 20. | Source cosine. |
| Formal only | Formal cosine top 20. | Formal cosine. |
| Source discovery / formal selection | Source cosine top 20. | Formal cosine. |
| RRF / formal selection | Equal reciprocal-rank fusion of both top-20 prefixes, offset 60, then 20 retained candidates. | Formal cosine. |
| Quota / formal selection | Both heads' first ten ranks, deduplicated, then alternating later ranks to fill 20. | Formal cosine. |

The last three use the same formal hard-joint selector: `.7 × normalized formal cosine + .3 × marginal predicted joint coverage`. Fusion scores determine shortlist membership only. Query authored references and group labels enter only post-ranking diagnostics.

Comparing source discovery/formal selection with formal-only isolates discovery. Comparing it with source-only isolates selector geometry on the same source shortlist. The raw control and all 24 paired single-head controls reproduce all **3,000 prior selected-item and joint-trace checks** exactly, with zero cosine-score difference.

Hybrid discovery has 40 prefix opportunities before deduplication, compared with 20 for a single-head policy. Actual unique unions contain 20–28 candidates, averaging 23.64. Final shortlist and demonstration budgets are matched; upstream opportunity is different. The batch scores both full candidate geometries for shared evidence, so this is not a standalone single-head latency comparison.

## Every fixed arm

Projected cells average all three fixed seeds. Values are support percentage / nDCG; no best checkpoint, seed, width, weight, or policy is chosen.

| Shared dimension / prior action-negative weight | Source only | Formal only | Source discovery / formal selection | RRF / formal selection | Quota / formal selection |
| --- | --- | --- | --- | --- | --- |
| 384D / 1 | 100% / .8933 | 98.9% / .8917 | 100% / .8927 | 100% / .8926 | 100% / .8926 |
| 384D / 2 | 100% / .8940 | 95.8% / .8697 | 100% / .8751 | 100% / .8751 | 100% / .8751 |
| 512D / 1 | 100% / .8929 | 98.1% / .8953 | 100% / .8966 | 100% / .8965 | 100% / .8966 |
| 512D / 2 | 100% / .8935 | 94.2% / .8627 | 100% / .8685 | 100% / .8685 | 100% / .8685 |

Every new policy recovers the same 47 formal-only misses with zero newly lost support outcomes. Source-only already provides complete coverage. The small average relevance increase relative to formal-only remains below stronger source and raw controls; it does not establish an overall advantage for the learned formal representation.

Fusion changes shortlist membership frequently, but rarely changes the selected five relative to source discovery/formal selection: RRF selects identical items and scores in **1,431/1,440** outcomes; quota does so in **1,434/1,440**. Their slightly different relevance means accompany identical support. This panel offers little remaining evidence for choosing among these discovery recipes.

## Where the failures moved

The unpruned source/formal union supplies complete authored complementary support in every pair. Formal-only's own discovery prefix lacks support in 47 outcomes; its hard selector then exhausts the support available within that prefix. The two-head union is a diagnostic counterfactual for this single-head control, which never consults that union for discovery. Both merges and source-only discovery retain the needed support in every final shortlist, and the formal selector chooses it successfully.

Thus this run has no residual union-availability, hybrid-pruning, or hybrid-selection support failures. That is an observed result under correct authored-label predictions, not a general guarantee. Fixed fusion can discard useful unique candidates, and prediction or relevance errors can still defeat selection; counterexample tests preserve those limits.

For the previously weak 384D, weight-2 formal clerk/certify group, three-seed mean support rises from **79.2% to 100%** and nDCG from **.7684 to .7953** under all three new discovery policies. Paired source-only relevance remains higher at **.8295**. Formal officer/inspect already has complete hard-joint support and is unchanged at **100% / .9006** under the new policies.

The 47 misses cover 29 distinct queries across repeated checkpoints: 16 custodian/register, 20 clerk/certify, and 11 executor/issue outcomes. They are not 47 independently sampled sources. Only five development groups are present, and the recipe responds to previously exposed diagnostics; no statistical generalization or independent final-test claim follows.

## Richer data and the next phase

The bounded inventory confirms that the current 480-row Legal panel has no nonempty condition, exception, or temporal field. It identifies richer authored material: 15 Intent contract cases, five UI guard cases sharing one source, 41 synthetic authorization cases, 53 proof-tactician recipes, and provider-conformance recipes spanning 13 logic families. Exact source paths, counts, and 16 observed file bindings are recorded in the inventory.

These are regression opportunities, not independently reviewed natural-source gold. Intent references are partly constructed through the existing parser; UI interpretations add caller-declared state assumptions; several provider fixtures mandate offline fake runners. Sealed panels were excluded through descriptor inspection, without constructing or opening their partition rows. No richer fixture is silently admitted to the pinned Legal experiment.

The next work should prioritize:

1. Preserve raw MMR, raw hard-joint, and source-only controls. Use the fixed source-discovery/formal-selection arm as a diagnostic; this panel does not justify production fusion or further tuning of RRF and quota parameters.
2. Define a separate richer-data contract with explicit source/context bindings, logic-family identity, nonempty qualifiers, scope, and binders. Treat authored fixtures as adapter regressions and obtain genuine source-only review before measuring fidelity. Auxiliary assumptions must be supplied explicitly when they determine the target.
3. Measure downstream generation and checking: faithful statement construction, syntactic acceptance, reference equivalence where appropriate, and useful native proofs remain distinct endpoints. Retrieval support alone supplies none of them.
4. Admit the separate 8D, native 768D, and Leanstral embedding/checkpoint lanes before comparing them numerically. This run uses cached 384D source vectors and frozen experimental projection heads; it does not evaluate those other encoders or retrain existing autoencoders. The [comprehensive plan](../../implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md) retains their independent representation and proof-state work packages.

The existing source-only review handoff remains **40 pending items**, with zero preliminary adjudication candidates. No annotations, reviewer authentication, author-independence evidence, or sign-offs were invented.

## Evidence

All **475 focused tests passed in 18.61 seconds**, exit 0. Ruff passed for the five new Python files. The actual CLI completed in **25.95 seconds**, exit 0. Tests cover full canonical target linkage across heads, excluded training-query membership, disjoint prefixes with matched final budgets, fusion/quota counterexamples, frozen control replay, reference mutation without ranking changes, prohibited refitting, digest corruption, cross-generation pairing, protected-protocol drift, and partial-deadline accounting.

Report payload SHA256: `35310c8a2cbb85daa1e00c0c9051b46a9cc0b44d363b3031bea72c2cb38e156b`.

The compact report is about 674 KB. Its 13 detailed artifacts total about 218.75 MB, retain all **7,320 scored policy-query rows**, and include complete head-prefix, union, final-shortlist, and selection traces. All 25 listed source bindings, 12 checkpoints, and 25 predecessor detail artifacts verify. Listed bindings remain a partial dependency closure.

No encoder or LLM was loaded, no weights were fitted, and no provider, native prover, or sealed final-test input was used by the experiment. Protected AF-002 inputs remain unchanged. Primary fidelity stays `unavailable`, useful native proof coverage stays `unrun`, and qualification and production admission stay false.
