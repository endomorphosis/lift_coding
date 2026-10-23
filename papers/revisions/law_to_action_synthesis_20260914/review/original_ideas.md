# Original-ideas recovery review: Law to Action

Reviewed 2026-09-14 UTC. Read all 17 printed pages of the original paper, including references and appendices, and compared the revision's `main.tex`, `results.tex`, `limitations.tex`, `appendices.tex`, and `evaluation_details.tex`. Page references below refer to the **original PDF's printed page numbers**. No manuscript edits, experiments, runtime actions, or external citation verification were performed for this review. External bibliographic checking is a separate part of the parent review.

The original's strongest recoverable idea is a **compiler-and-runtime pipeline that keeps source interpretation, formal evidence, delegated authority, and observed effects distinct**. The current paper accurately reports the bounded experiment, but its main text compresses this pipeline into a comparatively generic enforcement wrapper. Restore approximately 1.5–2 pages of mechanism and a short future-work paragraph. Retain the new empirical boundaries and results unchanged.

## What should return, and on what evidence

“Design” below means described by the original implementation inspection, not newly established by this review. Before calling an optional path implemented in the current artifact, connect it to the retained implementation mapping or qualify it as an architectural interface. A definition or registered representation alone does not establish an executed backend.

| Priority and idea | Original evidence | Present revision | Recommended treatment and evidential boundary |
|---|---|---|---|
| **High: IR, logic, and prover are different layers** | §3.1, pp4–5; Appendix B, pp12–13 | Appendix `app:logic` preserves much of the distinction; the main text mainly names QF_BOOL | Promote the distinction into a short main-text subsection. Explain why normative force, temporal scope, entity relations, and agent attitudes cannot be flattened without declared losses. Use four representative roles rather than another long backend catalog. The scored route remains QF_BOOL only. |
| **High: typed proof workflow and evidence acceptance** | §3.2, p5; §4.2, pp5–6; Appendix B.2, p13 | Evidence kinds and unavailable backends survive, but job construction, checked translation, reconstruction, and compatible-result selection largely disappear | Restore the sequence: typed obligation → supported encoding → bounded backend run → independent checking/reconstruction where required → typed receipt. Distinguish satisfiability, policy decisions, monitor observations, and theorem evidence. No universal assurance ordering and no claim that SAT evidence meets a theorem requirement. |
| **High: per-action jobs and hard admission** | §4.1–4.2, p5, lines176–194 | Main text says every required constraint must pass, without explaining the required job population | Name applicability, positive grant, nonconflict, security invariant, pre-obligation, coverage, and context binding as architectural job roles. Explain that coverage is relative to the declared modeled scope. Use a compact admission equation; do not imply that every role was independently exercised in each scored cell. |
| **High: decision-to-use binding and three distinct milestones** | §4.3, p6, lines202–213; §6.3, p7; Appendix C.4, p14 | Invocation and consumption are present, but the separate plan/permit/completion distinction is faint | Explain that plan admission, a current execution permit, and observed completion answer different questions. Bind actor/audience, tool/version, arguments/effects, roots, time, and use state at the protected boundary. Tie the explanation to the new A3 replay/context-change failures and A4 results, without attributing the improvement to a single component. |
| **High: current state is host-controlled and invalidates old evidence** | §5, p6, lines226–242; Appendix C.2, p14 | Revision/fence/idempotency appear mainly in an appendix table; event-driven invalidation and reuse are absent | Restore a paragraph on short typed transactions, exact command identity after lost replies, stale-fence rejection, and rechecking dependencies after relevant root changes. Separate qualified durable-consumption behavior from the wider incremental-reuse architecture. No exactly-once claim for remote effects. |
| **High: learned proposals remain separate from checked acceptance** | §3.2, p5, lines164–169; Appendix B.2, p13, lines462–467; Appendix F, pp16–17 | Main text accurately says no trained encoder was used, but the architectural role of learning is lost | Restore one explanatory paragraph: a model can nominate an IR, premises, tactics, or a repair; it cannot change the evidence type or remove an obligation. Structural equality, entailment, equivalence, equisatisfiability, and similarity are different contracts. Learned methods were not evaluated here. |
| **Medium/high: task-specific ContextPacks and semantic minification** | §2.4, p4, lines126–130; §6.1, p7; Appendix F, pp16–17 | Retrieval remains in an infrastructure row; ContextPacks, local aliases, and semantic minification are absent | Give a clearly labeled extension/future-work paragraph. Bounded retrieval is an architectural mechanism; preservation of all required source maps, obligations, dependencies, and current roots is a condition for any proposed minification. Do not claim checked semantic preservation, token savings, or an evaluated learned compressor. |
| **Medium/high: intent-side and independently derived effect-side correlation** | §2.2, p3, lines91–95; Appendix A.2, p11; worked trace p8 | General effect binding remains; the two-stream correlation mechanism is mostly absent | Explain the reason for correlating declared intent with code/handler facts under one Security IR root: harmless text must not conceal a broader effect. In the measured study, the handler accepts declarative instructions and effects are independently observed; generated-code extraction and CVE transfer remain unmeasured. |
| **Medium: source interpretation includes loss and uncertainty, not only seven fields** | §2.1, p2, lines61–69; Appendix A.1, pp10–11 | The restricted compiler and loss diagnostics remain; the rich bridge and explicit unsupported-facet retention are compressed | Add a sentence that unsupported definitions, exceptions, temporal meanings, or competing interpretations remain explicit and block uses that require them. A rich representation and a restricted executable view can coexist with a declared relationship. Do not imply legal correctness from source-span linkage. |
| **Medium: rejection witnesses support local replanning** | §4.1, p5, lines181–187; §7, p8, lines306–313; Appendix B.2, p13 | The runtime rejects, but the feedback to a proposing agent is largely absent | Restore one sentence about affected actions and failed obligations being returned for revision. Distinguish this interface from an observed planning improvement: the closed-loop study was not executed. |
| **Medium: immutable declaration, run, result, and receipt separation** | §2.4, p3, lines121–125; Appendix A.4, p12 | Identity/provenance are present, but declaration immutability across prover runs is not explained | One sentence plus an architecture arrow is enough: new checking evidence does not rewrite the norm or skill declaration it evaluates. This gives a concrete role to content addressing and supports traceability without implying truth or public availability. |
| **Medium: record identity differs from packaging identity** | §2.3, p3, lines104–109; Appendix A.3, p11 | The source cohort and container distinction remain, but entry/body/container identities are missing | Keep in the appendix or a short lineage caption. An intrinsic record can retain identity across repackaging while exact body and container provenance stay independently traceable. Avoid reintroducing large unverified inventory counts into the main text. |
| **Medium: distributed evidence access without shared state authority** | §6.1–6.4, pp7–8; Appendix C, pp13–14 | Current infrastructure appendix retains the basic roles | Promote at most two sentences alongside the architecture diagram: IPFS identifies artifacts, libp2p carries exchanges, UCAN bounds delegation, and the typed owner controls mutable state. These are complementary roles, not four independent safety findings. Network/publication claims remain limited to the actual local qualification. |
| **Low: detailed solver/tool registry and MCP++ profile catalog** | §3.2, p5; §6.4, pp7–8 | Compressed or omitted | Keep the detailed lists in appendices. Naming every backend or A–G profile would consume space without strengthening the measured claim. Preserve distinctions between the auxiliary policy gate, full enforcement wrapper, and other routes. |
| **Future work only: program worlds, learned transition residuals, refactoring, parallel sealing, proof-carrying test reuse** | Appendix F, p16, lines535–540 | Absent | Do not restore as implemented contributions. The original explicitly states that the uncommitted implementation bytes were unavailable and that these were ongoing extensions. One optional sentence is sufficient; omission is preferable to overclaiming. |

