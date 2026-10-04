# VeriCodeGen 2026 paper completion program

**Latest retained update, 2026-09-13T17:09:07.434105+00:00:** the [fresh authenticated observation](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/NS024_post_merge_observation_v1/result.private.json) confirms **85/86 completed**: Autoformalization 29/29, Law 29/29 and Supervision 27/28. The supervisor database recovery and normal NS-022 completion succeeded. NS-024 packaging has now merged at f7549b44 and completed, including its actual fresh TeX build, matching PDF text, accepted release binaries, and successful reproduction of all three supplement components. NS-025 final readiness is the sole task still in progress. The final three-paper local handoff follows its completion. Outside reviewers and returned annotations are not prerequisites; human-evaluation claims remain unmeasured. Earlier observations below are historical.

[Current manuscript PDFs, supplements and delivery status](DELIVERY.md).

Reviewed 2026-09-11. This program prepares **three independent
`ipfs_accelerate_py.agent_supervisor` implementation supervisors**, one per PDF.
Each has a root goal, subgoals, a dependency-ordered taskboard, a detailed review,
and its own configuration. Research tasks are open; creating these boards does
not establish experimental results. All three supervisors were launched on
September 11; initial startup and validation-command defects were found before
any model dispatch. Saved task histories and the exact repairs are recorded in
`runtime_bootstrap/`. Use the live status command below for current execution.

| Paper | Review | Native goals and TODOs | Original PDF main / total pages | Original missing evidence (current scope narrowed below) |
| --- | --- | --- | --- | --- |
| Compiler-Guided Autoformalization with Adaptive Multi-View Representations | [Review](autoformalization/review.md) | [Current goals](../../.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/paper.objectives.md), [29 tasks](../../.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/paper.todo.md), [config](../../.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/supervisor.json) | 9 / 27 | 44 TBD cells across A–E source-to-proof and T0–T5 training matrices; independently judged fidelity, genuine proof transfer, actual training and consumer evidence |
| From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents | [Review](law_to_action/review.md) | [Current goals](../../.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/paper.objectives.md), [29 tasks](../../.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/paper.todo.md), [config](../../.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/supervisor.json) | 8 / 17 | Five “Not run” and three pending evaluation rows; corpus fidelity, actual protected effects, durable capability use, real solver/crypto/network integration |
| Proof-Carrying Neurosymbolic Supervision: State, Logic-Governed Decisions, and Test-Evidence Reuse | [Review](neurosymbolic_supervision/review.md) | [Current goals](../../.worktrees/vericodegen-neurosymbolic_supervision-2026/papers/completion/neurosymbolic_supervision/paper.objectives.md), [28 tasks](../../.worktrees/vericodegen-neurosymbolic_supervision-2026/papers/completion/neurosymbolic_supervision/paper.todo.md), [config](../../.worktrees/vericodegen-neurosymbolic_supervision-2026/papers/completion/neurosymbolic_supervision/supervisor.json) | 9 / 28 | 34 TBD cells, unfinished abstract/results/disclosures; live paired A–D experiments, provider receipts, cold-oracle test reuse, measured costs |

The original 75 tasks sit under 22 subgoals and three root goals. Every task names its
paper evidence, dependencies, deliverables, acceptance criteria and candidate
implementation paths. Existing mocks, source inspections, estimates and dry-run
telemetry are explicitly separated from executed evidence in the reviews.

**Retained status through 14:51:05 UTC on 13 September 2026:** **83 of 86 tasks are completed**: Autoformalization **29/29**, Law **29/29** and supervision **25/28**. The [actual NS-022 amendment and restart](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/ns022_actual_amend_restart_v4/result.private.json) (`6374f2a3`) succeeded: two normal task updates moved NS-022 from blocked revision 11 to ready revision 12 and then **ready revision 13 before launch**, and the root-owned replacement supervisor registered. The [authenticated post-restart observation at 14:51:05 UTC](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/post_restart_observation_v1/result.private.json) (`0cbd1637`) confirms **NS-022 in progress at revision 14**. This establishes its native claim; provider prompt delivery is a separate observation. **NS-024 remains ready at revision 10** after the [repository-relative release handoff](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/ready_local_release_handoff_v5/result.private.json) (`72622790`), and **NS-025 remains ready at revision 6**. The retained task counts are one in progress and two ready. These are joined retained observations, not a fresh or globally atomic native query made by this documentation update; task counts do not establish publication readiness.

