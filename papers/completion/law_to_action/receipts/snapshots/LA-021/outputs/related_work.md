# Related work for a bounded generated-code-to-protected-effect evaluation

Status: LA-021 literature comparison complete. Closest systems, implementable
arm rationale, and workshop fit are cited from primary sources retrieved or
Crossref/arXiv-checked on 12 September 2026. Three versioned agent-runtime
records (AgentSpec, Progent, CaMeL) were previously checked in
`receipts/snapshots/LA-021/operator-review/primary_sources.json`. This note is
an editable related-work manuscript, not a scored bake-off and not a completion
receipt.

No system named below was executed as an experimental arm in this paper's
protocol. The reconstructed draft cited eight infrastructure sources
(`mcp`, `mcp-auth`, `catala`, `cvefixes`, `quack`, `ipfs`, `libp2p`, `ucan`).
Those remain; the additions below supply the missing generated-code,
runtime-enforcement, proof-carrying authorization, executable-law, and
agent-security comparisons. Broad storage and transport descriptions stay
subordinate to the tested contribution.

Bibliographic keys match `papers/completion/law_to_action/manuscript/related_work.bib`.
`manuscript/main.tex` loads that file only (`\bibliography{related_work}`), so
the eight inherited keys stay resolvable without duplicating `references.bib`.
Citation is by discussion, not `\nocite` of unrun systems. LA-022 later
reconciles the complete results narrative.

## 1. Planned contribution and current qualification boundary

The paper's selected experimental question, frozen by LA-002 and LA-003, is
whether an independently extracted generated-code effect, correlated with a
reviewed Security/Intent constraint and a context-bound admission, is denied
at one actual pre-invocation delegate while a matched admitted case can still
perform useful permitted work. The only selected protected route is
`SupervisorPreInvocationEnforcement.authorize_and_delegate` in explicit
`ENFORCE` mode around one benchmark-owned sandbox mutation handler. Code-effect
correlation is an input from `map_code_security_requests` /
`correlate_security_requests`, not a claim of independent static analysis of
arbitrary languages.

That question is a runtime-checking instance of the workshop's verifiable-coding
brief [vericode2026cfp]: the planned method would admit generated code only when
a separately checked artifact binds actor, tool, arguments, effects, roots,
and clock, with independent observation of the handler mutation. It is not a legal-interpretation
study, not an all-logic prover survey, not a trained-normalizer evaluation, and
not a claim of complete mediation on every MCP, network, or remote path.

The accepted LA-008 observer checkpoint is narrower than that planned study: it
handles trusted declarative `export_json` requests with literal data. It does not
execute arbitrary generated source or establish process/network isolation.
Integration of this observer with the selected enforcement delegate and scored
comparisons remains pending.

Four comparison axes are used throughout. They match the protocol's outcome
vocabulary rather than venue prestige.

| Axis | What is compared | What would count as evidence here |
| --- | --- | --- |
| Assurance boundary | Where a non-admitted action is actually stopped | Handler call and mutation counters at the selected `ENFORCE` delegate |
| Source fidelity | Whether a constraint is a reviewed derivation from a named source | Held-out legal/CVE/skill labels with abstention; not retrieval similarity |
| Generated-code effect observation | Whether undeclared or broader code effects are observed independently of intent text | Separate code/handler effect record; model assertions are not observations |
| Useful-work measurement | Whether permitted work still succeeds | Allowed-task success and false denials beside forbidden-effect counts |

Rejecting every action would look safe on forbidden-effect rate alone. Useful
permitted work is therefore a first-class outcome [saltzer1975protection].

## 2. Closest related systems

Closest does not mean most famous. It means overlapping the selected route on
at least one axis above. Each paragraph states the primary source, the
assurance boundary the source actually claims, and the gap relative to this
evaluation. None of these systems is a scored arm.

### 2.1 Runtime enforcement and complete mediation

Saltzer and Schroeder [saltzer1975protection] state complete mediation, least
privilege, and economy of mechanism as protection principles. Schneider
[schneider2000enforceable] characterizes security automata that can be enforced
by a monitor that sees program actions. Erlingsson and Schneider
[erlingsson2000irm] inline such monitors. Ligatti, Bauer, and Walker
[ligatti2005edit] add edit automata that may truncate or insert actions.
Hamlen, Morrisett, and Schneider [hamlen2006enforcement] separate what is
enforceable by static analysis, execution monitoring, or rewriting.