## Suggested integrated main text: approximately 7.4 pages

The budgets include tables/figures and are planning estimates, not compiled page measurements. Preserve the official template and normal font/spacing; revise placement rather than compressing typography to reach a target.

| Section | Approximate pages | Content |
|---|---:|---|
| Title, abstract, introduction | 0.90 | Distinguish source interpretation from action authority; state the bounded measured contribution early. |
| Related work | 0.70 | Keep the verified relevant comparisons, with direct positioning against runtime monitors, capability systems, executable law, and checked translation. Avoid expanding this section to carry the method. |
| Sources and typed representations | 1.05 | Current three-stream table and sample boundaries; add source maps/losses, independent effect correlation, and declaration/result separation. |
| Typed obligations and checked evidence | 1.10 | Four illustrative logic roles; proof workflow; admission equation; learned-proposal/checked-acceptance boundary. |
| Context-bound execution and state | 1.30 | Invocation tuple, current-root validation, capability and consumption, trusted typed owner, concise worked example, architecture figure. |
| Evaluation | 1.65 | Keep the final-split and full-population results, family-level inference, source-contract qualifications, and compact operational accounting. Use appendices for backend inventories and diagnostic details. |
| Limitations and extensions | 0.55 | Current scientific limits plus ContextPacks/minification and unexecuted closed-loop work. |
| Conclusion | 0.15 | State the measured action-boundary result and the broader pipeline's separate validation needs. |
| **Total** | **7.40** | Leaves modest layout margin below nine main-text pages. |

