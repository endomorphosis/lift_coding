# Autoformalization representation and stage boundaries

Date: 2026-10-04. This implements the representation declaration boundary from AFI-01/AFI-06 and prepares separate stage contracts for AFI-09a in the [implementation backlog](50-autoformalization-alignment-implementation-backlog-2026-10-04.md). It follows the [statement scope work](52-autoformalization-statement-scope-coverage-2026-10-04.md) and preserves the [comprehensive improvement plan](49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md).

The independent 8D spaCy, 384D GTE-small and 768D Alibaba multilingual GTE paths retain their existing producers and checkpoints. Their vector widths are properties of particular views, not complete representation identities. Leanstral's optional embedding role remains separately unqualified.

## Representation declaration boundary

The new [lane bundle owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_lane_bundle.py) exports `validate_lane_bundle(bundle, *, expected_bindings)`. Import and validation require only the standard library. The function checks data and joins; it executes no encoder, decoder, reconstruction, optimizer, proof or model download.

A closed bundle contains `schema`, `profile`, `producer_receipt`, ordered `rows` and `content_sha256`. The profile binds lane, representation stage, actual output dimension, producer identity, pooling/endpoint, normalization, precision and matching fit/inference input recipes. The producer identity includes a profile ID, model/revision, implementation-manifest digest, asset-manifest digest and a separately named checkpoint digest where needed.

| View | Width | Identity and geometry retained |
| --- | ---: | --- |
| Historical spaCy features | 8 | Linguistic feature hash, six-decimal coordinates, no learned reconstruction claim. |
| Raw GTE-small | 384 | Mean pooling, L2, exact float32 values. |
| Raw Alibaba multilingual GTE | 768 | CLS pooling, L2, exact float32 values and separately bound model/code. |
| Learned384 residual activation | 8 | Checkpoint-bound branch; its original 384D skip connection remains necessary. |
| Learned384 residual projection | 384 | Checkpoint-bound residual output; preserved without L2 renormalization. |
| Learned384 decoder condition | 32 | Separate checkpoint-bound conditioning endpoint, preserved without L2 renormalization. |

Raw, learned latent, learned projection, reconstruction and decoder condition remain separate stage names. Derived available vectors require a checkpoint, tensor endpoint and upstream vector digest. A missing upstream may be retained as an unavailable derived view with a reason. This schema supplies no new trained native8 or native768 projection head. Saved native768 token controls or frozen identity sidecars do not become trained autoencoder reconstructions by renaming them.

Every row retains its ID, exact source/context input, full input digest, serialized encoder text and its digest, outcome, vector and vector digest, upstream binding, token-receipt binding and producer-row digest. Known encoder recipes are exact source only, the existing role-marked source frame, and the role-marked declared-context frame. The function recomputes their literal encoder text. Context can remain declared while the source-only recipe leaves it unforwarded; the receipt reports that distinction and never resolves context.

The normalized producer receipt binds its full profile digest, originating artifact file declaration and ordered row bindings. Caller-selected `expected_bindings` independently pin the complete sealed profile and producer-receipt values, plus every ordered input ID/digest. Local resealing cannot replace those external selections. Source/vector/token substitutions are checked against the producer-row association, including cases where dimensions or source strings happen to match.

All available coordinates must be finite floats of the exact width. Native raw vectors preserve exact float32 scalars; historical features preserve their six-decimal values. A declared L2 profile validates its stated tolerance without changing coordinates. Non-unit derived producers remain unchanged. Unavailable vectors are null with reasons. Zero vectors require an explicit `ablation_zero` outcome and reason; they cannot stand in for successful production.

Ordinary JSON is bounded to 32 MiB, depth 20 and 1.2 million nodes, with at most 128 rows and output width 8,192. Bool coordinates, nonfinite values, unknown fields, extra authority fields and oversized declarations reject. Payload/profile/receipt seals use sorted compact UTF8 JSON with `ensure_ascii=False` and `allow_nan=False`, excluding only their own `content_sha256`. External profile and receipt hashes cover the complete sealed values. Vector digests retain JSON scalar serialization, including the distinction between negative and positive zero.

This dictionary boundary does not inspect the declared artifact file, rerun tokenization or authenticate the producer. A normalized historical association is not runtime attestation. The [saved assay](../../artifacts/autoformalization-alignment-20261003/representation-boundary-01/assay.json) supplies separate local file checks for its selected inputs.

## Separate stage declarations

The new [stage owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_stage_declarations.py) exports `validate_fit_declaration`, `validate_rank_declaration` and `validate_score_declaration`, each with mandatory `expected_bindings`. They validate separate closed payloads and externally selected role values. These are declaration validators; the proposed numerical `fit_alignment`, `rank_alignment` and `score_alignment` workers remain later work.

Fit binds a complete TRAIN representation ledger, formal-view identities, a fixed relation policy and a proposed resource/update budget. Every training mask remains at integer zero, and the receipt reports that semantic fitting lacks contrastive admission. Budgeted updates are requested work; executed updates remain zero. A DEV row or foreign source/profile cannot enter the TRAIN declaration merely by changing its local checksum.

