# Opt-in source preflight around retained decoder inference

Date: 2026-10-04. Status: implemented and replayed on exposed development inputs. Independent source fidelity, runtime qualification and proof authority remain unestablished.

The new [decoder wrapper](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_span_decoder.py) makes the previous [source warnings](source-grounding-report.md) operational: inputs with warnings do not reach the retained source-span decoder. Its bounded replay preserves every surviving numerical output under the original controls. This establishes filtering and reproducibility; the remaining inputs still abstain, so it supplies no demonstrated formalization-quality gain.

## Interface and execution contract

`decode_with_preflight(decoder, requests, latents, latent_ablation=...)` takes an already constructed native dimensional source-span decoder, exact source text, declared context and already produced vectors. Each request has exactly `id`, `source_text`, `context_text` and `requires_context_resolution`. It accepts no reference, row-kind or vocabulary channel and does not invoke the grammar grounding compiler. The wrapper binds the retained decoder's checkpoint, input dimension and declared model-state identity.

The wrapper validates every vector, including vectors belonging to blocked requests, before transforming the complete original batch. Rotation assigns each request the next original row's vector before filtering; a blocked row can therefore remain a rotation donor. Zero vectors retain the owner's enabled conditioning branch, while the disabled control gates that branch off. The owner receives transformed vectors with control `none`, or the separate `disabled` control. Native source-only, 8D, 384D and 768D contracts have boundary tests; this numerical assay uses native768 only.

Source preflight then records unsupported-profile or clarification outcomes. Warning-free source remains `unassessed`; it does not become semantically supported. Declared context is retained but unresolved, and context-bearing inputs are withheld. The retained tokenizer separately checks source encoding limits without truncation. The wrapper submits eligible sources once and returns all requests in their original order, including explicit blocked, encoding-unavailable, decoder-abstained, decoder-unavailable and unaccepted proposal outcomes.

Returned native receipts must agree with exact sources, effective vectors, checkpoint metadata, controls and authority flags. Decoded proposals additionally require consistent copied spans, modality diagnostics, decision margins, canonical IR, display and formal payload. Malformed receipts raise a contract error. Operational import, OS or runtime failures produce explicit unavailable outcomes, exposing only the base exception category.

`validate_preflight_decoding(record, requests, latents)` recomputes deterministic preparation and checks saved native receipt structure without numerical inference. It cannot independently authenticate an internally consistent invented model output. The assay's actual inference, complete-row comparisons to separately hashed prior outputs and before/after tensor checks supply the observed numerical evidence. Neither interface accepts an artifact or establishes source fidelity or a proof.

This is an explicit import. Existing checkpoint-bound owners, package exports, catalogs and default runtime entry points remain unchanged. Supplying an already constructed decoder also means blocking a request does not unload that model.

## Executed matched replay

The [replay plan](preflight-decoder-01/plan.json), [input joins](preflight-decoder-01/request_joins.json) and [report](preflight-decoder-01/report.json) bind all 34 exact source-only native768 vectors, their original input identities and the existing declared contexts. The runner reads the source/context manifest without passing its TRAIN vocabulary to the wrapper. It reads no authored reference semantics. Nine states comprise three reconstructed initialization controls and the retained selected400/last800 checkpoints for three seeds; no new state is trained.

| Measurement | Observed result |
| --- | ---: |
| Original requests in every wrapper response | 34 |
| Sources forwarded per invocation | 24 |
| Unsupported-profile inputs withheld | 6 |
| Clarification inputs withheld | 4 |
| Decoder proposals among forwarded inputs | 0 |
| Forwarded abstentions per invocation | 24, all `copied_spans_overlap` |
| Primary invocations: nine states × four controls | 36 |
| Complete primary rows equal to prior raw outputs | 864 / 864 |
| Exact private reload comparisons with disjoint storage | 9 / 9 |
| Total numerical row forwards, including reloads | 1,080 |
| Prior matched raw replay row forwards | 1,530 |

All surviving complete decoder rows, including logits and source/vector digests, are bitwise equal in canonical JSON to the same original positions in the [raw replay](decoder-replay-report.md). Full-order rotation is preserved; zero and disabled remain separate controls. One private restoration per state, nine total, uses distinct parameter storage and reproduces its real-vector wrapper response exactly. Actual model tensor digests, checkpoint payloads and global Torch RNG are unchanged. All 258 preceding checked file bindings remain unchanged.

The primary request denominator is 1,224 occurrences: 864 forwarded and 360 withheld. Nine repeat calls add 306 request occurrences: 216 forwarded and 90 withheld. The wrapper therefore avoids 450 numerical row forwards in this matched replay. This is a measured invocation-count reduction on this authored panel, not a production latency result or an independent false-acceptance rate. Previous raw decoded outputs occur only on sources now withheld; all surviving sources still abstain. The original outputs remain preserved.

The worker ran CPU float32 with one Torch thread and inference mode, a 120/130-second CPU limit, an external 180-second timeout and cooperative 2 GiB RSS checks. Measured wall time was 30.732 seconds, CPU time 49.533 seconds and peak RSS 715,948 KiB. There were zero optimizer steps, new encoder calls or proof calls. Observed loaded repository files are bound; this is not a complete transitive environment manifest.

## Verification and next work

The [107 wrapper boundary tests](../../external/ipfs_datasets/tests/unit/logic/legal_ir/test_canonical_span_decoder.py), previous preflight/grounding tests, qualifier tests and source-guard tests passed **382 tests in 4.00 seconds**. Ruff passed the wrapper, its tests and the replay runner. Tests cover blocked batches with zero decoder calls, full-order rotation, malformed vectors and receipts, operational failures, detached validation and use without Torch imports. A direct enormous-integer vector probe also rejects before a decoder call. The [stage validation](preflight-decoder-validation-01/validation.json) binds these files and the updated plan, rechecks saved deterministic receipts and raw parity, and records independent read-only audit scope.

All 34 independent human source reviews remain pending. Next, admit independent natural-source/context labels and evaluate warning coverage, missed warnings and unnecessary blocking separately from generation fidelity. Build a separately versioned decoder that can represent canonical symbols, exact anchors, multiple qualifiers and eventually typed scope; retain the old copy decoder as a baseline. Measure useful source-faithful output coverage on all registered requests before advancing source/formal contrastive alignment, proof retrieval and bounded Leanstral repair. Leanstral embedding pooling still requires its own resource-admitted numerical canary.