The central narrative should be: **three kinds of source information → obligations for one action → evidence accepted under an explicit contract → a fresh capability/consumption decision → an independently observed effect**. Present the 900-cell experiment as a test of the last part of this architecture, with structural source checks and qualifications clearly identified alongside it. Do not imply that the experiment validates the semantic compilation of law or the whole multi-logic architecture.

## Ready-to-adapt paragraphs

### 1. Representation and logic have different jobs

Placement: after the three-source subsection, before the runtime. Original pp4–5 and12–13; current appendix `app:logic`.

> A domain IR records what was extracted and where it came from; a logical view gives those statements a declared interpretation; a backend checks an encoding within a supported fragment. These layers are kept separate. Frame relations describe entities and their attributes, deontic operators distinguish obligations from permissions and prohibitions, and temporal operators express validity and ordering. Cognitive and event representations can distinguish an agent's stated belief or intention from evidence about the world. Cross-view links and shared symbols do not, by themselves, prove that a translation preserves those meanings. The scored experiment uses only the propositional QF_BOOL route; the other views describe the broader architecture, not additional evaluated backends.

This recovers the motivation for multi-logic support without suggesting that combining names of logics constitutes verification. DCEC is mentioned in the current appendix introduction but lacks its own explanatory row; restore its **belief versus authenticated fact** distinction if space permits.

### 2. Proof work is a typed contract

Placement: same subsection. Original p5 and p13; current main constraint-checking paragraph and appendix evaluation evidence map.

> The authorization layer organizes checking around an action's required obligations. Each job identifies its premises, assumptions, target, logical fragment, resource bound, and required kind of evidence. A backend may return a model, a core, a proof candidate, or an inconclusive result; reconstruction and a declared checker supply additional evidence only where available. Policy approval, runtime observations, satisfiability results, and kernel-checked theorems retain separate types. In the evaluated route, SymPy DPLL and an independent truth-table checker establish agreement on the encoded propositional query. That evidence cannot satisfy a request whose contract requires a kernel-checked theorem.

Do not reintroduce “full proof-oriented enforcement” as the empirical arm label: A4's qualified SAT check is materially narrower than the original architecture's optional theorem-required route.

### 3. Learning proposes; the declared checker accepts

Placement: end of typed-evidence subsection. Original p5, lines164–169, and p13, lines462–467.

> Learned components may propose a normalization, a premise set, a tactic, or a revised plan. Acceptance remains governed by the declared checking contract. A similarity score cannot establish entailment, and an equisatisfiable encoding is not necessarily equivalent under every downstream use. The system therefore retains the source map, assumptions, translation relationship, checker identity, and result type rather than treating every successful model output as verified. Rejection witnesses identify affected actions and missing obligations so a proposing agent can revise them. This interface motivates a future closed-loop study; no trained normalizer, encoder, or model-guided replanning was evaluated here.

