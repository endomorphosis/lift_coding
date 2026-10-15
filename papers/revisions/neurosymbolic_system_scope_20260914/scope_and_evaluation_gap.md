# Restoring the whole-system neurosymbolic supervision question

Author-facing assessment, 2026-09-14. This document compares the supplied original PDF, the final editable manuscript, and the local protocol/audit records. It does not report new experiments or certify current runtime readiness. The final paper and its historical results are preserved.

## Finding

The final paper answers a materially narrower question than the original draft. The original thesis was that persistent obligations and semantic state can displace repeated neural reasoning and validation while preserving a declared acceptance standard. The final empirical question is whether adding native semantic context to matched raw context changes one-proposal cold repair. That is a useful component experiment, but it does not answer the original system-level efficiency question.

Narrowing unsupported claims was appropriate for an evidence-limited manuscript. Treating that narrowed manuscript as completion of the original research objective was not sufficient. The missing evaluations should remain research obligations even when their claims are removed from a submission.

## Evidence inspected

- Original: `papers/vericodegen_neurosymbolic_supervision_workshop_draft.pdf`, especially abstract, sections 1, 4, 8, and 9.3; layout-preserving extraction inspected locally.
- Final: `papers/final/neurosymbolic_supervision/editable/manuscript/fragments/{abstract,introduction,design,evidence_method,analysis_method,results}.tex`, `generated/ablations.tex`, and `layout/table18.tex`.
- Earlier intent: `papers/completion/neurosymbolic_supervision/protocol/{scope,preregistered_protocol}.md` and `audit/{preliminary_evidence,claim_evidence_matrix}.json`.
- Earlier review: `papers/completion/neurosymbolic_supervision/review.md`.

The original PDF explicitly says context reduction is one consequence, not the sole purpose (section 1), and requires actual provider-boundary measurements, warm/cold comparisons, amortization, useful progress, and false-admission results (section 8). These were already recognized evaluation needs.

The first local preregistration planned 384 final units: 16 families × six conditions × two repetitions × two cache profiles. The final manuscript describes a later 192-cell plan and retention of 32 cells: eight families × A/B × two repetitions, cold only. It reports 160 withdrawn factor cells and eight additional unrecruited families. These are different protocol stages; 384 and 192 must not be presented as competing counts of the same frozen experiment. This assessment has not reconstructed every intervening amendment or its authorization history.

## Claim-to-evaluation gaps

| Research question | Evidence retained in the final paper | Evidence still needed for the original claim |
|---|---|---|
| Can semantic state replace repeated source/context reconstruction? | A receives selected raw context; B receives the same raw selection plus semantic context. | A separate context-substitution treatment with preserved required information, source expansion on demand, actual tokens including expansion/fallback, and independent quality assessment. Keep the existing additive treatment as a distinct control. |
| Does symbolic reasoning replace model work? | Constructed provider-gate controls; every final cell has one proposal POST. | Genuine caller-level deterministic analysis, checked reasoning or bounded synthesis closing tasks without model calls, alongside successful authorized residual dispatch; common hidden validation and all planning/formalization/retry model calls counted. |
| Does persistent state reduce repeated planning and recovery? | One-proposal cold repair; local publication/restart controls. | Multi-step task sequences with repository changes, replanning and interrupted/restarted runs; compare stateless and persistent variants with equal available information and acceptance criteria. |
| Does verification reuse save work while preserving outcomes? | Historical false reuse 1/26; corrected route requires full cold; no admitted positive reuse or speedup. | Valid reuse on unchanged covered obligations, dependency/fixture/configuration/environment mutations, preserved lifecycle effects, and a separate cold oracle checking each retained reuse claim. Measure execution cost directly. |
| Do procedures or semantic-world memory avoid repeated reasoning? | Untested/out of scope in the final boundary table. | A named implemented profile, held-out task sequences, actual consumption affecting the next action, comparison with simple retrieval/templates, invalidation and fallback, and independent downstream correctness. Learned components require their own frozen artifact and holdout. |
| Does the integrated system save tokens at adequate quality? | A 5/16 useful repairs; B 4/16. Usage available for 16/32 cells; settlement unavailable for all 32. | Matched integrated and baseline runs with complete workflow usage, task-quality endpoints, failures retained, startup/warm costs, and family-level uncertainty. No whole-system savings percentage is established today. |

Boundary qualification is valuable, but rejection fixtures and shimmed continuation are not comparative whole-system efficacy. Native proof performance likewise remains unmeasured; it needs a real admitted backend/profile if retained as a benefit claim.

## Token and cost accounting

Separate three hypotheses: fewer tokens per request, fewer model invocations, and less repeated reasoning across a task sequence. A shorter context does not establish the latter two. Test/proof reuse primarily saves validation compute unless it also demonstrably avoids model work.