These papers are the theoretical ancestors of a pre-invocation gate. They do
not compile legal or CVE sources, do not correlate generated-code effects with
Intent IR, and do not measure useful MCP-handler work. This paper does not
re-implement an inlined Java monitor. The implementable analogue is an explicit
`ENFORCE` check immediately around one handler, with OFF/AUDIT/SHADOW recorded
as non-enforcement.

### 2.2 Proof-carrying code and proof-carrying authorization

Necula [necula1997pcc] has untrusted code carry a proof that a checker verifies
before execution. Appel and Felten [appel1999pca] apply the same idea to
authentication: a request carries a proof in an authorization logic, and a
small checker decides access. Pnueli, Siegel, and Singerman
[pnueli1998translation] check a translation result independently of the
translator. CompCert [leroy2009compcert] shows
that a realistic compiler can itself be proved.

These systems supply the paper's proof-before-delegation pattern and the
insistence that a `proof_cid` in an envelope is not a checked proof. They do
not observe generated-code tool effects in an MCP agent, and they do not treat
legal interpretation as a reviewed, lossy compilation. This paper does not
claim a new proof-carrying-code calculus.

### 2.3 Executable legal rules versus checked derivation

Sergot et al. [sergot1986bna] encode a statute as a logic program. Prakken and
Sartor [prakken2015lawlogic] survey law and logic from an argumentation
perspective and keep interpretation, defeasibility, and proof distinct.
Benzmüller, Parent, and van der Torre [benzmueller2020logikey] provide a
normative-reasoning framework and tool chain. Catala [catala] is the closest
executable-law language: literate legal specifications compile to programs,
with a demonstrated tax-code compiler [merigoux2021tax].

Catala is a source-to-program compiler for expert-authored law. It is not an
agent runtime, not a capability system, and not a generated-code effect
observer. The reconstructed manuscript already cites Catala as a
precedent for executable law while placing this work at runtime agent and
capability boundaries. That distinction is preserved: a Legal IR atom is a
modeled, possibly lossy compilation of selected facets (modality, actor,
action, object, conditions, exceptions, temporal qualifiers). Unsupported
facets must remain explicit. Legal interpretation, expert disagreement, and
jurisdiction/date applicability are not discharged by a successful parser or
solver job. They remain labeling obligations (LA-005/LA-009), not theorems.

### 2.4 Capabilities, policy languages, and MCP authorization

Miller [miller2006robust] states object-capability discipline. Macaroons
[birgisson2014macaroons] attenuate contextual caveats in decentralized
authorization. Zanzibar [pang2019zanzibar] stores consistent relation tuples
for global authorization. Cedar [cutler2024cedar] is an analyzable
authorization language with a validated design. UCAN [ucan] is the signed
delegation specification used by the inspected stack. MCP [mcp] supplies tool
discovery and invocation; MCP authorization [mcp-auth] specifies OAuth 2.1
resource-server roles and requires implementations to follow OAuth 2.1
security best practices. That protocol is not a generated-code effect monitor.

These sources justify a lightweight policy-plus-capability arm: check a signed,
attenuated grant for an exact actor, audience, resource, ability, and validity
window. They do not by themselves observe generated-code effects or compile
legal/CVE constraints. UCAN verification is not theorem checking. A valid
signature on irrelevant bytes, a parsed unsigned stub, or an agent-authored
permission sentence cannot replace a strict verifier. Exact proof-capability
binding remains a separate trusted mapping.

### 2.5 Verifiable generated code

HumanEval [chen2021codex] measures functional correctness of generated
programs. SWE-bench [jimenez2024swebench] measures issue resolution on real
repositories. Clover [sun2024clover] closes a generate–verify–repair loop
against formal specifications. LeanDojo [yang2023leandojo] and autoformalization
with LLMs [wu2022autoformalization] target theorem-prover artifacts.

These are the workshop-neighborhood coding and proof systems. They measure
tests, issue resolution, or proof success. They do not count independently
observed forbidden handler mutations under a mismatched admission, and they do
not treat CVE vulnerable/fixed pairs or skill Markdown as sources of runtime
constraints. This paper does not absorb the autoformalization lane's training
or proof-transfer claims.

### 2.6 Agent-security benchmarks and agent runtime isolation

AgentSpec [wang2025agentspec] provides an agent rule language with runtime
triggers, predicates and enforcement. Progent [shi2025progent], in its May
2026 revision, constrains tool calls through symbolic privilege rules and
classifies policy updates with an SMT solver. These directly adjacent systems
belong in the comparison; the proposed study cannot claim to introduce agent
runtime rules, tool privilege control, or guarded policy updates. Their cited
results are not measurements of this implementation.

