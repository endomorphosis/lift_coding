# Retained native768 decoder replay

Date: 2026-10-03. Scope: bounded CPU execution on the 34 already exposed authored development inputs. This stage establishes reproducible numerical execution and exposes output-contract limits. Independent source fidelity, deployment qualification and proof authority remain unestablished.

The retained decoders load and run, so another decoder fit is not the immediate priority. The source-span branch cannot express the current positive reference contract, while the formula-sidecar branch cannot express several required symbols. Both need explicit capability admission and a compatible output representation before meaningful fidelity comparisons or training decisions.

## Inputs and execution boundaries

Both workers reused the exact source-only [native768 receipts](richer-embedding-01/native768_embeddings.json) and [input manifest](richer-embedding-01/embedding_inputs.json): 34 identities, 33 distinct texts, pinned multilingual GTE vectors of width 768. The two same-wording contextual inputs retain separate identities but identical texts and vectors; their assumptions were withheld. No new encoder calls or training ran. Neither worker read the original decoder validation corpus or sealed final test.

The [source-span runner](replay_source_span.py) uses the current five checkpoint-bound implementation files and the unchanged public checkpoint loader. The [sidecar runner](replay_formula_sidecar.py) uses fourteen helpers whose bytes match the frozen experiment export and the isolated checkout at commit `64bc5734dc82db72e955f2e809b770127e9b6cfc`, plus separately bound archived donor dependencies. The isolated checkout remains clean. Its complete source-span implementation is still absent; this replay does not make it a complete integration checkout.

Both workers used Torch `2.13.0+cu130`, CPU float32, one thread, inference mode and bounded processes. Source-span elapsed time was 19.50 seconds with peak RSS 672.1 MiB; sidecar elapsed time was 1.93 seconds with peak RSS 574.4 MiB. Each stayed below its 2 GiB measured-memory budget. Memory checks occur at run/batch boundaries; Linux `RLIMIT_RSS` is not a strict allocation ceiling. These are local worker measurements, not service latency or complete dependency manifests.

## Source-span results

The [observed report](span-replay-01/report.json) binds six retained checkpoints: selected400 and last800 for seeds 1729, 1730 and 1731. Three additional initial controls reconstruct each checkpoint's declared initializer exactly; they are new zero-update controls, not retained trained checkpoints. Public restoration checks embedded source-parent identity, configuration, 23 model tensors, 33,271 parameters, and saved Adam moments. No optimizer update or resume ran.

Every state decoded all 34 source inputs with real, zero, disabled and one-position rotated vectors. Nine fresh private models reproduced the real-vector outputs exactly with disjoint parameter storage. There were 45 public inference calls and 1,530 row forwards, including the reload comparisons. Model weights and Torch RNG state remained unchanged.

| Seed | Reconstructed initial: decoded/34 | Selected400: decoded/34 | Last800: decoded/34 |
| --- | ---: | ---: | ---: |
| 1729 | 4 | 3 | 3 |
| 1730 | 0 | 0 | 0 |
| 1731 | 0 | 0 | 0 |

These counts are identical across the four controls. Every abstention reported overlapping copied spans. Real, zero, disabled and rotated conditioning changed no generated IR, status or reason in any state. In the trained states, conditioning changed modality logits: maximum real-versus-disabled differences range from 1.018 to 2.078, while real-versus-rotated differences range from 0.00687 to 0.05578. The reconstructed initial branch has no such differences. Numerical conditioning is active after training, but this panel supplies no observed generation benefit from matching the vector to the source.

The identical-source contextual pair yields exactly equal real-vector prediction receipts in all nine states. This is the expected consequence of withholding the distinct assumptions; it provides no context-interpretation result.