### 4. Current state is part of the decision

Placement: runtime subsection, directly before the results' explanation of replay/root changes. Original p6 and p14; current infrastructure and durable-state qualifications.

> An earlier decision is evidence about one invocation and one relevant state. Before delegation, the protected wrapper compares that binding with the host-controlled current actor, arguments, effects, policy roots, clock, and use state. Changed dependencies require renewed checking. The operational owner accepts typed commands with revision, generation, fence, and idempotency bindings; after a lost reply, an identical command can retrieve its committed result, while a different payload or stale authority must not be treated as the same operation. This separates an admitted plan from a current execution permit and separates both from observed completion. Durable consumption qualifies the selected local boundary; it does not make arbitrary remote effects exactly once.

The broader event-driven dependency invalidation mechanism can be described as design. The existing development cold/warm/stale measurements and 14-case durable-state qualification have narrower scope; do not turn them into a causal study of general proof reuse.

### 5. Context construction and semantic minification

Placement: limitations/extensions, with a short main-method pointer if needed. Original p4, p7, and pp16–17.

> A further extension is to build task-specific ContextPacks from content-addressed source and proof dependencies instead of repeatedly sending full collections. Local aliases can shorten references while preserving a map to the original objects. Any proposed semantic minification must retain the required obligations, source mappings, unsupported facets, and current-root dependencies; retrieval relevance or embedding similarity cannot certify that an omitted constraint is irrelevant. The present study does not evaluate such a compressor. A separate evaluation would report context size and token use, compilation and checking overhead, invalidation behavior, and authorized task utility, rather than equating shorter prompts with lower total cost.

This should not be phrased as an existing checked semantic-preservation guarantee. The original identifies it as an ongoing extension.

### 6. A concrete action example

Placement: runtime section, ideally paired with the diagram. Original p8 is explicitly a composition walkthrough; the current Appendix D supplies a **separate diagnostic replay**.

> Consider a procedure that requests a JSON export. Its Intent IR records the selected data, destination, proposed effect, prerequisites, and expected verification. Source-derived legal or security restrictions enter only when their applicability and required evidence are established. An acceptable constraint result still leaves a separate question: whether the current principal has authority for this exact export. Changing the recipient invalidates the invocation binding; replaying a consumed request fails the use-state check. The measured study instantiates this action boundary with declarative instructions and an independent filesystem journal. The worked diagnostic trace exposes intermediate checks but contributes no additional scored trials.

Avoid saying that the concrete measured skill trace invoked the legal compiler: the current Appendix D explicitly identifies the skill adapter. Likewise, do not present independent code-effect extraction as part of this declarative-handler experiment.

## Optional notation and diagram

Use one equation block rather than a claimed theorem. These are proposed explanatory definitions, **not machine-checked results or a transcription of an original equation**.

Let an invocation be

\[
x=(u,a,v,h_{\mathrm{args}},h_{\mathrm{effects}},R,n),
\]

where \(u\) identifies actor/audience, \(a,v\) the tool and version, \(R\) the relevant policy/source/environment roots, and \(n\) the use identity. Let \(J(x)\) be the mandatory obligations selected for the declared modeled scope. Then describe evidence admission as

\[
\mathrm{Admit}(x,E)
=\mathrm{ScopeResolved}(x)\;\land\;
\bigwedge_{j\in J(x)}
\left[\mathrm{Checked}(e_j,j,x)\land
\mathrm{MeetsContract}(\mathrm{kind}(e_j),\rho_j)\right].
\]

Here `MeetsContract` is an explicit compatibility check, **not** a numeric ranking of SAT, policy, monitor, and theorem evidence. Missing evidence, unresolved obligations, or unsupported required facets make this admission condition false. For a permit to proceed toward delegation, separately require

\[
\mathrm{Admit}(x,E)\land\mathrm{CurrentBinding}(x,s_t)
\land\mathrm{CapabilityOK}(x,s_t)
\land\mathrm{ConsumeCommitted}(n,s_t).
\]

