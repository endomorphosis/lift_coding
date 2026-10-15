# Appendices and checklist — retained increment-016

> Reconstructed local reading view, created after the operator requested a new package. This is not the missing supplied v2 revision package. It uses only retained increment-016; its relationship to the originally supplied named PDF is unverified. Historical claims are transcribed, not newly authenticated or rerun.

The selected [PDF](../source_reference/main.pdf) and [LaTeX source snapshot](../source_reference/source_snapshot/main.tex) are preserved separately. The first part below is the exact `pdftotext -layout` reading view with page boundaries and original line numbers. PDF extraction can alter mathematical glyphs, ligatures, table layout, and hyphenation; do not use that text to reconstruct equations. The second part preserves the mathematical LaTeX expressions in an ordered source assembly. Original individual file bytes, not the inserted boundary comments, remain authoritative.

Appendices occupy PDF pages 12–30; the original checklist occupies pages 31–37. These labels describe the selected historical document, not the missing v2 manuscript.

## PDF reading view: appendices and checklist

### PDF page 12

````text
454   A    Full conditional argument record
455   The following audited statements are retained verbatim from the earlier formal argument record.
456   Their Equation 2, Algorithm 1, and statement identifiers name that record; they are not additional
457   final experiments or numbered algorithms in the main text. References to a sealed profile or the
458   absence of a campaign describe the scope of that argument audit. Later constructed corrections and
459   the cold comparison do not retroactively discharge its universal premises. The intended algorithm’s
460   bounded retry branch is architectural specification; the final empirical protocol permits no proposal
461   retry.

462   Conditional acceptance and reuse arguments (audited)
463   The statements below restate Equation 2, the accepted-lineage sketch, the dependency-projection
464   reuse obligation, the three acceptance questions, and Algorithm 1 with explicit scope, premises,
465   and conclusions. Every sketch is unmachine-checked: the sealed validation profile has no usable
466   z3, lean, coqc, or cvc5, and no independently checked proof artifact discharges these arguments.
467   Implementation evidence supports only the named tested premises. External side-effect atomicity
468   and universal dependency closure are not inferred. Unknown specifications stay visible.

469   Statement FA-EQ2 (acceptance invariant)

470   Scope. One publication of an accepted lineage root under a declared artifact policy. The statement
471   is a design invariant for that publication operation. It is not a theorem that every current write path
472   enforces the invariant, and it is not a claim about Git, remote stores, or physical effects outside the
473   tested expected-parent compare-and-swap.

474   Premises. Let s be the current accepted root, s′ a candidate successor, a the requesting actor, and q
475   the required obligation set. Write Publish(s′ ) for the unique accepted-lineage publication of s′ .

      Conclusion.
                          Publish(s′ ) ⇒ CurrentParent(s) ∧ Authorized(a, s)
                                           ∧ Scoped(a) ∧ CompleteManifest(q, s′ )                        (2′ )
                                                                       ′              ′
                                           ∧ EvidenceAdmitted(q, s ) ∧ CAS(s, s ).

476   Argument (unmachine-checked). If publication is defined to succeed only after those six gates,
477   then any published s′ satisfies them. The converse is not claimed: a candidate that meets the gates
478   may still lose compare-and-swap. Failed, stale, incomplete, or simulated attempts are not Publish
479   successors.

480   What the invariant does not establish. Properties omitted by the checked policy; truth of unsup-
481   ported or lossy translations; honesty of signed observations; atomicity of external side effects; global
482   consensus; or universal enforcement by unexamined write paths.

483   Statement FA-I31 (accepted-lineage induction)

484   Scope. Roots reachable solely through accepted publication transitions of the operation in FA-EQ2,
485   under a fixed statement profile Θ and policy predicate PΘ over artifact manifests.

486   Premises.
487         1. Initial-root policy. The initial accepted root satisfies PΘ .
488         2. Exact input. Required subject bytes and dependency references are verified before admis-
489            sion.
490         3. Complete manifest. The requirement manifest is complete under an admitted completeness
491            rule; membership of some units is not completeness.
492         4. Checker. Each accepted evidence item satisfies its designated checker relation and evidence
493            class.


                                                        12

````

### PDF page 13

````text
494        5. Translation bound. Lossy or unsupported translations cannot discharge source-level
495           obligations.
496        6. Current parent. Publication names the expected current parent.
497        7. Exclusive publication. Compare-and-swap linearizes concurrent same-parent writers; losers
498           are not successors.
499        8. Protected authority. Policy and checker identities cannot change under ordinary worker
500           authority.

501   Conclusion.    Every root reachable solely through accepted publication transitions satisfies PΘ .

502   Argument (unmachine-checked). Induction on the number of successful publications. The base
503   case is premise 1. For the inductive step, the publisher checks PΘ on the exact candidate manifest
504   and current parent before compare-and-swap linearization. Failed, stale, incomplete, or simulated
505   attempts are excluded from the successor relation, so they are not inductive cases. The induction
506   preserves only properties actually expressed by PΘ .

507   Nonvacuity. The successor relation is nonempty on the tested sealer: a complete current manifest
508   can publish, while an empty or incomplete mandatory manifest cannot. Deny-all publication would
509   make the invariant hold vacuously and is not a useful-progress witness.

510   Statement FA-I32 (dependency-projected test reuse)

511   Scope. Transfer of a previous setup/call/teardown observation of test t between states s and s′ under
512   a declared runtime/effect profile θ. The statement is a proof obligation, not a theorem of arbitrary
513   pytest execution.

514   Premises. Let Obsθ (t, s) be the relevant observation. Suppose there exist a complete projection
515   πD and a deterministic function fθ such that
                                            Obsθ (t, s) = fθ (πD (s))
516   on every state admitted by the reuse policy.

517   Conclusion. If πD (s) = πD (s′ ), then Obsθ (t, s) = Obsθ (t, s′ ). An admitted previous observation
518   may transfer only inside that profile and those assumptions.

519   Argument (unmachine-checked). Immediate from functionality of fθ . The difficult premises
520   are completeness and determinism of πD . Equal digests of incomplete manifests do not satisfy πD
521   completeness. Opaque, uncontrolled, or unknown fixture values, incomplete runtime traces, and
522   teardown failures do not discharge the obligation; they require execution or fail closed. A cold
523   full-run oracle and adversarial mutations can check an implementation; they do not prove universal
524   dependency closure. No such independent cold-oracle campaign is recorded here.

525   Statement FA-I33 (three acceptance questions)

526   Scope.   Any candidate action that might be described as “accepted.”

527   Premises and conclusions (separate).

       Question                       What a positive answer establishes, and what it does not
       Behavioral claim               The candidate program or model satisfies its stated obligation under
                                      the declared checker, environment, and evidence class. This is not
                                      permission to act and not publication of a lineage root.
528    Action permission              This actor may perform this action now under the bound lease,
                                      policy, scope, and roots. This is not behavioral correctness and not
                                      publication.
       Publication                    This candidate and its evidence become the current accepted root.
                                      This is not, by itself, proof that omitted obligations hold or that
                                      external effects occurred exactly once.


                                                       13

````

### PDF page 14

````text
529   Neither a proof of behavior nor a capability grant answers all three. Formalization fixes the statement;
530   authorization binds actor, tool, arguments, resources, effects, scope, time, and roots; execution
531   observations report what happened; publication chooses the accepted lineage.

532   Statement FA-ALG1 (composed supervision loop)

533   Scope. Algorithm 1 remains the intended composition: a control-flow specification, not a newly
534   executed full-loop result. It is labeled executed composition only on the steps supported by the
535   integrated guard-before-write witness. Passing isolated stop-path tests does not establish the complete
536   loop.

537   Intended algorithm.     Input: authorized query q, current source forest F , policy P , budget B.

538        1. Reconcile event, task, and artifact state; refresh F and derive G, O.
539        2. If cancelled or budget exhausted: return explicit non-success.
540        3. If every current obligation is admitted: return goal-completion verification.
541        4. Generate bounded task proposals; preview and separately admit ready work.
542        5. If no task is admissible: return wait-or-review, not goal success.
543        6. Claim the task; bind lease/fence, preimages, required context, and validation.
544        7. Choose a deterministic, authorized residual-model, review, or unavailable route.
545        8. If review or unavailable: record a blocked attempt; return to the event service.
546        9. Produce and apply a candidate only through checked isolated execution.
547       10. Rescan; derive Onew from authorized rules, not the worker’s pass claim.
548       11. Verify or reuse evidence; retain failed, unknown, and pending obligations.
549       12. If the failure is refinable: record a new residual; return a bounded retry.
550       13. If evidence is incomplete or unsafe: return defer-or-reject.
551       14. Persist the manifest; recheck current bindings; compare-and-swap the expected parent.
552       15. If publication conflicts: return reconcile, not completion.
553       16. Record the accepted task transition and updated F , G, O; reevaluate at line 1.
554       17. Propose procedure or policy learning separately; never self-promote.

555   Executed composition (integrated witness only). The integrated witness supports a frozen guard-
556   before-write cycle: authorized pre-state and obligation; counterexample; admitted deterministic route;
557   isolated patch application; independent tests; narrow cache reuse of an unchanged eligible receipt;
558   complete-manifest publication; and rejection of invalid, incomplete, and simulated non-completion.
559   Those steps correspond to intended lines 4, 7 (deterministic), 9, 11 (narrow reuse), 13, 14, and 16,
560   plus the negative reading of line 17 (no worker self-promotion). They do not execute the live event-
561   service loop, residual production-model dispatch, budget-exhaustion composition, wait-or-review,
562   procedure/policy learning, native proof, federation, or a matched A–D experiment.

563   Trusted limitations retained with the algorithm. Unknown or inconsistent specifications remain
564   visible. Incomplete projections cannot silently authorize reuse. External exactly-once behavior
565   outside the tested write-ahead-log / compare-and-swap / lifecycle boundary is not claimed. Optional
566   native proving and world/procedure extensions are out of scope unless a later task supplies an eligible
567   profile and consumed-result evidence.

568   B    Frozen comparison
569   Population and treatment. The eight recruited families are Tomlkit, installer, Tornado, more-
570   itertools, charset-normalizer, iniconfig, wheel, and Jinja. They are a convenience sample, not a
571   representative sample of Python repositories. Two arms and two nested repetitions yield 32 fixed
572   cells, 16 per arm. Repetition identifiers 104729 and 130363 identify design positions; they were not
573   served to the model API as random seeds.


                                                        14

````

### PDF page 15

````text
574   Before final outcomes, the A/B local-cold comparison was retained as an order-preserving subset
575   of the original 192-cell plan. The remaining 160 factor cells were withdrawn, and eight additional
576   target families were not recruited. C/D routing, warm caches, test reuse, publication efficacy, the
577   original sixteen-family inferential objectives, and D/A promotion comparisons remain outside this
578   experiment. The narrowed comparison is descriptive.
579   Arm A receives the selected public raw context. Arm B preserves the matched raw selection and
580   adds actual native source-linked semantic context. Sixteen exact family/arm request commitments
581   precede final generation; each arm’s two repetitions use its fixed request. This treatment changes the
582   combined request and cannot isolate semantic subcomponents or prompt compression. Public source
583   and native preparation remain separate from confidential acceptance tests.

584   One proposal and independent cold execution. Each cell permits one Grok 4.6 proposal POST,
585   requesting at most 4,096 output tokens through a strict structured edit response. There is no scientific
586   fallback, retry, served seed, or reasoning-effort parameter. A failed request consumes its original cell
587   rather than creating a replacement. The frozen order is executed sequentially.
588   Proposal execution uses one CPU, 2 GiB, and a 32-process limit. The nominal gateway and HTTP-
589   wrapper bounds are 600 seconds; the child bound is 595 seconds and the socket timeout is 590 seconds.
590   Compliance depends on actual measured intervals. A configured limit, missing measurement, or
591   nonfinite value is not evidence that the budget was met.
592   The operator retains exact candidate bytes and a specific AI review before eligible scoring. That
593   procedural review supplies no independent human annotation. Scoring runs separately in a cold,
594   network-disabled container with one CPU, 2 GiB, and a 128-process limit, bounded by 120 host
595   seconds and 115 child seconds. The scorer’s process limit was fixed prospectively for both arms and
596   all eight families because unchanged public concurrency tests require up to 100 threads. The earlier
597   32-process public-baseline failure remains recorded; proposal and native-preparation limits remain
598   32.
599   Useful completion requires an admitted candidate, nonempty public and hidden checks all passing,
600   and measured resource compliance. Failed, refused, expired, unscored, or incomplete cells receive no
601   useful-completion credit. Unknown states remain explicit and prevent a complete-cohort analysis until
602   their terminal accounting is resolved. An import or collection error with no hidden assertions executed
603   is incomplete validation, not an observed hidden behavioral assertion failure. Separate scoring and
604   sealed records do not establish comprehensive resistance to adversarial scorer manipulation.

605   Interruption and provenance. The original resource lease ended during cell 7. Its request, failure,
606   cleanup, and unknown termination-sender evidence remain retained. A separately admitted managed
607   lease and continuation runtime govern cells 8–32 without replaying the consumed prefix or changing
608   requests, model, order, scorer, limits, or analysis. Both runtime source versions remain explicit. The
609   lease is a cooperative allocation, not an exclusive physical resource reservation; per-phase process
610   boundaries apply the configured resource limits.
611   Continuation checks add work around effect admission and receipt signing. The signed gateway
612   interval ends before signing; whole operator invocation time extends through subprocess completion
613   and output flush/synchronization. These distinct intervals must retain their endpoints rather than
614   being presented as a single total host clock.

615   C    Analysis and evidence separation
616   For family f , arm a, and repetition r, let Yf ar indicate admitted useful completion. Average the two
617   fixed repetitions within each family and arm: Ȳf a = (Yf a1 + Yf a2 )/2. The retained contrast is
                                                      8
                                            ˆ︁ = 1
                                                     ∑︂ (︁                )︁
                                            ∆                Ȳf B − Ȳf A .
                                                 8
                                                     f =1

618   Families are the independent analysis units; 32 nested cells are not 32 independent repositories.
619   A descriptive robust-family outcome additionally requires both repetitions to succeed and is not a
620   promotion decision.


                                                            15

````

### PDF page 16

````text
621   The frozen bootstrap draws eight whole family blocks with replacement, sharing each draw across
622   arms and repetitions. It uses 20,000 resamples, Python 3.12 random.Random with seed 20260911,
623   lexicographically ordered family identifiers, and exactly eight randrange(8) draws per resample.
624   The 95% percentile endpoints use linear interpolation at (B − 1)p for p ∈ {0.025, 0.975} and
625   B = 20,000. These intervals are conditional, descriptive summaries of eight convenience-selected
626   families, not population-level coverage or superiority/noninferiority decisions.
627   Failures remain in the fixed outcome denominator. Resource summaries report their available-
628   observation counts and missingness. Provider child, HTTP wrapper, gateway, scorer, and operator
629   clocks can overlap and are not added as disjoint costs. Shared native preparation is counted once.
630   Baseline checks, prior failed attempts, review, queue waits, cleanup, and artifact work retain their
631   own accounting scopes. Token usage and cost ticks are telemetry; unavailable settled charges and
632   unmeasured effort remain unknown.
633   The developmental pilot is a separate four-family, 24-cell A/B study with three nested repetitions. Its
634   retained labels include ten useful completions, five per arm, from 24 POSTs and 12 scores. Ten child
635   durations exceeded 595 seconds by less than 1 ms, and pilot cell 20 exceeded 600 seconds in both
636   wrapper and gateway clocks. These deviations and labels remain preserved; the final resource policy
637   is not applied retrospectively to relabel the pilot.
638   Earlier boundary evidence is also separate from final repair outcomes. The mutation/cold comparison
639   retains one false reuse among all 26 cases, rather than reporting a selected zero-of-25 subset. All four
640   later correction invocations, including failed and partial attempts, remain visible; corrected full-cold
641   execution supplies no positive reuse credit. Constructed gate checks and public-baseline passes do
642   not count as useful final repairs.

643   D    Historical cold-study accounting details
644   Complete fixed-cohort accounting. All 32 planned cells have verified terminal records; none is
645   missing or replaced. The experiment made 32 original proposal POSTs and 16 scoring invocations,
646   of which 15 completed cold validation. Useful completion was 9/32 (28.125%): A achieved 5/16
647   and B 4/16. Table 3 reports the family counts. Failures remain in these denominators. The mean of
648   the eight paired family differences, B minus A, is −0.0625, or −6.25 percentage points. The frozen
649   20,000-resample whole-family bootstrap gives a descriptive 95% percentile interval of [−0.1875, 0].
650   Each resample draws eight families and preserves both arms and their nested repetitions. The interval
651   describes this convenience sample; it supplies no population-level superiority, noninferiority, or
652   promotion decision.

653   Concentration across families. Tomlkit yielded one useful completion per arm, Tornado two for
654   A and one for B, and more-itertools two for each arm. The other five families yielded none. Seven
655   family differences are zero; the Tornado difference is −0.5 and accounts for the aggregate gap. Its B
656   cell 012 (repetition 130363) ended in a transport failure without a response or scorer invocation. This
657   outcome remains part of the fixed comparison. The data do not isolate an effect of semantic content,
658   a particular native component, or prompt compression. The treatment changes the combined request,
659   and the recorded endpoint includes operational and provider failures.

660   Failure categories and incomplete validation. The remaining 23 cells comprise 14 proposal-
661   child deadlines, two known proposal failures, and seven records with the original signed label
662   hidden_acceptance_failed. The two proposal failures were cell 003 (Tomlkit, A, 130363),
663   which returned HTTP 503, and the transport failure in cell 012. Their known local termination
664   does not establish whether a remote charge occurred. Among the seven hidden-failure labels, six
665   completed cold validation and failed executed hidden checks. Cell 005 (installer, A, 104729) instead
666   passed 28/28 public checks but collected zero hidden assertions and ended with an import-name
667   failure. It is incomplete hidden validation, neither an observed hidden behavioral assertion failure nor
668   a demonstrated external infrastructure fault. Its original label and zero useful credit are preserved; no
669   candidate, test, or failed request was revised and rerun.

670   Measured time and unavailable costs. The provider-child, HTTP-wrapper, and signed proposal-
671   gateway clocks each cover 32/32 cells. Their medians are 472.777, 473.660, and 474.107 seconds,
672   respectively. The 14 deadline cells are resource-unqualified under the frozen measured predicates;


                                                         16

````

### PDF page 17

````text
673   configured caps do not imply that every measured duration complied. Scoring-gateway time is
674   available for 16/32 cells, with a median of 2.500 seconds across those invocations, including the
675   incomplete validation. Only one of eight families has complete scoring-time observations for
676   both repetitions of both arms. The frozen policy therefore leaves the paired scoring-cost interval
677   unavailable instead of imputing zeros or bootstrapping fewer families. Grant-to-terminal duration
678   includes waiting and bookkeeping: its median is 603.644 seconds and its maximum 10,938.574
679   seconds. These intervals overlap and are not summed. API usage is reported for 16/32 cells;
680   settlement is unavailable for all 32. No dollar total, complete effort cost, or net efficiency gain is
681   established.

682   Runtime and accounting deviations. The original lease ended during cell 007. Its consumed
683   failure and unknown signal sender remain recorded; a prospectively admitted continuation covers
684   only cells 008–032, with separately identified executable sources. The original requests, order, limits,
685   and analysis policy remain fixed. The 26 additive disclosures also preserve pre-effect launch errors,
686   bookkeeping takeovers, diagnostic corrections, and interrupted operator work. Cell 027 had sufficient
687   credential headroom at its metadata check but only 895.290 seconds at the later reservation, below
688   the intended 900-second margin; exact POST time is unobserved. Cell 029’s delayed bookkeeping
689   enlarges its grant-to-terminal clock without creating another scientific trial. Outer invocation durations
690   and work after signed-gateway clock sampling retain separate scopes and missingness. They are not
691   added to the signed gateway interval or treated as measured AI reasoning effort.

692   Evidence and comparison limits. Fifteen failed proposals lacked original candidate-binding files.
693   Their later unsigned sidecars describe the unchanged public inventory and an empty patch; they are
694   derived metadata, not returned model edits, recovered original files, or successful candidates. The
695   four-family developmental pilot remains separate: its 24 cells yielded ten historical useful labels, five
696   per arm, with retained timing deviations rather than retrospective final-policy compliance. Earlier
697   boundary evidence in Table 6 is also separate from final repair outcomes. The ablation scope in
698   Table 7 records unmeasured or withdrawn endpoints. C/D routing, warm-cache reuse, publication
699   efficacy, and the original sixteen-family inferential objectives are not evaluated by these 32 cells.


700   E    Explicit public development objectives

701   Twelve newly authored public examples make three original development objectives concrete using
702   their retained public titles and prefix-source APIs. They are not recovered historical issue text,
703   hidden acceptance checks or independent families. On unchanged XML, OAuth and Click prefixes,
704   respectively, 2/4, 1/4 and 2/4 examples conform. XML attaches namespace declarations to a descen-
705   dant when the declaring element has no ordinary attributes; OAuth authorization metadata raises
706   an AttributeError, including with explicitly supplied response types; Click help still enumerates
707   choices when their display is disabled. Public comparison cases exercise ordinary attributes, disabled
708   namespace processing, token-only metadata, visible choices and explicit metavar behavior.
709   All twelve examples run in three fresh processes under frozen 60-second bounds, with no setup errors.
710   An earlier run’s three missing-constructor-argument errors are retained as harness failures. The
711   revised OAuth setup uses actual token and endpoint classes and all required combined-server claims.
712   Full unchanged source inventories retain 16, 199 and 145 entries; actual imported modules bind to
713   those prefixes. A separate 545-check audit reconstructs predicates and source/process provenance
714   without further execution. The new objective manifest binds text, examples, repair surfaces and
715   public API sources. Together with the separately retained nine-example Pyparsing public-report
716   reproduction, these provide explicit development objectives for the original four-family matrix.
717   Independent scorer admission, complete operational trajectories and matched cache/component arms
718   remain required. No model or hidden scorer is called; example conformity is not a repair-success or
719   system-quality estimate.
720   A later qualification exposes a limit in the newly authored OAuth expectation. The original accepted
721   reference passes three of four public examples; combined server metadata omits one configured
722   response type. An independently authored configured-key-preserving candidate passes all four new
723   examples but fails the unchanged original acceptance check. Public-only API review does not
724   justify requiring the abstract-validator metadata probe to advertise every internal dispatch key. Exact
725   three-key equality is therefore an unqualified author assumption, retained diagnostically rather than


                                                         17

````

### PDF page 18

````text
726   imposed on original acceptance. This is a prospective contract correction before new model dispatch;
727   neither the original criterion nor the contrary observations are overwritten. It is not a proof that every
728   possible repair faces incompatible requirements. The supplemental native call’s missing enclosing
729   timer also remains unknown.


730   F    Additional benchmark qualification

