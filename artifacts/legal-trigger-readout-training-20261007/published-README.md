# Frozen source-span donor: global versus predicted-trigger modality readout

An actual matched CPU experiment trained two residual O/P/F adapters on an
unchanged source-span donor. Predicted-trigger evidence improved class and whole
proposal exactness on this fresh authored cohort. These are experimental
occurrence proposals, with no reviewed statutory fidelity or formal output.

| Fresh final endpoint | Unchanged donor | Global adapter | Predicted-trigger adapter |
| --- | ---: | ---: | ---: |
| Raw O/P/F class correct, all supported rows | 19/64 | 29/64 | 47/64 |
| Exact emitted positive proposal | 11/64 | 17/64 | 30/64 |
| Exact proposal with nonempty condition | 4/32 | 7/32 | 12/32 |
| Supported learned refusals | 19/64 | 19/64 | 19/64 |
| Supported structural blocks | 2/64 | 2/64 | 2/64 |
| Supported proposals emitted | 43/64 | 43/64 | 43/64 |
| Learned unsupported-profile refusals | 53/64 | 53/64 | 53/64 |
| Unsupported proposals emitted | 6/64 | 6/64 | 6/64 |
| Raw five occurrence spans exact | 49/64 | 49/64 | 49/64 |
| Mean supported class cross entropy | 1.09372 | 1.08300 | 0.65386 |
| Selected adapter update | — | 120 | 240 |

Both adapters actually completed 240 AdamW updates with seed 24603, learning
rate 0.003, zero weight decay and gradient clip 5. Each received 3,840 input records
in 240 batches of 16 (8 positive + 8 negative). Only the 1,920 positive presentations
per arm were encoded for class fitting; the 1,920 negative records were ignored
by the adapter and had no class targets. Across both arms this is 480 actual
updates, 7,680 input records and 3,840 encoded positive presentations, rather than
new support/refusal training. TRAIN diagnostic panels are extra source-only
forward passes and do not contribute optimizer updates.

The donor has 22,330 frozen parameters. Both adapters have the same 4,355 trainable
parameters and 26,685 total parameters. Initial adapter tensors are identical,
with seeded hidden weights and zero final class projection. Actual initial
donor class logits and complete core outputs match on 16 training inputs. Each
uses the same 64-dimensional encoded token states before the donor's global
projection. The global arm averages real tokens; the trigger arm normalizes
`P(S<=t)*P(E>=t)` over real tokens from the donor's predicted modality endpoints.
Those are independent endpoint marginals, not a learned joint interval model.
No target span, keyword lookup, nearest-anchor recovery or repair enters inference.

The byte encoder, BiGRU, original class logits, support gate, nullable-presence
and all five pointer heads remain frozen. Only the residual adapter changes.
The full original donor checkpoint and its old Adam state are preserved as
exact UTF8 JSON bytes inside each new checkpoint. Both adapter optimizers start
fresh; no donor-moment continuation is claimed. All-negative update calls invoke
neither the encoder nor Adam and leave checkpoint progress unchanged.

The donor is the previous ordered step 240 source-span checkpoint, exact file
SHA256 `9809ec3fd092536f8c4effb74d8a401dc5db9ff9a031952a1e3f92f9c7292c6e`.
The fresh corpus has 512 supported  + 512 unsupported TRAIN rows and 64+64 each in
selection/final, with 512/64/64 paired parent groups. All 1,280 sources, declared
facet values and role/action/object/condition identities are disjoint from the
earlier pilot and across new splits. Eight templates and the operator aliases
are deliberately shared. This is new wording/identity coverage within the same
authored grammar, not new syntax or US Code semantic gold. The old 12/64 result
is a different cohort; the comparable unchanged-donor baseline here is 11/64.

Class, template, nullable cells, Unicode, repeated occurrences and negative
category ledgers are retained. Unsupported means outside this single-rule
profile, not legally false. Unsupported cases include modal deletion, token-local
modal anagrams, extra exceptions and second rules. Caller attachment is inherited
by each paired derivative, never learned. At inference it remains an explicit
`rule|statement` premise, copied only if a condition is predicted present.