The [NS-020 provenance application at 14:40:44 UTC](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/ns020_compaction_provenance_preparation_v1/root_application_v1/result.private.json) (`46146daf`) passed normal validation and appended two validation/evidence records while preserving **NS-020 completed at revision 8**, its outputs and prior history. The [source-only writing-input installation at 14:47:28 UTC](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/worker_complete_writing_inputs_v1/root_source_application_v1/result.private.json) (`4d3a3b74`) installed exactly 63 additive files at `fc9dc176`, including locally readable NS-022 sources/PDF and NS-024 release inputs. It performed no native or scientific calls. The earlier [NS-022 retirement at 14:40:08 UTC](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/ns022_actual_retire_only_v1/result.private.json) (`33539c7a`) and writing-input installation remain retained. The subsequent restart has now succeeded at source `54fed`; manuscript adoption is still pending.

The [14:00:32 UTC handoff](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/ready_complete_release_handoff_v4/result.private.json) (`a7be3ad2`) and [earlier authenticated three-paper inspection](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/independent_all_paper_progress_v1/inspection.private.json) remain historical records; their earlier NS-022 and NS-024 statuses are superseded above.

The [NS-019 derivative-provenance application](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/ns019_ascii_derivative_provenance_adoption_preparation_v1/root_application_v1/result.private.json) (`c45b65f0`) finished at **14:02:03 UTC** through two native validation/evidence calls. NS-019 remains **completed at revision 8**; its completed history and scientific outcomes were not replaced or replayed.

The [bounded AF/Law final-deliverable audit at 14:02 UTC](runtime_bootstrap/unblock_20260912/af_law_final_delivery_audit_20260913T140220Z.private.json) (`cd422b09`) confirms that all four current PDF/ZIP hashes and sizes match their final checksum and handoff records. Both PDFs use embedded Type1/TrueType fonts, and both outer ZIPs pass full member CRC checks. AF has **9 main pages, references beginning on page 10, and 21 total pages**; the older format record's reference-page-9 locator is historical and does not change the correct main-page count. Law has **7 main pages and 23 total pages**. No large AF training artifact was read, and no scientific or numerical reproduction was rerun. Author proofreading and submission acknowledgments remain author-only responsibilities, without an outside-reviewer requirement.

The earlier [saved native guidance record at 13:08:13 UTC on 13 September 2026](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/ready_release_guidance_v1/result.private.json) and [supervision snapshot at 12:56:56 UTC on 13 September 2026](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/native_status_125533/status.private.json) remain history. The earlier [paired native application](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/ns016_017_adoption_route_v1/integration_candidate_v2/actual_decimal_application_v3/result.private.json) and [worker-guidance record](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/ready_analysis_writing_guidance_v1/result.private.json) retain NS-016 completed at revision 7 and NS-028 completed at revision 15.

**Retained-evidence update, 12:02 UTC on 13 September 2026:** all **32 final supervision trials are terminal**. The strict [complete-result analysis](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/analysis/analysis.private.json) (`824366e7`) records nine useful completions: **A 5/16, B 4/16**, with B−A = **−0.0625** and a descriptive family-bootstrap interval **[−0.1875, 0]**. It retains 32 provider POSTs, 16 score reservations and 15 completed cold validations; all 32 external charges remain unsettled. The comparison covers eight historical families with two repetitions nested within each arm; it supplies no confirmatory promotion claim. Original failures, boundary disclosures and cleanup evidence remain retained; no scientific trial is running or being replayed. Independent full-32 and candidate-metadata audits passed. Actual candidate export (`5207826d`) contains 1,005,818 bytes; root R1 acceptance (`f6a094d6`) and bundle admission (`a1817ab5`) are complete. The [actual adoption bundle](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/adoption_bundle_v1/bundle_manifest.private.json) contains **631 files / 28,873,490 bytes**; native task status and the subsequent anonymous-component qualification are reported separately.

