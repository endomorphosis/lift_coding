# Proof-Carrying Neurosymbolic Supervision: State, Reasoning, and Evidence Reuse

> Reconstructed local reading view, created after the operator requested a new package. This is not the missing supplied v2 revision package. It uses only retained increment-016; its relationship to the originally supplied named PDF is unverified. Historical claims are transcribed, not newly authenticated or rerun.

The selected [PDF](../source_reference/main.pdf) and [LaTeX source snapshot](../source_reference/source_snapshot/main.tex) are preserved separately. The first part below is the exact `pdftotext -layout` reading view with page boundaries and original line numbers. PDF extraction can alter mathematical glyphs, ligatures, table layout, and hyphenation; do not use that text to reconstruct equations. The second part preserves the mathematical LaTeX expressions in an ordered source assembly. Original individual file bytes, not the inserted boundary comments, remain authoritative.

The main body occupies PDF pages 1–10; References occupies page 11. This observed main-text span exceeds the requested nine-page limit. No new build or style-conformance check was performed.

## PDF reading view: main body and references

### PDF page 1

````text
               Proof-Carrying Neurosymbolic Supervision:
                  State, Reasoning, and Evidence Reuse


                                                  Anonymous Author(s)
                                                      Affiliation
                                                       Address
                                                        email



                                                         Abstract

 1             Coding agents repeatedly reconstruct repository context, reason about changes,
 2             and validate results. We study an obligation-centered supervision architecture
 3             that retains source-linked semantic state, routes supported obligations through
 4             checked symbolic mechanisms, and uses neural proposals for unresolved work.
 5             Evidence applicability governs validation reuse and accepted-state publication.
 6             The empirical question is whether their combined startup and operating costs
 7             reduce neural work and validation effort while preserving useful progress. We
 8             evaluate context substitution, avoided model calls, persistent planning, validation
 9             reuse and native proof consumption as distinct mechanisms, retaining an earlier
10             additive-context cold-repair study as separate evidence. On four constructed tasks,
11             symbolic repair and residual routing pass the same independent checks as a model-
12             first baseline with 2,430 versus 4,865 provider tokens. This 50.05% reduction is
13             confined to that development suite. Other experiments exercise lifecycle-preserving
14             reuse, memory consumption, publication, crash recovery and proofs over actual
15             saved state. Simple retrieval matches memory’s action reduction, and measured
16             reuse savings do not recover priming cost over five repetitions. In two development
17             comparisons on one natural two-issue repository sequence, every arm accepts one
18             issue and none completes the trajectory. These mixed findings establish bounded
19             capabilities and implementation limitations. Complete integrated token savings
20             remain open; component percentages cannot be combined into a system estimate.


21   1    Problem and contribution

22   The cost of a coding agent includes repeated repository discovery, specification interpretation,
23   planning, repair, validation, and recovery. Persistent state can avoid some of this work only when the
24   state remains applicable to the current program. A shorter prompt can omit necessary dependencies; a
25   cached pass can refer to obsolete source. Repository-agent interfaces and test-validation benchmarks
26   make this boundary between proposals and checks central to useful repair [13, 5].
27   Our proposed method has three connected contributions. First, source and intent produce identity-
28   bound semantic facts and explicit unresolved obligations. Second, those obligations guide determinis-
29   tic analysis, checked reasoning and bounded synthesis before an authorized neural residual. Third,
30   validation, evidence reuse and accepted-state publication preserve the scope and applicability of each
31   observation. Accepted changes invalidate affected facts and plans, providing the next iteration with
32   persistent, current evidence.
33   The resulting hypothesis concerns the entire workflow: repeated neural reasoning and validation may
34   be displaced by persistent, checked work. Context compression is one possible mechanism. Fewer
35   model calls and less replanning are distinct mechanisms, while test reuse primarily reduces validation

     Submitted to NeurIPS 2026 Workshop on AI for Verifiable Coding. Do not distribute.

````

### PDF page 2

````text
36   computation. Each requires its own correctness and cost comparison. No benefit follows merely from
37   having a symbolic component in the source tree.
38   We retain an earlier additive-context cold-repair study as one bounded experiment, then evaluate miss-
39   ing mechanisms incrementally. Architecture, local qualification, development pilots and confirmatory
40   effectiveness have different evidential roles. A failed or inconclusive experiment remains a result;
41   an unrun comparison remains an open research obligation. In particular, the original 32 cold cells
42   cannot establish the value of persistent reasoning or whole-system token savings.


43   2   The supervision loop

44   Compile state and obligations. The semantic index extracts source-linked symbols, dependencies,
45   contracts and analysis limits. Intent supplies candidate goals and permitted effects; formalization
46   produces bounded obligations without turning an inferred specification into authority. Semantic
47   state is separate from operational task state and artifact storage. Missing dependencies, dynamic
48   features and lossy translations remain an explicit unknown frontier that requires more source, broader
49   checking or abstention.

50   Reason before proposing. For each obligation, the intended supervisor considers applicable
51   evidence or procedures, exact dependency and static analysis, contract/solver checks, and bounded
52   deterministic repair or synthesis. A neural model proposes unresolved work through a permitted
53   residual route. Abstract interpretation, translation validation and counterexample-guided methods
54   provide established foundations; the contribution is their composition at the supervisor’s decision
55   boundary, not a new general-purpose prover [2, 1, 10, 12]. The evaluation must demonstrate that a
56   computed result changes the next actual action and passes independent checks. A route label or a
57   candidate’s assertion that it closes a claim is insufficient.

58   Validate, reuse and publish. Candidate edits are checked against the current source and required
59   acceptance conditions. Evidence reuse requires matching subjects, dependency and environment
60   identities, declared checker semantics and trust policy. For fixture-based tests, collection and
61   materialized setup state must be resolved before call-phase reuse; required setup and teardown effects
62   still run, and teardown failure prevents whole-item success. A complete accepted-transition manifest
63   binds the current parent and applicable evidence before publication. Restart reconciliation must
64   support valid continuation as well as rejection of stale work.

65   Persist, invalidate and replan. An accepted transition updates the state used by the next task.
66   Source, dependency, fixture, policy and capability changes invalidate affected evidence and reopen
67   obligations. Procedural memory can nominate previously useful actions, but applicability and
68   independent validation remain necessary. Learned world models and procedure discovery require
69   held-out downstream evaluation; their source presence does not establish generalization. The intended
70   savings appear over trajectories of tasks, so a single cold proposal is an incomplete test of this
71   architecture.

72   Separate resource hypotheses.      For a fixed workload of N tasks and arm a, let
                                                                ∑︂
                                       Ta (N ) = Tsetup,a +               Tj ,
                                                              j∈Ca (N )


73   where Ca (N ) contains every workflow model call, including planning, formalization, proposals,
74   review, failed attempts, retries and recovery. Provider-reported totals are preserved without adding
75   overlapping cached or reasoning-token fields. Unknown usage remains unknown. The reduction
76   1−Tsystem (N )/Tbaseline (N ) is meaningful only for matched workloads with adequate independently
77   measured progress and comparable complete accounting. Report setup and priming at explicit reuse
78   horizons; provider charges, host computation and elapsed time are separate quantities. Independent
79   experimental oracle work is reported separately from each arm’s runtime validation, without hiding
80   mandatory runtime costs.


                                                       2

````

### PDF page 3

````text
 81   3   Method and trusted assumptions
 82   Separate evidence classes. Semantic state links facts, dependencies, contracts, and unresolved
 83   obligations to source. Operational state records goals, tasks, attempts, leases, and decisions. Artifact
 84   storage preserves candidate bytes and accepted manifests. An evidence item binds a subject to a
 85   declared statement, checker, environment, and provenance. A passing test concerns the finite checks
 86   actually executed; a formal derivation concerns its encoded relation and premises; a grant concerns
 87   an actor’s permission to act now. These classes cannot substitute for one another. In particular, a
 88   signature binds a record to a key under cryptographic assumptions. It establishes neither checker
 89   adequacy nor the honesty of an observation.

 90   Applicable evidence. The intended loop derives obligations from current source, chooses an
 91   admissible analysis or proposal route, checks an isolated candidate, and admits only evidence
 92   applicable to that candidate. Translation validation motivates checking a particular conversion against
 93   its stated relation [10]; a source-linked record alone is not such validation. Abstract facts likewise
 94   depend on an approximation relation [2]. A typed or content-addressed representation does not imply
 95   full source-language soundness.

 96   Conditional acceptance and reuse. If publication succeeds only after checking the current parent,
 97   authorized scope, complete requirement manifest, admitted evidence, and expected-parent compare-
 98   and-swap, each successful successor satisfies those gates. Given a valid initial root and exclusive
 99   use of that publication operation, induction preserves the declared manifest policy. This does not
100   establish enforcement by unexamined write paths or atomicity of external effects.
101   For test reuse, suppose the observation of test t under profile θ factors through a complete dependency
102   projection:
                                             Obsθ (t, s) = fθ (πD (s)).
103   If fθ is deterministic on every admitted state, equal projections imply equal observations. Com-
104   pleteness and determinism are substantive premises; hashing an incomplete dependency list, opaque
105   fixture, or uncontrolled effect does not discharge them. Appendix A preserves the full conditional,
106   unmachine-checked statements and the distinction between behavioral acceptance, action permission,
107   and publication.

