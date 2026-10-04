# Canonical symbol and source anchor transport

Date: 2026-10-04. Status: implemented output codec and prepared weak supervision. No new neural decoder has been trained, and independent fidelity and proof authority remain unestablished.

The new [byte codec](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_byte_codec.py) can transport the canonical symbols, exact source anchors and multiple qualifiers that the retained decoder outputs cannot represent on the current panel. It round-trips all 22 existing source-constructed proposals without changing their contents. This removes a representation obstacle; it does not generate proposals from source or establish their meaning.

## Exact output contract

The alphabet has 259 fixed IDs: padding, BOS, EOS and the 256 UTF8 byte values. No corpus-fitted target vocabulary is required. Compact canonical JSON carries a versioned schema, exact source SHA256, the complete seven-facet rule and ordered anchor triples containing field path, start and end. Decoding uses the supplied exact source to reconstruct every full anchor's literal text, facet and canonical symbol. Operators are fixed by the profile: conditions and temporal lists use `all`, exceptions use `any`. Authority flags remain false.

`validate_proposal`, `encode_proposal`, `decode_proposal` and `inspect_encoding` enforce closed schemas, complete leaf coverage, nonoverlapping half-open character spans, sorted unique qualifier lists and exact source joins. They reject malformed framing, padding within outputs, invalid UTF8, duplicate JSON keys, nonfinite JSON, excessive nesting, noncanonical serialization and capacity overflow. The default cap is 4,096 framed byte tokens; payloads have a separate 32,768-byte hard limit. Nothing is truncated or repaired. The profile permits one flat rule, at most 64 atoms per qualifier facet and atoms of at most 512 characters; these bounds define transport scope, not measured semantic support.

The codec consults no grammar, model, vocabulary or prover. Encoding consumes a supplied proposal and is serialization, not source-to-formal inference. A structurally consistent wrong alias or modality can pass occurrence checks: an anchor shows where the proposed evidence appears, not whether the interpretation is correct. Richer binders, context interpretation, nested operators and multiple rules require separately versioned contracts.

## Prepared data and baselines

The [preparation plan](canonical-codec-01/plan.json) and [report](canonical-codec-01/report.json) retain all 34 requests and their previous outcomes. [Target-free inputs](canonical-codec-01/target_free_inputs.json) contain exact source/context and 102 existing vectors across the independent 8D, 384D and 768D lanes. They contain no canonical IR or target token IDs. These are raw linguistic features or raw embedding-model vectors, rather than learned autoencoder representations.

[Training supervision](canonical-codec-01/train_weak_supervision.json) contains only the 16 TRAIN proposals across four source groups. Their labels come from the development grammar and frozen TRAIN-supervised atom catalog. The weak decoder-fit mask is enabled for these records; strong semantic, contrastive, proof and fidelity-evaluation masks are zero throughout. Each training group has equal aggregate loss weight, and next-token masks cover content bytes and EOS while excluding BOS. No fitting or optimizer update ran.

The six [development transport records](canonical-codec-01/development_transport_diagnostics.json) have all fit/evaluation masks zero. Two unavailable positive mappings remain in the eight-positive development denominator. Ten unsupported, ambiguous or contextual inputs have no candidate sequences; no synthetic gold abstention labels were invented. All 34 independent human reviews remain pending. The 4,096-token cap is a predeclared policy, not a fitted threshold; TRAIN capacity records are frozen before this run's DEV capacity diagnostics. The cohort remains exposed development material.

| Partition | Exact proposal round trips | Framed byte tokens per proposal | Exact anchors |
| --- | ---: | ---: | ---: |
| TRAIN | 16 / 16 | 534–701 | 124 |
| Constructed DEV proposals | 6 / 6 | 532–693 | 48 |

All 22 proposals fit the new cap, and none fits a numeric 512-token ceiling in byte units. The compact wire needs 530–699 bytes plus BOS/EOS. Canonical IR alone uses 177–244 bytes; those shorter records omit exact anchors. Previous whole-string token counts and new byte counts have different units, so this does not reinterpret an old checkpoint's capacity. Byte transport may cost substantially more generation steps than a typed-atom vocabulary; compare actual runtime and fidelity before choosing a trained arm.

The [static baseline comparison](canonical-codec-01/existing_codec_static_baselines.json) distinguishes a real retained decoder vocabulary from a codec newly fitted on the 16 weak TRAIN proposals. The existing typed-atom codec already supports up to four qualifiers and canonical aliases, but does not emit exact anchors. Its older retained source-conditioned checkpoint uses 27 source tokens and 28 target tokens and cannot encode any of the 22 current sources or canonical proposals. The TRAIN-refitted codec represents all 22 sources and canonical targets statically: sources use 21–37 tokens and canonical targets 19–22. It remains a separate preparation asset with no neural checkpoint. Neither static capacity nor a round trip is decoder accuracy.

The deterministic run took 0.834 seconds with peak RSS 46,528 KiB and preserved all 311 preceding checked bindings plus the previous wrapper/test pins. An import guard observed no model-stack attempts; no neural training, model, new encoder or proof ran. CPU/wall limits and cooperative memory checks are recorded, while loaded repository files are not a complete environment manifest.

## Verification and next experiment

The [92 codec tests](../../external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_byte_codec.py), previous wrapper/preflight/grounding tests and existing qualifier/source-guard tests passed **474 tests in 4.03 seconds**. Ruff passed the codec, tests and preparation runner. Independent checks covered 1,295 token-ID, Unicode and malformed-JSON cases and all 22 exact proposal round trips. The [stage validation](canonical-codec-validation-01/validation.json) checks saved masks, split separation, vector joins, static baselines, capacities, prior bindings and documentation.

Next, compare a separately identified byte generator with a TRAIN-fitted typed-atom generator and a separate source-anchor prediction head. The latter may reduce sequence cost while retaining exact spans; it still needs new compatible weights and cannot represent unseen typed symbols without a declared extension. Both source/context interfaces must consume the target-free file; target tokens enter only the training loss. Include real, zero, disabled and full-order rotated embeddings and raw-source controls. Bound every free-running generation, record invalid/incomplete output and context clarification, and preserve all-request coverage accounting. Use weak labels only for a development canary; independently reviewed natural sources are required before any fidelity or production claim. Source/formal contrastive alignment, proof retrieval and Leanstral generation/embedding experiments retain their separate gates.
