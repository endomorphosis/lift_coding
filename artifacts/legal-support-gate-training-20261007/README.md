# Support-gate training archive: all trained candidates rejected

Both matched support gates completed 240 optimizer calls, but every trained
update-120 and update-240 checkpoint failed the predeclared selection floors.
Both selected their exact cold step-zero fallback. Selected outputs match the
frozen parent: **38/64 exact positives and 13/64 unsupported emissions** on the
new authored final. This completed study demonstrates no selected prediction or
qualified-accuracy improvement and makes no default promotion.

The [root report 68](../../implementation_plan/docs/68-support-gate-refusal-training-2026-10-07.md)
explains the contribution. The [full release](https://huggingface.co/Publicus/legal-ir-autoencoder/tree/ae5a6b555f66f9ea7cdf3f46a03c689d07485bb5/experiments/support-gate-20261007/run-01)
contains all six original 0/120/240 research states and two selected-zero aliases.
The link uses the verified immutable publication revision.
`published-README.md` preserves the release README exactly, including its original
source-link snapshot. It is separate from this archive's explanatory README and
any later merged source guide.
Prepublication reviews and build receipts retain their historical pending-link
strings. This README, the current retention manifest and final source guide
use the verified immutable release and contribution bindings.

Both arms train 3,169 parameters over the same 97-wide frozen bundle: contextual
states plus the original ordered Conv3 byte mean/max/log-length features. They
start with identical seeded tensors and zero final projections. Global mean
versus predicted-modality coverage is the only pooling difference. The entire
selected support/action MLP parent, class readout, support/action heads, all
presence and five endpoint heads, modes and historical checkpoint/Adam bytes
remain frozen. Only a fresh support gate Adam fits BCE over all 16 sources per
call: eight supported and eight unsupported. Across both arms this is 480 calls
and 7,680 source presentations; no old Adam, action, class or encoder is updated.
The original encoder already preserves byte order.

| Saved TRAIN at actual update 240 | Parent | Global | Local |
| --- | ---: | ---: | ---: |
| Whole exact /512 | 322 | 310 | 317 |
| Unsupported emitted /512 | 112 | 108 | 99 |
| Clipped support-probability BCE | .426070 | .405175 | .349219 |
| Modal-misspelling emitted /128 | 109 | 105 | 97 |

Local improves TRAIN refusal counts and BCE while whole exactness is lower.
On selection, global loses two whole successes; local at 120 adds an unsupported
emission, and local at 240 falls below the positive emission/refusal floors.
Equal totals can hide replaced successes or new unsupported emissions, so paired
case sets are retained. These diagnostics do not change the frozen selector.
Rejected trained states were not evaluated on final or retention. Only cold
selected states were evaluated there; all selected paired gains and losses are
zero, and all 384 earlier parent dictionaries match their archived panels.

Validation retains 170 successful test executions with a source-qualified
collection ledger and 23 separate pure selector fixtures. The original XML
had six case-name collisions; collection metadata binds all executed cases to
unchanged source files without rerunning tests to repair provenance. Separate
CPU2 read-only replay of downloaded selected aliases matches all 1,024 full outputs across two arms and
four cohorts, with complete model/parent state, full Adam, modes, flags and RNG
unchanged, no references read and zero extra updates. The unchanged guardian
retains 23 historical pure tests; they were not rerun for this study. Its owned
child exited zero, was reaped and only its own lease/claim was released. The prior
failed 200 MB claim remains retained. Thirty-five model-phase RSS samples peak
at 817,844,224 bytes, about 780 MiB; these are sampled process-group sums, not an
absolute peak, continuous coverage or a kernel quota.

`retention-manifest.json` maps all **109 released files** to exact local bytes or
immutable Hub resolve URLs, with byte counts and SHA256. It preserves
92 release files locally. The eight checkpoint containers, three complete TRAIN
panels and six candidate selection panels are 17 Hub-only files; no numerical
weights are copied into Git. Every local archive file except the retention
manifest itself is also bound. All eight checkpoint containers download byte-exact. All 109 published file
identities were verified while preserving all 2,747 prior file identities.
Later independent contribution, incoming-branch and publication receipts are
kept separately under `evidence/`; the local manifest binds those additions.

These are authored engineering occurrences rather than independently reviewed
statutes. All emitted admission masks are zero and formal output is null. Caller
attachment remains an explicit premise, conditions are opaque, and support
means the declared single-rule profile rather than legal truth. This source-text
model consumes no legal latent vectors and supplies no reviewed-law semantics,
logic-family lowering, native/teacher/runtime qualification or Lake admission.
The separately integrated native 384D checkpoint availability has its own task
and schema lineage. A future trial needs new excluded final material and a
predeclared TRAIN-only hypothesis. Historical absolute paths and old scorer/
renderer bindings are provenance; portable replay needs deliberate validated
path rebinding while preserving weights, producers and complete expected outputs.