108   Executed scope. The historical cold comparison exercises native context preparation, model
109   proposals, candidate custody and AI inspection, and separate cold scoring. Earlier constructed
110   controls and a local guard-before-write witness test named implementation boundaries; they do not
111   establish that the complete intended loop ran as a live benchmark. Its original proof profile lacks the
112   admitted backend, key provenance, and exact statement binding required for native proof admission.
113   New development profiles and their measured results are reported separately in Section 6; neither
114   native proving performance nor empirical reuse benefit is inferred from the conditional arguments.

115   4   Historical component-study design
116   The retained cold study compares raw selected public context (A) with the same raw selection plus
117   native source-linked semantic context (B). Eight convenience-selected Python repository families and
118   two nested repetitions per arm yield 32 fixed cells. Sixteen family/arm request commitments precede
119   final generation. The treatment is additive and cannot isolate context compression. The retained
120   A/B cells form an order-preserving subset of a later 192-cell plan; 160 factor cells were withdrawn
121   and eight additional target families were not recruited. These missing comparisons remain separate
122   research obligations.
123   Each cell permits one Grok 4.6 proposal, requesting at most 4,096 output tokens, with no model
124   retry, scientific fallback or served random seed. The nominal gateway bound is 600 seconds; actual
125   measured compliance governs useful credit. Eligible candidates undergo separate cold, network-
126   disabled public and hidden scoring. Useful completion requires admission, nonempty passing checks
127   and measured resource compliance. Failed, expired, unscored and incompletely validated cells
128   remain in the denominator. Separate scoring alone does not establish resistance to arbitrary candidate
129   interference.


                                                         3

````

### PDF page 4

````text
130   The analysis averages repetitions within each family and then contrasts B with A across eight family
131   blocks. A prespecified 20,000-resample paired family bootstrap provides a conditional descriptive
132   interval, without a population superiority or noninferiority claim. Model, scorer and wrapper clocks
133   may overlap and are not added as disjoint costs; unavailable usage remains unknown. The separate
134   four-family pilot and earlier qualification controls supply no additional final trials. Appendices B, C
135   and D retain the full design, interruption history, analysis recipe and accounting exceptions.

136   5   Historical cold-repair results
137   All 32 planned cells have verified terminal records. Nine yielded useful completion: A achieved
138   5/16 and B 4/16. The eight-family mean difference, B minus A, is −0.0625, with a descriptive
139   95% whole-family bootstrap interval of [−0.1875, 0]. Seven family differences are zero; Tornado
140   accounts for the aggregate difference. One B Tornado request ended in a transport failure. This
141   convenience sample supplies no population-level superiority or noninferiority conclusion and cannot
142   isolate semantic content from other features of the combined request.
143   The 23 non-useful cells comprise 14 proposal-child deadlines, two known proposal failures and seven
144   original hidden-failure labels. Six of the latter executed hidden checks and failed; one passed public
145   checks but collected zero hidden assertions due to an import error. It remains incomplete validation
146   with no useful credit. All failures remain in the fixed denominator. Sixteen scorer invocations include
147   this incomplete case; fifteen completed cold validation. Provider usage is available for only 16/32
148   cells, and the original experiment has no complete-cohort token or settled-charge total.
149   The developmental four-family pilot remains separate, with ten historical useful labels among 24 cells,
150   five per arm. Interruption, measured timing deviations, missing costs and reconstructed candidate
151   metadata are retained in Appendix D. Those records preserve the original outcomes and do not
152   provide additional scientific trials. The historical study supports an additive-context observation only;
153   it does not evaluate the whole-system reasoning and reuse hypothesis.

154   6   Incremental system evaluation
155   The following evaluations extend the original architecture questions. They are development mea-
156   surements and local qualification, separate from the historical cold experiment and from any future
157   confirmatory population. Their profiles and source versions are explicit; a partial combined controller
158   is qualified below, while the complete matched system comparison remains open.

159   Context substitution opportunity. We reconstructed all sixteen historical A/B request commit-
160   ments across eight unique families and checked the selected public source against its hashes. All
161   254 selected windows were protected editable or test source; there were zero eligible unchanged-
162   dependency files and zero substituted windows. The guarded substitution adapter therefore retained
163   the raw source. Saved native packets contained no explicit obligation CIDs and 14,471 unresolved
164   dependency-edge occurrences. Instruction text was retained, but this cohort cannot establish explicit
165   obligation preservation or dependency compression.
166   Using tiktoken 0.12.0 with o200k_base, exact tokenization of system/user message content totaled
167   91,783 for A, 107,870 for B, and 108,577 for guarded substitution C: increases of 17.53% and 18.30%
168   over A. These counts exclude chat-template overhead and output, and are not Grok provider usage. A
169   second named encoding gives the same direction. Eighteen constructed adapter controls separately
170   check expansion and rejection; they do not qualify a native producer. This result identifies a population
171   requirement: a compression experiment must include unchanged dependencies that can actually be
172   replaced under its stated policy.

173   Native dependency context and bounded projection. Three authored multi-module repositories
174   supply six fresh native exact dependency admissions. Twelve cold/incremental index and semantic-
175   bundle root comparisons agree; dependency edits invalidate prior capsules and unknown-call mu-
176   tations require raw fallback. Full transported native capsules total 8,399 serialized context-content
177   tokens versus 1,467 for raw source. A new restricted projection instead transports source-bound
178   integer equations. Six separate Z3 equivalence checks and 252 concrete source executions check that
179   projection; its 1,353 tokens are 7.77% below raw. Plain AST source compaction totals 1,464 tokens.


                                                         4

````

### PDF page 5

````text
180   These are named-encoding offline counts, not provider savings. The equation profile excludes floats,
181   custom objects, side effects and unsupported syntax. The compact projection is an evaluated addition;
182   the full native capsule payload itself is larger than raw source in these examples.

183   Repository context and preparation. Native repository custody, current-source expansion and
184   invalidation checks pass on bounded XML/pyparsing scopes and on both full declared Requests
185   inventories (97 files each); these profiles permit zero raw-source omissions. Five full pyparsing
186   producer processes reach their 600-second deadline. A subsequent immutable-state identity profile
187   completes full preparation in 566.254 seconds, followed by a passing independent native consumer;
188   all 302 XML/pyparsing regular files are retained and 22 negative controls pass. This establishes
189   completion under the bound in one shared-host run. Preparation is still substantial, and these profiles
190   establish no compression or replicated speedup. A subsequent full comment-change comparison
191   exposes 1,568 differing graph records. A rescanning guard restores byte equality but fails a later
192   import-inventory case. Preserving original frontend observations then gives exact full equality while
193   reusing 153 of 154 Python files. Incremental takes 607.971 seconds versus 440.276 cold, adds a
194   53.75 MB sidecar and incurs separately metered bootstrap costs. Useful incremental economics
195   remain open. Appendix G retains source scopes, identity checks, earlier failures and actual costs.

196   Live context substitution. The three dependency-bearing development repositories also support a
197   matched raw-versus-equation repair pilot. Both arms pass all three separate cold behavioral checks;
198   all six requests return usage. Provider input totals are 4,014 raw versus 3,817 compact (4.91% fewer),
199   and total usage is 4,866 versus 4,637 (4.71% fewer). Both arms use three requests with the same
200   Grok 4.6 low-effort profile and resource ceilings as the routing pilot. Cached-input totals differ,
201   so charge differences cannot be attributed solely to compaction. This tests a restricted, verified
202   representation on trivial constructed repairs; dynamic source expansion and broader repository quality
203   remain unmeasured. The result is separate from, and must not be added to, the routing reduction.

204   Checked symbolic closure and live residuals. A new development caller invokes the native Python
205   analyzer, bounded CEGIS repair, visible behavioral checks and native routing. Four constructed tasks
206   include false success without observation, swallowed backend failure, interval clamping and stable
207   deduplication. Both arms receive the same source, objective and public checks; separate Docker
208   execution scores broader behavioral checks. The first two defects fit the declared deterministic
209   grammar. The remaining two require the same model residual in both arms. Internal CEGIS marker
210   gates are not counted as theorem proofs; behavioral checks justify only these bounded obligations.

      Table 1: Constructed four-task routing development comparison. One observation per task and arm;
      no population inference.

          Arm                             Independently passed       Model calls    Total provider tokens
          Model first                                         4/4               4                    4,865
          Symbolic first plus residual                        4/4               2                    2,430

211   All six Grok 4.6 requests returned usage, under the same low-effort profile, max_tokens=2048
212   request parameter and 240-second deadline, without retries. The observed reduction is 50.05% on
213   this suite. Eliminating two requests accounts for 2,282 baseline tokens; response variation on the
214   residual tasks accounts for the remaining 153-token net difference. Provider cache state was not
215   controlled. There were no auxiliary workflow model calls or model-assisted setup in this caller;
216   experiment authoring and implementation effort are outside that runtime denominator. The initial
217   expired-credential attempt dispatched zero requests and remains a separate development record.
218   General repository performance and full-system setup amortization remain unmeasured.

219   Supplementary scorer validation. A post-development audit exposes five false admissions among
220   six crafted incorrect candidates in the original pilot scorers. Candidate interference with oracle helpers
221   or premature process termination could masquerade as passing execution. A new isolated scorer
222   separates the oracle from the candidate worker, restricts public dependency imports and requires
223   observed calls and positive completion. It rejects all six crafted candidates and all seven unrepaired
224   controls. All ten unique saved candidate bodies still pass, preserving the eight routing and six context


                                                          5