Rank binds a query representation ledger, a frozen TRAIN bank, ranking policy and the applicable checkpoint. Query rows admit identity, input/representation bindings and availability. Reference targets, reference hashes, organizer groups and authored row kinds are absent from the closed query schema. TRAIN bank records may retain their formal-view identities as potential demonstrations. Missing query vectors remain in the ledger. Raw ranking and projected ranking have distinct checkpoint requirements.

Score consumes separately bound saved ranking values, the exact frozen bank and a reference ledger joined to each query's input identity. Missing references or admission evidence remain explicit. Fidelity-evaluation masks stay zero and no score is computed. Dictionary validation does not establish that a ranking was previously made durable, that reference files were inaccessible during fitting/ranking, or that reference admission has been authenticated. Separate file workflows and isolated workers must establish those properties.

Saved rankings retain their complete rank declaration. Their query-manifest, bank, policy and checkpoint hashes must join that same generation. Saved rows must match its ordered query IDs and input hashes; unavailable or zero-ablation queries cannot claim available ranked hits. Source-to-formal ranking still has only opaque formal-view/feature-space declarations here. An executable worker needs a separately checked formal-vector bank and feature-codec join.

Stage role pins cover complete sealed values and ordered row digests. Neither equal dimensions nor a self-consistent caller declaration substitutes for an externally selected generation. The validators keep fitting, ranking and scoring structurally separate without claiming that a legacy combined experiment driver now has isolated file access.

## Retained numerical owners

The existing [projection owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_projection.py) retains its exact native384 profile, feature codec, dual heads, old loss and checkpoint format. Its current loss treats unequal target IDs as negatives and requires negative weights at least one. It cannot exclude an unknown relation; the new masked loss in the backlog remains necessary. Author/document groups supply splitting controls, not semantic equivalence.

The mathematical `rank_vectors` helper in the [experiment owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_experiment.py) accepts vectors and IDs without targets. Its legacy experiment driver loads reference-bearing development records before fitting and computes scores before ranking persistence. It remains a historical driver rather than an isolated new worker. The [checkpoint retrieval owner](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_representation_retrieval.py) also accepts the full development panel at its public boundary even though its ranking calculations ignore targets.

The new declaration contracts provide input schemas for later workers around appropriate numerical helpers. They do not execute the proposed 12-arm contrastive experiment, alter the original TRAIN16 masks, select a production encoder or modify a retained decoder checkout.

## Verification and remaining work

The [persistent assay](../../artifacts/autoformalization-alignment-20261003/assay_lane_identity.py) reads pinned historical artifacts and transcribes separately identified views. Exact context envelopes are recovered from the existing target-free context transport manifest, with older authored input hashes retained in a separate join ledger. New source/context envelope hashes are not presented as the older panel hash recipe.

The saved run preserved 204 vectors exactly across six views of 34 requests: 102 raw vectors and 102 learned384 endpoint vectors. Every view retained all 34 available rows and five zero masks. Learned endpoint norms remained non-unit; no normalization was introduced. The fresh static worker completed in approximately 0.63 seconds with a 36,028 KiB peak RSS and an import guard blocking optional model stacks. It hashed checkpoint bytes without deserializing their weight contents or replaying projection layers.

Historical representation files include training-derived codec and selection metadata. Loading that metadata is recorded separately from query-reference access. No human review or query-reference panel enters this assay, and stored target prefixes supply no computation input. The new consumer bundles contain only the source/context envelopes, representation profiles, producer associations and vectors.

Raw native384 backend input IDs differ legitimately from outer request IDs; the saved production input/results association supplies the join. Native768 retains token digests but omits token arrays, and historical8 has no token digest. Those differences remain observable. Neither a missing token array nor its hash becomes an independent retokenization result.

The [validation receipt](../../artifacts/autoformalization-alignment-20261003/representation-boundary-01/validation.json) records the actual assay and targeted tests, implementation pins and prior scope-generation checks. Tests use authored engineering fixtures and exercise externally pinned substitutions, stage relabeling, context/serialization drift, precision and normalization, unavailable ledgers, zero ablations, role leakage and false authority. No test fixture is semantic gold.

The targeted suite passed 439 checks: 158 new lane checks, 72 new stage checks, and 209 existing raw/context/checkpoint representation checks. Ruff passed the six new implementation, test and assay/validation files. The prior scope receipt's 89 file bindings are rechecked. Its separately documented legacy registry mismatch remains recorded; that test was not rerun in this stage. The dependency manifest is partial and the older 554-file chain is not repeated.

All new receipts retain pending verification/admission, five zero masks and false source-fidelity, proof and runtime-attestation flags. Leanstral final-hidden declarations can describe an externally selected diagnostic vector; validating one never qualifies its runtime or resolves the previously observed batch inconsistency. Model, encoder, optimizer and prover execution remain zero in this stage.

The next implementation work is a pinned file workflow and isolated stage workers, followed by the separately versioned mask-aware contrastive loss. Actual semantic fitting requires admitted TRAIN relations and appropriate native8/native768 checkpoint profiles. Scoring requires independently admitted references, and broader formal-view adapters remain necessary for the 40-family pilot.
