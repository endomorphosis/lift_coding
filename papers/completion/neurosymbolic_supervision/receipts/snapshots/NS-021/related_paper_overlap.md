# Distinct contribution and overlap with the companion workshop submissions

Status on 2026-09-11: this is a nonidentifying overlap audit for the neurosymbolic-supervision paper against the two companion 2026 AI for Verifiable Coding workshop drafts. It does not identify authors, repositories, or private projects. It does not treat shared implementation surfaces, shared literature, or shared environment limits as independent experimental replication.

The three drafts, as recovered for this completion program:

| Short name | Title | Distinct research question |
|---|---|---|
| Neurosymbolic supervision (this paper) | Proof-Carrying Neurosymbolic Supervision: State, Logic-Governed Decisions, and Test-Evidence Reuse | Can persistent semantic state, explicit obligations, residual model authorization, phase-aware test evidence, and accepted-transition publication govern repository evolution without silently upgrading evidence, relative to matched raw-context baselines? |
| Autoformalization | Compiler-Guided Autoformalization with Adaptive Multi-View Representations | Do compiler-guided multi-view representations and independently admitted proof feedback improve source-facet fidelity and useful checked proof coverage per cost on unseen material? |
| Law to action | From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents | Can source-grounded Legal/Security/Intent constraints prevent non-admitted effects at a protected tool-invocation boundary while still permitting useful authorized work? |

## What is distinct

This paper's intended contribution is a *tested supervision/evidence composition*, not a new proof calculus, a new autoformalization learner, or a new legal compiler.

It may claim, if and only if the frozen A–D experiment and independent oracle later support the exact wording:

- persistent, identity-bound semantic state separate from operational task state and durable artifacts;
- obligation-gated routing that may authorize a neural residual but cannot let a model lower objectives or drop required tests;
- admission of test and proof results only for declared statements, environments, and trust profiles, including fixture-lifecycle reuse scored by a cold oracle;
- accepted-state publication with parent-bound invalidation.

It may not claim:

- that it is the first neurosymbolic agent (the draft already says it does not claim to be the first neurosymbolic agent);
- that combining PCC, CEGAR, CEGIS, equality saturation, build-system reuse, coding agents, retrieval/hammers, or prompt compression automatically improves performance;
- that hashing, model confidence, or an available solver proves arbitrary Python;
- autoformalization training, held-out source-fidelity, or proof-transfer results belonging to the autoformalization draft;
- legal/CVE/skill corpus enforcement, MCP handler mediation, or UCAN/capability results belonging to the law-to-action draft;
- native Groth16 or learned world-model efficacy unless that optional profile is separately qualified (currently unavailable / future work).

The autoformalization draft's distinct contribution is source-grounded IR construction, multi-view learning, and independently judged proof transfer (pipeline arms A–E and learning arms T0–T5). The law-to-action draft's distinct contribution is corpus-grounded constraint compilation and pre-invocation enforcement on protected tool handlers, with both forbidden-effect and useful-work endpoints.

Those are different independent variables, different endpoints, and different oracles. They are related workshop papers, not three writes of one experiment.

## Shared literature (not shared experiments)

Two bibliographic works appear in both this paper and the autoformalization reconstruction:

| Work | This paper | Autoformalization reconstruction | What the overlap is |
|---|---|---|---|
| Pnueli, Siegel, and Singerman, Translation validation, TACAS 1998 | `[4]` / `baseline04` | `original07` | Common foundation for checking a produced conversion. Not a joint benchmark. |
| Jiang et al., Thor, NeurIPS 2022 | `[10]` / `baseline10` | `original10` | Common hammer/ATP baseline. Not a joint Thor rerun. |

LeanDojo `[9]` is cited here as a retrieval baseline; the autoformalization draft discusses Tactician/Hammer/Leanstral as proposal mechanisms without that same twelve-item list. Citing adjacent proof-search papers does not mean either submission evaluated the other's protocol.

The law-to-action reconstruction's eight references are infrastructure and corpus records (tool-invocation specification, a legal language, a vulnerability-fix collection, content identifiers, capability tokens, and related protocol notes). It does not share this paper's twelve-item list. Catala, CVE-fix collections, and the public tool-invocation specification are that paper's sources, not this paper's evaluation set.

No shared citation is an experimental result. Each paper must generate tables from its own frozen receipts.

## Shared implementation surfaces (disclose; do not triple-count)

The three drafts describe mechanisms that inspect the same agent-supervisor, datasets, and content-addressed kit forest. Anonymous names for those surfaces, without repository URLs:

