"""Render measured incremental results and retain a numbered evidence snapshot.

Never runs experiments or overwrites the historical final manuscript.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def load(relative):
    return json.loads((ROOT / relative).read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--increment", required=True)
    args = parser.parse_args()
    assert args.increment.isdigit()
    snapshot = ROOT / "increments" / args.increment
    snapshot.mkdir(parents=True)
    sources = ["evals/context/results/summary.json", "evals/context/results/rows.json",
               "evals/routing_v2/summary.json", "evals/routing_v2/metering_audit.json",
               "evals/reuse/runs/development-v6/summary.json",
               "evals/reuse/runs/development-v6/cases.json",
               "evals/reuse/runs/development-v6/timing.json",
               "evals/compositional_v2/summary.json"]
    ctx, routing, reuse, native = [load(p) for p in (
        sources[0], sources[2], sources[4], sources[7])]
    sources.extend(["evals/persistence/summary.json", "evals/context/native_development/results_v1/summary.json"])
    persistence, dependency = load(sources[-2]), load(sources[-1])
    sources.append("evals/context/live_v1/summary.json")
    live_context = load(sources[-1])
    assert live_context["complete"] and live_context["observed_cells"] == 6
    sources.extend(["evals/procedures/summary.json", "evals/procedures/control_summary.json",
                    "evals/native_proof/runs/source-built-v1/summary.json"])
    procedures, procedure_control, native_proof = [load(p) for p in sources[-3:]]
    sources.extend(["evals/scorer_integrity/summary.json", "evals/scorer_integrity/saved_rescore.json",
                    "evals/native_proof/runs/horn-v1/honest_only_summary.json",
                    "evals/publication_baseline/run-v1/summary.json"])
    scorer, rescores, horn, publication = [load(p) for p in sources[-4:]]
    assert scorer["frozen_files_match"] and scorer["saved_records"] == len(rescores) == 14
    assert scorer["categories"]["adversarial"]["old_false_admissions"] == 5
    assert scorer["categories"]["adversarial"]["stronger_false_admissions"] == 0
    assert all(r["stronger_scorer_success"] == r["original_success"] for r in rescores)
    for row in rescores:
        path = ROOT.parents[2] / row["source_record"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["source_record_sha256"]
    assert horn["checks_passed"] and len(horn["positive_rows"]) == 3
    assert not horn["incomplete_investigation"]["custom_executable_run"]
    assert publication["returncode"] == 0 and publication["counts"]["passed"] == 47
    sources.extend(["evals/scorer_integrity/freeze.json", "evals/scorer_integrity/artifact_audit.json",
                    "evals/native_proof/runs/horn-v1/freeze.json",
                    "evals/publication_baseline/run-v1/freeze.json",
                    "evals/publication_baseline/run-v1/loaded_sources.json",
                    "evals/publication_baseline/run-v1/results.xml"])
    for row in horn["positive_rows"]:
        sources.extend(str(Path(row[k]).relative_to(ROOT)) for k in ("proof", "witness", "prove_receipt", "verify_receipt"))
    sources.extend(["evals/world_memory_development/runs/development-v1/summary.json",
                    "evals/world_memory_development/runs/development-v1/validation.json",
                    "evals/world_memory_development/runs/development-v1/compiler_identity_audit.json",
                    "evals/sealing_development/run-v1/summary.json",
                    "evals/sealing_development/run-v1/artifact_audit.json",
                    "evals/sealing_development/continuation-v1/summary.json"])
    world, world_validation, world_compiler, sealing, seal_validation, continuation = [load(p) for p in sources[-6:]]
    assert all(t["passed"] == t["cases"] == 11 for t in world["totals"].values())
    assert len([r for r in world["rows"] if r["arm"] != "producer"]) == 44
    assert sealing["complete"] and sealing["main_publications"] == 3
    assert continuation["complete"] and continuation["original_run_unchanged"]
    assert continuation["fresh_next_event_consumed_recovered_root"]
    assert world_validation["passed"] and world_validation["check_count"] == 893
    assert world_compiler["candidate_identity_mismatches"] == world_compiler["observation_identity_mismatches"] == 11
    assert seal_validation["checks_passed"] == 181
    sources.extend(["evals/sealing_development/preparation-timing-v1/summary.json",
                    "evals/sealing_development/phase_artifact_audit.json"])
    seal_timing = load(sources[-2])
    assert seal_timing["all_evidence_content_identical"]
    assert all(a["accepted"] == a["trials"] == 4 for a in seal_timing["arms"].values())
    sources.extend(["evals/world_memory_development/runs/compiler-continuation-v1/summary.json",
                    "evals/world_memory_development/runs/compiler-continuation-v1/validation.json",
                    "evals/world_memory_development/source_profiles/compiler_identity_v1/source.diff",
                    "evals/integrated_v1/context_qualification/results_v6_bounded_index/summary.json",
                    "evals/integrated_v1/context_qualification/audit_v6_bounded_index.json",
                    "evals/integrated_v1/context_qualification/results_v6_bounded_index/freeze.json",
                    "evals/integrated_v1/context_qualification/results_v5/outcome.json",
                    "evals/integrated_v1/context_qualification/results_v7_full_index/outcome.json",
                    "evals/integrated_v1/context_qualification/comparison_v5_v7_xml.json",
                    "evals/integrated_v1/context_qualification/merkle_node_index_v1.patch",
                    "evals/integrated_v1/public_issue_reproduction_v1/summary.json",
                    "evals/recruitment/verified_metadata_v1/summary.json",
                    "evals/recruitment/ancestry_v1/summary.json",
                    "evals/recruitment/repository_identity_v2/summary.json",
                    "evals/recruitment/repository_identity_audit.json"])
    world_cont = load("evals/world_memory_development/runs/compiler-continuation-v1/summary.json")
    world_cont_audit = load("evals/world_memory_development/runs/compiler-continuation-v1/validation.json")
    context_roundtrip = load("evals/integrated_v1/context_qualification/results_v6_bounded_index/summary.json")
    context_audit = load("evals/integrated_v1/context_qualification/audit_v6_bounded_index.json")
    assert world_cont["passed"] == world_cont["case_count_including_seed"] == 12
    assert world_cont["action_calls_including_seed"] == 19 and world_cont["service_process_count"] == 25
    assert world_cont_audit["passed"] and world_cont_audit["check_count"] == 1183
    assert context_roundtrip["all_roundtrips_passed"] and context_audit["all_checks_passed"]
    assert sum(r["cold_incremental_equal_cases"] for r in context_audit["cases"]) == 4
    assert sum(r["native_negative_controls"] for r in context_audit["cases"]) == 22
    full_context = load("evals/integrated_v1/context_qualification/results_v7_full_index/outcome.json")
    xml_comparison = load("evals/integrated_v1/context_qualification/comparison_v5_v7_xml.json")
    assert full_context["pyparsing_process"]["timed_out"]
    assert full_context["pyparsing_process"]["bound_seconds"] == 600
    assert xml_comparison["baseline_native_state_cid"] == xml_comparison["variant_native_state_cid"]
    assert xml_comparison["baseline_semantic_root_cid"] == xml_comparison["variant_semantic_root_cid"]
    assert xml_comparison["all_public_file_bytes_modes_equal"]
    for task in ("ns-hist-01-xmltodict", "ns-hist-02-pyparsing"):
        prefix = "evals/integrated_v1/context_qualification/results_v6_bounded_index/" + task + "/"
        sources.extend(prefix + name for name in ("producer.json", "consumer.json", "semantic_scope.json",
                       "retained_raw_inventory.json", "cold_incremental_identity_checks.json"))
    sources.extend(["evals/recruitment/arm64_qualification/run-v1/scoring-v2/score_summary.json",
                    "evals/recruitment/arm64_qualification/run-v1/artifact_audit.json",
                    "evals/recruitment/arm64_qualification/run-v1/nonexpected_error_triage.json"])
    benchmark = load(sources[-3])
    benchmark_audit = load(sources[-2])
    assert benchmark["qualified"] and benchmark["ordinary_native_imports"]
    assert not benchmark["native_algorithms_modified"] and not benchmark["initializer_bypass_used"]
    assert benchmark_audit["checks_passed"] == 180
    assert benchmark_audit["nonexpected_setup_errors_per_control"] == 8
    assert not benchmark_audit["all_collected_tests_error_free"]
    controls = {r["control"]: r for r in benchmark["controls"]}
    assert controls["gold"]["native_resolved"] and not controls["unfixed"]["native_resolved"]
    assert all(r["expected_checks_completed"] == 187 and r["expected_missing"] == 0
               and r["expected_errors"] == 0 for r in controls.values())
    sources.extend(["evals/integrated_v1/controller_qualification/development-v2/summary.json",
                    "evals/integrated_v1/controller_qualification/development-v2/audit.json",
                    "evals/integrated_v1/controller_qualification/development-v2/profile.json",
                    "evals/integrated_v1/context_qualification/routing_enrollment_v1/summary.json",
                    "evals/integrated_v1/context_qualification/routing_context_audit_v1.json",
                    "evals/recruitment/literature_exposure_v1.json"])
    controller = load(sources[-6])
    controller_audit = load(sources[-5])
    assert controller_audit["passed"] and not controller_audit["failed"]
    assert controller["event_count"] == 13 and controller["controller_invocations"] == 16
    assert controller["terminal_status_counts"] == {"accepted": 9, "effect_unknown": 1, "residual_pending": 2, "stale_parent": 1}
    assert controller["provider_dispatches"] == controller["native_sealing_calls"] == 0
    assert controller_audit["operation_counts"]["scorer_attempts"] == 30
    assert controller_audit["operation_counts"]["scorer_terminal_receipts"] == 29
    sources.extend([
        "evals/integrated_v1/controller_qualification/development-v3-attempt2/summary.json",
        "evals/integrated_v1/controller_qualification/development-v3-attempt2/audit_v3.json",
        "evals/integrated_v1/controller_qualification/development-v3-attempt2/REPORT.md",
        "evals/integrated_v1/controller_qualification/development-v3-attempt2-artifact-manifest.json",
        "evals/integrated_v1/context_qualification/repository_service_qualification_v1/qualification.json",
        "evals/integrated_v1/context_qualification/requests_public_enrollment_v1/summary.json",
        "evals/recruitment/arm64_qualification/requests5414/run-v4/score_summary.json",
        "evals/recruitment/arm64_qualification/requests5414/run-v4/artifact_audit.json",
        "evals/recruitment/arm64_qualification/requests5414/run-v4/environment_port.json",
        "evals/recruitment/arm64_qualification/requests5414/run-v4/distribution_continuity.json",
        "evals/recruitment/candidate_scoring_v1/qualification-v2/summary.json",
        "evals/recruitment/candidate_scoring_v1/endpoint_v2_network_diagnosis.json",
        "evals/recruitment/additional_metadata_v1/summary.json",
        "evals/recruitment/rebench_screen_v1/queue.json",
        "evals/recruitment/rebench_screen_v1/freeze.json",
        "evals/recruitment/rebench_ancestry_v1/summary.json",
        "evals/recruitment/rebench_identity_v1/summary.json",
        "evals/recruitment/rebench_screen_audit.json",
        "evals/recruitment/ADDITIONAL_RECRUITMENT.md",
    ])
    joined = load("evals/integrated_v1/controller_qualification/development-v3-attempt2/summary.json")
    joined_audit = load("evals/integrated_v1/controller_qualification/development-v3-attempt2/audit_v3.json")
    assert joined["events"] == 8 and joined["controller_invocations"] == 9
    assert joined["status_counts"] == {"accepted": 6, "residual_pending": 1, "stale_parent": 1}
    assert joined["native_publication_attempts"] == 7 and joined["native_recovery_CAS_calls"] == 1
    assert joined_audit["all_passed"] and joined_audit["check_count"] == 6424
    assert joined_audit["all_actual_scorer_processes"] == 42
    assert joined["provider_dispatches"] == joined["provider_tokens"] == 0
    repository_context = load("evals/integrated_v1/context_qualification/repository_service_qualification_v1/qualification.json")
    requests_context = load("evals/integrated_v1/context_qualification/requests_public_enrollment_v1/summary.json")
    assert repository_context["all_checks_passed"] and len(repository_context["checks"]) == 12
    assert requests_context["all_roundtrips_passed"] and len(requests_context["rows"]) == 2
    assert requests_context["source_substitutions"] == requests_context["provider_calls"] == 0
    for row in requests_context["rows"]:
        result = row["summary"]
        assert result["producer"]["declared_files"] == 97
        assert result["producer"]["python_files"] == 35
        assert result["consumer"]["all_checks_passed"]
        assert len(result["consumer"]["negative_controls"]) == 11
        prefix = "evals/integrated_v1/context_qualification/requests_public_enrollment_v1/" + row["id"] + "/"
        sources.append(prefix + "freeze.json")
        sources.extend(prefix + result["producer"]["task_id"] + "/" + name
                       for name in ("producer.json", "consumer.json"))
    benchmark5414 = load("evals/recruitment/arm64_qualification/requests5414/run-v4/score_summary.json")
    assert benchmark5414["qualified"] and benchmark5414["ordinary_native_imports"]
    controls5414 = {r["control"]: r for r in benchmark5414["controls"]}
    assert controls5414["gold"]["native_resolved"] and not controls5414["unfixed"]["native_resolved"]
    assert all(r["expected_checks_completed"] == 131 and r["expected_missing"] == 0
               and r["expected_errors"] == 0 and r["parsed_status_counts"].get("ERROR", 0) == 0
               for r in controls5414.values())
    candidate_endpoint = load("evals/recruitment/candidate_scoring_v1/qualification-v2/summary.json")
    assert not candidate_endpoint["qualified"]
    assert sum(r["control_passed"] for r in candidate_endpoint["native_controls"]) == 3
    assert all(r["passed"] for r in candidate_endpoint["negative_controls"])
    additional = load("evals/recruitment/additional_metadata_v1/summary.json")
    screen = load("evals/recruitment/rebench_screen_v1/queue.json")
    screen_audit = load("evals/recruitment/rebench_screen_audit.json")
    assert additional["candidate_rows_not_deduplicated_across_datasets"] == 22067
    assert not any(r["protected_columns_decoded"] for r in additional["datasets"])
    assert screen["metadata_pair_candidates"] == 53 and screen["primary_count"] == 16
    assert screen_audit["all_checks_passed"] and screen_audit["candidate_pairs"] == 16
    assert screen_audit["actual_forward_ancestry_results"] == 16
    assert screen_audit["current_identity_comparisons_to_prior"] == 448
    assert screen_audit["confirmatory_enrolled_families"] == 0
    assert all("x86_64" in task["image_name"]
               for row in screen["ranked_candidates"][:16] for task in row["tasks"])
    context_prefix = "evals/integrated_v1/context_qualification/"
    sources.extend(context_prefix + name for name in (
        "full_context_profiles_v11_audit.json", "audit_full_context_profiles_v11.py"))
    full_profiles = load(context_prefix + "full_context_profiles_v11_audit.json")
    assert full_profiles["all_checks_passed"] and len(full_profiles["profiles"]) == 5
    assert not full_profiles["full_pyparsing_roundtrip_complete"]
    assert full_profiles["literal_union_actual_predicates"]["all_equal"]
    assert full_profiles["literal_union_actual_predicates"]["actual_link_payloads_compared"] == 55859
    for relative, digest in full_profiles["input_sha256"].items():
        source = context_prefix + relative
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == digest
        sources.append(source)
    sources.extend(context_prefix + name for name in (
        "full_state_identity_v12_audit.json", "audit_full_state_identity_v12.py",
        "state_identity_validation_v5/summary.json", "state_identity_v5.patch",
        "state_identity_cache_design_v5.md", "requests_public_reads_v1/summary.json"))
    full_state = load(context_prefix + "full_state_identity_v12_audit.json")
    assert full_state["all_audit_checks_passed"] and full_state["all_roundtrips_complete"]
    assert full_state["runtime_files_rehashed"] == 7255 and full_state["runtime_unchanged"]
    assert full_state["native_regressions_passed"] == 159
    for relative, digest in full_state["input_sha256"].items():
        source = context_prefix + relative
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == digest
        sources.append(source)
    full_state_rows = {row["producer"]["task_id"]: row for row in full_state["rows"]}
    assert full_state_rows["ns-hist-02-pyparsing"]["producer"]["python_files"] == 154
    assert sum(len(row["consumer"]["negative_controls"]) for row in full_state_rows.values()) == 22
    assert sum(row["producer"]["declared_files"] for row in full_state_rows.values()) == 302
    assert all(row["consumer"]["all_checks_passed"] for row in full_state_rows.values())
    source_reads = load(context_prefix + "requests_public_reads_v1/summary.json")
    assert source_reads["all_checks_passed"] and source_reads["native_source_expansions"] == 4
    assert sum(row["exact_raw_bytes_returned"] for row in source_reads["rows"]) == 79942
    endpoint_prefix = "evals/recruitment/candidate_scoring_v1/"
    sources.extend(endpoint_prefix + name for name in (
        "qualification-v3/summary.json", "qualification-v3/audit.json",
        "qualification-v3/artifact_manifest.json", "registry_v3.json", "CONTRACT_V3.md",
        "cumulative_source_qualification_v1/summary.json"))
    endpoint3 = load(endpoint_prefix + "qualification-v3/summary.json")
    endpoint3_audit = load(endpoint_prefix + "qualification-v3/audit.json")
    assert endpoint3["qualified"] and all(row["control_passed"] for row in endpoint3["native_controls"])
    assert len(endpoint3["native_controls"]) == 4 and len(endpoint3["negative_controls"]) == 10
    assert endpoint3_audit["passed"] and endpoint3_audit["check_count"] == 94
    assert endpoint3_audit["artifact_count"] == 1175
    assert not endpoint3["adversarial_candidate_oracle_integrity_qualified"]
    cumulative_source = load(endpoint_prefix + "cumulative_source_qualification_v1/summary.json")
    assert cumulative_source["qualified"] and cumulative_source["actual_source_tree_matches_expected"]
    assert cumulative_source["source_files"] == 98 and cumulative_source["changed_paths"] == 3
    sources.extend(["evals/recruitment/replay_rebench_screen_audit.py",
                    "evals/recruitment/rebench_screen_replay_audit_v2.json"])
    replay_screen = load(sources[-1])
    assert replay_screen["all_checks_passed"] and replay_screen["check_count"] == 629
    assert procedure_control["independently_replayed_cells"] == 16
    assert native_proof["positive_proofs"] == 3 and native_proof["ordinary_rejections"] == 8
    assert persistence["observations"]["same_attempt_not_executed_twice"]
    assert dependency["cold_incremental_root_matches"] == dependency["cold_incremental_comparisons"] == 12
    # Regenerate routing totals from all terminal cells, preserving zero-call paths.
    cells = [json.loads(p.read_text()) for p in sorted((ROOT / "evals/routing_v2/results").glob("*.json"))
             if not p.name.endswith(".local.json")]
    assert len(cells) == routing["scheduled_cells"] == 8
    for arm in ("baseline", "system"):
        rows = [r for r in cells if r["arm"] == arm]
        assert sum(r["success"] for r in rows) == routing["arms"][arm]["successes"]
        assert sum(r["provider_calls"] for r in rows) == routing["arms"][arm]["provider_calls"]
        assert sum(r["normalized_usage"]["total_tokens"] for r in rows) == routing["arms"][arm]["total_tokens"]
        sources.extend(str(p.relative_to(ROOT)) for p in (ROOT / "evals/routing_v2/results").glob(arm + "-*.json"))
    receipts = list((ROOT / "evals/routing_v2/results/provider").glob("*/result.json"))
    assert len(receipts) == 6
    for p in receipts:
        r = json.loads(p.read_text())
        assert r["status"] == "response" and r["served_model"] == "grok-4.6"
        assert r["usage"]["total_tokens"] == r["normalized_usage"]["total_tokens"]
        sources.extend([str(p.relative_to(ROOT)), str(p.with_name("request.json").relative_to(ROOT))])
    # The paired residual requests are byte-identical canonical envelopes.
    for name in ("clamp_interval", "stable_deduplication"):
        folder = ROOT / "evals/routing_v2/results/provider"
        assert (folder / ("baseline-" + name) / "request.json").read_bytes() == (folder / ("system-" + name) / "request.json").read_bytes()
    assert ctx["total_substituted_windows"] == 0
    assert native["artifact_verification"]["valid"]
    assert reuse["matched_cases"] == reuse["case_count"] == 14
    counts = ctx["message_content_token_totals"]
    a, b = routing["arms"]["baseline"], routing["arms"]["system"]
    reduction = 100 * (1 - b["total_tokens"] / a["total_tokens"])
    text = r"""\section{Incremental system evaluation}
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
system/user message content totaled @RAW@ for A, @ADD@ for B, and @SUB@ for
guarded substitution C: increases of @ADDINC@\% and @SUBINC@\% over A.
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
@FULLCAPSULES@ serialized context-content
tokens versus @DEPROW@ for raw source. A new restricted projection instead
transports source-bound integer equations. Six separate Z3 equivalence checks
and 252 concrete source executions check that projection; its @EQUATIONS@
tokens are @EQUATIONRED@\% below raw. Plain AST source compaction totals
@ASTTOKENS@ tokens. These are named-encoding offline counts, not provider savings.
The equation profile excludes floats, custom objects, side effects and unsupported
syntax. The compact projection is an evaluated addition; the full native capsule
payload itself is larger than raw source in these examples.

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
from @XMLBASE@ to @XMLOPT@ seconds in one observation per profile. Full pyparsing
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
takes @FULLXMLPREP@ seconds; pyparsing takes @FULLPYPREP@ seconds, with
@FULLPYCPU@ CPU seconds. The latter producer process takes @FULLPYPROCESS@
seconds and its consumer @FULLPYCONSUMER@ seconds. All 302 regular files and
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
frozen objects. Full pyparsing incremental mutation equality remains separate
work. The successful full run establishes completion within the bound, not a
replicated speedup or token benefit; the five previous deadlines remain results.