For arm a and a prespecified workload of N tasks, record:

`T_a(N) = T_setup,a + sum(all provider-reported token usage attributable to tasks 1..N)`.

The sum includes objective compilation, planning, formalization, retrieval/context expansion involving models, proposal generation, critic/review calls, failed attempts, retries, recovery, and model-assisted procedure acquisition. Preserve input, output, cached input, and exposed reasoning-token fields separately. Respect each provider's inclusion semantics: cached input may be a subset of input and reasoning tokens may already be included in output. Do not double-count them or equate cached tokens with avoided tokens. Unknown remote usage remains unknown; local request tokenization is separately labeled and cannot recover unknown output usage.

For a matched fixed workload with complete comparable telemetry, token reduction is `1 - T_system(N) / T_baseline(N)`. Report total tokens over all scheduled tasks and each arm's tokens per independently successful task; if there are no successes, the latter is undefined. Never drop failed attempts from expenditure. Paired success-only analyses can be secondary but cannot replace fixed-cohort quality and cost comparisons.

Report quality and token expenditure jointly, preferably success-versus-token-budget curves, with a quality margin and minimum useful-progress threshold chosen before confirmatory runs. Low expenditure from abstaining or failing is not an efficiency win. Cluster uncertainty by independent repository/task lineage and preserve dependencies within sequences and repetitions.

Keep provider charges, host compute, latency, storage, and human effort as separate measured quantities. Include setup and warm priming at prespecified horizons. Under an explicitly constant marginal-token approximation, break-even is the smallest N for which `T_setup,system - T_setup,baseline < N * (t_baseline - t_system)`; if the denominator is nonpositive there is no positive break-even under that model. Prefer measured cumulative curves when costs change with history. A cold oracle run solely for independent experimental audit should be reported as evaluation overhead, separately from the actual arm's deployment work, so mandatory runtime validation is neither hidden nor charged twice.

The preliminary 58.90% estimated context reduction on 40 fixtures has zero model receipts and no production-eligible rows. The preliminary 43.0539% estimated sealer compute reduction has zero measured timing rows. Neither is a measured whole-system token saving.

## Evaluation program to restore the original scope

1. Inventory the currently loadable integrated system and map each original mechanism to a real caller, evidence consumer, and observed action. Distinguish implemented, qualified, exercised, and measured benefit. Use the existing local inventory as a starting point, not a current readiness certificate.
2. Make telemetry complete on development-only end-to-end runs. Demonstrate one independently valid deterministic closure, one valid neural residual, one qualified reuse case, and one valid restart continuation. Resolve the existing reuse limitation before counting reuse as operational success. Record all auxiliary model calls.
3. Retain the historical cold A/B study unchanged as an exploratory additive-context result. Run a distinct context-substitution study to test compression. Do not relabel or pool these treatments.
4. Compare matched baseline, semantic context, semantic plus symbolic routing, and full persistent lifecycle variants. Separate routing and reuse with one-factor removals; include stateless versus persistent memory and procedure controls where those mechanisms are claimed. Freeze exact interventions because a package effect does not identify every component's contribution.
5. Use both independent repair tasks and held-out multi-task repository trajectories: repeated understanding/planning, localized edits, obligation/counterexample repair, dependency changes, validation reuse, and interruption/recovery. Include supported symbolic problems and difficult unknown-frontier cases without choosing tasks for favorable savings. Freeze oracle provenance, permissions, budgets, cache state, and split policy. A broader software-supervision result would still not establish all-domain reasoning performance.
6. Pilot only on development data, fix harness problems, then choose confirmatory population size using observed variance, intended precision, feasibility, and independent-family count. The old 16-family target is a historical plan, not a demonstrated power calculation. Freeze endpoints and stopping rules before new final outcomes. Track unrun required comparisons as incomplete research rather than closing them merely by deleting claims.

This document does not freeze a new run budget, select a provider, or launch an experiment. Those implementation choices require current runtime and telemetry evidence; no numerical benefit is assumed.

## Manuscript direction

Restore the original architecture as the organizing argument: source/intent → semantic state and obligations → checked symbolic routes or neural residual → independent validation and applicable reuse → accepted state → invalidation and replanning. Explain what each stage can avoid recomputing and which observations would establish that benefit.

Organize results around context substitution, avoided neural calls, persistent multi-step work, validation reuse, and integrated quality/cost. Include the existing cold-repair result as one bounded study with its unfavorable/inconclusive outcome intact. Put detailed lease, receipt and transport accounting in the supplement while keeping material failures and missingness visible in the main text.

Until the new experiments exist, the defensible broad paper is an architecture/method paper with partial empirical evidence and explicit hypotheses. It can describe the whole system without claiming all of its benefits were demonstrated. A completed empirical claim about whole-system token savings requires the missing measurements; editorial expansion alone cannot supply them.
