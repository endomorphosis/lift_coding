# Autoencoder progress integrated with text-to-logic work

Date: 2026-10-06. This review continues the [autoformalization plan](49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md)
and [implementation backlog](50-autoformalization-alignment-implementation-backlog-2026-10-04.md).
It inventories the shared Git histories and worktrees before another training
experiment. The initial remote snapshots are workspace
`3b0162bebe0b7a09727081cb8c5f5c15378caba1` and datasets
`5171a632c6b9f0ecb2939d29d2ad74992cbfeb11`.
The [datasets progress guide](../../external/ipfs_datasets/docs/autoencoders/progress_integration.md)
provides the training-owner map and next experiment sequence.

The [grouped-decoder follow-up](59-grouped-legal-decoders-consolidation-2026-10-06.md)
reviews later mains, preserves current decoder improvements, restores historical
handoffs and contributes the new source-conditioned grouped profile.

## What was already contributed

The inventory covers 35 registered workspace worktrees and 16 datasets worktrees,
with 298 and 410 local refs respectively. All origin heads were fetched: 35
workspace and nine datasets tracking entries, including each symbolic HEAD.
Relevant branch histories, effective source trees and recent findings were then
reviewed; this is not a claim that every unrelated agent branch was qualified.
Existing dirty worktrees, locks, ordinary HEADs and indexes are preserved.

The [16-study matrix](../../artifacts/autoencoder-integration-review-20261006/findings/evidence-matrix.json)
records exact source commits, report paths, sizes and SHA-256 identities. Every
reviewed study is reachable from its repository's initial `origin/main`.
Our last two decoder contributions remain present: TRAIN-paraphrase mixtures
and balanced modality supervision retain their code, tests and evidence. The
source-v2 continuation and retained original-text reconstruction scorer are
also present. The newer generated-field trainer is extended by subsequent work;
its older branch must not replace the later implementation.

Other agents' frozen source-AE evaluation, expanded source-only training,
downstream decoder conditioning, joint span selection and six-condition joint
controls are already published. All 209 sampled alignment/publication Python
and Markdown files that exist on main match the canonical working files exactly.
The joint-span branch's remaining shared-file differences reflect subsequent
plan/backlog/gitignore changes. Its successor conditioning branch has all 27
changed paths identical to main. These are already integrated contributions,
so replaying those branch merges would add no useful source change.

The two joint-conditioning publication snapshots `8c02d655...` and
`3b39519d...` contain identical artifact trees. They represent one study, with
repeated numerical controls. The [comparison receipt](../../artifacts/autoencoder-integration-review-20261006/findings/duplicate-publications.json)
keeps that duplication explicit.

## What the studies establish together

| Work | Observed result | Consequence for the next formalization experiment |
| --- | --- | --- |
| Protected historical 8D linguistic teacher | Original feature decoder and training lineage remain separate | Preserve its replay; teacher parser omissions need source fidelity checks before distillation |
| 8D learned Legal formula sidecar | Real head training, original development 1/48 and exposed wording 0/48 exact | This result concerns a different decoder from the historical teacher |
| 384D/768D restricted formula sidecars | Selected original development 48/48; newest auxiliary changes wording exact 20→19 and 46→46 | Keep the loss opt-in and existing selected parents; lower CE is insufficient for promotion |
| 4096D native formula heads | Two-clause TRAIN fitting executes; broader exposed development is 0/12 exact in both arms | Native readiness is real, while source generalization remains open |
| Expanded source-only 8/384/768 MLPs | Nine selected models lower DEV vector MSE, but all trail TRAIN-only PCA | Measure representation and decoder benefit separately; width and reconstruction are not semantic evidence |
| Frozen native768 decoder interventions | Raw/PCA/AE generated IR, status and reason agree on every paired source/seed occurrence | Train matched conditioner-specific decoders before attributing a semantic benefit to learned features |
| Joint span selection | Raw structural proposals increase 10→183/192; all ten old proposals are preserved | Useful candidate generation, with unmeasured independent fidelity and visible semantic errors |
| Intent/UI native reconstruction and projections | Complete support and scoped real modality Lake checks exist | Preserve family-specific validators and distinguish coverage restoration from source fidelity |

The expanded MLP study has 1,827 actual optimizer updates: 1,800 selected-model
updates and 27 private numerical comparison updates. It is source reconstruction
over authored TRAIN32/DEV32 with zero semantic admission masks. Its new models
are not the Legal formula sidecars. The six-condition span study has 1,152 model
forwards for 2,304 paired greedy/joint outcomes, with no new fitting or encoder
calls. Inverse PCA/AE reconstructions retain full 768D width and use unchanged
raw-trained decoder weights. These counts describe different completed work and
must not be added as a common training success rate.

The [findings synopsis](../../artifacts/autoencoder-integration-review-20261006/findings/README.md)
includes the full lane distinctions, source limitations and measured scalar
comparisons. The datasets four-width guide now states the executed 4096D status
at its introduction while preserving its historical initial-comparison tables.

## Recover effective source, not just ancestry

Canonical source snapshots had removed some files even though their originating
branches were ancestors of main. An ordinary merge of an ancestor restores none
of those files. Restoration therefore uses exact missing paths, source hashes,
tested dependency closure and current-main preimages. Existing improvements are
preserved rather than replaced by complete older trees.

