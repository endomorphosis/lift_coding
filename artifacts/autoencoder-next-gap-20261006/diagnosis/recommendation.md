# Next Legal 384D/768D decoder gap

The next bounded step should observe source, recurrent and combined scalar logits
on the exact published paraphrase-modality endpoints before adding another loss.
The available evidence shows a wording-dependent obligation failure at 384D, but
does not reveal which component makes those particular decisions.

This assessment reads saved JSON and source files only. It launches no model,
encoder, training, compiler, solver or Lake process. `findings.json` binds 36
evidence files and inventories 18 source files with exact hashes and function
locations; `read_saved_evidence.py` regenerates it without importing the package.

## What the completed comparison establishes

| Width and arm | R4 TRAIN modality accuracy, parent → endpoint | R4 TRAIN modality CE, parent → endpoint | Exposed v3 exact | Exposed v3 modality correct |
| --- | --- | --- | --- | --- |
| 384, zero | 180/180 → 180/180 | 0.0000480199 → 0.0000295881 | 20/48 | 139/180 |
| 384, 0.05 | 180/180 → 180/180 | 0.0000480199 → 0.00000480474 | 19/48 | 136/180 |
| 768, zero | 180/180 → 180/180 | 0.0000509461 → 0.0000315194 | 46/48 | 178/180 |
| 768, 0.05 | 180/180 → 180/180 | 0.0000509461 → 0.00000721434 | 46/48 | 178/180 |

R4 parent minimum full-vocabulary modality margins are already 6.36386 at 384D
and 5.74102 at 768D. The head is confident on these TRAIN examples before fitting.
Increasing confidence on the same bank does not address the observed gap.

All 41 zero-arm 384D modality errors are obligations: 39 O→P and two O→F. The
positive arm has 41 O→P and three O→F. Permission and prohibition are 60/60 in
both arms. The zero arm has one additional action error. Four paragraphs change:
one wrong P becomes wrong F, while three correct obligation sites become P;
one previously exact paragraph is lost. None is repaired. At 768D the two P→O
errors and every saved formula remain unchanged between arms.

384D exactness by v3 wording family is 4/16 actor-normative, 7/16 gerund-normative,
and 9/16 noun-subject for zero; the last falls to 8/16 for the positive arm.
768D has 14/16 actor-normative and 16/16 in each other family. These are repeatedly
exposed authored examples, not fresh statutory evaluation.

The R4 TRAIN wording uses “The rule requires/permits/forbids …” and “For the
actor, … is required/permitted/forbidden by the rule.” V3 uses other normative
status, normative noun and gerund-subject forms. The saved TRAIN head readout
cannot establish head accuracy on those v3 forms. Wider embeddings also use
different encoders, so cross-width differences are not a dimension-only ablation.

## How the logits are produced

`action_factorized_clause_decoder_experiment.py` defines the scalar features and
head readouts. `clause_features` transforms the explicit clause vectors through
the frozen paragraph projection and original TRAIN-only centered/RMS transform.
Separate action and non-action tanh projections produce 64 features each. The
non-action projection is shared by actor, modality and object. `_values` stacks
the full 32-token readouts into `(batch, 8 clauses, 4 fields, 32 tokens)`. Padding
zeros scalar guidance without forcing a grammar token or stopping generation.

`ordered_clause_recurrent_decoder_experiment.py:155`, `next_logits`, computes:

```
recurrent_input = token_embedding(consumed_token)
                + paragraph_conditioning
                + clause_to_embedding(concat(non_action_features, action_features))
recurrent_logits = output(GRU(recurrent_input, hidden))
scalar_logits    = recurrent_logits + cached_source_logits[causal_slot, field]
```

The clause slot is obtained from the already consumed lexical prefix. Boundary
count corrections operate at separate rule-closing sites. At an actual modality
colon, full-vocabulary greedy argmax chooses from the additive scalar logits.
No rule count or target prefix is supplied to generation. The recurrent component
already includes paragraph, clause and generated-history effects; an additive
trace does not isolate one of those causes.

An auxiliary update to the non-action projection can also change the recurrent
clause features. Consequently, a lower isolated modality-head CE need not yield
a higher combined modality margin. That is an architectural mechanism, not an
established cause of the four observed changes until their logits are collected.

## Existing diagnostic and ablation APIs

`generated_scalar_observation.py:103`, `collect_source_scalar_trace`, observes one
unchanged greedy pass. A temporary read-only hook captures the existing recurrent
output; source logits come from the generation-state cache. It adds no source-head
or model forward, model copy, forced token or reference input. Every visited scalar
site records all 32 recurrent/source/combined coordinates, causal grammar and
source-slot provenance. Float32 addition must reconstruct the combined tensor
exactly. Hooks, modes, weights, gradients and random state must be preserved.

