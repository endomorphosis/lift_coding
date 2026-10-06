# Next bounded TRAIN-wording experiment

Status: proposed specification; no sources, encoder outputs, optimizer fits or
future evaluation labels have been produced by this document. The source-head
diagnostic must finish first. This specification is an authored reconstruction
experiment, with no semantic qualification or checkpoint promotion.

## Question and fixed comparison

Test whether supervision on two additional explicit normative constructions
improves modality recognition and complete generated rules while preserving
original reconstruction. Compare the same 384D and 768D parents under an
additional TRAIN source-head loss of **0 versus 0.05**. Preserve the complete
original batches, curriculum, optimizer recipe, selection rule and output budget.
No hyperparameter sweep, new architecture, role vocabulary, conditioning method
or word-order sampler is bundled into this comparison.

The wording below is selected from ordinary explicit duty, authorization and
prohibition constructions, using the original TRAIN lexical inventory. It was
not selected by querying current v3 predictions, inspecting v3 target bodies or
matching a reported failing sentence. The prior exposed-development results
motivate examining generalization, but do not supply these TRAIN labels. The
wording is independently specified here in the engineering sense; no independent
human review or pristine semantic authorship is asserted.

## Exact new TRAIN strata

Use the complete authenticated `original-training-bank-used.json` in R4's saved
preparation results. It contains 180 original TRAIN source rows, representing
exactly 90 unique rules with two original sources per rule. Decode targets using
the exact pinned 32-token codec. Each target must have the unchanged seven fields
`modality`, `actor`, `action`, `object`, `conditions`, `exceptions` and `temporal`.
Never derive a target by parsing a new sentence or copying a model prediction.

Render each unique TRAIN rule once in each of the following two strata.

| Stratum | O | P | F |
| --- | --- | --- | --- |
| `explicit_actor_status_v1` | `Under this regulation, the {actor} is obliged to {action} the {object}.` | `Under this regulation, the {actor} is authorized to {action} the {object}.` | `Under this regulation, the {actor} is prohibited from {gerund} the {object}.` |
| `regulation_norm_operator_v1` | `This regulation places a duty on the {actor} to {action} the {object}.` | `This regulation grants the {actor} permission to {action} the {object}.` | `This regulation bans the {actor} from {gerund} the {object}.` |

The complete gerund map is `approve → approving`, `deliver → delivering`,
`examine → examining`, `preserve → preserving`, `publish → publishing`. The
actor remains the actor, the object remains the object, and the action remains
its original canonical action. `Regulation` introduces no additional actor,
condition, scope binding, citation or reference obligation in the authored
target. All target qualifier lists stay exactly as in the original TRAIN rule;
they are empty in this restricted bank. A compatibility check must reject a
future nonempty qualifier rather than dropping it to fit this renderer.

Each stratum has 90 clauses: 30 O, 30 P and 30 F. Combined: 180 unique proposed
clause strings, 60 per modality, 36 per actor, 36 per action, and 90 per object.
All 90 formal rules already belong to TRAIN. No new actor/action pair, symbol,
contextual meaning, qualifier or reviewed legal interpretation is created.

Fix the deterministic packing seed at **20261006**. Within each stratum, group
rules by exact `(actor, action, object)`; there must be 30 groups, each containing
O/P/F. Shuffle the sorted group list once using the seed plus stratum ordinal,
then shuffle each group's three modalities. Concatenate three rounds of that
same group order. Pack six paragraphs at each length 1, 2, 4 and 8, in that order.
Each stratum consumes exactly `6×(1+2+4+8)=90` clauses without replacement. This
yields 48 paragraphs and 180 clause occurrences. Every paragraph must contain
distinct content groups, so no paragraph introduces competing O/P/F statements
for the same content. Retain complete ordered targets and their 32V sequences.

For each clause retain its literal text, text SHA-256, template and modality
stratum, original rule digest, both original TRAIN source IDs/text hashes,
original target digest/token digest, and parent paragraph/slot. For each
paragraph retain ordered clause identities, complete target, target token IDs,
length, source hash and derivation list. Publish source-only rows separately from
formal references. Provenance is `authored_rendering_of_original_TRAIN_rules`;
`source_semantics_verified`, `admitted`, `qualified` and `roundtrip_ok` are false.

## Seal and exclude before native preparation

Seal the actual templates, gerund table, exact original bank and codec, seed,
packing policy, output inventory, task source files, data policies and all
exclusion inputs before any new encoder forward or checkpoint scoring. Seal the
future development package described below before fitting. Do not adapt the
wordings after observing source-head scores; any change requires a new recipe.

Recheck the ten R4 prior source inventories: original bank, raw TRAIN/validation/
test/canary, paragraph TRAIN/validation, and exposed r6/r8/v3. Also exclude R4's
new sources, the current 64-source composition packet, and any subsequently
published wording cohort captured before the seal. Check both paragraph and
individual clause strings, literal hashes and case-folded whitespace-normalized
forms. The source inventory is mandatory even where complete prior vectors are
unavailable. Recheck available prior native-vector inventories separately and
report incomplete vector coverage explicitly.

