# Novelty statement for the bounded law-to-action evaluation

This statement supplies contribution language integrated in `manuscript/main.tex`
during LA-021. It matches the LA-002 scope decision and the LA-003 protocol. It
is not a claim that the scored study has already run, and it is not a
first-of-kind claim about reference monitors, proof-carrying code, executable
law, capabilities, MCP, or agent-security benchmarks. Primary-source
comparisons live in `related_work.md` and `manuscript/related_work.bib`.

## One-paragraph contribution

The planned workshop-specific contribution is a bounded test of runtime checking for
generated code: under explicit `ENFORCE` configuration, an independently
extracted generated-code effect that is correlated with a reviewed
Security/Intent constraint, and that lacks a matching context-bound admission,
must not produce the handler's declared forbidden mutation, while a matched
admitted case can still perform useful permitted work. The only selected
protected route is `SupervisorPreInvocationEnforcement.authorize_and_delegate`
around one benchmark-owned sandbox mutation handler. Legal IR, CVE source
records, skill Markdown, UCAN grants, content identifiers, and solver jobs are
inputs or accompanying mechanisms. They are not themselves the evaluated
safety result.

The current accepted LA-008 observer covers trusted declarative `export_json`
requests with literal data. Arbitrary-source execution, process/network
isolation, and the complete scored delegate integration are not established
by that checkpoint. AgentSpec and Progent already supply directly relevant
runtime-rule and tool-privilege mechanisms; the contribution must be assessed
against them as well as CaMeL, without a first-system or superiority claim.

## What is composed, not invented

Each piece has a primary-source ancestor. The composition, and the measurement
plan attached to it, is the paper's contribution.

| Piece | Ancestor (primary source) | What this paper adds in the selected evaluation |
| --- | --- | --- |
| Stop a non-admitted action at the actual resource | Complete mediation [saltzer1975protection]; security automata / IRM / edit automata [schneider2000enforceable, erlingsson2000irm, ligatti2005edit] | One explicit `ENFORCE` delegate with independent handler-effect counters; default `OFF` is recorded as pass-through |
| Require a checked artifact before untrusted execution | Proof-carrying code and authentication [necula1997pcc, appel1999pca] | Context-bound admission over actor, tool, arguments, effects, roots, and clock; a `proof_cid` or envelope field is not a check |
| Compile norms from legal text | Catala and related executable-law work [catala, merigoux2021tax, sergot1986bna, prakken2015lawlogic] | Legal IR is a lossy, reviewed compilation of selected facets, used as a constraint source, not as a proof that the law was interpreted |
| Scoped vulnerable/fixed evidence | CVEfixes [cvefixes] | Candidate prohibitions plus independently mapped code effects; retrieval similarity is not transfer |
| Capability attenuation | UCAN, Macaroons, Cedar, object capabilities [ucan, birgisson2014macaroons, cutler2024cedar, miller2006robust] | Lightweight policy+UCAN as arm A3, distinct from proof-oriented A4 |
| Application-level tool enforcement | MCP authorization [mcp, mcp-auth] | An enforcement adapter the protocol actually places on the selected route |
| Utility beside forbidden effects | AgentDojo and related agent-security evaluations [debenedetti2024agentdojo, ruan2024toolemu] | Allowed-task success and false denials as first-class outcomes so blanket denial cannot look like success |

The paper does not claim to introduce a new authorization logic, a new legal
programming language, a new proof checker, a new MCP specification, or a new
general agent benchmark suite. CaMeL [debenedetti2025camel], Catala, AgentDojo,
Clover [sun2024clover], and CompCert [leroy2009compcert] are closer on
individual axes and remain unrun. AgentSpec [wang2025agentspec] and Progent
[shi2025progent] already supply agent runtime rules and tool-privilege control.

## Experimental contribution that may be claimed after evidence exists

If and only if later tasks produce retained raw records, the supported empirical
claim is of this form:

> On the frozen sandbox handler and the selected `ENFORCE` route, matched
> fixed actions show [measured forbidden-effect counts, allowed-work success,
> false denials, unknowns, timeouts] under arms A0/A3/A4 after the named
> mechanisms qualify, with lineage-family clustering and the predeclared
> denominator. A0/A1/A2 remain equivalence controls in the model-free study.

Until those records exist, the manuscript must describe an implementation
report plus a frozen evaluation protocol, not an end-to-end safety result.
Zero observed forbidden effects, if later obtained, support a bounded
empirical rate and interval on the tested population, not a universal safety
theorem.

## Modeling assumptions

These are part of the contribution boundary, not caveats to be dropped in the
abstract.

