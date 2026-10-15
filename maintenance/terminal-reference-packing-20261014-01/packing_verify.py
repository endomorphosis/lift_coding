"""Cold owner, metadata, complete context, codec and scripted token-cost replay."""
import argparse
import json
from pathlib import Path
import resource
from packing_io import ROOT, FALSE, inputs, read, write, wire, sha
from packing_run import POLICY, FILES, build_contexts, measure_contexts, check_lease

def artifact_check(output, result):
    if [v['relative_path'] for v in result['artifact_pins']] != sorted(FILES):
        raise ValueError('complete selected artifact scope required')
    for row in result['artifact_pins']:
        if set(row) != {'relative_path', 'bytes', 'sha256'}:
            raise ValueError('closed artifact pin required')
        raw = read(output/row['relative_path'], 32*1024**2)
        if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
            raise ValueError('selected artifact changed')

def result_check(result):
    fields = {'schema', 'completed', 'policy', 'native_head', 'source_count', 'task_count',
        'native_capsule_inventory', 'metadata_original_record_counts', 'context_compilations',
        'exact_context_variant_roundtrips', 'local_script_pairs', 'artifact_pins', 'provider_invocations',
        'new_optimizer_updates', 'new_prover_invocations', 'source_body_execution',
        'planning_requirements_all_unresolved', 'seconds', 'peak_rss_kib', *FALSE}
    if type(result) is not dict or set(result) != fields or result['schema'] != 'terminal-reference-packing-experiment@1':
        raise ValueError('closed packing result scope required')
    if result['completed'] is not True or result['policy'] != POLICY:
        raise ValueError('complete packing policy required')
    if any(result.get(k) is not False for k in FALSE) or result['source_body_execution'] is not False:
        raise ValueError('unobserved provider, runtime or proof authority')
    counters = {'source_count': 5, 'task_count': 4, 'context_compilations': 4,
        'exact_context_variant_roundtrips': 12, 'local_script_pairs': 36,
        'provider_invocations': 0, 'new_optimizer_updates': 0, 'new_prover_invocations': 0}
    if any(type(result[k]) is not int or result[k] != v for k,v in counters.items()):
        raise ValueError('exact local work counters required')
    if result['planning_requirements_all_unresolved'] is not True:
        raise ValueError('unresolved instruction frontier required')

