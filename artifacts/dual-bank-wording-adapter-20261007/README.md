# Dual-bank replay reuses the original model and native embeddings

The [datasets adapter](https://github.com/endomorphosis/ipfs_datasets_py/blob/aed87b0d980422c2ca9efaa26cf92df30c51d768/docs/autoencoders/dual_bank_wording_training_adapter.md)
composes separately validated retained/new wording banks without changing the
original numerical trainer. The [updated reconstruction plan](../../implementation_plan/docs/65-dual-bank-wording-retention-adapter-2026-10-07.md)
incorporates the other agent's measured replacement-bank regression.

| Completed check | Result | Scope |
| --- | --- | --- |
| New private adapter controls | 82 pass | Synthetic native vectors, real CPU CE; no optimizer fit |
| Existing schedule/owner controls | 54 pass | Original helpers unchanged |
| Independent source review | Approved | 13 owner pins, receipt/ownership/timeout controls |
| Actual retained preparation | Two separately authenticated 180-clause banks | Existing control13/balanced16 envelopes, no Torch during preparation |
| Original-checkpoint forward probe | 170 detached calls, 1,020 clause observations | Original selected 384D auxiliary tensor, same native cached vectors |
| Actual sampling coverage | 85 calls/510 observations per bank | All 360 sources have two or three observations; four templates have 255 each |
| Independent actual result review | Approved | 432 native vector/token/span joins, bank/cache/logit/CE bindings |
| GitHub datasets readback | 17 files byte-identical | Source owners, test and docs at immutable published commit |

The same previously registered/public selected checkpoint has tensor SHA
`0b3c7c3b1a5581cd393d9bb8db1d24b87fe2cb9dff0be268aa2b5ed1f88b6594`.
Every observed modality argmax is correct. Mean sampled source-modality CE is
0.021159160493 for retained wording and 0.011466635487 for balanced wording.
These repeated schedule observations are not unique-source averages, formula
rollouts, teacher-forced token loss or a new reconstruction improvement.
Independent stdlib CE recomputation agrees within 4.42e-7. The generator asserts
state and RNG invariance; independent review rechecks bytes/joins and does not
rerun the model or RNG.

There are zero optimizer commits. No encoder, training, network or database
action ran in the isolated probes. Training/reference metadata was intentionally
accessed for bank preparation; there is no reference-blinding or semantic review
claim. Native asset receipts establish recorded consistency, not new execution
attestation. Resource admission, actual matched fitting and complete postfit
retention evaluation remain required. No new checkpoint, ModelManager record
or Hugging Face release is produced here. The existing 8D/768D, source-span and
prose decoder tasks remain separate.

The retention manifest pins nine evidence/script files. It preserves exact
publication copies of control XML, reviews, metadata and model-output logits;
raw model weights, embedding inventories and databases are not copied.

Useful records: [source review](independent-review.json),
[result review](independent-result-check.json),
[actual bank preparation](retained-bank-preparation.json),
[actual source CE observations](retained-bank-forward-observations.json),
[new controls](dual-bank-controls.xml), [existing controls](legacy-owner-controls.xml),
[GitHub source readback](source-github-byte-readback.json),
[retention manifest](retention-manifest.json).