````

### PDF page 6

````text
225   record outcomes above. This supplementary rescore supports these saved outcomes; the small control
226   set does not establish general scorer robustness. Original scorers and observations remain retained.

227   Lifecycle-preserving test reuse. A proposed local evaluation adapter uses native cache admis-
228   sion and Ed25519 runner attestations issued only after actual passing setup/call/teardown. Its
229   explicitly enrolled pure workload and immutable fixture profile support valid call-phase reuse
230   while setup and teardown still execute. Fourteen prespecified cases cover unchanged work,
231   source/test/fixture/configuration/ environment mutations, missing or tampered evidence, revoca-
232   tion, unsupported fixture values and lifecycle failure. All fourteen match separate cold-process
233   outcomes. Reuse followed by failing teardown correctly fails the whole item; the result is not
234   zero-error evidence for arbitrary pytest programs.
235   Five alternating warm/cold timing pairs omit all five warm test-body executions while retaining five
236   setups and teardowns in each arm. Total host wall time was 1.281 seconds cold and 1.240 seconds
237   warm, excluding the separately recorded prime and issuance costs. This small descriptive difference
238   does not establish a reliable net speedup or token savings. The default production plugin probe
239   executed the body in both write and read/write modes and produced no positive reuse. Thus the result
240   qualifies the proposed bounded adapter, not deployment of the native default reuse path. Earlier failed
241   development invocations and the historical false-reuse observation remain retained. The measured
242   0.256-second cold prime and 0.006-second issuance exceed the observed wall-time saving over these
243   five repetitions; a net benefit at that horizon is not demonstrated.

244   Persistent work across process termination. Three actual processes exercise the native session
245   journal/checkpoint with the same checked deterministic caller. Duplicate pending notifications
246   coalesce. The first process exits abruptly after one completion; the next resumes exactly one unfinished
247   scan, and a third restart finds no pending work. Each actual execution passes the independent
248   behavioral oracle, and no original attempt executes twice. However, a fresh notification for a
249   completed snapshot schedules and executes analysis again. Journal continuity is supported by this
250   case; completed-result memoization, accepted-root publication and cross-task token savings are not
251   established.

252   Publication and recovery qualification. Forty-seven existing source-shipped tests pass in a fresh
253   compatible native profile. They cover immutable-root publication, stale writers, competing CAS
254   updates, seal storage and restart recovery at injected persistence boundaries. These are constructed
255   software qualifications, including placeholder proof records and exception-based interruptions. They
256   do not establish a newly integrated evidence-producing workflow, actual process-kill tolerance at
257   each boundary, or measured parallel-sealing savings.

258   Evidence-backed sealing and completed recovery. A new caller independently replays finite
259   computation receipts, checks exact source/input/policy bindings and complete coverage, then invokes
260   native integrity-only seal verification and publication. A full checkpoint and two delta seals become
261   successive current roots; a competing delta loses stale parent CAS. Four prepared states cover
262   700 independently checked state/input observations, using five computation subprocesses and three
263   unchanged-receipt reuses. Five constructed mutations reject. Native digest verification alone accepts
264   three internally consistent but semantically wrong or stale receipts; the caller’s independent replay
265   and bindings are therefore substantive gates.
266   Two real process terminations preserve the expected accepted roots. Native recovery recognizes
267   a valid pre-CAS seal but leaves its transition pending; retrying the same publication is refused. A
268   separately evaluated recovery caller rechecks the persisted evidence and completes native CAS/WAL
269   phases with zero new computation calls. A subsequent fresh process consumes that accepted root and
270   publishes the next changed state, reaching a four-seal chain. This establishes bounded continuation
271   under an explicit added caller. It does not establish native automatic recovery, theorem proofs,
272   power-loss tolerance or a compute saving: the independent receipt checker still runs on reuse. Four
273   paired trials separately compare actual preparation of two cold operations: all eight preparations pass
274   with identical receipt and seal content. Median preparation time is 63.21 ms sequential versus 32.10
275   ms parallel; maximum sampled aggregate process RSS rises from 44.66 to 55.54 MiB. The host is not
276   exclusive, sampled RSS counts shared pages per process, and these tiny preparation trials measure
277   neither publication latency nor a whole-system speedup.


                                                         6

````

### PDF page 7

````text
278   Procedure synthesis and stored candidates. A bounded native synthesis/body-store comparison
279   completes seven of eight units in both cold and stored arms: 3,883 correct fresh-query decisions, zero
280   false admissions and 554 abstentions on unsupported parity. Stored candidates require six synthesis
281   calls and 23 tried candidates versus eight and 29 cold, under exact source-catalog and policy bindings.
282   A separately frozen fixed-template control matches quality with no synthesis, so retrieval has no
283   demonstrated advantage over that simpler control. Fresh-process replay, binding mutations and
284   scaffold sensitivity are checked; this initial executor/store profile has no model calls. A later signed
285   native TEST integration executes the exact saved candidate on 136 new bounded inputs through all
286   six native handlers. All decisions match the oracle; 30 evidence negatives and 13 runtime controls
287   pass. Its 17.243-second worker cost plus preparation does not establish savings. Appendix J separates
288   this tested execution from repository applicability and promotion.

289   World-state memory and actual subsequent actions. A native typed transition producer, persistent
290   block/SQLite store and admission path are connected by a new evaluation dispatcher. Eleven tasks
291   per arm run in fresh interpreters against a closed three-action integer service; selected actions always
292   execute and their current outputs are independently checked. All 44 task/arm outcomes pass. Native
293   memory uses 16 action executions versus 27 without memory, but exact JSON retrieval and complete-
294   condition templates also use 16. Charging each arm the common three-action seed gives 19 versus
295   30. Changed state, source and declared environment invalidate prior observations; fallback creates
296   fresh evidence consumed by the next process. Native total process time is 8.947 seconds versus 8.739
297   without memory, including common import/storage work and excluding the separately recorded
298   shared seed. Thus fewer search attempts do not establish a wall-time advantage. The frozen dispatcher
299   uses retrieved typed records directly: an audit finds that the native compiler emits incorrect record
300   identifiers in all eleven compiled proposals, so compiler-mediated dispatch is not qualified by this
301   run. These results establish bounded storage/lookup consumption, not learned world-model benefit,
302   transfer, production integration or token savings. A separately frozen compiler correction selects each
303   record’s own identity. The ensuing consumer resolves compiler-selected records from the native store
304   before actual execution: the seed and eleven later cases pass, using 19 actions and 25 fresh service
305   processes. Changed source, state and environment still invalidate prior observations. Independent
306   checks preserve all original comparison artifacts. This qualifies the corrected compiler-mediated
307   path; it does not change the original simple-retrieval/template parity or supply learned transfer and
308   token-savings evidence.

309   Native compositional reasoning. An existing original-source vertical slice was run with its compat-
310   ible nested datasets tree. A baseline component contract discharged, an injected fault was refuted, and
311   repair restored discharge. Localization produced an UNSAT core and a cvc5 interpolant separately
312   checked by Z3; the final artifact was verified by semantic rescanning, composition redischarge and
313   test replay. Selected and full tests passed. Host elapsed time was 19.309 seconds. This is one existing
314   constructed fixture with a prescribed fault and expected repair, not a held-out synthesis experiment.
315   Internal benchmark estimates are not counted as measured token or compute savings. An earlier
316   source profile failed to import the required composition module and is preserved separately. Solver
317   validation does not imply kernel reconstruction or all-language correctness.

318   Native proof production and statement binding. The source-built native backend produces three
319   v3 Merkle/count proofs and three honest v2 implication-chain proofs. For v3, primary setup takes
320   7.810 seconds, proving 12.048–12.474 seconds and verification 3.053–5.147 milliseconds. Tested
321   malformed witnesses, proofs and keys reject. Both profiles require exact outer-statement checks
322   at the caller: the raw verifier can accept changed displayed metadata when its scalar public inputs
323   remain unchanged. These are measured bounded circuit relations, not proofs that arbitrary tests
324   executed or production trust admission. Stronger v2 textual-binding assurance remains unconfirmed,
325   and the v5 pytest-attestation profile is unsupported. Appendix I retains the separate profiles, mutation
326   observations and v2 costs. A subsequent native archive producer/consumer binds four actual accepted
327   controller events to one honest v3 proof, with seven mutation rejections. A second integration
328   consumes the actual accepted Requests repair, restores all 97 source files and rejects eight mutations.
329   Its 11.979-second proof and 5.256-millisecond verification are post-cohort overhead; original receipts
330   still supply execution evidence.

331   Combined controller and native publication. Constructed thirteen-event reasoning and eight-
332   event publication profiles join the actual native services and exercise real interruptions, native


                                                         7

````

### PDF page 8

````text
333   full/delta publication and fresh accepted-source consumption. A separate Requests curator fixture
334   measures 377.226 seconds of phases including full context preparation. These zero-provider controls
335   establish bounded continuation, not token savings. Appendix H retains their complete costs, failures
336   and unsigned integrity-only trust boundary.

