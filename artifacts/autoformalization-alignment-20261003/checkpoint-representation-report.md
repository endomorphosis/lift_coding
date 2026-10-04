# Frozen checkpoint representations and retrieval

The retained 384D source decoder produced three actual learned endpoints for
all 34 authored inputs, yielding 102 endpoint vectors without re-encoding the
sources. All three endpoints scored below the saved raw GTE-small control on
the eight positive development queries. This supports retaining raw source
retrieval and evaluating contrastive alignment as a separate objective. It
does not establish which representation best preserves source meaning.

## Matched retrieval outcomes

Every arm ranks the same sixteen TRAIN source examples by cosine, with a
top-five budget and deterministic input-ID ties. References enter only after
ranking. The fixed seven-facet authored relevance and same-pool ideal ordering
match the earlier source-vector experiment.

| Representation of the 384D input | Endpoint width | nDCG@5 on eight positive queries | Difference from raw |
| --- | ---: | ---: | ---: |
| Saved raw GTE-small vector | 384 | 0.961897 | 0 |
| Residual branch activation | 8 | 0.842882 | -0.119015 |
| Learned residual projected vector | 384 | 0.903596 | -0.058301 |
| Formula decoder conditioning state | 32 | 0.758260 | -0.203637 |

These are predeclared endpoints of one checkpoint. They were not selected by
these outcomes, and their widths remain distinct from the independent 8D
spaCy and 768D multilingual source lanes. In particular, the 8D residual
activation needs the original 384D input skip connection for reconstruction;
it is not a complete compressed autoencoder state.

All four controls attain the same available qualifier identity coverage:
condition recall 0.75 averaged over queries and 0.80 weighted by occurrence,
with exception and temporal identity recall 1.0. The training pool still
contains no exact development target or full core tuple. Exact-counterpart
recall remains unavailable, and observed core-scoped qualifier/full-rule
coverage remains zero. The different scores concern ranking under authored
relevance, rather than new semantic coverage or proof utility.

The eight unsupported/ambiguous inputs receive diagnostic rankings without
semantic scores or abstention decisions. The two explicit-context cases also
receive diagnostic rankings; their context is withheld from this source-only
checkpoint. Their identical source vectors yield identical endpoint vectors.
The earlier declared-context experiment retains its separate input profile.

## Actual learned-state extraction

The unchanged donor file has SHA-256
`6e3f4d731d798aa2732afc37bd74fec34da3267a323844975d2dab78f59f9c61`.
Its architecture is `residual-projection-latent-formula-gru/v1`, with thirteen
serialized tensors and 25,224 parameters. The selected residual width is 8,
condition width 32, input/output width 384, and input normalization is identity.
The checkpoint records 1,500 performed optimizer steps and a selected
900-step generation; no training occurred in this experiment.

The current full source-decoder loader rejects the checkpoint's complete
implementation manifest because its cross-domain UI-decoder pin differs from
the current file. The new extraction profile preserves that failure boundary.
The existing offline teacher inspector admitted the exact checkpoint and
fourteen listed sources in the preserved donor tree. The experiment then used
the existing original thirteen-tensor constructor under a separately named
projection-only profile. It did not edit stored pins, run the UI decoder, or
admit the current full decoder.

Only the saved native GTE-small vectors enter the layers:

`branch = tanh(down(x)); projected = x + up(branch); condition = tanh(condition_layer(projected))`.

Source text supplies identity only. No parser features, formal targets,
expected outcomes, reference prefixes, sample memory or target-assisted
safety projection enter these operations. No GRU or formula token call occurs.
Public sparse `encode()` readouts can still apply target-assisted safety
projection, so they are unsuitable as the primary learned-state control.

The native run used CPU float32, one thread, evaluation/inference mode, and
row batches of one. Loaded parameter hashes match the donor before and after
extraction, with no gradients. An independently loaded existing numerical
model returned bitwise-equal projected vectors and conditioning states for
every input. Source preparation, extraction and retrieval completed in
2.197 seconds. No backbone inference, model download, optimizer, LLM or prover
call was needed.

## Reconstruction and checkpoint readiness

The learned 384D projection has mean coordinate MSE 0.002065231 relative to
the supplied raw vector, mean L2 correction 0.884312557, and mean unit cosine
similarity 0.772503297. Raw identity has zero input-reconstruction error.
These numerical preservation measurements answer a different question from
retrieval or source fidelity; they cannot establish superiority over identity.

The [readiness receipt](checkpoint-01/readiness.json) records the inspected
lane selections:

- The retained local `en_core_web_sm` linguistic checkpoint has all thirteen
  vector-weight tables empty. It contains populated categorical logit tables,
  whose behavior was not evaluated here. This metadata inspection does not
  reload that runtime or claim a learned 8D vector endpoint.
- The retained source384 checkpoint supports this projection-only comparison.
  Its full current decoder remains unadmitted.
- The inspected 768D coexistence catalog selects no trained autoencoder
  checkpoint. Native multilingual backbone vectors are available. This is a
  finding about that selection, rather than an exhaustive absence claim.

Checkpoint training and tuning manifests declare 180 and 60 rows. Exact
source, casefolded/whitespace-normalized source, and vector-hash intersections
with this panel are all zero. Only checkpoint metadata was inspected; no
original corpus rows were opened. These checks do not authenticate semantic
source-group independence or create a confirmation set.

## Saved evidence and verification

The [machine report](checkpoint-01/report.json) binds seven saved artifacts,
55 listed executing source files, the fourteen-file archived donor inspection,
all selected assets, saved raw-source receipts, panel and review bindings,
and the protected protocol. All 46 source files from the preceding context
generation remain unchanged. Listed-file integrity remains distinct from a
complete dependency manifest and independent runtime attestation.

Report file SHA-256:
`22d30a0566e1d81d5f94980e7a018da8775d2a26ef894ec3ec493850c2b66f42`.
Report payload SHA-256:
`ede7fa782440272208e16f8d7411eb137bda5b4c0ed372b6c3020030be8026bf`.

The [validation receipt](checkpoint-representation-validation.json) records
exact plan/receipt/ranking/scoring/assay replay and an additional scalar
float64 layer-equation check against every observed float32 endpoint. Maximum
coordinate discrepancies were 3.24e-7 for the residual activation, 2.09e-7 for
the projected vector, and 3.71e-6 for conditioning, all within the fixed 1e-5
component tolerance. This mathematical check does not establish general
runtime repeatability or semantic meaning. Focused checks passed 176 tests
and Ruff on six new Python files. A helper-name and CPU-thread ordering issue
were corrected before any generation output was written.

The [runbook](../../external/ipfs_datasets/docs/autoencoders/alignment_checkpoint_representations.md)
and [configuration](../../external/ipfs_datasets/configs/autoencoders/alignment_checkpoint_development_v1.json)
document the selected assets and representation recipes. All 34 independent
source/context reviews remain pending, with zero submissions. No formal
statement, proof, fidelity qualification or production selection resulted.

The next alignment experiment should keep frozen raw encoders, use explicit
trainable source/formal heads and semantic negative masks, and compare against
these preserved controls. Independent source-facet review and a larger
disjoint corpus remain necessary before claiming that any representation
improves autoformalization.
