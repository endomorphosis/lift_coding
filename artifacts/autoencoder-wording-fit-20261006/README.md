# Paired normative decoder training, October 6

This workspace evidence records verified native source preparation, matched 384D/768D decoder fits and prospective development wording. It follows the previous source/recurrent modality diagnosis, preserves the original 170-update stream and tests two new TRAIN wording strata. The 8D linguistic teacher, 4096D lineage and compiler/proof acceptance gates are unchanged.

The implementation guide is `external/ipfs_datasets/docs/autoencoders/normative_wording_training.md`. The experiment freeze is `external/ipfs_datasets/workspace/test-logs/decoder-normative-wording-r2-20261006`. Sources, labels, actual native caches, fitted endpoints, terminal receipts and posthoc observations have separate authenticated bindings.

## Evidence map

- `development/`: prospectively sealed 60-source wording panel, complete original-rule references, exclusions, recipe, codec and independent audit. Original DEV meanings were previously exposed; this is not a fresh semantic holdout.
- `review/native_preparation_audit.json`: actual native source/asset/context joins for 276 vectors per width. Composition64 source overlap exclusions are complete, but prior composition64 vector comparison is explicitly incomplete.
- `review/preflight_audit.json`: original checkpoint prediction parity, full TRAIN head denominators and balanced schedules.
- `review/fit_audit.json`: four actual 170-update fits, original schedule/loss controls and exact archived zero replay.
- `review/development_results_audit.json`: independent saved-output reconstruction and scalar-logit math. Reference access is gated on all eight durable generated panels.
- `pipeline/seal_evaluation.py`: endpoint and future-label bindings; it hashes future reference bytes without parsing labels or running models.
- `review-evidence.tar.gz`: bounded source, native vector, fit, prediction and trace evidence. Checkpoint tensors, model assets and duplicate inherited control/input bodies are excluded; their hashes and compact metrics remain in manifests and receipts. Existing local authenticated dependencies are required to reproduce the numerical run.

## Reading reconstruction correctly

This trains the formula decoder heads while verified local semantic encoders remain frozen. Native embeddings at 384D and 768D come from different encoders, so the comparison does not isolate dimensionality. Temperature, encoder context and output limits remain 0, 512 and 512. Greedy formula generation receives no target prefixes; teacher-forced token loss is a separate posthoc measurement.

The source, recurrent and combined head logits are captured in the same greedy pass before future reference access. Missing/unvisited scalar sites retain null correctness and remain in the denominator. This observation does not measure native input reconstruction MSE. Tiny MSE values in inherited original-panel artifacts arise from identity projection and are not evidence that a learned embedding reconstructor improved.

Exact authored scalar-rule reconstruction does not qualify broader legal text, nonempty qualifiers or all logic families. No Lake build, compiler/decompiler, solver or family projection runs in this experiment; no span receives proof admission, `roundtrip_ok` or formalized status, and no checkpoint is promoted.

The main integration also preserves the other agent's contextual runtime and its separate original-cohort IR/prose evidence. Its outputs must not be combined with this panel as a single dataset score. Ordinary working HEADs/indexes and unrelated local changes are preserved by scoped alternate-index publication.

## Results

The four fits and eight requested endpoint observations completed successfully. Selected and last-attempt tensors are identical for each arm; the table uses selected endpoints and does not treat the repeated alias observation as an independent replication.

| Width | Arm | TRAIN modality | New wording exact | Source modality | Token CE | Fit seconds | Greedy ms/span |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 384D | zero | 121/180 | 55/60 | 55/60 | 0.0083256300 | 40.385 | 3.1855 |
| 384D | 0.05 auxiliary | 180/180 | 60/60 | 60/60 | 0.0025041777 | 40.865 | 3.2234 |
| 768D | zero | 164/180 | 60/60 | 60/60 | 0.0015389897 | 50.369 | 4.4134 |
| 768D | 0.05 auxiliary | 180/180 | 60/60 | 60/60 | 0.0015766217 | 49.578 | 4.4010 |

At 384D the auxiliary fixes five complete formula outputs, with no new error on this panel, and reduces teacher-forced token CE by 69.92%. All five corrections are obligations in the separately authored “bears a duty” template. At 768D the control is already exact on all 60 sources; the auxiliary increases token CE by 2.45%. Actor, action and object fields are correct on all 60 sources in every panel. All generated documents reach EOS and pass the restricted scalar schema syntax check.

For example, `The registrar bears a duty to preserve the archive.` previously decoded as permission (`P`); the new 384D arm emits the following complete authored-rule IR:

```json
{
  "rules": [
    {
      "actor": "registrar",
      "action": "preserve",
      "modality": "O",
      "object": "archive",
      "conditions": [],
      "exceptions": [],
      "temporal": []
    }
  ]
}
```

This is the actual generated scalar-rule representation, with `O` denoting obligation. It is not generated Lean code, a general logic-family projection or a theorem certificate.

Original development formula exactness remains 48/48 for every arm. Its token CE is slightly worse with the auxiliary: +0.0000108385 at 384D and +0.0000049118 at 768D. The new wording result supports a specific 384D generalization gain, not uniform improvement across widths. No checkpoint is promoted.

Native preparation generated 276 verified source vectors per width. TRAIN/DEV encoder wall times were 7.542/1.244 seconds at 384D and 31.092/6.022 seconds at 768D, or 0.0318/0.1345 seconds per unique source across those forwards. The preparation driver took 66.424 seconds and guardian took 108.322 seconds.

Parallel width drivers took 154.457 seconds at 384D and 207.542 seconds at 768D, including compatibility, fit, original control evaluation and saved evidence. Their guardians took 236.424/265.616 seconds. The new-wording observation driver took 28.598 seconds; guardian took 64.891 seconds. Selected-panel greedy time is 0.0032 seconds/span at 384D and 0.0044 seconds/span at 768D; posthoc scoring and resource accounting are additional costs. Original row throughput during the fit call is about 30/s at 384D and 24/s at 768D. Tiny paired timing differences under host sharing are not a measured speedup.

The complete results and immutable archive manifest are under `docs/implementation/reports/evidence/decoder-normative-wording-20261006/`. Final tests cover 297 distinct pure contracts, native source/asset/context joins, exact zero numerical/tensor replay, nine original controls and same-pass full-vocabulary observations.

The next experiment should test exposed v3 wording retention and a separately sealed richer source panel before considering promotion. Preserve complete nonempty qualifiers and the original source/semantic review requirements; this 32-token empty-qualifier grammar cannot establish those capabilities. Reuse verified native caches and original update bindings, and profile validation/copy/accounting overhead before modifying the numerical training owner.
