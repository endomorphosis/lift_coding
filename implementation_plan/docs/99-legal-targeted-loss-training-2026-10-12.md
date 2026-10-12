# Targeted LegalIR loss training and retained findings, 2026-10-12

The LegalIR source-span decoder now has a dedicated targeted-loss checkpoint contract and a mixed-layout curriculum for testing actor-span ranking and condition/exception presence objectives. Source [PR #1291](https://github.com/endomorphosis/ipfs_datasets_py/pull/1291) merged as `12b2de0f1c949b793772ce29edad84355978b9b7`. Its 146 additions include two modules, two tests, measured findings, a remaining-gap plan and finite public evidence. Existing source producers and checkpoint schemas are unchanged; the new policy uses its own authoritative outer schema and loader.

All four matched cells started from the same retained 400-update source-only parent with fresh Adam, the same 168 rows, order seed 1729 and 32 new updates each. Actor ranking OFF/ON was crossed with condition/exception presence weight 1/2; modality weight 2 and inference K=8 were fixed. All 151 outputs were frozen before scoring the new full authored evaluation references. The builder author could see these references, and they share authored templates: they are engineering declarations, not independently reviewed statutory gold.

| Cell | New authored raw /72 | New authored joint /72 | Older raw and joint /96 | Older permission→obligation, each readout |
|---|---:|---:|---:|---:|
| Common parent | 6 | 6 | 96 | 0 |
| Ranking OFF, presence 1 | 19 | 22 | 93 | 3 |
| Ranking OFF, presence 2 | 18 | 18 | 86 | 4 |
| Ranking ON, presence 1 | 18 | 23 | 94 | 2 |
| Ranking ON, presence 2 | 16 | 16 | 90 | 2 |

Every candidate fails the necessary older gate of 96/96 raw and joint exactness with zero permission-to-obligation errors. All four also produce 13 joint permission-to-obligation errors on the new evaluation panel. None is selected or promoted. Rankings improve candidate coverage but have mixed exact-output effects; increasing presence weight reduces joint exactness and introduces more temporal false negatives in this one-seed comparison. The next training priority is permission-preserving updates and loss-interference measurement, followed by replicated comparisons on separately authored panels.

All four checkpoints and 239 files are available at the [verified immutable Hugging Face release](https://huggingface.co/Publicus/legal-ir-autoencoder/tree/0958f81330fb7bb7664a8ce85355413d289932b7/releases/20261012-targeted-loss-v1). The 104,535,421-byte release passed independent raw-copy, immutable identity and CLI download checks. All 3,863 earlier file identities, including root attributes, remain exact. Eight bounded additive commits completed without unknown outcomes. Weights, raw head outputs and large authored data stay in that archive; Git contains the finite public evidence subset. Full shared-ledger bodies and private endpoint snapshots are excluded.

Pure validation passed 156 tests plus 266 subtests, without failures, errors or skips. Independent source, saved-output, runtime and actual-publication reviews passed. All 128 updates completed under the existing guardian. Each serial cell used a distinct 200 MB reservation that was released after durable artifacts and owned group/lease closeout; earlier 522 ledger records and existing caps were preserved, with 526 records at the final sampled endpoint. Sampled model-phase RSS stayed about 699–711 MiB. Release of accounting reservations does not delete retained weights, and these observations do not establish a kernel hard memory cap or continuous custody.

This parent contribution advances only `external/ipfs_datasets` to the actual source merge and adds this guide/evidence. It starts from newer main `318ac594c030272076635a92da05c2f4b9456d87`, retaining the parallel source-admission and selective-context work, including accelerator `06a437cdba28e148912d998bf2cb85a805a3d4d9`. The opening preservation audit verified all 32 selected historical commits as ancestral to their respective integration bases. Five separate recovery refs/worktrees retain their distinct histories and branch-only counts 48/50/5/4/6; they are not silently adopted. Canonical checkout HEAD, symbolic branch and index bytes were preserved at the observed endpoints. Final merged-tree review is recorded separately from this pre-merge guide.

- [Prior matched curriculum and retained archive](95-legal-matched-temporal-curriculum-2026-10-12.md)
- [Parallel native source admission](97-supervisor-native-source-task-admission-2026-10-12.md)
- [Parallel selective candidate context](98-supervisor-selective-candidate-context-2026-10-12.md)
- [Source qualification gaps](https://github.com/endomorphosis/ipfs_datasets_py/blob/12b2de0f1c949b793772ce29edad84355978b9b7/docs/autoencoders/targeted_loss_training_gaps_20261012.md)
- [Measured result analysis](../../artifacts/legal-targeted-loss-20261012-01/targeted-result-analysis-v01.json)

Configured 384D conditioning is disabled and no encoder ran. Genuine 8D/384D/768D latent conditioning, independently reviewed US Code/context fidelity, broader logic-family contracts and actual `lake build legal` compilation remain open qualification work. The exact source head's observed hosted jobs failed before runners/test steps because of GitHub's account billing lock; other workflow failures and queued runs are retained separately. No hosted CI success or general legal accuracy is claimed.