Reject the complete generation on a duplicate or overlap. Do not silently remove
a colliding sentence, replace it with an easier case, or select a surviving
subset. Future evaluation sources must be excluded from TRAIN in the same way.
Its label bodies are not inputs to TRAIN generation, vector preparation,
normalization, training or inference. No current v3 source rendering is used as
a TRAIN template, and no v3 target is used to construct a TRAIN label.

## Source prefix and clause context

The normative prefix is part of the actual model input. Keep `Under this
regulation,` and `This regulation` in each exact clause when encoding it. Do not
strip them, replace the source with the target or encode a predicted action
alone. Paragraph inputs preserve the literal blank-line separators and order.

Reuse `clause_source_context.build_source_contexts` and its source-only exact-text
cache join. Each descriptor binds full paragraph text, complete clauses, vector
digests, and original character/byte start/end offsets. The prefix belongs to
the corresponding segment and its offsets. Build the padded `(batch, 8, width)`
clause packet and mask from those descriptors using the frozen parent's original
TRAIN-only transform. The packet conveys source segmentation rather than
supplied legal assumptions; it is not a context-resolution model. No target,
reference prefix, parser-produced rule or reviewer answer enters this packet.

Teacher forcing in numerical TRAIN loss may use the declared complete TRAIN
targets under the existing API. At inference, recurrence receives only model
generated prior tokens and the exact source/context features. Save free-running
generation before reference scoring. Keep source-head and recurrent decoder
observations distinct so a source classification gain cannot conceal unchanged
or worse formula generation.

## Native cache and preparation contract

Reuse a vector only for an identical source and the exact producer/profile/input
recipe/dimension/dtype/pooling/normalization/token receipt, with verified stored
numerical content and file bindings. A name, width or equal-looking sentence is
insufficient. The R4 production/cache owners are the existing verified reference
for this new generation. New strings will ordinarily require new vectors.

Produce at most 216 unique sources per width: 48 paragraphs plus 180 clauses,
minus the 12 single-clause paragraph aliases. Use the existing verified local
384D GTE-small and 768D complete GTE producer with context **512**, batch **4**,
one CPU thread, `eval`/inference mode and the existing mean/CLS normalized
float32 profiles. No weights are downloaded. Refuse overlength inputs; no
truncation, padding-as-semantic-fallback or context-window increase is allowed.
Generation temperature remains zero. A bounded offline parent must enforce the
resource and wall limits; native forward interruption limitations remain visible.

The other agents' 64-source native384/native768 train/query bundles remain useful
for separate source-only reconstruction and inspection. Their semantics remain
pending with zero masks. Their historical native768 profile declares an 8192
ceiling with actual inputs at most 37 tokens; preserve that recorded identity.
Do not relabel it as the new 512-token generation. Any reuse in another consumer
requires an explicit compatibility contract with the existing profile and
actual token receipts. It supplies neither additional semantic TRAIN targets
nor a replacement for missing new-wording native vectors.

## Training loss, control and work accounting

Use the exact same authenticated R13 selected parent at each width as the last
paired wording studies, subject to successful current code/artifact compatibility
preflight. Record its complete file and tensor hashes. Use fresh AdamW/scheduler
state, seed 1729, base learning rate 0.0001, original non-action multiplier 10,
four original curriculum stages of 12/26/36/48 rows, 10 epochs per stage, and
batch size 8. Preserve the original source-value, recurrent token, cardinality,
action and boundary losses, plus the original 384D auxiliary where present.
Preserve their row identities, update order, denominators and targets exactly.

The two new arms differ only in the weight of the new full-vocabulary modality
term:

`L_total = L_original + λ × mean(CE(logits[:, slot0, modality, all32Tokens], gold_modality))`

Use `λ=0` and `λ=0.05`. Feed one clause from each of the six
`O/P/F × wording_stratum` cells per committed update. Order each 30-row stratum
by a SHA-256 key binding seed, stratum, source hash and source ID; cycle by
`committed_step mod 30`. Do not sample according to validation loss, confidence,
errors, predicted modality, a chosen easy role, or elapsed-time progress.

The zero-weight arm performs the identical diagnostic source-head forward with
gradients disabled and adds no zero graph to the original loss. It must match
the ordinary original-only continuation's tensors, ordinary update receipts,
RNG state and generated original panels exactly. A mismatch aborts the comparison
instead of being called a zero-control result. Positive gradients operate only
through the existing trainable source-head/decoder path; frozen source encoders,
normalization and projection guards stay live.

Each arm must complete 170 original optimizer updates, 1,220 original decoder
row presentations, 112,920 original valid target tokens and 12,800 original
source-value positions. Each arm observes 1,020 new clause presentations;
the positive arm supervises those presentations and the zero arm does not.
Aggregate new exposure is 340 per modality and 510 per wording stratum, with
each unique clause seen five or six times. Report this extra supervised work
and measured wall cost; the arms are not equal in backward FLOPs. Four fits
across the two widths therefore have 680 original updates if all complete.

