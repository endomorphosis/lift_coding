# Bounded wording result and remaining training gaps

The independent saved-output audit passed 44,616 checks across all eight
60-source panels. It rebuilt scalar logits/CE and exact float32 addition,
decoded the actual generated tokens, checked complete ordered rules and all
seven facets, and verified the fixed head/formula denominators. No additional
model or encoder inference was performed. Both evaluation child and guardian
exited zero and the owned reservation was released.

| Selected model | Exact complete rules | Modality head correct | Formula token CE | Generation wall time per span |
| --- | --- | --- | --- | --- |
| 384D zero | 55/60 | 55/60 | 0.008325630034 | 0.0031855 s |
| 384D additional wording CE | 60/60 | 60/60 | 0.002504177679 | 0.0032234 s |
| 768D zero | 60/60 | 60/60 | 0.001538989713 | 0.0044134 s |
| 768D additional wording CE | 60/60 | 60/60 | 0.001576621695 | 0.0044010 s |

All selected/last state pairs have identical tensor hashes and identical greedy
predictions. Eight panels are eight observations of four trained endpoints,
not eight independent fitted replicates. Full observer driver wall time was
28.597861 seconds; guardian wall time was 64.891360 seconds. Every timing above
uses warm verified native source vectors, 60 samples, one worker, bridge names
`[]`, prover flag false and metric disk cache false. This is not a bridge-on
legal-IR timing. The trace-derived panel does not measure embedding MSE.

The five 384D improvements all resolve an obligation/permission confusion in
the `bears a duty to` development template. Before, both the source head and
complete generated rule selected permission (`P`); afterward both selected the
authored obligation (`O`). The other six facets stayed the same. None of the
55 previously exact rules regressed.

- `The registrar bears a duty to preserve the archive.`
- `The registrar bears a duty to preserve the notice.`
- `The notary bears a duty to approve the archive.`
- `The trustee bears a duty to publish the notice.`
- `The notary bears a duty to approve the notice.`

For the first example the real generated IR changed from:

```json
{"rules":[{"action":"preserve","actor":"registrar","conditions":[],"exceptions":[],"modality":"P","object":"archive","temporal":[]}]}
```

to:

```json
{"rules":[{"action":"preserve","actor":"registrar","conditions":[],"exceptions":[],"modality":"O","object":"archive","temporal":[]}]}
```

Complete before/after outputs and source/recurrent/combined margins for all
five fixes are retained in `paired_modality_fixes.json`. Their shared wording
pattern is the scope of the observed improvement, not evidence of arbitrary
legal text fidelity.

The same extra loss provides no measured development benefit at 768D. Complete
rules and modality heads stay 60/60, while formula token CE rises by
0.000037631982. The 768D source modality-head CE also rises from
0.000007566368 to 0.001281434557, despite unchanged argmax correctness. This
supports retaining the 768D zero arm as the comparison baseline rather than
applying the same auxiliary recipe to every width.

The original 48-row development panel remains exact for both arms and widths,
but its positive-arm CE rises by 0.000010838528 at 384D and 0.000004911794 at
768D. The 384D wording gain is therefore a tradeoff, not uniform loss improvement.
One seed and one sealed authored panel do not establish a globally optimal
recipe. The new 384D strings were excluded from TRAIN; their original target
meanings had prior exposure and influence on earlier selection. They are now
also exposed measurement inputs. Do not recycle their reference bodies into
TRAIN or rename them a fresh semantic holdout for another comparison.

The next useful gap is broader, authenticated source/target coverage rather
than further fitting this now-perfect small development panel. Keep width-
specific baselines, and prepare a new independently reviewed natural-source
confirmation set before choosing a production candidate. If auxiliary weights
or exposure are compared, choose the rule using TRAIN and the unchanged original
selection policy, seal new confirmation inputs before fitting, and report exact
source fidelity separately from CE. No checkpoint was promoted by this result.

Richer conditions, exceptions, temporal quantities and scopes require a
compatible versioned target codec and decoder, with complete targets and real
review; this fixed 32-token, empty-qualifier grammar cannot represent them.
Do not omit those facets to fit the current benchmark. The legal logic-family
floor, richer modalities, natural laws and held-out semantics remain separate
qualification work. Only real `lake build <Lib>` results can admit Lean work.
All current admission and qualification flags remain false, and the Constitution
remains unformalized.

Composition64 source strings are excluded, but the sealed numeric prior-vector
comparisons omit its saved native bundles. That comparison remains incomplete.
Old original-panel identity-projection MSE is not learned embedding
reconstruction; native encoders are frozen in this decoder-head experiment.
