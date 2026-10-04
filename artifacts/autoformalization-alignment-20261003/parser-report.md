# Complete qualifier parsing comparison — 2026-10-03

An opt-in controlled English compiler now preserves compound qualifiers and
rejects the actor ambiguity exposed by the [richer evaluation](richer-report.md).
On its unchanged authored panel, exact agreement increased from **4/24 to 22/24
positive cases**, including **1/8 to 6/8 development cases**. The two unseen
conditions still cause abstention. All **673 tests passed in 35.92 seconds**;
Ruff and the actual comparison CLI passed.

These are exploratory regression results. The grammar was designed after
examining exposed development failures. The panel is synthetic, authored, and
unreviewed; these gains do not establish independent source fidelity or a new
held-out evaluation. Native useful proving remains unrun.

## Why a separate profile

The legacy parser inferred procedures from event-like nouns such as
“application,” “order,” and “notice,” even without a stated procedural relation.
That diagnostic blocked many richer cases. It also masked separate losses:
one compound qualifier phrase could map to one best atom, and multiple time
limits could disappear. Removing the procedure check alone would expose silent
losses and preserve the legacy actor ambiguity.

The new [ExplicitQualifierCanonicalCompiler](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_explicit_qualifiers.py)
therefore parses the complete controlled sentence directly. It matches exact
caller-declared atom surfaces, retains all supported qualifier atoms, and
requires `and` for conditions, `or` for exceptions, and `and` for time limits.
It accepts declared article, copula, and `applies` forms, without fuzzy atom
assignment. Unsupported connective polarity, quantification, scope, extra
clauses, or unknown phrases cause abstention. It does not invent procedures or
call the legacy converter, a model, or a fallback.

Its configuration CID and provenance identify a separate opt-in profile.
The frozen default compiler, parser, benchmark identities, richer fixtures,
and protected protocol bytes remain unchanged. The frozen round-trip
orchestrator rejects the alternative configuration before execution. The
comparison explicitly runs the new compiler, the existing IR-only
source-withheld renderer, and the new compiler again; that composition does
not claim frozen benchmark admission.

## Same-panel results

The [machine-readable report](parser-01/report.json) binds the unchanged
[panel](richer-01/panel.json), old construction evidence, listed implementation
files, and the new [construction records](parser-01/constructions.json).
Before comparing results, the runner reran all **34 baseline constructions**
and required exact equality with their saved receipts.

| Diagnostic | Frozen baseline | Opt-in profile |
| --- | ---: | ---: |
| Training exact authored IR | 3/16 | 16/16 |
| Development exact authored IR | 1/8 | 6/8 |
| Combined exact authored IR | 4/24 | 22/24 |
| Combined positive exact round trips | 4/24 | 22/24 |
| Development retained conditions / reference atoms | 1/10 | 8/10 |
| Development retained exceptions / reference atoms | 1/10 | 8/10 |
| Development retained temporal atoms / reference atoms | 1/10 | 8/10 |
| Negative cases emitting a candidate | 1/8 | 0/8 |
| Explicit-context cases resolving to a candidate | 0/2 | 0/2 |

There are 18 new exact authored matches and no exact-match regressions among
the positive cases. Every new emitted candidate preserves its complete IR
through rendering and reparsing. The six multiple-qualifier positive cases
retain both conditions, both exceptions, and both time limits. The two
development `identity_verified` conditions remain outside the frozen training
vocabulary and produce explicit `unmapped_conditions` abstentions. They are
not silently replaced with a known atom.

All 22 emitted positive candidates produced actual CID-bound deontic bridge
transport artifacts with disclosed gaps. These artifacts are schema/transport
evidence, not native syntax or solver/kernel proof receipts.

## Ambiguity and unsupported meaning

The [source-only guard](../../external/ipfs_datasets/ipfs_datasets_py/logic/legal_ir/canonical_source_guards.py)
recognizes a narrow attributed-actor pattern involving two distinct named
participants and a third-person deontic subject:

> The clerk told the custodian that they must retain the application.

The old compiler selected `clerk`, and that candidate survived an exact round
trip. The new profile abstains with `source.unresolved_actor_pronoun`, binds the
pronoun's exact source span, and records that clarification is required. The
application still needs to surface that diagnostic and obtain an explicit
actor; no interactive clarification workflow or general coreference resolver
was added.

The other seven negative cases also emit no IR. Independent regressions reject
unsupported condition disjunction, exception conjunction, temporal
disjunction, negated qualifiers, double negation, coordinated or reported
actors, multiple rules, and unsupported trailing prose. Absence is an observed
output, not a general certificate of correct unsupported-semantic recognition.

The two explicit-context cases still bind their source and differing
assumptions separately and remain unavailable. The new compiler has no context
resolver and does not infer, concatenate, or inject those assumptions into a
query interpretation.

## Implementation and verification

The [comparison runner](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_parser_experiment.py)
receives only source text, request identity, and the frozen training vocabulary
at construction time. References enter posthoc scoring afterward. Its report
declares `development_used_to_design_grammar=true` and
`development_used_in_vocabulary_fit=false`. The old validation split and
sealed final-test material remain outside the experiment's input scope.

The tests exercise complete source consumption, exact qualifier retention,
polarity, unknown atoms, competing complete parses, source maps and CIDs,
frozen-orchestrator rejection, reference-mutation invariance, immutable
baseline replay, context unavailability, deadline handling, forged evidence
rejection, and protocol drift. The combined run covered 20 focused test files
and passed 673 cases. It does not replace a release-wide or native-prover
campaign. [Workflow documentation](../../external/ipfs_datasets/docs/autoencoders/alignment_parser_improvement.md)
provides the grammar, direct API example, scope, and reproduction command.

No encoder, autoencoder, Leanstral weights, provider, solver, or kernel ran.
No projection head was fitted. The independent 8D, 384D, and 768D source paths
and the previous 22D/27D formal feature assays are unchanged. Bindings cover
the listed files, not a complete transitive dependency closure. The report
retains `qualified=false` and `production_admitted=false`.

## Next work supported by the result

The [comprehensive plan](../../implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md)
can now use a measured qualifier-preserving construction baseline. Subsequent
work should evaluate independently sourced and reviewed richer material,
extend explicit assumptions and binder/scope representation, and compare
open-vocabulary formal features with matched retrieval-conditioned generation
budgets. Actual native qualifier interpretations and checker execution remain
necessary before useful-proof coverage can be evaluated. The controlled
grammar improves this panel's construction baseline; it does not solve general
natural-language autoformalization.
