# Support/action training retention archive

This archive preserves the source, corpus, recorded outputs and review evidence
for the [published support/action experiment](https://huggingface.co/Publicus/legal-ir-autoencoder/tree/f2e6e9ad6b693a605066146dd8985f036fcaa50a/experiments/support-action-20261007/run-01).
The parent [report67](../../implementation_plan/docs/67-support-action-residual-training-2026-10-07.md)
explains the resulting contribution. `published-README.md` preserves the exact
published README bytes, including its original prepublication link snapshot.

The frozen trigger parent gives 28/64 exact positive proposals and 7/64
unsupported emissions on the fresh authored final panel. Linear and MLP residuals
give 37/64 and 39/64 exact proposals while unsupported emissions worsen to 11/64
and 12/64. Both select update 120 after 240 actual updates each. The arms share
480 joint optimizer calls and 7,680 encoded source presentations; support sees
all records, and action targets supervise only 3,840 positive presentations.
The 195 versus 6,339 trainable parameters are not capacity matched. Class,
optional presence and all nonaction span outputs remain fixed.

A separate label-informed posthoc diagnostic intersects the saved parent and
candidate emission statuses. It gives 29/64 exact positives for either arm and
retains the parent's 7/64 unsupported emissions. The emission set is a subset of
the parent's on checked sources; it neither repairs existing unsupported emissions
nor establishes fresh policy performance. It was designed after final exposure,
changes no selected weights, selection or defaults, and must be predeclared and
tested on a new panel before policy use. Raw 37/39 and 11/12 results remain separate.
Both older cohorts are exposed postfit retention diagnostics.

Validation records 131 distinct decoder/proposal tests and 8 pure selector
fixtures. The byte-identical guardian retains its 23 historical pure tests; they
were not rerun for this experiment. Separate CPU2 read-only replay of the
immutable downloaded checkpoints reproduces all 768 complete outputs across
both arms and three cohorts, preserving model/parent tensors, full Adam state,
head counters, modes and RNG with zero additional updates and no references read.
Training's owned child was reaped and only its own CPU lease and disk claim were
released. The 35 model-phase RSS samples peaked at 787,025,920 bytes; this is a
sampled group sum, not an absolute peak, continuous coverage or kernel quota.

`retention-manifest.json` maps all 97 published files to exact local bytes or
immutable Hub resolve URLs, with byte counts and SHA256. The two selected
checkpoint containers, three complete TRAIN panels and six candidate selection
panels are Hub-only; no numerical weights are copied into this Git archive.
Remaining published files retain their exact bytes, plus separate postpublication
receipts under `evidence/`. `local_files` binds every local file except the
retention manifest itself. Final source contribution, integration and downloaded replay receipts are
retained separately from the immutable published snapshots.

These are authored engineering targets, mechanically checked without independent
legal review. All admission masks remain zero and formal output is null. The
model reads source text with an explicit caller attachment premise; it does not
consume legal latents or qualify real US Code fidelity, broader logic families,
`lake build legal`, reviewed statutory semantics, or default promotion. Plans
and helpers retain historical absolute paths; portable replay needs deliberate
path rebinding and regenerated reviews without changing weights or expected
outputs.