337   Natural two-issue comparisons. Two frozen Requests 5414-to-6028 development cohorts compare
338   four arms with equal public access and four-call trajectory ceilings. Every arm in each cohort accepts
339   the first issue and fails the second. First requests within each cohort are byte-identical; B permits
340   no source omission, while C/D establish no successful symbolic closure. Partial D publishes and
341   retrieves accepted source. The first cohort’s A/C/D continuations exceed their source bound; B spends
342   its remaining calls on failed candidates. A new conflict-first retriever keeps required source within
343   the same bounds in the second cohort. All sixteen calls then execute, including expansion requests
344   and three outputs rejected by a file-mode transport defect. Table 2 retains both cohorts separately. In
345   the second, B/C/D use 10.43%/12.01%/7.77% more tokens than A at the same observed acceptance
346   count. Uncontrolled server caching, one exposed family and adaptive follow-up preclude causal
347   component or general efficiency claims. Complete-trajectory cost ratios remain undefined.

      Table 2: Natural Requests cold development cohorts, retained separately. Every arm accepts 1/2
      nodes and completes 0/1 trajectories in each cohort. Second-cohort wall includes nested services;
      first-cohort timing limits remain in the appendix.

          Arm           First calls   First tokens    Second calls        Second tokens    Second seconds
          A                      1         14,428                   4             56,543            227.882
          B                      4         65,695                   4             62,439            249.385
          C                      1         14,589                   4             63,336            415.743
          D (partial)            1         14,269                   4             60,937            489.516


348   Remaining system questions. These increments establish local mechanisms and expose limitations.
349   They leave open matched context-substitution efficacy, persistent multi-task quality/cost, procedure
350   and world-memory utility on real tasks, production reuse, governed publication, integrated native
351   proof admission, and a held-out comparison with complete startup, fallback, failed-attempt and
352   recovery accounting. Additional benchmark recruitment and environment qualification are reported
353   in Appendix F; they add no model-quality outcomes.


354   7   Related work

355   Proof-carrying code places explicit evidence between a producer and a consumer’s safety policy [7].
356   This motivates separating an artifact from the evidence needed to accept it. Our finite-check repair
357   experiment and signed provenance records are not proof-carrying code in that formal sense. Abstract
358   interpretation and translation validation similarly motivate explicit approximation and conversion
359   relations [2, 10], not automatic admission of a backend or source-language proof.


      Table 3: Useful completions in the fixed 32-cell A/B cold comparison. Eight families are the analysis
      blocks; two repetitions per arm are nested.
                    Family                           A useful / 2       B useful / 2   B−A mean
                    09-tomlkit                                  1                  1            0
                    10-installer                                0                  0            0
                    11-tornado                                  2                  1         -0.5
                    12-more-itertools                           2                  2            0
                    13-charset_normalizer                       0                  0            0
                    14-iniconfig                                0                  0            0
                    15-wheel                                    0                  0            0
                    16-jinja                                    0                  0            0
                    All eight (16 cells per arm)          5 / 16             4 / 16      -0.0625


                                                          8

````

### PDF page 9

````text
360   Mokhov et al. separate scheduling from the decision whether a task needs rebuilding [4]. Our
361   reuse obligation additionally names the statement, environment, lifecycle, and trust conditions
362   for transferring a test observation. The cold comparison supplies no measured incremental-reuse
363   advantage over build systems.
364   SWE-agent studies an interface for repository navigation, editing, and program execution [13]; SWT-
365   Bench studies test-based validation of real-world fixes [5]. They motivate treating both information
366   access and executable checks as parts of a repair method. Differences in tasks, interaction, models,
367   and acceptance criteria preclude a head-to-head performance claim or an assertion that we reran their
368   benchmarks. The contribution here is a bounded composition of evidence and authority mechanisms,
369   not a first-of-kind claim or a new foundational algorithm.


370   8   Limitations

371   The historical study’s eight convenience-selected families and two nested repetitions cannot support
372   broad repository-population inference. Its intervention changes the complete context supplied to
373   the model; component ablations and a prompt-compression causal claim remain unavailable. The
374   withdrawn C/D, warm-cache, reuse, publication, and sixteen-family objectives are not completed
375   outcomes. The new context and routing pilots use small constructed tasks and distinct source
376   profiles. Their observed reductions cannot be added together or extrapolated to an integrated system.
377   Qualification counts and exhaustive bounded input grids are not independent samples of repository
378   tasks. The memory comparison is one constructed sequence; ordinary retrieval and templates
379   match its action-count reduction. Sealing measurements use finite execution receipts, explicit added
380   admission/recovery callers and two tiny preparation operations. These profiles have not yet been
381   combined into a single matched repository-trajectory experiment.
382   Finite tests cover their executed assertions. Passing them does not establish complete behavioral cor-
383   rectness, source-level semantic fidelity, or adequate coverage of every relevant behavior. Independent
384   human semantic annotations, expert agreement, and human time were not measured. AI candidate
385   inspection does not supply those measurements.
386   The conditional design arguments retain checker adequacy, complete dependency projections, pro-
387   tected policy authority, and exclusive checked publication as premises. They establish no universal
388   Python theorem, native proof performance, global consensus, external exactly-once effects, or com-
389   plete adversarial scorer integrity. A local constructed witness cannot fill a missing production or
390   final-comparison measurement.
391   The interrupted runtime, actual timing deviations, prior failures, and unknown remote charges limit
392   net-efficiency claims. Lease occupancy is not compute usage. Overlapping clocks and a pilot cost
393   projection that aliases the same executions cannot be charged twice. Separate source epochs and
394   actual cap observations must remain visible even when a candidate passes its tests.
395   Numerical reproduction from anonymous, manifest-bound scalar derivatives is narrower than original-
396   signature verification or confidential-oracle rescoring. Changed derivative bytes are not authenticated
397   by the original signature. Reference source derivatives must be distinguished from executed source,
398   with upstream attribution and licences retained. Stable provenance hashes can permit correlation, so
399   a lexical anonymity audit is bounded and does not guarantee de-identification.


400   9   Conclusion

401   Persistent semantic state, obligation-guided reasoning, applicable evidence reuse and accepted-state
402   publication provide a method for avoiding repeated work under a declared acceptance standard. The
403   development experiments exercise these mechanisms and expose their costs: symbolic closures avoid
404   model calls on constructed tasks, simple controls match some memory benefits, and priming can
405   outweigh validation reuse. Native publication and archive proofs preserve declared bindings without
406   proving arbitrary execution truth. Neither natural repository development comparison completes a
407   whole trajectory or establishes a general efficiency advantage. The earlier additive-context study
408   remains a separate, unfavorable result. Complete system-level token savings require matched,
409   independently scored trajectories, mechanism ablations and full accounting of setup, failed attempts


                                                        9

````

### PDF page 10

````text
410   and recovery. The architecture defines this research question; the missing integrated measurements
411   remain necessary.




                                                     10

````

### PDF page 11

````text
412   References
413    [1] Edmund M. Clarke, Orna Grumberg, Somesh Jha, Yuan Lu, and Helmut Veith. Counterexample-
414        guided abstraction refinement. In Computer Aided Verification (CAV 2000), volume 1855 of
415        Lecture Notes in Computer Science, pages 154–169. Springer, 2000. doi: 10.1007/10722167_15.
416    [2] Patrick Cousot and Radhia Cousot. Abstract interpretation: a unified lattice model for static
417        analysis of programs by construction or approximation of fixpoints. In Proceedings of the 4th
418        ACM SIGACT-SIGPLAN Symposium on Principles of Programming Languages, POPL ’77,
419        pages 238–252, Los Angeles, California, 1977. ACM Press. doi: 10.1145/512950.512973.
420    [3] Carlos E. Jimenez, John Yang, Alexander Wettig, Shunyu Yao, Kexin Pei, Ofir Press, and
421        Karthik Narasimhan. SWE-bench: Can language models resolve real-world GitHub issues?
422        In The Twelfth International Conference on Learning Representations, 2024. URL https:
423        //openreview.net/forum?id=VTF8yNQM66.
424    [4] Andrey Mokhov, Neil Mitchell, and Simon Peyton Jones. Build systems à la carte. Proceedings
425        of the ACM on Programming Languages, 2(ICFP):1–29, 2018. doi: 10.1145/3236774. Expanded
426        as Build systems à la carte: Theory and practice, Journal of Functional Programming 30, e11,
427        2020, doi:10.1017/S0956796820000088.
428    [5] Niels Mündler, Mark Niklas Müller, Jingxuan He, and Martin Vechev. SWT-bench: Testing and
429        validating real-world bug-fixes with code agents. In Advances in Neural Information Processing
430        Systems 37, pages 81857–81887. Neural Information Processing Systems Foundation, 2024.
431        doi: 10.52202/079017-2601.
432    [6] Nebius.   SWE-rebench dataset.           https://huggingface.co/datasets/nebius/
433        SWE-rebench. Test-split metadata at revision 89cdfbab; accessed 2026-09-14.
434    [7] George C. Necula. Proof-carrying code. In Proceedings of the 24th ACM SIGPLAN-SIGACT
435        Symposium on Principles of Programming Languages, POPL ’97, pages 106–119, Paris, France,
436        1997. ACM Press. doi: 10.1145/263699.263712.
437    [8] OpenAI.     Introducing SWE-bench verified.       https://openai.com/index/
438        introducing-swe-bench-verified/, 2024. Accessed 2026-09-14.
439    [9] OpenAI. Why SWE-bench verified no longer measures frontier coding capabilities. https://
440        openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/, 2026. Pub-
441        lished February 23, 2026; accessed 2026-09-14.
442   [10] Amir Pnueli, Michael Siegel, and Eli Singerman. Translation validation. In Tools and Algorithms
443        for the Construction and Analysis of Systems (TACAS 1998), volume 1384 of Lecture Notes in
444        Computer Science, pages 151–166. Springer, 1998. doi: 10.1007/BFb0054170.
445   [11] Scale AI. SWE-bench pro dataset. https://huggingface.co/datasets/ScaleAI/
446        SWE-bench_Pro. Test-split metadata at revision 7ab51149; accessed 2026-09-14.
447   [12] Armando Solar-Lezama. Program Synthesis by Sketching. PhD dissertation, University of
448        California, Berkeley, 2008. URL https://www2.eecs.berkeley.edu/Pubs/TechRpts/
449        2008/EECS-2008-176.html. Technical Report UCB/EECS-2008-176.
450   [13] John Yang, Carlos E. Jimenez, Alexander Wettig, Kilian Lieret, Shunyu Yao, Karthik
451        Narasimhan, and Ofir Press. SWE-agent: Agent-computer interfaces enable automated software
452        engineering. In Advances in Neural Information Processing Systems 37, pages 50528–50652.
453        Neural Information Processing Systems Foundation, 2024. doi: 10.52202/079017-1601.




                                                      11