AgentDojo [debenedetti2024agentdojo] is the closest agent-security benchmark:
dynamic tool environments, prompt-injection attacks, and a utility-versus-attack
trade-off. ToolEmu [ruan2024toolemu] identifies LM-agent risks in an
LM-emulated sandbox. InjecAgent [zhan2024injecagent] benchmarks indirect prompt
injection in tool-integrated agents. τ-bench [yao2024taubench] measures
policy-following tool-agent-user interaction. AgentHarm
[andriushchenko2025agentharm] measures harmfulness of LLM agents. CaMeL
[debenedetti2025camel] is an adjacent *design* for agent runtime
isolation: capability-based checks constrain data flows at tool calls under
the system's configured policies. This is not a universal guarantee against
all misuse of tools.

These systems motivate measuring forbidden effects *and* useful work, and they
motivate treating prompt-only and retrieval-plus-prompt safeguards as distinct
from a reference monitor. They are not this paper's protocol. ToolEmu's
emulated tools are not independently observed handler mutations. AgentDojo's
environments are not the selected `authorize_and_delegate` route. CaMeL is not
wired into the scored arms. Citing them does not mean they were run.

CVEfixes [cvefixes] remains a source collection of vulnerabilities and fixes,
not a runtime. Vulnerable examples are positive controls for a scoped
prohibition; fixed examples are negative controls for that prohibition. A fix
is not universal safety. Retrieval similarity is not transfer.

## 3. Comparison on the four axes

Literature comparison only. Every "Benchmarked here?" cell is **No**.

| System (primary source) | Assurance boundary | Source fidelity | Generated-code effect observation | Useful-work measurement | Relation to this evaluation | Benchmarked here? |
| --- | --- | --- | --- | --- | --- | --- |
| Complete mediation [saltzer1975protection] | Every access checked by a reference monitor | Not a source compiler | Access requests, not generated-code IR | Availability is a protection goal | Design principle for the selected `ENFORCE` route | No |
| Security automata / IRM / edit automata [schneider2000enforceable, erlingsson2000irm, ligatti2005edit] | Monitor or rewriter on program actions | Policy automaton, not legal/CVE corpora | Program events | Not MCP-handler utility | Ancestor of pre-invocation enforcement | No |
| Proof-carrying code [necula1997pcc] | Checker accepts a proof before running untrusted code | Compiler-produced proofs | Binary/code meeting a safety policy | Correctness, not task utility | Ancestor of proof-before-delegation | No |
| Proof-carrying authentication [appel1999pca] | Small checker of an authorization-logic proof | Auth-logic formulas | Network request, not tool-effect IR | Access decision | Ancestor of proof-carrying authorization | No |
| CompCert / translation validation [leroy2009compcert, pnueli1998translation] | Proved or validated compiler | Source program to assembly | Compilation, not agent tools | Compiler correctness | Distinct-meaning reminder: translator ≠ proof | No |
| Catala / tax-code compiler [catala, merigoux2021tax] | Compiled legal program | Expert-authored literate law | Program execution, not MCP handlers | Tax computation | Closest executable-law precedent | No |
| BNA-as-LP / law-and-logic / LogiKEy [sergot1986bna, prakken2015lawlogic, benzmueller2020logikey] | Logical derivation from encoded norms | Encoding is already an interpretation | Not generated-code effects | Not agent utility | Keep interpretation distinct from checked derivation | No |
| UCAN / Macaroons / Cedar / Zanzibar [ucan, birgisson2014macaroons, cutler2024cedar, pang2019zanzibar] | Capability or policy decision on a request | Policy, caveats, or relation tuples | Request fields, not independent code effects | Authorization latency/consistency, not handler utility | Lightweight policy+capability class (arm A3) | No |
| MCP + MCP authorization [mcp, mcp-auth] | Tool discovery/invocation; OAuth 2.1 resource-server roles | Protocol schema | Tool call payload | Interoperability | Why a separate application enforcement adapter is required | No |
| CaMeL [debenedetti2025camel] | Capability isolation of agent data flow | Not legal/CVE/skill IR | Tool arguments via capabilities | Utility on existing agent benches in that paper | Adjacent capability-based agent-runtime design | No |
| AgentSpec [wang2025agentspec] | Runtime triggers, predicates, and enforcement rules | User-specified or generated rules; not this paper's reviewed corpus | Agent actions, including code execution in its reported domains | Safety and overhead in its own evaluation | Direct precedent for an agent runtime-rule layer | No |
| Progent [shi2025progent] | Deterministic privilege checks on tool names and arguments; SMT-classified policy updates | Task-derived symbolic policies | Tool-call admission under the configured policy | Security and utility in its own evaluation | Direct precedent for tool privilege control and guarded updates | No |
| AgentDojo [debenedetti2024agentdojo] | Prompt-injection attack vs defense in tool agents | Task/policy text | Tool calls in dynamic envs | Benign-task utility vs attack success | Closest agent-security *benchmark* | No |
| ToolEmu [ruan2024toolemu] | LM-emulated risky tools | Not source-grounded IR | Emulated, not real handler counters | Safety vs helpfulness | Related safety bench; different observer | No |
| InjecAgent / AgentHarm / τ-bench [zhan2024injecagent, andriushchenko2025agentharm, yao2024taubench] | Injection, harm, or policy-following oracles | Task specs | Tool-use traces | Task or harm scores | Related agent evaluations; different oracles | No |
| HumanEval / SWE-bench [chen2021codex, jimenez2024swebench] | Tests or issue resolution | Problems or GitHub issues | Generated patch behavior via tests | Pass@k or resolve rate | Useful-coding neighborhood; no gated forbidden-effect counters | No |
| Clover / LeanDojo / autoformalization [sun2024clover, yang2023leandojo, wu2022autoformalization] | Spec/proof checker | Formal spec or informal math | Proof or verified program | Proof or closed-loop success | Workshop neighbors; different artifact | No |
| CVEfixes [cvefixes] | None (dataset) | Vulnerable/fixed source pairs | N/A | N/A | Security-source collection; not a runtime | No |
| This paper (planned, unrun as a scored study) | `ENFORCE` at `authorize_and_delegate` around one sandbox handler | Reviewed Legal/Security/Intent IR; legal fidelity not a substitute for the runtime claim | Independent handler counters plus retained code-effect mapping | Allowed work and false denials beside forbidden effects | Selected contribution | Protocol frozen; not a completed bake-off |

