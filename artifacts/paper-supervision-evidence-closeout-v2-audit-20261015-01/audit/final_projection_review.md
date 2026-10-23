# Final projection review

Reviewed only generated assembly/workstream outputs. No original evidence was read, and no experiments, solvers, builds, models or production actions ran. This review does not authenticate originating executions. Historical workstream content receives a self-check because this reviewer authored it; other workstreams and root assembly were reviewed independently.

## Required corrections before sealing this assembly

1. **Null-identity join creates false invocation claims.** The reviewed cross_ir_trace.jsonl marks prompt_to_intent “actually invoked” for both `t1:unbound-slot:10` and `T1-retrieval-candidate`, whose `run_id` fields are null. The former is explicitly an uninvoked slot. Generated standalone Intent training also has null run identity, making null equality a likely join path; regardless of implementation cause, the uninvoked-slot status is inconsistent. Reject null identity matches, preserve standalone training as its own development study, and leave those benchmark stage statuses unavailable unless an explicit same-run receipt establishes invocation. Add a check that no uninvoked slot receives an actually-invoked stage through an automatic join.

2. **Stage naming overstates the observed correspondence.** Seven reviewed CodebaseIR rows use stage `intent_to_source_grounding` with “actually invoked.” Their observations instead establish source indexing/adaptation or Source384 inference. The T1 observation explicitly says indexed preparation and local security-code@1 adaptation; numerical observations say unsupported unchanged predictions. The Intent advisors failed open. Preserve these as `source_to_codebase_preparation` or `source_to_codebase_inference` observations and leave actual Intent→Codebase semantic matching/admission unestablished. An explicit separate `intent_correspondence_status` field can preserve the required architecture without inflating invocation coverage. Failed-open Intent advice is a stage invocation, not a learned intent-frame prediction.

## Counters and units checked

The reviewed assembly has 85 mixed ledger rows:38 invoked benchmark_trial units, one registered uninvoked slot,16 retained Requests event joins,14 case pairs,8 Horn controls,5 timing pairs and3 Horn proof reports. The benchmark subset comprises37 identified invoked trials, one invoked trial without recovered original ID, and one uninvoked slot. These are inventory counts, not a pooled efficacy denominator. The 62 session/call rows contain distinct identity kinds and must not be described as62 proven conversation sessions.

Incomplete reported counters are preserved separately from complete totals:177,371 for the older native security run (completeness unknown),265,932 for the older indexed failure (completeness false), and1,310,764/1,621,661/2,452,634 for Grok X1 (unknown completeness). The revised results table correctly uses “Reported tokens” with a separate native-completeness column. Every results.csv reported-total field agrees with the corresponding normalized run's reported_tokens value in this generated snapshot. No lost reported incomplete counter was found.

Do not reinterpret the token schemas during aggregation: Codex cache/reasoning subsets; historical Requests direct-Grok disjoint reasoning with cache subset; Grok CLI disjoint fresh/cache/cache-write/output and unknown reasoning inclusion. Null per-call usage in historical projections remains unknown. Neither complete native counters nor task reward establish complete auxiliary/pipeline cost.

## Proof, manuscript and reviewer-matrix checks

The proposed addendum retains exact title and G(F)/O/B framing, full cross-IR design, repository adaptation/qualification prerequisite, T1 native-input-supervisor versus true native-harness distinction, earlier fallback, three missing usages, adverse numerical/Grok evidence, unsupported zero-update Source384, separate two Requests cohorts and zero completed trajectories. It also retains two positive matrix reuses among14 cases and the historical1/26 false reuse. These are appropriate scope constraints.

Reviewer matrix5a now explicitly says the T2 wrapper requires three axiom checks and original axiom stdout is unrecovered. Matrix6 distinguishes the narrow guard receipt from the unmachine-checked manuscript acceptance/reuse sketches. This resolves the earlier expected-versus-observed axiom wording concern without asserting new proof execution.

Optional clarity: proposed sentence P23's “missing evidence-algebra/header-contract files” could be read as denying the retained local T2 header-guard theorem commitment. Say “unrecovered general evidence-algebra/runtime-checker correspondence proof chain” and explicitly retain the narrow T2 receipt if revising that sentence. The current surrounding reviewer matrix already provides that distinction; no original result should be changed.

The encoder ledger keeps Source384 zero target training and unsupported outputs separate from T1's local24-epoch code learning and standalone Intent training. The latter is an8D inherited lexical branch,75/75 authored versus0/3 weak-public holdouts, with backend bytes unverified. None qualifies a384D joined domain deployment. LegalIR/UI/UX applicability and action-authority joins remain unavailable. No whole-program proof, generalization claim, complete project token total or account settlement is established.

The uninvoked/null-stage bug and source-versus-intent-stage label are the only required corrections found in this generated-output review. All existing files were left unchanged. Root should apply those corrections, rerun its deterministic integrity checks, and append a resolution note keyed to this reviewed snapshot.

## Reviewed snapshot commitments

```json
{
  "sha256": {
    "runs.jsonl": "334edbfa6733924876d07e5cb759faa88b70aaeaf2ee699241f24874274cd029",
    "results.csv": "93126480c68accf70e059d9fcab659efcc03cfdf6d66acc42f17f0f10b3760d8",
    "results.md": "4dcbbd9dc6f1d80646ec638c2c986b92ace67873b297baf816803eda2d92ffac",
    "sessions.jsonl": "a838a6dbc602b999723dcaf6332fb7a1189b441bf72890eee8f49dd45aaf73c1",
    "cross_ir_trace.jsonl": "2b6cd10cc151c90eb028eac9264a937e41d534d3f677326e009a067da94149bd",
    "encoder_deployment_ledger.jsonl": "aa063dbc4fb4c8fd92a580a33dda5df03d2c841064444a7ab1d387b13260d112",
    "proposed_manuscript/evidence_addendum.md": "e5549329d04f8a5b0d579eef95e3d5a17d980ae9390b33868d9fe63a23221db2",
    "reviewer_matrix.md": "93f4c58926e190dd5b8e84d8117e4e0ed3b1cfcbf889af4c7ebe5eb9faaf31d9"
  },
  "csv_reported_total_checks": 39,
  "csv_total_mismatches": [],
  "reviewed_trace_rows": 195,
  "reviewed_trace_status_counts": {
    "unavailable/unsupported": 178,
    "actually invoked": 17
  }
}
```
