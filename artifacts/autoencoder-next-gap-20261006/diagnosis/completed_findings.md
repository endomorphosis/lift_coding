# Completed source/recurrent diagnostic

The current larger-width decoder gap is principally incorrect source-head
modality evidence on unfamiliar normative wording. The additive recurrent path
does not cause the 384D zero-control errors or either 768D modality error. The
positive 384D arm adds one recurrent override and worsens the source head at two
other obligation sites. Increasing the already saturated R4 auxiliary weight
would therefore miss the main issue.

| Saved selected endpoint | Source modalities correct | Combined modalities correct | Correct source overturned | Exact paragraphs, unchanged by observation |
| --- | ---: | ---: | ---: | ---: |
| 384D zero | 139/180 | 139/180 | 0 | 20/48 |
| 384D 0.05 auxiliary | 137/180 | 136/180 | 1 | 19/48 |
| 768D zero | 178/180 | 178/180 | 0 | 46/48 |
| 768D 0.05 auxiliary | 178/180 | 178/180 | 0 | 46/48 |

All four observed greedy outputs match their archived token IDs, termination
status and EOS exactly. Each panel has 720 scored scalar sites, 180 each for
actor/action/modality/object, with no unavailable or unvisited sites. Actor and
object source/combined outputs are 180/180 throughout. At 384D both arms share
one source/combined action error; at 768D actions are 180/180.

The source-plus-recurrent observation has not improved these outputs: it explains
unchanged inference. The raw recurrent readout is an additive component trained
with the source residual; at many scalar sites its maximum is a grammar token.
Its argmax accuracy is not the accuracy of an independent decoder or supported
logic family. The readout includes paragraph, clause and generated-history
effects, which this observation does not causally separate.

## Four changed 384D examples

The full paragraph targets and zero/positive formulas are retained in
`matched-formula-transitions.json`; these are all four changed paragraphs, rather
than a selected subset. The table shows their changed clause and its full32V
target-versus-best-other margins.

| Authored obligation clause | Zero source/combined margins | Positive source/combined margins | Result |
| --- | --- | --- | --- |
| The secretary is obligated to publish the notice. | -0.184827 / -0.312353 | -0.156828 / -0.206985 | Source and output change from wrong P to wrong F |
| The obligation is for the trustee to deliver the archive. | +0.779618 / +0.633410 | +0.120811 / -0.026272 | Source remains correct O; recurrent addition overturns it to P |
| Publishing the archive is an obligation of the secretary. | +0.148925 / +0.014553 | -0.338195 / -0.473123 | Source and output change from correct O to P |
| Publishing the notice is an obligation of the notary. | +0.262663 / +0.151960 | -0.614094 / -0.725330 | Source and output change from correct O to P |

The single override occurs in a previously exact paragraph, causing the 20→19
exact regression. The other two newly wrong obligation sites occur in paragraphs
that already contain another error. Thus clause accuracy degrades by three while
paragraph exactness degrades by one. No source-wrong scalar site is corrected by
recurrence in these four models.

At 768D both remaining errors are authored permissions beginning “The secretary
is authorized to …”: deliver the notice and publish the notice. Both source heads
prefer O. In the zero arm their source margins are -5.026630 and -2.933405;
the combined margins are -4.871593 and -2.767157. Recurrence slightly reduces the
error margins but cannot overcome the incorrect source evidence. One actor/action
pair was seen in TRAIN and the other was unseen, so this is not explained solely
by unseen pair composition. Both formulas remain wrong in the positive arm.

## Next training work

Prepare broader TRAIN-only normative wording with complete target derivation,
explicit clause/paragraph links, balanced modalities, original-vector checks and
authenticated verified local embeddings. Separate an untouched evaluation cohort
before fitting. Keep the current v3 set labeled exposed development and never
move its error rows into the training inventory. Measure the new source bank's
modality confusion and margins before increasing its loss coefficient.

Preserve the original ordinary decoder/count/action/boundary work and exact
execution-matched zero control. A separate TRAIN-only consistency term can be
considered for genuinely source-correct eroded margins, using the existing strict
replay and recurrent gradient whitelist, but only after checking its active TRAIN
signal. That addresses the one observed override, whereas diverse source-head
supervision addresses the predominant error pattern. Keep the 8D linguistic
teacher, other input widths, normalizer, source context limit and success gates
protected.

## Validation and timing scope

The independent standard-library audit performed 66,467 checks. It reconstructed
all 92,160 additive coordinates using binary float32 pack/unpack, independently
computed every component's full32V argmax, margin and double log-sum-exp CE, and
verified per-field counts, authored source-slot labels, model/source/codec hashes,
complete missing-site accounting and archived greedy equality. Maximum numerical
metric difference was 0.0. It imported neither Torch nor the package and executed
no model. The new driver passed 73 pure tests; prior observer tests were not rerun.

Four 48-row panels use one CPU worker, batch size 8, temperature 0 and both output
and context limits 512. Generation plus observation takes about 0.527–0.530
seconds per 384D panel and 0.670–0.678 seconds per 768D panel. Posthoc scoring is
separate. The numerical driver takes 25.252 seconds including state restoration,
preparation and scoring; its guardian takes 67.006 seconds including admission
and accounting. Bridge names are `[]`, provers are disabled and the metric disk
cache is disabled; authenticated source vectors are warm.
No encoder, cold compiler or bridge-on evaluation is measured.

The child and guardian exit 0, the reservation is released, no live owned process
group remains and retained diagnostic output is 9,690,794 bytes under a 100 MB
reservation. The 145 GB campaign cap remains unchanged. The earlier seal was
superseded before launch when final durability checks were added; it is preserved
separately, and no resource claim was created for it.

This is a closed authored Legal reconstruction diagnosis. Temporal, condition
and exception lists in these fixtures are empty. No compiler repair, extra logic
family coverage, fresh statutory fidelity, convergence, checkpoint promotion or
Lean admission follows. The diagnostic runs no `lake build <Lib>`; the Constitution
remains unformalized and no span becomes `roundtrip_ok`.
