# Predicted-trigger readout improves modality; frozen support and spans remain limiting

The matched CPU experiment improves raw O/P/F class accuracy from **29/64**
with a matched global readout to **47/64** with predicted-trigger evidence. Exact
emitted proposals improve from **17/64 to 30/64** on the same fresh authored final cohort.
The unchanged donor scores 19/64 and 11/64, respectively. This advances the
[source-span pilot](64-scope-span-decoder-training-2026-10-07.md) while preserving
the earlier [reconciliation](61-autoencoder-reconciliation-2026-10-07.md),
[normative runtime](62-normative-decoder-runtime-2026-10-07.md) and
[native-cache runtime](63-retained-native-decoder-inputs-2026-10-07.md).
The selected experimental checkpoints and full evidence are available at
[the pinned Hugging Face release](https://huggingface.co/Publicus/legal-ir-autoencoder/tree/09ac0af19c801b53216f83c3544c8d54b763f091/experiments/trigger-readout-20261007/run-01).

The [datasets implementation](https://github.com/endomorphosis/ipfs_datasets_py/blob/89e485b4e26203c40b930cd9bb5ed71d8eda5207/docs/implementation/legal_scope_trigger_readout_pilot_20261007.md) adds an explicit opt-in residual
modality head to the frozen step 240 ordered source-span donor. Both arms have
the same 4,355 trainable parameters, seeded hidden tensors and zero final class
projection; initial complete donor core outputs and modality logits match on 16 measured
inputs. The donor has 22,330 frozen parameters. The global arm mean-pools encoded
token states before the donor global projection. The other arm uses those same
states weighted by normalized `P(S<=t)*P(E>=t)` from model-predicted modality
endpoint marginals. The source encoder, original class head, support, optional
presence and all pointer heads remain frozen. This is a source-derived readout,
not a result for 8D/384D/768D latent conditioning.

| Fresh final: 64 supported + 64 unsupported, 64 paired parents | Donor | Global adapter | Trigger adapter |
| --- | ---: | ---: | ---: |
| Selected adapter update | — | 120 | 240 |
| Actual adapter updates | 0 | 240 | 240 |
| Raw class correct, including blocked/refused supported rows | 19/64 | 29/64 | 47/64 |
| Exact emitted positive proposal | 11/64 | 17/64 | 30/64 |
| Whole exact with nonempty condition | 4/32 | 7/32 | 12/32 |
| Mean positive class CE | 1.09372 | 1.08300 | 0.65386 |
| Raw five spans exact | 49/64 | 49/64 | 49/64 |
| Positive learned refusal / structural block | 19 / 2 | 19 / 2 | 19 / 2 |
| Unsupported learned refusal / incidental block / emission | 53 / 5 / 6 | 53 / 5 / 6 | 53 / 5 / 6 |

The fresh corpus has 512 + 512 TRAIN rows and 64 + 64 each in selection/final.
Its 1,280 sources and 640 paired parent groups are excluded from the earlier
pilot and are disjoint between new splits. Declared actor, action, object and
condition values and semantic heads are also excluded and split-disjoint. The
eight templates and modal aliases are deliberately shared. Unicode, repeated occurrences,
nullable object/condition cells and the four unsupported categories are retained.
These are authored engineering targets, not reviewed US Code meanings. The old
12/64 score is a different cohort; the comparable donor score here is 11/64.

Both arms use seed 24603, AdamW learning rate 0.003, no weight decay, clip 5 and 240
updates. Each scheduled batch has 8 supported + 8 unsupported records. Only the
eight positives are encoded for class fitting; negatives have no class labels
and do not train the frozen support gate. Across both arms there are 480 actual
updates, 7,680 input records, 3,840 encoded positive presentations and 3,840 ignored
negative records. Full TRAIN diagnostic panels are extra source-only inference,
not optimizer updates. Last TRAIN raw classes are 215/512 and 395/512 for global
and trigger adapters. Donor moments are retained as exact provenance; each
adapter starts a fresh AdamW optimizer and does not continue donor Adam.

Selection uses raw class exactness on all supported selection rows, then whole
emitted exactness, then earlier update. Both choices and checkpoint hashes are
durable before the numerical runner parses final references; all three final
panels are durable before scoring. Authors had constructed/mechanically checked
the labels before fitting. This is a numerical barrier, not independent legal
gold or an authors-blind test. These final labels and outputs are now exposed;
further use is retention-only.

The trigger readout correctly classifies 17/21 permissions; the donor class head
classifies none correctly. Trigger confusion with O/P/F columns is O→[13,2,7],
P→[2,17,2], F→[2,2,17], with gold totals 22/21/21. Remaining class errors are
measured; one seed and a shared grammar do not establish broad generalization.

The frozen gate and endpoints impose a **38/64 whole-proposal ceiling** here.
Among those 38 emission-ready span-correct sources, class errors are 27/21/8,
yielding 11/17/30 exact outputs. Another 26 sources need changes to nonclass
behavior. For nonempty conditions the frozen ceiling is 14/32 and the trigger
gets 12/32. Raw nonempty condition spans are 31/32; a correct condition span alone
does not make a correct whole proposal. The gerund-agent template has wrong
action spans on all 8 cases, six support refusals and two bad-span emissions,
despite five correct trigger classes. It remains 0/8 whole exact. All six
unsupported emissions are modal anagrams and remain unchanged by this study.

Every emitted proposal remains unreviewed, with all five admission masks zero
and null formal output. The caller supplies attachment; the output copies it
only when a condition is predicted. Conditions remain opaque, context is
unresolved and coverage is unassessed. No semantic parser, target span, keyword
mapping or repair enters inference.
Exceptions, temporal qualifiers, multiple-rule behavior, broader-family lowering
and `lake build legal` qualification remain open. Existing 8D/384D/768D weights,
other agents' runtime changes and default asset selections are preserved.

Validation passed 93 distinct readout/donor/proposal cases and 23 pure guardian
cases. Independent reviewers checked corpus separation, source/checkpoint
closure, all score panels, actual progress, selection ties and final barriers.
They revalidated 147 final emitted proposals through the unchanged owner, all
masks zero. Separate-process two-thread replay reproduced 256 complete outputs
exactly and preserved donor/adapter/full Adam/mode/RNG with no optimizer updates.
The strengthened Hub replay also binds its script/inputs/expected panels and
fsyncs its receipt; the initial replay's less complete receipt is retained.

The guarded child exited 0 and was reaped. Its own lease and 200 MB reservation
were released. The resource audit left other claims untouched and confirmed
that the prior failed pilot's 200 MB claim remained retained.
Fourteen model-phase group-RSS samples peaked at 758,779,904 bytes (723.6 MiB),
with maximum observed model gap 1.032 s. This is a sampled non-atomic process sum,
not an absolute peak, kernel quota or continuous ownership proof. The numerical
runner took 12.27 s. Guardian admission and final inventory add overhead; the
RSS model phase also includes imports and polling.
Hosted CI availability is recorded independently from these local results.

The [retained evidence](../../artifacts/legal-trigger-readout-training-20261007/README.md)
contains the full corpus/protocol, source/result/resource reviews, metrics,
selection/barrier records and publication/byte readback. Large source-only TRAIN
prediction panels and numerical tensors remain in the pinned Hub release.
Source contribution: [datasets PR](https://github.com/endomorphosis/ipfs_datasets_py/pull/1276).

During contribution, the other agent's measured native 384D wording continuation
arrived on datasets `b6abb3263...` and workspace `d3a4550584...`; both isolated
bases were fast-forwarded to preserve it. Its balanced-bank replacement lost
retained reconstructions, while the existing-bank continuation retained both
banks. The [parallel findings](https://github.com/endomorphosis/ipfs_datasets_py/blob/b6abb3263/docs/autoencoders/balanced_wording_continuation_20261007.md)
reinforce complete retention checks and explicit bank exposure ledgers. This is
a separate architecture/denominator and is not pooled with the table above.
The source merge `89e485b4e...` also follows the newer upstream dual-bank trainer
adapter commit `aed87b0d9...`, its actual first parent. Preservation is checked
relative to that parent. The other 14 original `b6abb3263...` files remain byte
exact, and the original continuation report's prefix is preserved with the
upstream five-line append. Numerical producer pins remain unchanged. The
upstream adapter probe performed no fitting.

We therefore checked the selected readouts on the earlier exposed source cohort,
after fitting/selection, with no parameter or selection changes. Donor/global/
trigger classes are 25/28/53 of 64, whole proposals 12/15/29 of 64, and whole
exactness with nonempty conditions is 4/9/13 of 32. All 128 donor dictionaries
exactly match the archived old panel. These aggregate gains include per-case
regressions: trigger loses five old correct classes and two whole exact outputs
while gaining 33 and 19;
global loses 17 classes and eight whole exact outputs while gaining 20 and 11. The
384 evaluated rows are posthoc exposed retention only; the extra donor-logit
passes make 512 top-level forward invocations. This is not a new holdout or model
promotion. Reviewed retention evidence is appended to the pinned Hub release.

The next matched training hypothesis should preserve this stronger trigger
readout while addressing source support and action endpoints, particularly
gerund-agent action spans. Declare which donor tensors may update, the balance and
loss recipe, retention limits and a fresh final before fitting. Preserve exact
class, full-proposal, nonempty-qualifier, false-refusal and unsupported-emission
denominators together. Separately prepare reviewed source/context/meaning
examples before lowering to native logic families and checking Lean; a compiling
formula cannot supply the missing legal review. Do not retune against this final
or promote these experimental weights as default legal autoformalization.