**Anonymous final32 component succeeded at 12:57 UTC.** The [actual local build](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/anonymous_release_execution_v3/execution.private.json) (`00b2e492`) completed with **399 members / 7,460,880 bytes** and a **1,923,384-byte [ZIP](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/anonymous_release_actual_v3/supplement.zip)**. Exact table equality and reproduction after fresh ZIP extraction passed. The [release manifest](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/anonymous_release_actual_v3/release/release_manifest.json) (`6612cfa4`) and [root file audit](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/anonymous_v3_root_actual_release_review.private.json) (`1994470a`) bind the actual files. This final32 component is preserved inside the subsequently completed combined supplement described below; the final manuscript submission package remains pending. No publication or scientific replay occurred.

The [NS-019 rendering](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/actual_NS019_render_execution_v2/execution.private.json) and [NS-020 boundary reconciliation](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/actual_NS020_reconciliation_execution_v1/execution.private.json) produced seven and four outputs for ordinary-worker adoption; native completion is reported separately above. Both earlier failures remain preserved: the [first build](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/anonymous_release_execution_v1/execution.private.json) rejected an unapproved public-reference path, and the [second build](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/anonymous_release_execution_v2/execution.private.json), under its [earlier root approval](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/anonymous_release_admission_v2.approved.private.json), rejected a comparison between control-request and scientific-request digests. Both exited before creating their output directories; their source and evidence were not overwritten.

**Combined supervision supplement succeeded at 13:05:38 UTC.** The prepared [supervision supplement ZIP](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/combined_release_actual_v1/supplement.zip) contains the final32, prior-pilot and historical-boundary components in separate namespaces: **468 files / 8,985,278 expanded bytes**, with an actual ZIP size of **2,280,657 bytes** (SHA256 `48cee756e4e1bcdcf4d541b6c8721f21cba0800e990e1159a64f3eeb888a0b07`). All three child numerical reproducers passed before packing and after fresh extraction, giving **six successful reproductions** with matching results. The [actual build result](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/combined_release_actual_v1/result.private.json), [combined manifest](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/combined_release_actual_v1/combined/manifest.json) and [root byte audit](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/combined_root_actual_artifact_review_v1.private.json) bind this local artifact. Populations and cost scopes remain separate; no scientific trial, publication or final-paper completion is claimed. The [durable NS-024/025 handoff](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/ready_release_guidance_v1/result.private.json) finished at **13:08:13 UTC** through two normal supervisor API updates, retaining NS-024 ready at revision 7 and NS-025 ready at revision 6.

The three remaining native tasks are **NS-022, NS-024 and NS-025**. NS-020 has completed, including its appended provenance correction. The accepted integrated manuscript, combined supplement and repository-local writing inputs are prepared. NS-022 has a confirmed native claim at in-progress revision 14 after the successful restart. NS-024 and NS-025 remain ready. Ordinary manuscript/package adoption and final readiness validation remain pending. No outside reviewers or returned packets are required; independent-human/expert fidelity, agreement and adjudication remain unmeasured.

**The integrated supervision manuscript is prepared and root accepted.** The [20-page candidate PDF](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/ns024_actual_integrated_manuscript_v1/manuscript_v2/build/main.pdf) is **252,576 bytes** (SHA256 `0fb82abbec94c3858b6c9e63fcd456b16a5ad4aa2f294c4b52d08a8592c59862`): six main pages, references on page 7, technical appendices on pages 8–12, LLM disclosures on page 13 and all 16 checklist answers on pages 14–20. The [actual build package](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/ns024_actual_integrated_manuscript_v1/package.private.json) and [root acceptance at 13:48:04 UTC](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/ns024_integrated_root_review_v1.private.json) bind the file, preserved first 12 pages, clean added pages and embedded Type1/TrueType fonts. This is the accepted local candidate; NS-022/024/025 have not yet adopted and completed the final delivery. No author attestation or publication is claimed.