````

## Exact ordered LaTeX source: main assembly

This partial assembly replaces only manifest-listed `\input{...}` directives with their verbatim UTF-8 source text in `main.tex` order and inserts labeled comments. It is provided for exact formulas and source review, not as a standalone compilable document. Bibliography and figure commands remain as in the original; their retained files are in the source snapshot. No empirical sentence or equation is editorially corrected here.

````latex
% Working whole-system revision; historical results retained separately.

% BEGIN retained input: header.tex
% Assembly input only. Use the official research style in anonymous default mode.
\documentclass{article}
\PassOptionsToPackage{numbers,compress}{natbib}
\usepackage{neurips_2026_vericode}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,booktabs,microtype,url,hyperref,graphicx}
\title{Proof-Carrying Neurosymbolic Supervision:\\State, Reasoning, and Evidence Reuse}
\workshoptitle{AI for Verifiable Coding}
\author{Anonymous Authors}
\hypersetup{pdftitle={Proof-Carrying Neurosymbolic Supervision: State, Reasoning, and Evidence Reuse},
  pdfauthor={Anonymous Authors}}

% END retained input: header.tex

\usepackage{xcolor} % Required by the unchanged official checklist answer macros.
\begin{document}
\maketitle

% BEGIN retained input: fragments/abstract.tex
\begin{abstract}
Coding agents repeatedly reconstruct repository context, reason about changes,
and validate results. We study an obligation-centered supervision architecture
that retains source-linked semantic state, routes supported obligations through
checked symbolic mechanisms, and uses neural proposals for unresolved work.
Evidence applicability governs validation reuse and accepted-state publication.
The empirical question is whether their combined startup and operating costs
reduce neural work and validation effort while preserving useful progress.
We evaluate context substitution, avoided model calls, persistent planning,
validation reuse and native proof consumption as distinct mechanisms, retaining
an earlier additive-context cold-repair study as separate evidence.
On four constructed tasks, symbolic repair and residual routing pass the same
independent checks as a model-first baseline with 2,430 versus 4,865 provider
tokens. This 50.05\% reduction is confined to that development suite.
Other experiments exercise lifecycle-preserving reuse, memory consumption,
publication, crash recovery and proofs over actual saved state. Simple
retrieval matches memory's action reduction, and measured reuse savings do
not recover priming cost over five repetitions. In two development comparisons
on one natural two-issue repository sequence, every arm accepts one issue and
none completes the trajectory. These mixed findings establish bounded capabilities and
implementation limitations. Complete integrated token savings remain open;
component percentages cannot be combined into a system estimate.
\end{abstract}

% END retained input: fragments/abstract.tex


% BEGIN retained input: fragments/introduction.tex
\section{Problem and contribution}
\label{sec:introduction}

The cost of a coding agent includes repeated repository discovery, specification
interpretation, planning, repair, validation, and recovery. Persistent state can
avoid some of this work only when the state remains applicable to the current
program. A shorter prompt can omit necessary dependencies; a cached pass can
refer to obsolete source. Repository-agent interfaces and test-validation
benchmarks make this boundary between proposals and checks central to useful
repair~\citep{baseline08,baseline11}.

Our proposed method has three connected contributions. First, source and intent
produce identity-bound semantic facts and explicit unresolved obligations.
Second, those obligations guide deterministic analysis, checked reasoning and
bounded synthesis before an authorized neural residual. Third, validation,
evidence reuse and accepted-state publication preserve the scope and
applicability of each observation. Accepted changes invalidate affected facts
and plans, providing the next iteration with persistent, current evidence.

The resulting hypothesis concerns the entire workflow: repeated neural
reasoning and validation may be displaced by persistent, checked work.
Context compression is one possible mechanism. Fewer model calls and less
replanning are distinct mechanisms, while test reuse primarily reduces
validation computation. Each requires its own correctness and cost comparison.
No benefit follows merely from having a symbolic component in the source tree.

We retain an earlier additive-context cold-repair study as one bounded
experiment, then evaluate missing mechanisms incrementally. Architecture,
local qualification, development pilots and confirmatory effectiveness have
different evidential roles. A failed or inconclusive experiment remains a
result; an unrun comparison remains an open research obligation. In particular,
the original 32 cold cells cannot establish the value of persistent reasoning
or whole-system token savings.

% END retained input: fragments/introduction.tex


% BEGIN retained input: fragments/system.tex
\section{The supervision loop}
\label{sec:system}

\paragraph{Compile state and obligations.}
The semantic index extracts source-linked symbols, dependencies, contracts and
analysis limits. Intent supplies candidate goals and permitted effects;
formalization produces bounded obligations without turning an inferred
specification into authority. Semantic state is separate from operational task
state and artifact storage. Missing dependencies, dynamic features and lossy
translations remain an explicit unknown frontier that requires more source,
broader checking or abstention.

\paragraph{Reason before proposing.}
For each obligation, the intended supervisor considers applicable evidence or
procedures, exact dependency and static analysis, contract/solver checks, and
bounded deterministic repair or synthesis. A neural model proposes unresolved
work through a permitted residual route. Abstract interpretation, translation
validation and counterexample-guided methods provide established foundations;
the contribution is their composition at the supervisor's decision boundary,
not a new general-purpose prover~\citep{baseline02,baseline03,baseline04,baseline05}.
The evaluation must demonstrate that a computed result changes the next actual
action and passes independent checks. A route label or a candidate's assertion
that it closes a claim is insufficient.

\paragraph{Validate, reuse and publish.}
Candidate edits are checked against the current source and required acceptance
conditions. Evidence reuse requires matching subjects, dependency and
environment identities, declared checker semantics and trust policy. For
fixture-based tests, collection and materialized setup state must be resolved
before call-phase reuse; required setup and teardown effects still run, and
teardown failure prevents whole-item success. A complete accepted-transition
manifest binds the current parent and applicable evidence before publication.
Restart reconciliation must support valid continuation as well as rejection of
stale work.

\paragraph{Persist, invalidate and replan.}
An accepted transition updates the state used by the next task. Source,
dependency, fixture, policy and capability changes invalidate affected evidence
and reopen obligations. Procedural memory can nominate previously useful
actions, but applicability and independent validation remain necessary. Learned
world models and procedure discovery require held-out downstream evaluation;
their source presence does not establish generalization. The intended savings
appear over trajectories of tasks, so a single cold proposal is an incomplete
test of this architecture.

\paragraph{Separate resource hypotheses.}
For a fixed workload of $N$ tasks and arm $a$, let
\[
 T_a(N)=T_{\mathrm{setup},a}+\sum_{j\in\mathcal C_a(N)}T_j,
\]
where $\mathcal C_a(N)$ contains every workflow model call, including planning,
formalization, proposals, review, failed attempts, retries and recovery.
Provider-reported totals are preserved without adding overlapping cached or
reasoning-token fields. Unknown usage remains unknown. The reduction
$1-T_{\mathrm{system}}(N)/T_{\mathrm{baseline}}(N)$ is meaningful only for
matched workloads with adequate independently measured progress and comparable
complete accounting. Report setup and priming at explicit reuse horizons;
provider charges, host computation and elapsed time are separate quantities.
Independent experimental oracle work is reported separately from each arm's
runtime validation, without hiding mandatory runtime costs.

% END retained input: fragments/system.tex


% BEGIN retained input: fragments/evidence_method.tex
\section{Method and trusted assumptions}
\label{sec:evidence-method}

\paragraph{Separate evidence classes.}
Semantic state links facts, dependencies, contracts, and unresolved obligations
to source. Operational state records goals, tasks, attempts, leases, and
decisions. Artifact storage preserves candidate bytes and accepted manifests.
An evidence item binds a subject to a declared statement, checker, environment,
and provenance. A passing test concerns the finite checks actually executed;
a formal derivation concerns its encoded relation and premises; a grant concerns
an actor's permission to act now. These classes cannot substitute for one another.
In particular, a signature binds a record to a key under cryptographic
assumptions. It establishes neither checker adequacy nor the honesty of an
observation.

