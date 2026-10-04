# Abstract registration drafts

Prepared September 12, 2026. These are reviewable registration drafts, not
submitted abstracts or claims that the experiments are finished. The full papers
must be reconciled with their final evidence before submission.

The [official workshop dates](https://vericodegen.github.io/cfp.html) list the
abstract deadline as September 11 AoE (September 12, 12:00 UTC) and the paper
deadline as September 13 AoE (September 14, 12:00 UTC). The
[OpenReview research portal](https://openreview.net/group?id=NeurIPS.cc/2026/Workshop/VERICODEGEN)
requires the submitting author's account and author metadata. The user confirmed
that **all three abstracts are already registered**. Submission links/IDs were
not supplied. No submission or change to those registrations has been made by
this agent; the drafts below remain optional reference text for the paper work.

## Autoformalization

**Title:** Compiler-Guided Autoformalization with Adaptive Multi-View Representations

**Abstract:** Autoformalization requires both faithful interpretation of a source
and a computational route for reasoning about the resulting representation. We
describe a compiler-guided architecture that couples symbolic intermediate
representations to adaptive multi-view representation learning. Deterministic
parsers construct source-linked declarations, decompilers expose reconstruction
errors, and guarded optimization updates shared representations. Retrieval and
learned proof guidance propose context and search steps; native checkers determine
whether supported formal claims hold. Explicit preservation contracts distinguish
obligations, permissions, observations, and other logical views. The evaluation
design separates numerical reconstruction, symbolic round trips, source fidelity,
proof coverage, and total learning and verification cost. The implementation
includes a qualified packed CPU training path and a development model-to-proof
pipeline. Training experiments and independent semantic-fidelity annotation are
in progress. This submission draft presents the architecture and evaluation
protocol; it does not claim a measured generalization or end-to-end performance
improvement.

**Suggested keywords:** autoformalization; intermediate representations;
representation learning; proof checking; semantic fidelity.

## Law to Action

**Title:** From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents

**Abstract:** Generated code can satisfy a requested task while violating a
constraint on its effects. We study runtime enforcement at a bounded
pre-invocation Model Context Protocol handler. Legal documents, vulnerability and
repair records, and procedural instructions are represented as Legal, Security,
and Intent intermediate representations with distinct authority. Context-bound
admission connects a proposed action to the constraints and evidence that justify
it. Our evaluation asks whether the handler can prevent a correlated forbidden
sandbox mutation while allowing a matched permitted action to perform useful
work. The protocol separates constraint interpretation, admission decisions,
observed effects, and independent human review. These representations do not
establish legal correctness, universal vulnerability absence, or permission by
themselves. This submission draft presents an implementation and evaluation
protocol with retained source-reproduction evidence. End-to-end measurements and
independent legal, security, and intent judgments remain in progress.

**Suggested keywords:** runtime enforcement; Model Context Protocol; generated
code; authorization; neuro-symbolic systems.

## Neurosymbolic supervision

**Title:** Proof-Carrying Neurosymbolic Supervision: State, Logic-Governed Decisions, and Test-Evidence Reuse

**Abstract:** Coding agents repeatedly reconstruct repository state and rerun
validation, while cached evidence can become invalid when dependencies change.
We present an architecture that separates content-addressed semantic state,
operational task state, and durable verification evidence. Typed obligations
guide analysis, proof search, bounded synthesis, and authorized model calls.
Candidate changes are checked against current source, and retained evidence is
admitted only for its declared statements, environment, and trust profile.
Accepted transitions invalidate affected planning and verification state. The
evaluation protocol compares matched supervision conditions using historical
pre-fix source snapshots, independent cold scoring, and adversarial dependency
mutations. It measures useful completion, invalid admission and reuse, and total
cost with explicit denominators and uncertainty. Unchanged baseline tests have
been qualified for the frozen historical source population; production
development qualification and final comparative experiments remain in progress.
The contribution is a method for governing repository changes with explicit
evidence. This draft makes no measured claim of safe reuse or net cost reduction.

**Suggested keywords:** coding agents; semantic state; proof-carrying code;
incremental verification; test-evidence reuse.

## Draft provenance and author decisions

Titles follow the current supervisor configurations. The descriptions follow
the recovered autoformalization abstract, the law-to-action manuscript, and the
neurosymbolic manuscript and task contracts, with unmeasured claims removed.
Source heads at preparation were `233231536f45f8b268d064c10bf010e663fdba11`
(autoformalization), `817c57d83f7cc7506db505c2ca7574a61c7b4079` (law-to-action),
and `f9aba72dfd502752194c6af9cce7093b8d073656` (supervision).

The author must confirm the title, abstract, complete author list and order,
affiliations, contact/profile information, conflicts, and the workshop's
LLM-review acknowledgment in the actual submission form. The portal's currently
required fields were not accessible in the unauthenticated page read. These
drafts do not supply or infer that information.