The [official workshop check](runtime_bootstrap/unblock_20260912/ns028_ab_pilot_review/runtime_contract_v3/final_AB_cold32_proposal_v1/actual_post32_v1/workshop_requirements_1257_v1/review.private.json) (`0f7294cf`, checked 13 September at 12:56 UTC) confirms the research-paper deadline is **13 September AoE, equivalent to 14 September 2026 at 12:00 UTC**. Use the unmodified official style, 4–9 main-text pages, anonymous paper and artifacts, required LLM disclosures, and the 50 MB PDF / 100 MB supplement limits. Author proofreading and actual submission remain separate; no outside review or collected human annotations are required to finish these manuscripts.

**All three autoformalization seeds completed full T2 and T3.** The original
final checker OOM remains a failed run outcome. A separately reviewed checker
successfully verified the saved outputs at **17:25:30 UTC**, without retraining:
394 original files / 53,087,253,217 bytes, six final T2/T3 checkpoint identities,
and preserved promotion locks. Actual checker wall time was 1,265.157 seconds;
peak cgroup memory was 23.672 GiB under its 32 GiB limit. Native checkpoint
delivery passed at **17:51:35 UTC**: all seven shards and 391 selected files
passed native store/read-back/consumer checks. Root independently checked all
14 phase records and container cleanup. Compact evidence and snapshots are
now integrated into the live supervisor checkout. AF-029 was amended and
released through the native API with all prior history preserved. The ordinary
supervisor completed AF-029; root verified all 104 receipt artifacts, 91 output
snapshot mappings and 182 original bundle files. All three actual checkpoint
promotion evaluations have now completed, each with 38 fixed canaries. All
retained identical compiler output across guidance settings and native promotion
rejection. Root verified all 189 bound files and container cleanup; the compact
result bundle was adopted and the ordinary supervisor completed all29 AF tasks. A subsequent audit found stale manuscript claims and double-counted historical costs; the complete correction is now integrated at `091624a7`, with10 append-only native validation/evidence calls preserving all29 completed task histories. The corrected PDF has nine main pages and21 total pages. [Current PDF](../../.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/submission/paper.pdf) and [supplement](../../.worktrees/vericodegen-autoformalization-2026/papers/completion/autoformalization/submission/supplement.zip) are available locally.
No learned consumer effect is claimed.

The native reconstruction routine can return the supplied target embedding.
Observed perfect T2 cosine/zero MSE is therefore target-assisted and supplies
no source-free generalization or semantic-fidelity credit. Actual parameter
updates and compiler-contract checks retain their distinct measured scope.

The Law fixed-action task retained 900 protocol-unadmitted observations after
its worker could not create the required per-attempt resource groups. Its
size-gate rescue repeated the diagnostic run; both runs and the rejected first
proposal are now preserved. Native task completion does not discharge the
missing admitted benchmark. The qualified operator runner started the unchanged
900-cell matrix under the frozen per-cell CPU, memory, process and timeout
limits. It stopped after 459 admitted cases and one resource-observation error
during normal exit. Retained physical evidence independently establishes that
case's resource limits and cleanup; its original monitoring error remains recorded.
Two normal-exit monitor failures now have separate verified physical-resource dispositions; the original errors remain unchanged. The operator matrix has now completed all900 scientific cases across902 host attempts. The five-segment reduction passed at00:25 UTC on13 September: measured group CPU totals1608.817478 seconds, including both failed startups at591 and625. Those two failures and the original459/560 monitor errors remain separately recorded; each recovered startup stayed within its remaining cumulative active allowance, and no scientific case was repeated. The full reduction passed independent review of9,933 retained bindings. Its20-file evidence bundle is integrated at `91ab8b60`; source integration `cab10050` preserved all22 native history domains. Body amendment `e4f9b0c3` and release `7197fc1f` preserved prior history, and the ordinary supervisor claimed LA-029 at revision4. No new benchmark execution was dispatched during adoption. LA-019 diagnostic analysis was recovered and completed; it does not supply LA-029's missing admitted benchmark.
The LA-009 shared-validator provenance correction is integrated through the native
validation/evidence APIs; it changes no numeric outcomes.

