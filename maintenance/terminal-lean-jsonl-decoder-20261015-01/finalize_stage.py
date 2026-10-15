"""Seal concrete kernel-checked JSONL decoding without promoting task authority."""
import argparse
import json
import os
from pathlib import Path
import runpy

from jsonl_io import ROOT, FALSE, inputs, read, write, wire, sha


def finalize(args):
    from jsonl_verify import validate_result, artifact_check, fault_precondition, verify_copied_inputs, COUNTS
    from run_process import selected
    retained = {}

    def get(name):
        raw = read(ROOT / name, 32 * 1024**2)
        retained[name] = raw
        return json.loads(raw)

    result = get(args.run + '/result.json')
    validate_result(result)
    artifacts = artifact_check(ROOT / args.run, result)
    process = get(args.run + '-process-report.json')
    tests = get(args.regression + '-process-report.json')
    faults = get(args.fault + '-fault-report.json')
    fault_process = get(args.fault + '-process-report.json')
    cold = get(args.cold + '-cold-report.json')
    cold_process = get(args.cold + '-process-report.json')
    if selected() != cold_process['after']:
        raise ValueError('current producers differ from selected cold replay')
    helper = runpy.run_path(str(ROOT.parent / 'terminal-reference-packing-20261014-01' / 'finalize_stage.py'),
                           run_name='public_binding_helpers')
    helper['validate_report_bindings'](run=args.run, result=result,
        result_raw=retained[args.run + '/result.json'], process=process, tests=tests,
        cold=cold, cold_process=cold_process, faults=faults, fault_process=fault_process,
        fault_name=args.fault + '-fault-report.json', fault_raw=retained[args.fault + '-fault-report.json'])
    fault_precondition(args.fault + '-fault-report.json', output=ROOT / args.run,
                       result=result, result_raw=retained[args.run + '/result.json'])
    from scheduler_constraints import validate_scheduler_contract
    from constraint_projections import validate_constraint_projections
    from file_case_run import validate_file_case_run
    from jsonl_lean import build_lean_theory, validate_constraint_lean_evidence
    from jsonl_run import source_records, TASK
    corpus, bodies, instructions, lineage = inputs()
    verify_copied_inputs(ROOT / args.run, bodies=bodies, instructions=instructions)
    from native_structural_ir import verify_structural_ir
    structural = json.loads(artifacts['structural-report.json'])
    verify_structural_ir(repository=ROOT / args.run / 'source-repository',
                         output=ROOT / args.run / 'structural', expected=structural)
    base = json.loads(artifacts['base-materials.json'])
    contract = base['contract']
    validate_scheduler_contract(contract, instruction=instructions[TASK], head=result['native_head'],
                                source_records=source_records(bodies))
    validate_constraint_projections(base['constraint_projections'], contract=contract)
    cases = json.loads(artifacts['file-case-report.json'])
    validate_file_case_run(cases, output=ROOT / args.run / 'file-cases', contract=contract)
    theory = build_lean_theory(contract=contract, cases=cases['derived_cases'])
    if wire(theory) != artifacts['lean-theory.json'] or cases['counts'] != COUNTS:
        raise ValueError('selected theory or case inventory differs from exact observed bytes')
    lean = json.loads(artifacts['lean-evidence.json'])
    validate_constraint_lean_evidence(lean, theory=theory, output=ROOT / args.run / 'lean')
    if len(lean['proved_theorems']) != 17 or lean['positive_compiles'] != 1 or lean['false_controls_rejected'] != 4:
        raise ValueError('complete native finite-model proof inventory required')
    from decoder_witnesses import build_decoder_witnesses
    from decoder_lean import build_decoder_theory, validate_decoder_evidence
    witnesses = build_decoder_witnesses(filecases=cases)
    if wire(witnesses) != artifacts['decoder-witnesses.json'] or witnesses['summary'] != result['decoder_summary']:
        raise ValueError('complete exact byte-to-row witness replay required')
    decoder_theory = build_decoder_theory(witnesses=witnesses)
    if wire(decoder_theory) != artifacts['decoder-theory.json']:
        raise ValueError('total decoder theory differs from the retained exact bytes')
    decoder_evidence = json.loads(artifacts['decoder-evidence.json'])
    validate_decoder_evidence(decoder_evidence, theory=decoder_theory, output=ROOT / args.run / 'decoder-lean')
    if (len(decoder_evidence['proved_theorems']) != 104
            or decoder_theory['finite_model_case_count'] != 16
            or decoder_theory['composed_decoded_model_case_count'] != 16):
        raise ValueError('complete concrete decoder and composed model theorem inventory required')
    inventories = base['inventories']
    if len(inventories) != 4 or any(row['native_coverage']['receipt']['accepted'] is not False for row in inventories):
        raise ValueError('file projection cannot promote original task coverage')
    original_bytes = sum(row['instruction']['bytes'] for row in inventories)
    if original_bytes != 6227:
        raise ValueError('all four complete original instructions required')
    status = {'schema': 'terminal-lean-jsonl-decoder-improvement-status@1',
        'completed_milestone': True, 'selected_run': args.run,
        'selected_result_sha256': sha(retained[args.run + '/result.json']),
        'source_count': 5, 'task_count': 4, 'original_instruction_bytes_retained': original_bytes,
        'typed_contract_clauses': len(contract['clauses']), 'file_case_count': 30,
        'outcome_counts': cases['counts'], 'all_fixture_expectations_matched': True,
        'file_to_model_binding': 'strict_rows_derived_only_from_exact_actual_observed_JSONL_payloads',
        'verification_bracket': 'entry_and_exit_after_candidate_files_already_exist',
        'actual_file_generations_reobserved': True,
        'historical_observations_are_current_capabilities': False,
        'concrete_byte_to_row_correspondence': 'kernel_checked_for_retained_exact_byte_and_row_witnesses_only',
        'decoder_summary': witnesses['summary'],
        'concrete_finite_model_outcomes_kernel_checked': 16,
        'decoded_bytes_to_authored_model_outcomes_kernel_checked': 16,
        'standalone_theory_builder_authenticates_file_origins': False,
        'decoder_proofs': {'positive_compiles': decoder_evidence['positive_compiles'],
            'false_controls_rejected': decoder_evidence['false_controls_rejected'],
            'proved_theorems': decoder_evidence['proved_theorems'],
            'proof_scope': decoder_evidence['proof_scope']},
        'finite_model_proofs': {'positive_compiles': lean['positive_compiles'],
            'false_theorem_controls_rejected': lean['false_controls_rejected'],
            'proved_theorems': lean['proved_theorems'], 'proof_scope': lean['proof_scope']},
        'regression_tests': tests['tests'], 'native_fault_controls': len(faults['controls']),
        'metadata_original_record_counts': result['metadata_original_record_counts'],
        'cold_replay_qualified': True, 'all_original_tasks_still_blocked': True,
        'formal_parser_correctness_proved': False,
        'general_Python_parser_Lean_equivalence_proved': False,
        'Python_checker_equivalent_to_Lean_model_proved': False,
        'FOL_SMT_Lean_interpretation_correspondence_proved': False,
        'supplied_metrics_are_runtime_measurements': False,
        'physical_filesystem_immutability_proved': False, 'original_prompt_interpretation_verified': False,
        'source_body_execution': False, 'new_optimizer_updates': 0,
        'external_provider_calls': 0, 'provider_usage': None,
        'full_supervisor_dispatch_exercised': False, 'original_task_satisfaction': False,
        'source_runtime_equivalence': False, 'source_to_model_equivalence': False,
        'training_convergence_proved': False, **FALSE}
    write(ROOT / 'improvement-status-01.json', status)
    plan = {'schema': 'terminal-codebase-intent-ir-improvement-plan@12',
        'completed_fragment': {
            'scope': 'concrete_exact_JSONL_byte_to_row_kernel_checks_plus_bounded_finite_scheduler_candidate',
            'file_boundary': 'four_exact_owned_request_and_plan_leaves; no hidden benchmark files',
            'strict_parser': 'UTF8, exact schemas, canonical bounded integers, decoded duplicate keys and IDs, exact byte spans',
            'custody': 'descriptor-based actual file identities and bytes, with current generation reobservation',
            'model': 'request and plan rows derived exclusively from retained parsed payloads',
            'decoder': 'total bounded Lean decoding over numeric byte lists and Unicode scalar identifiers, with concrete fixture equalities and Option-based composition into all sixteen authored model outcomes',
            'metrics': 'explicit authored exact rationals; runtime calculation remains pending',
            'proofs': 'Lean kernel checks defined finite-model theorems and seven byte-derived positive cases',
            'metadata': 'fresh DuckDB/DuckLake hydration and fresh-process reconstruction of all metadata families',
            'original_instructions': 'all four originals and their native coverage rejections retained'},
        'evidence_summary': {'file_case_count': 30, 'outcome_counts': cases['counts'],
            'regression_tests': tests['tests'], 'native_fault_controls': len(faults['controls']),
            'finite_model_theorems': len(lean['proved_theorems']),
            'decoder_summary': witnesses['summary'],
            'decoder_theorems': len(decoder_evidence['proved_theorems']),
            'decoder_false_controls_rejected': decoder_evidence['false_controls_rejected']},
        'remaining_semantic_bridges': [
            {'order': 1, 'work': 'Generalize concrete decoder correspondences to supported-domain parser and logic-lowering theorems.',
             'acceptance': 'Prove the decoder sound and complete for an explicit bounded JSONL grammar, including byte, line, ID and row limits. Relate the actual Python parser/checker to Lean semantics and typed FOL/SMT. Concrete fixture equalities do not establish a universal implementation theorem.'},
            {'order': 2, 'work': 'Bind metric values to independently checked source-derived calculations.',
             'acceptance': 'Specify cost, padding, latency and sequential-time formulas and source dependencies; resolve bucket-local batch IDs, length domains, generation rounding, declared shapes, strict thresholds and floating-point behavior.'},
            {'order': 3, 'work': 'Connect the file validation bracket to an actual supervised candidate execution.',
             'acceptance': 'Observe requests before dispatch and plans after completion under the native task/grant/claim lifecycle; bind freshness to codebase owner and actual file generations, without treating observations as proof of physical immutability.'},
            {'order': 4, 'work': 'Complete original IntentIR coverage and dependency-aware proof-cache admission.',
             'acceptance': 'Every original acceptance condition is represented and supported, or remains an explicit blocking residual. No parser receipt, candidate contract or finite-model theorem can waive source/runtime correspondence.'},
            {'order': 5, 'work': 'Measure semantic capsules and code minification with paired official task outcomes and provider tokens.',
             'acceptance': 'Same model, task and starting state; include setup, history, retrieval, tool outputs, retries and cache usage. Report task success and total tokens separately from local byte compression.'},
            {'order': 6, 'work': 'Train and evaluate codebase_IR with explicit partitions and conditional convergence assumptions.',
             'acceptance': 'No held-out fitting; compare simple baselines, reconstruction, retrieval and downstream tasks. State optimization assumptions and empirical stopping criteria; finite-model proofs do not establish neural convergence.'}],
        'contract_interpretation_and_runtime_correspondence_unproved': True,
        'source_metric_findings': {
            'source_prefill_and_decode_context': 'aligned request prompt lengths, not declared plan shape.seq_align',
            'declared_shapes': 'affect compilation cost and latency; unique-shape compilation resets per bucket',
            'compilation_latency': 'first request in lexicographically first batch for each shape; request order matters',
            'zero_sequence_shape': 'skips compilation cost but can still receive compilation latency',
            'numeric_residual': 'source binary64 constants, division and summation differ from ideal rational arithmetic',
            'required_profile': 'default constants and granularity64 must be explicitly bound, not inferred from the model'},
        'supervisor_boundary_findings': {
            'existing_context_permit_authorizes_JSONL_writer': False,
            'next_execution_slice': 'distinct signed authored candidate scope with live claim and request-only predispatch observation',
            'full_admitted_runtime_prerequisites': 'genuine Quack owner, route-sealed typed task source and installed isolated worker boundary'},
        'all_original_task_requirements_pending': True, 'full_task_satisfaction': False, **FALSE}
    write(ROOT / 'improvement-plan-v12.json', plan)
    verify_copied_inputs(ROOT / args.run, bodies=bodies, instructions=instructions)
    verify_structural_ir(repository=ROOT / args.run / 'source-repository',
                         output=ROOT / args.run / 'structural', expected=structural)
    if artifact_check(ROOT / args.run, result) != artifacts:
        raise ValueError('selected evidence changed during finalization')
    validate_file_case_run(cases, output=ROOT / args.run / 'file-cases', contract=contract)
    fault_precondition(args.fault + '-fault-report.json', output=ROOT / args.run,
                       result=result, result_raw=retained[args.run + '/result.json'])
    if selected() != cold_process['after'] or inputs()[3] != lineage:
        raise ValueError('producer or input lineage changed during finalization')
    for name, raw in retained.items():
        if read(ROOT / name, 32 * 1024**2) != raw:
            raise ValueError('selected report changed during finalization')
    names = []
    for basepath, dirs, files in os.walk(ROOT, followlinks=False):
        dirs[:] = [name for name in dirs if name not in {'.git', '__pycache__', '.pytest_cache'}]
        for name in dirs + files:
            if (Path(basepath) / name).is_symlink():
                raise ValueError('unexpected public evidence symlink')
        for name in files:
            relative = (Path(basepath) / name).relative_to(ROOT).as_posix()
            if relative not in {'evidence-manifest.json', 'seal-config-01.json'}:
                names.append(relative)
    names.append('seal-config-01.json')
    config = {'schema': 'terminal-codebase-ir-evidence-selection@1', 'root': str(ROOT), 'files': sorted(names),
        'selection_scope': 'owned_public_exact_Lean_JSONL_decoder_and_finite_model_evidence',
        'excluded_git_metadata': True, 'symlink_targets_opened': False, 'proof_authority': False}
    write(ROOT / 'seal-config-01.json', config)
    from seal_training_evidence import seal
    manifest = seal(config, ROOT / 'evidence-manifest.json')
    seal(config, ROOT / 'evidence-manifest.json', verify=True)
    print(json.dumps({'sealed': True, 'files': manifest['file_count'], 'bytes': manifest['total_bytes'],
        'tests': tests['tests']['tests'], 'file_cases': 30, 'finite_model_theorems': 17,
        'decoder_theorems': len(decoder_evidence['proved_theorems']),
        'manifest_sha256': sha(read(ROOT / 'evidence-manifest.json', 1024**2))}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('run', 'regression', 'fault', 'cold'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    for value in vars(args).values():
        if Path(value).name != value or value in {'.', '..'}:
            raise ValueError('owned selected names required')
    finalize(args)