References were read only after all forward calls. The [posthoc scope receipt](span-replay-01/posthoc_reference_scope.json) applies the owner's unchanged literal-span contract to the 24 positive references. None is compatible: fourteen fail exact token-aligned condition copying, six require multiple spans per qualifier facet, and four have ambiguous repeated object spans. The other ten rows comprise eight unsupported/ambiguous diagnostics and two contextual inputs with unapplied assumptions. Literal exact accuracy is therefore unavailable with a denominator of zero, rather than a measured semantic accuracy of zero.

All three selected400/last800 outputs for seed1729 occur on authored negative diagnostics. They include a relative-calendar obligation rendered as prohibition, an exactly-one quantifier copied into malformed semantic roles, and negated obligation rendered as prohibition. They pass the decoder's narrow syntax gate and illustrate why proposals need a separate source-capability and semantic gate. They were not accepted or qualified artifacts, so this is not a production false-acceptance estimate. All 34 authored references still await independent review.

## Formula-sidecar results

The [sidecar report](sidecar-replay-01/report.json) restores the initial, selected epoch-0 and trained last-attempt states of `768-generated-fields-every2-2718`. Each has 32 saved state tensors and 189,736 parameters. Binary tensor digests match the saved receipts; the three models use disjoint storage. Original training normalization, clause normalization, count prior, codec and architecture remain unchanged. The source-only cache deduplicates exact text only after checking identical vectors and preserves all 34 query identities.

There are 102 saved BOS-only forward observations across three states from fifteen batches. A separate eight-row A/B/A probe brings the forward call count to sixteen. Another fifteen batches produce 102 complete free-running generations. Initial and selected forward outputs are bitwise equal, consistent with their identical epoch-0 weights. All generations reach EOS under the original configured output cap of 512.

| State | Complete generations | JSON parse-valid | Distinct output texts | Maximum content tokens |
| --- | ---: | ---: | ---: | ---: |
| Initial | 34 | 0 | 1 | 19 |
| Selected epoch 0 | 34 | 0 | 1 | 19 |
| Trained last attempt | 34 | 34 | 16 | 38 |

The last attempt remains unselected. JSON parsing was the only generation syntax check in this assay; no native family checker or proof ran. Every last-attempt output contains one rule and empty condition, exception and temporal lists. Its 32-token fixed codec cannot emit `clerk`, `custodian` or `case_file`. Saved normalization and frozen identity projection are not learned 768D vector reconstruction. The earlier 42/48 development result and its extra-rule rejection remain historical observations; their corpus and predictions were not replayed here.

## Consequences for the improvement plan

1. Add decoder capability admission before generation and acceptance. Unsupported operators, unresolved context and unrepresentable fields need explicit abstention/clarification outcomes. Keep all prespecified requests in service coverage; do not remove unsupported inputs to inflate accuracy.
2. Define a source-grounded typed representation that preserves literal anchors separately from canonical symbols. Compare a separately versioned canonicalization layer or open vocabulary decoder with the untouched literal-copy and fixed-codec controls. Do not change references or invent aliases inside evaluation.
3. Support multiple qualifier atoms, their operators and scope, repeated mentions, and whole-rule association explicitly. A longer training run cannot repair an output representation that excludes required distinctions.
4. Retain real/disabled/zero/swapped conditioning controls. Measure independent semantic outcomes and useful generation changes; logit sensitivity alone does not select a conditioning architecture.
5. Proceed with independently adjudicated richer source/context labels and a disjoint natural-source corpus, then compare raw retrieval, admitted learned states and source/formal contrastive alignment. Preserve the recorded sidecar rejection policy and source-span selection identities.

The replay workers and numerical outputs are immutable stage evidence. The [numerical validation](decoder-replay-01/validation.json) checks 245 file bindings, row joins, control arithmetic, reload equality, generation counts and predecessor preservation without running another model. The [final documentation receipt](decoder-replay-02/validation.json) binds the corrected documentation and preserves that numerical stage. Independent read-only audits checked both decoder branches; they did not supply semantic source review. New unit tests were unnecessary for these artifact-only assays. The sidecar runner has three reported Ruff style findings; lint success is not claimed, and its executed bytes are preserved.