NS-028 retains its protected completion guard. The original and V2 pilots each
retain three failed consumed slots, 21 cancelled-unissued cells and no scores.
The V3 pilot uses the same eight V2 payloads, four units, A/B arms, three repeats
and fixed 24-cell order with common host/child/socket limits of 600/595/590
seconds. **All24 pilot cases are terminal: ten repairs passed cold tests, two failed hidden acceptance, ten hit the generation deadline, one response failed parsing and one candidate remained unscored after its review grant expired.** The12 actual cold scores and all failures are retained; strict reduction and public receipt export pass. Cell20's wrapper/gateway exceeded600 seconds; the ten generation deadlines also slightly exceeded the595-second child cap. All remain disclosed failures. Both arms have five useful developmental witnesses; this supplies no final comparison. The native current-source/final-admission checks are integrated; all8 native final preparations,16 request commitments, final service qualification, pre-outcome32-case freeze and actual offline client qualification are complete. Final generation started at01:40 UTC. Historical 03:00 UTC observation: six of32 cells were terminal: two full cold passes, two generation timeouts, one HTTP503 failure and one incomplete hidden import validation; case007 was active at03:00 UTC; the current count appears above. Reviewed pilot evidence is integrated and NS-028 completed15. Root independently verified its156 outputs,158 artifacts, normal validation and preserved native history. The cumulative generation ceiling
remains 31, including prior failures and the separate diagnostic. Unknown
remote costs remain unknown; no failed scientific cell is replaced or refunded.
[Current unblock record](UNBLOCKING.md) records the remaining work.

The user clarified that **no outside reviewers are available or required to
finish the manuscripts**. Applied AF/Law amendments removed those scheduling
gates. Independent-human/expert fidelity, agreement and adjudication remain
unmeasured; unsupported empirical claims are withdrawn or left as future work.
[Optional author feedback](REVIEW_START_HERE.md) links the preserved historical
forms. Packet review and reviewer recruitment do not block writing. Author
comments remain descriptive and non-independent, never semantic gold. All three
abstracts are registered. No labels or benchmark outcomes have been invented.

## Sources and supplied templates

The user supplied [this Overleaf project](https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0).
Access from this environment returned HTTP 403 on 2026-09-11. Its contents and
which manuscripts it contains remain unverified; no manuscript source was
downloaded. Each first task attempts authorized source recovery and can
reconstruct LaTeX from the PDF with a discrepancy audit. Independent code and
protocol tasks do not depend on Overleaf access.

[source_inputs.json](source_inputs.json) records hashes of the nine supplied
PDF/template inputs and review-time repository commits. These commits are
starting locations, not a claim that the dirty workspace is a frozen experiment.

The user also supplied these local **research-paper** inputs:

- [neurips_2026_vericode_workshop.tex](../neurips_2026_vericode_workshop.tex): manuscript shell.
- [neurips_2026_vericode.sty](../neurips_2026_vericode.sty): unmodified workshop style.
- [checklist.tex](../checklist.tex): 16 questions, with actual Yes/No/N/A answers and justifications to fill separately for each paper.

These are formatting templates, not the editable manuscripts. Use the research
package in default submission mode. The supplied competition variants follow a
different track and do not apply to these three research submissions. Preserve
the originals; each manuscript gets its own checklist copy. Default anonymous
author text produced by the official style is expected, and must not be
misclassified as an unfinished author field. Remove genuine draft result and
checklist placeholders in the completed manuscripts.