Record actual float32 weighted loss, full32V logits, target IDs and per-clause
losses; observed/completed/committed/uncommitted forwards; separately attributable
positive supervision; and stop reasons. Cache source tensors once. Preserve
deadline checks before preparation, model copies, forwards, backward, optimizer
commit, state saves and validation. Use cooperative fit 180 seconds, width
driver 900 seconds and parent guard 1,000 seconds, with all partial completed
states/evidence retained if a limit is reached. Neither timeout nor low loss
grants completion, acceptance or promotion.

## Future untouched development seal

Before numerical fitting, a separate author/review-preparation owner must freeze
a new source-wording development package and its exposure policy. It must not
copy or adapt the two TRAIN templates, R4, r6/r8/v3 or the composition64
renderings. Reserve groups at source/rule-combination level and record every
overlap with original TRAIN and prior development. Preserve the original split
and do not turn a TRAIN rule into an independently held-out semantic case merely
by giving it a new string.

A minimal restricted-codec diagnostic proposal is two new renderings of the
30 unique original validation rules: **60 single-clause sources**, balanced O/P/F,
with actor/action groups disjoint from original TRAIN. Those counts and the
disjointness are mandatory preparation checks, not assumed admissions. Keep
complete seven-field targets derived from the original validation provenance;
label provenance remains authored development. If that inventory or a complete
target is incompatible, refuse rather than manufacturing an eligible subset.
Additional paragraph recombinations must be a separately declared panel with
explicit dependence on those single clauses.

The new source wording can remain untouched by the upcoming fits, but its
existing canonical target meanings and original validation material have prior
exposure. State that limitation. A later independent natural-source confirmation
cohort requires new sources and actual authenticated review/adjudication; this
small prospective wording package does not replace it.

Seal source IDs, full sources, group/split policy, counts, source and reference
file hashes, author/process provenance and target-compatibility outcomes before
the fit. Keep label bodies inaccessible to TRAIN/producer/inference code. Use
the unchanged original-development selection rule, with the new package held
for postfit measurement. Save source-only free-running outputs for every arm's
selected and last completed endpoint before loading its references. No tuning,
endpoint promotion or new wording redesign follows this panel's scores in the
same generation.

## Required measurements and semantic limits

Save all original nine source/control panels for both selected and last endpoints.
Record original development, new TRAIN full180, and future development confusion
tables and CE separately. For each retain complete generated JSON/formula text,
codec/structural status, exact whole-paragraph and ordered whole-rule agreement,
modality, actor, action and object correctness, count/order/boundary correctness,
all seven field agreements, abstentions and denominators. Empty qualifier lists
are explicit floor limitations rather than evidence of qualifier coverage.

Score new source-head outputs independently of recurrent generated formulas.
Report paired source/head/formula joins so, for example, correct modality logits
paired with an incorrect generated rule remain visible. Selection stays fixed;
postfit family/qualifier checks cannot be replaced with high cosine similarity,
low CE or a compiler/decompiler agreement count.

Report preparation/encoder wall time per unique source, cached numerical training
wall time per original row/update, source-head readout wall time per clause,
free-running inference wall time per span, and parent elapsed time/RSS/CPU.
Record sample counts, cache warmth and scope, worker count, bridge names,
prover/cache flags, model source hashes and native profile identities. This
experiment has bridge names `[]`, legal-IR prover flag false and metric disk
cache false; it is not a bridge-on legal-IR speed baseline. Warm verified source
vectors must be identified as such during decoder fitting/inference.

No new family projections are skipped to claim faster qualification. The 32V
authored grammar lacks richer roles, qualifiers, Boolean scope and contextual
meaning, and does not establish the eight-family legal floor. Richer composition
targets require a separately versioned compatible decoder plus authenticated
labels. Only an actual `lake build <Lib>` grants Lean admission; these restricted
head comparisons grant none. The US Constitution remains unformalized.

## Storage and admission before launch

The retained campaign cap is **145,000,000,000 bytes**. A saved prior census
reports 4,493,042,688 bytes of headroom before a later 139,650,728-byte archive;
that is historical evidence, not current launch admission. Recalculate named
root apparent bytes plus every full outstanding/retained claim using the existing
resource owner immediately before each phase. Do not release foreign leases,
delete retained findings, reset scheduler state or substitute filesystem free
space for campaign headroom.

Reserve separate bounded phases: preparation 100 MB, preflight 100 MB per width,
training 400 MB per width, and postfit measurement 100 MB. Budget a further
300 MB for an exact compressed publication archive if needed, avoiding extra
copies of authenticated parent states. At most two 1,536 MiB decoder workers
run in parallel under CPU/memory admission; native preparation should use one
worker and its independently checked existing encoder memory bound. Reserve no
GPU by default without a profile establishing a numerical bottleneck. Treat the
numbers as requested phase bounds, not occupied bytes or already granted leases.

Stop before any dependent model load when resource/source/data gates fail.
Release only the owned reservation after child exit and retain complete output
and partial/failure receipts. Sparse/control-plane publication and Hugging Face
uploads require their existing artifact/policy contracts and are separately
recorded; this local diagnostic specification neither uploads weights nor changes
shared database state. It preserves the protected 8D linguistic teacher,
restart12 checkpoint, archived states, HACC checkout and canonical tree pin.