def validate_fault_report(fault, *, result, result_raw):
    """Validate the complete declared fault data against the selected run.

    This establishes report consistency only. It neither authenticates receipt
    origin nor observes an owner. Retained producer/process provenance and the
    separate live native replay remain necessary.
    """
    def require(ok, message):
        if not ok:
            raise ValueError(message)

    require(type(result) is dict and type(result_raw) is bytes,
            'caller selected result data and exact bytes required')
    require(type(fault) is dict and fault.get('schema') == 'terminal-reference-packing-fault-controls@1'
            and fault.get('qualified') is True, 'qualified preceding fault controls required')
    # Keep custody joins before closed scope validation: a report from another
    # result is rejected as such, even if it also lacks the current full schema.
    require(fault.get('selected_run') == result.get('selected_run', ''),
            'preceding fault report selected run differs')
    require(fault.get('selected_result_sha256') == sha(result_raw)
            and wire(fault.get('native_head')) == wire(result.get('native_head')),
            'preceding faults must bind exact result and native head')

    fields = {'schema', 'qualified', 'selected_run', 'selected_result_sha256', 'native_head',
        'selected_artifact_pins_sha256', 'packet_controls', 'native_owner_controls',
        'pure_packet_negative_controls', 'positive_exact_variant_roundtrips',
        'selected_run_artifacts_unchanged', 'source_body_execution', 'provider_invocations',
        'optimizer_updates', 'prover_invocations', *FALSE}
    require(set(fault) == fields, 'closed preceding fault report scope required')
    require(type(fault['selected_run']) is str and fault['selected_run']
            and Path(fault['selected_run']).name == fault['selected_run']
            and fault['selected_run'] not in {'.', '..'}, 'canonical selected fault run required')
    require(fault['selected_artifact_pins_sha256'] == sha(wire(result['artifact_pins'])),
            'preceding faults must bind exact selected artifact pins')
    require(fault['selected_run_artifacts_unchanged'] is True,
            'preceding fault artifact stability not qualified')
    require(all(fault[key] is False for key in FALSE) and fault['source_body_execution'] is False,
            'preceding faults promote unobserved authority')
    counters = {'pure_packet_negative_controls': 28, 'positive_exact_variant_roundtrips': 12,
                'provider_invocations': 0, 'optimizer_updates': 0, 'prover_invocations': 0}
    require(all(type(fault[key]) is int and fault[key] == expected for key, expected in counters.items()),
            'exact preceding fault work counters required')

    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    require(type(fault['native_head']) is dict, 'complete typed preceding fault head required')
    head = CodebaseHead.from_dict(fault['native_head'])
    require(wire(head.to_dict()) == wire(fault['native_head']), 'canonical preceding fault head required')

    task_ids = {'headless-terminal', 'llm-inference-batching-scheduler',
                'feal-differential-cryptanalysis', 'break-filter-js-from-html'}
    expected_controls = {
        'rechecksummed_promoted_provider_claim': 'ReferenceCodecError',
        'rechecksummed_changed_decoded_hash': 'ReferenceCodecError',
        'reencoded_changed_lift_slot_hash': 'NestedContextError',
        'reencoded_changed_full_instruction': 'NestedContextError',
        'reencoded_weakened_native_requiredness': 'NestedContextError',
        'reencoded_changed_restoration_guidance': 'NestedContextError',
        'caller_context_changed_after_packing': 'ValueError',
    }
    packets = fault['packet_controls']
    require(type(packets) is list and len(packets) == 4, 'all four public task fault packets required')
    observed_tasks = set()
    for packet in packets:
        packet_fields = {'task_id', 'positive_byte_exact_variants', 'controls', 'codec_processes_are_pure_data', *FALSE}
        require(type(packet) is dict and set(packet) == packet_fields, 'closed public task fault packet required')
        require(type(packet['task_id']) is str and packet['task_id'] in task_ids
                and packet['task_id'] not in observed_tasks, 'complete unique public task fault scope required')
        observed_tasks.add(packet['task_id'])
        require(type(packet['positive_byte_exact_variants']) is int and packet['positive_byte_exact_variants'] == 3,
                'exact three positive variant restorations per task required')
        require(packet['codec_processes_are_pure_data'] is True and all(packet[key] is False for key in FALSE),
                'task packet faults must remain pure data without authority')
        controls = packet['controls']
        require(type(controls) is list and len(controls) == 7, 'seven named packet refusals per public task required')
        observed_controls = set()
        for control in controls:
            require(type(control) is dict and set(control) == {'control', 'refused', 'error_class', 'message', *FALSE},
                    'closed named packet fault refusal required')
            name = control['control']
            require(type(name) is str and name in expected_controls and name not in observed_controls,
                    'complete unique named packet refusal scope required')
            observed_controls.add(name)
            require(control['refused'] is True and control['error_class'] == expected_controls[name],
                    'expected actual packet refusal class required')
            require(type(control['message']) is str and 0 < len(control['message'].encode('utf-8')) <= 4096,
                    'bounded packet refusal diagnostic required')
            require(all(control[key] is False for key in FALSE), 'packet refusal must not promote authority')
        require(observed_controls == set(expected_controls), 'complete named packet refusal inventory required')
    require(observed_tasks == task_ids, 'complete public task fault inventory required')

    owner = fault['native_owner_controls']
    owner_fields = {'native_entry_observation_passed', 'mutation_inside_callback',
        'private_provisional_candidate_created', 'candidate_returned_to_caller',
        'stale_source_exit_error_class', 'stale_source_exit_error_message',
        'exact_original_source_restored', 'baseline_native_owner_reobserved_after_restore',
        'wrong_full_head_error_class', 'wrong_full_head_error_message',
        'wrong_full_head_callback_entered', 'native_head_unchanged', 'owner_head_update_performed', *FALSE}
    require(type(owner) is dict and set(owner) == owner_fields, 'closed native owner fault control scope required')
    require(all(owner[key] is True for key in ('native_entry_observation_passed', 'mutation_inside_callback',
        'private_provisional_candidate_created', 'exact_original_source_restored',
        'baseline_native_owner_reobserved_after_restore')), 'preceding native source entry/exit restoration not qualified')
    require(all(owner[key] is False for key in ('candidate_returned_to_caller', 'wrong_full_head_callback_entered',
        'owner_head_update_performed', *FALSE)), 'preceding native owner fault escaped or promoted authority')
    require(owner['stale_source_exit_error_class'] == 'StaleCodebaseError'
            and owner['wrong_full_head_error_class'] == 'StaleCodebaseError', 'actual native stale-source and stale-head refusals required')
    for key in ('stale_source_exit_error_message', 'wrong_full_head_error_message'):
        require(type(owner[key]) is str and 0 < len(owner[key].encode('utf-8')) <= 4096,
                'bounded native stale refusal diagnostic required')
    require(type(owner['native_head_unchanged']) is dict
            and wire(owner['native_head_unchanged']) == wire(head.to_dict()),
            'native head changed during preceding faults')