## Submission priorities and timing

The [workshop CFP](https://vericodegen.github.io/cfp.html), checked again 2026-09-13,
lists abstract and paper deadlines of September 11 and September 13,
2026 AoE, respectively. The research-paper cutoff is **September 14, 2026,
12:00 UTC**, confirmed by the official-check record above.
It requires 4–9 main-text pages, excluding references and appendices; anonymous
paper and linked artifacts; the official workshop template; methodology-relevant
LLM disclosures; and at most 50 MB PDF / 100 MB supplementary ZIP. The workshop
is non-archival. Recheck the live dates before author submission.

Each supervisor should start with source recovery and an independent
claim/code/environment audit, then freeze its smallest credible experimental
scope **before observing outcomes**. P0 marks submission-critical work; P1
supports fuller evidence. Dependency closure can bring P1 work onto a P0 path.
The full experiments are not assumed feasible before September 13. If a run
cannot finish, record the concrete limitation and remove or narrow its associated
empirical claim; never fill a result cell with an estimate or fabricated value.
An unrun experimental obligation is not marked completed merely because it is
documented. Record scope changes explicitly in the paper's claim matrix.

The three lanes can run in parallel:

1. **Autoformalization:** recover/audit → freeze source splits and the supported
   structural-evidence scope → validate real training/proof adapters → execute
   admitted comparisons → analyze measured outcomes and costs → complete the
   manuscript with unmeasured human-fidelity claims excluded.
2. **Law to action:** recover/audit → freeze legal/CVE/skill cohorts and explicit
   formal-property provenance → qualify actual effects and enforcement → run
   admitted comparisons → analyze measured outcomes and costs → complete the
   manuscript with unmeasured expert-validity claims excluded.
3. **Neurosymbolic supervision:** recover/audit → pin the loaded repository forest
   and independent cold oracle → qualify provider admission, reuse and recovery
   → run the frozen32-cell A/B cold comparison → analyze actual model,
   proof and execution costs → complete manuscript.

Each lane ends with clean-environment reproduction and an anonymous submission
package. This work does not require an outside reviewer. Optional author
feedback and actual submission remain separate; author approval is never
inferred. The three abstracts are already registered. These boards authorize
preparation, not messages to organizers or an OpenReview submission.

## Native supervisor integration

The canonical implementation lives at `external/ipfs_accelerate`, with datasets
and kit dependencies under `external/ipfs_datasets` and `external/ipfs_kit`.
The older nested checkout under `hallucinate_app` is not the launch source.

From the repository root:

```bash
python3 scripts/paper_supervisors.py validate
python3 scripts/paper_supervisors.py commands
```

`validate` imports the actual native goal/task parsers and supervisor CLI/config
builder. It checks task and parent DAGs, goal membership, namespaces, outputs,
reviewed acceptance criteria, template inputs, and isolated-worktree settings.
It checks the import sources in that checkout; the root checkout retains the
initial 75-task seed. Later native follow-ups have separate admission evidence
and their current contracts are linked above.
It does not call a model, run a benchmark, or claim live provider readiness.
The checked result is saved in [validation.json](validation.json).
The focused tests in `tests/test_paper_supervisors.py` cover evidence integrity,
follow-up coverage and isolated native database configuration. Additional
materializer, Quack owner, campaign lifecycle and DuckLake integration suites
exercise fresh temporary stores without running paper experiments. Run them with
`python3 -m unittest discover -s tests -p test_paper_supervisors.py -v`.

Use a committed integration checkout containing these inputs before live work:
native ephemeral workers start from Git commits and cannot see untracked paper
files. Existing unrelated dirty workspace changes were left untouched during
this review. Commit only the reviewed campaign inputs in the integration
checkout, or carry them to a dedicated integration branch through your normal
Git workflow. Do not discard existing work to satisfy launch preflight.

The database campaign uses three dedicated DuckDB owners served over authenticated
loopback Quack, three native implementation supervisors, and a genuine DuckLake
catalog containing history fetched through Quack. Each paper has its own branch,
checkout, database, worker directories and merge queue. The native supervisor
performs task claims, implementation, validation and merges. The campaign process
starts owners, checks real remote readiness, monitors children and projects history.
A complete native route pins Grok `grok-4.6` as primary and Codex
`gpt-5.6-terra` with **high** reasoning as its fallback, as requested by the user.
Fallback requires fresh independently verified Grok quota exhaustion.
A failed lane is reported; it is never silently reset or switched to another task
authority. Native execution/coordination bookkeeping uses private local sidecars.

```bash
python3 scripts/paper_supervisor_campaign.py start
python3 scripts/paper_supervisor_campaign.py status
python3 scripts/paper_supervisor_campaign.py stop
```

`start` launches a detached controller. `serve` runs the same controller in the
foreground. The older `paper_supervisors.py run --paper all` entry point delegates
to this database campaign. `status` checks process birth identities and fetches
current tasks/events through each actual Quack endpoint. Stopping the controller
terminates only its owned supervisors and owners. It does not stop other campaigns.

Integration branches are `agent/vericodegen-2026-<paper>`, in
`.worktrees/vericodegen-<paper>-2026`. Runtime source pins and the verified TeX
installation are recorded in [runtime_bootstrap/](runtime_bootstrap/).
Workers can compile with the tested user-local command:

```bash
/home/barberb/.local/bin/vericodegen-latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex
```

The TeX and research mounts are qualified in actual inert Grok and Codex
containers. No actual quota-triggered provider fallback has been observed.
Scoped task-owned PDF/ZIP admission is implemented and tested; final packages
still require the manuscript and submission checks on their actual contents.

State defaults to `~/.local/state/ipfs_accelerate_py/vericodegen-2026/`;
use `--state-root` for another location. The campaign files are `campaign.json`,
`health.json`, `campaign.log`, `quack-snapshot.json`, and `ducklake-status.json`.
Each paper has `owner.log`, `supervisor.log`, `control.duckdb`, and native worker
state beneath `state/`. The owner alone opens its live control database file;
inspect it through Quack. The opaque token handle is public; token files stay
private and resolved credentials are scrubbed from provider environments.
DuckLake lives under `ducklake/` and is a history projection, not task authority.

Long training/benchmark jobs should checkpoint progress and publish heartbeat
logs. A task attempt has a two-hour worker limit and three attempts; a genuinely
longer experiment must be split into resumable work with explicit dependencies
and resource allocation. Each protocol task must set actual CPU/GPU/model/API
budgets from available resources; this plan does not assume three concurrent
GPU training jobs fit the host. Keep non-GPU work progressing while scarce
resources are occupied. Do not change any other paper's manuscript/results.

## Boards, follow-ups and completion evidence

`tasks.json`, `paper.objectives.md` and `paper.todo.md` are reviewed import
sources. `materialize_paper_database.py` imports their complete native task and
goal contracts into a new database once, verifies dependencies and readiness,
and refuses to overwrite an existing store. Live statuses and discovered tasks
belong in the native database. Private per-attempt Markdown projections used by
the native execution bridge do not grant scheduling authority. Source PDFs,
templates, reviews, seed manifests, configurations and validators are protected
worker inputs. Register follow-ups through the native database API with unique
same-paper IDs, explicit goal lineage, dependencies, outputs, validation and
concrete acceptance criteria; preserve/export their evidence contracts for the
receipt verifier. The root goal must account for those follow-ups too.

Twelve implementation tasks name intended source-edit paths in `Allowed paths`.
The native worker derives its write scope from `Outputs`; those source paths
still need an exact output contract or a bounded follow-up before dispatch.
`Reuse candidates` is a discovery hint only. Each task's own evidence snapshot
directory must be included in native `Outputs`; `Predicted files` alone does
not grant write scope. Baseline tests and independent
oracles must not be weakened to improve reported results. The initial
`cpu-medium` / `execution` metadata describes the implementation worker; protocol
tasks must allocate and declare actual GPU/network resources for experiments.

Each task writes
`papers/completion/<paper>/receipts/<TASK-ID>.json`, following this schema:

```json
{
  "schema": "paper-task-evidence/v1",
  "task_id": "AF-001",
  "status": "complete",
  "completed_at": "2026-09-11T00:00:00+00:00",
  "source_versions": {"repository": "actual commit; record relevant dirty overlay and dependencies"},
  "artifacts": {
    "papers/completion/autoformalization/receipts/snapshots/AF-001/main.tex": "actual sha256",
    "papers/completion/autoformalization/receipts/snapshots/AF-001/build.log": "actual sha256"
  },
  "outputs": {
    "papers/completion/autoformalization/manuscript/main.tex": "papers/completion/autoformalization/receipts/snapshots/AF-001/main.tex"
  },
  "criteria": [{
    "criterion": "Copy the exact reviewed criterion here; include every criterion in order",
    "status": "met",
    "explanation": "What the retained evidence establishes and its limits",
    "evidence": ["papers/completion/autoformalization/receipts/snapshots/AF-001/main.tex"]
  }],
  "commands": [{
    "argv": ["actual-command", "actual-argument"],
    "exit_code": 0,
    "log": "papers/completion/autoformalization/receipts/snapshots/AF-001/build.log"
  }]
}
```

The example is a schema illustration, not a receipt or experiment result.
Snapshot every scientific deliverable (all files for directory deliverables);
keep immutable evidence under the task's snapshots directory. The task's own
receipt and snapshot directory are native bookkeeping outputs: do not
recursively snapshot the snapshot directory. Criteria refer to those hashed
snapshots. Record the actual tools, commands, versions, data/model identities,
errors, annotation provenance if collected (otherwise unmeasured), and full result denominators. Use the exact
seed criteria list; for a new native follow-up, its complete `Acceptance` field
is one criterion. Follow-up validation uses the same `verify-task` command.

Read the actual UTC clock when recording `completed_at`, for example with
`datetime.now(timezone.utc).isoformat()`; never copy the example timestamp or
guess a future time. Preserve the exact executable argument vector in each
`commands[].argv`, including the complete Python `-c` program. A prose label
for a command is not executable evidence. For Python reading a program from
stdin (`python3 -`), retain that complete program as a hashed snapshot and set
`commands[].stdin_artifact` to its repository-relative snapshot path. Record
literal environment values and the actual working directory needed to replay
the command. Named repository scripts may use their retained source version;
an explicit `script_artifact` can bind a separate immutable script copy.

When correcting a receipt, retain the original receipt and original snapshots
as immutable history, add the exact replay source and logs, and clearly label
the later replay's timestamp and environment. A later successful replay does
not prove that an earlier malformed command ran successfully.

```bash
python3 scripts/paper_supervisors.py verify-task --paper autoformalization --task AF-001
python3 scripts/paper_supervisors.py verify-goal --paper autoformalization --goal AF-G000
```

Task checks compare current deliverables against immutable snapshots. Goal
checks retain historical task evidence while reconciling later revisions of
shared outputs, so editing a manuscript in a later task does not erase its
source-recovery evidence. Receipts and passing checks establish artifact
integrity and recorded coverage; they are not independent scientific replication
or a substitute for final clean-environment reproduction and the claim audit.
Optional author feedback does not block manuscript completion.
Source-recovery checkpoint receipts are now being recorded after local builds
and PDF reconciliation. They do not establish any benchmark result or a
submission-ready manuscript. Keep private provenance and receipt snapshots out
of the anonymous publication package; final packaging tasks must audit that
separation. Use the database status and each receipt's stated scope to determine
what has actually been completed.