\paragraph{Applicable evidence.}
The intended loop derives obligations from current source, chooses an
admissible analysis or proposal route, checks an isolated candidate, and admits
only evidence applicable to that candidate. Translation validation motivates
checking a particular conversion against its stated relation~\citep{baseline04};
a source-linked record alone is not such validation. Abstract facts likewise
depend on an approximation relation~\citep{baseline02}. A typed or
content-addressed representation does not imply full source-language soundness.

\paragraph{Conditional acceptance and reuse.}
If publication succeeds only after checking the current parent, authorized
scope, complete requirement manifest, admitted evidence, and expected-parent
compare-and-swap, each successful successor satisfies those gates. Given a valid
initial root and exclusive use of that publication operation, induction
preserves the declared manifest policy. This does not establish enforcement by
unexamined write paths or atomicity of external effects.

For test reuse, suppose the observation of test $t$ under profile $\theta$
factors through a complete dependency projection:
\[
  \operatorname{Obs}_{\theta}(t,s)=f_{\theta}(\pi_D(s)).
\]
If $f_\theta$ is deterministic on every admitted state, equal projections imply
equal observations. Completeness and determinism are substantive premises;
hashing an incomplete dependency list, opaque fixture, or uncontrolled effect
does not discharge them. Appendix~\ref{sec:formal-arguments-ns023} preserves
the full conditional, unmachine-checked statements and the distinction between
behavioral acceptance, action permission, and publication.

\paragraph{Executed scope.}
The historical cold comparison exercises native context preparation, model proposals,
candidate custody and AI inspection, and separate cold scoring. Earlier
constructed controls and a local guard-before-write witness test named
implementation boundaries; they do not establish that the complete intended
loop ran as a live benchmark. Its original proof profile lacks the admitted
backend, key provenance, and exact statement binding required for native proof
admission. New development profiles and their measured results are reported
separately in Section~\ref{sec:incremental-evaluation}; neither native proving
performance nor empirical reuse benefit is inferred from the conditional arguments.

% END retained input: fragments/evidence_method.tex


% BEGIN retained input: fragments/historical_method_summary.tex
\section{Historical component-study design}
\label{sec:historical-design-summary}

The retained cold study compares raw selected public context (A) with the same
raw selection plus native source-linked semantic context (B). Eight
convenience-selected Python repository families and two nested repetitions per
arm yield 32 fixed cells. Sixteen family/arm request commitments precede final
generation. The treatment is additive and cannot isolate context compression.
The retained A/B cells form an order-preserving subset of a later 192-cell plan;
160 factor cells were withdrawn and eight additional target families were not
recruited. These missing comparisons remain separate research obligations.

Each cell permits one Grok 4.6 proposal, requesting at most 4,096 output tokens,
with no model retry, scientific fallback or served random seed. The nominal
gateway bound is 600 seconds; actual measured compliance governs useful credit.
Eligible candidates undergo separate cold, network-disabled public and hidden
scoring. Useful completion requires admission, nonempty passing checks and
measured resource compliance. Failed, expired, unscored and incompletely
validated cells remain in the denominator. Separate scoring alone does not
establish resistance to arbitrary candidate interference.

The analysis averages repetitions within each family and then contrasts B with
A across eight family blocks. A prespecified 20,000-resample paired family
bootstrap provides a conditional descriptive interval, without a population
superiority or noninferiority claim. Model, scorer and wrapper clocks may
overlap and are not added as disjoint costs; unavailable usage remains unknown.
The separate four-family pilot and earlier qualification controls supply no
additional final trials. Appendices~\ref{sec:design},
\ref{sec:analysis-method} and~\ref{sec:historical-accounting} retain the full
design, interruption history, analysis recipe and accounting exceptions.

% END retained input: fragments/historical_method_summary.tex


% BEGIN retained input: fragments/results.tex
\section{Historical cold-repair results}
\label{sec:results}

All 32 planned cells have verified terminal records. Nine yielded useful
completion: A achieved 5/16 and B 4/16. The eight-family mean difference,
B minus A, is $-0.0625$, with a descriptive 95\% whole-family bootstrap interval
of $[-0.1875,0]$. Seven family differences are zero; Tornado accounts for the
aggregate difference. One B Tornado request ended in a transport failure.
This convenience sample supplies no population-level superiority or
noninferiority conclusion and cannot isolate semantic content from other
features of the combined request.

The 23 non-useful cells comprise 14 proposal-child deadlines, two known proposal
failures and seven original hidden-failure labels. Six of the latter executed
hidden checks and failed; one passed public checks but collected zero hidden
assertions due to an import error. It remains incomplete validation with no
useful credit. All failures remain in the fixed denominator. Sixteen scorer
invocations include this incomplete case; fifteen completed cold validation.
Provider usage is available for only 16/32 cells, and the original experiment
has no complete-cohort token or settled-charge total.

The developmental four-family pilot remains separate, with ten historical
useful labels among 24 cells, five per arm. Interruption, measured timing
deviations, missing costs and reconstructed candidate metadata are retained
in Appendix~\ref{sec:historical-accounting}. Those records preserve the original
outcomes and do not provide additional scientific trials. The historical study
supports an additive-context observation only; it does not evaluate the
whole-system reasoning and reuse hypothesis.

% END retained input: fragments/results.tex


% BEGIN retained input: fragments/incremental_results.tex
\section{Incremental system evaluation}
\label{sec:incremental-evaluation}

The following evaluations extend the original architecture questions. They are
development measurements and local qualification, separate from the historical
cold experiment and from any future confirmatory population. Their profiles
and source versions are explicit; a partial combined controller is qualified
below, while the complete matched system comparison remains open.

\paragraph{Context substitution opportunity.}
We reconstructed all sixteen historical A/B request commitments across eight
unique families and checked the selected public source against its hashes.
All 254 selected windows were protected editable or test source; there were
zero eligible unchanged-dependency files and zero substituted windows.
The guarded substitution adapter therefore retained the raw source. Saved
native packets contained no explicit obligation CIDs and 14,471 unresolved
dependency-edge occurrences. Instruction text was retained, but this cohort
cannot establish explicit obligation preservation or dependency compression.

Using \texttt{tiktoken} 0.12.0 with \texttt{o200k\_base}, exact tokenization of
system/user message content totaled 91,783 for A, 107,870 for B, and 108,577 for
guarded substitution C: increases of 17.53\% and 18.30\% over A.
These counts exclude chat-template overhead and output, and are not Grok
provider usage. A second named encoding gives the same direction.
Eighteen constructed adapter controls separately check expansion and rejection;
they do not qualify a native producer. This result identifies a population
requirement: a compression experiment must include unchanged dependencies that
can actually be replaced under its stated policy.

\paragraph{Native dependency context and bounded projection.}
Three authored multi-module repositories supply six fresh native exact
dependency admissions. Twelve cold/incremental index and semantic-bundle root
comparisons agree; dependency edits invalidate prior capsules and unknown-call
mutations require raw fallback. Full transported native capsules total
8,399 serialized context-content
tokens versus 1,467 for raw source. A new restricted projection instead
transports source-bound integer equations. Six separate Z3 equivalence checks
and 252 concrete source executions check that projection; its 1,353
tokens are 7.77\% below raw. Plain AST source compaction totals
1,464 tokens. These are named-encoding offline counts, not provider savings.
The equation profile excludes floats, custom objects, side effects and unsupported
syntax. The compact projection is an evaluated addition; the full native capsule
payload itself is larger than raw source in these examples.

\paragraph{Repository context and preparation.}
Native repository custody, current-source expansion and invalidation checks
pass on bounded XML/pyparsing scopes and on both full declared Requests
inventories (97 files each); these profiles permit zero raw-source omissions.
Five full pyparsing producer processes reach their 600-second deadline. A
subsequent immutable-state identity profile completes full preparation in
566.254 seconds, followed by a passing independent native consumer; all
302 XML/pyparsing regular files are retained and 22 negative controls pass.
This establishes completion under the bound in one shared-host run. Preparation
is still substantial, and these profiles establish no compression or replicated
speedup. A subsequent full comment-change comparison exposes 1,568 differing
graph records. A rescanning guard restores byte equality but fails a later
import-inventory case. Preserving original frontend observations then gives
exact full equality while reusing 153 of 154 Python files. Incremental takes
607.971 seconds versus 440.276 cold, adds a 53.75 MB sidecar and incurs separately
metered bootstrap costs. Useful incremental economics remain open.
Appendix~\ref{sec:incremental-context-preparation} retains source scopes,
identity checks, earlier failures and actual costs.

\paragraph{Live context substitution.}
The three dependency-bearing development repositories also support a matched
raw-versus-equation repair pilot. Both arms pass all three separate cold
behavioral checks; all six requests return usage. Provider input totals are
4,014 raw versus 3,817 compact (4.91\% fewer),
and total usage is 4,866 versus 4,637 (4.71\%
fewer). Both arms use three requests with the same Grok 4.6 low-effort profile
and resource ceilings as the routing pilot. Cached-input totals differ, so
charge differences cannot be attributed solely to compaction. This tests a
restricted, verified representation on trivial constructed repairs; dynamic
source expansion and broader repository quality remain unmeasured. The result
is separate from, and must not be added to, the routing reduction.