731   An independently pinned SWE-bench Verified metadata projection [3, 8] supplies 500 candidate
732   repairs from twelve repository names. Ten of eleven prospectively selected two-issue pairs have
733   forward base-commit ancestry; one has reverse ancestry in PR-date order. A separate current
734   GitHub identity audit checks all 192 candidate/original repository pairs, finds no shared repository
735   or declared fork identities, and flags two shared-owner groups. This does not establish historical
736   code independence, portfolio separation or absence from model training. A later audit reports test-
737   specification problems in a selected hard subset and evidence of solution exposure in tested frontier
738   models [9]. Its selected-subset rate is not a whole-dataset error estimate, and it does not measure
739   contamination in our provider profile. Public examples exposed during this literature review are
740   separately recorded before any prospective split. No new confirmatory family or complete natural
741   trajectory is enrolled.
742   Requests 6028 has a separately named ARM environment preserving its public Python version and
743   thirteen listed Python package versions. The unchanged native SWE-bench 5.0.2 parser/grader ob-
744   serves all 187 designated checks in both controls: unfixed source passes 185 and fails the two required
745   failing checks; reference source passes all 187 and is the only resolved control. Both collected outputs
746   also contain eight missing-fixture setup errors outside the designated set. The original script lacks
747   a test-exit marker, so a zero container exit cannot establish acceptance. This is designated-check
748   qualification, not an error-free full-suite result or equivalence to the published x86 environment. Pro-
749   tected reference/test content remains in curator custody; model-facing selection reads public metadata
750   only. Earlier import and decoding failures are retained. Infrastructure qualification contributes no
751   provider-token or repair success observation for either treatment.
752   Requests 5414 subsequently qualifies in a new named ARM profile using its public development
753   dependencies and Docker’s default bridge network. Both controls complete all 131 designated checks:
754   unfixed source passes 130 and the reference passes all 131. The full parsed outputs have 288 versus
755   289 passes, respectively, with one expected failure each and no setup errors. The original offline port,
756   a dependency-build failure and a plugin-startup failure remain retained; the successful profile is a
757   development correction. This does not make the original failed port successful. A later candidate
758   grading service version fails its four-control qualification: three controls behave as expected, but
759   this node’s reference is not accepted despite all designated checks completing. Four existing public
760   network-timeout checks instead encounter a network-unreachable condition; the earlier standalone
761   run used the same image, package versions and evaluation bytes. The unique cause and a reliable
762   remedy are not established by this discrepancy. Eight service rejection controls pass. This retained
763   discrepancy illustrates why standalone benchmark qualification alone does not qualify a new endpoint.
764   A subsequently frozen service version passes one attempt at each of its four native controls and all
765   ten rejection controls. It preserves exact objective, profile, cumulative patch and resulting source-tree
766   bindings. Public network readiness probes bracket Requests 5414’s evaluation, with no automatic
767   retries; an incomplete grade remains unavailable for repair decisions. All eight qualification probes
768   pass. The 94-check audit retains 1,175 artifacts; the four control containers take 87.429894 seconds
769   in total. This qualifies the named service and its observed controls, without proving the unique cause
770   or remedy of the previous network failure or stability throughout future test runs. Candidate and
771   benchmark tests still share the original test process; adversarial oracle integrity is not established.
772   Requests 6028 retains its eight outside-set fixture errors.
773   An additive public-only cumulative-source control changes two production files and adds one Git-
774   ignored Python file. The service inventories all 98 resulting files, matches the independently expected
775   tree, and returns the unchanged unfixed grade of 185/187 in 6.048 seconds. This checks complete
776   source-carry transport into grading, not successful repair or an accepted multi-issue trajectory. Earlier
777   four-control cohorts remain unchanged.
778   A further pinned metadata-only projection yields 21,336 SWE-rebench rows [6] from 3,468 repository
779   names and 731 SWE-bench Pro rows [11] from eleven names. The 22,067-row sum is not deduplicated


                                                         18

````

### PDF page 19

````text
780   across datasets; protected issue, reference and test fields are not decoded in this projection. A
781   prospectively seeded screen uses 2025 metadata dates, available image fields, distinct base commits
782   and exclusion of prior repository/owner names. It yields 53 candidate pairs. All first sixteen pairs have
783   actual forward Git ancestry, and 448 comparisons against the 28 prior current repository identities
784   find no repository, declared-fork or owner match. Each candidate has a distinct current repository
785   and owner identity. These checks do not prove historical code independence, portfolio separation
786   or training novelty. Image-field eligibility is a convenience filter; all 32 selected image names
787   specify x86_64, whereas the evaluation host is ARM. Source/environment/scorer qualification and a
788   prospective confirmatory split remain open; zero new families are enrolled.
789   The first frozen additional pair, Zarr 2996 and 3015, subsequently passes four original native grading
790   controls on explicitly ported ARM environments. Unfixed source passes 16/22 and 157/158 designated
791   checks, respectively; each reference passes its complete set. Every control runs once, with zero retries
792   or provider calls. The native test-spec factory, test commands, parser and designated criteria remain
793   unchanged; the script port removes four Conda activation commands. The environments preserve
794   Python 3.11.11/3.11.14 and all 50/67 observed installed distribution versions, while architecture,
795   platform binaries and system-library builds differ. The local native fork reports version 4.0.3. Its
796   complete declared dependency installation failed because an ARM YSON binary distribution was
797   unavailable; a separately named local Docker backend uses the available Python implementation,
798   leaving cloud backends unsupported.
799   The four native grader container intervals total 10.647 seconds, excluding environment acquisition,
800   builds, Git preparation and audit. Earlier missing build-helper, project-version and Git-image-
801   reference failures remain retained. The full public collection probe collected 3,045 tests for 2996 and
802   exited zero; 3015 collected 3,123 but exited one during teardown with resource/unraisable warnings.
803   The targeted controls do not reproduce that teardown failure, and their success does not erase it.
804   As with Requests, the original script lacks a separate test-exit marker, and native shared-process
805   execution does not establish adversarial oracle integrity. These results qualify the four original
806   controls; candidate endpoint, complete trajectory and token economics require separate evaluation.
807   No confirmatory family is enrolled by these controls.
808   A subsequent Zarr candidate endpoint qualifies all nineteen frozen controls, with 190 audit checks: six
809   actual native grading calls, ten rejections before dispatch, two wrong-source containers stopped before
810   hidden grading, and one duplicate-ID rejection. Empty and cumulative-public candidates retain the
811   unfixed grades; reference production projections pass 22/22 and 158/158. Each projection preserves
812   the full original reference’s production and base-public bytes while omitting one ancillary added
813   document, then reruns the unchanged designated checks. This qualifies the projected candidates, not
814   transport of the full original patches. Non-Python edits remain outside this endpoint’s admitted scope.
815   Exact public base inventories contain 189/181 files, including the editable installation’s generated
816   version module. Cumulative controls make three production edits, including a Git-ignored addition,
817   and retain all 190/182 resulting files. The initial endpoint attempt failed before hidden grading
818   because of raw mode differences and its rejection of the ancillary document; a later preparation
819   attempt caught a no-op Git apply in a nested checkout. Both failures remain retained. The qualified
820   revision preserves image-exact modes and verifies actual edits in isolated Git repositories. Six
821   grader containers total 14.426 seconds within 30.363 seconds of outer service calls, including the
822   duplicate-ID control. Preparation, environment acquisition and audit are separate. There are zero
823   retries or provider calls. Context, accepted-source trajectory carry, publication and model efficacy
824   are not enrolled by this endpoint qualification; adversarial oracle integrity and non-Python transport
825   remain unqualified.
826   The second frozen additional family, Xradar, then completes its four original native controls on
827   explicit ARM ports. Issue267 has 11/13 unfixed passes and 13/13 reference passes; issue269 has
828   55/58 and 58/58. All designated cases complete, with one attempt per control and no provider
829   calls. Full original reference patches, including ancillary edits, are retained. The unchanged native
830   factory/parser/test commands govern both nodes. Public collection yields 354 and 356 cases with exit
831   zero. Each public prefix matches 106 original Git blobs, and all 22 data fixtures selected from pristine
832   public tests match their registry hashes, totaling 183,051,686 bytes; both images fetch them offline.
833   Both ports preserve Python3.10.17 and all 196 installed distribution records, including two project
834   distributions with natural imports resolving to the base-specific editable source. Four exact package
835   versions require ARM source wheels. Conda binary/build variants and optional compiled-feature


                                                         19

````

### PDF page 20

````text
836   parity remain unqualified. Retained failures include initial duplicate-project metadata ambiguity, a
837   missing ARM binary wheel, and a node-orchestrator key error after the shared runtime built. Versioned
838   corrections preserve runtime pins and do not retry grading. Failed and successful shared builds take
839   118.916 and 188.913 seconds; cached-wheel materialization takes 19.143 seconds, and the complete
840   node-build/import/cache/package/collection phase 31.950 seconds. Four native grader containers
841   total 69.044 seconds; these are scoped intervals, not complete recruitment cost. Environment and
842   native audits pass 373 and 129 checks, respectively, with 120 custody artifacts and 59 native source
843   files. Candidate endpoint, context, model trajectory, confirmatory enrollment and adversarial oracle
844   integrity remain unqualified.
845   For a later development experiment on the existing pyparsing snapshot, the current public issue
846   report supplies a concrete objective. Its nine examples reproduce the reported recursive-whitespace
847   defect on unchanged public source: eight conform to the reported expectation and one fails. The
848   report is frozen for that new experiment; its exact bytes at the original base date remain unverified. A
849   reproduced public example is not complete hidden acceptance.


850   G    Repository preparation and source custody

851   Repository context custody and preparation cost. A separate native producer/consumer qualifi-
852   cation retains all 302 regular files across the XML and pyparsing development snapshots, including
853   unparsed source. Its bounded semantic scope analyzes one of six and five of 154 Python files, respec-
854   tively; four dependency capsules grant no source omission. Four cold/incremental root-and-block
855   comparisons agree, four exact source expansions execute, and 22 negative controls reject. An added
856   caller checks required-source CIDs and current bytes because native freshness omits that mapping;
857   native “sufficient” flags are not behavioral authority. Full pyparsing scanning produces 3,957 symbols
858   and 55,859 edges, but the unmodified producer process does not finish within its 600-second bound.
859   Hoisting a repeated immutable node-CID index preserves the full XML state/root and reduces its
860   preparation from 64.838 to 26.296 seconds in one observation per profile. Full pyparsing still reaches
861   the 600-second bound after that change. Source retention and bounded integration therefore do not
862   establish affordable whole-repository preparation, context compression or repair efficacy. Three later
863   isolated profiles add a fixed-profile CID encoder, cached syntax validation and an exact literal-union
864   predicate. Across all five profiles XML state/root identity is unchanged and every native consumer
865   passes; each full pyparsing producer still hits the process deadline. In the last profile the producer
866   writes its result at 597.222 seconds before the 600.202-second termination; the native consumer does
867   not run. An earlier stage diagnostic had also assembled and verified a full bundle before timing out in
868   source-binding reads. Missing final output therefore does not prove that bundle construction itself
869   failed.
870   The literal-union change preserves all 55,859 actual link predicates against 3,957 node CIDs, an
871   embedded-CID rejection, 1,235 constructed comparisons and 64 native regressions. The indepen-
872   dently validated full bundle has 67,872 blocks and agrees with the last producer’s state/root. Its
873   72.358 versus 2.834 seconds measure only one diagnostic predicate pass per implementation on a
874   shared host; they are not a whole-pipeline speedup estimate.
875   A generic current-repository service separately checks exact source inventory, file modes and ob-
876   jective/request identities. Twelve controls pass across three XML preparations: a source change
877   requires new state/root/pack identities, whereas an objective-only change retains state/root and creates
878   a new pack. Both public Requests nodes then complete actual native producer/consumer roundtrips,
879   retaining 97 files each and scanning all 35 declared Python files. Eleven negative controls pass per
880   node; neither node permits any raw-source omission. These are context and custody checks, with
881   zero provider calls and no repair-quality or compression comparison. Four subsequent Requests API
882   expansions return 79,942 exact raw bytes across two real read processes, preserving source, request,
883   freeze and objective identities. They add no omissions or model calls.
884   A sixth isolated profile memoizes identity only within an exact immutable native state instance under
885   frozen codec/runtime bindings. Both full producer processes and their separate native consumers now
886   complete. XML preparation takes 9.103 seconds; pyparsing takes 566.254 seconds, with 553.516
887   CPU seconds. The latter producer process takes 569.609 seconds and its consumer 1.740 seconds.
888   All 302 regular files and 11,781,935 bytes are materialized; pyparsing’s additional opaque symlink is
889   retained without following it. Both sources’ previous available state/root identities agree, including


                                                        20

````

### PDF page 21

````text
890   the independently checked 67,872-block pyparsing bundle. All 22 binding/tampering controls pass
891   and all 7,255 frozen runtime source files remain unchanged. Zero source omissions and zero signed
892   receipts are retained, along with the unresolved semantic frontier.
893   The profile passes 159 native regressions. Separate full XML unchanged, comment-change cold
894   and comment-change incremental states preserve serialized identities and all 1,992 reachable blocks
895   across the parent and memoized profiles. Each profile performs twenty actual source materializations
896   and rejects twenty corrupt-source reads. This qualifies immutable-object identity caching, not
897   execution/proof reuse or a defense against reflective mutation of frozen objects. The successful
898   full run establishes completion within the bound, not a replicated speedup or token benefit; the five
899   previous deadlines remain results.
900   A subsequent frozen full-pyparsing comment-change comparison fails cold versus incremental
901   equality. Its three workers complete within a separately declared 900-second bound: baseline 656.008
902   seconds, changed cold 609.801 seconds and changed incremental 784.021 seconds. Baseline and
903   changed-cold workers run concurrently on the shared host; incremental restoration, full source guards,
904   native previous-state/bundle loading, persistence and process exit are included in its worker interval.
905   Earlier driver enrollment copy/freeze creation is not separately timed. These observations establish
906   no incremental speedup.
907   The changed snapshot, symbols and artifacts agree, but 1,568 of 55,859 edge records differ: 1,564
908   ambiguous candidate edges change resolution metadata from finite_may to definite, and four
909   derived references change with their edge identities. All retain conservative confidence and multiple
910   candidates. Consequently state and semantic-root identities differ. Independent comparison reads
911   every persisted block: 65,856 shared CIDs have identical bytes, with 2,016 distinct CIDs on each
912   side, covering links, capsules and their indexes and roots. Both stores contain 67,872 blocks; their
913   payloads total 112,728,034 cold versus 112,724,906 incremental bytes. Ten source-read controls
914   pass and 7,255 runtime files remain unchanged. The driver exits one at the equality assertion after
915   all workers exit zero; this is a retained graph-metadata failure, not another preparation timeout. A
916   later actual native explanation-consumer probe loses the ambiguity limitation on all 1,564 directly
917   changed edges while retaining their conservative-confidence limitation; four derived references are
918   excluded. The fresh process takes 3.070 seconds and rechecks 7,255 runtime files. This establishes
919   an explanation-output consequence, not an execution authorization or soundness failure.
920   A subsequent isolated guard refuses previous-state frontend reuse when graph projection has already
921   replaced a lexical target with a concrete symbol. Such paths are reanalyzed from current source before
922   whole-inventory resolution; the guard does not simply preserve stale resolution metadata. Seven
923   changing inventory controls preserve state, roots, all block bytes and explanations. The full pyparsing
924   comment-change comparison then restores exact serialized state/root equality and all 67,872 block
925   payloads (112,728,034 bytes), also matching the earlier cold output. It reuses 20 of 154 Python paths,
926   172 symbols and 1,428 original frontend edges, while rescanning 134 paths. These counts are not
927   omitted source bytes or avoided execution checks.
928   The two fresh workers run concurrently under unchanged 900-second bounds: cold takes 437.699
929   seconds and guarded incremental 614.522 seconds. The latter includes 107.173 seconds of prior-state
930   restore/reverification and 55.736 seconds of scanning; graph construction and full verification still
931   execute. The earlier 656.008-second baseline preparation is reused as an artifact and remains a
932   separately incurred cost. Enrollment copying/freezing is not timed; the subsequent independent byte
933   audit takes 3.625 seconds. Nine new source controls pass and 7,255 runtime file digests remain
934   unchanged. Native regression tests retain 187 passes and one failure: an existing performance
935   expectation requires reuse of a path that this correctness guard deliberately rescans. An earlier invalid
936   authored fixture is also retained. A further inventory control exposes the guard’s limit: adding a
937   previously missing imported module leaves incremental confidence conservative while cold analysis
938   becomes exact. The guard’s successful comment-only comparison remains valid, but it is not a
939   general lossless solution. No execution-soundness consequence is inferred.
940   A new profile instead persists the original Python frontend observations before pytest unification
941   and graph projection. It binds their exact sidecar bytes to the accepted parent state, source inventory,
942   namespace and extractor/runtime profile; unsupported or stale inputs fall back to current analysis.
943   Current pytest analysis and whole-inventory graph resolution still run. The full comment-change
944   comparison reuses 153 of 154 Python paths, 3,885 original symbols and 52,977 original edges,
945   extracting 772 edges from the changed file. Cold and incremental serialized state, root, all 67,872


                                                         21

````

### PDF page 22

````text
946   blocks/112,728,034 bytes and the complete sidecar agree. The native state and blocks also equal
947   the earlier cold output. Each sidecar adds 53,753,923 bytes of storage. Ten bounded equality cases
948   and sixteen rejection/fallback checks include the earlier unresolved-import confidence case; ten full-
949   worker source controls pass and 7,256 runtime hashes remain unchanged. Accepted honest producer
950   custody remains an assumption: hash binding alone does not prove that arbitrary observations follow
951   from source.
952   All three new workers finish within frozen 900-second bounds. Baseline sidecar bootstrap takes
953   231.354 seconds in addition to the separately paid original 656.008-second preparation. Changed
954   cold takes 440.276 seconds and incremental 607.971 seconds. Incremental includes 105.262 seconds
955   of parent restoration and verification, 55.520 seconds of scanning with observation decode/encode,
956   390.254 seconds of bundle construction, 48.819 seconds of full verification and 4.727 seconds of
957   persistence. Bootstrap overlaps changed cold; incremental follows bootstrap, for 839.328 seconds of
958   new worker schedule time. Enrollment takes a separate 0.533 seconds and the independent audit 5.958
959   seconds. Nested stages are not added again to process totals. This qualifies actual original-observation
960   reuse on one full public change; incremental preparation is still slower, and zero source omissions or
961   provider calls establish no token saving or general speedup.

962   H    Combined controller, publication and recovery
963   First combined controller qualification. A new caller joins actual native context reads, source-
964   bound semantic analysis, symbolic routing, compiler-mediated world memory, isolated behavioral
965   scoring and a durable effect journal. On the four existing constructed routing tasks, two supported
966   initial repairs pass and two remain residual-pending with the provider disabled. Authored follow-up
967   events consume accepted source, recheck a comment change and reject a stale local parent. Ordinary
968   no-op detection receives the same current behavioral checks as the memory path. Three actual process
969   interruptions exercise validated continuation, durable receipt reconciliation and an executed effect
970   whose completion remains unknown; the unknown effect is held without redispatch. Across thirteen
971   events there are nine local acceptances, two pending residuals, one stale parent and one unknown
972   effect. These event counts are not thirteen independent repair tasks. Thirty scorer attempts yield 29
973   durable terminal receipts. Local ledger CAS is not native Kit publication; sealing, lifecycle reuse and
974   certified procedures are not yet combined here. With zero provider calls this qualification establishes
975   no integrated token-savings effect.

976   Subsequent native publication profile. The separately frozen eight-event sequence yields six
977   acceptances, one stale branch and one pending residual. A full checkpoint at generation 0 is followed
978   by a delta at generation 1. A real service exits with code 94 after native seal persistence and before
979   CAS. A fresh process loads the pending seal, rechecks the entire parent chain and exact local evidence,
980   replays visible and audit behavior, then completes native CAS/WAL through an explicitly added
981   development adapter, reaching generation 2. Another fresh event consumes the native stored accepted
982   source and publishes generation 3. A branch based on generation 0 reaches native publication and
983   loses with a generation mismatch.
      Table 4: Actual work in the eight-event native publication qualification. Event outcomes are dependent
      continuation observations.
                          Operation                                                Count
                          Controller invocations / terminal effects               9 / 68
                          Native context reads / source expansions                 4/8
                          Input scans / accepted-candidate scans                   8/3
                          Symbolic attempts / produced candidates                  4/3
                          Native routing calls                                         8
                          World-memory service calls / compiled actions           11 / 2
                          Publication attempts / native reads / recovery         7/4/1
                          Controller / additional admission scorer processes     18 / 24
                          Provider requests / provider tokens                      0/0

984   Invocation wall time is 60.906438 seconds; the additional 24 behavioral replays consume 13.759197
985   seconds within that total, not as a separate additive cost. Context enrollment, inventory freezing,


                                                        22

````

### PDF page 23

````text
 986   implementation and read-only audit are outside this runtime denominator. Crash-time work is retained
 987   through a durable receipt, and recovery does not double-count its aliased completion. Both ordinary
 988   and memory paths run the same cheap current-source check and accept no-op revisits without
 989   symbolic or model repair. The compiled memory action dispatches an actual check; no reduction in
 990   checks is demonstrated.
 991   The complete required leaf set is externally frozen: accepted source, semantic preparation, effect
 992   inventory, visible behavior and audit behavior. Every changed candidate receives a new native
 993   scan. All five leaves are replaced per delta. Native integrity verification checks content and digests;
 994   unsigned local receipts additionally depend on trusted controller/scorer execution, a durable effect
 995   ledger and an evaluation-owned CID index. This is neither a theorem about arbitrary Python nor
 996   production trust admission. Stored parent chains are recursively checked and the requested source is
 997   behaviorally replayed on read. Broader crash phases, concurrent publication, provider effects, real
 998   repository edits and lifecycle reuse remain open.
 999   The read-only audit passes 6,424 checks. The archive retains 504 source and metadata files, including
1000   483 native source files across the loaded closure and preceding context enrollment. The first profile’s
1001   omitted imported wrapper and the first audit’s pointer-envelope parser failure are retained. Correcting
1002   the audit did not rerun behavioral outcomes; the archived previous controller still passes its original
1003   9,188 checks.

1004   Full-repository service fixture and measured cost. A separate curator-held Requests 6028 fixture
1005   begins with its reference candidate and then adds a neutral comment to the same accepted production
1006   source. Both states contain all 97 source files. It executes two full native context preparations, four
1007   world-memory service calls and six original native grader invocations: two initial checks and four
1008   fresh publication, interruption, recovery and read replays. All six complete the 187 designated checks.
1009   Reference and hidden test payloads remain in curator custody. This fixture does not execute the
1010   Requests 5414-to-6028 upstream transition or any model repair, and it does not establish adversarial
1011   oracle integrity.
1012   The first full checkpoint reaches generation 0. The second process constructs a delta and actually exits
1013   with code 94 after seal persistence but before CAS. A fresh process recovers generation 1; another
1014   fresh process reads and restores the exact second accepted source. Wrong-tree, wrong-receipt, source-
1015   drift and incomplete-effect controls all reject before grader replay. All four required leaves—accepted
1016   source, semantic preparation, observed non-sealing effects and native behavior—are replaced on
1017   transition. The effect leaf excludes all sealing operations, including prior reads; the outer workflow
1018   ledger must still count their actual work. Parent/source admission and fresh grading are additional
1019   checks. Unsigned local receipts and native integrity mode establish neither a theorem of execution
1020   nor verification reuse.

       Table 5: Measured disjoint sequential intervals for the Requests 6028 curator fixture. Grader processes
       are nested in these phases and are not added again.

                    Phase                                                Count     Wall seconds
                    Full native context preparation                           2         318.283
                    Initial accepted-candidate checks                         2          16.047
                    World-memory service calls                                4           5.858
                    Publication/recovery/read and rejection controls          8          37.037
                    Sum of measured intervals                                           377.226