Infrastructure citations [quack, ipfs, libp2p] describe operational state,
content identity, and peer transport. They remain necessary implementation
context. They are not closest systems on the four axes and are not baselines.

## 4. Implementable baseline rationale

LA-003 freezes five matched arms on the same preselected action, actor,
audience, arguments, sandbox state, handler, observer, clock, and route. The
rationale for those arms is taken from the primary sources above. The
implementation is the corresponding *mechanism class in this stack*, not a
port of those artifacts. Fixture verifiers, mocked receipts, and in-memory
consumption do not qualify a scored arm.

| Arm | Mechanism class | Primary-source rationale | What is actually implementable here | What the arm may be used to claim |
| --- | --- | --- | --- | --- |
| A0 unguarded sandbox | No reference monitor | Negative control implied by complete mediation [saltzer1975protection]; unconstrained tool use in SWE-bench/AgentDojo [jimenez2024swebench, debenedetti2024agentdojo] | Direct preselected handler request with independent effect observation | Mechanism reference. Not "agents are unsafe in general." |
| A1 prompt-only label | Policy text without a monitor | Prompt defenses evaluated in AgentDojo [debenedetti2024agentdojo]; policy-following in τ-bench [yao2024taubench] | Same delegate as A0; inert frozen policy-text metadata | In the *model-free* study: equivalence control only. Prompt efficacy is not identified because no planner consumes the text. Prompt efficacy, if measured at all, belongs to the separate LA-016 model study after a pinned model exists. |
| A2 retrieval+prompt label | Retrieved source text without a monitor | Retrieval of legal/CVE/skill text without enforcement; Catala and CVEfixes are sources, not gates [catala, cvefixes] | Same delegate as A0; inert policy and lineage-safe retrieval metadata | Equivalence control in the model-free study. Retrieval efficacy is not identified there. |
| A3 lightweight policy+UCAN | Capability/policy check without proof jobs | UCAN [ucan], Macaroons [birgisson2014macaroons], Cedar [cutler2024cedar], MCP authorization [mcp-auth] | Declared lightweight policy plus a *qualified real* capability verifier | Capability/policy comparison versus A0 after LA-011/LA-014 qualify the verifier. Not a Cedar or Zanzibar replica. |
| A4 full enforcement | Proof-carrying admission + complete mediation + durable use | PCC [necula1997pcc], PCA [appel1999pca], IRM/edit automata [schneider2000enforceable, ligatti2005edit], Saltzer complete mediation [saltzer1975protection] | A3 plus explicit `ENFORCE`, exact context/root/clock/effect binding, qualified selected proof/checker route, and durable consumption | Full selected-mechanism comparison versus A3/A0 after LA-010 and LA-012 qualify those mechanisms. Not a CompCert-strength theorem. |