\paragraph{Checked symbolic closure and live residuals.}
A new development caller invokes the native Python analyzer, bounded CEGIS
repair, visible behavioral checks and native routing. Four constructed tasks
include false success without observation, swallowed backend failure, interval
clamping and stable deduplication. Both arms receive the same source, objective
and public checks; separate Docker execution scores broader behavioral checks.
The first two defects fit the declared deterministic grammar. The remaining two
require the same model residual in both arms. Internal CEGIS marker gates are
not counted as theorem proofs; behavioral checks justify only these bounded
obligations.

\begin{table}[htbp]
\centering
\caption{Constructed four-task routing development comparison. One observation
per task and arm; no population inference.}
\label{tab:routing-development}
\begin{tabular}{lrrr}
\toprule
Arm & Independently passed & Model calls & Total provider tokens \\
\midrule
Model first & 4/4 & 4 & 4,865 \\
Symbolic first plus residual & 4/4 & 2 & 2,430 \\
\bottomrule
\end{tabular}
\end{table}

All six Grok 4.6 requests returned usage, under the same low-effort profile,
\texttt{max\_tokens=2048} request parameter and 240-second deadline, without retries.
The observed reduction is 50.05\% on this suite. Eliminating two requests
accounts for 2,282 baseline tokens; response variation on the residual tasks
accounts for the remaining 153-token net difference. Provider cache state was
not controlled. There were no auxiliary workflow model calls or model-assisted
setup in this caller; experiment authoring and implementation effort are outside
that runtime denominator. The initial expired-credential attempt dispatched
zero requests and remains a separate development record. General repository
performance and full-system setup amortization remain unmeasured.

\paragraph{Supplementary scorer validation.}
A post-development audit exposes five false admissions among six crafted
incorrect candidates in the original pilot scorers. Candidate interference
with oracle helpers or premature process termination could masquerade as
passing execution. A new isolated scorer separates the oracle from the candidate
worker, restricts public dependency imports and requires observed calls and
positive completion. It rejects all six crafted candidates and all seven
unrepaired controls. All ten unique saved candidate bodies still pass, preserving
the eight routing and six context record outcomes above. This supplementary
rescore supports these saved outcomes; the small control set does not establish
general scorer robustness. Original scorers and observations remain retained.

\paragraph{Lifecycle-preserving test reuse.}
A proposed local evaluation adapter uses native cache admission and Ed25519
runner attestations issued only after actual passing setup/call/teardown.
Its explicitly enrolled pure workload and immutable fixture profile support
valid call-phase reuse while setup and teardown still execute. Fourteen
prespecified cases cover unchanged work, source/test/fixture/configuration/
environment mutations, missing or tampered evidence, revocation, unsupported
fixture values and lifecycle failure. All fourteen match separate cold-process
outcomes. Reuse followed by failing teardown correctly fails the whole item;
the result is not zero-error evidence for arbitrary pytest programs.

Five alternating warm/cold timing pairs omit all five warm test-body executions
while retaining five setups and teardowns in each arm. Total host wall time was
1.281 seconds cold and 1.240 seconds warm, excluding the separately recorded
prime and issuance costs. This small descriptive difference does not establish
a reliable net speedup or token savings. The default production plugin probe
executed the body in both write and read/write modes and produced no positive
reuse. Thus the result qualifies the proposed bounded adapter, not deployment
of the native default reuse path. Earlier failed development invocations and
the historical false-reuse observation remain retained.
The measured 0.256-second cold prime and 0.006-second issuance exceed
the observed wall-time saving over these five repetitions; a net benefit at
that horizon is not demonstrated.

\paragraph{Persistent work across process termination.}
Three actual processes exercise the native session journal/checkpoint with
the same checked deterministic caller. Duplicate pending notifications coalesce.
The first process exits abruptly after one completion; the next resumes exactly
one unfinished scan, and a third restart finds no pending work. Each actual
execution passes the independent behavioral oracle, and no original attempt
executes twice. However, a fresh notification for a completed snapshot schedules
and executes analysis again. Journal continuity is supported by this case;
completed-result memoization, accepted-root publication and cross-task token
savings are not established.

\paragraph{Publication and recovery qualification.}
Forty-seven existing source-shipped tests pass in a fresh compatible native
profile. They cover immutable-root publication, stale writers, competing CAS
updates, seal storage and restart recovery at injected persistence boundaries.
These are constructed software qualifications, including placeholder proof
records and exception-based interruptions. They do not establish a newly
integrated evidence-producing workflow, actual process-kill tolerance at each
boundary, or measured parallel-sealing savings.

\paragraph{Evidence-backed sealing and completed recovery.}
A new caller independently replays finite computation receipts, checks exact
source/input/policy bindings and complete coverage, then invokes native
integrity-only seal verification and publication. A full checkpoint and two
delta seals become successive current roots; a competing delta loses stale
parent CAS. Four prepared states cover 700 independently checked state/input
observations, using five computation subprocesses and three unchanged-receipt
reuses. Five constructed mutations reject. Native digest verification alone
accepts three internally consistent but semantically wrong or stale receipts;
the caller's independent replay and bindings are therefore substantive gates.

Two real process terminations preserve the expected accepted roots. Native
recovery recognizes a valid pre-CAS seal but leaves its transition pending;
retrying the same publication is refused. A separately evaluated recovery
caller rechecks the persisted evidence and completes native CAS/WAL phases
with zero new computation calls. A subsequent fresh process consumes that
accepted root and publishes the next changed state, reaching a four-seal chain.
This establishes bounded continuation under an explicit added caller. It does
not establish native automatic recovery, theorem proofs, power-loss tolerance
or a compute saving: the independent receipt checker still runs on reuse.
Four paired trials separately compare actual preparation of two cold operations:
all eight preparations pass with identical receipt and seal content. Median
preparation time is 63.21 ms sequential versus 32.10 ms parallel;
maximum sampled aggregate process RSS rises from 44.66 to 55.54 MiB.
The host is not exclusive, sampled RSS counts shared pages per process, and
these tiny preparation trials measure neither publication latency nor a
whole-system speedup.

\paragraph{Procedure synthesis and stored candidates.}
A bounded native synthesis/body-store comparison completes seven of eight units
in both cold and stored arms: 3,883 correct fresh-query decisions, zero false
admissions and 554 abstentions on unsupported parity. Stored candidates require
six synthesis calls and 23 tried candidates versus eight and 29 cold, under exact
source-catalog and policy bindings. A separately frozen fixed-template control
matches quality with no synthesis, so retrieval has no demonstrated advantage
over that simpler control. Fresh-process replay, binding mutations and scaffold
sensitivity are checked; this initial executor/store profile has no model calls.
A later signed native TEST integration executes the exact saved candidate on
136 new bounded inputs through all six native handlers. All decisions match
the oracle; 30 evidence negatives and 13 runtime controls pass. Its 17.243-second
worker cost plus preparation does not establish savings. Appendix~\ref{sec:signed-native-procedure}
separates this tested execution from repository applicability and promotion.

\paragraph{World-state memory and actual subsequent actions.}
A native typed transition producer, persistent block/SQLite store and admission
path are connected by a new evaluation dispatcher. Eleven tasks per arm run in
fresh interpreters against a closed three-action integer service; selected
actions always execute and their current outputs are independently checked.
All 44 task/arm outcomes pass. Native memory uses 16 action executions versus
27 without memory, but exact JSON retrieval and complete-condition templates
also use 16. Charging each arm the common three-action seed gives 19 versus
30. Changed state, source and declared environment invalidate prior observations;
fallback creates fresh evidence consumed by the next process.
Native total process time is 8.947 seconds versus 8.739 without
memory, including common import/storage work and excluding the separately
recorded shared seed. Thus fewer search attempts do not establish a wall-time
advantage. The frozen dispatcher uses retrieved typed records directly: an
audit finds that the native compiler emits incorrect record identifiers in
all eleven compiled proposals, so compiler-mediated dispatch is not qualified
by this run. These results establish bounded storage/lookup consumption, not
learned world-model benefit, transfer, production integration or token savings.
A separately frozen compiler correction selects each record's own identity.
The ensuing consumer resolves compiler-selected records from the native store
before actual execution: the seed and eleven later cases pass, using 19 actions
and 25 fresh service processes. Changed source, state and environment still
invalidate prior observations. Independent checks preserve all original
comparison artifacts. This qualifies the corrected compiler-mediated path;
it does not change the original simple-retrieval/template parity or supply
learned transfer and token-savings evidence.

\paragraph{Native compositional reasoning.}
An existing original-source vertical slice was run with its compatible nested
datasets tree. A baseline component contract discharged, an injected fault was
refuted, and repair restored discharge. Localization produced an UNSAT core and
a cvc5 interpolant separately checked by Z3; the final artifact was verified by
semantic rescanning, composition redischarge and test replay. Selected and full
tests passed. Host elapsed time was 19.309 seconds. This is one existing
constructed fixture with a prescribed fault and expected repair, not a held-out
synthesis experiment. Internal benchmark estimates are not counted as measured
token or compute savings. An earlier source profile failed to import the
required composition module and is preserved separately. Solver validation
does not imply kernel reconstruction or all-language correctness.

