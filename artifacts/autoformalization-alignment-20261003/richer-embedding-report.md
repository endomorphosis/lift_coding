# Native source embeddings and richer structural retrieval

The experiment produced real source vectors for all 34 authored inputs in
each independent 8D, 384D, and 768D lane. The fixed source-to-structure ridge
prototype improved the 768D retrieval score on this small panel and reduced
the 8D and 384D scores. These observations support retaining raw source
retrieval as a control. They do not establish that an autoencoder, statement
generator, or prover improved.

## Measured retrieval comparison

| Source representation | Raw source cosine nDCG@5 | Structural ridge nDCG@5 | Difference |
| --- | ---: | ---: | ---: |
| 8D spaCy feature hash | 0.906353 | 0.787888 | -0.118465 |
| 384D GTE-small | 0.961897 | 0.915219 | -0.046678 |
| 768D multilingual GTE | 0.983838 | 0.995722 | +0.011885 |

Each head trains on exactly 16 authored training examples and ranks all 16
training demonstrations. Evaluation uses the same eight positive development
queries and top-five budget. The formal anchors are L2-normalized 2048D
positive hashed structural counts, with seed zero. The ridge map uses source
unit vectors, alpha 1.0, a dual linear solve, and no intercept. No policy or
hyperparameter was selected using development scores.

Relevance is a fixed, equal-weight average over seven facets. Single-rule core
facets use exact identity matches; qualifier facets use typed atom Jaccard.
DCG uses the linear relevance fraction and is normalized against the best
ordering of this same training pool. This authored structural relevance is
separate from independent source meaning and useful proof coverage.

The pool contains no exact counterpart or full core tuple for any development
reference. Exact-target retrieval is consequently unavailable, and strict
core-scoped qualifier and full-rule coverage remain zero. All six retrieval
controls attain the pool's unscoped qualifier identity ceiling: conditions
6/8 by mean query recall and 8/10 by occurrence-weighted recall; exceptions
and temporal atoms 100%. The two `identity_verified` condition occurrences
are absent from training. The observed ranking differences do not increase
the set of qualifier identities supplied by the pool.

## Actual encoder execution

The 8D lane uses the verified frozen spaCy lexical, POS, dependency, and modal
cue feature stream with the installed `en_core_web_sm` pipeline. Its signed
feature hash, L2 normalization, and six-decimal output are the existing source
representation. No autoencoder state or target-aware reconstruction operation
was executed.

The 384D lane uses the pinned local GTE-small checkpoint
`17e1f347d17fe144873b1201da91788898c639cd`, CPU float32, mean pooling and L2
normalization. Its full native production receipt retains exact source byte
spans, actual forward-token evidence, verified model assets, and original
float32 outputs. The source byte blob can be reconstructed by ordered UTF-8
concatenation of the saved input texts.

The 768D lane uses the user-specified multilingual GTE model at revision
`9bbca17d9273fd0d03d5725c7a4b0f6b45142062` and implementation revision
`40ced75c3017eb27626c9d4ea981bde21a2662f4`. Seven ordinary files, totaling
627,905,786 bytes, were downloaded into a new experiment asset directory and
matched the existing pinned manifest. The complete checkpoint loader admitted
all 138 encoder/classifier tensors without missing, unexpected, or ignored
keys. Classifier logits do not supply the dense embedding. The first-source
probe verified bitwise-equal complete-model and bare-encoder hidden states;
the actual embeddings use CLS/L2 on CPU float32.

The recorded token ranges are 7–37 for spaCy, 9–41 including special tokens
for GTE-small, and 10–43 including special tokens for multilingual GTE. No
source was truncated. These short-input checks do not verify maximum-context
numerics or long-input memory capacity. Native byte and runtime receipts
provide integrity evidence, not external cryptographic attestation or semantic
qualification.

## Context, review, and generation

Only exact source text enters the encoders. The two interpretations sharing
source wording but different explicit assumptions retain distinct input hashes
and have exactly equal source vectors in all three lanes. Neither context is
applied. Both cases are excluded from semantic retrieval scoring. The eight
unsupported or ambiguous development inputs have diagnostic rankings only;
these rankings do not constitute an abstention or clarification decision.

The richer review bundle was loaded by its file hash and revalidated as blank
preparation before its status entered this report. All 34 items remain
pending, with zero independent submissions or authenticated reviewer identity
attestations. The existing parser's 22/24 authored-reference matches remain
unchanged. No statement generation, native/kernel proof, or Leanstral hidden
state extraction occurred. Leanstral's configured runner required more
available host memory than the initial preflight reported.

## Evidence and verification

The [machine report](richer-embedding-01/report.json) binds 38 listed executing
source files, the protected protocol, the prior panel and blank review bundle,
all encoder receipts, three ridge heads, and all rankings and posthoc scores.
The 27 predecessor source bindings remain unchanged. CPU inference and
retrieval completed in 17.494 seconds; the separate pinned asset staging took
1193.104 seconds. The
[staging receipt](richer-encoder-assets/staging.json) records exact official
revision URLs, hashes, and sizes.

Report file SHA-256:
`1c663860ededddead242464a78a8a672a57a5c6727924b98108e0edc1399776b`.
Report payload SHA-256:
`9d79626ec7e81a043163a8636fa737ece867765a93168a2298a64490836873e3`.

The [runbook](../../external/ipfs_datasets/docs/autoencoders/alignment_richer_embedding_retrieval.md)
documents the profiles, relevance formula, and evidence limits. The
[configuration](../../external/ipfs_datasets/configs/autoencoders/alignment_embedding_development_v1.json)
pins the predecessor and local assets. Detailed reconstruction of receipt,
head, ranking, source, review, and focused-test evidence is recorded in
[richer-embedding-validation.json](richer-embedding-validation.json).

The next alignment comparison needs a larger, independently annotated corpus
with qualifier identities and rule associations represented across disjoint
source groups. Keep the raw retrieval controls and compare learned objectives
against them. This stage does not support replacing an existing encoder or
autoencoder based on eight exposed development cases.
