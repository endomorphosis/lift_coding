# Decoder reconstruction gap follow-up

This work adds an opt-in, strict qualifier representability preflight and diagnoses the next Legal decoder training gap. One owned observation completed successfully on four fixed 384D/768D decoder endpoints. It used frozen S/M2/E numerical owners and made no compiler speed claim or new fit.

Each endpoint saw 48 original TRAIN paragraphs and 48 normative TRAIN paragraphs, containing 360 rules and 1,440 scalar reference sites. All four original TRAIN generations reproduced the archived tokens, statuses and EOS exactly. All 5,760 scalar sites were visited and available; source, recurrent and combined distributions competed over the full 32-token vocabulary.

| Width and arm | Original TRAIN exact / 48 | Normative TRAIN exact / 48 | Normative source modality / 180 | Normative generated modality / 180 |
| --- | --- | --- | --- | --- |
| 384D zero | 48 | 19 | 121 | 121 |
| 384D auxiliary | 48 | 48 | 180 | 180 |
| 768D zero | 48 | 38 | 164 | 165 |
| 768D auxiliary | 48 | 48 | 180 | 180 |

Both auxiliary endpoints generate all 96 TRAIN paragraphs exactly, so another same-cohort combined-modality objective has no observed classification failure to repair. The 384D source-only action head has one TRAIN error (179/180), corrected by the combined decoder. The completed exposed-v3 diagnostic instead retains 19 source-head modality errors, two source-correct/combined-wrong modality decisions, and one generated action error. Increasing source scale fixes the two stored decisions but leaves the 19 source errors and worsens full-vocabulary modality cross-entropy. No scaled rollout, scale selection, checkpoint selection or inference default change occurred.

Balanced reviewed source-wording, actor, action and modality coverage is the next proposed training step. Exposed v3 sources remain outside new TRAIN. Nonempty qualifier representation and review remain separate: the current 32-token normative lane cannot represent them, and the 64-item qualifier review packet still has zero authenticated reviews. The new preflight preserves all rows, qualifier counts, scope and split boundaries and refuses lossy flattening or vocabulary fitting on a filtered TRAIN subset. A public byte fixture requires 579 tokens and correctly refuses the unchanged 512-token cap. Successful transport grants no training, semantic or proof authority.

The observation used one CPU worker, batch size 8, temperature 0, bridge names `[]`, provers false, metric disk cache false and CUDA disabled. Source-vector caches were warm; it was not a cold compiler or bridge-on legal-IR evaluation. Configured observation context/output remained 512. Original 768D caches retain their historical tokens8192 identity without relabeling or re-encoding. Original 384D paragraph/context vectors remain caller-byte authenticated without a saved encoder-producer receipt; normative producer records remain separately pinned. No encoder forward or new encoder verification occurred.

The numerical driver took 34.192 seconds; the outer guardian took 71.008 seconds. Auxiliary greedy rollout took 0.941817 seconds for 96 384D paragraphs (9.811 ms/paragraph) and 1.232560 seconds for 96 768D paragraphs (12.839 ms/paragraph), excluding setup, posthoc scoring and encoder/compiler/native/Lake work. Maximum sampled process-group RSS was 783,077,376 bytes within the reserved 1536 MiB. The 100 MB reservation was durably released after child exit 0, reap and empty owned group. These figures measure this cached decoder replay, without asserting a throughput improvement on a different cohort.

The dedicated qualifier tests pass 37 cases; the stored-logit diagnosis passes 17 pure cases; the observer passes 20 pure contracts. Nine disposable publication tests cover exact whitelists, concurrent upstream progress, source/scope mutation rejection, streaming artifact authentication, replacement-and-restore rejection and stable hardlink acceptance. Publication uses a private index and nonforce main pushes; normal working HEADs/indexes and the pinned restart12 checkpoint are preserved.

The canonical module is `external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_qualifier_training_preflight.py`; its dedicated tests are adjacent under `tests/unit/logic/legal_ir/`. The package guide and compact evidence are copied to `docs/autoencoders/reconstruction_gap_followup_20261006.md` and `docs/autoencoders/evidence/reconstruction-gap-followup-20261006/`. The immutable workspace archive retains the complete new traces, plans, provenance and actual resource receipts without model or embedding bodies. The final publication receipts identify both main commits.

This is exposed TRAIN/development evidence with empty qualifiers, not a fresh semantic holdout or proof of convergence. No new fitting, model promotion, family proof or Lake build occurred. All qualification, formalization, roundtrip and admission flags remain false. Only an applicable actual `lake build <Lib>` grants Lean admission. The Constitution remains unformalized, and the 8D linguistic teacher and 4096D lineage remain unchanged.
