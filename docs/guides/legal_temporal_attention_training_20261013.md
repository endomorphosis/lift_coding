# LegalIR temporal attention integration, 2026-10-13

The N7 temporal attention candidate completed 32 bounded updates and passed its technical retention checks. It failed the preregistered engineering selection gates, so it does not replace the default decoder.

The candidate and fixed historical N6 CE control both score 95/96 complete legacy IR, 25/36 fresh-development temporal presence and 19/36 fresh-test temporal presence. Fresh complete joint IR is 0/36 on both splits. Older authored evaluation joint IR is 49/72 for attention versus 50/72 for the control. Training temporal presence was already 168/168 before this run; complete training IR stays 153/168.

All 632 initial complete-head and 632 final protected-head comparisons pass. The separate independent recount verifies 35 panel summaries, 32 scored row sets and 20 paired comparisons. The first technical attempt failed before any update after 704 inference forwards and remains preserved with its 200 MB retained claim. The successful retry uses 1760 inference forwards and 32 training batch forwards, with zero new historical-control updates.

The implementation and contract tests belong to the `external/ipfs_datasets` source repository. See the [source experiment guide](../../external/ipfs_datasets/docs/guides/legal_temporal_attention_training_20261013.md). This root change records compact evidence and the final source gitlink; full checkpoints/raw captures remain in the separately verified Hub archive.

The next proposal is an actor span correction from the common N4 parent. Manual authored-reference review separates the 15 remaining whole-IR failures into 12 selected actor-boundary errors, two selected condition-boundary errors and one abstention. The aggregate 13 actor-role nonmatches include the abstention. Examine source-local modal/quote boundary features and grammar candidates, with a head-only control preserving modality and permission outcomes. This review provides no legal-expert or statutory gold. It is a design proposal. No additional training or admission was performed for this proposal. Existing fresh 72 examples are exposed engineering diagnostics. Statutory 8 stay unscored, semantic accuracy remains unset, latent semantics and broad-family compatibility remain unqualified, and no new `lake build legal` execution is claimed.

[Public summary](../implementation/reports/evidence/legal-temporal-attention-20261013-01/public-result-summary-v01.json), [independent result review](../implementation/reports/evidence/legal-temporal-attention-20261013-01/result-independent-review-v01.json) and [next gaps](../implementation/reports/evidence/legal-temporal-attention-20261013-01/next-experiment-gaps-v01.json) retain the measured negative result.

Source integration commit: [7e60814a93fb81604092a0e0627fbc1996e644b7](https://github.com/endomorphosis/ipfs_datasets_py/commit/7e60814a93fb81604092a0e0627fbc1996e644b7).
Source contribution: [4a3ee0e6aa5d1af4a540f45aed3b88eff7207aa1](https://github.com/endomorphosis/ipfs_datasets_py/commit/4a3ee0e6aa5d1af4a540f45aed3b88eff7207aa1), merged through [PR1296](https://github.com/endomorphosis/ipfs_datasets_py/pull/1296).
Hub repository: `Publicus/legal-ir-autoencoder`.
Release prefix: `releases/20261013-temporal-attention-v1`.
Immutable Hub revision and verified archive URL: [3440e82e07555b9f7e1d2608cac762ef66eecae4](https://huggingface.co/Publicus/legal-ir-autoencoder/tree/3440e82e07555b9f7e1d2608cac762ef66eecae4/releases/20261013-temporal-attention-v1).
Publication receipt: [verified publication receipt](../implementation/reports/evidence/legal-temporal-attention-20261013-01/hf-publication-verification-v01.json).

[Compact manual authored training-error review](../implementation/reports/evidence/legal-temporal-attention-20261013-01/authored-training-error-review-v02.json) refines the older aggregate gap counts. This compact packet is retained in Git evidence and is outside the already sealed 136-file Hub release specification.