1021   The six grader containers consume 31.625 seconds within the measured intervals. Their four replay
1022   service wrappers are also nested, not independent extra costs. The frozen-start-to-result artifact
1023   span is 377.640 seconds; this is not a separately instrumented whole-process timer and excludes
1024   earlier imports and profile creation. Later code archival and read-only audit take 0.275 seconds
1025   together, outside the fixture intervals. There is one shared-host observation, no parallel comparison
1026   and no provider calls. The 275-check audit retains 33 public code snapshots and hashes 1,136 private
1027   artifacts. This closes the stated service controls while leaving multi-issue model efficacy, token
1028   savings and broader crash coverage open.


                                                         23

````

### PDF page 24

````text
1029   Natural Requests sequence: intervention and failure paths. The first live repository cohort
1030   contains one development family, two genuine public issue nodes and four arms, executed in frozen
1031   D/C/A/B order with independent local cold stores. Each trajectory has at most four provider requests,
1032   with at most two at its first issue; unused slots carry forward. All planning, proposal, expansion
1033   and recovery purposes share that ceiling. The common Grok 4.6 low-reasoning profile has a 2,048-
1034   output-token limit and a 65,536-byte request limit. Source retrieval selects whole production modules
1035   with three-file/48,000-raw-byte limits, and exact requested expansions replace the earlier selection.
1036   Accepted first-node source is committed on its exact public base and carried through a real three-way
1037   merge with the next base. No reference patch enters the model or its public history.
1038   A uses ordinary lexical retrieval and the common current-source check. B actually prepares and reads
1039   native context, but zero omissions qualify, so its model context falls back to the same raw source.
1040   C additionally runs native analysis, bounded synthesis and routing; its native candidate fails before
1041   the model repairs the first issue. D adds actual world-memory services, accepted-source context
1042   preparation, native publication and stored-source read. It remains partial: lifecycle reuse, certified
1043   procedures, learned world utility and integrated theorem proof are absent. Native permitted model
1044   routes share the same fixed provider profile, so model-tier selection cannot explain cost differences.
1045   Each arm retains its own histories and state; the effect journal provides durable identities for every
1046   arm.
1047   All four initial requests have identical canonical bytes and 13,693 provider input tokens. Each returns
1048   one independently passing first-node repair. A and B receive 13,568 cached input tokens each, versus
1049   512 each for C/D; local cold state therefore does not imply equal remote cache state. Returned
1050   reasoning and output lengths vary. Small first-node total-token differences cannot be attributed to
1051   source compression or a witnessed avoided model call.
1052   A/C/D’s accepted edits each conflict in the next public source merge. Their retriever appends the
1053   required conflict module to its ordinary selection, yielding four modules, 80,552 raw source bytes
1054   and a 91,202-byte request. The frozen 65,536-byte gate halts before dispatch. B’s different initial
1055   edit merges without a conflict and its next request fits at 53,319 bytes. Its three subsequent candidate
1056   grades are 184/187, 185/187 and 185/187, all unsuccessful; the original current source passed 185/187.
1057   The second node thus fails in every arm, through different observed paths. Source-bound halts are
1058   retained failures, not successful symbolic closures.
1059   The complete fixed-cohort provider totals are 14,428 (A), 65,695 (B), 14,589 (C) and 14,269 (D),
1060   summing to 108,981 across seven actual posts. Each arm has one accepted node, so tokens per
1061   accepted node equal those fixed-cohort totals; tokens per completed trajectory are undefined. All un-
1062   successful model attempts remain charged. The first-horizon totals are 14,428/14,192/14,589/14,269
1063   in A/B/C/D order. These are observed cumulative costs, not counterfactual quality-versus-budget
1064   curves or independent repeats. Charges, cached input, visible output and reasoning components
1065   remain separate in the retained provider receipts; account settlement is not inferred.
1066   The original driver terminates with exit 143 while B’s first controller is still running. That same
1067   worker finishes and commits its accepted event. A separately frozen reconciliation checks the exact
1068   terminal output, journal, source/profile identities and absence of pending effects, then executes only
1069   the original remaining B6028 event. B5414 is never restarted. Its outer invocation time, waited
1070   CPU and exit status remain unavailable; the controller’s own 209.770-second timer survives. B’s
1071   two controller intervals sum to 408.510 seconds, which is a different timing scope from other
1072   arms’ enclosing invocation intervals. Docker workload CPU is unavailable throughout. Preparation,
1073   grading, memory and publication/read phases are nested within runtime and must not be added twice.
1074   Development qualification and source/environment acquisition remain separately scoped overhead.
1075   A/C/D enclosing intervals are 96.745, 285.790 and 507.358 seconds, respectively; B’s enclosing total
1076   is unavailable.
1077   The separate ledger audit passes 1,769 source, journal, request, attribution and budget checks. It joins
1078   all seven model receipts to their actual effects and dispatch intents, with no unknown provider effects.
1079   Sixteen unique native grader receipts include the two additional D publication/read replays; repeated
1080   appearances of saved completions are not new calls. Model and effect accounting are complete for
1081   this cohort, while outer runtime accounting remains incomplete because B5414’s enclosing timer is
1082   missing. The source archive contains 504 files. Preparation records include observed native imports;
1083   the source-expansion process lacks a separate actual import receipt, which limits the demonstrated
1084   execution closure. The quantitative result is not a production trust admission.


                                                         24

````

### PDF page 25

````text
1085   One family with implementation failures and uncontrolled server caching cannot identify a general
1086   mechanism effect. Equal accepted-node counts also conceal the different second-node opportunities.
1087   No arm completes the intended natural trajectory, and the broader cache, warm-horizon, ablation
1088   and independent-family program remains required. Subsequent transport corrections receive a new
1089   profile; these outcomes and request bounds remain unchanged.

1090   Second natural Requests cohort. A separately frozen conventional retrieval correction gives
1091   mandatory conflict modules priority, followed by optional lexical source that fits the existing three-
1092   file/48,000-raw-byte/65,536-request-byte bounds. A detached driver retains all eight outer invocation
1093   timers without restart. On actual B/D continuations, the conflict and two optional modules fit in
1094   47,424 raw bytes and a 54,773-byte request. A/C’s different accepted first edits merge cleanly. All
1095   four first requests remain byte-identical within this cohort. No source omission or successful symbolic
1096   closure occurs; D still lacks integrated lifecycle reuse, certified procedures and learned memory
1097   utility.
1098   All sixteen calls execute and consume 243,255 provider tokens, including expansion decisions, failed
1099   proposals and local transport failures. A uses two calls per issue, while B/C/D use one then three.
1100   Each accepts only issue5414. A’s first proposal passes 123/131 designated checks; the next passes.
1101   For issue6028, A spends one call expanding source and one on a candidate grading 185/187. C
1102   expands once and grades two candidates at 185/187. D grades its first and third candidates at 185/187;
1103   their cumulative patch bytes are identical. B grades one candidate at 185/187. The remaining three
1104   outputs, one D and two B, restore all 97 pristine file contents but retain mode0644 instead of0664 on
1105   one file. The frozen transport rejects these mode-only differences; its text-edit interface has no mode
1106   channel. Those three provider calls remain charged, no graders run for them, and their counterfactual
1107   grades remain unknown. No retrospective repair or rerun alters this cohort.
1108   Fixed-cohort tokens are 56,543/62,439/63,336/60,937 in A/B/C/D order; first-node cumulative tokens
1109   are 29,787/14,782/14,364/14,163. Tokens per completed trajectory are undefined. Total components
1110   are 227,336 input, 1,804 visible output and 14,115 reasoning tokens; 47,744 cached input tokens
1111   are a subset. Cached-input counts are 1,024/30,976/14,720/1,024, so local cold starts do not control
1112   provider caching. API-reported charges total $0.1627138000; settlement is unmeasured.
1113   All 21 unique grader calls complete: nineteen direct and two D publication/read replays. Six passing
1114   and fifteen failing grades include repeated validation of the same task and are not independent success
1115   counts. Their 509.499 seconds of container time are nested within 544.910 seconds of outer grader
1116   service, which is itself part of runtime. The 53 unique outer effects have complete elapsed timers.
1117   Enclosing invocations total 1,382.526 seconds. Native context contributes 106.468/211.192/213.978
1118   seconds for B/C/D; D publication/read, including replays, takes 78.228 seconds. These components
1119   are not added twice. Docker CPU and driver-preflight CPU remain unknown. The logical runtime-
1120   state snapshot contains 5,495 files/297,870,884 bytes, excluding qualification and private scorer
1121   stores; it is not deduplicated physical usage.
1122   The prospectively fixed detailed audit passes 3,698 checks; independent root aggregate and final joins
1123   reconcile all costs, nodes and 510 archived sources. The final root join passes 1,412 checks after
1124   retaining an initial projection-ID assumption failure and joining explicit residual/enclosing event
1125   identities. The curator independently joins all 21 requests, dispatches, receipts and outer completions,
1126   with no unknown effects. All 310 observed worker/world/sealing imports match the archive; a
1127   separate native context audit binds 163 observed producer/consumer paths and all ten context effects.
1128   Expansion lacks a separate actual-import receipt, and standard-library/third-party import closure
1129   is not established by these native-prefix receipts. The follow-up supports no token saving and is
1130   not pooled as an independent confirmatory replication. Original cache, operational-sequence and
1131   component comparisons remain required.


1132   I   Native proof profiles and exact statement checks

1133   A real native proof relation. The copied native backend was built offline with locked dependencies
1134   because the bundled binary did not implement the source’s v3 circuit. Isolated development keys
1135   support a four-leaf Event-DAG Merkle/count relation. Three actual proofs for counts 1, 2 and 4 verify;
1136   eight witness, public-input, proof and key mutations reject. Primary setup takes 7.810 seconds, proof
1137   generation 12.048–12.474 seconds, and verification 3.053–5.147 milliseconds; serialized proof JSON


                                                         25

````

### PDF page 26

````text
1138   is 1,484 bytes. The raw verifier accepts a different outer root that maps to the same field element.
1139   The evaluation caller’s exact-root/count and key/binary checks reject that alternate statement before
1140   dispatch. This boundary is part of the result: the native relation alone does not bind arbitrary outer
1141   metadata. Development setup is not production trust admission, and a Merkle relation is not proof
1142   that arbitrary tests executed. The v5 pytest-attestation circuit remains unsupported in this backend.

1143   The original bounded Horn profile. The source-built v2 backend also produces and verifies
1144   three honest implication chains of lengths 1, 2 and 4. Setup takes 1.101 seconds, proving 2.238–
1145   2.390 seconds, and verification 3.187–5.267 milliseconds; each proof JSON is 1,700 bytes. The
1146   honest prover rejects the tested incomplete or inconsistent inputs. When the scalar public inputs
1147   remain unchanged, the raw verifier accepts three changed outer metadata fields; exact statement and
1148   source/key checks at the evaluation caller reject them before dispatch. Honest examples and wrapper
1149   checks do not establish that every satisfying circuit witness corresponds to the advertised textual
1150   axioms. That stronger assurance remains unconfirmed.

1151   Actual accepted-history archive integration. A separately frozen producer/consumer profile
1152   follows the constructed controller’s native generation-3 pointer through four accepted seals, each with
1153   five required receipt units. It excludes the stale unaccepted branch and the separate ordinary trajectory.
1154   Producer and fresh consumer use native Kit verified reads on exact archive clones, reconstruct the
1155   original local effect receipts and check the complete source, parent and leaf bindings. The original
1156   archive and controller ledger remain unchanged. No behavioral checker is rerun; the original local
1157   execution remains the authority for its recorded observations.
1158   Each canonical event commits its seal/parent, source and original binding, complete receipt-CID
1159   map and verified pack digest. The already qualified standard v3 backend proves their four-leaf
1160   archive relation. The consumer checks the externally expected full root/count and exact binary/key,
1161   in addition to the accepted pointer and chain. The raw scalar-root limitation still applies; the proof
1162   does not establish that arbitrary code or tests executed correctly. The stopped custom-v2 investigation
1163   is not used.
1164   One honest proof and one runtime pairing verification complete. Producer and fresh-consumer
1165   read processes take 0.325531 and 0.342170 seconds, proving 12.617511 seconds and verification
1166   0.006725 seconds. The measured driver totals 14.749495 seconds, including source/key/archive
1167   hashing, clones and negative controls. These phases are nested. Earlier backend compilation, the
1168   original 7.810198-second development key setup and historical controller execution are separately
1169   scoped costs. A later audit adds a 0.006085-second native verification. This is one shared-host
1170   observation with existing keys, not a replicated speed comparison or evidence that proving beats
1171   direct hashing.
1172   All seven frozen controls reject: missing/corrupt receipt bytes, incomplete leaf inventory, stale parent,
1173   reordered events, changed event source commitment and changed full root. Four exercise the native
1174   reader; the last three reject at exact statement binding before pairing. The proof JSON is 1,484 bytes;
1175   the original 69-file store contains 2,010,722 bytes, including additional unselected records. A small
1176   proof does not replace the original source/receipt custody that the consumer still reads. The separate
1177   audit passes 218 checks, recomputes all event digests and the full Merkle root, and archives 34
1178   observed source files. The audit shares the cryptographic backend. This establishes no new behavioral
1179   check, model call, execution reuse, token saving or production admission.

1180   Actual Requests accepted-source archive. A separate post-cohort consumer uses the actual
1181   Requests cold-v2 D5414 checkpoint. D6028 failed and contributes no accepted seal. This single
1182   event has four required units: accepted source, native behavior, semantic preparation and complete
1183   non-sealing effects. Two fresh processes read exact archive clones through native verified-byte
1184   storage and admission, recheck original source, patch, objective, environment, context and effect
1185   bindings, and restore all 97 files with exact bytes and raw modes. The original 118-file archive
1186   and ledger remain unchanged. This explicit archive load dispatches no new grader; the historical
1187   controller’s ordinary read included a grader replay.
1188   The event digest includes the complete pack, required receipt CIDs and source inventory. One honest
1189   standard v3 proof commits its root/count with three padded leaves. Proving takes 11.978556 seconds
1190   and runtime verification 5.255706 milliseconds; direct producer/consumer read-and-restore take
1191   0.419219 and 0.423702 seconds. The complete 14.737743-second driver includes these costs, cloning,


                                                          26

````

### PDF page 27

````text
1192   hashing and all controls. An additional 0.278576-second audit includes one 7.364014-millisecond
1193   verification; previously metered key setup and cohort execution are separate. The proof is 1,484
1194   bytes, while its supporting archive occupies 12,514,534 apparent bytes. This consumer retains direct
1195   evidence checks; the proof adds overhead and establishes no amortized or token saving.
1196   Eight frozen mutations reject. Missing/corrupt behavior receipts, omitted units, changed parent
1197   and changed source binding fail archive admission. Changed event, full root and count fail exact
1198   outer-statement binding before pairing. The changed-parent checkpoint is looked up under delta
1199   kind and rejected before cycle traversal; the initial auditor expected a later kind/cycle error. Its
1200   failure is retained, and a separate corrected auditor checks that exact earlier lookup rejection without
1201   rerunning the experiment. The audit passes 1,462 checks and archives 514 source files. It shares the
1202   cryptographic backend. This is actual repository archive consumption, not inline proof use in the
1203   original cohort, a proof of arbitrary test execution or production admission.

1204   J   Signed native procedure execution
1205   The surviving saved bounded-sequence candidate now passes native seven-layer verification, cer-
1206   tificate issuance, certificate admission and TEST interpreter execution. Its exact procedure identity
1207   is retained. A local TEST-only HMAC signer and trusted immutable-input custody provide this
1208   development admission; the selection receipt grants no native registry promotion or production
1209   authority. The arithmetic candidate is not relabelled as a repository-repair procedure.
1210   The prospectively frozen corpus contains 32 test, 24 adversarial, 48 held-out and 32 shadow in-
1211   puts, disjoint from the original exposed inputs and one another. All 136 native executions match
1212   independent decisions: 13 true and 123 false. False is a computed answer, not an execution failure.
1213   Six handlers per input produce 816 dispatches, 408 distinct current check receipts and 136 distinct
1214   decision receipts. The audit reconstructs exact invocation CIDs and restores all native trace, outcome
1215   and receipt objects. These newly authored partitions were prepared after development; they are not
1216   population-generalization evidence.
1217   Eight distinct proof, test, adversarial, held-out, shadow, specification, source-episode and counterex-
1218   ample artifacts precede signing. Seven bounded Z3 contracts are connected to 4,100 concrete catalog
1219   executions; this is a bounded logical result with a measured source bridge, not a theorem for arbitrary
1220   Python. The original IR has an empty required-proof-contract list. An added adapter enforces the
1221   named proof payload; native contract-specific proof coverage is not inferred. Independent artifact
1222   admission recomputes concrete decisions, and runtime validation repeats catalog operations. These
1223   costs are charged; this experiment does not demonstrate receipt-only computation avoidance.
1224   Thirty pre-issuer evidence controls and thirteen native runtime controls pass, including signature,
1225   expiry, catalog, observation, query identity, cross-invocation and domain mutations. LIVE dispatch
1226   rejects. Exact invocation checkpoint reuse avoids redispatch in the same interpreter process; cross-
1227   process checkpoint restoration is untested. Since native canonical values reject floats, a frozen
1228   canonical-JSON transport preserves input bytes behind a checked typed query CID. The evidence
1229   corpus retains 1,192 float-bearing adversaries.
1230   Preparation and freeze take 1.402121 seconds. Three fresh bounded workers take 1.521004 seconds
1231   for evidence production, 6.902933 seconds for admission and issuance, and 8.819003 seconds for
1232   execution and controls: 17.242940 seconds total. The 6.771036 seconds of native invocation calls and
1233   5.127014 seconds of evidence-negative work are nested. Independent audit adds 2.929698 seconds.
1234   Evidence payloads occupy 2,373,459 bytes and native runtime objects 2,704,141 bytes, excluding
1235   snapshots and logs. Earlier float, immutable-mapping and SMT serialization failures retain their
1236   original profiles, limits and costs. Profile copying before the driver was not timed. The freeze pins
1237   10,736 paths; 156 observed loaded files include 112 standard-library/other paths outside the native
1238   source freeze. Local custody does not supply OS isolation against hostile Python. No provider call,
1239   model-token saving, repository transfer or production authority is attributed to this integration.




                                                         27

````

### PDF page 28

````text
1240   K    Family-level display
       Figure 1 displays the same family counts as Table 3; it is not an additional experiment.


                                        Eight family blocks: descriptive A/B outcomes
                      09-tomlkit                                                                    A
                                                                                                    B
                     10-installer


                     11-tornado


              12-more-itertools


         13-charset_normalizer


                     14-iniconfig


                       15-wheel


                         16-jinja

                                      0.0                          0.5                            1.0
                                              Useful fraction across two nested repetitions


       Figure 1: Useful completions by family and arm in the same 32-cell comparison. Each arm has two
       nested repetitions per family; the figure adds no trials.
1241




                                                        28

````

### PDF page 29

````text
1242   L    Historical boundary evidence
1243   Table 6 retains the historical qualification scope separately from the final repair comparison. Identifiers
1244   of the form NS-NNN name internal qualification records, not repository families or independent
1245   repair trials. The anonymous boundary component retains the detailed evidence index and limitations.

       Table 6: Historical evidence boundaries. Local controls, unavailable measurements, and the retained
       false-reuse case are not additional final repair outcomes.
           Boundary              Safe rejection             Valid progress                Evidence
           Provider gate         Missing/mismatched au- Deterministic repair              NS-008
                                 thority and untrusted and injected residual
                                 close rejected in fix- fixture; no production
                                 tures.                     routing claim.
           Loss-aware trans-     Modal erasure and un- Exact/conservative                 NS-009
           lation                validated solver lift re- translation only; no
                                 fused.                     kernel source proof.
           Native      theo-     Untested: no admitted Unavailable: no gen-               NS-014      scope
           rem/circuit           native proof profile.      uine proof or measured        closure
                                                            prove/verify run.
           Fixture/call/         Prior false reuse 1/26 re- Full public cold base-        NS-011;     cor-
           teardown reuse        tained; corrected route line only; no admit-             rected NS-027
                                 requires full cold.        ted positive reuse or
                                                            speedup.
           Publication after     Empty/stale/failed pub- WAL/CAS recovery                 NS-012/013
           restart               lication refused in local and valid continuation;
                                 controls.                  explicit      hermetic
                                                            shims.
           World/procedure       Untested/out of scope.     Untested: no retained         NS-015      scope
           consumption                                      paired pre/post con-          closure
                                                            sumption.
1246



1247   M     Withdrawn and unmeasured comparisons

       Table 7: Withdrawn and unmeasured comparisons. These entries are scope dispositions, not zero-
       effect measurements.
        Endpoint                           Scope
        C/D routing/governance com-        Withdrawn or unmeasured; no final comparison or effect esti-
        parative benefits                  mate.
        proof/test reuse or local_warm     Withdrawn or unmeasured; no final comparison or effect esti-
        effects                            mate.
        certificate/publication compar-    Withdrawn or unmeasured; no final comparison or effect esti-
        ative benefits                     mate.
        adversarial scorer-integrity       Withdrawn or unmeasured; no final comparison or effect esti-
        qualification                      mate.
        independent human semantic         Withdrawn or unmeasured; no final comparison or effect esti-
        annotation                         mate.
        Non-A/B planned cells (128)        Withdrawn; no measured ablation rows.
        A/B warm planned cells (32)        Withdrawn; no measured ablation rows.




                                                          29

````

### PDF page 30

````text
1248   N    LLM use, public reproduction, and responsible use
1249   Scientific model use. The historical cold-repair comparison uses Grok 4.6 to propose source edits
1250   from the fixed A/B context requests (Section B). Each of the 32 cells consumes one proposal POST
1251   with a maximum of 4,096 requested output tokens and a structured edit response. No scientific
1252   fallback, retry, served random seed, or reasoning-effort parameter is used. The model’s weights and
1253   exact served revision are unavailable. Candidate inspection by AI is a procedural control; it is not
1254   independent human assessment or a substitute for executed checks.
1255   The new routing and context development pilots each use six Grok 4.6 requests under a separately
1256   frozen low-effort profile, with at most 2,048 requested output tokens and 240 seconds per request.
1257   These pilots do not share the historical experiment’s reasoning-effort setting or task population.
1258   All twelve responses retain actual model identity and token-usage fields; no scientific retry, model
1259   fallback or auxiliary model call is included in these development workflows. Deterministic analysis,
1260   solver checks and executed oracles remain distinct from model proposals.

