# Existing source data and the next fidelity slice

This is a saved-data audit, not a training or semantic review run. It executes
no canonical package imports, encoders, autoencoders, decoders, solvers or Lake.
The [machine report](readiness-audit.json) records **3,839 checks**, exact file
bindings and the limits of the rechecked provenance. The
[reproduction script](audit_saved_training_data.py) reads JSON and hashes bytes;
its output filenames require a fresh destination for another run.

## What can be reused now

| Data owner | Exact source/formal material | Existing native features | Permitted scope |
| --- | --- | --- | --- |
| R4 TRAIN augmentation | 48 paragraphs; 180 unique clauses; 90 original TRAIN rules rendered in two styles | Complete 384D and 768D paragraph, clause and ordered segment caches; 216 unique sources per width | Existing authored diagnostic fitting and source-head inspection under an explicitly frozen new recipe |
| Other agents' 64-source compositional cohort | 64 blank reviewer envelopes; 16 source groups; source-only TRAIN32/DEV32 partition | Complete native384/native768 train/query bundles and exact producer artifacts | Source-only representation fitting or inference diagnostics; semantic target fitting remains pending |
| Existing typed-anchor teacher cohort | 16 source-parser weak proposals from four TRAIN groups | Typed source-GRU profile; it does not consume the native semantic caches | Separately declared weak teacher diagnostics with `weak_decoder_fit=1`; other four masks remain zero |

The R4 results are under
`external/ipfs_datasets/workspace/test-logs/decoder-training-paraphrases-r4-20261004/preparation-r1/results`:
`training-references.json` joins by exact paragraph ID to
`dimension-inputs-384.json` and `dimension-inputs-768.json`. Each dimension file
has 48 source-only rows, 180 cached clauses, and complete ordered source
segments. Production records retain actual native numerical outputs and token
receipts. This audit compared every cached vector to its saved production output,
every source segment to the corresponding paragraph clause, and every formal
rule to its two original TRAIN derivations. It checked all ten existing literal
and normalized-source exclusions, including exposed v3. Literal separation
does not establish semantic independence or a fresh holdout.

R4 has 60 O, 60 P and 60 F clauses, with five actor names, five actions and two
objects. Its targets always contain an actor, action and object; all conditions,
exceptions and temporal lists are empty. It supplies new wording of existing
rules, not new formal meanings, qualifier scope, contextual resolution, missing
roles or general logic-family coverage. The latest modality auxiliary experiment
already used this complete bank. Parent confidence on it cannot establish
out-of-distribution fidelity.

The 64-source native cache lives under
`artifacts/autoformalization-publication-20261004/expansion/encoding-01/worker`:
`native384_raw_train_bundle.json`, `native384_raw_query_bundle.json`,
`native768_raw_train_bundle.json`, and `native768_raw_query_bundle.json`.
Its [pair map](cache-pair-map.json) binds each exact source/input/reviewer ID and
source-reconstruction split while leaving every formal target null. All source
envelopes agree with the original pending review packet; all 320 per-item
semantic mask values remain zero. The source reconstruction partition must not
be mistaken for semantic label admission.

These caches preserve their own producer profiles. In particular, the older
composition native768 profile declares an 8192-token historical ceiling; its
actual inputs contain at most 37 tokens. R4 production explicitly used 512.
Do not relabel one profile as the other or change the encoder context window.
A bounded cache consumer must bind the original profile and token observations
through an explicit compatibility contract. This audit rehashed named frozen R4
producer sources and composition producer artifacts, but did not rehash the
complete binary dependency closure or every installed model asset.

## Why richer semantic training is still pending

The 64-source packet has zero submitted reviews, authenticated interpretations,
adjudications or admitted formal targets. The source-only expansion encoders and
successful autoencoder fitting changed none of those facts. Recording and
declared-evidence intake have no operation that promotes caller declarations to
semantic training labels. The older 34-item cohort also remains unreviewed.

The current R4/selected 384D/768D restricted decoder uses a 32-token lexical
codec. Of the composition packet's four actor names, only `registrar` is present;
`clerk`, `custodian` and `officer` are absent. Its actions `notify`, `retain`,
`audit` and `authorize`, and its objects `applicant`, `filing` and `application`,
are absent. No nonempty qualifier value is expressible. Flat condition/exception
lists also lack explicit conjunction, disjunction and attachment operators.
An embedding alone cannot remove those output-contract limits. Pending targets
must not be shortened, renamed or stripped of qualifiers to fit the old head.

The typed-anchor lineage offers source-character anchors and a different
TRAIN-fitted symbol catalog; supplied or required unresolved context still
abstains. It is a separate source-token model, not an interchangeable decoder for
the native384/native768 vectors. Its 16 weak examples establish neither broad
source fidelity nor independent semantic training data.

## Smallest useful next preparation

First inspect the four selected source-head panels under the existing caches and
saved labels. The present hypothesis is a wording shift in modality recognition;
it remains a hypothesis until those numerical diagnostics locate the error.
This data audit does not execute that experiment or choose a new checkpoint.

If that diagnosis supports additional wording supervision, prepare **one new
authored TRAIN generation** directly from the same authenticated original180
bank. Keep all 90 rule identities, exact actor/action/object bindings and O/P/F
balance. Use two preregistered rendering families with explicit agents and
polarity, and preserve every original training batch. For example, a closed
family can render `Under this rule, the {actor} is required/permitted/forbidden
to {action} the {object}.` A second family should change order or syntactic
attachment while retaining an explicit actor and the same complete rule.
These are proposed diagnostic fixtures, not independently reviewed meanings.

Before generating vectors, freeze the actual templates, rules, seed, packing,
ordered derivations, source-only producer inputs, exclusion inventories and
completed-update budget. Reject every exact/normalized collision against R4,
original TRAIN/DEV/test/canary, exposed r6/r8/v3, and the composition cohort.
Derive targets solely from original TRAIN; read no v3 target body for fitting.
Keep the exposed sets in their existing development role. Native preparation
can reuse already identical sources only under their exact profile; genuinely
new strings require newly recorded local forwards with no downloads or larger
context. Train the complete source-value output under a fixed small arm only
after diagnosis, comparing ordinary CE and exact generated rules against the
same parent and original controls. Counts and every target facet belong in the
manifest; relative CE gains alone remain insufficient for promotion.

In parallel, obtain actual candidate-blind independent annotations of the
pending richer sources through the existing recorder and process-owned
verification/adjudication workflow. A new profile must express missing roles,
qualifier presence and attachment, scope operators, repeated mentions, context,
and multiple rules before these admitted pairs enter fitting. Preserve
ambiguous/unsupported decisions instead of supplying convenient target values.
An actionable preparation artifact is a compatibility report plus blank review
handoff, not a manufactured completed review.

Freeze a **separate future evaluation cohort before the next semantic fit**.
Reserve source groups, wording families, target combinations, label provenance,
exposure history and reviewer process; record the untouched material's manifest
without sending labels to training. The existing 64/34 cohorts and v3 are exposed
development evidence and cannot serve as that confirmation set. A source-only
TRAIN32/DEV32 grouping is not an equivalence label or automatic negative mask.

Every new semantic claim still requires applicable logic-family validation and
actual `lake build <Lib>` for Lean admission. The restricted authored decoder
does not establish the legal eight-family floor, statutory fidelity or
Constitution formalization. This preparation changes no qualification gate,
selected checkpoint, protected teacher, model weights or storage allocation.
