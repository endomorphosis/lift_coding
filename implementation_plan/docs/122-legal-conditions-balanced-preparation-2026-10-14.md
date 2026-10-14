# LegalIR class-balanced preparation and storage refusal — 2026-10-14

**Prepared and source-tested; not trained.** Storage clearance refused before
any reservation, numerical model execution or optimizer update. There are no
N12 weights, predictions, accuracy measurements or model-promotion decision.
The latest completed comparison remains the
[N11 conditions-presence experiment](120-legal-conditions-presence-training-2026-10-14.md).

The new opt-in `SpanConditionsBalancedAdapterDecoder` preserves the N11
architecture and starts from the exact trained N10 checkpoint
`b4ea8a502789f6dddba6e159eb7ecebb753d8344a833b0afb9109cfd6830bcd3`.
Its 40 parent tensors stay frozen. Two copied presence tensors store520 values;
only130 conditions values train, while390 inactive values, gradients and Adam
moments remain fixed. Existing decoder source and loaders are unchanged.

The sole experimental change is the loss. The retained training data contains
96 condition-absent and72 condition-present sources. The fixed weights are
168/(2×96)=7/8 and168/(2×72)=7/6. Compute unreduced conditions cross-entropy,
multiply each row by its class weight, then average over all12 batch rows.
Dividing by the sum of batch weights would change this objective and is refused.
Weighted and unweighted losses, actual float32 weights and per-row contributions
are traced separately. Fresh Adam, learning rate0.001, clip5, seed/order1729,
the original168 sources and32 updates/384 occurrences remain fixed.

Nine detached behavioral controls pass. Independent review checks the exact
unchanged factory, frozen-state, restoration and serialization functions and
all38 retained source owners. A source-only production bootstrap confirms
39 declared owners,15 loaded producers and7 mandatory source modules, with zero
model calls, checkpoint parses or numerical imports.

The preregistered evaluation compares the saved N10 and N11 outputs with the
candidate initial/trained states:40 panels,36 authored score sets and9 scopes.
It reports all seven IR fields, optional-presence TP/TN/FP/FN IDs and gold-split
ambiguity/abstention. Success requires retaining both N11 complete-IR gains,
recovering its four added condition false negatives, introducing no new
condition-head FP/FN or positive-ambiguity IDs relative to N10, and no complete
IR losses against either comparator. All632 protected heads and32 permissions
must pass. Technical completion and scientific success are separate; this fixed
recipe has no automatic retry, sweep, threshold fitting or default promotion.

The initial capacity snapshot passed native admission accounting by only
19,689,729 bytes, below the prior run's roughly64MB output. A second qualified
check includes200MB of future output headroom in addition to the200MB claim.
Its actual figures were:

| Accounting item | Bytes |
| --- | ---: |
| Apparent usage in the four counted roots | 103,311,717,553 |
| Existing full nonreleased reservations | 44,381,777,216 |
| Proposed run reservation | 200,000,000 |
| Conservative future output bound | 200,000,000 |
| Full-run charged bound | 148,093,494,769 |
| Shared cap | 145,000,000,000 |
| Additional headroom required | **3,093,494,769** |

Physical free space was148,894,699,520 bytes. This is a shared accounting-cap
refusal; ordinary native admission also fails at147,893,494,769 charged bytes.
All538 prior record bodies remain exact, no new claim or attempt was created,
and no storage cleanup or reservation reconciliation was performed. The cap
stays unchanged. Releasing space or
reconciling a reservation requires ownership and durability evidence; the next
run needs a new qualified capacity clearance and an immutable plan that binds it.
Recipes retain machine-specific ancestor paths; reuse requires reviewing those
physical source and artifact bindings as well as capacity.

The separate [checkpoint-components prototype](../../artifacts/legal-conditions-recall-20261014-01/checkpoint-components-design-v01.json)
passes synthetic controls and independent source review. It deduplicates repeated
numeric arrays and reconstructs the original canonical checkpoint bytes. Actual
trained-checkpoint round trips and size savings remain unqualified; it neither
changes this loss comparison nor supplies the missing shared-cap headroom.

All scored reference panels remain previously exposed engineering diagnostics.
Eight statutory examples stay unscored, latent conditioning stays disabled with
384D placeholders, and independent US Code fidelity, genuine8D/384D/768D decoding,
broader logic-family compliance and `lake build legal` remain unqualified.
Hosted CI passing is not claimed.

Prepared evidence: [training design](../../artifacts/legal-conditions-recall-20261014-01/training-design-v01.json),
[independent trainer review](../../artifacts/legal-conditions-recall-20261014-01/trainer-source-independent-review-v01.json),
[evaluation contract](../../artifacts/legal-conditions-recall-20261014-01/evaluation-contract-v01.json),
and [actual capacity refusal](../../artifacts/legal-conditions-recall-20261014-01/capacity-clearance-v01.json).

This preparation starts from source main `0897aa1d4252e175477addac5417028241de596a`
and root main `839ef8a9acb2e3ec98c1f94a20e8f8c7d491e481`. Their incoming80source
paths, six new nominated-allocation evidence/report paths and accelerator
`83ad1ca1a43ae53d3642efe8799d25a9df8cebf3` are preserved. The intake verifies
32 selected histories, five distinct registered recovery branches,15 historically
absent refs and canonical raw HEAD/index files. Further integration uses the
actual latest first parent and preserves every other gitlink.

The existing trained [N11 weights and full results](https://huggingface.co/Publicus/legal-ir-autoencoder/tree/702caba2da183f9d98a0ffd12f1240243167aab2/releases/20261014-conditions-presence-v1) remain the published checkpoint. No N12 checkpoint was generated.

The saved capacity snapshots show2,913,184,498 bytes of growth entirely in `/tmp/pytest-of-barberb`; the other three counted roots and all538 reservation bodies are unchanged. This observation supplies no authority to delete another agent's test data.

The fresh prepublication audit found root main advanced to
`9cb9b6dc482dfb8759bb11a4fbfe3cf0c7119ae2`. This contribution fast-forwards
its owned checkout to that parent, preserving all32 incoming paths, including
the other agent’s publication audit, accelerator
`e4b8c4bba2fc7d5b7484b9021cbb9a5bcfc5e7d4` and kit
`40c98c71b95be750509ffdb21e7e5494d91b4e79`. Only the datasets gitlink
will advance for this prepared source contribution.

GitHub source PR #1301 records billing-locked hosted jobs that did not start.
Queued or cancelled checks are not passing validation. Publication relies on
the recorded local source/synthetic controls and exact reviewed blobs.

Source [PR #1301](https://github.com/endomorphosis/ipfs_datasets_py/pull/1301)
merged as `a0f60d42f836571a0023515e92dfb0e5724f0d79`, with reviewed head
`890098506872d96848667c4a986324d30c86d28a` and actual first parent
`f0912bd8bfdc3971fcfd32c6ea63ae1bd6a9c195`. Merge verification preserves
all31,397 incoming tree entries and all61 reviewed additions exactly, including
the intervening native-span-cache and validation-argument changes. The root
datasets pointer advances to this actual merge. A fresh root observation still
finds `9cb9b6dc482dfb8759bb11a4fbfe3cf0c7119ae2`, with no further incoming
paths or gitlink changes.