\paragraph{Native proof production and statement binding.}
The source-built native backend produces three v3 Merkle/count proofs and three
honest v2 implication-chain proofs. For v3, primary setup takes 7.810
seconds, proving 12.048--12.474 seconds and verification
3.053--5.147 milliseconds. Tested malformed witnesses, proofs and
keys reject. Both profiles require exact outer-statement checks at the caller:
the raw verifier can accept changed displayed metadata when its scalar public
inputs remain unchanged. These are measured bounded circuit relations, not
proofs that arbitrary tests executed or production trust admission. Stronger
v2 textual-binding assurance remains unconfirmed, and the v5 pytest-attestation
profile is unsupported. Appendix~\ref{sec:incremental-native-proof} retains the
separate profiles, mutation observations and v2 costs. A subsequent native
archive producer/consumer binds four actual accepted controller events to one
honest v3 proof, with seven mutation rejections. A second integration consumes
the actual accepted Requests repair, restores all 97 source files and rejects
eight mutations. Its 11.979-second proof and 5.256-millisecond verification
are post-cohort overhead; original receipts still supply execution evidence.

\paragraph{Combined controller and native publication.}
Constructed thirteen-event reasoning and eight-event publication profiles join
the actual native services and exercise real interruptions, native full/delta
publication and fresh accepted-source consumption. A separate Requests curator
fixture measures 377.226 seconds of phases including full context
preparation. These zero-provider controls establish bounded continuation,
not token savings. Appendix~\ref{sec:incremental-controller-publication} retains
their complete costs, failures and unsigned integrity-only trust boundary.

\paragraph{Natural two-issue comparisons.}
Two frozen Requests 5414-to-6028 development cohorts compare four arms with
equal public access and four-call trajectory ceilings. Every arm in each
cohort accepts the first issue and fails the second. First requests within
each cohort are byte-identical; B permits no source omission, while C/D
establish no successful symbolic closure. Partial D publishes and retrieves
accepted source. The first cohort's A/C/D continuations exceed their source
bound; B spends its remaining calls on failed candidates. A new conflict-first
retriever keeps required source within the same bounds in the second cohort.
All sixteen calls then execute, including expansion requests and three outputs
rejected by a file-mode transport defect. Table~\ref{tab:requests-cold} retains
both cohorts separately. In the second, B/C/D use 10.43\%/12.01\%/7.77\% more
tokens than A at the same observed acceptance count. Uncontrolled server caching,
one exposed family and adaptive follow-up preclude causal component or general
efficiency claims. Complete-trajectory cost ratios remain undefined.

\begin{table}[htbp]
\centering
\caption{Natural Requests cold development cohorts, retained separately.
Every arm accepts 1/2 nodes and completes 0/1 trajectories in each cohort.
Second-cohort wall includes nested services; first-cohort timing limits remain
in the appendix.}
\label{tab:requests-cold}
\begin{tabular}{lrrrrr}
\toprule
Arm & First calls & First tokens & Second calls & Second tokens & Second seconds \\
\midrule
A & 1 & 14,428 & 4 & 56,543 & 227.882 \\
B & 4 & 65,695 & 4 & 62,439 & 249.385 \\
C & 1 & 14,589 & 4 & 63,336 & 415.743 \\
D (partial) & 1 & 14,269 & 4 & 60,937 & 489.516 \\
\bottomrule
\end{tabular}
\end{table}

\paragraph{Remaining system questions.}
These increments establish local mechanisms and expose limitations. They leave
open matched context-substitution efficacy, persistent multi-task quality/cost,
procedure and world-memory utility on real tasks, production reuse, governed
publication, integrated native proof admission, and a held-out comparison with complete
startup, fallback, failed-attempt and recovery accounting.
Additional benchmark recruitment and environment qualification are reported in
Appendix~\ref{sec:incremental-recruitment}; they add no model-quality outcomes.

% END retained input: fragments/incremental_results.tex

\begin{table}[tbp]
\centering
\caption{Useful completions in the fixed 32-cell A/B cold comparison. Eight families are the analysis blocks; two repetitions per arm are nested.}
\label{tab:final32}

% BEGIN retained input: generated/table17.tex
\begin{tabular}{lrrr}
\hline
Family & A useful / 2 & B useful / 2 & B$-$A mean \\
\hline
09-tomlkit & 1 & 1 & 0 \\
10-installer & 0 & 0 & 0 \\
11-tornado & 2 & 1 & -0.5 \\
12-more-itertools & 2 & 2 & 0 \\
13-charset\_normalizer & 0 & 0 & 0 \\
14-iniconfig & 0 & 0 & 0 \\
15-wheel & 0 & 0 & 0 \\
16-jinja & 0 & 0 & 0 \\
\hline
All eight (16 cells per arm) & 5 / 16 & 4 / 16 & -0.0625 \\
\hline
\end{tabular}
% Repetitions are nested; the eight families are the analysis blocks.

% END retained input: generated/table17.tex

\end{table}

% BEGIN retained input: fragments/related_work.tex
\section{Related work}
\label{sec:related-work}

Proof-carrying code places explicit evidence between a producer and a
consumer's safety policy~\citep{baseline01}. This motivates separating an
artifact from the evidence needed to accept it. Our finite-check repair
experiment and signed provenance records are not proof-carrying code in
that formal sense. Abstract interpretation and translation validation
similarly motivate explicit approximation and conversion
relations~\citep{baseline02,baseline04}, not automatic admission of a backend
or source-language proof.

Mokhov et al.\ separate scheduling from the decision whether a task needs
rebuilding~\citep{baseline07}. Our reuse obligation additionally names the
statement, environment, lifecycle, and trust conditions for transferring a
test observation. The cold comparison supplies no measured incremental-reuse
advantage over build systems.

SWE-agent studies an interface for repository navigation, editing, and program
execution~\citep{baseline08}; SWT-Bench studies test-based validation of
real-world fixes~\citep{baseline11}. They motivate treating both information
access and executable checks as parts of a repair method. Differences in tasks,
interaction, models, and acceptance criteria preclude a head-to-head performance
claim or an assertion that we reran their benchmarks. The contribution here is
a bounded composition of evidence and authority mechanisms, not a first-of-kind
claim or a new foundational algorithm.


% END retained input: fragments/related_work.tex


% BEGIN retained input: fragments/limitations.tex
\section{Limitations}
\label{sec:limitations}

The historical study's eight convenience-selected families and two nested
repetitions cannot support broad repository-population inference. Its
intervention changes the complete
context supplied to the model; component ablations and a prompt-compression
causal claim remain unavailable. The withdrawn C/D, warm-cache, reuse,
publication, and sixteen-family objectives are not completed outcomes.
The new context and routing pilots use small constructed tasks and distinct
source profiles. Their observed reductions cannot be added together or
extrapolated to an integrated system. Qualification counts and exhaustive
bounded input grids are not independent samples of repository tasks.
The memory comparison is one constructed sequence; ordinary retrieval and
templates match its action-count reduction. Sealing measurements use finite
execution receipts, explicit added admission/recovery callers and two tiny
preparation operations. These profiles have not yet been combined into a
single matched repository-trajectory experiment.

Finite tests cover their executed assertions. Passing them does not establish
complete behavioral correctness, source-level semantic fidelity, or adequate
coverage of every relevant behavior. Independent human semantic annotations,
expert agreement, and human time were not measured. AI candidate inspection
does not supply those measurements.

The conditional design arguments retain checker adequacy, complete dependency
projections, protected policy authority, and exclusive checked publication as
premises. They establish no universal Python theorem, native proof performance,
global consensus, external exactly-once effects, or complete adversarial scorer
integrity. A local constructed witness cannot fill a missing production or
final-comparison measurement.

The interrupted runtime, actual timing deviations, prior failures, and unknown
remote charges limit net-efficiency claims. Lease occupancy is not compute
usage. Overlapping clocks and a pilot cost projection that aliases the same
executions cannot be charged twice. Separate source epochs and actual cap
observations must remain visible even when a candidate passes its tests.

Numerical reproduction from anonymous, manifest-bound scalar derivatives is
narrower than original-signature verification or confidential-oracle rescoring.
Changed derivative bytes are not authenticated by the original signature.
Reference source derivatives must be distinguished from executed source, with
upstream attribution and licences retained. Stable provenance hashes can permit
correlation, so a lexical anonymity audit is bounded and does not guarantee
de-identification.

% END retained input: fragments/limitations.tex


% BEGIN retained input: fragments/conclusion.tex
\section{Conclusion}
\label{sec:conclusion}

Persistent semantic state, obligation-guided reasoning, applicable evidence
reuse and accepted-state publication provide a method for avoiding repeated
work under a declared acceptance standard. The development experiments exercise
these mechanisms and expose their costs: symbolic closures avoid model calls
on constructed tasks, simple controls match some memory benefits, and priming
can outweigh validation reuse. Native publication and archive proofs preserve
declared bindings without proving arbitrary execution truth. Neither natural
repository development comparison completes a whole trajectory or establishes a
general efficiency advantage. The earlier additive-context study remains a
separate, unfavorable result. Complete system-level token savings require
matched, independently scored trajectories, mechanism ablations and full
accounting of setup, failed attempts and recovery. The architecture defines
this research question; the missing integrated measurements remain necessary.

% END retained input: fragments/conclusion.tex

\label{paper:main-end}
\clearpage
\label{paper:references-start}
\bibliographystyle{plainnat}
\bibliography{verified_references}
\clearpage

````
