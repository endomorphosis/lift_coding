# Richer autoformalization evaluation — 2026-10-03

The richer evaluation is implemented and its first evidence run is complete.
It identifies two concrete improvement priorities: preserving qualifier
identity in formal features, and expanding source interpretation while handling
ambiguity explicitly. **575 focused regression tests passed in 24.59 seconds**;
the actual CLI completed successfully. This run uses authored, synthetic,
unreviewed fixtures. Independent source fidelity remains unavailable and native
useful proving remains unrun.

The [comprehensive improvement plan](../../implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md)
remains the roadmap. This increment adds the richer evaluation contract and
actual construction checks that the preceding
[retrieval experiments](hybrid-report.md) could not measure.

## What was implemented

The [panel](richer-01/panel.json) contains 16 training positives, eight
development positives, six unsupported cases, two ambiguous cases, and two
cases that attach different explicit assumptions to the same source. All
positive references contain conditions, exceptions, and time limits. The
development positives recombine train-known actors, actions, and objects;
two deliberately introduce an unseen condition. Sources and references are
manual literals, with separate hashes and complete case-group separation.
They were not produced by compiling or rendering a reference.

The [construction adapter](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_richer_evaluation.py)
runs the existing source compiler, renders each emitted candidate, and compiles
that rendering again. Authored references enter scoring afterward. Training
references alone supply the frozen vocabulary. Context assumptions are bound
and compiled separately; the current source-only compiler does not resolve
them into the query. Its two context-dependent cases remain unavailable.

The [runner](../../external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_richer_experiment.py)
also compares the original training-only formal codec with a codec fit on the
16 richer training references. It loads no model or projection checkpoint and
fits no neural weights. The original validation split and sealed partitions
remain outside this run's input scope.

## Measured construction results

The [machine-readable report](richer-01/report.json) binds the configuration,
listed implementation files, protected protocol, panel, construction records,
and representation diagnostics.

| Diagnostic | Training positives | Development positives | Combined positives |
| --- | ---: | ---: | ---: |
| Cases | 16 | 8 | 24 |
| Emitted candidate matching authored IR | 3 | 1 | 4 |
| Abstained | 13 | 7 | 20 |
| Candidate round trips preserving exact IR | 3 | 1 | 4 |
| Retained condition atoms / reference atoms | 3/20 | 1/10 | 4/30 |
| Retained exception atoms / reference atoms | 3/20 | 1/10 | 4/30 |
| Retained temporal atoms / reference atoms | 3/20 | 1/10 | 4/30 |

Every positive abstention includes `typed_deontic.unrepresented_procedure`;
the two unseen-condition cases additionally report
`typed_deontic.unmapped_condition`. All four successes are prohibition cases.
No obligation, permission, or multiple-qualifier positive emitted a candidate
on this fixture. These are descriptive results from six authored case groups,
including two development groups, and should not be generalized to a natural
document corpus. Missing candidates stay in the qualifier-retention denominator.

Seven of the eight unsupported or ambiguous cases emitted no IR. That absence
does not establish correct recognition of unsupported semantics or the ability
to ask an appropriate clarification. The remaining case reveals a specific
gap:

> The clerk told the custodian that they must retain the application.

The compiler selected `clerk` as the obligated actor, emitted an obligation,
and preserved that candidate through an exact round trip. The fixture requires
clarification because “they” does not identify a unique actor. This is a
concrete example of schema acceptance and round-trip preservation accompanying
an unreviewed source interpretation. Its complete records remain visible in
[constructions.json](richer-01/constructions.json).

Five emitted candidates produced actual CID-bound deontic bridge transport
artifacts, including this ambiguous case. Their artifacts disclose native
syntax and proof gaps. No solver or kernel executed and no useful-proof
coverage was measured.

## Formal representation results

The [saved assays](richer-01/representation_assays.json) compare exact vectors
before any learned projection:

| Codec | Formal feature width | Distinct authored targets | Distinct vectors | Distinct-target collision pairs |
| --- | ---: | ---: | ---: | ---: |
| Original training-only codec | 22 | 24 | 18 | 6 |
| Richer training-only codec | 27 | 24 | 24 | 0 |

All six original collisions pair rules with identical modality, actor, action,
and object but different qualifier identities. Four pairs occur in training
and two in development. The original qualifier blocks have no known atoms,
so equal counts of unknown conditions, exceptions, and time limits produce
equal vectors. Any deterministic projection of those vectors preserves their
equality; changing a loss function cannot recover the discarded names.

The richer codec distinguishes the 24 observed targets after fitting known
qualifier names on training references alone. The two development
`identity_verified` occurrences still use the unknown condition bucket. Zero
observed collisions establishes separation only on these targets. Other unseen
names can still collide, and a learned projection can collapse distinct inputs.
Binder, nested-scope, temporal reasoning, and proof semantics were not tested
by this flat codec.

The 22 and 27 widths describe **formal features**, not the existing 8D spaCy,
384D embedding, or 768D multilingual embedding inputs. The new codec has a new
feature-space identity and needs a compatible newly trained formal projection
head before numerical comparison. Existing 22-input checkpoint weights cannot
be reused as a 27-input head. No such training ran here.

## Improvement order supported by this evidence

1. Investigate the procedure classification that blocks obligations,
   permissions, and compound qualifiers on these fixed cases. Add focused
   semantic regressions before changing the production parser; preserve
   unsupported meanings and abstention receipts throughout the change.
2. Add explicit actor ambiguity and context-resolution contracts. Keep the
   source, assumptions, atom interpretations, and their provenance separately
   bound. A context-aware encoder input needs its own declared serialization
   and execution receipts.
3. Extend formal features to preserve atom identity and typed structure. Use
   the richer train-only codec as a finite-panel baseline; evaluate an
   open-vocabulary structural encoder for qualifiers, binders, and scope.
   Admit a new formal head with its own feature-space identity and matched
   training/evaluation budgets.
4. Prepare independent source-bound review of richer material and explicit
   native interpretations before evaluating useful proofs. The earlier 40-item
   review queue covers the earlier panel and does not adjudicate these cases.
   Candidate agreement, successful rendering, and bridge transport retain
   separate statuses from source fidelity and native proof acceptance.
5. Resume retrieval-conditioned construction comparisons after these
   semantics and data boundaries are measurable. Keep independent 8D, 384D,
   768D, and Leanstral lanes as specified in the main plan. Leanstral hidden
   embedding extraction, encoder execution, and native prover campaigns
   remain separate experiments.

The [workflow documentation](../../external/ipfs_datasets/docs/autoencoders/alignment_richer_evaluation.md)
includes the reproducible command and scope. The [configuration](../../external/ipfs_datasets/configs/autoencoders/alignment_richer_development_v1.json)
admits a bounded development run, with protected protocol and original
training-data identities. The evidence remains `qualified=false` and
`production_admitted=false`; bindings cover the listed files rather than a
complete transitive dependency closure.
