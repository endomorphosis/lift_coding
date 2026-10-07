# Normative selected checkpoint replay completed

Date: 2026-10-07. The separate opt-in Legal384/768 runtime now accepts the exact
saved normative zero and auxiliary recipes, without changing weights, recipes,
vectors or original-contextual defaults. Four actual selected states replay
their original 48-row cached validation split. All 192 outputs match the archived
contextual parents' tokens/status/EOS, preserving weights, inputs and RNG.

The [datasets API and contract](https://github.com/endomorphosis/ipfs_datasets_py/blob/6a954ecef4fa78a5e58aa4fdb070cc3d1e86fcff/docs/autoencoders/normative_legal_ir_runtime.md)
and [next-step plan](../../implementation_plan/docs/62-normative-decoder-runtime-2026-10-07.md)
explain selection, scope and remaining reconstruction work. Later datasets main
`47d492c697f3e766d107ae9c02d8b8dcd18660b2` preserves this tested contribution and
the other agent's bounded finite-record projection addition; none of the fifteen
runtime source files changed in that successor. The parent's newer October 7
reconciliation and qualifier-boundary contributions are retained too.

| Evidence | Observation |
| --- | --- |
| [Independent code review](independent-review.json) | Reviewed four changed source/test files; prior foreign registry-module origin finding resolved |
| [Initial control receipt](runtime-controls.xml) | 163 old and 28 new cases pass |
| [Final normative controls](normative-controls-final.xml) | All 31 normative cases pass; 194 distinct cases overall, no failures/errors/skips |
| [Actual final preparation](preflight-final/original-assets-preflight.json) | Four selected states, exact fifteen-owner/asset pins, no Torch import or model load |
| [Genuine catalog resolution](registered-selector-resolution.json) | All four exact ten-selector lookups match registered original pins; native read-only store, no manager/write |
| [Actual decoder replay](generation-final/generation-result.json) | Four states × 48 source-only rows, all EOS, unchanged tensors/vectors/RNG |
| [Separate parent comparison](original-parent-parity.json) | All four have 48/48 exact token/status/EOS parity; no gold scoring |
| [Independent result check](independent-result-check.json) | Independently verified all 192 typed outputs, row order, source/context/mask joins, tensor pins and four recorded bindings |

The selected and last-attempt containers remain published and registered from
the [previous availability completion](../normative-checkpoint-availability-20261006/README.md).
The runtime only accepts `role="selected"` independently of `selected=True`.
The versioned decoder contract is an execution API identity; native schema,
profile and format remain null. All runtime-release, teacher, quality, complete
IO and proof qualification flags remain false. No supervisor default, encoder,
optimizer, fitting, Hub update or new registry write was activated.

The inputs are the original caller-bound cached validation split. Fresh wording,
the normative TRAIN bank, nonempty qualifiers and arbitrary new text are not
admitted by this API. Parent-output retention does not establish a fresh semantic
holdout or exact original legal-text reconstruction. The inherited 512 experiment
setting does not newly authenticate producer provenance or qualify long-span
decoding; historical original 768D encoder 8192 metadata stays separate.

## Retention and reproduction

[retention-manifest.json](retention-manifest.json) binds 24 original files byte
for byte. The retained actual candidate reports contain IDs and emitted tokens,
not original source vectors or weights. Plans omit source-vector payloads;
options contain pins. Existing weights, cached vectors, corpus and full database
stay at their original paths. The private pre-fix metadata plans remain earlier
observations and are not edited or used for the reviewed replay.

The [preparation script](prepare_original_assets.py), [replay/comparison script](replay_original_assets.py)
and [read-only resolution script](resolve_registered_selectors.py) retain exact
workstation/source paths. This is an evidence directory, not a portable model
bundle. On the retained workstation, preparation is followed by generation and
then a separate comparison process. The independent review pin is checked before
restoration; optimizer/fitting/encoder/DB/Hub imports and network/reference/prior
prediction reads are blocked during generation. The selected input bytes and
source generation are fenced after the calls. Reviewers did not rerun models,
read a live database or use the network.

```bash
IPFS_DATASETS_PY_MINIMAL_IMPORTS=1 python prepare_original_assets.py
IPFS_DATASETS_PY_MINIMAL_IMPORTS=1 CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python replay_original_assets.py generate
IPFS_DATASETS_PY_MINIMAL_IMPORTS=1 python replay_original_assets.py compare
IPFS_ACCEL_SKIP_CORE=1 python resolve_registered_selectors.py
```

The separate code and result reviews preserve their distinct scope. All current
auxiliary TRAIN generation is already exact on the existing cohorts; the next
reconstruction work follows the independently reviewed balanced-data proposal
and compatible qualifier/text/transfer contracts in the plan above.