Useful scientific contrasts in the model-free study are A3 versus A0 and A4
versus A3/A0 after the named mechanisms qualify. An A0/A1/A2 discrepancy is a
comparability defect, not prompt or retrieval efficacy. CaMeL, AgentDojo,
ToolEmu, Catala, Cedar, CompCert, and Clover remain unrun. If a later task
were to execute an external suite, that would require its own protocol, pins,
and receipt; it is outside LA-021.

## 5. Workshop fit

The NeurIPS 2026 Workshop on AI for Verifiable Coding [vericode2026cfp] asks
for research on making generated code checkable: proofs, tests, types, or
other independently checkable artifacts, in a 4–9 page anonymous research
paper using the official 2026 workshop template. The live CFP retrieved on
12 September 2026 lists runtime monitoring of agents, verified guardrails,
constrained tool use, and access-control policies among in-scope topics. This
paper's workshop-specific fit is runtime checking of generated-code effects
before a protected tool handler, with source-grounded constraints and a
separately checked admission. That is a verifiable-coding contribution even
when the check is a context-bound authorization receipt rather than a compiler
proof in Lean or Dafny.

Neighboring submissions in this campaign are distinct and must not be absorbed:

- Autoformalization with LLMs and LeanDojo-style proof retrieval
  [wu2022autoformalization, yang2023leandojo] concern source-to-proof
  training and theorem-prover artifacts. They are not this runtime route.
- Closed-loop verified generation [sun2024clover] concerns spec/proof repair
  loops, not MCP-handler mediation.
- Semantic program worlds, learned residuals, refactoring, parallel sealing,
  and proof-carrying test reuse are recorded as unavailable for this draft
  (review p8 §8; Appendix F) and stay future work. They belong to the
  neurosymbolic-supervision lane if anywhere, not to this paper's implemented
  contributions.

Page budget: the reconstructed main text was eight pages. Related work replaces
infrastructure-only citations with the comparison above without pretending that
every cited system was measured. The concise section is integrated in
`manuscript/main.tex`. This note retains the longer comparison for authors and
later LA-022 results reconciliation. Compiled main-text page count is recorded
in the LA-021 receipt.

## 6. What this comparison does not claim

- It does not claim superiority, SOTA, or "first neuro-symbolic MCP
  enforcement." Component ideas are old: reference monitors, proof-carrying
  code, executable law, capabilities, and agent-security benches all exist.
- It does not treat listing a system as benchmarking it.
- It does not treat legal compilation as a proof of legal correctness.
- It does not treat UCAN, CIDs, libp2p, or DuckDB/Quack as safety results.
- It does not treat default `OFF` or in-memory consumption as enforcement.
- It does not treat fixture/hermetic tests as empirical benchmark records.
- It does not claim complete mediation outside the selected route.

## 7. Citation metadata log

Verification status: primary identifiers were checked on 12 September 2026
against Crossref, arXiv abstract pages, the workshop CFP, and live
specification URLs. Operator review of AgentSpec, Progent, and CaMeL versioned
abstracts on 11 September 2026 is retained. Historical access dates copied from
the reconstructed bibliography are not new observations. The table below is a
record of those checks, not a record that each system was executed.

Corrections made during this check:

- Cedar: inherited DOI `10.1145/3649817` is Cocoon, a different PACMPL OOPSLA1
  2024 paper. Correct Cedar DOI is `10.1145/3649835` (pages 670–697). Inherited
  eprint `2403.04623` is a different arXiv record; Cedar extended version is
  `2403.04651`.
- Hamlen et al.: inherited DOI `10.1145/1111596.1111603` does not resolve.
  Correct TOPLAS DOI is `10.1145/1111596.1111601`.
- Clover: inherited TU Wien DOI `10.34727/2024/isbn.978-3-85448-065-5_27`
  resolves to a different FMCAD 2024 paper. Clover is cited from arXiv
  `2310.17807` only.
- MCP authorization: the reconstructed paraphrase "application implementations
  remain responsible for enforcing security requirements" is not a verbatim
  quotation of the live 2025-11-25 authorization page. That page specifies
  OAuth 2.1 resource-server roles and OAuth 2.1 security considerations.

