# Actual source-span training and the remaining modality gap

The new experimental single-rule occurrence decoder was trained with pointwise
and ordered byte encoders under the same bounded protocol. Ordered bytes improve
exact emitted positive proposals from **5/64 to 12/64** on this authored final.
Neither result qualifies legal autoformalization. Both selected custom JSON
checkpoints and the full experiment evidence are published at
[Publicus/legal-ir-autoencoder](https://huggingface.co/Publicus/legal-ir-autoencoder/tree/6a69f6cf05ffcaf911f7737086c706e06714b8d6/experiments/single-rule-scope-20261007/run-01).

This contribution builds on the October 7
[reconciliation](61-autoencoder-reconciliation-2026-10-07.md),
[normative runtime](62-normative-decoder-runtime-2026-10-07.md) and
[retained native-input runtime](63-retained-native-decoder-inputs-2026-10-07.md).
The isolated contribution was advanced to datasets `c4382ae53...` and workspace
`094c566adc...`, preserving those agents' newer code, reports and all other
submodule pins. The source-only span head is a separate experimental task;
existing 8D/384D/768D weights, native caches and default runtime selections are
preserved. This is not a latent-conditioned decoder result.

The [datasets implementation and contract](https://github.com/endomorphosis/ipfs_datasets_py/blob/8b1cff7c9a83e8ed04459abc962409c8d2bdb09a/docs/implementation/legal_scope_span_decoder_pilot_20261007.md) add generic Unicode
source tokens, full UTF8 byte encoding, a token BiGRU, support/class/presence
heads and five independent start/end pointers. The ordered arm's two Conv3
layers replace Conv1. All common tensors match at initialization; extra neighbor
weights start at zero. Initial first-batch logits and16 inference outputs match.
Parameter counts are 21,562 and 22,330, so capacity differs by 768 weights.

| Fresh final,64 supported +64 unsupported in64 paired groups | Pointwise | Ordered |
| --- | ---: | ---: |
| Selected update, from 0/120/240 | 120 | 240 |
| Actual completed updates | 240 | 240 |
| Training row presentations | 3,840 | 3,840 |
| Exact emitted positive proposal | 5/64 | 12/64 |
| Positive learned refusal | 20/64 | 18/64 |
| Positive structural block | 9/64 | 5/64 |
| Learned unsupported-profile refusal | 57/64 | 59/64 |
| Unsupported proposal emitted | 5/64 | 4/64 |
| Exact positive or learned negative refusal | 62/128 | 71/128 |
| Raw five spans exact, including blocked/refused positives | 35/64 | 47/64 |
| Raw modality class correct | 22/64 | 25/64 |
| Exact positives with nonempty conditions | 1/32 | 4/32 |

TRAIN has 512 supported and512 unsupported rows, selection/final each 64+64,
with all source strings, facet lexemes and parent groups split-disjoint. Eight
word orders, O/P/F, nullable object/condition, Unicode and repeated occurrences
are authored construction tests. Unsupported rows cover modal deletion,
token-local modal anagrams, extra exceptions and second rules; they carry no
structural target and do not assert legal falsity. The matched run uses seed 24602,
AdamW learning rate 0.003, zero decay, batch 16 (8+8), clip 5 and support gate 0.5.
Across both arms, actual fitting is 480 updates and 7,680 presentations. No other
unfinished training pipeline was resumed.

Both selections were durably saved before the numerical runner parsed final
references, and both final prediction panels were saved before final scoring.
Corpus authors had built and mechanically reviewed those labels before fitting;
this barrier does not make the labels independently reviewed statutory gold.
The final is now exposed. Old grouped 85.2% measurements have different tasks and
cohorts and are not baselines for this table.

The strongest measured bottleneck is modality class: ordered trigger spans are
64/64 exact, but class is 25/64 and the model predicts no P. Thirty of 47 span-exact
positives have the wrong class. Five of 17 span-and-class-exact positives are
refused or structurally blocked. Class loss stays near log(3) in the last 20 TRAIN
updates while span losses are small; the recipe has not meaningfully learned
that objective. This motivates a local readout test without establishing a
causal explanation. Ordered actor/action/object/condition spans are 64/64,
50/64,61/64,61/64; nonempty object/condition spans are each 29/32, and 32 correct
nulls contribute to the larger totals.

Every proposal validates through the existing scope owner with all five admission
masks zero. Condition attachment is a supplied caller premise, not a learned
decision; the condition remains opaque. Context is required but unavailable,
coverage is unassessed and formal output is null. This pilot neither lowers to
any logic family nor runs `lake build legal`. Exceptions, temporal qualifiers,
multiple rules and natural US Code fidelity remain open.

Validation passed 231 distinct decoder/owner cases, including 28 new head cases.
Independent posthoc review rescored every selection and final panel and checked
all six snapshots, source pins, progress, selection ties and final barriers.
A separate two-thread CPU process reproduced 256 complete final outputs exactly,
with unchanged model/full Adam/mode/RNG and no optimizer steps. One-thread
pointwise replay differed only in 22 support-probability floats, at most 1.19e-7;
it stopped before testing the ordered arm. Exact replay uses the original thread
setting. These are engineering checks, not semantic or legal accuracy checks.

The first pipe-gated launch failed before model execution when disk inventory
delayed the initial lease observation. The reviewed fix starts monitoring before
inventory and preserves the same limits. Successful attempt 02 exited 0, reaped
its child and released its own lease and reservation. The failed attempt's own
disk claim and receipts remain retained. The resource review records 28 active
samples and a maximum 1.016s observed gap, but does not claim continuous coverage.
Training-phase peak RSS is unmeasured. The numerical runner took 12.58s; admission
and final inventory are additional work, not model throughput.

The [retained evidence](../../artifacts/legal-scope-span-training-20261007/README.md)
includes both successful and failed custody evidence, tests, source/result
reviews, corpus, schedule, losses, every evaluation panel, selected checkpoint
hashes and Hub byte readback. Numerical tensors live on Hugging Face. Source
contribution: [datasets PR](https://github.com/endomorphosis/ipfs_datasets_py/pull/1275). Hosted CI status is recorded in the
contribution receipt; local passing tests do not imply hosted CI passed.

The next bounded experiment should compare a global modality readout with a
readout of model-predicted trigger states or learned trigger attention. Freeze
the existing source backbone for the first diagnostic, use a zero-initialized
residual readout to preserve identical initial outputs, disclose parameter
budgets and keep support errors separate. No oracle spans, target lookup,
modality keyword mapping or change to the exposed final is allowed. Register a
new protocol and fresh parent groups before fitting; per-class confusion,
nonempty qualifier exactness and whole emitted proposals are necessary endpoints.
After source interpretation is reviewed, test the native family parser/lowering
and Lean build on those same meaning-bearing examples. Compiler acceptance alone
cannot supply the missing legal review. Broader-family work and latent transfer
remain separate measured tasks.
