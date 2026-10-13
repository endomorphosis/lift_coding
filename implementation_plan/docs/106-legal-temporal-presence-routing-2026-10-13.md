# LegalIR temporal-presence comparison, 2026-10-13

The fixed parent-temporal-presence route restores the two legacy errors while reducing newer authored correctness. It remains an opt-in saved-score diagnostic. No checkpoint or default decoder is promoted.

| Readout | Legacy joint | Authored development joint | Authored evaluation joint |
| --- | --- | --- | --- |
| Trained split features | 94/96 | 45/72 | 32/72 |
| Parent temporal presence with trained boundaries | 96/96 | 35/72 | 30/72 |
| All parent optional presence with trained boundaries | 96/96 | 19/72 | 27/72 |

The original learned temporal boundaries still find the correct date spans in the two legacy errors; their presence decisions mark those spans absent. Unconditional parent routing also restores false positives on duration-bearing conditions, exceptions, and names. Development temporal false positives rise from 3 to 17; evaluation false positives rise from 0 to 8. Both routed variants retain all trained boundary and modality score bytes, but the additional constraints can change joint assignments or abstentions.

The source contribution adds `ipfs_datasets_py.logic.legal_ir.presence_routing.compose_presence_scores`, an explicit pure score-composition helper with exact source/ID/token validation and detached provenance. It neither runs a model nor repairs the original raw owner report. Callers can explicitly feed its returned score packet to the unchanged joint selector. It is useful for reproducible ablations, not for automatic replacement of the trained decoder.

The evidence in [the artifact directory](../../artifacts/legal-temporal-presence-20261013-01/) includes the fixed plan, analyzer, complete panel summaries and matched error IDs, independent result replay, and the next temporal-head training proposal. The full local diagnostic is retained by SHA256 `284040c26ed56e3dbff94e88108d9635d49344a48be794cf7b53e1684f7d9226`; its 5.16 MB body is omitted from Git to avoid another large copy. Existing checkpoints and raw score captures remain in the [immutable Hugging Face release](https://huggingface.co/Publicus/legal-ir-autoencoder/tree/70525bcf70e801e78f4882b4834494d67ec0d2b6/releases/20261013-split-feature-v1).

The next training comparison isolates temporal classification: freeze the completed split-feature model, clone its full eight-output presence head, and train only the temporal rows using authenticated training targets. Compare temporal cross-entropy against the same cross-entropy plus a balanced signed-margin objective. Preserve actual learned boundaries, modality, and non-temporal presence throughout. This training is proposed, not executed here.

The analyzer replays all 392 source occurrences for each of four fixed variants, including greedy and joint outcomes, abstentions, and permission preservation. All 32 legacy permissions remain P. Its 384 authored targets are previously exposed and share templates; eight law rows remain unreviewed and unscored. No independent statutory fidelity, genuine latent-dimension conditioning, broader logic-family, or Lake build result is claimed. There is no new trained checkpoint to upload.
