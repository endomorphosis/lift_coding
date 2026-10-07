# Experimental single-rule source-span decoder pilot

Two small source-only models were actually trained on an authored engineering
corpus. Ordered byte convolutions improved this pilot's exact emitted proposals,
but neither model is ready for legal autoformalization. Existing 8D, 384D and
768D autoencoder assets and cached normative runtimes were preserved.

| Fresh-final endpoint | Pointwise bytes, kernel 1 | Ordered bytes, kernel 3 |
| --- | ---: | ---: |
| Exact emitted positive proposal | 5 / 64 (7.8125%) | 12 / 64 (18.75%) |
| Learned unsupported-profile refusal | 57 / 64 | 59 / 64 |
| Unsupported proposals emitted | 5 / 64 | 4 / 64 |
| Positive exact or learned negative refusal | 62 / 128 (48.4375%) | 71 / 128 (55.46875%) |
| Raw modality class correct, all supported inputs | 22 / 64 | 25 / 64 |
| Raw five occurrence spans exact, all supported inputs | 35 / 64 | 47 / 64 |
| Selected optimizer step | 120 | 240 |
| Parameters | 21,562 | 22,330 |

Both arms ran 240 AdamW updates with the same 3,840 presentations each, seed24602,
batch16 (8 supported / 8 unsupported), learning rate0.003, zero weight decay,
gradient clip5 and fixed support threshold0.5. Same-shaped tensors were copied;
the extra ordered-convolution neighbors started at zero. Actual first-batch
logits were identical, and the initial16 source-only outputs matched. The
ordered arm has additional trainable weights; this is not parameter-count parity.

The corpus has512 paired parent groups in TRAIN and64 each in selection/final,
with one supported and one unsupported row per group. All source strings,
parent groups and facet lexemes are disjoint across splits. Eight authored word
orders cover O/P/F, nullable objects/conditions, repeated occurrences and Unicode.
Unsupported-profile rows include deleted or anagrammed modal tokens, extra
exceptions and second rules. Unsupported means outside the pilot grammar, not a
finding that the sentence is legally false. These are not reviewed US Code
targets, nor semantic gold from either JusticeDAO cache.

Checkpoint candidates were at0/120/240. Selection used positive exact plus
learned negative refusal, then fewer negative emissions, then more positive
exact, then earlier step. Both selections were durably saved before the numerical
runner opened final-reference JSON. Both final prediction panels were durably
saved before final scoring. Corpus authors/reviewers had constructed and checked
the labels before fitting; this barrier is not a claim that all authors were blind
to final labels. Final is now exposed and must not be used for another fit or
selection. Old grouped85.2% results measure a different task and cohort.

The learned head tokenizes generic Unicode words/punctuation, encodes UTF8 bytes
with two masked Conv1 or Conv3 layers, runs a token BiGRU and predicts support,
O/P/F, optional presence and separate start/end heads for modality, actor, action,
object and condition. It checks an externally supplied source SHA before model
execution. Condition attachment is an explicit caller premise, not learned.
Inference cannot access targets or the semantic parser and never repairs a bad
span. Source-derived inputs are not 8D/384D/768D latent vectors.

Every emitted proposal goes through the existing canonical-scope transport owner
and retains all five admission masks at zero. Conditions remain opaque,
source context is unavailable and coverage is unassessed. Formal output is null;
no logical formula, proof admission or `lake build legal` qualification is
claimed. Exceptions, temporal qualifiers, multiple rules and broader logic-family
lowering remain separate work.

The ordered model found modality/actor spans64/64, action50/64, object61/64 and
condition61/64. Its class head produced no P in final, and only25/64 classes were
correct. Thirty of its47 span-exact positives had the wrong class; five of the17
span-and-class-exact positives were refused or structurally blocked. Among the32
supported cases with nonempty conditions, whole-proposal exactness is1/32 versus
4/32. The ordered raw nonempty object and condition spans are each29/32; the61/64
figures above include32 correct null cases. Mean class
loss in the last20 TRAIN updates stayed near log(3), despite low span losses.
This exposes failures of the current recipe; it does not establish pooling as
their cause or demonstrate convergence.

The next hypothesis is a matched learned-trigger readout versus the current
global class readout, with the same source-only inputs, identical initial outputs,
fresh parent groups, explicit parameter accounting, per-class distributions and
separate support errors. Use predicted trigger features at inference, not gold
spans or a modality keyword lookup. Do not retrofit this release's source bytes
or tune against its exposed final.

`checkpoints/bytekernel1/checkpoint.json` and
`checkpoints/bytekernel3/checkpoint.json` are selected finite JSON containers with
strict model and full Adam state, internal seals and exact producer/Torch pins.
They are custom research checkpoints, not Transformers AutoModel weights. The
three original numerical source files are preserved under `source/`; install the
corresponding datasets contribution or copy those exact bytes into a compatible
checkout before restoring. Torch2.13.0+cu130 was used on CPU with CUDA disabled.
No encoder/model downloads or GPU training occurred.

API: `restore_scope_span_checkpoint(json.loads(checkpoint_bytes))` returns
`(model, optimizer, steps)`; call `predict_scope_span_decoder(model, source_text,
condition_attachment, expected_source_sha256=...)` for an unadmitted proposal.
The source module's unit tests document closed input/output and checkpoint rules.

Validation passed231 distinct decoder/owner tests. A separate two-thread CPU
process restored both selected model/full-Adam containers, reproduced all256
complete final outputs exactly, and left model/optimizer/mode/RNG unchanged with
zero optimizer steps. A one-thread fail-fast replay changed22 pointwise-arm
support-probability floats by at most1.1921e-7, while its other fields matched;
one-thread ordered replay was not reached. Exact replay pins the original thread
setting, rather than claiming arbitrary-thread floating-point identity.

The first gated launch failed before model/Torch training because disk inventory
delayed the monitor's first observation. Its failure receipts are retained. The
reviewed fix starts monitoring before inventory, with unchanged bounds; attempt02
completed and its child was reaped and its own lease/reservation released. The
training runner took12.58s; the guardian includes slower admission/final inventory.
Monitor sampling does not establish uninterrupted ownership, and training-phase
peak RSS was not measured. No production/default model is promoted.

`release-manifest.json` authenticates each released file. Plans retain original
local paths as provenance; portable reruns need rebinding paths and regenerated
review receipts. Unselected numeric snapshots remain local and are authenticated
in the selection reports. No rerun should reuse exposed final as fresh evidence.