The Git decoder-profile review found a live consumer importing an absent module,
with further absent snapshot dependencies and a removed streamed-content helper.
The repair restores the tested bounded Git profile dependency closure and adds
the streaming CID function to the current content owner while preserving its
existing encoding caches. Hashing consumes every chunk and yields the same raw
source CID regardless of chunk boundaries. Source identity and a DuckDB row still
grant no formula or proof admission. Exact candidate sources and test receipts
are retained in the [branch review](../../artifacts/autoencoder-integration-review-20261006/branches/).

The older autoformalization campaign illustrates the same history/tree problem:
1,082 of 1,569 branch files were absent from the effective main tree. The bounded
recovery restores 23 useful files (699,974 bytes), including denominator
accounting, reproducible corrected tables, and authentic scalar training and
failed guidance-activation evidence. It preserves the current protocol and does
not reactivate old launchers, task-board completion flags or provider runtimes.
The [historical recovery note](../../papers/completion/autoformalization/INTEGRATION_RECOVERY_20261006.md)
states the incomplete external payload closure and the target-assisted T2
measurements. Historical compiler feedback and feature losses did not activate
the failed learned-guidance campaign. The pure replay covers 30 accounting tests
and three exact table reproductions; it runs no model or theorem prover.

Six uncommitted `all_weights` publication source/test files and six retained
completion/readback records are also contributed. Their pure tests and saved
bindings establish reviewed publication machinery and retained findings. No Hub
transfer or weight download occurs in this review. Existing publication evidence
must not be relabeled as checkpoint quality or current formula qualification.
The [recovery inventory](../../artifacts/autoencoder-integration-review-20261006/pipeline/recovery-candidates.json)
binds these 35 paths to their source blobs or exact pre-existing bytes.

The missing IR wrapper APIs are recovered as a complete opt-in interface: six
owners, their six test modules, and four additive `checkpoint_hub` entry points.
The existing optimized Legal loader remains intact. These entry points require
exact domain/cell, corpus, checkpoint and decoder-format bindings before cached
replay; original Intent/Security fragment heads remain distinct from document,
text-reconstruction and general logic decoders. Target compatibility preflight
loads no model and confers no semantic qualification. Interface tests use stubbed
model owners, so they establish contracts rather than new numerical fidelity.
Current domain owners retain separate projections, heads and losses.

The review also corrected a current raw-Lean recovery probe that labeled direct
`lean` success as an accepted native proof. Its v2 output now records
`compile_passed` and `native_compile_diagnostic` while `accepted`, `admitted` and
`lake_executed` stay false. Diagnostic control counts remain separate from
admission counts. Thirteen mocked tests cover successful raw compilation,
negative/policy/timeout outcomes and summary accounting; no Lean, Lake or model
was executed. Historical receipts retain their original bytes and scope.

## Prevent the same omission in later merges

Use the read-only [effective-tree audit](../../scripts/review_autoencoder_progress.py)
on source revisions and individual retained files:

```bash
python3 scripts/review_autoencoder_progress.py \
  --repository external/ipfs_datasets \
  --source 60f5c2951ac34231f05b54e50f2725296871c5b9 \
  --target origin/main \
  --path ipfs_datasets_py/logic/formalization/autoencoder/paraphrase_modality_auxiliary_training.py \
  --path tests/unit/logic/formalization/autoencoder/test_paraphrase_modality_training_runner.py \
  --fail-on-missing --output /tmp/paraphrase-retention-review.json
```

The target ref resolves once to an immutable commit. The command compares Git
blobs rather than uncommitted worktree contents and records history reachability
separately from identical, modified and missing paths. Default mode is an
inventory; `--fail-on-missing` supplies an explicit missing-file enforcement
check. Modified files require human or agent review against later work. Output
must be fresh, and the tool changes no Git index, branch, model or source file.
Real temporary Git fixtures cover ancestor deletion, independent identical
history, later improvements, path substitution and mutation boundaries.

## Advancement into text-to-formal-logic training

The combined work should next prepare independently reviewed source/formal
TRAIN pairs and fresh grouped evaluation material for roles, modality/negation,
qualifier presence/attachment, context, operators and multi-rule composition.
Compiler proposals, teacher outputs and agreement censuses remain separately
attributed. Use the same admitted pairs for repaired decoder heads and learned
source/formal alignment, with compatible output contracts established first.

Then compare raw/PCA/AE/source-only decoders under equal architectures,
initialization, completed updates, selection rules and decoding budgets. Report
all-facet and whole-rule fidelity alongside CE, vector losses, abstentions,
throughput and resource cost. Broader native targets may not fit the short or
fixed legal grammars; that incompatibility needs an explicit decoder profile.
Reduced latents and 4096D capacity remain separate cost experiments.

Keep the existing target, sparse-update, Arrow, Quack/DuckDB and Hub owners.
Full fitting can spend substantially more time in preparation and validation
than numerical refinement: one complete-feature study records 7.55 seconds of
refinement within 315.04 seconds of fitting. Bind reuse to exact source generation,
target, producer and policy while retaining live admission checks. A small CE
gain alone does not justify a universal optimizer or architecture change.

Family semantics and source meaning remain required. The eight-family Legal
floor and applicable code/state/TLA+ routes are retained, with solver eligibility
specific to supported profiles. Scoped native IntentIR/UIUXIR/SecurityIR/LegalIR
builds exist, but every new generated artifact needs its own required check.
Only an actual `lake build <Lib>` may grant Lean admission. This integration
review grants no model promotion, semantic qualification or law formalization.
The Constitution remains unformalized.