1261   Research and manuscript assistance. AI assistance also contributed to source recovery and
1262   drafting, implementation and debugging, experiment preparation and candidate inspection, and
1263   analysis and artifact preparation. The original authoring supervisors were configured to use Grok
1264   4.6, with Codex gpt-5.6-terra at high reasoning effort as a fallback only following independently
1265   verified primary-quota exhaustion. This describes the configured authoring policy, not a claim that
1266   every task used a fallback or that these models generated the scientific comparison under a mixed route.
1267   The configured policy does not identify the model behind every separate interactive assistance session.
1268   AI-assisted checking supplies no measured human semantic fidelity, expert agreement, or human
1269   effort time, and does not discharge the conditional arguments in Appendix A. The present incremental
1270   evaluation code, reports and manuscript revision also received interactive Codex assistance. That
1271   authoring effort is not included in the measured deployment-task token totals; no full research-effort
1272   saving is claimed.

1273   Anonymous numerical reproduction. The historical supplement keeps the 32-cell final compari-
1274   son, the separate 24-cell developmental pilot, and historical boundary controls in distinct components.
1275   Its top-level README.md specifies Python 3.12 and the command python3 -B reproduce.py
1276   –root ROOT –output OUTPUT, where ROOT is a fresh extraction and OUTPUT is a fresh directory
1277   outside it. The program checks the manifest-bound files and reproduces their retained numerical
1278   summaries; it does not generate new proposals, execute candidates or hidden tests, rerun historical
1279   qualifications, or authenticate original signed records. Hidden tests, reference patches, credentials,
1280   keys, and raw private operational logs are excluded. Original and derivative hashes have distinct
1281   roles: original signatures do not authenticate modified anonymous derivative bytes. Exact executed
1282   source and labeled reference derivatives remain distinct. Upstream retrieval metadata, revisions, and
1283   retained license and copyright notices accompany the released assets. Stable hashes and timestamps
1284   may permit correlation, so these release controls do not guarantee anonymity. New development
1285   artifacts are retained separately with source and request hashes, terminal outcomes and replay com-
1286   mands. They have not been incorporated into that historical anonymous supplement; its reproduction
1287   command does not reproduce the new evaluations.

1288   Potential impacts and limits. Explicit evidence boundaries may help users identify stale checks
1289   and unsupported acceptance claims, but this experiment establishes no general reliability or efficiency
1290   benefit. Incorrect repairs, incomplete tests, or mistaking signed provenance for correctness could
1291   lead to unsafe deployment; automated coding can also be misused to introduce harmful changes.
1292   The stated scope, isolated checks, restricted artifact projection, and visible failures reduce particular
1293   risks without establishing comprehensive adversarial resistance. No model weights or human-subject
1294   dataset are released, and no human semantic annotations, expert-agreement study, or human-time
1295   measurements were collected for the reported comparison.




                                                         30

````

### PDF page 31

````text
1296   NeurIPS Paper Checklist
1297       1. Claims
1298          Question: Do the main claims made in the abstract and introduction accurately reflect the
1299          paper’s contributions and scope?
1300          Answer: [Yes]
1301          Justification: The abstract and Sections 1, 5, and 8 restrict the contribution to explicit
1302          evidence boundaries, conditional arguments, and the fixed eight-family A/B comparison (A
1303          5/16, B 4/16). They do not claim semantic correctness, a general performance advantage, or
1304          benefits from withdrawn routing, reuse, or publication comparisons.
1305          Guidelines:
1306             • The answer [N/A] means that the abstract and introduction do not include the claims
1307                made in the paper.
1308             • The abstract and/or introduction should clearly state the claims made, including the
1309                contributions made in the paper and important assumptions and limitations. A [No] or
1310                [N/A] answer to this question will not be perceived well by the reviewers.
1311             • The claims made should match theoretical and experimental results, and reflect how
1312                much the results can be expected to generalize to other settings.
1313             • It is fine to include aspirational goals as motivation as long as it is clear that these goals
1314                are not attained by the paper.
1315       2. Limitations
1316          Question: Does the paper discuss the limitations of the work performed by the authors?
1317          Answer: [Yes]
1318          Justification: Section 8 states the convenience-sample scope, combined-context intervention,
1319          finite-test and trusted-premise limitations, and missing human semantic fidelity, expert agree-
1320          ment, and human-time measurements. Sections C and 5 retain failures, timing deviations,
1321          overlapping clocks, incomplete validation, and unsettled charges.
1322          Guidelines:
1323             • The answer [N/A] means that the paper has no limitation while the answer [No] means
1324                that the paper has limitations, but those are not discussed in the paper.
1325             • The authors are encouraged to create a separate “Limitations” section in their paper.
1326             • The paper should point out any strong assumptions and how robust the results are to
1327                violations of these assumptions (e.g., independence assumptions, noiseless settings,
1328                model well-specification, asymptotic approximations only holding locally). The authors
1329                should reflect on how these assumptions might be violated in practice and what the
1330                implications would be.
1331             • The authors should reflect on the scope of the claims made, e.g., if the approach was
1332                only tested on a few datasets or with a few runs. In general, empirical results often
1333                depend on implicit assumptions, which should be articulated.
1334             • The authors should reflect on the factors that influence the performance of the approach.
1335                For example, a facial recognition algorithm may perform poorly when image resolution
1336                is low or images are taken in low lighting. Or a speech-to-text system might not be
1337                used reliably to provide closed captions for online lectures because it fails to handle
1338                technical jargon.
1339             • The authors should discuss the computational efficiency of the proposed algorithms
1340                and how they scale with dataset size.
1341             • If applicable, the authors should discuss possible limitations of their approach to
1342                address problems of privacy and fairness.
1343             • While the authors might fear that complete honesty about limitations might be used by
1344                reviewers as grounds for rejection, a worse outcome might be that reviewers discover
1345                limitations that aren’t acknowledged in the paper. The authors should use their best
1346                judgment and recognize that individual actions in favor of transparency play an impor-
1347                tant role in developing norms that preserve the integrity of the community. Reviewers
1348                will be specifically instructed to not penalize honesty concerning limitations.


                                                         31

````

### PDF page 32

````text
1349   3. Theory assumptions and proofs
1350      Question: For each theoretical result, does the paper provide the full set of assumptions and
1351      a complete (and correct) proof?
1352      Answer: [No]
1353      Justification: Section 3 and Appendix A give explicit scopes, premises, and conditional
1354      argument sketches, but do not claim a complete formal proof of the intended implementation.
1355      The arguments are unmachine-checked, and dependency completeness, checker adequacy,
1356      and exclusive checked publication remain assumptions.
1357      Guidelines:
1358         • The answer [N/A] means that the paper does not include theoretical results.
1359         • All the theorems, formulas, and proofs in the paper should be numbered and cross-
1360            referenced.
1361         • All assumptions should be clearly stated or referenced in the statement of any theorems.
1362         • The proofs can either appear in the main paper or the supplemental material, but if
1363            they appear in the supplemental material, the authors are encouraged to provide a short
1364            proof sketch to provide intuition.
1365         • Inversely, any informal proof provided in the core of the paper should be complemented
1366            by formal proofs provided in appendix or supplemental material.
1367         • Theorems and Lemmas that the proof relies upon should be properly referenced.
1368   4. Experimental result reproducibility
1369      Question: Does the paper fully disclose all the information needed to reproduce the main ex-
1370      perimental results of the paper to the extent that it affects the main claims and/or conclusions
1371      of the paper (regardless of whether the code and data are provided or not)?
1372      Answer: [No]
1373      Justification: Sections B and C disclose the retained protocol and frozen reduction, and Sec-
1374      tion N describes the anonymous numerical replay. Independent regeneration and confidential-
1375      oracle rescoring are not supplied: exact served model revisions, private original custody,
1376      and hidden tests are unavailable through that replay.
1377      Guidelines:
1378         • The answer [N/A] means that the paper does not include experiments.
1379         • If the paper includes experiments, a [No] answer to this question will not be perceived
1380            well by the reviewers: Making the paper reproducible is important, regardless of
1381            whether the code and data are provided or not.
1382         • If the contribution is a dataset and/or model, the authors should describe the steps taken
1383            to make their results reproducible or verifiable.
1384         • Depending on the contribution, reproducibility can be accomplished in various ways.
1385            For example, if the contribution is a novel architecture, describing the architecture fully
1386            might suffice, or if the contribution is a specific model and empirical evaluation, it may
1387            be necessary to either make it possible for others to replicate the model with the same
1388            dataset, or provide access to the model. In general. releasing code and data is often
1389            one good way to accomplish this, but reproducibility can also be provided via detailed
1390            instructions for how to replicate the results, access to a hosted model (e.g., in the case
1391            of a large language model), releasing of a model checkpoint, or other means that are
1392            appropriate to the research performed.
1393         • While NeurIPS does not require releasing code, the conference does require all submis-
1394            sions to provide some reasonable avenue for reproducibility, which may depend on the
1395            nature of the contribution. For example
1396           (a) If the contribution is primarily a new algorithm, the paper should make it clear how
1397                to reproduce that algorithm.
1398           (b) If the contribution is primarily a new model architecture, the paper should describe
1399                the architecture clearly and fully.
1400           (c) If the contribution is a new model (e.g., a large language model), then there should
1401                either be a way to access this model for reproducing the results or a way to reproduce
1402                the model (e.g., with an open-source dataset or instructions for how to construct
1403                the dataset).


                                                    32

````

### PDF page 33

