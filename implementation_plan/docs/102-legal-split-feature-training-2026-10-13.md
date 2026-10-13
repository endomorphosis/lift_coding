# LegalIR split-feature training, 2026-10-13

The completed split-feature experiment raises joint exact authored evaluation outputs to **32/72**, compared with 22/72 for the preceding full-parameter arm and 27/72 for the saved-score hybrid. Legacy full-rule retention falls to **94/96**. This checkpoint fails the declared 96/96 retention gate and remains an opt-in experimental artifact.

The model freezes the parent's original feature path and modality head, then trains an independent copied feature path with the span presence/start/end heads. Its 34 tensors partition into 17 trainable and 17 frozen tensors. Both feature copies initially match the parent; all four saved heads, tokens, greedy outputs, and joint outputs match on 392 source occurrences before training. All 392 final modality vectors remain bit-identical to the parent. Two feature paths per source forward mean equal compute with the earlier arms is not claimed.

One bounded run completed 32 fresh Adam updates on the same 168 training rows: seed/order 1729, batch 12, learning rate 0.001, presence weight 1, modality weight 2, actor hinge disabled. The configured dimension is 384 but latent conditioning is disabled, with zero external latent/context encoder calls. This result does not qualify genuine 8D, 384D, or 768D conditioning.

| Exposed authored panel | Parent joint | Full parameters joint | Span heads only joint | Saved-score hybrid joint | Split features joint |
|---|---:|---:|---:|---:|---:|
| Legacy tuning, 96 rows | 96 | 93 | 96 | 96 | 94 |
| Development, 72 rows | 0 | 42 | 4 | 39 | 45 |
| Evaluation, 72 rows | 6 | 22 | 6 | 27 | 32 |

Both legacy regressions are temporal-presence false negatives: `native-tuning-calendula-t6-q7-o` and `native-tuning-calendula-t6-q7-p`. All other legacy roles remain 96/96. All 32 legacy permission rows retain P with no P-to-O, P-to-F, or abstentions. Freezing also preserves the parent's errors among 24 newer authored permissions: 14 P, 4 O, 6 F. Evaluation object spans match 45/72 under joint decoding and 38/72 under greedy decoding; the difficult actor-duration-name class remains joint exact 2/12 on evaluation and 0/12 on development.

The independent saved-output recount reproduces all 42 state/panel summaries, 24 matched recovery/regression ID comparisons, initial complete-head parity, and final modality parity. It uses no production/analyzer scorer and performs no model forward or checkpoint JSON parse. All 53 new output files were frozen before new target scoring. The pure suite passed 194 tests and 383 subtests. Tensor/gradient/optimizer facts remain source-bound trainer metadata rather than independent numerical replay.

The model run completed in 35.292 seconds with sampled RSS 752,267,264 bytes and terminal storage 33,605,972 bytes. Its own 200 MB reservation was released; all original 528 ledger records remain unchanged. Shared CPU, RSS, storage, and wall limits were not increased.

The release-relative weight path is `cells/split-features/results/cell-checkpoint.json`, 3,592,389 bytes, SHA256 `95bd50a7cc6e25381ad126e3d955f0816c31470ec469fb22ceca297e35115035`. Loading belongs inside the qualified numerical runtime and uses the new split-feature loader, not the parent loader. The inference API still requires a validated 384-value placeholder vector for each source; disabled latent mode does not establish latent semantics.

All 384 authored targets were previously exposed and share templates. Eight law-source rows remain unreviewed and unscored. There is no independent statutory accuracy, multi-seed significance, broader logic-family qualification, or actual `lake build legal` in this experiment.

Next work should first test temporal-presence retention using saved scores, then predeclare any replay/distillation training comparison. Further work needs reviewed provision-group statutory holdouts, actor/object binding examples, real encoder/dimension controls, and separately executed typed-family and Lake checks. The detailed gap plan distinguishes each proposed experiment from completed evidence.

The [immutable experimental release](https://huggingface.co/Publicus/legal-ir-autoencoder/tree/70525bcf70e801e78f4882b4834494d67ec0d2b6/releases/20261013-split-feature-v1) contains 100 files totaling 43,262,631 bytes. Four bounded commits preserved all 4,244 preexisting file identities and root attributes. Every new payload file was downloaded at that immutable revision and matched its approved SHA256. The checkpoint is [available directly](https://huggingface.co/Publicus/legal-ir-autoencoder/blob/70525bcf70e801e78f4882b4834494d67ec0d2b6/releases/20261013-split-feature-v1/cells/split-features/results/cell-checkpoint.json). Previous releases remain available.

Source [PR #1293](https://github.com/endomorphosis/ipfs_datasets_py/pull/1293) merged contribution `64e93527bed84ecadaab70a570d82a177a859967` as `cc94dafaf39123bb24b8eb2a043168d9255ff92d`. It contributes the opt-in decoder, tests, [clarified use documentation](https://github.com/endomorphosis/ipfs_datasets_py/blob/cc94dafaf39123bb24b8eb2a043168d9255ff92d/docs/autoencoders/legal_split_feature_training_20261013_v02.md), and finite public evidence: 51 new blobs, 5,225,701 bytes. Immutable commit review preserved every unrelated parent-tree entry and all ten source gitlinks. The root contribution advances only `external/ipfs_datasets` to this actual merge and adds this guide and bounded evidence; it starts from root main `3bc997233cb26eeda2d018fca40b747470f61dfb`, retaining the newer source-view measurement work and accelerator pointer. Canonical checkouts and indexes remain untouched. Hosted CI status is separate from the local pure, training, and publication checks.