State in prose that this describes the selected guarded path and its trusted adapters. It is not a sufficient condition for semantic legal correctness, universal mediation, successful completion, or exactly-once remote effects.

A compact editable architecture figure can follow this topology:

```text
Legal sources ──> Legal IR ─┐
CVE/fix records > Security IR├─> applicable constraints + exact invocation
Skill Markdown > Intent IR ─┘                 │
       source maps / losses / identities      ▼
                                  typed obligations + evidence checks
                                               │ decision receipt
learned proposals ───── nominate ───────────────┘
                                               ▼
host current state + signed capability ──> revalidate + consume
                                               │
                                               ▼
                                     protected handler ──> observed effect
```

Caption should explicitly distinguish broader architecture from evaluated scope. Shade or annotate the selected QF_BOOL check, explicit ENFORCE export boundary, capability verification, durable consumption, and effect journal as the measured/qualified path. Do not shade the entire legal-semantic or learned-proposal pipeline as empirically validated. Keep DuckDB/Quack, IPFS, and libp2p as supporting labels or a small legend, not a second full architecture.

## Claims that should stay narrow

- Preserve the final split: A4 forbidden effects **0/54**, allowed useful work **54/54**; A3 forbidden effects **18/54**. All splits remain **900** scored cells across **30** families, with **0/90**, **90/90**, and **33/90** in the corresponding A4/A3 counts. The repeated seeds are not independent families.
- A1/A2 are inert model-free controls, not measurements of prompt or retrieval effectiveness. There were no scientific model calls or generated programs.
- Legal source linkage, grammar validity, and machine-contract coverage do not establish semantic legal applicability or exception fidelity. The SkillCenter comparison is shared-producer conformance, not independent expert agreement.
- CVE source differences do not establish vulnerability polarity or transfer to the export handler. Preserve the unknown/unsupported findings.
- The richer theorem, temporal, cognitive, interpolation, and learned routes must not inherit the QF_BOOL result. An unavailable backend is not a negative theorem result.
- Current A3–A4 comparisons change several mechanisms together. They support the complete measured configuration, not component-level causal attribution. Unadmitted ablation/diagnostic records must remain outside the scored rates.
- Neither immutable content identity, peer authentication, signed delegation, nor a database commit alone proves legal safety. The original's layered distinctions are an explanatory strength worth preserving.
- Do not restore the original “evaluation remains to be completed” wording wholesale. Replace it with the actual measured/unmeasured split now available. Conversely, do not add a new human-review requirement or imply that author portal attestations have already occurred.

## Source commitments

Hashes recorded at 2026-09-14T03:17:28Z. The parent may subsequently edit the revision; these pins identify the comparison inputs, not the eventual merged revision.

| Input | SHA-256 |
|---|---|
| `papers/from_law_to_action_corpus_grounded-1.pdf` | `000b0d1960854966be836788f05c1fe33b8c0c6a2943a8d88f20241f99b38da0` |
| `review/original.txt` | `7ba3ca062ada2271540676831842f095769a6feb085d2290ba96b26fa7182541` |
| `manuscript/main.tex` | `cfc205cf5bd8afa8d1b5e1678e8798ee6118a4eb8c92080a9265758d91e763ec` |
| `manuscript/results.tex` | `09c126580b76900e1ccd933379518a11862bd5269e1237ec7adbf6c565e86fdd` |
| `manuscript/limitations.tex` | `0f7d4ca2268ebe0b2e2fc883eb74a85cb06ad46209e01ccc2387d05c7eb41faf` |
| `manuscript/appendices.tex` | `6b297f611820a944b673022fa6d6f79ef50170640839e787a5da98fd5b88b20f` |
| `manuscript/evaluation_details.tex` | `ab3ab9d0be9dd280665b888ec0baadb7c2676fd43d1c3740ca46d135ae4af892` |

Relative paths in this table are under `papers/revisions/law_to_action_synthesis_20260914/`, except the original PDF. The extracted text includes one trailing empty form-feed segment; the reviewed original has 17 substantive pages, not 18.