| Key | Primary identifier | Notes |
| --- | --- | --- |
| mcp, mcp-auth | specification URLs, rev. 2025-11-25 | Retained; historical access 6 September 2026; live retrieval 12 September 2026 |
| catala | doi:10.1145/3473582 | PACMPL ICFP 2021; Crossref pages 1–29, article-number pagination retained |
| cvefixes | doi:10.1145/3475960.3475985 | PROMISE 2021, pages 30–39 |
| quack, ipfs, libp2p, ucan | specification/documentation URLs | Infrastructure; not closest systems; live titles confirmed 12 September 2026 |
| saltzer1975protection | doi:10.1109/PROC.1975.9939 | Proc. IEEE 63(9):1278–1308 |
| necula1997pcc | doi:10.1145/263699.263712 | POPL 1997, pp. 106–119 |
| appel1999pca | doi:10.1145/319709.319718 | CCS 1999, pp. 52–62 |
| schneider2000enforceable | doi:10.1145/353323.353382 | TISSEC 3(1):30–50 |
| erlingsson2000irm | doi:10.1109/SECPRI.2000.848461 | IEEE S&P 2000, pp. 246–255 |
| ligatti2005edit | doi:10.1007/s10207-004-0046-8 | IJIS 4(1–2):2–16 |
| hamlen2006enforcement | doi:10.1145/1111596.1111601 | TOPLAS 28(1):175–205; corrected DOI |
| pnueli1998translation | doi:10.1007/BFb0054170 | TACAS 1998, LNCS 1384, pp. 151–166 |
| sergot1986bna | doi:10.1145/5689.5920 | CACM 29(5):370–386 |
| prakken2015lawlogic | doi:10.1016/j.artint.2015.06.005 | AI 227:214–245 |
| benzmueller2020logikey | doi:10.1016/j.artint.2020.103348 | AI 287:103348 |
| merigoux2021tax | doi:10.1145/3446804.3446850 | CC 2021, pp. 71–82 |
| miller2006robust | Johns Hopkins PhD, 2006 | No DOI used |
| birgisson2014macaroons | doi:10.14722/ndss.2014.23212 | NDSS 2014 |
| pang2019zanzibar | USENIX ATC 2019, pp. 33–46 | Official proceedings URL recorded |
| cutler2024cedar | doi:10.1145/3649835; arXiv:2403.04651 | PACMPL 8(OOPSLA1):670–697; corrected identifiers |
| leroy2009compcert | doi:10.1145/1538788.1538814 | CACM 52(7):107–115 |
| chen2021codex | arXiv:2107.03374 | Submitted 7 July 2021 |
| jimenez2024swebench | ICLR 2024; arXiv:2310.06770; OpenReview VTF8yNQM66 | OpenReview API 403 on 12 September 2026; arXiv abstract retrieved |
| sun2024clover | arXiv:2310.17807 | Submitted 26 October 2023; false FMCAD DOI removed |
| yang2023leandojo | doi:10.52202/075280-0944 | NeurIPS 36, pp. 21573–21612 |
| wu2022autoformalization | doi:10.52202/068431-2344; arXiv:2205.12615 | NeurIPS 35, pp. 32353–32368 |
| debenedetti2024agentdojo | doi:10.52202/079017-2636; arXiv:2406.13352 | NeurIPS 37, pp. 82895–82920 |
| ruan2024toolemu | ICLR 2024; arXiv:2309.15817 | Submitted 25 September 2023 |
| zhan2024injecagent | doi:10.18653/v1/2024.findings-acl.624; arXiv:2403.02691 | ACL Findings 2024, pp. 10471–10506 |
| yao2024taubench | arXiv:2406.12045 | Submitted 17 June 2024 |
| andriushchenko2025agentharm | ICLR 2025; arXiv:2410.09024 | Submitted 11 October 2024 |
| debenedetti2025camel | arXiv:2503.18813v2 | Version 2, 24 June 2025; not benchmarked here |
| wang2025agentspec | arXiv:2503.18666v3 | Version 3, 31 July 2025; not benchmarked here |
| shi2025progent | arXiv:2504.11703v3 | Version 3, 14 May 2026; not benchmarked here |
| vericode2026cfp | https://vericodegen.github.io/cfp.html | Retrieved 12 September 2026 |

## 8. Related-work section integrated in `manuscript/main.tex`

The concise workshop section is in `manuscript/main.tex` (`sec:related`). It
is a literature comparison on the selected `ENFORCE` question. No listed
external system is a run baseline. LA-022 later reconciles this section with
actual results.
