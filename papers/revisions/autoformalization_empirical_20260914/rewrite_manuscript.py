from pathlib import Path
E=Path(__file__).resolve().parent
old=(E/'prior_handoff/editable/manuscript/main.tex').read_text()
header=old[:old.index('\\begin{abstract}')]
header=header.replace('% AF-022 claim-bearing manuscript.','% Empirical revision: frozen inference, structural compilation and native proof checks.')
header+='\\input{../results/empirical_numbers.tex}\n'
abstract=r'''\begin{abstract}
Autoformalization must preserve an informal requirement's meaning while producing an artifact that a machine can check. We study a compiler-guided architecture that couples typed, source-grounded intermediate representations to learned reconstruction and isolated proof-feedback heads. Its central distinction is between source fidelity, structural validity, and proof acceptance: success at one does not establish the others. We evaluate native compilers on 1,913 held-out legal-source units, compare direct model formalization on a fixed 100-unit subset, and examine three recovered training seeds using inference that cannot select outputs against evaluation targets. Shared parameters change mean embedding reconstruction cosine from \AEColdCosine{} to \AETrainedCosine{}; this is a source-conditioned reconstruction diagnostic, with no demonstrated compression bottleneck. A separately qualified learned prior orders actual structural checks while preserving their outcomes. An executable compiler repair is evaluated by paired structural changes and regressions. On 64 constructed proof goals, Leanstral supplies 12 kernel-accepted proofs among 32 valid goals and none among 32 invalid controls under a fixed admission policy. These experiments expose useful implementation behavior and substantial limitations; independent legal-semantic fidelity and general natural-source proof transfer remain unmeasured.
\end{abstract}

\section{Introduction}
A well-typed formula can misrepresent its source, and a correct proof can establish the wrong requirement. This distinction matters when autoformalization extends beyond mathematical statements to policies, programs, and execution traces. An obligation is not an observation, permission is not execution, and belief is not fact. Mathematical autoformalization has made natural-language translation into proof-assistant statements increasingly practical~\citep{wu2022autoformalization,azerbayev2023proofnet,jiang2024multilanguage}. For verifiable coding, the corresponding question is how to improve source-to-symbolic mappings while preserving these distinctions and retaining an explicit basis for accepting a result.

We investigate a compiler-guided architecture. Deterministic compilers produce typed intermediate representations (IRs) with source spans and modal profiles. Decomposers expose logical views; decompilers reconstruct inspectable content; learned components model reconstruction and propose priorities. Feedback can update shared parameters, train isolated prediction heads, or motivate an executable compiler repair. Structural checks and proof kernels retain authority over their respective acceptance decisions. The schema, operators, sorts, and admissibility rules are engineered; learning operates within those contracts.

The contribution is an implemented architecture accompanied by a measured account of its boundaries. We make three contributions:
\begin{enumerate}
\item We specify separate contracts for source-grounded compilation, source-withheld reconstruction, and conditional proof transfer between logical views.
\item We evaluate native compilation and a paired exception-scoping repair on 1,913 held-out source units, with a direct-model comparison on a prospectively selected 100-unit subset. We report representation checks, reconstruction behavior, abstention, and runtime failures without interpreting them as legal-semantic accuracy.
\item We evaluate actual three-seed learned states through a target-independent inference boundary, exercise a learned check-order consumer with rollback, and compare native proof assistance on 64 constructed valid and invalid goals.
\end{enumerate}
The result is an empirical systems study rather than evidence that every component of the proposed source-to-proof architecture already improves end-to-end fidelity. In particular, independent semantic annotations were not collected. The distinction enables concrete automated evaluation without using a compiler or theorem prover as a surrogate human interpretation of a legal source.

'''
reprs=old[old.index('\\section{Representations, teachers, and reconstruction}'):old.index('\\section{Multi-view translation and a coding example}')]
start=reprs.index('Actual native export, promotion, ingestion')
end=reprs.index('\\subsection{Retrieval, planning, and proof proposals}',start)
reprs=reprs[:start]+r'''The retained checkpoints reveal which parts of this design were learned. The three T2 states contain changed embedding-projection tables but empty modality and view-logit tables. Their classification outputs therefore provide no learned classification gain. The T3 states preserve the T2 reconstruction parameters and add an obligation-family prior; other single-label heads provide no calibrated estimate of correctness. The executed guidance consumer uses that prior to order two required checks. It performs both checks and leaves the IR and checker contracts unchanged. This is an operational use of learned state, with a deliberately limited hypothesis: a learned priority may change order, but cannot increase coverage merely by skipping obligations.

''' +reprs[end:]
reprs=reprs.replace('On the sealed validation \\texttt{PATH}, native Lean/Z3/CVC5/Vampire/E/Coq/Isabelle assistance was unavailable, and no Hammer or Leanstral benchmark from other papers was run.', 'Our executed assistance study uses Lean 4.33.1, Z3 4.15.4, CVC5 1.3.3, and a local Leanstral-1.5 model. It uses constructed goals with explicit premises, rather than importing benchmark scores from other papers.')
# The old reconstruction description contained target-assisted diagnostics;
# the following explicit experimental boundary supersedes those observations.
reprs+=r'''
\paragraph{Inference boundary.}
A legacy reconstruction helper could move its prediction toward the supplied target, including returning the target vector itself. We exclude that helper from evaluation. The new consumer fixes its output alphabet from training-checkpoint keys, computes a direct source-conditioned projection, writes predictions, and only then invokes the scorer. It cannot choose a candidate against the target. This repairs the measurement boundary without retraining the stored weights. The decoder still consumes the source embedding itself; identity copying would attain cosine~1 and MSE~0. Consequently, the experiment measures how a learned projection generalizes, not compression or an independent test of textual meaning.

'''
theory=old[old.index('\\section{Multi-view translation and a coding example}'):old.index('\\section{Evaluation protocol}')]
evaltext=r'''\section{Experimental design}
\subsection{Data, separation, and budgets}
The frozen legal-source cohort contains 69 training units, 15 selection units, 38 fixed canaries, and 1,913 final-test units. The latter comprise 993 CFR, 738 MPEP, 175 U.S.\ Code, and seven guidance units. Eight exact-normalized aliases are retained as provenance but excluded from statistical denominators. Components were constructed before model evaluation from source-family, edition, and lexical/paraphrase relationships. The final set contains 20 operational components across four source editions, with one component containing 1,738 raw records. These are not 20 independent legal corpora. All training and selection units are CFR; the final cohort therefore includes substantial domain shift.

We froze inference code, checkpoint identities, compiler profiles, prompts, sampling, and metric definitions before opening final-test sources. Compiler inputs use the first 4,096 characters of each source; we report the resulting truncation count. Embeddings use the complete document under the original MiniLM windowing contract. The direct-model subset is the 100 units with the lowest salted-prefix hash of normalized source content. Its prompt contains source text and the target schema, with no compiler output or evaluation label. The subset comparison reuses the matching compiler rows; it is not a model result over all 1,913 units.

Compiler B has a five-second per-unit budget. C and its repaired counterpart have ten seconds, including their reconstruction cycle. Native structural checks finish before cycle evaluation, so a later cycle timeout does not erase an observed compilation result. Leanstral jobs are temporary, limited to 90\,GiB and four CPU cores, and terminated after active inference. Each model request is deterministic at temperature zero and permits one attempt. Proof requests allow 1,024 output tokens; direct formalization permits 2,048 tokens and at most eight formulas. Costs include failed startup qualification and completed attempts. Concurrent execution makes observed latency descriptive, rather than a controlled throughput comparison.

\subsection{Native compilation and reconstruction}
We distinguish the architectural pipeline labels A--E from the learning labels T0--T5. A is direct model formalization; B is a bounded typed deontic compiler; C uses typed multi-view IR; D adds property-specific checked bridges; E admits learned advice. The natural-source experiment executes A on 100 units and B/C on the complete cohort. D's proof machinery is tested on a separate constructed population. E's executed consumer is a learned check-order policy, not the broader proposed semantic-mutation route.

B invokes the native compiler and native semantic round-trip implementation with a deterministic source-derived vocabulary, capped at 1,000 atoms per category, and strict abstention on unsupported input. C invokes the native spaCy legal encoder, ModalIR compiler, and clause enrichment. It omits the full codec's knowledge-graph and embedding decoration, which are unnecessary for these representation checks. The recorded spaCy model configuration is used without fitting on the final set.

Two independent software checks test registered modal operators and typed formula fields, and bind normalized source content, identifiers, and span bounds. An empty, well-shaped IR may pass the schema; it does not count as nonempty coverage. These checks establish neither predicate truth nor legal interpretation. For reconstruction, we remove the original text, metadata, source identifiers, spans, and frame fields before native decompilation. Operator, predicate, condition, and exception fields remain because they are the representation being evaluated. Recompilation uses the same bounded source profile. Exact cycle agreement compares their formula multisets and excludes empty-to-empty matches from nonempty coverage.

T5 applies the previously developed executable exception-scoping patch to C. It separates exception predicates from governing actions and labels exception cues explicitly. The held-out comparison measures changed fields and structural regressions; it does not supply independent semantic labels for those changes.

\subsection{Learning and proof assistance}
T0 is the native cold projection. T1 adds the retained 69-entry sample memory. T2 contains shared parameters trained with memory disabled; T3 adds isolated structural-feedback heads. The three fixed seeds are 104729, 130363, and 155921. Each retained T2 run accepted one epoch with five packed update families; each T3 run applied 256 structural-feedback updates. We verified the original state hashes and extracted exact compact inference arrays. MiniLM re-encoding matched all 15 retained selection vectors bit for bit. T3 reconstruction values are reused from T2 only after exact equality of protected decoder state is checked; they are not an independent replication. T1 performs actual native memory lookups, with verified cold fallback on misses.

T4 evaluates the qualified learned priority through off/on/rollback execution on each source and seed. Every mode runs both checks. The priority is a learned global frequency prior, not a source-adaptive estimate of proof success. We measure activation, order, identical acceptance outcomes, and restoration of the baseline after rollback.

The proof study contains eight families, each with four valid and four invalid constructed goals: premise transfer, polarity, equality transport, integer identities, natural order, finite next-state preservation, dependent equality, and higher-order propositions. Native controls validate the labels, including explicit countermodels for invalid higher-order and dependent families. A fixed tactic baseline, SMT-guided reconstruction, and Leanstral receive identical theorem declarations. SMT statuses alone are never accepted as Lean proofs. Generated proof bodies must pass a fixed syntax policy and Lean kernel checking, with no admitted axioms. Five older development goals qualify serving but do not enter the 64-goal denominator.

\paragraph{Statistics.}
We report all planned denominators, separating abstention, timeout, malformed output, empty representation, and successful checks. Paired differences use 10,000 bootstrap resamples of the original source components with seed 104729. Domain-stratified unit resamples are secondary, conditional descriptions of this finite cohort. The dominant component and four-edition dependence limit generalization of either interval. Proof-study intervals resample the eight constructed families; these template variants are not independent real-world theorems.

\section{Results}
\subsection{Compilation and source-withheld reconstruction}
\input{../results/empirical_pipeline.tex}
\input{../results/empirical_pipeline_discussion.tex}

\subsection{Reconstruction, learned priorities, and repair}
\input{../results/empirical_learning.tex}
\input{../results/empirical_learning_discussion.tex}

\subsection{Native proof assistance}
\input{../results/empirical_assistance.tex}
The fixed baseline accepts all 32 valid controls, while SMT-guided native reconstruction accepts 24; the dependent and higher-order families fall outside the translator's supported fragment. Leanstral accepts 12 valid goals and no invalid control under the primary policy. Its remaining outcomes comprise 30 abstentions, 15 policy rejections, five native rejections, and two length-truncated responses. The totals refer to all 64 cases, including invalid controls. Thus the model does not improve on the baseline for these elementary goals.

A post-hoc interface sensitivity check admits two additional harmless syntax forms without editing or regenerating proof bodies. It adds three accepted valid proofs, giving 15/32 in that diagnostic. The primary result remains 12/32. This distinction matters because an admission-policy rejection is not necessarily a logical error. The local model also required an explicit tokenizer chat template: the GGUF lacked one, and the server's default format was inappropriate. We qualified the corrected framing and special-token sequence before the new proof requests.

'''
related=old[old.index('\\section{Related work}'):old.index('\\section{Limitations and conclusion}')]
related=related.replace('Our Hammer and Leanstral routes are the corresponding implemented mechanisms, but sealed-\\texttt{PATH} native checkers were unavailable, so we do not claim LeanDojo/Thor/Baldur performance.','Our executed solver and model experiments test this reconstruction boundary on explicit constructed goals. They do not reproduce LeanDojo, Thor, or Baldur benchmark performance.')
limitations=r'''\section{Limitations and conclusion}
The measurements support a bounded empirical conclusion: native compilation, learned projection, executable repair, and model-assisted proof checking can be evaluated separately within a shared architecture. They also identify the limits of the current implementation. A source span identifies where a formula came from, not whether it means the right thing. Exact reconstruction can preserve an incorrect interpretation. The embedding experiment has no compression bottleneck, its classification tables are empty, and its proof-feedback heads provide a global prior rather than source-adaptive confidence. The learned consumer schedules checks without changing which obligations must pass. The elementary proof study favors a simple native baseline.

Independent legal-semantic fidelity, full-document compiler coverage, and useful cross-view proof transfer from arbitrary natural sources remain open. The four-edition corpus, imbalanced connected components, source prefixes, and constructed proof templates restrict external validity. Our contribution is the implemented coupling of these mechanisms and a reproducible measurement of their actual behavior, including failures. Improving source interpretation will require explicit semantic targets and richer property-specific bridges, while keeping reconstruction diagnostics and proof acceptance distinct.\label{af-main-text-end}

\clearpage
\bibliographystyle{plainnat}
\bibliography{references}
\clearpage
\appendix
'''
appendix=old[old.index('\\section{Actual training and promotion execution}'):old.index('\\section{Historical recovery copy}')]
appendix=appendix.replace('T2 train/selection family cross-entropy is unchanged from T0; its cosine 1/MSE 0 uses the supplied target and is not a learned reconstruction gain.','Historical T2 train/selection family cross-entropy is unchanged from T0. The earlier cosine 1/MSE 0 diagnostic used the supplied target and is excluded from the current target-independent reconstruction experiment.')
appendix+=r'''
\section{Empirical execution and reproducibility}
\input{../results/empirical_execution.tex}
The anonymous supplement contains metric-level per-unit observations, fixed protocols, source/model identities, native proof receipts, and table-generation code. It excludes large model weights and private host paths. Complete local evidence retains raw requests, responses, compiler outputs, and exact state identities. Software qualification used constructed positive and negative cases and the selection set. Infrastructure amendments and failed attempts are retained; no final-source outcome was used to select a revised model or compiler candidate.

\input{llm_disclosure.tex}
\clearpage
\input{checklist.tex}
\end{document}
'''
(E/'editable/manuscript/main.tex').write_text(header+abstract+reprs+theory+evaltext+related+limitations+appendix)
print('Wrote new empirical narrative; numerical tables will be generated from completed runs.')