````text
1404          (d) We recognize that reproducibility may be tricky in some cases, in which case
1405              authors are welcome to describe the particular way they provide for reproducibility.
1406              In the case of closed-source models, it may be that access to the model is limited in
1407              some way (e.g., to registered users), but it should be possible for other researchers
1408              to have some path to reproducing or verifying the results.
1409   5. Open access to data and code
1410      Question: Does the paper provide open access to the data and code, with sufficient instruc-
1411      tions to faithfully reproduce the main experimental results, as described in supplemental
1412      material?
1413     Answer: [No]
1414     Justification: The anonymous supplement provides manifest-bound inputs, selected source
1415     versions, retained license/retrieval metadata, and Python 3.12 instructions that reproduce
1416     the reported scalar summaries. It does not provide model weights, hidden-oracle access, or
1417     public authentication of original private signatures; Section N states these limits.
1418      Guidelines:
1419         • The answer [N/A] means that paper does not include experiments requiring code.
1420         • Please see the NeurIPS code and data submission guidelines (https://neurips.cc/
1421           public/guides/CodeSubmissionPolicy) for more details.
1422         • While we encourage the release of code and data, we understand that this might not
1423           be possible, so [No] is an acceptable answer. Papers cannot be rejected simply for not
1424           including code, unless this is central to the contribution (e.g., for a new open-source
1425           benchmark).
1426         • The instructions should contain the exact command and environment needed to run to
1427           reproduce the results. See the NeurIPS code and data submission guidelines (https:
1428           //neurips.cc/public/guides/CodeSubmissionPolicy) for more details.
1429         • The authors should provide instructions on data access and preparation, including how
1430           to access the raw data, preprocessed data, intermediate data, and generated data, etc.
1431         • The authors should provide scripts to reproduce all experimental results for the new
1432           proposed method and baselines. If only a subset of experiments are reproducible, they
1433           should state which ones are omitted from the script and why.
1434         • At submission time, to preserve anonymity, the authors should release anonymized
1435           versions (if applicable).
1436         • Providing as much information as possible in supplemental material (appended to the
1437           paper) is recommended, but including URLs to data and code is permitted.
1438   6. Experimental setting/details
1439      Question: Does the paper specify all the training and test details (e.g., data splits, hyperpa-
1440      rameters, how they were chosen, type of optimizer) necessary to understand the results?
1441     Answer: [Yes]
1442     Justification: Section B specifies the historical cold comparison, and Section 6 distinguishes
1443     the new constructed development profiles, calls, oracles, cost scopes and limitations. Frozen
1444     per-study artifacts retain the exact requests, execution settings, cases and source bindings;
1445     the development observations are not pooled with historical results.
1446      Guidelines:
1447         • The answer [N/A] means that the paper does not include experiments.
1448         • The experimental setting should be presented in the core of the paper to a level of detail
1449           that is necessary to appreciate the results and make sense of them.
1450         • The full details can be provided either with the code, in appendix, or as supplemental
1451           material.
1452   7. Experiment statistical significance
1453      Question: Does the paper report error bars suitably and correctly defined or other appropriate
1454      information about the statistical significance of the experiments?
1455     Answer: [No]


                                                   33

````

### PDF page 34

````text
1456      Justification: The historical study retains its explicitly descriptive whole-family bootstrap
1457      interval, but the new small constructed development pilots do not provide population-level
1458      uncertainty estimates or statistical significance claims. Their observed savings are limited to
1459      the fixed cases; held-out repeated comparisons remain necessary.
1460      Guidelines:
1461          • The answer [N/A] means that the paper does not include experiments.
1462          • The authors should answer [Yes] if the results are accompanied by error bars, confidence
1463            intervals, or statistical significance tests, at least for the experiments that support the
1464            main claims of the paper.
1465          • The factors of variability that the error bars are capturing should be clearly stated (for
1466            example, train/test split, initialization, random drawing of some parameter, or overall
1467            run with given experimental conditions).
1468          • The method for calculating the error bars should be explained (closed form formula,
1469            call to a library function, bootstrap, etc.)
1470          • The assumptions made should be given (e.g., Normally distributed errors).
1471          • It should be clear whether the error bar is the standard deviation or the standard error
1472            of the mean.
1473          • It is OK to report 1-sigma error bars, but one should state it. The authors should
1474            preferably report a 2-sigma error bar than state that they have a 96% CI, if the hypothesis
1475            of Normality of errors is not verified.
1476          • For asymmetric distributions, the authors should be careful not to show in tables or
1477            figures symmetric error bars that would yield results that are out of range (e.g., negative
1478            error rates).
1479          • If error bars are reported in tables or plots, the authors should explain in the text how
1480            they were calculated and reference the corresponding figures or tables in the text.
1481   8. Experiments compute resources
1482      Question: For each experiment, does the paper provide sufficient information on the com-
1483      puter resources (type of compute workers, memory, time of execution) needed to reproduce
1484      the experiments?
1485      Answer: [No]
1486      Justification: Sections B, C, and 5 report per-phase CPU, memory, process and time limits,
1487      available measured clocks, prior work, and missingness. Provider-side hardware and total
1488      compute/effort or settled charges are unavailable, and overlapping clocks, reservation
1489      lifetimes, and configured caps are not presented as measured total compute.
1490      Guidelines:
1491          • The answer [N/A] means that the paper does not include experiments.
1492          • The paper should indicate the type of compute workers CPU or GPU, internal cluster,
1493            or cloud provider, including relevant memory and storage.
1494          • The paper should provide the amount of compute required for each of the individual
1495            experimental runs as well as estimate the total compute.
1496          • The paper should disclose whether the full research project required more compute
1497            than the experiments reported in the paper (e.g., preliminary or failed experiments that
1498            didn’t make it into the paper).
1499   9. Code of ethics
1500      Question: Does the research conducted in the paper conform, in every respect, with the
1501      NeurIPS Code of Ethics https://neurips.cc/public/EthicsGuidelines?
1502      Answer: [N/A]
1503      Justification: Author review of and conformance with the NeurIPS Code of Ethics has not
1504      been attested in the preparation record. This answer records unavailable author confirmation,
1505      not a claim that the work violates the code; the author must review it before submission.
1506      Guidelines:
1507          • The answer [N/A] means that the authors have not reviewed the NeurIPS Code of
1508            Ethics.


                                                    34

````

### PDF page 35

````text
1509         • If the authors answer [No], they should explain the special circumstances that require a
1510           deviation from the Code of Ethics.
1511         • The authors should make sure to preserve anonymity (e.g., if there is a special consid-
1512           eration due to laws or regulations in their jurisdiction).
1513   10. Broader impacts
1514      Question: Does the paper discuss both potential positive societal impacts and negative
1515      societal impacts of the work performed?
1516      Answer: [Yes]
1517      Justification: Section N discusses potential benefits of making evidence boundaries explicit,
1518      and harms from incorrect repairs, misplaced trust in signed provenance, unsafe deployment,
1519      malicious edits, and residual privacy correlation. It states the limited scope of the proposed
1520      mitigations and makes no measured societal-benefit or comprehensive security claim.
1521      Guidelines:
1522         • The answer [N/A] means that there is no societal impact of the work performed.
1523         • If the authors answer [N/A] or [No], they should explain why their work has no societal
1524           impact or why the paper does not address societal impact.
1525         • Examples of negative societal impacts include potential malicious or unintended uses
1526           (e.g., disinformation, generating fake profiles, surveillance), fairness considerations
1527           (e.g., deployment of technologies that could make decisions that unfairly impact specific
1528           groups), privacy considerations, and security considerations.
1529         • The conference expects that many papers will be foundational research and not tied
1530           to particular applications, let alone deployments. However, if there is a direct path to
1531           any negative applications, the authors should point it out. For example, it is legitimate
1532           to point out that an improvement in the quality of generative models could be used to
1533           generate Deepfakes for disinformation. On the other hand, it is not needed to point out
1534           that a generic algorithm for optimizing neural networks could enable people to train
1535           models that generate Deepfakes faster.
1536         • The authors should consider possible harms that could arise when the technology is
1537           being used as intended and functioning correctly, harms that could arise when the
1538           technology is being used as intended but gives incorrect results, and harms following
1539           from (intentional or unintentional) misuse of the technology.
1540         • If there are negative societal impacts, the authors could also discuss possible mitigation
1541           strategies (e.g., gated release of models, providing defenses in addition to attacks,
1542           mechanisms for monitoring misuse, mechanisms to monitor how a system learns from
1543           feedback over time, improving the efficiency and accessibility of ML).
1544   11. Safeguards
1545      Question: Does the paper describe safeguards that have been put in place for responsible
1546      release of data or models that have a high risk for misuse (e.g., pre-trained language models,
1547      image generators, or scraped datasets)?
1548      Answer: [N/A]
1549      Justification: The release contains no model weights or human-subject dataset of the
1550      high-risk types described by this question. Section N and the supplement documentation
1551      nevertheless describe excluded private logs, credentials, keys, hidden tests and reference
1552      patches, and the residual limits of anonymization.
1553      Guidelines:
1554         • The answer [N/A] means that the paper poses no such risks.
1555         • Released models that have a high risk for misuse or dual-use should be released with
1556           necessary safeguards to allow for controlled use of the model, for example by requiring
1557           that users adhere to usage guidelines or restrictions to access the model or implementing
1558           safety filters.
1559         • Datasets that have been scraped from the Internet could pose safety risks. The authors
1560           should describe how they avoided releasing unsafe images.


                                                   35

````

### PDF page 36

````text
1561          • We recognize that providing effective safeguards is challenging, and many papers do
1562            not require this, but we encourage authors to take this into account and make a best
1563            faith effort.
1564   12. Licenses for existing assets
1565       Question: Are the creators or original owners of assets (e.g., code, data, models), used in
1566       the paper, properly credited and are the license and terms of use explicitly mentioned and
1567       properly respected?
1568       Answer: [No]
1569       Justification: The supplement retains upstream revisions, retrieval metadata, license and
1570       copyright notices, and distinguishes exact executed source from reference derivatives. A
1571       complete confirmation of all provider and asset terms of use is unavailable in this preparation,
1572       so retained notices alone are not asserted to establish full compliance.
1573       Guidelines:
1574          • The answer [N/A] means that the paper does not use existing assets.
1575          • The authors should cite the original paper that produced the code package or dataset.
1576          • The authors should state which version of the asset is used and, if possible, include a
1577            URL.
1578          • The name of the license (e.g., CC-BY 4.0) should be included for each asset.
1579          • For scraped data from a particular source (e.g., website), the copyright and terms of
1580            service of that source should be provided.
1581          • If assets are released, the license, copyright information, and terms of use in the
1582            package should be provided. For popular datasets, paperswithcode.com/datasets
1583            has curated licenses for some datasets. Their licensing guide can help determine the
1584            license of a dataset.
1585          • For existing datasets that are re-packaged, both the original license and the license of
1586            the derived asset (if it has changed) should be provided.
1587          • If this information is not available online, the authors are encouraged to reach out to
1588            the asset’s creators.
1589   13. New assets
1590       Question: Are new assets introduced in the paper well documented and is the documentation
1591       provided alongside the assets?
1592       Answer: [Yes]
1593       Justification: The supplement documents its final-comparison, developmental-pilot, and
1594       historical-boundary components with separate manifests, numerical reproduction commands,
1595       source and derivative identities, and explicit data-access and inference limitations. Section N
1596       explains this scope, including the distinction between integrity hashes and authentication of
1597       private originals.
1598       Guidelines:
1599          • The answer [N/A] means that the paper does not release new assets.
1600          • Researchers should communicate the details of the dataset/code/model as part of their
1601            submissions via structured templates. This includes details about training, license,
1602            limitations, etc.
1603          • The paper should discuss whether and how consent was obtained from people whose
1604            asset is used.
1605          • At submission time, remember to anonymize your assets (if applicable). You can either
1606            create an anonymized URL or include an anonymized zip file.
1607   14. Crowdsourcing and research with human subjects
1608       Question: For crowdsourcing experiments and research with human subjects, does the paper
1609       include the full text of instructions given to participants and screenshots, if applicable, as
1610       well as details about compensation (if any)?
1611       Answer: [N/A]


                                                    36

````

### PDF page 37

````text
1612       Justification: The reported source-code comparison includes no crowdsourcing or human-
1613       subject annotation study. Section 8 states that human semantic fidelity, expert agreement and
1614       human time were not measured; AI candidate inspection is not relabeled as human research.
1615       Guidelines:
1616          • The answer [N/A] means that the paper does not involve crowdsourcing nor research
1617             with human subjects.
1618          • Including this information in the supplemental material is fine, but if the main contribu-
1619             tion of the paper involves human subjects, then as much detail as possible should be
1620             included in the main paper.
1621          • According to the NeurIPS Code of Ethics, workers involved in data collection, curation,
1622             or other labor should be paid at least the minimum wage in the country of the data
1623             collector.
1624   15. Institutional review board (IRB) approvals or equivalent for research with human
1625       subjects
1626       Question: Does the paper describe potential risks incurred by study participants, whether
1627       such risks were disclosed to the subjects, and whether Institutional Review Board (IRB)
1628       approvals (or an equivalent approval/review based on the requirements of your country or
1629       institution) were obtained?
1630       Answer: [N/A]
1631       Justification: No human-subject experiment or crowdsourcing is reported, so no participant-
1632       risk, compensation or IRB-approval result is claimed. The absence of human semantic
1633       annotations and expert-agreement measurements is explicit in Section 8; this answer does
1634       not invent institutional approval.
1635       Guidelines:
1636          • The answer [N/A] means that the paper does not involve crowdsourcing nor research
1637             with human subjects.
1638          • Depending on the country in which research is conducted, IRB approval (or equivalent)
1639             may be required for any human subjects research. If you obtained IRB approval, you
1640             should clearly state this in the paper.
1641          • We recognize that the procedures for this may vary significantly between institutions
1642             and locations, and we expect authors to adhere to the NeurIPS Code of Ethics and the
1643             guidelines for their institution.
1644          • For initial submissions, do not include any information that would break anonymity (if
1645             applicable), such as the institution conducting the review.
1646   16. Declaration of LLM usage
1647       Question: Does the paper describe the usage of LLMs if it is an important, original, or
1648       non-standard component of the core methods in this research? Note that if the LLM is used
1649       only for writing, editing, or formatting purposes and does not impact the core methodology,
1650       scientific rigor, or originality of the research, declaration is not required.
1651       Answer: [Yes]
1652       Justification: Section B and Section N identify methodology-essential Grok 4.6 scientific
1653       proposals under one-POST/no-fallback rules and describe AI assistance in implementation,
1654       inspection, analysis and writing. The configured authoring Grok-to-Codex gpt-5.6-terra
1655       high quota-only fallback is distinguished from observed scientific use, without claiming that
1656       every fallback or interactive session used that model.
1657       Guidelines:
1658          • The answer [N/A] means that the core method development in this research does not
1659             involve LLMs as any important, original, or non-standard components.
1660          • Please refer to our LLM policy in the NeurIPS handbook for what should or should not
1661             be described.




                                                    37

````

## Exact ordered LaTeX source: appendix assembly

This partial assembly replaces only manifest-listed `\input{...}` directives with their verbatim UTF-8 source text in `main.tex` order and inserts labeled comments. It is provided for exact formulas and source review, not as a standalone compilable document. Bibliography and figure commands remain as in the original; their retained files are in the source snapshot. No empirical sentence or equation is editorially corrected here.

````latex
\appendix
\label{paper:appendix-start}

% BEGIN retained input: appendix/entry.tex
\section{Full conditional argument record}
\label{sec:argument-record}

The following audited statements are retained verbatim from the earlier formal
argument record. Their Equation 2, Algorithm 1, and statement identifiers name
that record; they are not additional final experiments or numbered algorithms
in the main text. References to a sealed profile or the absence of a campaign
describe the scope of that argument audit. Later constructed corrections and
the cold comparison do not retroactively discharge its universal premises.
The intended algorithm's bounded retry branch is architectural specification;
the final empirical protocol permits no proposal retry.


% BEGIN retained input: appendix/formal_arguments.tex
% Audited restatement of the conditional acceptance and reuse arguments (NS-023).
% This fragment is for later manuscript integration (NS-022). It is not a
% machine-checked proof, not a universal-Python theorem, and not a claim that
% Algorithm~1 ran as a complete live loop.
%
% Compile context: the reconstructed body already loads amsmath/amssymb.
% Do not treat this file as an independent experiment result.

\section*{Conditional acceptance and reuse arguments (audited)}
\label{sec:formal-arguments-ns023}

The statements below restate Equation~2, the accepted-lineage sketch, the
dependency-projection reuse obligation, the three acceptance questions, and
Algorithm~1 with explicit scope, premises, and conclusions. Every sketch is
\textbf{unmachine-checked}: the sealed validation profile has no usable
\texttt{z3}, \texttt{lean}, \texttt{coqc}, or \texttt{cvc5}, and no independently
checked proof artifact discharges these arguments. Implementation evidence
supports only the named tested premises. External side-effect atomicity and
universal dependency closure are not inferred. Unknown specifications stay
visible.

\subsection*{Statement FA-EQ2 (acceptance invariant)}
\label{stmt:fa-eq2}

\paragraph{Scope.}
One publication of an accepted lineage root under a declared artifact policy.
The statement is a design invariant for that publication operation. It is not a
theorem that every current write path enforces the invariant, and it is not a
claim about Git, remote stores, or physical effects outside the tested
expected-parent compare-and-swap.

\paragraph{Premises.}
Let $s$ be the current accepted root, $s'$ a candidate successor, $a$ the
requesting actor, and $q$ the required obligation set. Write $\mathrm{Publish}(s')$
for the unique accepted-lineage publication of $s'$.

\paragraph{Conclusion.}
\begin{equation}
\begin{aligned}
\mathrm{Publish}(s')\Rightarrow{}&\mathrm{CurrentParent}(s)\land\mathrm{Authorized}(a,s)\\
&\land\mathrm{Scoped}(a)\land\mathrm{CompleteManifest}(q,s')\\
&\land\mathrm{EvidenceAdmitted}(q,s')\land\mathrm{CAS}(s,s').
\end{aligned}
\tag{2$'$}
\end{equation}

\paragraph{Argument (unmachine-checked).}
If publication is defined to succeed only after those six gates, then any
published $s'$ satisfies them. The converse is not claimed: a candidate that
meets the gates may still lose compare-and-swap. Failed, stale, incomplete, or
simulated attempts are not $\mathrm{Publish}$ successors.

\paragraph{What the invariant does not establish.}
Properties omitted by the checked policy; truth of unsupported or lossy
translations; honesty of signed observations; atomicity of external side
effects; global consensus; or universal enforcement by unexamined write paths.

\subsection*{Statement FA-I31 (accepted-lineage induction)}
\label{stmt:fa-i31}

\paragraph{Scope.}
Roots reachable \emph{solely} through accepted publication transitions of the
operation in FA-EQ2, under a fixed statement profile $\Theta$ and policy
predicate $P_{\Theta}$ over artifact manifests.

\paragraph{Premises.}
\begin{enumerate}
\item \textbf{Initial-root policy.} The initial accepted root satisfies $P_{\Theta}$.
\item \textbf{Exact input.} Required subject bytes and dependency references are
verified before admission.
\item \textbf{Complete manifest.} The requirement manifest is complete under an
admitted completeness rule; membership of some units is not completeness.
\item \textbf{Checker.} Each accepted evidence item satisfies its designated
checker relation and evidence class.
\item \textbf{Translation bound.} Lossy or unsupported translations cannot
discharge source-level obligations.
\item \textbf{Current parent.} Publication names the expected current parent.
\item \textbf{Exclusive publication.} Compare-and-swap linearizes concurrent
same-parent writers; losers are not successors.
\item \textbf{Protected authority.} Policy and checker identities cannot change
under ordinary worker authority.
\end{enumerate}

\paragraph{Conclusion.}
Every root reachable solely through accepted publication transitions satisfies
$P_{\Theta}$.

\paragraph{Argument (unmachine-checked).}
Induction on the number of successful publications. The base case is premise~1.
For the inductive step, the publisher checks $P_{\Theta}$ on the exact candidate
manifest and current parent before compare-and-swap linearization. Failed,
stale, incomplete, or simulated attempts are excluded from the successor
relation, so they are not inductive cases. The induction preserves only
properties actually expressed by $P_{\Theta}$.

\paragraph{Nonvacuity.}
The successor relation is nonempty on the tested sealer: a complete current
manifest can publish, while an empty or incomplete mandatory manifest cannot.
Deny-all publication would make the invariant hold vacuously and is not a
useful-progress witness.

\subsection*{Statement FA-I32 (dependency-projected test reuse)}
\label{stmt:fa-i32}

\paragraph{Scope.}
Transfer of a previous setup/call/teardown observation of test $t$ between
states $s$ and $s'$ under a declared runtime/effect profile $\theta$. The
statement is a proof \emph{obligation}, not a theorem of arbitrary pytest
execution.

\paragraph{Premises.}
Let $\mathrm{Obs}_{\theta}(t,s)$ be the relevant observation. Suppose there exist
a complete projection $\pi_D$ and a deterministic function $f_{\theta}$ such that
\[
\mathrm{Obs}_{\theta}(t,s)=f_{\theta}(\pi_D(s))
\]
on every state admitted by the reuse policy.

\paragraph{Conclusion.}
If $\pi_D(s)=\pi_D(s')$, then $\mathrm{Obs}_{\theta}(t,s)=\mathrm{Obs}_{\theta}(t,s')$.
An admitted previous observation may transfer only inside that profile and those
assumptions.

\paragraph{Argument (unmachine-checked).}
Immediate from functionality of $f_{\theta}$. The difficult premises are
completeness and determinism of $\pi_D$. Equal digests of incomplete manifests
do not satisfy $\pi_D$ completeness. Opaque, uncontrolled, or unknown fixture
values, incomplete runtime traces, and teardown failures do not discharge the
obligation; they require execution or fail closed. A cold full-run oracle and
adversarial mutations can check an implementation; they do not prove universal
dependency closure. No such independent cold-oracle campaign is recorded here.

\subsection*{Statement FA-I33 (three acceptance questions)}
\label{stmt:fa-i33}

\paragraph{Scope.}
Any candidate action that might be described as ``accepted.''

\paragraph{Premises and conclusions (separate).}
\begin{center}
\begin{tabular}{@{}p{0.28\linewidth}p{0.66\linewidth}@{}}
\toprule
Question & What a positive answer establishes, and what it does not \\
\midrule
Behavioral claim &
The candidate program or model satisfies its stated obligation under the
declared checker, environment, and evidence class. This is not permission to
act and not publication of a lineage root. \\
Action permission &
This actor may perform this action now under the bound lease, policy, scope,
and roots. This is not behavioral correctness and not publication. \\
Publication &
This candidate and its evidence become the current accepted root. This is not,
by itself, proof that omitted obligations hold or that external effects
occurred exactly once. \\
\bottomrule
\end{tabular}
\end{center}

Neither a proof of behavior nor a capability grant answers all three. Formalization
fixes the statement; authorization binds actor, tool, arguments, resources,
effects, scope, time, and roots; execution observations report what happened;
publication chooses the accepted lineage.

\subsection*{Statement FA-ALG1 (composed supervision loop)}
\label{stmt:fa-alg1}

\paragraph{Scope.}
Algorithm~1 remains the intended composition: a control-flow specification,
not a newly executed full-loop result. It is labeled \textbf{executed
composition} only on the steps supported by the integrated guard-before-write
witness. Passing isolated stop-path tests does
not establish the complete loop.

\paragraph{Intended algorithm.}
Input: authorized query $q$, current source forest $F$, policy $P$, budget $B$.
\begin{enumerate}
\item Reconcile event, task, and artifact state; refresh $F$ and derive $G$, $O$.
\item If cancelled or budget exhausted: return explicit non-success.
\item If every current obligation is admitted: return goal-completion verification.
\item Generate bounded task proposals; preview and separately admit ready work.
\item If no task is admissible: return wait-or-review, not goal success.
\item Claim the task; bind lease/fence, preimages, required context, and validation.
\item Choose a deterministic, authorized residual-model, review, or unavailable route.
\item If review or unavailable: record a blocked attempt; return to the event service.
\item Produce and apply a candidate only through checked isolated execution.
\item Rescan; derive $O_{\mathrm{new}}$ from authorized rules, not the worker's pass claim.
\item Verify or reuse evidence; retain failed, unknown, and pending obligations.
\item If the failure is refinable: record a new residual; return a bounded retry.
\item If evidence is incomplete or unsafe: return defer-or-reject.
\item Persist the manifest; recheck current bindings; compare-and-swap the expected parent.
\item If publication conflicts: return reconcile, not completion.
\item Record the accepted task transition and updated $F$, $G$, $O$; reevaluate at line~1.
\item Propose procedure or policy learning separately; never self-promote.
\end{enumerate}

\paragraph{Executed composition (integrated witness only).}
The integrated witness supports a frozen guard-before-write cycle:
authorized pre-state and obligation; counterexample; admitted deterministic
route; isolated patch application; independent tests; narrow cache reuse of an
unchanged eligible receipt; complete-manifest publication; and rejection of
invalid, incomplete, and simulated non-completion. Those steps correspond to
intended lines 4, 7~(deterministic), 9, 11~(narrow reuse), 13, 14, and 16, plus
the negative reading of line~17 (no worker self-promotion). They do \emph{not}
execute the live event-service loop, residual production-model dispatch,
budget-exhaustion composition, wait-or-review, procedure/policy learning, native
proof, federation, or a matched A--D experiment.

\paragraph{Trusted limitations retained with the algorithm.}
Unknown or inconsistent specifications remain visible. Incomplete projections
cannot silently authorize reuse. External exactly-once behavior outside the
tested write-ahead-log / compare-and-swap / lifecycle boundary is not claimed.
Optional native proving and world/procedure extensions are out of scope unless
a later task supplies an eligible profile and consumed-result evidence.

% END retained input: appendix/formal_arguments.tex



% END retained input: appendix/entry.tex


% BEGIN retained input: fragments/design.tex
\section{Frozen comparison}
\label{sec:design}

\paragraph{Population and treatment.}
The eight recruited families are Tomlkit, installer, Tornado, more-itertools,
charset-normalizer, iniconfig, wheel, and Jinja. They are a convenience sample,
not a representative sample of Python repositories. Two arms and two nested
repetitions yield 32 fixed cells, 16 per arm. Repetition identifiers 104729 and
130363 identify design positions; they were not served to the model API as
random seeds.

Before final outcomes, the A/B local-cold comparison was retained as an
order-preserving subset of the original 192-cell plan. The remaining 160 factor
cells were withdrawn, and eight additional target families were not recruited.
C/D routing, warm caches, test reuse, publication efficacy, the original
sixteen-family inferential objectives, and D/A promotion comparisons remain
outside this experiment. The narrowed comparison is descriptive.

Arm A receives the selected public raw context. Arm B preserves the matched
raw selection and adds actual native source-linked semantic context.
Sixteen exact family/arm request commitments precede final generation; each
arm's two repetitions use its fixed request. This treatment changes the
combined request and cannot isolate semantic subcomponents or prompt
compression. Public source and native preparation remain separate from
confidential acceptance tests.

\paragraph{One proposal and independent cold execution.}
Each cell permits one Grok 4.6 proposal POST, requesting at most 4,096 output
tokens through a strict structured edit response. There is no scientific
fallback, retry, served seed, or reasoning-effort parameter. A failed request
consumes its original cell rather than creating a replacement. The frozen
order is executed sequentially.

Proposal execution uses one CPU, 2 GiB, and a 32-process limit. The nominal
gateway and HTTP-wrapper bounds are 600 seconds; the child bound is 595 seconds
and the socket timeout is 590 seconds. Compliance depends on actual measured
intervals. A configured limit, missing measurement, or nonfinite value is not
evidence that the budget was met.

The operator retains exact candidate bytes and a specific AI review before
eligible scoring. That procedural review supplies no independent human
annotation. Scoring runs separately in a cold, network-disabled container with
one CPU, 2 GiB, and a 128-process limit, bounded by 120 host seconds and 115
child seconds. The scorer's process limit was fixed prospectively for both
arms and all eight families because unchanged public concurrency tests require
up to 100 threads. The earlier 32-process public-baseline failure remains
recorded; proposal and native-preparation limits remain 32.

Useful completion requires an admitted candidate, nonempty public and hidden
checks all passing, and measured resource compliance. Failed, refused,
expired, unscored, or incomplete cells receive no useful-completion credit.
Unknown states remain explicit and prevent a complete-cohort analysis until
their terminal accounting is resolved. An import or collection error with
no hidden assertions executed is incomplete validation, not an observed
hidden behavioral assertion failure. Separate scoring and sealed records do
not establish comprehensive resistance to adversarial scorer manipulation.

\paragraph{Interruption and provenance.}
The original resource lease ended during cell 7. Its request, failure, cleanup,
and unknown termination-sender evidence remain retained. A separately admitted
managed lease and continuation runtime govern cells 8--32 without replaying
the consumed prefix or changing requests, model, order, scorer, limits, or
analysis. Both runtime source versions remain explicit. The lease is a
cooperative allocation, not an exclusive physical resource reservation;
per-phase process boundaries apply the configured resource limits.

Continuation checks add work around effect admission and receipt signing.
The signed gateway interval ends before signing; whole operator invocation
time extends through subprocess completion and output flush/synchronization.
These distinct intervals must retain their endpoints rather than being
presented as a single total host clock.


% END retained input: fragments/design.tex


% BEGIN retained input: fragments/analysis_method.tex
\section{Analysis and evidence separation}
\label{sec:analysis-method}

For family $f$, arm $a$, and repetition $r$, let $Y_{far}$ indicate admitted
useful completion. Average the two fixed repetitions within each family and arm:
$\bar Y_{fa}=(Y_{fa1}+Y_{fa2})/2$. The retained contrast is
\[
  \widehat{\Delta}=\frac{1}{8}\sum_{f=1}^{8}
                   \bigl(\bar Y_{fB}-\bar Y_{fA}\bigr).
\]
Families are the independent analysis units; 32 nested cells are not 32
independent repositories. A descriptive robust-family outcome additionally
requires both repetitions to succeed and is not a promotion decision.

The frozen bootstrap draws eight whole family blocks with replacement, sharing
each draw across arms and repetitions. It uses 20,000 resamples, Python 3.12
\texttt{random.Random} with seed 20260911, lexicographically ordered family
identifiers, and exactly eight \texttt{randrange(8)} draws per resample.
The 95\% percentile endpoints use linear interpolation at $(B-1)p$ for
$p\in\{0.025,0.975\}$ and $B=20{,}000$. These intervals are conditional,
descriptive summaries of eight convenience-selected families, not
population-level coverage or superiority/noninferiority decisions.

Failures remain in the fixed outcome denominator. Resource summaries report
their available-observation counts and missingness. Provider child, HTTP
wrapper, gateway, scorer, and operator clocks can overlap and are not added
as disjoint costs. Shared native preparation is counted once. Baseline checks,
prior failed attempts, review, queue waits, cleanup, and artifact work retain
their own accounting scopes. Token usage and cost ticks are telemetry;
unavailable settled charges and unmeasured effort remain unknown.

The developmental pilot is a separate four-family, 24-cell A/B study with
three nested repetitions. Its retained labels include ten useful completions,
five per arm, from 24 POSTs and 12 scores. Ten child durations exceeded 595
seconds by less than 1 ms, and pilot cell 20 exceeded 600 seconds in both
wrapper and gateway clocks. These deviations and labels remain preserved;
the final resource policy is not applied retrospectively to relabel the pilot.

Earlier boundary evidence is also separate from final repair outcomes.
The mutation/cold comparison retains one false reuse among all 26 cases,
rather than reporting a selected zero-of-25 subset. All four later correction
invocations, including failed and partial attempts, remain visible; corrected
full-cold execution supplies no positive reuse credit. Constructed gate checks
and public-baseline passes do not count as useful final repairs.


% END retained input: fragments/analysis_method.tex


% BEGIN retained input: appendix/historical_results_details.tex
\section{Historical cold-study accounting details}
\label{sec:historical-accounting}

\paragraph{Complete fixed-cohort accounting.}
All 32 planned cells have verified terminal records; none is missing or replaced.
The experiment made 32 original proposal POSTs and 16 scoring invocations,
of which 15 completed cold validation. Useful completion was 9/32 (28.125\%):
A achieved 5/16 and B 4/16. Table~\ref{tab:final32} reports the family counts.
Failures remain in these denominators. The mean of the eight paired family
differences, B minus A, is $-0.0625$, or $-6.25$ percentage points. The frozen
20,000-resample whole-family bootstrap gives a descriptive 95\% percentile
interval of $[-0.1875,0]$. Each resample draws eight families and preserves both
arms and their nested repetitions. The interval describes this convenience
sample; it supplies no population-level superiority, noninferiority, or
promotion decision.

\paragraph{Concentration across families.}
Tomlkit yielded one useful completion per arm, Tornado two for A and one for B,
and more-itertools two for each arm. The other five families yielded none.
Seven family differences are zero; the Tornado difference is $-0.5$ and
accounts for the aggregate gap. Its B cell~012 (repetition 130363) ended in a
transport failure without a response or scorer invocation. This outcome remains
part of the fixed comparison. The data do not isolate an effect of semantic
content, a particular native component, or prompt compression. The treatment
changes the combined request, and the recorded endpoint includes operational
and provider failures.

\paragraph{Failure categories and incomplete validation.}
The remaining 23 cells comprise 14 proposal-child deadlines, two known proposal
failures, and seven records with the original signed label
\texttt{hidden\_acceptance\_failed}. The two proposal failures were cell~003
(Tomlkit, A, 130363), which returned HTTP~503, and the transport failure in
cell~012. Their known local termination does not establish whether a remote
charge occurred. Among the seven hidden-failure labels, six completed cold
validation and failed executed hidden checks. Cell~005 (installer, A, 104729)
instead passed 28/28 public checks but collected zero hidden assertions and
ended with an import-name failure. It is incomplete hidden validation, neither
an observed hidden behavioral assertion failure nor a demonstrated external
infrastructure fault. Its original label and zero useful credit are preserved;
no candidate, test, or failed request was revised and rerun.

\paragraph{Measured time and unavailable costs.}
The provider-child, HTTP-wrapper, and signed proposal-gateway clocks each cover
32/32 cells. Their medians are 472.777, 473.660, and 474.107 seconds,
respectively. The 14 deadline cells are resource-unqualified under the frozen
measured predicates; configured caps do not imply that every measured duration
complied. Scoring-gateway time is available for 16/32 cells, with a median of
2.500 seconds across those invocations, including the incomplete validation.
Only one of eight families has complete scoring-time observations for both
repetitions of both arms. The frozen policy therefore leaves the paired
scoring-cost interval unavailable instead of imputing zeros or bootstrapping
fewer families. Grant-to-terminal duration includes waiting and bookkeeping:
its median is 603.644 seconds and its maximum 10,938.574 seconds. These intervals
overlap and are not summed. API usage is reported for 16/32 cells; settlement
is unavailable for all 32. No dollar total, complete effort cost, or net
efficiency gain is established.

\paragraph{Runtime and accounting deviations.}
The original lease ended during cell~007. Its consumed failure and unknown
signal sender remain recorded; a prospectively admitted continuation covers
only cells~008--032, with separately identified executable sources. The original
requests, order, limits, and analysis policy remain fixed. The 26 additive
disclosures also preserve pre-effect launch errors, bookkeeping takeovers,
diagnostic corrections, and interrupted operator work. Cell~027 had sufficient
credential headroom at its metadata check but only 895.290 seconds at the
later reservation, below the intended 900-second margin; exact POST time is
unobserved. Cell~029's delayed bookkeeping enlarges its grant-to-terminal clock
without creating another scientific trial. Outer invocation durations and
work after signed-gateway clock sampling retain separate scopes and missingness. They are not added
to the signed gateway interval or treated as measured AI reasoning effort.

\paragraph{Evidence and comparison limits.}
Fifteen failed proposals lacked original candidate-binding files. Their later
unsigned sidecars describe the unchanged public inventory and an empty patch;
they are derived metadata, not returned model edits, recovered original files,
or successful candidates. The four-family developmental pilot remains separate:
its 24 cells yielded ten historical useful labels, five per arm, with retained
timing deviations rather than retrospective final-policy compliance.
Earlier boundary evidence in Table~\ref{tab:boundary-history} is also separate
from final repair outcomes. The ablation scope in
Table~\ref{tab:withdrawn-comparisons} records unmeasured or withdrawn endpoints.
C/D routing, warm-cache reuse, publication efficacy, and the original
sixteen-family inferential objectives are not evaluated by these 32 cells.

% END retained input: appendix/historical_results_details.tex


% BEGIN retained input: appendix/incremental_qualification_details.tex
\section{Explicit public development objectives}
Twelve newly authored public examples make three original development objectives
concrete using their retained public titles and prefix-source APIs. They are not
recovered historical issue text, hidden acceptance checks or independent families.
On unchanged XML, OAuth and Click prefixes, respectively, 2/4, 1/4 and 2/4
examples conform. XML attaches namespace declarations to a descendant when the
declaring element has no ordinary attributes; OAuth authorization metadata raises
an AttributeError, including with explicitly supplied response types; Click help
still enumerates choices when their display is disabled. Public comparison cases
exercise ordinary attributes, disabled namespace processing, token-only metadata,
visible choices and explicit metavar behavior.

All twelve examples run in three fresh processes under frozen 60-second bounds,
with no setup errors. An earlier run's three missing-constructor-argument errors
are retained as harness failures. The revised OAuth setup uses actual token and
endpoint classes and all required combined-server claims. Full unchanged source
inventories retain 16, 199 and 145 entries; actual imported modules bind to those
prefixes. A separate 545-check audit reconstructs predicates and source/process
provenance without further execution. The new objective manifest binds text,
examples, repair surfaces and public API sources. Together with the separately
retained nine-example Pyparsing public-report reproduction, these provide explicit
development objectives for the original four-family matrix. Independent scorer
admission, complete operational trajectories and matched cache/component arms
remain required. No model or hidden scorer is called; example conformity is not
a repair-success or system-quality estimate.

A later qualification exposes a limit in the newly authored OAuth expectation.
The original accepted reference passes three of four public examples; combined
server metadata omits one configured response type. An independently authored
configured-key-preserving candidate passes all four new examples but fails the
unchanged original acceptance check. Public-only API review does not justify
requiring the abstract-validator metadata probe to advertise every internal
dispatch key. Exact three-key equality is therefore an unqualified author
assumption, retained diagnostically rather than imposed on original acceptance.
This is a prospective contract correction before new model dispatch; neither
the original criterion nor the contrary observations are overwritten. It is not
a proof that every possible repair faces incompatible requirements. The
supplemental native call's missing enclosing timer also remains unknown.

\section{Additional benchmark qualification}
\label{sec:incremental-recruitment}
An independently pinned SWE-bench Verified metadata projection~\citep{swebench2024,swebenchverified2024} supplies 500
candidate repairs from twelve repository names. Ten of eleven prospectively
selected two-issue pairs have forward base-commit ancestry; one has reverse
ancestry in PR-date order. A separate current GitHub identity audit checks all
192 candidate/original repository pairs, finds no shared repository or declared
fork identities, and flags two shared-owner groups. This does not establish
historical code independence, portfolio separation or absence from model
training. A later audit reports test-specification problems in a selected hard
subset and evidence of solution exposure in tested frontier models~\citep{swebenchverifiedaudit2026}.
Its selected-subset rate is not a whole-dataset error estimate, and it does not
measure contamination in our provider profile. Public examples exposed during
this literature review are separately recorded before any prospective split.
No new confirmatory family or complete natural trajectory is enrolled.

Requests 6028 has a separately named ARM environment preserving its
public Python version and thirteen listed Python package versions. The unchanged
native SWE-bench 5.0.2 parser/grader observes all 187 designated checks in both
controls: unfixed source passes 185 and fails the two required failing checks;
reference source passes all 187 and is the only resolved control. Both collected
outputs also contain eight missing-fixture setup errors outside the designated
set. The original script lacks a test-exit marker, so a zero container exit
cannot establish acceptance. This is designated-check qualification, not an
error-free full-suite result or equivalence to the published x86 environment.
Protected reference/test content remains in curator custody; model-facing
selection reads public metadata only. Earlier import and decoding failures are
retained. Infrastructure qualification contributes no provider-token or repair
success observation for either treatment.

Requests 5414 subsequently qualifies in a new named ARM profile
using its public development dependencies and Docker's default bridge network.
Both controls complete all 131 designated checks: unfixed source passes 130
and the reference passes all 131. The full parsed outputs have 288 versus 289
passes, respectively, with one expected failure each and no setup errors.
The original offline port, a dependency-build failure and a plugin-startup
failure remain retained; the successful profile is a development correction.
This does not make the original failed port successful. A later candidate
grading service version fails its four-control qualification: three controls
behave as expected, but this node's reference is not accepted despite all
designated checks completing. Four existing public network-timeout checks
instead encounter a network-unreachable condition; the earlier standalone
run used the same image, package versions and evaluation bytes. The unique
cause and a reliable remedy are not established by this discrepancy.
Eight service rejection controls pass. This retained discrepancy illustrates
why standalone benchmark qualification alone does not qualify a new endpoint.
A subsequently frozen service version passes one attempt at each of its four
native controls and all ten rejection controls. It preserves exact objective,
profile, cumulative patch and resulting source-tree bindings. Public network
readiness probes bracket Requests 5414's evaluation, with no automatic retries;
an incomplete grade remains unavailable for repair decisions. All eight
qualification probes pass. The 94-check audit retains 1,175 artifacts; the four
control containers take 87.429894 seconds in total. This qualifies the named
service and its observed controls, without proving the unique cause or remedy
of the previous network failure or stability throughout future test runs.
Candidate and benchmark tests still share the original test process; adversarial
oracle integrity is not established. Requests 6028 retains its eight
outside-set fixture errors.

An additive public-only cumulative-source control changes two production files
and adds one Git-ignored Python file. The service inventories all 98 resulting
files, matches the independently expected tree, and returns the unchanged
unfixed grade of 185/187 in 6.048 seconds. This checks complete source-carry
transport into grading, not successful repair or an accepted multi-issue
trajectory. Earlier four-control cohorts remain unchanged.

A further pinned metadata-only projection yields 21,336 SWE-rebench
rows~\citep{swerebenchmetadata2026} from 3,468 repository names and 731
SWE-bench Pro rows~\citep{swebenchprometadata2026} from eleven names.
The 22,067-row sum is not deduplicated across datasets; protected issue,
reference and test fields are not decoded in this projection. A prospectively
seeded screen uses 2025 metadata dates, available image fields, distinct base
commits and exclusion of prior repository/owner names. It yields 53 candidate
pairs. All first sixteen pairs have actual forward Git ancestry, and 448
comparisons against the 28 prior current repository identities find no
repository, declared-fork or owner match. Each candidate has a distinct current
repository and owner identity. These checks do not prove historical code
independence, portfolio separation or training novelty. Image-field eligibility
is a convenience filter; all 32 selected image names specify x86\_64, whereas
the evaluation host is ARM. Source/environment/scorer qualification and a
prospective confirmatory split remain open; zero new families are enrolled.

The first frozen additional pair, Zarr 2996 and 3015, subsequently passes four
original native grading controls on explicitly ported ARM environments. Unfixed
source passes 16/22 and 157/158 designated checks, respectively; each reference
passes its complete set. Every control runs once, with zero retries or provider
calls. The native test-spec factory, test commands, parser and designated
criteria remain unchanged; the script port removes four Conda activation
commands. The environments preserve Python 3.11.11/3.11.14 and all 50/67
observed installed distribution versions, while architecture, platform binaries
and system-library builds differ. The local native fork reports version 4.0.3.
Its complete declared dependency installation failed because an ARM YSON
binary distribution was unavailable; a separately named local Docker backend
uses the available Python implementation, leaving cloud backends unsupported.

The four native grader container intervals total 10.647 seconds, excluding
environment acquisition, builds, Git preparation and audit. Earlier missing
build-helper, project-version and Git-image-reference failures remain retained.
The full public collection probe collected 3,045 tests for 2996 and exited zero;
3015 collected 3,123 but exited one during teardown with resource/unraisable
warnings. The targeted controls do not reproduce that teardown failure, and
their success does not erase it. As with Requests, the original script lacks
a separate test-exit marker, and native shared-process execution does not
establish adversarial oracle integrity. These results qualify the four original
controls; candidate endpoint, complete trajectory and token economics require
separate evaluation. No confirmatory family is enrolled by these controls.

A subsequent Zarr candidate endpoint qualifies all nineteen frozen controls,
with 190 audit checks: six actual native grading calls, ten rejections before
dispatch, two wrong-source containers stopped before hidden grading, and one
duplicate-ID rejection. Empty and cumulative-public candidates retain the
unfixed grades; reference production projections pass 22/22 and 158/158.
Each projection preserves the full original reference's production and
base-public bytes while omitting one ancillary added document, then reruns
the unchanged designated checks. This qualifies the projected candidates,
not transport of the full original patches. Non-Python edits remain outside
this endpoint's admitted scope.

Exact public base inventories contain 189/181 files, including the editable
installation's generated version module. Cumulative controls make three
production edits, including a Git-ignored addition, and retain all 190/182
resulting files. The initial endpoint attempt failed before hidden grading
because of raw mode differences and its rejection of the ancillary document;
a later preparation attempt caught a no-op Git apply in a nested checkout.
Both failures remain retained. The qualified revision preserves image-exact
modes and verifies actual edits in isolated Git repositories.
Six grader containers total 14.426 seconds within 30.363 seconds of outer
service calls, including the duplicate-ID control. Preparation, environment
acquisition and audit are separate. There are zero retries or provider calls.
Context, accepted-source trajectory carry, publication and model efficacy are
not enrolled by this endpoint qualification; adversarial oracle integrity
and non-Python transport remain unqualified.

The second frozen additional family, Xradar, then completes its four original
native controls on explicit ARM ports. Issue267 has 11/13 unfixed passes and
13/13 reference passes; issue269 has 55/58 and 58/58. All designated cases
complete, with one attempt per control and no provider calls. Full original
reference patches, including ancillary edits, are retained. The unchanged
native factory/parser/test commands govern both nodes. Public collection yields
354 and 356 cases with exit zero. Each public prefix matches 106 original Git
blobs, and all 22 data fixtures selected from pristine public tests match their
registry hashes, totaling 183,051,686 bytes; both images fetch them offline.

Both ports preserve Python3.10.17 and all 196 installed distribution records,
including two project distributions with natural imports resolving to the
base-specific editable source. Four exact package versions require ARM source
wheels. Conda binary/build variants and optional compiled-feature parity remain
unqualified. Retained failures include initial duplicate-project metadata
ambiguity, a missing ARM binary wheel, and a node-orchestrator key error after
the shared runtime built. Versioned corrections preserve runtime pins and do
not retry grading. Failed and successful shared builds take 118.916 and 188.913
seconds; cached-wheel materialization takes 19.143 seconds, and the complete
node-build/import/cache/package/collection phase 31.950 seconds. Four native
grader containers total 69.044 seconds; these are scoped intervals, not complete
recruitment cost. Environment and native audits pass 373 and 129 checks,
respectively, with 120 custody artifacts and 59 native source files. Candidate
endpoint, context, model trajectory, confirmatory enrollment and adversarial
oracle integrity remain unqualified.

For a later development experiment on the existing pyparsing snapshot, the
current public issue report supplies a concrete objective. Its nine examples
reproduce the reported recursive-whitespace defect on unchanged public source:
eight conform to the reported expectation and one fails. The report is frozen
for that new experiment; its exact bytes at the original base date remain
unverified. A reproduced public example is not complete hidden acceptance.

\section{Repository preparation and source custody}
\label{sec:incremental-context-preparation}
\paragraph{Repository context custody and preparation cost.}
A separate native producer/consumer qualification retains all 302 regular files
across the XML and pyparsing development snapshots, including unparsed source.
Its bounded semantic scope analyzes one of six and five of 154 Python files,
respectively; four dependency capsules grant no source omission. Four
cold/incremental root-and-block comparisons agree, four exact source expansions
execute, and 22 negative controls reject. An added caller checks required-source
CIDs and current bytes because native freshness omits that mapping; native
``sufficient'' flags are not behavioral authority. Full pyparsing scanning
produces 3,957 symbols and 55,859 edges, but the unmodified producer process does
not finish within its 600-second bound. Hoisting a repeated immutable
node-CID index preserves the full XML state/root and reduces its preparation
from 64.838 to 26.296 seconds in one observation per profile. Full pyparsing
still reaches the 600-second bound after that change. Source retention and
bounded integration therefore do not establish affordable whole-repository
preparation, context compression or repair efficacy. Three later isolated
profiles add a fixed-profile CID encoder, cached syntax validation and an exact
literal-union predicate. Across all five profiles XML state/root identity is
unchanged and every native consumer passes; each full pyparsing producer still
hits the process deadline. In the last profile the producer writes its result
at 597.222 seconds before the 600.202-second termination; the native consumer
does not run. An earlier stage diagnostic had also assembled and verified a
full bundle before timing out in source-binding reads. Missing final output
therefore does not prove that bundle construction itself failed.

The literal-union change preserves all 55,859 actual link predicates against
3,957 node CIDs, an embedded-CID rejection, 1,235 constructed comparisons and
64 native regressions. The independently validated full bundle has 67,872
blocks and agrees with the last producer's state/root. Its 72.358 versus 2.834
seconds measure only one diagnostic predicate pass per implementation on a
shared host; they are not a whole-pipeline speedup estimate.

A generic current-repository service separately checks exact source inventory,
file modes and objective/request identities. Twelve controls pass across three
XML preparations: a source change requires new state/root/pack identities,
whereas an objective-only change retains state/root and creates a new pack.
Both public Requests nodes then complete actual native producer/consumer
roundtrips, retaining 97 files each and scanning all 35 declared Python files.
Eleven negative controls pass per node; neither node permits any raw-source
omission. These are context and custody checks, with zero provider calls and
no repair-quality or compression comparison.
Four subsequent Requests API expansions return 79,942 exact raw bytes across
two real read processes, preserving source, request, freeze and objective
identities. They add no omissions or model calls.

A sixth isolated profile memoizes identity only within an exact immutable
native state instance under frozen codec/runtime bindings. Both full producer
processes and their separate native consumers now complete. XML preparation
takes 9.103 seconds; pyparsing takes 566.254 seconds, with
553.516 CPU seconds. The latter producer process takes 569.609
seconds and its consumer 1.740 seconds. All 302 regular files and
11,781,935 bytes are materialized; pyparsing's additional opaque symlink is
retained without following it. Both sources' previous available state/root
identities agree, including the independently checked 67,872-block pyparsing
bundle. All 22 binding/tampering controls pass and all 7,255 frozen runtime
source files remain unchanged. Zero source omissions and zero signed receipts
are retained, along with the unresolved semantic frontier.

The profile passes 159 native regressions. Separate full XML unchanged,
comment-change cold and comment-change incremental states preserve serialized
identities and all 1,992 reachable blocks across the parent and memoized
profiles. Each profile performs twenty actual source materializations and
rejects twenty corrupt-source reads. This qualifies immutable-object identity
caching, not execution/proof reuse or a defense against reflective mutation of
frozen objects. The successful full run establishes completion within the bound, not a
replicated speedup or token benefit; the five previous deadlines remain results.

A subsequent frozen full-pyparsing comment-change comparison fails cold versus
incremental equality. Its three workers complete within a separately declared
900-second bound: baseline 656.008 seconds, changed cold 609.801 seconds and
changed incremental 784.021 seconds. Baseline and changed-cold workers run
concurrently on the shared host; incremental restoration, full source guards,
native previous-state/bundle loading, persistence and process exit are included
in its worker interval. Earlier driver enrollment copy/freeze creation is not
separately timed. These observations establish no incremental speedup.

The changed snapshot, symbols and artifacts agree, but 1,568 of 55,859 edge
records differ: 1,564 ambiguous candidate edges change resolution metadata from
\texttt{finite\_may} to \texttt{definite}, and four derived references change
with their edge identities. All retain conservative confidence and multiple
candidates. Consequently state and semantic-root identities differ. Independent
comparison reads every persisted block: 65,856 shared CIDs have identical bytes,
with 2,016 distinct CIDs on each side, covering links, capsules and their indexes
and roots. Both stores contain 67,872 blocks; their payloads total 112,728,034
cold versus 112,724,906 incremental bytes. Ten source-read controls pass and
7,255 runtime files remain unchanged. The driver exits one at the equality
assertion after all workers exit zero; this is a retained graph-metadata failure,
not another preparation timeout. A later actual native explanation-consumer
probe loses the ambiguity limitation on all 1,564 directly changed edges while
retaining their conservative-confidence limitation; four derived references
are excluded. The fresh process takes 3.070 seconds and rechecks 7,255 runtime
files. This establishes an explanation-output consequence, not an execution
authorization or soundness failure.

A subsequent isolated guard refuses previous-state frontend reuse when graph
projection has already replaced a lexical target with a concrete symbol.
Such paths are reanalyzed from current source before whole-inventory resolution;
the guard does not simply preserve stale resolution metadata. Seven changing
inventory controls preserve state, roots, all block bytes and explanations.
The full pyparsing comment-change comparison then restores exact serialized
state/root equality and all 67,872 block payloads (112,728,034 bytes), also
matching the earlier cold output. It reuses 20 of 154 Python paths, 172 symbols
and 1,428 original frontend edges, while rescanning 134 paths. These counts
are not omitted source bytes or avoided execution checks.

The two fresh workers run concurrently under unchanged 900-second bounds:
cold takes 437.699 seconds and guarded incremental 614.522 seconds. The latter
includes 107.173 seconds of prior-state restore/reverification and 55.736
seconds of scanning; graph construction and full verification still execute.
The earlier 656.008-second baseline preparation is reused as an artifact and
remains a separately incurred cost. Enrollment copying/freezing is not timed;
the subsequent independent byte audit takes 3.625 seconds. Nine new source
controls pass and 7,255 runtime file digests remain unchanged. Native regression
tests retain 187 passes and one failure: an existing performance expectation
requires reuse of a path that this correctness guard deliberately rescans.
An earlier invalid authored fixture is also retained. A further inventory
control exposes the guard's limit: adding a previously missing imported module
leaves incremental confidence conservative while cold analysis becomes exact.
The guard's successful comment-only comparison remains valid, but it is not a
general lossless solution. No execution-soundness consequence is inferred.

A new profile instead persists the original Python frontend observations before
pytest unification and graph projection. It binds their exact sidecar bytes to
the accepted parent state, source inventory, namespace and extractor/runtime
profile; unsupported or stale inputs fall back to current analysis. Current
pytest analysis and whole-inventory graph resolution still run. The full
comment-change comparison reuses 153 of 154 Python paths, 3,885 original symbols
and 52,977 original edges, extracting 772 edges from the changed file. Cold and
incremental serialized state, root, all 67,872 blocks/112,728,034 bytes and the
complete sidecar agree. The native state and blocks also equal the earlier cold
output. Each sidecar adds 53,753,923 bytes of storage. Ten bounded equality
cases and sixteen rejection/fallback checks include the earlier unresolved-import
confidence case; ten full-worker source controls pass and 7,256 runtime hashes
remain unchanged. Accepted honest producer custody remains an assumption:
hash binding alone does not prove that arbitrary observations follow from source.

All three new workers finish within frozen 900-second bounds. Baseline sidecar
bootstrap takes 231.354 seconds in addition to the separately paid original
656.008-second preparation. Changed cold takes 440.276 seconds and incremental
607.971 seconds. Incremental includes 105.262 seconds of parent restoration and
verification, 55.520 seconds of scanning with observation decode/encode,
390.254 seconds of bundle construction, 48.819 seconds of full verification and
4.727 seconds of persistence. Bootstrap overlaps changed cold; incremental
follows bootstrap, for 839.328 seconds of new worker schedule time. Enrollment
takes a separate 0.533 seconds and the independent audit 5.958 seconds.
Nested stages are not added again to process totals. This qualifies actual
original-observation reuse on one full public change; incremental preparation
is still slower, and zero source omissions or provider calls establish no
token saving or general speedup.


\section{Combined controller, publication and recovery}
\label{sec:incremental-controller-publication}
\paragraph{First combined controller qualification.}
A new caller joins actual native context reads, source-bound semantic analysis,
symbolic routing, compiler-mediated world memory, isolated behavioral scoring
and a durable effect journal. On the four existing constructed routing tasks,
two supported initial repairs pass and two remain residual-pending with the
provider disabled. Authored follow-up events consume accepted source, recheck
a comment change and reject a stale local parent. Ordinary no-op detection
receives the same current behavioral checks as the memory path.
Three actual process interruptions exercise validated continuation, durable
receipt reconciliation and an executed effect whose completion remains unknown;
the unknown effect is held without redispatch. Across thirteen events there are
nine local acceptances, two pending residuals, one stale parent and one unknown
effect. These event counts are not thirteen independent repair tasks. Thirty
scorer attempts yield 29 durable terminal receipts. Local ledger CAS is not
native Kit publication; sealing, lifecycle reuse and certified procedures are
not yet combined here. With zero provider calls this qualification establishes
no integrated token-savings effect.


\paragraph{Subsequent native publication profile.}
The separately frozen eight-event sequence yields six acceptances, one stale
branch and one pending residual. A full checkpoint at generation 0 is followed
by a delta at generation 1. A real service exits with code 94 after native
seal persistence and before CAS. A fresh process loads the pending seal,
rechecks the entire parent chain and exact local evidence, replays visible
and audit behavior, then completes native CAS/WAL through an explicitly added
development adapter, reaching generation 2. Another fresh event consumes the
native stored accepted source and publishes generation 3. A branch based on
generation 0 reaches native publication and loses with a generation mismatch.

\begin{table}[htbp]
\centering
\caption{Actual work in the eight-event native publication qualification.
Event outcomes are dependent continuation observations.}
\begin{tabular}{lr}
\toprule
Operation & Count \\
\midrule
Controller invocations / terminal effects & 9 / 68 \\
Native context reads / source expansions & 4 / 8 \\
Input scans / accepted-candidate scans & 8 / 3 \\
Symbolic attempts / produced candidates & 4 / 3 \\
Native routing calls & 8 \\
World-memory service calls / compiled actions & 11 / 2 \\
Publication attempts / native reads / recovery & 7 / 4 / 1 \\
Controller / additional admission scorer processes & 18 / 24 \\
Provider requests / provider tokens & 0 / 0 \\
\bottomrule
\end{tabular}
\end{table}

Invocation wall time is 60.906438 seconds; the additional 24 behavioral
replays consume 13.759197 seconds within that total, not as a separate additive
cost. Context enrollment, inventory freezing, implementation and read-only
audit are outside this runtime denominator. Crash-time work is retained through
a durable receipt, and recovery does not double-count its aliased completion.
Both ordinary and memory paths run the same cheap current-source check and
accept no-op revisits without symbolic or model repair. The compiled memory
action dispatches an actual check; no reduction in checks is demonstrated.

The complete required leaf set is externally frozen: accepted source,
semantic preparation, effect inventory, visible behavior and audit behavior.
Every changed candidate receives a new native scan. All five leaves are
replaced per delta. Native integrity verification checks content and digests;
unsigned local receipts additionally depend on trusted controller/scorer
execution, a durable effect ledger and an evaluation-owned CID index. This
is neither a theorem about arbitrary Python nor production trust admission.
Stored parent chains are recursively checked and the requested source is
behaviorally replayed on read. Broader crash phases, concurrent publication,
provider effects, real repository edits and lifecycle reuse remain open.

The read-only audit passes 6,424 checks. The archive retains 504 source and
metadata files, including 483 native source files across the loaded closure
and preceding context enrollment. The first profile's omitted imported wrapper
and the first audit's pointer-envelope parser failure are retained. Correcting
the audit did not rerun behavioral outcomes; the archived previous controller
still passes its original 9,188 checks.

\paragraph{Full-repository service fixture and measured cost.}
A separate curator-held Requests 6028 fixture begins with its reference
candidate and then adds a neutral comment to the same accepted production
source. Both states contain all 97 source files. It executes two full native
context preparations, four world-memory service calls and six original native
grader invocations: two initial checks and four fresh publication, interruption,
recovery and read replays. All six complete the 187 designated checks.
Reference and hidden test payloads remain in curator custody. This fixture
does not execute the Requests 5414-to-6028 upstream transition or any model
repair, and it does not establish adversarial oracle integrity.

The first full checkpoint reaches generation 0. The second process constructs
a delta and actually exits with code 94 after seal persistence but before CAS.
A fresh process recovers generation 1; another fresh process reads and restores
the exact second accepted source. Wrong-tree, wrong-receipt, source-drift and
incomplete-effect controls all reject before grader replay. All four required
leaves---accepted source, semantic preparation, observed non-sealing effects
and native behavior---are replaced on transition. The effect leaf excludes
all sealing operations, including prior reads; the outer workflow ledger must
still count their actual work. Parent/source admission and fresh grading are
additional checks. Unsigned local receipts and native integrity mode establish
neither a theorem of execution nor verification reuse.

\begin{table}[htbp]
\centering
\caption{Measured disjoint sequential intervals for the Requests 6028 curator
fixture. Grader processes are nested in these phases and are not added again.}
\begin{tabular}{lrr}
\toprule
Phase & Count & Wall seconds \\
\midrule
Full native context preparation & 2 & 318.283 \\
Initial accepted-candidate checks & 2 & 16.047 \\
World-memory service calls & 4 & 5.858 \\
Publication/recovery/read and rejection controls & 8 & 37.037 \\
\midrule
Sum of measured intervals & & 377.226 \\
\bottomrule
\end{tabular}
\end{table}

The six grader containers consume 31.625 seconds within the measured
intervals. Their four replay service wrappers are also nested, not independent
extra costs. The frozen-start-to-result artifact span is 377.640 seconds;
this is not a separately instrumented whole-process timer and excludes earlier
imports and profile creation. Later code archival and read-only audit take
0.275 seconds together, outside the fixture intervals. There is one
shared-host observation, no parallel comparison and no provider calls.
The 275-check audit retains 33 public code snapshots and hashes 1,136
private artifacts. This closes the stated service controls while leaving
multi-issue model efficacy, token savings and broader crash coverage open.

\paragraph{Natural Requests sequence: intervention and failure paths.}
The first live repository cohort contains one development family, two genuine
public issue nodes and four arms, executed in frozen D/C/A/B order with
independent local cold stores. Each trajectory has at most four provider
requests, with at most two at its first issue; unused slots carry forward.
All planning, proposal, expansion and recovery purposes share that ceiling.
The common Grok 4.6 low-reasoning profile has a 2,048-output-token limit and
a 65,536-byte request limit. Source retrieval selects whole production modules
with three-file/48,000-raw-byte limits, and exact requested expansions replace
the earlier selection. Accepted first-node source is committed on its exact
public base and carried through a real three-way merge with the next base.
No reference patch enters the model or its public history.

A uses ordinary lexical retrieval and the common current-source check. B
actually prepares and reads native context, but zero omissions qualify, so its
model context falls back to the same raw source. C additionally runs native
analysis, bounded synthesis and routing; its native candidate fails before
the model repairs the first issue. D adds actual world-memory services,
accepted-source context preparation, native publication and stored-source
read. It remains partial: lifecycle reuse, certified procedures, learned
world utility and integrated theorem proof are absent. Native permitted model
routes share the same fixed provider profile, so model-tier selection cannot
explain cost differences. Each arm retains its own histories and state; the
effect journal provides durable identities for every arm.

All four initial requests have identical canonical bytes and 13,693 provider
input tokens. Each returns one independently passing first-node repair. A and
B receive 13,568 cached input tokens each, versus 512 each for C/D; local cold
state therefore does not imply equal remote cache state. Returned reasoning
and output lengths vary. Small first-node total-token differences cannot be
attributed to source compression or a witnessed avoided model call.

A/C/D's accepted edits each conflict in the next public source merge.
Their retriever appends the required conflict module to its ordinary selection,
yielding four modules, 80,552 raw source bytes and a 91,202-byte request. The
frozen 65,536-byte gate halts before dispatch. B's different initial edit
merges without a conflict and its next request fits at 53,319 bytes. Its
three subsequent candidate grades are 184/187, 185/187 and 185/187, all
unsuccessful; the original current source passed 185/187. The second node
thus fails in every arm, through different observed paths. Source-bound
halts are retained failures, not successful symbolic closures.

The complete fixed-cohort provider totals are 14,428 (A), 65,695 (B),
14,589 (C) and 14,269 (D), summing to 108,981 across seven actual posts.
Each arm has one accepted node, so tokens per accepted node equal those
fixed-cohort totals; tokens per completed trajectory are undefined. All
unsuccessful model attempts remain charged. The first-horizon totals are
14,428/14,192/14,589/14,269 in A/B/C/D order. These are observed cumulative
costs, not counterfactual quality-versus-budget curves or independent repeats.
Charges, cached input, visible output and reasoning components remain separate
in the retained provider receipts; account settlement is not inferred.

The original driver terminates with exit 143 while B's first controller is
still running. That same worker finishes and commits its accepted event.
A separately frozen reconciliation checks the exact terminal output, journal,
source/profile identities and absence of pending effects, then executes only
the original remaining B6028 event. B5414 is never restarted. Its outer
invocation time, waited CPU and exit status remain unavailable; the controller's
own 209.770-second timer survives. B's two controller intervals sum to
408.510 seconds, which is a different timing scope from other arms' enclosing
invocation intervals. Docker workload CPU is unavailable throughout. Preparation,
grading, memory and publication/read phases are nested within runtime and must
not be added twice. Development qualification and source/environment acquisition
remain separately scoped overhead. A/C/D enclosing intervals are 96.745,
285.790 and 507.358 seconds, respectively; B's enclosing total is unavailable.

The separate ledger audit passes 1,769 source, journal, request, attribution and
budget checks. It joins all seven model receipts to their actual effects and
dispatch intents, with no unknown provider effects. Sixteen unique native
grader receipts include the two additional D publication/read replays; repeated
appearances of saved completions are not new calls. Model and effect accounting
are complete for this cohort, while outer runtime accounting remains incomplete
because B5414's enclosing timer is missing. The source archive contains 504
files. Preparation records include observed native imports; the source-expansion
process lacks a separate actual import receipt, which limits the demonstrated
execution closure. The quantitative result is not a production trust admission.

One family with implementation failures and uncontrolled server caching cannot
identify a general mechanism effect. Equal accepted-node counts also conceal
the different second-node opportunities. No arm completes the intended natural
trajectory, and the broader cache, warm-horizon, ablation and independent-family
program remains required. Subsequent transport corrections receive a new profile;
these outcomes and request bounds remain unchanged.

\paragraph{Second natural Requests cohort.}
A separately frozen conventional retrieval correction gives mandatory conflict
modules priority, followed by optional lexical source that fits the existing
three-file/48,000-raw-byte/65,536-request-byte bounds. A detached driver retains
all eight outer invocation timers without restart. On actual B/D continuations,
the conflict and two optional modules fit in 47,424 raw bytes and a 54,773-byte
request. A/C's different accepted first edits merge cleanly. All four first
requests remain byte-identical within this cohort. No source omission or
successful symbolic closure occurs; D still lacks integrated lifecycle reuse,
certified procedures and learned memory utility.

All sixteen calls execute and consume 243,255 provider tokens, including
expansion decisions, failed proposals and local transport failures. A uses
two calls per issue, while B/C/D use one then three. Each accepts only issue5414.
A's first proposal passes 123/131 designated checks; the next passes. For
issue6028, A spends one call expanding source and one on a candidate grading
185/187. C expands once and grades two candidates at 185/187. D grades its
first and third candidates at 185/187; their cumulative patch bytes are
identical. B grades one candidate at 185/187. The remaining three outputs,
one D and two B, restore all 97 pristine file contents but retain mode0644
instead of0664 on one file. The frozen transport rejects these mode-only
differences; its text-edit interface has no mode channel. Those three provider
calls remain charged, no graders run for them, and their counterfactual grades
remain unknown. No retrospective repair or rerun alters this cohort.

Fixed-cohort tokens are 56,543/62,439/63,336/60,937 in A/B/C/D order; first-node
cumulative tokens are 29,787/14,782/14,364/14,163. Tokens per completed trajectory
are undefined. Total components are 227,336 input, 1,804 visible output and
14,115 reasoning tokens; 47,744 cached input tokens are a subset. Cached-input
counts are 1,024/30,976/14,720/1,024, so local cold starts do not control provider
caching. API-reported charges total \$0.1627138000; settlement is unmeasured.

All 21 unique grader calls complete: nineteen direct and two D publication/read
replays. Six passing and fifteen failing grades include repeated validation
of the same task and are not independent success counts. Their 509.499 seconds
of container time are nested within 544.910 seconds of outer grader service,
which is itself part of runtime. The 53 unique outer effects have complete
elapsed timers. Enclosing invocations total 1,382.526 seconds. Native context
contributes 106.468/211.192/213.978 seconds for B/C/D; D publication/read,
including replays, takes 78.228 seconds. These components are not added twice.
Docker CPU and driver-preflight CPU remain unknown. The logical runtime-state
snapshot contains 5,495 files/297,870,884 bytes, excluding qualification and
private scorer stores; it is not deduplicated physical usage.

The prospectively fixed detailed audit passes 3,698 checks; independent root
aggregate and final joins reconcile all costs, nodes and 510 archived sources.
The final root join passes 1,412 checks after retaining an initial projection-ID
assumption failure and joining explicit residual/enclosing event identities.
The curator independently joins all 21 requests, dispatches, receipts and outer
completions, with no unknown effects. All 310 observed worker/world/sealing
imports match the archive; a separate native context audit binds 163 observed
producer/consumer paths and all ten context effects. Expansion lacks a separate
actual-import receipt, and standard-library/third-party import closure is not
established by these native-prefix receipts. The follow-up supports no token
saving and is not pooled as an independent confirmatory replication. Original
cache, operational-sequence and component comparisons remain required.

\section{Native proof profiles and exact statement checks}
\label{sec:incremental-native-proof}
\paragraph{A real native proof relation.}
The copied native backend was built offline with locked dependencies because
the bundled binary did not implement the source's v3 circuit. Isolated
development keys support a four-leaf Event-DAG Merkle/count relation. Three
actual proofs for counts 1, 2 and 4 verify; eight witness, public-input,
proof and key mutations reject. Primary setup takes 7.810 seconds,
proof generation 12.048--12.474 seconds, and verification
3.053--5.147 milliseconds; serialized proof JSON is 1,484 bytes.
The raw verifier accepts a different outer root that maps to the same field
element. The evaluation caller's exact-root/count and key/binary checks reject
that alternate statement before dispatch. This boundary is part of the result:
the native relation alone does not bind arbitrary outer metadata. Development
setup is not production trust admission, and a Merkle relation is not proof
that arbitrary tests executed. The v5 pytest-attestation circuit remains
unsupported in this backend.

\paragraph{The original bounded Horn profile.}
The source-built v2 backend also produces and verifies three honest implication
chains of lengths 1, 2 and 4. Setup takes 1.101 seconds, proving
2.238--2.390 seconds, and verification
3.187--5.267 milliseconds; each proof JSON is 1,700 bytes.
The honest prover rejects the tested incomplete or inconsistent inputs.
When the scalar public inputs remain unchanged, the raw verifier accepts three
changed outer metadata fields; exact statement and source/key checks at the
evaluation caller reject them before dispatch. Honest examples and wrapper
checks do not establish that every satisfying circuit witness corresponds to
the advertised textual axioms. That stronger assurance remains unconfirmed.


\paragraph{Actual accepted-history archive integration.}
A separately frozen producer/consumer profile follows the constructed
controller's native generation-3 pointer through four accepted seals, each
with five required receipt units. It excludes the stale unaccepted branch and
the separate ordinary trajectory. Producer and fresh consumer use native Kit
verified reads on exact archive clones, reconstruct the original local effect
receipts and check the complete source, parent and leaf bindings. The original
archive and controller ledger remain unchanged. No behavioral checker is rerun;
the original local execution remains the authority for its recorded observations.

Each canonical event commits its seal/parent, source and original binding,
complete receipt-CID map and verified pack digest. The already qualified
standard v3 backend proves their four-leaf archive relation. The consumer
checks the externally expected full root/count and exact binary/key, in addition
to the accepted pointer and chain. The raw scalar-root limitation still applies;
the proof does not establish that arbitrary code or tests executed correctly.
The stopped custom-v2 investigation is not used.

One honest proof and one runtime pairing verification complete. Producer and
fresh-consumer read processes take 0.325531 and 0.342170 seconds, proving
12.617511 seconds and verification 0.006725 seconds. The measured driver
totals 14.749495 seconds, including source/key/archive hashing, clones and
negative controls. These phases are nested. Earlier backend compilation, the
original 7.810198-second development key setup and historical controller
execution are separately scoped costs. A later audit adds a 0.006085-second
native verification. This is one shared-host observation with existing keys,
not a replicated speed comparison or evidence that proving beats direct hashing.

All seven frozen controls reject: missing/corrupt receipt bytes, incomplete
leaf inventory, stale parent, reordered events, changed event source commitment
and changed full root. Four exercise the native reader; the last three reject
at exact statement binding before pairing. The proof JSON is 1,484 bytes;
the original 69-file store contains 2,010,722 bytes, including additional
unselected records. A small proof does not replace the original source/receipt
custody that the consumer still reads. The separate audit passes 218 checks,
recomputes all event digests and the full Merkle root, and archives 34 observed
source files. The audit shares the cryptographic backend. This establishes
no new behavioral check, model call, execution reuse, token saving or
production admission.


\paragraph{Actual Requests accepted-source archive.}
A separate post-cohort consumer uses the actual Requests cold-v2 D5414
checkpoint. D6028 failed and contributes no accepted seal. This single event
has four required units: accepted source, native behavior, semantic preparation
and complete non-sealing effects. Two fresh processes read exact archive clones
through native verified-byte storage and admission, recheck original source,
patch, objective, environment, context and effect bindings, and restore all
97 files with exact bytes and raw modes. The original 118-file archive and
ledger remain unchanged. This explicit archive load dispatches no new grader;
the historical controller's ordinary read included a grader replay.

The event digest includes the complete pack, required receipt CIDs and source
inventory. One honest standard v3 proof commits its root/count with three padded
leaves. Proving takes 11.978556 seconds and runtime verification 5.255706
milliseconds; direct producer/consumer read-and-restore take 0.419219 and
0.423702 seconds. The complete 14.737743-second driver includes these costs,
cloning, hashing and all controls. An additional 0.278576-second audit includes
one 7.364014-millisecond verification; previously metered key setup and cohort
execution are separate. The proof is 1,484 bytes, while its supporting archive
occupies 12,514,534 apparent bytes. This consumer retains direct evidence checks;
the proof adds overhead and establishes no amortized or token saving.

Eight frozen mutations reject. Missing/corrupt behavior receipts, omitted units,
changed parent and changed source binding fail archive admission. Changed event,
full root and count fail exact outer-statement binding before pairing. The
changed-parent checkpoint is looked up under delta kind and rejected before
cycle traversal; the initial auditor expected a later kind/cycle error. Its
failure is retained, and a separate corrected auditor checks that exact earlier
lookup rejection without rerunning the experiment. The audit passes 1,462
checks and archives 514 source files. It shares the cryptographic backend.
This is actual repository archive consumption, not inline proof use in the
original cohort, a proof of arbitrary test execution or production admission.

\section{Signed native procedure execution}
\label{sec:signed-native-procedure}
The surviving saved bounded-sequence candidate now passes native seven-layer
verification, certificate issuance, certificate admission and TEST interpreter
execution. Its exact procedure identity is retained. A local TEST-only HMAC
signer and trusted immutable-input custody provide this development admission;
the selection receipt grants no native registry promotion or production
authority. The arithmetic candidate is not relabelled as a repository-repair
procedure.

The prospectively frozen corpus contains 32 test, 24 adversarial, 48 held-out
and 32 shadow inputs, disjoint from the original exposed inputs and one another.
All 136 native executions match independent decisions: 13 true and 123 false.
False is a computed answer, not an execution failure. Six handlers per input
produce 816 dispatches, 408 distinct current check receipts and 136 distinct
decision receipts. The audit reconstructs exact invocation CIDs and restores
all native trace, outcome and receipt objects. These newly authored partitions
were prepared after development; they are not population-generalization evidence.

Eight distinct proof, test, adversarial, held-out, shadow, specification,
source-episode and counterexample artifacts precede signing. Seven bounded Z3
contracts are connected to 4,100 concrete catalog executions; this is a bounded
logical result with a measured source bridge, not a theorem for arbitrary Python.
The original IR has an empty required-proof-contract list. An added adapter
enforces the named proof payload; native contract-specific proof coverage is
not inferred. Independent artifact admission recomputes concrete decisions,
and runtime validation repeats catalog operations. These costs are charged;
this experiment does not demonstrate receipt-only computation avoidance.

Thirty pre-issuer evidence controls and thirteen native runtime controls pass,
including signature, expiry, catalog, observation, query identity, cross-invocation
and domain mutations. LIVE dispatch rejects. Exact invocation checkpoint reuse
avoids redispatch in the same interpreter process; cross-process checkpoint
restoration is untested. Since native canonical values reject floats, a frozen
canonical-JSON transport preserves input bytes behind a checked typed query CID.
The evidence corpus retains 1,192 float-bearing adversaries.

Preparation and freeze take 1.402121 seconds. Three fresh bounded workers take
1.521004 seconds for evidence production, 6.902933 seconds for admission and
issuance, and 8.819003 seconds for execution and controls: 17.242940 seconds
total. The 6.771036 seconds of native invocation calls and 5.127014 seconds of
evidence-negative work are nested. Independent audit adds 2.929698 seconds.
Evidence payloads occupy 2,373,459 bytes and native runtime objects 2,704,141
bytes, excluding snapshots and logs. Earlier float, immutable-mapping and SMT
serialization failures retain their original profiles, limits and costs.
Profile copying before the driver was not timed. The freeze pins 10,736 paths;
156 observed loaded files include 112 standard-library/other paths outside the
native source freeze. Local custody does not supply OS isolation against hostile
Python. No provider call, model-token saving, repository transfer or production
authority is attributed to this integration.

% END retained input: appendix/incremental_qualification_details.tex

\clearpage
\section{Family-level display}
Figure~\ref{fig:family-useful} displays the same family counts as Table~\ref{tab:final32}; it is not an additional experiment.
\begin{figure}[htbp]
\centering
\includegraphics[width=\linewidth]{layout/family_useful.pdf}
\caption{Useful completions by family and arm in the same 32-cell comparison. Each arm has two nested repetitions per family; the figure adds no trials.}
\label{fig:family-useful}
\end{figure}
\clearpage
\section{Historical boundary evidence}
\label{sec:historical-boundaries}
Table~\ref{tab:boundary-history} retains the historical qualification scope separately from the final repair comparison. Identifiers of the form NS-NNN name internal qualification records, not repository families or independent repair trials. The anonymous boundary component retains the detailed evidence index and limitations.
\begin{table}[htbp]
\centering
\caption{Historical evidence boundaries. Local controls, unavailable measurements, and the retained false-reuse case are not additional final repair outcomes.}
\label{tab:boundary-history}

% BEGIN retained input: layout/table18.tex
% NS020 preparation: retained component scope, not final32 result evidence.
\begin{tabular}{p{0.18\linewidth}p{0.24\linewidth}p{0.23\linewidth}p{0.17\linewidth}}
\hline
Boundary & Safe rejection & Valid progress & Evidence \\
\hline
Provider gate & Missing/mismatched authority and untrusted close rejected in fixtures. & Deterministic repair and injected residual fixture; no production routing claim. & NS-008 \\
Loss-aware translation & Modal erasure and unvalidated solver lift refused. & Exact/conservative translation only; no kernel source proof. & NS-009 \\
Native theorem/circuit & Untested: no admitted native proof profile. & Unavailable: no genuine proof or measured prove/verify run. & NS-014 scope closure \\
Fixture/\allowbreak call/\allowbreak teardown reuse & Prior false reuse 1/26 retained; corrected route requires full cold. & Full public cold baseline only; no admitted positive reuse or speedup. & NS-011; corrected NS-027 \\
Publication after restart & Empty/stale/failed publication refused in local controls. & WAL/CAS recovery and valid continuation; explicit hermetic shims. & NS-012/013 \\
World/procedure consumption & Untested/out of scope. & Untested: no retained paired pre/post consumption. & NS-015 scope closure \\
\hline
\end{tabular}
% Each row's exact case IDs, snapshots and limitations are in boundary_witnesses.json.
% No row substitutes for final repair efficacy or establishes distributed exactly-once effects.

% END retained input: layout/table18.tex

\end{table}
\section{Withdrawn and unmeasured comparisons}
\begin{table}[htbp]
\centering
\caption{Withdrawn and unmeasured comparisons. These entries are scope dispositions, not zero-effect measurements.}
\label{tab:withdrawn-comparisons}

% BEGIN retained input: generated/ablations.tex
\begin{tabular}{p{0.30\linewidth}p{0.64\linewidth}}
\hline
Endpoint & Scope \\
\hline
C/D routing/governance comparative benefits & Withdrawn or unmeasured; no final comparison or effect estimate. \\
proof/test reuse or local\_warm effects & Withdrawn or unmeasured; no final comparison or effect estimate. \\
certificate/publication comparative benefits & Withdrawn or unmeasured; no final comparison or effect estimate. \\
adversarial scorer-integrity qualification & Withdrawn or unmeasured; no final comparison or effect estimate. \\
independent human semantic annotation & Withdrawn or unmeasured; no final comparison or effect estimate. \\
Non-A/B planned cells (128) & Withdrawn; no measured ablation rows. \\
A/B warm planned cells (32) & Withdrawn; no measured ablation rows. \\
\hline
\end{tabular}
% A/B is the retained combined context contrast, not isolated component attribution.

% END retained input: generated/ablations.tex

\end{table}
\clearpage

% BEGIN retained input: appendix/llm_usage_disclosure.tex
% Proposed NS024 appendix insertion; reviewed integration and compilation are separate.
\section{LLM use, public reproduction, and responsible use}
\label{sec:ns024-disclosures}

\paragraph{Scientific model use.}
The historical cold-repair comparison uses Grok 4.6 to propose source edits from
the fixed A/B context requests (Section~\ref{sec:design}). Each of the 32 cells
consumes one proposal POST with a maximum of 4,096 requested output tokens and
a structured edit response. No scientific fallback, retry, served random seed,
or reasoning-effort parameter is used. The model's weights and exact served
revision are unavailable. Candidate inspection by AI is a procedural control;
it is not independent human assessment or a substitute for executed checks.

The new routing and context development pilots each use six Grok 4.6 requests
under a separately frozen low-effort profile, with at most 2,048 requested
output tokens and 240 seconds per request. These pilots do not share the
historical experiment's reasoning-effort setting or task population. All twelve
responses retain actual model identity and token-usage fields; no scientific
retry, model fallback or auxiliary model call is included in these development
workflows. Deterministic analysis, solver checks and executed oracles remain
distinct from model proposals.

\paragraph{Research and manuscript assistance.}
AI assistance also contributed to source recovery and drafting, implementation
and debugging, experiment preparation and candidate inspection, and analysis
and artifact preparation. The original authoring supervisors were configured to use
Grok 4.6, with Codex \texttt{gpt-5.6-terra} at high reasoning effort as a fallback
only following independently verified primary-quota exhaustion. This describes
the configured authoring policy, not a claim that every task used a fallback or
that these models generated the scientific comparison under a mixed route.
The configured policy does not identify the model behind every separate
interactive assistance session. AI-assisted checking supplies no measured
human semantic fidelity, expert agreement, or human effort time, and does not
discharge the conditional arguments in Appendix~\ref{sec:formal-arguments-ns023}.
The present incremental evaluation code, reports and manuscript revision also
received interactive Codex assistance. That authoring effort is not included in
the measured deployment-task token totals; no full research-effort saving is
claimed.

\paragraph{Anonymous numerical reproduction.}
The historical supplement keeps the 32-cell final comparison, the separate
24-cell developmental pilot, and historical boundary controls in distinct
components. Its top-level \texttt{README.md} specifies Python 3.12 and the
command \texttt{python3 -B reproduce.py --root ROOT --output OUTPUT}, where
\texttt{ROOT} is a fresh extraction and \texttt{OUTPUT} is a fresh directory
outside it. The program checks the manifest-bound files and reproduces their
retained numerical summaries; it does not generate new proposals, execute
candidates or hidden tests, rerun historical qualifications, or authenticate
original signed records. Hidden tests, reference patches, credentials, keys,
and raw private operational logs are excluded. Original and derivative hashes
have distinct roles: original signatures do not authenticate modified anonymous
derivative bytes. Exact executed source and labeled reference derivatives remain
distinct. Upstream retrieval metadata, revisions, and retained license and
copyright notices accompany the released assets. Stable hashes and timestamps
may permit correlation, so these release controls do not guarantee anonymity.
New development artifacts are retained separately with source and request
hashes, terminal outcomes and replay commands. They have not been incorporated
into that historical anonymous supplement; its reproduction command does not
reproduce the new evaluations.

\paragraph{Potential impacts and limits.}
Explicit evidence boundaries may help users identify stale checks and
unsupported acceptance claims, but this experiment establishes no general
reliability or efficiency benefit. Incorrect repairs, incomplete tests, or
mistaking signed provenance for correctness could lead to unsafe deployment;
automated coding can also be misused to introduce harmful changes. The stated
scope, isolated checks, restricted artifact projection, and visible failures
reduce particular risks without establishing comprehensive adversarial
resistance. No model weights or human-subject dataset are released, and no
human semantic annotations, expert-agreement study, or human-time measurements
were collected for the reported comparison. 

% END retained input: appendix/llm_usage_disclosure.tex

\clearpage
\label{paper:checklist-start}

% BEGIN retained input: checklist.tex
\section*{NeurIPS Paper Checklist}




\begin{enumerate}

\item {\bf Claims}
    \item[] Question: Do the main claims made in the abstract and introduction accurately reflect the paper's contributions and scope?
    \item[] Answer: \answerYes{}
    \item[] Justification: The abstract and Sections~\ref{sec:introduction}, \ref{sec:results}, and \ref{sec:limitations} restrict the contribution to explicit evidence boundaries, conditional arguments, and the fixed eight-family A/B comparison (A 5/16, B 4/16). They do not claim semantic correctness, a general performance advantage, or benefits from withdrawn routing, reuse, or publication comparisons.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the abstract and introduction do not include the claims made in the paper.
        \item The abstract and/or introduction should clearly state the claims made, including the contributions made in the paper and important assumptions and limitations. A \answerNo{} or \answerNA{} answer to this question will not be perceived well by the reviewers. 
        \item The claims made should match theoretical and experimental results, and reflect how much the results can be expected to generalize to other settings. 
        \item It is fine to include aspirational goals as motivation as long as it is clear that these goals are not attained by the paper. 
    \end{itemize}

\item {\bf Limitations}
    \item[] Question: Does the paper discuss the limitations of the work performed by the authors?
    \item[] Answer: \answerYes{}
    \item[] Justification: Section~\ref{sec:limitations} states the convenience-sample scope, combined-context intervention, finite-test and trusted-premise limitations, and missing human semantic fidelity, expert agreement, and human-time measurements. Sections~\ref{sec:analysis-method} and \ref{sec:results} retain failures, timing deviations, overlapping clocks, incomplete validation, and unsettled charges.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the paper has no limitation while the answer \answerNo{} means that the paper has limitations, but those are not discussed in the paper. 
        \item The authors are encouraged to create a separate ``Limitations'' section in their paper.
        \item The paper should point out any strong assumptions and how robust the results are to violations of these assumptions (e.g., independence assumptions, noiseless settings, model well-specification, asymptotic approximations only holding locally). The authors should reflect on how these assumptions might be violated in practice and what the implications would be.
        \item The authors should reflect on the scope of the claims made, e.g., if the approach was only tested on a few datasets or with a few runs. In general, empirical results often depend on implicit assumptions, which should be articulated.
        \item The authors should reflect on the factors that influence the performance of the approach. For example, a facial recognition algorithm may perform poorly when image resolution is low or images are taken in low lighting. Or a speech-to-text system might not be used reliably to provide closed captions for online lectures because it fails to handle technical jargon.
        \item The authors should discuss the computational efficiency of the proposed algorithms and how they scale with dataset size.
        \item If applicable, the authors should discuss possible limitations of their approach to address problems of privacy and fairness.
        \item While the authors might fear that complete honesty about limitations might be used by reviewers as grounds for rejection, a worse outcome might be that reviewers discover limitations that aren't acknowledged in the paper. The authors should use their best judgment and recognize that individual actions in favor of transparency play an important role in developing norms that preserve the integrity of the community. Reviewers will be specifically instructed to not penalize honesty concerning limitations.
    \end{itemize}

\item {\bf Theory assumptions and proofs}
    \item[] Question: For each theoretical result, does the paper provide the full set of assumptions and a complete (and correct) proof?
    \item[] Answer: \answerNo{}
    \item[] Justification: Section~\ref{sec:evidence-method} and Appendix~\ref{sec:formal-arguments-ns023} give explicit scopes, premises, and conditional argument sketches, but do not claim a complete formal proof of the intended implementation. The arguments are unmachine-checked, and dependency completeness, checker adequacy, and exclusive checked publication remain assumptions.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the paper does not include theoretical results. 
        \item All the theorems, formulas, and proofs in the paper should be numbered and cross-referenced.
        \item All assumptions should be clearly stated or referenced in the statement of any theorems.
        \item The proofs can either appear in the main paper or the supplemental material, but if they appear in the supplemental material, the authors are encouraged to provide a short proof sketch to provide intuition. 
        \item Inversely, any informal proof provided in the core of the paper should be complemented by formal proofs provided in appendix or supplemental material.
        \item Theorems and Lemmas that the proof relies upon should be properly referenced. 
    \end{itemize}

    \item {\bf Experimental result reproducibility}
    \item[] Question: Does the paper fully disclose all the information needed to reproduce the main experimental results of the paper to the extent that it affects the main claims and/or conclusions of the paper (regardless of whether the code and data are provided or not)?
    \item[] Answer: \answerNo{}
    \item[] Justification: Sections~\ref{sec:design} and \ref{sec:analysis-method} disclose the retained protocol and frozen reduction, and Section~\ref{sec:ns024-disclosures} describes the anonymous numerical replay. Independent regeneration and confidential-oracle rescoring are not supplied: exact served model revisions, private original custody, and hidden tests are unavailable through that replay.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the paper does not include experiments.
        \item If the paper includes experiments, a \answerNo{} answer to this question will not be perceived well by the reviewers: Making the paper reproducible is important, regardless of whether the code and data are provided or not.
        \item If the contribution is a dataset and\slash or model, the authors should describe the steps taken to make their results reproducible or verifiable. 
        \item Depending on the contribution, reproducibility can be accomplished in various ways. For example, if the contribution is a novel architecture, describing the architecture fully might suffice, or if the contribution is a specific model and empirical evaluation, it may be necessary to either make it possible for others to replicate the model with the same dataset, or provide access to the model. In general. releasing code and data is often one good way to accomplish this, but reproducibility can also be provided via detailed instructions for how to replicate the results, access to a hosted model (e.g., in the case of a large language model), releasing of a model checkpoint, or other means that are appropriate to the research performed.
        \item While NeurIPS does not require releasing code, the conference does require all submissions to provide some reasonable avenue for reproducibility, which may depend on the nature of the contribution. For example
        \begin{enumerate}
            \item If the contribution is primarily a new algorithm, the paper should make it clear how to reproduce that algorithm.
            \item If the contribution is primarily a new model architecture, the paper should describe the architecture clearly and fully.
            \item If the contribution is a new model (e.g., a large language model), then there should either be a way to access this model for reproducing the results or a way to reproduce the model (e.g., with an open-source dataset or instructions for how to construct the dataset).
            \item We recognize that reproducibility may be tricky in some cases, in which case authors are welcome to describe the particular way they provide for reproducibility. In the case of closed-source models, it may be that access to the model is limited in some way (e.g., to registered users), but it should be possible for other researchers to have some path to reproducing or verifying the results.
        \end{enumerate}
    \end{itemize}


\item {\bf Open access to data and code}
    \item[] Question: Does the paper provide open access to the data and code, with sufficient instructions to faithfully reproduce the main experimental results, as described in supplemental material?
    \item[] Answer: \answerNo{}
    \item[] Justification: The anonymous supplement provides manifest-bound inputs, selected source versions, retained license/retrieval metadata, and Python 3.12 instructions that reproduce the reported scalar summaries. It does not provide model weights, hidden-oracle access, or public authentication of original private signatures; Section~\ref{sec:ns024-disclosures} states these limits.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that paper does not include experiments requiring code.
        \item Please see the NeurIPS code and data submission guidelines (\url{https://neurips.cc/public/guides/CodeSubmissionPolicy}) for more details.
        \item While we encourage the release of code and data, we understand that this might not be possible, so \answerNo{} is an acceptable answer. Papers cannot be rejected simply for not including code, unless this is central to the contribution (e.g., for a new open-source benchmark).
        \item The instructions should contain the exact command and environment needed to run to reproduce the results. See the NeurIPS code and data submission guidelines (\url{https://neurips.cc/public/guides/CodeSubmissionPolicy}) for more details.
        \item The authors should provide instructions on data access and preparation, including how to access the raw data, preprocessed data, intermediate data, and generated data, etc.
        \item The authors should provide scripts to reproduce all experimental results for the new proposed method and baselines. If only a subset of experiments are reproducible, they should state which ones are omitted from the script and why.
        \item At submission time, to preserve anonymity, the authors should release anonymized versions (if applicable).
        \item Providing as much information as possible in supplemental material (appended to the paper) is recommended, but including URLs to data and code is permitted.
    \end{itemize}


\item {\bf Experimental setting/details}
    \item[] Question: Does the paper specify all the training and test details (e.g., data splits, hyperparameters, how they were chosen, type of optimizer) necessary to understand the results?
    \item[] Answer: \answerYes{}
    \item[] Justification: Section~\ref{sec:design} specifies the historical cold comparison, and Section~\ref{sec:incremental-evaluation} distinguishes the new constructed development profiles, calls, oracles, cost scopes and limitations. Frozen per-study artifacts retain the exact requests, execution settings, cases and source bindings; the development observations are not pooled with historical results.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the paper does not include experiments.
        \item The experimental setting should be presented in the core of the paper to a level of detail that is necessary to appreciate the results and make sense of them.
        \item The full details can be provided either with the code, in appendix, or as supplemental material.
    \end{itemize}

\item {\bf Experiment statistical significance}
    \item[] Question: Does the paper report error bars suitably and correctly defined or other appropriate information about the statistical significance of the experiments?
    \item[] Answer: \answerNo{}
    \item[] Justification: The historical study retains its explicitly descriptive whole-family bootstrap interval, but the new small constructed development pilots do not provide population-level uncertainty estimates or statistical significance claims. Their observed savings are limited to the fixed cases; held-out repeated comparisons remain necessary.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the paper does not include experiments.
        \item The authors should answer \answerYes{} if the results are accompanied by error bars, confidence intervals, or statistical significance tests, at least for the experiments that support the main claims of the paper.
        \item The factors of variability that the error bars are capturing should be clearly stated (for example, train/test split, initialization, random drawing of some parameter, or overall run with given experimental conditions).
        \item The method for calculating the error bars should be explained (closed form formula, call to a library function, bootstrap, etc.)
        \item The assumptions made should be given (e.g., Normally distributed errors).
        \item It should be clear whether the error bar is the standard deviation or the standard error of the mean.
        \item It is OK to report 1-sigma error bars, but one should state it. The authors should preferably report a 2-sigma error bar than state that they have a 96\% CI, if the hypothesis of Normality of errors is not verified.
        \item For asymmetric distributions, the authors should be careful not to show in tables or figures symmetric error bars that would yield results that are out of range (e.g., negative error rates).
        \item If error bars are reported in tables or plots, the authors should explain in the text how they were calculated and reference the corresponding figures or tables in the text.
    \end{itemize}

\item {\bf Experiments compute resources}
    \item[] Question: For each experiment, does the paper provide sufficient information on the computer resources (type of compute workers, memory, time of execution) needed to reproduce the experiments?
    \item[] Answer: \answerNo{}
    \item[] Justification: Sections~\ref{sec:design}, \ref{sec:analysis-method}, and \ref{sec:results} report per-phase CPU, memory, process and time limits, available measured clocks, prior work, and missingness. Provider-side hardware and total compute/effort or settled charges are unavailable, and overlapping clocks, reservation lifetimes, and configured caps are not presented as measured total compute.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the paper does not include experiments.
        \item The paper should indicate the type of compute workers CPU or GPU, internal cluster, or cloud provider, including relevant memory and storage.
        \item The paper should provide the amount of compute required for each of the individual experimental runs as well as estimate the total compute. 
        \item The paper should disclose whether the full research project required more compute than the experiments reported in the paper (e.g., preliminary or failed experiments that didn't make it into the paper). 
    \end{itemize}
    
\item {\bf Code of ethics}
    \item[] Question: Does the research conducted in the paper conform, in every respect, with the NeurIPS Code of Ethics \url{https://neurips.cc/public/EthicsGuidelines}?
    \item[] Answer: \answerNA{}
    \item[] Justification: Author review of and conformance with the NeurIPS Code of Ethics has not been attested in the preparation record. This answer records unavailable author confirmation, not a claim that the work violates the code; the author must review it before submission.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the authors have not reviewed the NeurIPS Code of Ethics.
        \item If the authors answer \answerNo, they should explain the special circumstances that require a deviation from the Code of Ethics.
        \item The authors should make sure to preserve anonymity (e.g., if there is a special consideration due to laws or regulations in their jurisdiction).
    \end{itemize}


\item {\bf Broader impacts}
    \item[] Question: Does the paper discuss both potential positive societal impacts and negative societal impacts of the work performed?
    \item[] Answer: \answerYes{}
    \item[] Justification: Section~\ref{sec:ns024-disclosures} discusses potential benefits of making evidence boundaries explicit, and harms from incorrect repairs, misplaced trust in signed provenance, unsafe deployment, malicious edits, and residual privacy correlation. It states the limited scope of the proposed mitigations and makes no measured societal-benefit or comprehensive security claim.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that there is no societal impact of the work performed.
        \item If the authors answer \answerNA{} or \answerNo, they should explain why their work has no societal impact or why the paper does not address societal impact.
        \item Examples of negative societal impacts include potential malicious or unintended uses (e.g., disinformation, generating fake profiles, surveillance), fairness considerations (e.g., deployment of technologies that could make decisions that unfairly impact specific groups), privacy considerations, and security considerations.
        \item The conference expects that many papers will be foundational research and not tied to particular applications, let alone deployments. However, if there is a direct path to any negative applications, the authors should point it out. For example, it is legitimate to point out that an improvement in the quality of generative models could be used to generate Deepfakes for disinformation. On the other hand, it is not needed to point out that a generic algorithm for optimizing neural networks could enable people to train models that generate Deepfakes faster.
        \item The authors should consider possible harms that could arise when the technology is being used as intended and functioning correctly, harms that could arise when the technology is being used as intended but gives incorrect results, and harms following from (intentional or unintentional) misuse of the technology.
        \item If there are negative societal impacts, the authors could also discuss possible mitigation strategies (e.g., gated release of models, providing defenses in addition to attacks, mechanisms for monitoring misuse, mechanisms to monitor how a system learns from feedback over time, improving the efficiency and accessibility of ML).
    \end{itemize}
    
\item {\bf Safeguards}
    \item[] Question: Does the paper describe safeguards that have been put in place for responsible release of data or models that have a high risk for misuse (e.g., pre-trained language models, image generators, or scraped datasets)?
    \item[] Answer: \answerNA{}
    \item[] Justification: The release contains no model weights or human-subject dataset of the high-risk types described by this question. Section~\ref{sec:ns024-disclosures} and the supplement documentation nevertheless describe excluded private logs, credentials, keys, hidden tests and reference patches, and the residual limits of anonymization.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the paper poses no such risks.
        \item Released models that have a high risk for misuse or dual-use should be released with necessary safeguards to allow for controlled use of the model, for example by requiring that users adhere to usage guidelines or restrictions to access the model or implementing safety filters. 
        \item Datasets that have been scraped from the Internet could pose safety risks. The authors should describe how they avoided releasing unsafe images.
        \item We recognize that providing effective safeguards is challenging, and many papers do not require this, but we encourage authors to take this into account and make a best faith effort.
    \end{itemize}

\item {\bf Licenses for existing assets}
    \item[] Question: Are the creators or original owners of assets (e.g., code, data, models), used in the paper, properly credited and are the license and terms of use explicitly mentioned and properly respected?
    \item[] Answer: \answerNo{}
    \item[] Justification: The supplement retains upstream revisions, retrieval metadata, license and copyright notices, and distinguishes exact executed source from reference derivatives. A complete confirmation of all provider and asset terms of use is unavailable in this preparation, so retained notices alone are not asserted to establish full compliance.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the paper does not use existing assets.
        \item The authors should cite the original paper that produced the code package or dataset.
        \item The authors should state which version of the asset is used and, if possible, include a URL.
        \item The name of the license (e.g., CC-BY 4.0) should be included for each asset.
        \item For scraped data from a particular source (e.g., website), the copyright and terms of service of that source should be provided.
        \item If assets are released, the license, copyright information, and terms of use in the package should be provided. For popular datasets, \url{paperswithcode.com/datasets} has curated licenses for some datasets. Their licensing guide can help determine the license of a dataset.
        \item For existing datasets that are re-packaged, both the original license and the license of the derived asset (if it has changed) should be provided.
        \item If this information is not available online, the authors are encouraged to reach out to the asset's creators.
    \end{itemize}

\item {\bf New assets}
    \item[] Question: Are new assets introduced in the paper well documented and is the documentation provided alongside the assets?
    \item[] Answer: \answerYes{}
    \item[] Justification: The supplement documents its final-comparison, developmental-pilot, and historical-boundary components with separate manifests, numerical reproduction commands, source and derivative identities, and explicit data-access and inference limitations. Section~\ref{sec:ns024-disclosures} explains this scope, including the distinction between integrity hashes and authentication of private originals.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the paper does not release new assets.
        \item Researchers should communicate the details of the dataset\slash code\slash model as part of their submissions via structured templates. This includes details about training, license, limitations, etc. 
        \item The paper should discuss whether and how consent was obtained from people whose asset is used.
        \item At submission time, remember to anonymize your assets (if applicable). You can either create an anonymized URL or include an anonymized zip file.
    \end{itemize}

\item {\bf Crowdsourcing and research with human subjects}
    \item[] Question: For crowdsourcing experiments and research with human subjects, does the paper include the full text of instructions given to participants and screenshots, if applicable, as well as details about compensation (if any)? 
    \item[] Answer: \answerNA{}
    \item[] Justification: The reported source-code comparison includes no crowdsourcing or human-subject annotation study. Section~\ref{sec:limitations} states that human semantic fidelity, expert agreement and human time were not measured; AI candidate inspection is not relabeled as human research.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the paper does not involve crowdsourcing nor research with human subjects.
        \item Including this information in the supplemental material is fine, but if the main contribution of the paper involves human subjects, then as much detail as possible should be included in the main paper. 
        \item According to the NeurIPS Code of Ethics, workers involved in data collection, curation, or other labor should be paid at least the minimum wage in the country of the data collector. 
    \end{itemize}

\item {\bf Institutional review board (IRB) approvals or equivalent for research with human subjects}
    \item[] Question: Does the paper describe potential risks incurred by study participants, whether such risks were disclosed to the subjects, and whether Institutional Review Board (IRB) approvals (or an equivalent approval/review based on the requirements of your country or institution) were obtained?
    \item[] Answer: \answerNA{}
    \item[] Justification: No human-subject experiment or crowdsourcing is reported, so no participant-risk, compensation or IRB-approval result is claimed. The absence of human semantic annotations and expert-agreement measurements is explicit in Section~\ref{sec:limitations}; this answer does not invent institutional approval.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the paper does not involve crowdsourcing nor research with human subjects.
        \item Depending on the country in which research is conducted, IRB approval (or equivalent) may be required for any human subjects research. If you obtained IRB approval, you should clearly state this in the paper. 
        \item We recognize that the procedures for this may vary significantly between institutions and locations, and we expect authors to adhere to the NeurIPS Code of Ethics and the guidelines for their institution. 
        \item For initial submissions, do not include any information that would break anonymity (if applicable), such as the institution conducting the review.
    \end{itemize}

\item {\bf Declaration of LLM usage}
    \item[] Question: Does the paper describe the usage of LLMs if it is an important, original, or non-standard component of the core methods in this research? Note that if the LLM is used only for writing, editing, or formatting purposes and does \emph{not} impact the core methodology, scientific rigor, or originality of the research, declaration is not required.
    %this research? 
    \item[] Answer: \answerYes{}
    \item[] Justification: Section~\ref{sec:design} and Section~\ref{sec:ns024-disclosures} identify methodology-essential Grok 4.6 scientific proposals under one-POST/no-fallback rules and describe AI assistance in implementation, inspection, analysis and writing. The configured authoring Grok-to-Codex \texttt{gpt-5.6-terra} high quota-only fallback is distinguished from observed scientific use, without claiming that every fallback or interactive session used that model.
    \item[] Guidelines:
    \begin{itemize}
        \item The answer \answerNA{} means that the core method development in this research does not involve LLMs as any important, original, or non-standard components.
        \item Please refer to our LLM policy in the NeurIPS handbook for what should or should not be described.
    \end{itemize}

\end{enumerate}

% END retained input: checklist.tex

\end{document}

````
