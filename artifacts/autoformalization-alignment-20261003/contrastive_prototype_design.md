# Proposed weak contrastive prototype

This inventory performed no model import, fit, encoder/prover call, or DEV reference inspection. Reuse `alignment_projection.py`: frozen native384 source vectors and TRAIN-fitted 27D formal features enter separate normalized linear heads. Shared384 requires 158,592 parameters; shared512 requires 211,456. Preserve all raw 8/384/768 lanes and retained autoencoders.

**Before any numerical canary:** create a separately versioned weak-contrastive-diagnostic fit policy/manifest for the 16 unreviewed TRAIN pairs, or wait for semantic labels. Existing `weak_decoder_fit=1` does not admit alignment training: `contrastive_supervision=0`. All old masks remain unchanged; strong semantic, contrastive-supervision, proof and fidelity admission stay zero. The new 64-item review packet supplies no labels.

TRAIN contains 16 distinct typed proposals, four author groups, 124 anchors and 27 formal feature coordinates including seven unknown buckets. Author groups are not equivalence classes; typed identity binds canonical IR, operators and scope. The old action-hard-negative heuristic selects 0 directed pairs; action-specific source SupCon has 0 same-action/different-actor positives. Four unordered pairs / 8 directed pairs share modality/actor/action/object and differ in qualifiers. Those are optional weak structural contrasts, not established logical negatives.

The existing differentiable loss is symmetric log-positive-mass InfoNCE. Equal target IDs define positives; current 16 IDs give a diagonal mask. Both heads receive gradients. Negative weights are ≥1: unknown-pair exclusion needs a new versioned loss; author groups cannot supply positive masks.

Proposed matrix: seeds 1729/1730/1731 × shared384/512 × uniform weight 1 / optional qualifier weight 2 = 12 arms. Predeclare 80 full-batch SGD steps, learning rate 0.1, weight decay 1e-4, momentum 0, temperature 0.07: 960 requested main updates. Only the 8 directed qualifier contrasts receive weight 2. Match initial states between weight arms within each seed/width; retain final fixed-step checkpoints. No DEV selection. These settings and update counts are proposed, not executed or measured.

Use a narrow new runner around public head/loss/checkpoint APIs: the old experiment driver reads DEV before fitting. Fit codec/weights on TRAIN16 alone; pin source/vector/profile/typed-target joins. Queries contain source/context and cached vectors only. Preserve all 34 outcomes; do not inherit the decoder's 22-row vocabulary limit.

Fix the bank at 16 TRAIN items. Save raw 8/384/768 source-to-source cosine, initial heads, and final projected source-to-source/source-to-formal ranks; break ties by ID. Cached autoencoder views remain separate controls. Save target-free ranks before optional authored DEV8 scoring. Report whole-rule/core/qualifier pool ceilings, 6 constructible / 2 unavailable DEV rows, and all 34 denominators. These are weak diagnostics; fidelity stays unestablished.

Proposed resource admission: fresh isolated native CPU float32 child, one intra/inter-op thread, CUDA disabled; OMP/MKL/OPENBLAS limits set before Torch. Bounds: 180s wall, 170s soft / 180s hard CPU, 2GiB cooperative RSS/HWM. Measure a tiny timing pass before admitting the matrix; count its updates separately and discard its weights. Journal actual steps/limits and incomplete arms. Save initial/final checkpoints, gradients/update counts and frozen input/owner checks. Private fresh reloads require disjoint storage, exact ranks and unchanged model/RNG. No optimizer resume.

The owner enforces source384 and shared384/512. Its hardcoded GTE-small source identity currently matches the saved native384 profile exactly. Any identity mismatch requires trusted profile equivalence or a new checkpoint version; dimensions alone are insufficient. Raw 8/GTE768 require new owners/checkpoints. The 27D bag-of-facets ignores operators/multi-rule scope; current operators are uniform. General claims require a scope-preserving typed tree view. `legal_joint_retrieval.py` needs actual formal384 embeddings and diagonal InfoNCE. Modal decoder losses are reconstruction/token objectives. The loss-configuration contrastive function uses Python floats, not autograd; reuse its admitted false-negative metadata rules only with suitable labels.

Read-only SHA256 pins under `external/ipfs_datasets/ipfs_datasets_py/`. A=`logic/formalization/autoencoder/`; B=`optimizers/logic_theorem_optimizer/`:

| Owner | SHA256 |
|---|---|
| A/alignment_projection.py | `d29853a4238350eabe2265b51c48913c9e77280af0ee131bbd04ef760199c18e` |
| A/alignment_experiment.py | `3c5940850b3104dba8896a496c9c37729661bbe7778ced745c410c339798be27` |
| A/action_contrastive_decoder_training.py | `18dc019d86cb96d670dd583ad16f6930a3b8a2ffd49a587f40d1ef6cb105b497` |
| B/legal_ir_loss_configuration.py | `d088888477452dab1e2d7a26fe754e95049f3a688a56d7a719ee59ed0a34d9d3` |
| B/legal_joint_retrieval.py | `577698c99d0cdd2209bdaaee01b40778f46251e9e1256d7537312d6655cdcb9d` |
| B/modal_latent_formula.py | `ec5bdcd752d157c9fc0257a45551cfe9ce7be172af767e8ed769bf1bc8a31d36` |
| B/modal_joint_formula.py | `5dda48e79614f49c2e2c8b107811bde37260355f7d4ca4e0e54a88d883725204` |

Input pins in `canonical-codec-01/`: train_weak_supervision.json=`97a333821790db1ad11a542f918a32e583b9b4ab150b82cdd71bbd883bbc42ba`; target_free_inputs.json=`134f9a3bf917f0613fb474c04d8a5e414da443b133e12149f026cd3b5aa9473d`. This design executes no fit and changes none of those files.
