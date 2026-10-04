# Richer source and context review recording

The richer review submission workflow is implemented and its readiness run
preserves all 34 existing items as pending. It accepts completed or partial
reviewer declarations, binds their exact source and context, and records
agreement or disagreement. No human answers, reviewer identities,
attestations, independently established semantic labels, or proofs were
created during this stage.

## Executed readiness result

The final [private machine report](richer-review-admission-02/report_private.json)
records zero submitted payloads, zero completed annotations and zero
authenticated independent reviews. All 34 source/context envelopes match the
original blank packet: 32 source-only items and two explicit-assumption items.
The two contextual interpretations retain their distinct input identities.
The [private receipt](richer-review-admission-02/receipt_private.json) replays
exactly against the pinned blank bundle and empty submission list.

No authored reference was used to score annotations or resolve a disagreement.
The original private bundle contains authored references, which the existing
preparation validator checks for integrity. That check does not adjudicate
their meaning. The new recording receipt contains no authored targets.

## Review contract

Reviewers complete a copy of the existing
[reviewer packet](structure-01/reviewer_items.json), preserving instructions,
source text, explicit context, hashes and item identities. A nonempty subset
or reordered items is allowed. Distribute only that packet, its
[reviewer manifest](structure-01/reviewer_manifest.json), and the new
[submission guide](richer-review-admission-02/submission_guide.json).
The full bundle and private receipts are organizer material.

Annotations distinguish a normative interpretation, an explicit absence of
normative rules, ambiguity, and unsupported meaning. Null fields remain
unanswered. An empty rule list records a reviewed absence only with the
corresponding interpretation and rationale. Whole rule facets can remain
pending; explicit empty qualifier lists and an empty object retain their
declared meanings.

Mechanical agreement compares the interpretation, flags, complete ordered
rules and exact scope description. It preserves qualifier attachment,
multiplicity and order. Notes, names and timestamps do not determine the
meaning signature. Different wording can therefore require human
reconciliation. Matching declarations remain unauthenticated; identity,
independence and adjudication need evidence outside this recording workflow.

## Implementation and verification

The [runbook](../../external/ipfs_datasets/docs/autoencoders/alignment_richer_review_admission.md)
documents the API, command line, annotation contract and review boundary.
The CLI admits SHA-pinned, bounded ordinary JSON, rejecting duplicate keys,
nonfinite values, altered input envelopes, duplicate review declarations,
nonregular files and symlink paths. It checks source and input bindings again
before writing fresh evidence. Output directories use mode 0700 and files
mode 0600; permissions and audience labels do not authenticate reviewers.

The combined preparation, admission and command-line checks passed **180
tests in 4.58 seconds**. Ruff passed on all five new Python files. Synthetic
annotations were used only in isolated tests and temporary fixtures; none
were submitted to the campaign's readiness run. The 38 source files bound by
the previous embedding experiment remain unchanged, as does the protected
research protocol.

The [validation receipt](richer-review-admission-validation.json) binds the
final output files, six new repository files, source checks, replay results,
test results and document links. The machine report lists seven executing
owner files and explicitly leaves full dependency attestation unavailable.

## Remaining work

All 34 items still need actual human review. Recording a complete declaration
does not supply independently adjudicated training or evaluation labels.
The next semantic milestone needs authenticated review provenance and
adjudication, followed by a larger natural-source corpus with separately
grouped context-sensitive cases. Autoencoder fitting, Leanstral embeddings,
generation and useful proof coverage were not evaluated in this stage.
