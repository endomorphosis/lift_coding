# LegalIR actor boundary training, 2026-10-13

The 32-update actor-only pilot leaves complete authored training IR at **153/168** and actor exactness at **155/168**. One exposed authored evaluation panel improves complete joint IR **32/72 to 33/72**. Fresh development and test complete IR remain **0/36** each. The default decoder is unchanged.

The implementation trains 130 active actor start/end scalars while preserving 34 original tensors and 650 inactive copied scalars. Initial complete-head and final protected-head binary32 parity each pass on 632 sources. Independent recount agrees with 837 result comparisons. All 62 model outputs were frozen before scoring.

## Architecture findings

The N7 temporal and N8 actor architectures have exactly matching initial sources, score vectors and decoded outputs on all 632 cases. N7's trained temporal-presence branch improves legacy full IR 94 to 95 but reduces older authored joint IR 51 to 49. N8's actor branch retains 94 and 51 while improving actor exactness on some exposed panels. Combining disjoint components is a future hypothesis; decoded behavior can interact through span constraints and abstention, and the two trained components represent 64 updates in total. No fusion has run.

Training actor gold top8 coverage was already 168/168. Five ranks improve without changing exact selections. Full gold assignments remain available for 160/168 training rows and 0/36 on each fresh panel. The next recommended comparison reuses the existing actor hinge loss at coefficient 0.25, margin 1 and its original negative domain, under an explicit actor-only ranking objective. This differs from the first sealed proposal's coefficient 1 and wider domain; the later reuse audit records that distinction. No additional training has run.

## Integration and archive

The datasets pointer advances to source merge `c9d0f016a9fcfa327346e056e38e2ffa3b25ffa0`. The source contribution is additive and preserves the 34 retained source-owner blobs. The separate accelerate pointer is unchanged. The branch/worktree audit preserves 32 selected commits, five recovery histories and 15 historical absences; canonical working-tree HEAD and index anchors remain unchanged.

[Immutable weights and full evidence](https://huggingface.co/Publicus/legal-ir-autoencoder/tree/fa37360840c070f9318d6ad2baef87d785eac504/releases/20261013-actor-boundary-v1): 135 additions, 69,977,808 bytes. All 4,631 previous file identities and all 135 downloaded hashes were independently verified. Git carries compact evidence; model weights and raw captures remain in the Hub archive.

[Public summary](evidence/legal-actor-boundary-20261013-01/public-result-summary-v01.json), [independent result review](evidence/legal-actor-boundary-20261013-01/result-independent-review-v01.json), [actual publication review](evidence/legal-actor-boundary-20261013-01/hf-publication-actual-independent-review-v01.json), [architecture comparison](evidence/legal-actor-boundary-20261013-01/architecture-comparison-followup-v01.json), [ranking reuse audit](evidence/legal-actor-boundary-20261013-01/next-ranking-reuse-audit-v01.json), [history preservation](evidence/legal-actor-boundary-20261013-01/history-preintegration-independent-review-v01.json) and [full-evidence pins](evidence/legal-actor-boundary-20261013-01/full-evidence-pins-v01.json) identify the retained records.

All scored references are exposed authored engineering examples. Eight statutory examples remain unscored. This pilot establishes no new legal semantic accuracy, broader logic-family qualification, `lake build legal` result or genuine 8D/384D/768D latent semantics.

Source hosted CI was blocked before execution by the account billing lock (four CodeQL jobs; 15 other checks queued). [Exact-head CI evidence](evidence/legal-actor-boundary-20261013-01/source-hosted-ci-v01.json) records that limitation separately from the passing local validations.