1. **Legal IR is a model, not the law.** The restricted compiler uses seven
   fields. Exceptions, cross-references, definitions, authority, and dates can
   be lost. Unrepresented material must not disappear into a successful
   result. Expert applicability and disagreement are labels, not solver
   output.
2. **Security IR is a scoped candidate prohibition.** A CVE or CWE identifier
   is not a policy. A fix is a negative control for that prohibition, not a
   proof that other vulnerabilities are absent. Transfer to generated code
   needs an explicit supported effect mapping.
3. **Intent IR is an untrusted procedure description.** Skill Markdown and
   self-authorizing text are data. They are never permission.
4. **Code-effect observation is bounded.** The inspected mapper consumes
   supplied fact groups and handler observations. It is not independent
   static analysis of arbitrary generated languages. A model assertion is not
   an observation.
5. **Proof jobs, signatures, content identifiers, and monitor observations
   have distinct meanings.** Satisfying one does not discharge the others.
6. **Selected logics and checkers are a fragment.** Registry membership is
   not a backend result. QF_LIA interpolation, unselected families, and
   kernel proofs are outside the evaluated method unless a later digest-bound
   deployment and retained receipt qualify them.
7. **The model-free A1/A2 arms do not identify prompt or retrieval efficacy.**
   No planner consumes that metadata. Prompt/retrieval comparisons belong only
   to a separate pinned-model study.

## Trust and deployment assumptions

A positive result on the selected route does not license these stronger
readings.

1. **Configuration.** The source default is `OFF`, which delegates without
   receipt verification or consumption. `AUDIT` and `SHADOW` are
   non-blocking. Only explicit `ENFORCE`, with injected roots, clock,
   issuer/service, and a qualified consumption store, is enforcement.
2. **State.** The default `InMemoryCapabilityConsumptionStore` is
   process-local. Restart-safe or cross-worker single-use is not claimed
   unless a durable adapter is qualified with concurrency, lost-reply, and
   restart injection.
3. **Complete mediation.** The claim is restricted to the selected
   `authorize_and_delegate` sandbox route. `ExecutionPermit`, MCP dispatch,
   Quack/DuckDB owner recovery, remote handlers, libp2p carriage, and other
   supervisor callers are not selected protected routes.
4. **Cryptography.** Fixture verifiers and fake bearer tokens are not UCAN
   verification. Real signatures, attenuation, revocation, and replay
   resistance require a qualified cryptographic provider.
5. **Roots and time.** Admission is relative to current trusted IR roots and
   clock. Stale roots, forged proof identifiers, wrong audience, widened
   path/tenant, and changed live environment are in-scope mutations only when
   actually executed on the selected route.
6. **Sources.** Release-card corpus totals are not evaluated populations.
   Lawful access, immutable pins, and independent labels are prerequisites
   for scored cases.
7. **Fixtures.** Existing CVE e2e, admissibility, MCP dispatch, and
   enforcement unit tests are hermetic or injectable-fake surfaces. They are
   conformance scaffolding, not the workshop result.

## Explicit non-claims (do not promote)

- Universal agent safety, default-safe deployment, or complete mediation of
  MCP.
- Trained SkillCenter normalizer or encoder performance.
- Exhaustive legal coverage or worldwide statutory completeness.
- Execution of every listed logic family.
- Peer availability, content persistence, or wide-area transport security.
- Semantic program worlds, learned residuals, refactoring, parallel sealing,
  or proof-carrying test reuse (unavailable for this draft; neighboring-paper
  scope).
- Superiority to Catala, CaMeL, AgentDojo, Cedar, CompCert, Clover, AgentSpec,
  Progent, or any other listed system.
- Any numerical safety, utility, or cost advantage before retained runs.
- First agent runtime-rule layer, first tool-privilege monitor, or first
  capability-isolated agent design.

## Workshop-specific novelty, in one sentence

For the AI for Verifiable Coding 2026 workshop [vericode2026cfp], the
distinct claim is that generated-code effects can be treated as independently
observed actions and checked at a real tool-handler boundary against
source-grounded, context-bound admission—measuring forbidden mutations and
useful permitted work together—without identifying that check with legal
interpretation, prompt text, retrieval, a signature, or a content identifier.

## Manuscript integration

The contribution paragraph, modeling and trust lists, and non-claims appear in
the abstract, introduction, related-work section, and conclusion of
`manuscript/main.tex`. The four draft "implemented contributions" are kept only
as unqualified implementation context, not as evaluated results. Bibliography
loading uses `related_work.bib` without `\nocite` of unrun systems. LA-022
later reconciles the full narrative with the evidence actually produced.