Selection candidates are 0/120/240, scored first by raw class exactness on all 64
supported selection examples, then exact emitted proposals, then earlier step.
Both choices were durably saved before the numerical runner parsed final
references. All three final panels (both adapters and donor) were durably saved
before final scoring. Corpus authors had constructed/reviewed the authored
labels before fitting; this is not an authors-blind legal gold test. This final
is now exposed and must be retention-only in subsequent fitting/selection.

The predicted-trigger confusion matrix is O→[13,2,7], P→[2,17,2], F→[2,2,17]
with columns O/P/F and gold totals 22/21/21. The donor emitted no P class on
supported final rows; the new readout correctly classifies 17/21 permissions.
On all supported rows, actor/action/object/condition spans are 61/64, 54/64,
61/64, 63/64. Nonempty object and condition spans are 29/32 and 31/32, while 32
correct nulls contribute to each full denominator. These pointer counts are
identical in all three lanes.

Only 38/64 supported examples have exact raw spans and an emitted proposal under
the frozen gate. Class errors among those 38 are 27/21/8 for donor/global/trigger,
giving 11/17/30 whole exact proposals. The other 26 examples cannot be fixed by
this class-only intervention. The gerund-agent template has 0/8 exact raw span
sets, six refusals and two incorrect-span emissions, despite 5/8 correct trigger
classes. Next work needs support/span generalization and the remaining O/P/F
errors, tested with a new protocol and fresh final; this cohort must not be tuned.

Every proposal validates through the existing canonical scope owner with all
five admission masks zero. Source/context semantics and coverage remain
unresolved, conditions remain opaque, and `formal_output` is null. No formula
lowering, `lake build legal` run, proof admission or default runtime promotion
occurred. Existing 8D/384D/768D autoencoder weights and other agent runtimes are
preserved. This source-derived readout does not consume those latent vectors.

The selected finite JSON containers are
`checkpoints/global/checkpoint.json` (step 120) and
`checkpoints/predicted_trigger/checkpoint.json` (step 240). They include exact donor
bytes, adapter values, full fresh Adam state, actual progress and closed
producer/feature recipes. These are custom research checkpoints, not
Transformers AutoModel assets. The numerical closure is preserved under
`source/`; use the matching datasets contribution and Torch 2.13.0+cu130 on CPU.
Restore rejects changed sources, recipes, state inventories or nonfinite values.

```python
import hashlib, json
from pathlib import Path
from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_trigger_readout as head
checkpoint = json.loads(Path("checkpoints/predicted_trigger/checkpoint.json").read_text())
model, optimizer, steps = head.restore_trigger_readout_checkpoint(checkpoint)
source = "The clerk shall submit notice if notice arrives."
result = head.predict_trigger_readout(model, source, "rule",
    expected_source_sha256=hashlib.sha256(source.encode()).hexdigest())
```

This example is an unscored opt-in call, not a statutory translation. The
constructor takes exact donor bytes and externally expected SHA; the explicit
training API takes supported O/P/F labels, never span targets.

Validation passed 93 distinct decoder/donor/proposal cases and 23 pure guardian
cases. Separate-process two-thread replay reproduced all 256 saved adapter final
outputs exactly with unchanged donor/adapter/full Adam/mode/RNG and no optimizer
steps. Independent result, corpus, model, runner and resource reviews are retained.
The guardian child completed and was reaped; its own lease/reservation released.
Fourteen model-phase RSS samples peaked at 758,779,904 bytes (about 723.6 MiB), with
maximum observed gap 1.033s. This is a sampled own-group sum, not an absolute peak,
kernel memory quota or continuous-coverage proof. The numerical runner took 12.27s;
admission/final inventory and import timing are separate from isolated fit time.

`release-manifest.json` binds every released file. Plans keep original absolute
paths as provenance; reruns require path rebinding and regenerated review
receipts. Unselected numeric snapshots are retained locally with exact hashes
in selection reports. New artifacts are appended under this experiment prefix;
existing Hub weights and aliases are not replaced.