`generated_scalar_observation.py:290`, `score_scalar_trace`, revalidates the trace
and only then accepts references. It reports source/recurrent/combined argmax,
full-vocabulary CE and margins by actual field site. Unavailable/unvisited sites
remain gaps. Its output is diagnostic and contains no differentiable loss.

`scripts/ops/autoencoder/diagnose_contextual_scalar_margins.py:194`, `observe_panel`,
provides the precedent: exact equality to archived token IDs, generation status
and EOS is mandatory before posthoc scoring. That runner authenticates a different
published study, so its recipe/publication constants should not be silently reused
for the paraphrase-modality experiment.

`ordered_clause_recurrent_decoder_experiment.py:301`, `bind_residual_off_model`,
removes the recurrent clause residual while preserving paragraph/scalar/count
paths. It makes a private model copy, changes inference and is a separate ablation,
not the zero-extra-forward observation. `bind_zero_condition_model` removes all
source paths and mask. `clause_source_controls.prepare_control` provides source
and context shuffles, reverse and rotate. None directly isolates scalar guidance
alone while retaining all recurrent conditioning; adding such a control would
require an explicit separately validated adapter. It is unnecessary for the first
additive diagnostic.

Existing `generated_source_margin_training` already provides a TRAIN-only margin
preservation loss with a strict recurrent-parameter whitelist and an execution-
matched zero control. It has been tested in a different prior comparison with
mixed exactness and added cost. Reimplementing it or choosing a coefficient from
v3 error traces would repeat tuning on exposed data. The prior contextual-margin
study also found source-wrong sites where recurrence usefully corrects the answer.
Blindly forcing source argmax or source/combined agreement is not justified.

## Small diagnostic recipe

1. Authenticate the published Oct4 training/evaluation manifests, archived source
   closure, four run summaries, selected/last-attempt state identities and original
   predictions. Keep both roles explicit, but execute the four unique selected
   endpoints once. Their tensors are identical to last-attempt within each arm;
   retain that equivalence as evidence rather than making redundant copies or
   counting eight independent endpoints.
2. Reuse the exact cached v3 source rows and contexts at each width. Preserve the
   saved TRAIN normalization, projection and codec. Run no encoder and fit no
   preprocessing. Collect source-only traces at temperature 0, output ceiling
   512, batch size 8 and one CPU worker per width under the existing outer guardian.
3. Persist all registered traces and verify exact archived-generation equality
   before opening the v3 reference JSON. Then score the decomposition, all fields,
   missing sites, and full-vocabulary target margins. Report the four 384D changed
   paragraphs and both 768D errors without using them as TRAIN labels.
4. If a training consistency intervention is proposed, also inspect the original
   TRAIN rollouts with the same observer. Measure active eligible sites and gradient
   ownership before launching a fit. Do not assume first-wrong supervision has
   signal at already exact TRAIN endpoints.
5. Choose the next intervention from this diagnosis: source-wrong v3 sites motivate
   broader independently authored TRAIN wording; source-correct/combined-wrong
   sites motivate a TRAIN-only consistency study using the existing loss path.
   Mixed cases require both counts to remain visible. Any new fit needs ordinary
   reconstruction, exact zero replay and a separately sealed untouched evaluation
   cohort. An inference ablation alone cannot establish a training improvement.

The cached inputs are
`decoder-fresh-normative-style-r2-20261004/preparation-r1/results/dimension-inputs-{384,768}.json`:
48 closed `{id, source_text, input}` rows, 180 clause-cache vectors and 180 explicit
source-context segments per width. `target_access` and `targets_attached` are
false. The 384 representation is local `thenlper/gte-small`, revision
`17e1f347d17fe144873b1201da91788898c639cd`; the 768 representation is local
`Alibaba-NLP/gte-multilingual-base` with its authenticated code/model profile.
Both saved preparations verify the actual 512-token forward limit. The profile's
historical 8192 value must not be mistaken for this experiment's context window.

## Source provenance and authority

The Oct4 training manifest already pins the existing scalar observer under
`decoder-content-matched-r3-20261004/experiment-source`. Its exact SHA256 is
`1f1d35f7fd90df0396f3222676f2ffd11f17e2b1b2c79c0a79f1600488eb08d8`,
which matches the current source at inspection. The current contextual-boundary
helper differs from the frozen numerical producer, so retain the frozen chain
rather than broadening imports to the live package or HACC tree. Exact aliases
and current/frozen hashes are in `findings.json`.

No recommendation changes success criteria or promotes a checkpoint. Only an
applicable successful `lake build <Lib>` grants Lean admission; no Lake build is
part of this saved decoder diagnosis. No Constitution span is formalized or marked
`roundtrip_ok`. Timing would be warm cached source-only observation, with bridge
names `[]`, provers false and metric disk cache disabled; it cannot be reported
as cold compiler or bridge-on Legal-IR throughput.
