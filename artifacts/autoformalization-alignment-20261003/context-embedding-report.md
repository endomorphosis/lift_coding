# Declared-context embedding sensitivity

The experiment produced 204 new native vectors: 68 in each independent 8D,
384D and 768D source lane. It reused the 102 saved raw-source vectors from
the earlier development generation. Supplying the two different declared
contexts separated their same-wording vectors in every lane. This measures
numerical sensitivity to additional input tokens; correct interpretation and
autoformalization improvement remain unmeasured.

## Matched input comparison

Each of the 34 authored source/context inputs has three views:

| View | Encoder input |
| --- | --- |
| Raw source | Original source text; saved vectors reused without inference. |
| Source frame only | Role-marked JSON containing exact source text and empty assumptions. |
| Declared context | The same JSON shell, with declared assumption text and bindings included for the two contextual inputs. |

The 32 inputs without assumptions have identical encoder text in the two new
arms. The two contextual inputs share exact source wording but supply
different actor assumptions. Their frame-only texts are identical; their full
texts differ. No row ID, split label, formal target, reference signature or
arm label enters the rendered encoder text.

The renderer uses sorted, compact UTF-8 JSON without a trailing newline. It
preserves original source and source/context input identities separately from
rendered-text and transport identities. The outer receipt records context
forwarding. The unchanged native producer's inner receipt concerns the literal
serialized text, rather than the original raw-source experiment.

## Observed vector changes

The same-wording pair was exactly equal by vector values and vector hash in
both the raw-source and frame-only views, in all three lanes. With its two
different declared contexts, the observed pair distances were:

| Native source lane | Declared-context pair cosine distance | Declared-context pair L2 distance |
| --- | ---: | ---: |
| 8D spaCy feature hash | 0.006120290 | 0.110637128 |
| 384D GTE-small | 0.004075981 | 0.090288217 |
| 768D multilingual GTE | 0.017622256 | 0.187735221 |

Cosine uses stable unit directions, with roundoff clamped to [-1, 1]. L2 uses
the supplied normalized values without renormalizing them. A larger separation
does not establish a better encoder, correct actor resolution, or useful
retrieval. The context text and structured bindings repeat some cues; their
individual effects are not isolated.

All 32 unchanged-text controls per lane passed the fixed numerical tolerance:
both L2 and cosine distance at most `1e-5`.

| Lane | Exactly equal control vector values and hashes | Controls within tolerance | Maximum control L2 distance |
| --- | ---: | ---: | ---: |
| 8D | 32/32 | 32/32 | 0 |
| 384D | 29/32 | 32/32 | 3.542e-7 |
| 768D | 32/32 | 32/32 | 0 |

Three supplied 384D control results differed slightly despite identical text.
The receipt profile uses batches of 16; this assay does not independently
identify the numerical cause. These observed comparisons establish neither
general determinism nor repeated-run stability. Vector-hash equality is
reported separately from numeric value equality.

Formatting itself changed every raw-source vector beyond tolerance. Across
all 34 inputs, the mean formatting cosine distances were 0.128808286 for 8D,
0.126336836 for 384D and 0.258563037 for 768D. On the two contextual inputs,
mean frame-to-declared-context cosine distances were 0.010154159,
0.013096178 and 0.078305622 respectively. These are different-sized groups;
the per-input receipts preserve the actual comparisons. The same JSON shell
is a necessary control for attributing the added-context change.

## Native execution and unchanged evidence

All three lanes produced 68 embedded receipts, with no rejected or missing
vectors. The run used the installed native Python environment
`/home/barberb/.local/bin/python`, CPU execution, existing local assets, and
the exact pinned encoder profiles from the raw baseline. The runner compared
backend profile, implementation hashes, runtime versions, pooling, precision,
batch settings and assets before accepting numerical comparisons. It also
matched the spaCy model/codec identity, GTE-small model identity, and complete
multilingual checkpoint-loading identity.

Recorded new-input token ranges were 20–50 for spaCy, 80–137 for GTE-small,
and 86–148 for multilingual GTE. No input was truncated. These short examples
do not test maximum-context behavior. Source preparation, inference and saved
assays completed in 26.123 seconds; model downloads and raw-baseline inference
were unnecessary.

The [machine report](context-02/report.json) binds 46 listed implementation
sources, including all 42 distinct sources bound by the previous embedding
and review-admission generations. Those sources and the protected protocol
remain unchanged. Listed-file integrity is not a complete dependency manifest
or an independently attested runtime.

The [first attempt](context-01/report.json) is preserved separately. It ran in
the lightweight test environment, where spaCy, Transformers and Safetensors
were unavailable, and produced zero vectors. Its pipeline-completion status
does not indicate native production; its three lane statuses and comparisons
record unavailability explicitly. The successful native run is `context-02`.

Report file SHA-256:
`981c280dd6d1c9116502238af8c4f86b0ea828b140a3d6b829a79624b8d12e3e`.
Report payload SHA-256:
`3e30dca46bfbfbbb425fbd5604c44e767e8309cccea29f7ac38c74ec2c73f24d`.

The [validation receipt](context-embedding-validation.json) records source,
input, native-lane, assay and review replay, document links, and the focused
engineering checks: 262 passing tests and Ruff on seven Python files. Two
test-only import-order edits followed that test run; implementation bytes
were unchanged. The [runbook](../../external/ipfs_datasets/docs/autoencoders/alignment_context_embeddings.md)
and [configuration](../../external/ipfs_datasets/configs/autoencoders/alignment_context_development_v1.json)
describe the reproducible input policy and evidence scope.

## Consequences for the improvement plan

The new profile can deliver declared context to each existing source encoder
without changing its numerical lineage. Retain raw-source and frame-only
controls in later experiments. Compare this JSON renderer with a separately
versioned natural-language role rendering or separate source/context fusion
only against independently reviewed interpretation and retrieval outcomes.
Observed distances provide no basis for selecting one renderer or source lane.

All 34 source/context review items remain pending, with zero submissions and
no authenticated independence. No context resolver, actual autoencoder
representation, learned alignment head, retrieval policy, statement generator,
Leanstral hidden-state extraction, or native proof was evaluated here. The
next evidence work is independent source-facet review and a larger disjoint
corpus, followed by matched learned-representation and interpretation checks
under the same admitted information.