\paragraph{Live context substitution.}
The three dependency-bearing development repositories also support a matched
raw-versus-equation repair pilot. Both arms pass all three separate cold
behavioral checks; all six requests return usage. Provider input totals are
@LIVEINPUTRAW@ raw versus @LIVEINPUTCOMPACT@ compact (@LIVEINPUTRED@\% fewer),
and total usage is @LIVETOTALRAW@ versus @LIVETOTALCOMPACT@ (@LIVETOTALRED@\%
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
Model first & @ASUCCESS@/4 & @ACALLS@ & @ATOKENS@ \\
Symbolic first plus residual & @BSUCCESS@/4 & @BCALLS@ & @BTOKENS@ \\
\bottomrule
\end{tabular}
\end{table}

All six Grok 4.6 requests returned usage, under the same low-effort profile,
\texttt{max\_tokens=2048} request parameter and 240-second deadline, without retries.
The observed reduction is @REDUCTION@\% on this suite. Eliminating two requests
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
@COLD@ seconds cold and @WARM@ seconds warm, excluding the separately recorded
prime and issuance costs. This small descriptive difference does not establish
a reliable net speedup or token savings. The default production plugin probe
executed the body in both write and read/write modes and produced no positive
reuse. Thus the result qualifies the proposed bounded adapter, not deployment
of the native default reuse path. Earlier failed development invocations and
the historical false-reuse observation remain retained.
The measured @PRIME@-second cold prime and @ISSUANCE@-second issuance exceed
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
preparation time is @SEALSEQ@ ms sequential versus @SEALPAR@ ms parallel;
maximum sampled aggregate process RSS rises from @RSSSEQ@ to @RSSPAR@ MiB.
The host is not exclusive, sampled RSS counts shared pages per process, and
these tiny preparation trials measure neither publication latency nor a
whole-system speedup.

\paragraph{Procedure synthesis and stored candidates.}
Native ProcedureCegis adds missing validation operations to a bounded scaffold;
a new evaluation executor performs those checks on concrete integer-sequence
inputs. A development body store reuses candidates only under matching native
request bindings, including actual source-catalog bytes and policy. In eight
units, cold synthesis and stored-candidate arms each complete seven units with
3,883 correct fresh-query decisions and zero false admissions. The unsupported
parity unit yields 554 abstentions in each arm. Stored candidates reduce search
from eight to six synthesis calls and from 29 to 23 tried candidates. However,
a separately frozen post-development fixed-template control matches the same
quality with no synthesis. These cases demonstrate reusable search results,
not an advantage over simple templates. Fresh-process replay, source-binding
changes and scaffold sensitivity are checked independently. This is a new
bounded executor/store integration, not a production-certified procedure
runtime, and uses no model calls.

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
Native total process time is @WORLDNATIVE@ seconds versus @WORLDNONE@ without
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
tests passed. Host elapsed time was @NATIVETIME@ seconds. This is one existing
constructed fixture with a prescribed fault and expected repair, not a held-out
synthesis experiment. Internal benchmark estimates are not counted as measured
token or compute savings. An earlier source profile failed to import the
required composition module and is preserved separately. Solver validation
does not imply kernel reconstruction or all-language correctness.

\paragraph{A real native proof relation.}
The copied native backend was built offline with locked dependencies because
the bundled binary did not implement the source's v3 circuit. Isolated
development keys support a four-leaf Event-DAG Merkle/count relation. Three
actual proofs for counts 1, 2 and 4 verify; eight witness, public-input,
proof and key mutations reject. Primary setup takes @PROOFSETUP@ seconds,
proof generation @PROVEMIN@--@PROVEMAX@ seconds, and verification
@VERIFYMIN@--@VERIFYMAX@ milliseconds; serialized proof JSON is 1,484 bytes.
The raw verifier accepts a different outer root that maps to the same field
element. The evaluation caller's exact-root/count and key/binary checks reject
that alternate statement before dispatch. This boundary is part of the result:
the native relation alone does not bind arbitrary outer metadata. Development
setup is not production trust admission, and a Merkle relation is not proof
that arbitrary tests executed. The v5 pytest-attestation circuit remains
unsupported in this backend.

\paragraph{The original bounded Horn profile.}
The source-built v2 backend also produces and verifies three honest implication
chains of lengths 1, 2 and 4. Setup takes @HORNSETUP@ seconds, proving
@HORNPROVEMIN@--@HORNPROVEMAX@ seconds, and verification
@HORNVERIFYMIN@--@HORNVERIFYMAX@ milliseconds; each proof JSON is 1,700 bytes.
The honest prover rejects the tested incomplete or inconsistent inputs.
When the scalar public inputs remain unchanged, the raw verifier accepts three
changed outer metadata fields; exact statement and source/key checks at the
evaluation caller reject them before dispatch. Honest examples and wrapper
checks do not establish that every satisfying circuit witness corresponds to
the advertised textual axioms. That stronger assurance remains unconfirmed.

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

\paragraph{Remaining system questions.}
These increments establish local mechanisms and expose limitations. They leave
open matched context-substitution efficacy, persistent multi-task quality/cost,
procedure and world-memory utility on real tasks, production reuse, governed
publication, integrated native proof admission, and a held-out comparison with complete
startup, fallback, failed-attempt and recovery accounting.
Additional benchmark recruitment and environment qualification are reported in
Appendix~\ref{sec:incremental-recruitment}; they add no model-quality outcomes.
"""
    proof_begin = text.index(r"\paragraph{A real native proof relation.}")
    proof_end = text.index(r"\paragraph{First combined controller qualification.}")
    proof_details = text[proof_begin:proof_end]
    text = text[:proof_begin] + r"""\paragraph{Native proof production and statement binding.}
The source-built native backend produces three v3 Merkle/count proofs and three
honest v2 implication-chain proofs. For v3, primary setup takes @PROOFSETUP@
seconds, proving @PROVEMIN@--@PROVEMAX@ seconds and verification
@VERIFYMIN@--@VERIFYMAX@ milliseconds. Tested malformed witnesses, proofs and
keys reject. Both profiles require exact outer-statement checks at the caller:
the raw verifier can accept changed displayed metadata when its scalar public
inputs remain unchanged. These are measured bounded circuit relations, not
proofs that arbitrary tests executed or production trust admission. Stronger
v2 textual-binding assurance remains unconfirmed, and the v5 pytest-attestation
profile is unsupported. Appendix~\ref{sec:incremental-native-proof} retains the
separate profiles, mutation observations and v2 costs.

""" + text[proof_end:]
    context_begin = text.index(r"\paragraph{Repository context custody and preparation cost.}")
    context_end = text.index(r"\paragraph{Live context substitution.}")
    context_details = text[context_begin:context_end]
    text = text[:context_begin] + r"""\paragraph{Repository context and preparation.}
Native repository custody, current-source expansion and invalidation checks
pass on bounded XML/pyparsing scopes and on both full declared Requests
inventories (97 files each); these profiles permit zero raw-source omissions.
Five full pyparsing producer processes reach their 600-second deadline. A
subsequent immutable-state identity profile completes full preparation in
@FULLPYPREP@ seconds, followed by a passing independent native consumer; all
302 XML/pyparsing regular files are retained and 22 negative controls pass.
This establishes completion under the bound in one shared-host run. Preparation
is still substantial, and these profiles establish no compression or replicated
speedup. Appendix~\ref{sec:incremental-context-preparation} retains source
scopes, identity/mutation checks, earlier failures and actual costs.

""" + text[context_end:]
    controller_begin = text.index(r"\paragraph{First combined controller qualification.}")
    controller_end = text.index(r"\paragraph{Remaining system questions.}")
    controller_details = text[controller_begin:controller_end]
    text = text[:controller_begin] + r"""\paragraph{Combined controller and native publication.}
The first combined caller exercises context, symbolic reasoning, world memory,
behavioral scoring and a durable effect journal across thirteen authored events,
including three real process interruptions. Two of four initial constructed
repairs pass; two remain residual-pending. A subsequent eight-event profile
adds actual native full/delta publication, stored-source consumption and
pre-CAS recovery after process exit 94. Six events are accepted, one stale
branch loses native CAS and one residual remains pending. Nine invocations
take @JOINEDWALL@ seconds, including 42 actual isolated scorer processes;
24 admission/retrieval replays are included in that total. The native profile
checks integrity, while unsigned local behavioral receipts depend on a trusted
development caller. All five receipt leaves change at each delta, so execution
reuse is not established. Ordinary current-source checks match memory no-op
handling. Both qualifications dispatch zero providers; pending repairs are not
successful token savings. Appendix~\ref{sec:incremental-controller-publication}
retains counts, costs, trust assumptions and failure/recovery boundaries.

""" + text[controller_end:]
    values = {
        "RAW": f"{counts['A_raw']['o200k_base']:,}", "ADD": f"{counts['B_additive']['o200k_base']:,}",
        "SUB": f"{counts['C_substitution']['o200k_base']:,}",
        "ADDINC": f"{-100 * ctx['reductions_relative_to_A']['B_additive']['o200k_base']:.2f}",
        "SUBINC": f"{-100 * ctx['reductions_relative_to_A']['C_substitution']['o200k_base']:.2f}",
        "ASUCCESS": a["successes"], "BSUCCESS": b["successes"], "ACALLS": a["provider_calls"],
        "BCALLS": b["provider_calls"], "ATOKENS": f"{a['total_tokens']:,}", "BTOKENS": f"{b['total_tokens']:,}",
        "REDUCTION": f"{reduction:.2f}", "COLD": f"{reuse['cold_wall_total_seconds']:.3f}",
        "WARM": f"{reuse['warm_wall_total_seconds']:.3f}", "NATIVETIME": f"{native['host_elapsed_seconds']:.3f}"}
    dtokens = dependency["message_content_token_totals"]
    values.update(PROOFSETUP=f"{native_proof['setup_primary_seconds']:.3f}",
                  PROVEMIN=f"{min(native_proof['prove_wall_seconds']):.3f}",
                  PROVEMAX=f"{max(native_proof['prove_wall_seconds']):.3f}",
                  VERIFYMIN=f"{1000*min(native_proof['verify_wall_seconds']):.3f}",
                  VERIFYMAX=f"{1000*max(native_proof['verify_wall_seconds']):.3f}")
    values.update(HORNSETUP=f"{horn['setup_seconds']:.3f}",
                  HORNPROVEMIN=f"{min(r['prove_seconds'] for r in horn['positive_rows']):.3f}",
                  HORNPROVEMAX=f"{max(r['prove_seconds'] for r in horn['positive_rows']):.3f}",
                  HORNVERIFYMIN=f"{1000*min(r['verify_seconds'] for r in horn['positive_rows']):.3f}",
                  HORNVERIFYMAX=f"{1000*max(r['verify_seconds'] for r in horn['positive_rows']):.3f}")
    values.update(WORLDNATIVE=f"{world['totals']['native_memory']['process_elapsed_seconds']:.3f}",
                  WORLDNONE=f"{world['totals']['no_memory']['process_elapsed_seconds']:.3f}")
    values.update(XMLBASE=f"{xml_comparison['baseline_preparation_wall_seconds_excluding_import']:.3f}",
                  XMLOPT=f"{xml_comparison['variant_preparation_wall_seconds_excluding_import']:.3f}")
    values.update(SEALSEQ=f"{1000*seal_timing['arms']['sequential']['median_prepare_seconds']:.2f}",
                  SEALPAR=f"{1000*seal_timing['arms']['parallel']['median_prepare_seconds']:.2f}",
                  RSSSEQ=f"{seal_timing['arms']['sequential']['max_sampled_aggregate_rss_bytes']/2**20:.2f}",
                  RSSPAR=f"{seal_timing['arms']['parallel']['max_sampled_aggregate_rss_bytes']/2**20:.2f}")
    lcraw = live_context["arms"]["raw"]["usage_totals"]
    lccompact = live_context["arms"]["compact"]["usage_totals"]
    values.update(LIVEINPUTRAW=f"{lcraw['input_tokens']:,}",
                  LIVEINPUTCOMPACT=f"{lccompact['input_tokens']:,}",
                  LIVEINPUTRED=f"{100 * live_context['reduction_vs_raw']['input_tokens']:.2f}",
                  LIVETOTALRAW=f"{lcraw['total_tokens']:,}",
                  LIVETOTALCOMPACT=f"{lccompact['total_tokens']:,}",
                  LIVETOTALRED=f"{100 * live_context['reduction_vs_raw']['total_tokens']:.2f}")
    values.update(FULLCAPSULES=f"{dtokens['C_full_native_substitution']['o200k_base']:,}",
                  DEPROW=f"{dtokens['A_raw']['o200k_base']:,}",
                  EQUATIONS=f"{dtokens['D_verified_equations']['o200k_base']:,}",
                  EQUATIONRED=f"{100 * dependency['reduction_vs_raw']['D_verified_equations']['o200k_base']:.2f}",
                  ASTTOKENS=f"{dtokens['E_plain_ast_source']['o200k_base']:,}",
                  PRIME=f"{reuse['prime_wall_seconds']:.3f}",
                  ISSUANCE=f"{reuse['issuance_wall_seconds']:.3f}")
    values["JOINEDWALL"] = f"{joined['controller_elapsed_seconds']:.3f}"
    full_py = full_state_rows["ns-hist-02-pyparsing"]["producer"]
    values.update(FULLXMLPREP=f"{full_state_rows['ns-hist-01-xmltodict']['producer']['preparation_wall_seconds_excluding_import']:.3f}",
                  FULLPYPREP=f"{full_py['preparation_wall_seconds_excluding_import']:.3f}",
                  FULLPYCPU=f"{full_py['preparation_cpu_seconds_excluding_import']:.3f}",
                  FULLPYPROCESS=f"{load(context_prefix + 'results_v12_full_state_identity/ns-hist-02-pyparsing/produce_process.json')['wall_seconds']:.3f}",
                  FULLPYCONSUMER=f"{load(context_prefix + 'results_v12_full_state_identity/ns-hist-02-pyparsing/consume_process.json')['wall_seconds']:.3f}")
    for key, value in values.items():
        text = text.replace("@" + key + "@", str(value))
        proof_details = proof_details.replace("@" + key + "@", str(value))
        context_details = context_details.replace("@" + key + "@", str(value))
        controller_details = controller_details.replace("@" + key + "@", str(value))
    assert all("@" not in s for s in (text, proof_details, context_details, controller_details))
    generated = ROOT / "manuscript/fragments/incremental_results.tex"
    generated.write_text(text)
    shutil.copyfile(generated, snapshot / "incremental_results.tex")
    qualification_text = r"""\section{Additional benchmark qualification}
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

The first Requests node has a separately named ARM environment preserving its
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

The second Requests node subsequently qualifies in a new named ARM profile
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
readiness probes bracket the first node's evaluation, with no automatic retries;
an incomplete grade remains unavailable for repair decisions. All eight
qualification probes pass. The 94-check audit retains 1,175 artifacts; the four
control containers take 87.429894 seconds in total. This qualifies the named
service and its observed controls, without proving the unique cause or remedy
of the previous network failure or stability throughout future test runs.
Candidate and benchmark tests still share the original test process; adversarial
oracle integrity is not established. The second node retains its eight
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

For a later development experiment on the existing pyparsing snapshot, the
current public issue report supplies a concrete objective. Its nine examples
reproduce the reported recursive-whitespace defect on unchanged public source:
eight conform to the reported expectation and one fails. The report is frozen
for that new experiment; its exact bytes at the original base date remain
unverified. A reproduced public example is not complete hidden acceptance.
"""
    qualification_text += r"""
\section{Repository preparation and source custody}
\label{sec:incremental-context-preparation}
""" + context_details
    qualification_text += r"""
\section{Combined controller, publication and recovery}
\label{sec:incremental-controller-publication}
""" + controller_details + r"""
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
"""
    qualification_text += r"""
\section{Native proof profiles and exact statement checks}
\label{sec:incremental-native-proof}
""" + proof_details
    qualification = ROOT / "manuscript/appendix/incremental_qualification_details.tex"
    qualification.write_text(qualification_text)
    shutil.copyfile(qualification, snapshot / "incremental_qualification_details.tex")
    shutil.copyfile(Path(__file__), snapshot / "update_manuscript.py")
    sources.extend([str(generated.relative_to(ROOT)), str(qualification.relative_to(ROOT)), "update_manuscript.py"])
    manifest = {}
    for source in sorted(set(sources)):
        p = ROOT / source
        manifest[source] = hashlib.sha256(p.read_bytes()).hexdigest()
        retained = snapshot / "inputs" / source
        retained.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, retained)
    (snapshot / "evidence_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (snapshot / "checks.json").write_text(json.dumps({"routing_totals_recomputed": True,
        "all_six_live_usage_receipts_checked": True, "paired_residual_requests_identical": True,
        "all_fourteen_saved_outcomes_preserved_on_rescore": True,
        "native_horn_honest_only_boundary_checked": True,
        "historical_cells_relabelled": False, "whole_goal_complete": False}, indent=2) + "\n")
    print(f"Generated working manuscript increment {args.increment}; full research objective remains open.")


if __name__ == "__main__":
    main()
