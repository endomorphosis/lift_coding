# Retained 768D decoder discovery and source checkout

Date: 2026-10-03. Scope: read-only checkpoint metadata, recorded development results, implementation hashes, and Git checkout inspection; creation of one isolated source checkout. No model, encoder, optimizer, or prover was executed.

**Real trained 768D-conditioned decoder weights already exist.** The user-confirmed [Alibaba multilingual GTE model](https://huggingface.co/Alibaba-NLP/gte-multilingual-base) is the source embedding encoder. Its checkpoint does not supply our typed-logic decoder. The older parallel-lineage catalog and inherited-interface preparation records describe a different generation and do not establish global absence of decoder weights.

The [discovery inventory](decoder-discovery-01/inventory.json) binds 19 retained native768 runs: three source-span decoder runs, and sixteen formula-sidecar runs across three named experiment families. The latter retain 48 initial, selected, and final-attempt state files. This is a scoped inventory, not an exhaustive search of the host. The [inspection script](inspect_decoder_discovery.py) records the discovery procedure and refuses to overwrite its output directory.

## Trained source-span decoder

The existing [open-vocabulary run summary](../legal-decoder-open-vocabulary-20261002/run-01/summary.json) records seeds 1729, 1730, and 1731. Each native768 candidate completed 800 new optimizer updates in two stages. Its tuning selection retained the checkpoint after 400 updates; both 400- and 800-update files remain available.

An exact reuse candidate is:

`/home/barberb/lift_coding/artifacts/legal-decoder-open-vocabulary-20261002/run-01/native768-1729/checkpoint-400.json`

It is 3,433,326 bytes, SHA256 `fd6bd55ba3a7698401c7b8201f8ebe195f364f8295e98a13d833f420c0add2fc`. The [last checkpoint](../legal-decoder-open-vocabulary-20261002/run-01/native768-1729/checkpoint-800.json) is a separate 800-update generation. The other two seeds are bound in the inventory.

This model reads the actual source tokens through UTF8 byte embeddings and a bidirectional GRU, then predicts source spans. A separate pooled native768 vector conditions its token features through a 768→16→64 FiLM path. Selected source spans populate one canonical deontic rule. The owner does not support arbitrary paraphrased atoms, multiple rules, or multiple atoms per facet. It is a trained source-span decoder with embedding conditioning; it is not an embedding-only decoder or an embedding reconstruction autoencoder. Its own 256-source-token limit is distinct from the backbone's 8192-token ceiling.

The [source-span static admission receipt](decoder-discovery-01/source-span-static-admission.json) verifies all five selected-checkpoint implementation pins against the current canonical source files and all five native-context producer pins. The public [owner](../../external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_span_dimensions.py) has `load_checkpoint(path, expected_sha256=...)` and `DimensionalSpanDecoder.decode_formal_logic(texts, latents, latent_ablation=...)`. Their symbols were inspected statically; no loader or inference call ran. The saved checkpoint contains Adam state, but numerical reload and exact optimizer resume were not replayed here.

The [training context manifest](../legal-decoder-open-vocabulary-20261002/training-context-manifest.json) binds the same multilingual model and code revisions as the alignment study. The historical [context inspection](../legal-decoder-open-vocabulary-20261002/run-01/native-context-inspection.json) reports 1,485 source/vector joins checked with no encoder reexecution and no target access. Previously recorded challenge aggregates did not show an improvement from the real latent context over disabled, zero, or swapped context. These are exposed development observations; the utility of this conditioning path still needs an independent matched evaluation.

## Trained formula sidecars with unselected final states

| Retained family | Native768 fits inspected | Updates per fit | Selected epoch | Projection policy |
| --- | ---: | ---: | ---: | --- |
| [Native dimensions](../../external/ipfs_datasets/docs/implementation/reports/evidence/decoder-native-dimensions-20261003/results.json) | 4 | 340 | 0 | Frozen identity |
| [Action binding](../../external/ipfs_datasets/docs/implementation/reports/evidence/decoder-action-binding-20261003/results.json) | 6 | 340 | 0 | Frozen identity |
| [Generated fields, r2](../../external/ipfs_datasets/docs/implementation/reports/evidence/decoder-generated-field-training-r2-20261003/results.json) | 6 | 340 | 0 | Frozen identity |

Every inspected selected-state model-state digest equals its initial digest. Every separately retained last-attempt model-state digest differs. The inventory verifies the canonical JSON digest of every saved model state, native input width, role, training-report joins, and the unchanged disabled qualification fields. Recorded binary tensor hashes are retained as metadata; this inspection does not numerically replay them.

These are learned formula sidecars using genuine cached native GTE vectors. Their frozen identity projections do not establish learned vector reconstruction. The sidecars have no serialized optimizer-resume state and do not satisfy the production runtime contract. The earlier action-specific contrastive objective is already implemented; it is different from the proposed paired source/formal/proof retrieval objective.

For example, the generated-field r2 `768-boundary-first-last-2718` final attempt records 42/48 ordered exact development documents, 48/48 syntactically valid outputs, and seven extra and seven missing whole rules. Its final selection rejection records `whole_rules_extra` regression at lengths 4 and 8 against both baseline and incumbent. The selected state remains epoch 0. The full inventory retains every inspected run rather than presenting this example as an independently selected winner. Selection-gate diagnosis must replay these decisions before proposing any policy change; improved token loss or aggregate exactness does not waive the existing gates.

The [existing decoder study](../../external/ipfs_datasets/docs/autoencoders/decoder_length_distillation.md) explains the source profiles and development cohorts. Native768 experiments use a 512-token encoder admission limit and a 512-token decoder output bound. These experiments do not qualify multilingual or long-context decoding up to the backbone's advertised limit.

## Existing checkouts and the new isolated base

The retained September release-validation checkout is:

`/home/barberb/lift_coding/.decoder-release-validation/20260930T233813Z-c2a7a95f/external/ipfs_datasets`

It remains at detached commit `28c6bdb833a9e1309db4b01018e588aa427a05f4`. Its tracked files are clean; it has an untracked release-smoke output directory. It predates the newer native-dimension and generated-field decoder modules. Preserve it as historical release evidence.

The newer `/home/barberb/lift_coding/.worktrees/ir-release-datasets-20261002` checkout is locked for interrupted proof-index recovery, at `3315224dfd184e24ea71bad2cb137509450deb88`. Preserve that owner and lock. `/tmp/ir-release-datasets-20261001` remains registered but its directory is absent; no stale registration was pruned.

The three inspected `workspace/test-logs/<family>/experiment-source` directories are frozen source exports, not Git checkouts. Published manifests bind their sources and immutable predecessor archives. Reuse them for exact historical replay; do not assume they are working branches or standalone dependency closures.

Created a new checkout:

`/home/barberb/lift_coding/.worktrees/alignment-decoder-768-20261003`

Branch: `codex/alignment-decoder-768-20261003`. Exact local base: `64bc5734dc82db72e955f2e809b770127e9b6cfc`, the available generated-field r2 commit. No fetch was needed. The checkout is clean and sparse, containing the autoencoder owners, relevant optimizer owners, configurations, operation scripts, unit tests, and autoencoder documentation. Eight inspected helper files match both the commit and canonical source bytes. An independent agent repeated the checkout and byte checks.

This is a source base for the newer formula-sidecar route. The source-span owner, its trainer, and some other canonical additions are absent from this commit. Its canonical contract directory is also outside the current sparse scope. A source-span integration needs a separately pinned overlay or a later commit containing that owner, plus its required dependencies. The published evidence manifests remain accessible in the canonical checkout and exact Git blobs; their archive parts were not copied into the new checkout. No runtime import, dependency closure, or numerical replay is implied by clean Git status.

## Changes to the improvement sequence

1. Reuse the three source-span checkpoint selections as a narrow one-rule copy baseline. First replay the exact loader and source/latent joins in a private numerical process. Evaluate source-only, real-context, zero-context, and mismatched-context controls on matched independently reviewed inputs. Preserve unsupported multi-rule and multi-atom outcomes.
2. Replay the final-attempt sidecars as explicitly unselected diagnostics, alongside their epoch-0 selected states. Preserve their exact source exports, code, input normalization, clause positions, vocabularies, and output limits. Diagnose whole-rule association, omission, duplication, order, and the recorded rejection reasons before changing objectives or selection policies.
3. Use the isolated source checkout for new integration. Any necessary uncommitted owner enters through a hashed overlay, never by relabelling old checkpoint pins. Keep the original 8D and 384D paths and all retained state files intact.
4. Add paired source/formal retrieval alignment as its own new objective. Compare it with raw native vectors and already implemented action-contrastive features. Keep decoder generation, token copying, learned conditioning, and reconstructed vectors as separate evaluated capabilities.
5. Reconcile the selected catalog in a future new generation after runtime replay. Its currently null768 entry remains frozen because earlier receipts bind those bytes; the discovery inventory supplies the newer asset identities without rewriting history.

All 55 predecessor source bindings, fourteen preserved donor sources, and the frozen research protocol remained unchanged. No original validation corpus or sealed test rows were accessed. No independent semantic review was completed; all 34 richer review items remain pending. There were no new unit-test runs because this stage inspected metadata, created a source checkout, and updated planning documents. Earlier numerical experiments and test receipts retain their own scopes and identities.
