# Permission retention training comparison — 2026-10-12

The all-parameter source-span decoder improves the newer authored panel but loses established permissions. The matched span-head-only decoder protects the modality representation and limits adaptation. Both candidates remain retained; no default model was selected or promoted.

## Published contribution

- Source PR: https://github.com/endomorphosis/ipfs_datasets_py/pull/1292
- Actual source merge: `b95938c2a816075466f8dc84f339cf622414030d`, ordinary two-parent merge with first parent `12b2de0f1c949b793772ce29edad84355978b9b7` and exact contribution head `22aefbb4cbcb3569b94c81fc3071bcffc416d8d2`.
- Immutable weights and evidence: https://huggingface.co/Publicus/legal-ir-autoencoder/tree/c1aa22e1677a7887ece53aac7caa52cef23ca8d7/releases/20261012-permission-retention-v1
- The Hub release adds 142 files / 67,107,397 bytes, preserves all 4,102 old remote identities and root attributes, and verifies every new downloaded byte. Weights and full private resource bodies are excluded from Git.
- Source contribution: 93 new source/test/documentation/evidence objects, 8,618,333 blob bytes. Actual first-parent changes match the closed object map exactly; all nonowned objects are preserved.

## Matched result

Both cells start from the same source-only 400-update parent and use identical 168 training rows, seed/order 1729, batch 12 and 32 fresh Adam updates. The all-parameter arm trains 23 named tensors. The frozen arm trains only the six presence/start/end tensors and freezes the other 17. The configured 384D latent path is disabled, with zero encoder calls. The new trainer records actual subset optimizer state; existing producers and defaults remain unchanged.

| Exposed authored panel | Parent raw/joint | All parameters raw/joint | Span heads only raw/joint |
| --- | ---: | ---: | ---: |
| Older tuning (96) | 96/96 | 93/93 | 96/96 |
| Fresh tuning (36) | 0/0 | 6/15 | 0/1 |
| Fresh challenge (36) | 7/7 | 23/23 | 8/8 |
| Older authored evaluation (72) | 12/12 | 49/52 | 16/16 |
| Authored development (72) | 0/0 | 40/42 | 4/4 |
| Newer authored evaluation (72) | 6/6 | 19/22 | 6/6 |

The frozen arm preserves all 392 full three-way modality vectors bit-for-bit and produces zero permission-to-obligation regressions on the older tuning panel. Full training produces three such regressions. Full training exactly reproduces the preceding targeted-loss control's 392 saved score payloads. Frozen modality also preserves existing mistakes: among the newer panel's 24 permission targets, parent/frozen heads give 14 permissions, four obligations and six prohibitions; full training gives two permissions, 13 obligations and nine prohibitions. Head errors and decoded abstentions are reported separately.

## Validation and limits

All 179 pure tests and 325 subtests passed with no skips. The two runs completed 64 updates and froze 87 output files before their new comparison was scored; reference panels had already been exposed. Independent recounts verified result counts and runtime receipts, and both reservations were released. Resource enforcement was sampled, not a kernel quota or continuous custody guarantee. No resource caps were raised or foreign ledger entries changed.

Current hosted CI is documented in `artifacts/legal-permission-retention-20261012-01/source-hosted-ci-observation-v01.json`; the local test result does not imply a successful hosted workflow.

These authored panels share templates and are exposed engineering evidence from one seed. The eight law examples are unscored observations. This run does not establish independently reviewed US Code accuracy, genuine 8D/384D/768D conditioning, broader logic-family correctness or actual `lake build legal` compilation.

## Next training experiment

First use saved outputs for a clearly labeled diagnostic combining frozen-parent modality predictions with adapted span predictions. It is not a trained model or blind evaluation. Then compare an actual architecture with a frozen modality feature path and a separate trainable span feature path, initially copied from the same parent, at matched data/order/update budgets. Retain the older permission gate and count existing/new modality mistakes separately. The frozen modality branch cannot repair its existing errors.

Before interpreting this as legal autoformalization progress, establish independently reviewed source-context targets from the user-provided US law datasets, freeze provision-group and cross-reference-aware splits, and qualify each real latent pair and typed logic-family adapter with actual compiler outcomes. Source gap documentation provides the broader staged plan.

## Preservation

Integration uses isolated worktrees and exact closed staged/committed/merged object inventories. The opening independent audit preserves 32 selected historical commits, five recovery references/worktree heads with unchanged branch-only counts, 15 historically absent branch names, and canonical HEAD/symbolic/raw-index endpoints. The final audit separately checks actual merge first-parent preservation and the newer compact-context and accelerator work. Canonical checkouts are not advanced by this contribution; the root datasets gitlink points to the actual source merge above.