def fault_precondition(name, result, result_raw):
    if not name or Path(name).name != name or name in {'.','..'}:
        raise ValueError('local preceding fault report required')
    raw=read(ROOT/name,1024**2);fault=json.loads(raw)
    validate_fault_report(fault, result=result, result_raw=result_raw)
    if wire(fault) != raw:
        raise ValueError('canonical preceding fault report bytes required')
    return raw,{'relative_path':name,'bytes':len(raw),'sha256':sha(raw)}

def verify(output, fault_report):
    resource.setrlimit(resource.RLIMIT_CPU, (240,240))
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32*1024**2,32*1024**2))
    if output.resolve() != output or output.parent != ROOT:
        raise ValueError('owned canonical selected run required')
    result_raw = read(output/'result.json'); result = json.loads(result_raw)
    result_check(result); artifact_check(output, result)
    fault_raw,fault_pin=fault_precondition(fault_report,{**result,'selected_run':output.name},result_raw)
    corpus,bodies,instructions,lineage = inputs()
    if wire(corpus) != read(output/'corpus-manifest.json') or wire(lineage) != read(output/'lineage.json'):
        raise ValueError('sealed selected input lineage differs')
    for task in corpus['tasks']:
        if read(output/'instructions'/task['task_id']/'instruction.md',8192) != instructions[task['task_id']]:
            raise ValueError('copied full task instruction differs')
    structural = json.loads(read(output/'structural-report.json'))
    from native_structural_ir import verify_structural_ir, _scheduler
    verify_structural_ir(repository=output/'source-repository', output=output/'structural', expected=structural)
    for s in structural['sources']:
        if read(output/'source-repository'/s['path'],8192) != bodies[s['path']]:
            raise ValueError('current original source differs')
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from native_capsules import verify_native_capsules
    from capsule_codec import build_capsule_codec
    from token_cost_review import load_tokenizer
    from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as metadata_api
    from benchmarks.agent_supervisor.container_coding.terminal_codebase_supervisor_fixture import reconstruct_terminal_codebase_metadata_records
    from packing_metadata import build_records
    from metadata_projections import _wire as metadata_wire
    native = json.loads(read(output/'native-capsules.json'))
    codecs = json.loads(read(output/'codec-views.json'))
    metadata = json.loads(read(output/'metadata-report.json'))
    with _scheduler().acquire(ResourceLane.VALIDATION, cpu_slots=1, memory_mb=1024, child_process_slots=1,
            timeout=30, request_id='terminal-reference-packing:cold') as lease:
        check_lease(lease)
        verify_native_capsules(CodebaseIRManifest.from_dict(structural['manifest']), CodebaseHead.from_dict(structural['head']), native)
        for s in structural['sources']:
            for arm in ['minified','aliased']:
                regenerated = build_capsule_codec(bodies[s['path']],s['path'],s['source_cid'],structural['head'],aliases=arm=='aliased')
                if codecs[s['path']][arm] != regenerated: raise ValueError('complete source codec differs')
        tokenizer, descriptor = load_tokenizer(json.loads(read(output/'tokenizer.json')))
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE, cpu_slots=1, memory_mb=256, child_process_slots=1,
                timeout=20, request_id='terminal-reference-packing:cold-metadata') as child:
            check_lease(child)
            reopened = metadata_api.validate_codebase_ir_metadata(output=output/'metadata',expected=metadata['native_metadata'],fresh_process=True)
        restored = {family:[json.loads(line)['payload'] for line in read(output/'metadata'/export['relative_path'],32*1024**2).splitlines()]
            for family,export in reopened['exports'].items()}
        recovered = reconstruct_terminal_codebase_metadata_records(restored)
        records = build_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,native=native,codecs=codecs,lineage=lineage)
        if metadata_wire(recovered) != metadata_wire(records) or sha(metadata_wire(recovered)) != metadata['records_sha256']:
            raise ValueError('complete DuckDB/DuckLake metadata differs')
        contexts = build_contexts(output=output,structural=structural,corpus=corpus,instructions=instructions,native=native,
            metadata=metadata,tokenizer=tokenizer,descriptor=descriptor,lease=lease)
        if wire(contexts) != read(output/'contexts.json'): raise ValueError('native full context or deterministic codec replay differs')
        if wire(measure_contexts(contexts,descriptor)) != read(output/'costs.json'):
            raise ValueError('complete scripted token ledger differs')
    if result['native_head'] != structural['head'] or result['native_capsule_inventory'] != native['complete_inventory'] or result['metadata_original_record_counts'] != metadata['family_counts']:
        raise ValueError('headline source/head/metadata bindings differ')
    verify_structural_ir(repository=output/'source-repository',output=output/'structural',expected=structural)
    if inputs()[3] != lineage or read(output/'result.json') != result_raw:
        raise ValueError('selected result or lineage changed during replay')
    artifact_check(output,result)
    if read(ROOT/fault_report,1024**2) != fault_raw:
        raise ValueError('preceding fault report changed during positive replay')
    return {'schema':'terminal-reference-packing-cold-replay@1','qualified':True,
        'selected_run':output.name,'selected_result_sha256':sha(result_raw),
        'selected_native_head':structural['head'],'selected_artifact_pins_sha256':sha(wire(result['artifact_pins'])),
        'preceding_fault_report':fault_pin,'qualified_faults_verified_before_positive_replay':True,
        'genuine_current_owner_before_and_after':True,'complete_duckdb_ducklake_reopened':True,
        'all_12_variants_restore_exact_native_contexts':True,'all_36_cost_scripts_reproduced':True,
        'reference_optimizer_selection_uses_whole_envelope_offline_bpe':True,
        'native_dictionary_selection_uses_utf8_bytes':True,'provider_usage':None, **FALSE}

if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--run',required=True); parser.add_argument('--report',required=True)
    parser.add_argument('--fault-report',required=True); args=parser.parse_args()
    for name in [args.run,args.report,args.fault_report]:
        if not name or Path(name).name != name or name in {'.','..'}: raise ValueError('local names required')
    report=verify(ROOT/args.run,args.fault_report); write(ROOT/args.report,report); print(json.dumps({'qualified':True,'pairs':36}))