| Shared surface | Role in this paper | Role in autoformalization | Role in law to action | Counting rule |
|---|---|---|---|---|
| Domain-neutral claim/evidence kernel and Legal/Security/Intent views | Source of typed obligations; domains do not share verdict authority | View families for autoformalization and proof transfer | Source-preserving Legal/Security/Intent compilers feeding authorization | One kernel inspection is one inspection. It is not three independent IR implementations. |
| Loss-aware translation / temporal-deontic projection | Must reject unjustified source-level lifting | Negative control when a converter erases modalities | Family-specific compilers with unsupported-facet abstention | A documented translation loss can be cited by each paper as a limitation. A single converter run is not three translation experiments. |
| Optional native proof wrapper and restricted derivation helper | NS-014 closed the native profile as unavailable | Native proof coverage is an autoformalization endpoint still to be measured | Solver/crypto integration is still to be measured | The same missing backend version and unverified key/circuit are one environment fact. Unavailable proving is not three independent negative results. |
| Typed operational-state owner, fences, and durable receipts | Publication, restart, and recovery (core D arm) | Promotion/rollback of learned guidance | Durable capability consumption and owner recovery | Shared bookkeeping. Each paper counts only the receipts from its own frozen protocol. |
| Content-addressed store and capability/token checks | Durable artifacts do not establish truth by persistence | A content identifier binds encoding, not interpretation | Content identity is not publication or authorization | Shared storage semantics. Persistence is not a result. |
| Protected tool-invocation and capability attenuation | Out of this paper's evaluated core; mentioned as requiring its own tests | Not the autoformalization endpoint | Central enforcement boundary | Law-to-action owns the handler-mediation claim. This paper must not absorb it. |

The reconstructed source-forest and capability inventory for this paper (`artifacts/source_forest.json`, `artifacts/capabilities.json`, `audit/implementation_inventory.json`) record inspection, not a live three-paper deployment. Those files may be cited anonymously as `anon-supplement:source-forest` in this paper only.

## Shared evaluation hazards

1. **Preliminary 40-task / 40-transition arithmetic** in this draft's Table 5 is a repository-reported NS-only preliminary. It has no model receipts and is not production-eligible. It is not an autoformalization training result, not a law-to-action enforcement result, and not a live A–D measurement. Do not reuse those percentages in the other papers or relabel them as new runs.

2. **Matched A–D arms** (raw context; semantic context; symbolic route/reuse; governed lifecycle) are this paper's protocol. They are not the autoformalization A–E source-to-proof pipeline or T0–T5 learning ablations, and not the law-to-action unguarded / prompt-only / retrieval+prompt / lightweight-policy / full-enforcement arms. Equal Latin letters do not make the experiments the same.

3. **Independent oracles.** This paper requires a hidden repair/acceptance oracle and a cold full validator for reuse. Autoformalization requires independently judged source fidelity and native checker receipts. Law to action requires observed handler effects and forbidden-versus-useful work. Scoring artifacts must not be copied across papers.

4. **Provider, solver, and GPU environment.** Quota exhaustion, missing native provers, and host capacity are campaign-environment facts. Reporting them in each paper as a limitation is honest. Reporting them as three independent experimental outcomes is double-counting.

5. **Optional campaigns.** Learned world models, semantic refactoring, federation, and native circuits are optional here and are also out of scope or future work in the companions unless that companion actually qualifies them. A future-work sentence in all three drafts is not three deferred implementations.

## Novelty statement for this paper (bounded)

The novelty that may appear in the anonymous manuscript is:

> The paper studies a composition of established methods — proof-carrying evidence, abstract interpretation, CEGAR, translation validation, CEGIS, equality saturation, build-system reuse, coding-agent interfaces, test-validation benchmarks, premise retrieval, theorem-prover hammers, and prompt compression — at the agent's operational boundary: persistent semantic state, explicit obligations, residual authorization, phase-aware test evidence, and accepted-transition publication. It does not introduce those foundations, is not the first neurosymbolic agent, and does not claim that the composition improves repair, cost, or safety until the frozen matched evaluation says so.

That statement is about this paper's question. It does not deny the companions' questions, and it does not treat their unrun tables as this paper's evidence.

## What NS-022 must keep visible

- Name the companions only as concurrent workshop submissions on autoformalization and on runtime enforcement of source-grounded constraints, without repository links or author-identifying aliases.
- State that shared kernel, translation, storage, and native-proof surfaces are common infrastructure, not three replications.
- Keep Table 5 labeled preliminary and NS-local.
- Keep native proving unavailable unless a later NS-014-class qualification reverses that closure with a real backend.
- Do not import autoformalization fidelity numbers or law-to-action corpus counts into this paper's abstract or Tables 17–18.

## What this audit does not claim

- It does not compare measured effect sizes; none of the three frozen live evaluations is complete in the evidence reviewed here.
- It does not assert that the companions will or will not be submitted.
- It does not assign authorship, funding, or artifact-release rights.
- It does not treat this document as the anonymous supplement. The supplement, if any, is an NS-024/NS-025 packaging product.

## Limitations

Companion bibliography reconstructions remain literal in places (`original01`–`original10` in autoformalization; eight infrastructure entries in law to action). Those papers have their own verification tasks. This audit used the recovered titles, abstracts, and reference strings to identify overlap, not a claim that those other bibliographies are already publisher-verified. If a companion later drops Thor or translation validation, the shared-literature table above should be updated; the distinct-contribution rule does not depend on those two citations remaining.
