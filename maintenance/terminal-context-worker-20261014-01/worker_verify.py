"""Cold current-owner replay and retained worker-data validation, without spawn.

Retained process births and consumer captures are historical observations. Their
data and artifact integrity do not confer current head, proof or task authority.
Current source is checked separately through the genuine native owner.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path, PurePosixPath
import re
import resource
import stat

from worker_io import ROOT, FALSE, inputs, read, write, wire, sha
from worker_run import POLICY, FILES, MODES, build_contexts, make_request, check_lease

TASKS = {'headless-terminal', 'llm-inference-batching-scheduler',
         'feal-differential-cryptanalysis', 'break-filter-js-from-html'}
WORKER_LEAVES = {'request.json', 'stdout.json', 'stderr.log', 'router-allocation.duckdb',
                 'router-allocation.duckdb.wal'}
MANDATORY_LEAVES = WORKER_LEAVES - {'router-allocation.duckdb.wal'}
MAX_ARTIFACT_BYTES = 32*1024**2
MAX_TOTAL_ARTIFACT_BYTES = 512*1024**2


def need(condition, message):
    if not condition:
        raise ValueError(message)


def _exact_json(value):
    return wire(value)


def _head(value):
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    need(type(value) is dict, 'complete native head object required')
    head = CodebaseHead.from_dict(value)
    need(wire(head.to_dict()) == wire(value), 'canonical complete native head required')
    return head


def validate_result(result):
    """Check the closed declared result; owner/worker replay is still required."""
    fields = {'schema', 'completed', 'policy', 'native_head', 'source_count', 'task_count',
        'sessions', 'worker_child_invocations', 'local_consumer_calls',
        'actual_external_provider_invocations', 'new_optimizer_updates', 'new_prover_invocations',
        'source_body_execution', 'metadata_original_record_counts', 'native_capsule_inventory',
        'artifact_pins', 'seconds', 'peak_rss_kib', *FALSE}
    need(type(result) is dict and set(result) == fields and
         result['schema'] == 'terminal-generic-context-worker-experiment@1', 'closed worker result scope required')
    need(result['completed'] is True and wire(result['policy']) == wire(POLICY), 'complete worker policy required')
    need(all(result[key] is False for key in FALSE) and result['source_body_execution'] is False,
         'worker result promotes unobserved source, provider or proof authority')
    counters = {'source_count': 5, 'task_count': 4, 'sessions': 12, 'worker_child_invocations': 48,
        'local_consumer_calls': 48, 'actual_external_provider_invocations': 0,
        'new_optimizer_updates': 0, 'new_prover_invocations': 0}
    need(all(type(result[key]) is int and result[key] == value for key, value in counters.items()),
         'exact worker result work counters required')
    _head(result['native_head'])
    need(type(result['seconds']) in {int, float} and math.isfinite(result['seconds']) and result['seconds'] >= 0
         and type(result['peak_rss_kib']) is int and result['peak_rss_kib'] >= 0,
         'finite nonnegative worker process diagnostics required')
    for key in ('metadata_original_record_counts', 'native_capsule_inventory'):
        value = result[key]
        need(type(value) is dict and value and all(type(name) is str and type(count) is int and count >= 0
             for name, count in value.items()), 'closed nonnegative metadata/capsule counter map required')
    _pins(result['artifact_pins'])


def _worker_path(name, *, directory=False):
    need(type(name) is str and '\\' not in name and all(ord(c) >= 32 for c in name),
         'canonical artifact path text required')
    path = PurePosixPath(name)
    need(not path.is_absolute() and str(path) == name and
         not any(part in {'.', '..', '.git'} for part in path.parts), 'canonical relative artifact path required')
    parts = path.parts
    need(parts and parts[0] == 'workers', 'closed worker artifact prefix required')
    need(len(parts) <= (4 if directory else 5), 'closed worker artifact depth required')
    if len(parts) >= 2:
        need(parts[1] in TASKS, 'unknown public worker task path')
    if len(parts) >= 3:
        need(parts[2] in MODES, 'unknown worker mode path')
    if len(parts) >= 4:
        need(re.fullmatch(r'turn-[0-3]', parts[3]), 'unknown worker turn path')
    if not directory:
        need(len(parts) == 5 and parts[4] in WORKER_LEAVES, 'unknown worker artifact leaf')
    return path


def _pins(pins):
    need(type(pins) is list and len(FILES)+48*4 <= len(pins) <= len(FILES)+48*5,
         'complete bounded worker artifact pin inventory required')
    names, total = [], 0
    for row in pins:
        need(type(row) is dict and set(row) == {'relative_path', 'bytes', 'sha256'}, 'closed worker artifact pin required')
        name = row['relative_path']
        need(type(name) is str and name not in names, 'duplicate or nontext artifact path')
        if name not in FILES:
            _worker_path(name)
        need(type(row['bytes']) is int and 0 <= row['bytes'] <= MAX_ARTIFACT_BYTES,
             'bounded exact artifact byte count required')
        need(type(row['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', row['sha256']), 'exact artifact SHA-256 required')
        total += row['bytes']
        need(total <= MAX_TOTAL_ARTIFACT_BYTES, 'total worker artifact byte bound exceeded')
        names.append(name)
    need(names == sorted(names) and set(FILES) <= set(names), 'complete sorted core/worker artifact inventory required')
    for task in TASKS:
        for mode in MODES:
            for step in range(4):
                prefix = f'workers/{task}/{mode}/turn-{step}/'
                need({prefix+leaf for leaf in MANDATORY_LEAVES} <= set(names), 'all referenced worker files must be pinned')
    return names


def artifact_check(output, result):
    """Acquire the complete closed artifact inventory, including empty stderr."""
    output = Path(output)
    need(output.is_absolute() and output.resolve(strict=True) == output and output.is_dir(), 'canonical owned output required')
    names = _pins(result['artifact_pins'])
    workers = output/'workers'
    need(workers.is_dir() and workers.resolve(strict=True) == workers, 'canonical existing worker subtree required')
    actual, visited = set(), 0
    for path in workers.rglob('*'):
        visited += 1
        need(visited <= 1024, 'worker subtree inventory bound exceeded')
        relative = path.relative_to(output).as_posix()
        info = path.lstat()
        need(path.resolve(strict=True) == path and not stat.S_ISLNK(info.st_mode), 'worker artifact symlink refused')
        if stat.S_ISDIR(info.st_mode):
            _worker_path(relative, directory=True)
        else:
            _worker_path(relative)
            need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, 'single-link regular worker leaf required')
            actual.add(relative)
    need(actual == {name for name in names if name.startswith('workers/')}, 'pinned worker scope differs from actual leaf inventory')
    acquired = {}
    from worker_capture import _read
    for row in result['artifact_pins']:
        path = output/row['relative_path']
        raw = _read(path, MAX_ARTIFACT_BYTES, empty=row['bytes'] == 0)
        need(len(raw) == row['bytes'] and sha(raw) == row['sha256'], 'selected worker artifact changed')
        acquired[row['relative_path']] = raw
    return acquired


def validate_capture(*, output_dir, request, capture, artifacts, expected_selection=None, expected_manifest=None):
    """Replay a retained capture's data joins without checking a PID as live."""
    import worker_capture as native
    import context_worker
    fields = {'schema', 'request_sha256', 'request_bytes', 'native_dispatch', 'observation',
        'output_artifacts', 'current_head_observation_owned_by_caller', 'provider_usage',
        'actual_external_provider_invocations', *native.FALSE}
    need(type(capture) is dict and set(capture) == fields and capture['schema'] == native.SCHEMA,
         'closed retained native worker capture required')
    need(all(capture[key] is False for key in native.FALSE) and capture['provider_usage'] is None
         and type(capture['actual_external_provider_invocations']) is int
         and capture['actual_external_provider_invocations'] == 0
         and capture['current_head_observation_owned_by_caller'] is True, 'capture promotes unobserved authority')
    request_raw = native._request(request)
    need(artifacts['request.json'] == request_raw and type(capture['request_bytes']) is int
         and capture['request_bytes'] == len(request_raw) and capture['request_sha256'] == sha(request_raw),
         'retained complete worker request differs')
    need(artifacts['stderr.log'] == b'', 'retained worker stderr is not empty')
    if expected_selection is None:
        expected_selection, expected_manifest = context_worker.prepare_request(request)
    observation = native._observation(artifacts['stdout.json'], request, request_raw, output_dir,
                                      expected_selection, expected_manifest)
    need(wire(observation) == wire(capture['observation'])
         and wire(observation['selection']) == wire(expected_selection)
         and wire(observation['selected_message_manifest']) == wire(expected_manifest),
         'retained child stdout/selected messages differ from deterministic replay')
    consumer = observation['consumer']
    need(wire(consumer['claims']) == wire(native.CONSUMER_CLAIMS), 'consumer claim scalar types differ')
    need(all(type(consumer[key]) is int for key in ('input_bytes', 'input_local_tokens', 'consumer_calls')),
         'exact consumer byte/token/call integers required')
    need(set(consumer['allocation_store']) == {'path', 'profile', 'slots_before', 'slots_after',
         'mutable_rows_before', 'mutable_rows_after'}, 'closed owned allocation-store capture required')
    files = capture['output_artifacts']
    need(type(files) is list and [row.get('relative_path') for row in files] == ['request.json', 'stdout.json', 'stderr.log'],
         'complete fixed worker output custody required')
    for row in files:
        need(type(row) is dict and set(row) == {'relative_path', 'bytes', 'sha256'}, 'closed worker output pin required')
        raw = artifacts[row['relative_path']]
        need(type(row['bytes']) is int and row['bytes'] == len(raw) and row['sha256'] == sha(raw),
             'worker output artifact custody differs')
    dispatch = capture['native_dispatch']
    need(type(dispatch) is dict and set(dispatch) == {'module', 'method', 'path', 'sha256', 'actual_child_birth',
        'actual_process_invoked', 'native_shared_parent_lease_used', 'native_child_lease', 'inherited_environment', 'shell'},
        'closed historical native dispatch description required')
    need(dispatch['module'] == 'ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime'
         and dispatch['method'] == 'run_process_group_stream' and dispatch['path'] == str(native.RUNTIME_SOURCE)
         and dispatch['sha256'] == sha(native._read(native.RUNTIME_SOURCE, 256_000)),
         'retained native launcher source identity differs')
    need(dispatch['actual_process_invoked'] is True and dispatch['native_shared_parent_lease_used'] is True
         and dispatch['inherited_environment'] is False and dispatch['shell'] is False,
         'historical native dispatch boundary differs')
    lease = dispatch['native_child_lease']
    need(type(lease) is dict and set(lease) == {'cpu_slots', 'memory_mb', 'child_process_slots'}
         and all(type(lease[key]) is int and lease[key] == value for key, value in
             {'cpu_slots': 1, 'memory_mb': 256, 'child_process_slots': 1}.items()), 'retained native child reservation differs')
    birth = dispatch['actual_child_birth']
    need(type(birth) is dict and set(birth) == {'pid', 'start_time_ticks'}
         and all(type(birth[key]) is int and birth[key] > 0 for key in birth), 'bounded historical child birth required')
    return observation, (birth['pid'], birth['start_time_ticks'])


def validate_deliveries(*, output, contexts, deliveries, descriptor, artifacts, head):
    """Validate every retained call in its actual selected-history sequence."""
    import worker_capture
    fields = {'schema', 'sessions', 'actual_low_level_native_worker_dispatches', 'actual_local_router_consumer_calls',
              'actual_external_provider_invocations', 'provider_usage', 'source_body_execution', *FALSE}
    need(type(deliveries) is dict and set(deliveries) == fields
         and deliveries['schema'] == 'terminal-generic-context-worker-deliveries@1', 'closed worker deliveries required')
    need(all(deliveries[key] is False for key in FALSE) and deliveries['provider_usage'] is None
         and deliveries['source_body_execution'] is False, 'deliveries promote unobserved authority')
    for key, count in {'actual_low_level_native_worker_dispatches':48, 'actual_local_router_consumer_calls':48,
                      'actual_external_provider_invocations':0}.items():
        need(type(deliveries[key]) is int and deliveries[key] == count, 'exact retained delivery counters required')
    tasks = {task['task_id']: task for task in contexts['tasks']}
    need(set(tasks) == TASKS and len(contexts['tasks']) == 4, 'complete public context task inventory required')
    sessions = deliveries['sessions']
    need(type(sessions) is list and len(sessions) == 12, 'exact twelve worker sessions required')
    seen, births, retained = set(), set(), 0
    for session in sessions:
        need(type(session) is dict and set(session) == {'task_id', 'delivery_mode', 'calls',
            'actual_local_consumer_calls', 'scripted_followups', 'model_outputs_produced', *FALSE}, 'closed worker session required')
        key = (session['task_id'], session['delivery_mode'])
        need(key[0] in TASKS and key[1] in MODES and key not in seen, 'complete unique task/mode session scope required')
        seen.add(key)
        need(type(session['actual_local_consumer_calls']) is int and session['actual_local_consumer_calls'] == 4
             and session['scripted_followups'] is True and session['model_outputs_produced'] is False
             and all(session[name] is False for name in FALSE), 'session promotes an unevaluated model behavior')
        calls = session['calls']
        need(type(calls) is list and len(calls) == 4, 'four ordered worker calls per session required')
        previous = []
        for step, call in enumerate(calls):
            need(type(call) is dict and set(call) == {'step', 'retry_of', 'request', 'capture', 'owner_current_before_and_after'},
                 'closed ordered worker call required')
            need(type(call['step']) is int and call['step'] == step and call['owner_current_before_and_after'] is True
                 and (call['retry_of'] is None if step != 3 else type(call['retry_of']) is int and call['retry_of'] == 2),
                 'worker call order/retry/current-owner declaration differs')
            expected = make_request(tasks[key[0]], key[1], step, descriptor, previous)
            need(wire(call['request']) == wire(expected) and wire(expected['expected_head']) == wire(head),
                 'retained worker request/head/history differs from deterministic current context')
            request = call['request']
            relative = f'workers/{key[0]}/{key[1]}/turn-{step}'
            directory = output/relative
            leaf = {name: artifacts[relative+'/'+name] for name in MANDATORY_LEAVES}
            observation, birth = validate_capture(output_dir=directory, request=request, capture=call['capture'], artifacts=leaf)
            need(birth not in births, 'historical child birth reused across retained dispatches')
            births.add(birth)
            previous = observation['selected_message_manifest']
            retained += 1
    need(seen == {(task, mode) for task in TASKS for mode in MODES} and retained == 48,
         'complete retained native worker inventory required')
    return {'retained_calls': retained, 'sessions': len(seen), 'distinct_historical_births': len(births),
            'new_worker_children_spawned': 0, 'historical_births_are_current_authority': False}


def fault_precondition(name, *, output, result, result_raw):
    need(type(name) is str and name and Path(name).name == name and name not in {'.','..'}, 'local preceding worker fault report required')
    report_name = name
    raw = read(ROOT/name, 1024**2)
    fault = json.loads(raw)
    fields = {'schema', 'qualified', 'selected_run', 'selected_result_sha256', 'native_head', 'controls',
        'source_fault', 'artifact_pins', 'actual_extra_worker_children', 'provider_usage', 'source_body_execution',
        'actual_external_provider_invocations', *FALSE}
    need(type(fault) is dict and set(fault) == fields and fault['schema'] == 'terminal-context-worker-faults@1'
         and fault['qualified'] is True and fault['selected_run'] == output.name
         and fault['selected_result_sha256'] == sha(result_raw) and wire(fault['native_head']) == wire(result['native_head']),
         'preceding qualified worker faults must bind exact run/result/head')
    need(wire(fault) == raw and all(fault[key] is False for key in FALSE) and fault['provider_usage'] is None
         and fault['source_body_execution'] is False and type(fault['actual_external_provider_invocations']) is int
         and fault['actual_external_provider_invocations'] == 0 and type(fault['actual_extra_worker_children']) is int
         and fault['actual_extra_worker_children'] == 1, 'preceding worker faults promote unobserved authority')
    controls = fault['controls']
    expected = {'overbudget_before_launch':0, 'rewritten_history_before_launch':0,
                'reordered_history_before_launch':0, 'source_changed_after_spawn':1}
    need(type(controls) is list and len(controls) == 4, 'four preceding worker fault controls required')
    seen = set()
    for control in controls:
        need(type(control) is dict and set(control) == {'control', 'refused', 'error_class', 'message', 'consumer_calls', *FALSE},
             'closed preceding worker fault refusal required')
        name = control['control']
        need(type(name) is str and name in expected and name not in seen and control['refused'] is True
             and type(control['consumer_calls']) is int and control['consumer_calls'] == expected[name]
             and all(control[key] is False for key in FALSE), 'preceding worker fault control scope/count differs')
        seen.add(name)
        need(type(control['error_class']) is str and control['error_class'] and type(control['message']) is str
             and 0 < len(control['message'].encode('utf-8')) <= 4096, 'bounded preceding worker refusal diagnostic required')
        if name == 'source_changed_after_spawn':
            need(control['error_class'] == 'StaleCodebaseError', 'actual stale-source exit refusal required')
    source = fault['source_fault']
    need(type(source) is dict and set(source) == {'mutation_after_actual_child_birth', 'candidate_escaped',
         'source_restored', 'native_owner_reobserved', 'actual_child_birth'} and source['mutation_after_actual_child_birth'] is True
         and source['candidate_escaped'] is False and source['source_restored'] is True
         and source['native_owner_reobserved'] is True, 'preceding source-after-spawn fault restoration not qualified')
    birth = source['actual_child_birth']
    need(type(birth) is dict and set(birth) == {'pid','start_time_ticks'}
         and all(type(birth[key]) is int and birth[key] > 0 for key in birth), 'historical extra-worker birth required')
    pins = fault['artifact_pins']
    need(type(pins) is list and len(pins) in {4,5}, 'complete retained source-fault worker pins required')
    names, parent, acquired = [], None, {}
    import worker_capture
    for entry in pins:
        need(type(entry) is dict and set(entry) == {'relative_path','bytes','sha256'}, 'closed source-fault artifact pin required')
        relative = entry['relative_path']
        need(type(relative) is str and '\\' not in relative, 'canonical source-fault path required')
        path = PurePosixPath(relative)
        need(not path.is_absolute() and path.as_posix() == relative and len(path.parts) == 3
             and path.parts[0].endswith('-artifacts') and path.parts[0] not in {'.','..'}
             and path.parts[1] == 'source_changed_after_spawn' and path.parts[2] in WORKER_LEAVES,
             'closed source-fault worker path scope required')
        need(relative not in names, 'duplicate source-fault artifact path')
        names.append(relative)
        current_parent = ROOT/path.parent
        need(parent is None or parent == current_parent, 'source-fault artifact directories differ')
        parent = current_parent
        need(type(entry['bytes']) is int and 0 <= entry['bytes'] <= MAX_ARTIFACT_BYTES
             and type(entry['sha256']) is str and re.fullmatch(r'[0-9a-f]{64}',entry['sha256']),
             'bounded exact source-fault artifact custody required')
        body = worker_capture._read(ROOT/relative,MAX_ARTIFACT_BYTES,empty=entry['bytes']==0)
        need(len(body) == entry['bytes'] and sha(body) == entry['sha256'], 'retained source-fault worker artifact changed')
        acquired[path.name] = body
    need(names == sorted(names) and MANDATORY_LEAVES <= set(acquired), 'complete sorted source-fault worker leaf scope required')
    need(parent.resolve(strict=True) == parent and {path.name for path in parent.iterdir()} == set(acquired)
         and all(path.is_file() and path.resolve(strict=True)==path for path in parent.iterdir()),
         'retained source-fault worker actual leaf scope differs')
    need({path.name for path in parent.parent.iterdir()} == {'source_changed_after_spawn'},
         'prelaunch-refused faults must not create worker outputs')
    request = json.loads(acquired['request.json'])
    request_raw = worker_capture._request(request)
    need(request_raw == acquired['request.json'] and wire(request['expected_head']) == wire(result['native_head']),
         'retained source-fault worker request/head differs')
    import context_worker
    selection, manifest = context_worker.prepare_request(request)
    observation = worker_capture._observation(acquired['stdout.json'],request,request_raw,parent,selection,manifest)
    need(wire(observation['selection']) == wire(selection) and acquired['stderr.log'] == b''
         and observation['consumer']['consumer_calls'] == 1,
         'retained source-fault worker selected payload/consumer differs')
    return raw, {'relative_path':report_name, 'bytes':len(raw), 'sha256':sha(raw)}


def verify(output, fault_report):
    resource.setrlimit(resource.RLIMIT_CPU, (480,480))
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32*1024**2,32*1024**2))
    output = Path(output)
    need(output.resolve(strict=True) == output and output.parent == ROOT, 'canonical owned completed worker run required')
    result_raw = read(output/'result.json', 1024**2)
    result = json.loads(result_raw)
    validate_result(result)
    need(wire(result) == result_raw, 'canonical completed worker result required')
    artifacts = artifact_check(output, result)
    fault_raw, fault_pin = fault_precondition(fault_report, output=output, result=result, result_raw=result_raw)
    corpus, bodies, instructions, lineage = inputs()
    need(wire(corpus) == artifacts['corpus-manifest.json'] and wire(lineage) == artifacts['lineage.json'], 'sealed worker public input lineage differs')
    for task, raw in instructions.items():
        need(read(output/'instructions'/task/'instruction.md',8192) == raw, 'complete copied instruction differs')
    structural = json.loads(artifacts['structural-report.json'])
    from native_structural_ir import verify_structural_ir, _scheduler
    verify_structural_ir(repository=output/'source-repository', output=output/'structural', expected=structural)
    for source in structural['sources']:
        need(read(output/'source-repository'/source['path'],8192) == bodies[source['path']], 'current complete copied source differs')
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest
    from native_capsules import verify_native_capsules
    from capsule_codec import build_capsule_codec
    from token_cost_review import load_tokenizer
    from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as metadata_api
    from benchmarks.agent_supervisor.container_coding.terminal_codebase_supervisor_fixture import reconstruct_terminal_codebase_metadata_records
    from metadata_projections import _wire as metadata_wire
    from worker_metadata import build_records
    native = json.loads(artifacts['native-capsules.json'])
    codecs = json.loads(artifacts['codec-views.json'])
    metadata = json.loads(artifacts['metadata-report.json'])
    head = _head(structural['head'])
    with _scheduler().acquire(ResourceLane.VALIDATION,cpu_slots=1,memory_mb=1024,child_process_slots=1,
            timeout=30,request_id='terminal-context-worker:cold-retained-replay') as lease:
        check_lease(lease)
        verify_native_capsules(CodebaseIRManifest.from_dict(structural['manifest']), head, native)
        for source in structural['sources']:
            for arm in ('minified','aliased'):
                regenerated = build_capsule_codec(bodies[source['path']],source['path'],source['source_cid'],structural['head'],aliases=arm=='aliased')
                need(wire(codecs[source['path']][arm]) == wire(regenerated), 'complete original source codec replay differs')
        tokenizer, descriptor = load_tokenizer(json.loads(artifacts['tokenizer.json']))
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=256,child_process_slots=1,
                timeout=20,request_id='terminal-context-worker:cold-owned-metadata') as child:
            check_lease(child)
            reopened = metadata_api.validate_codebase_ir_metadata(output=output/'metadata',expected=metadata['native_metadata'],fresh_process=True)
        restored = {family:[json.loads(line)['payload'] for line in read(output/'metadata'/entry['relative_path'],MAX_ARTIFACT_BYTES).splitlines()]
                    for family,entry in reopened['exports'].items()}
        recovered = reconstruct_terminal_codebase_metadata_records(restored)
        records = build_records(structural=structural,bodies=bodies,instructions=instructions,corpus=corpus,native=native,codecs=codecs,lineage=lineage)
        need(metadata_wire(recovered) == metadata_wire(records) and sha(metadata_wire(recovered)) == metadata['records_sha256'],
             'complete cold DuckDB/DuckLake record reconstruction differs')
        contexts = build_contexts(output=output,structural=structural,corpus=corpus,instructions=instructions,native=native,
            metadata=metadata,tokenizer=tokenizer,descriptor=descriptor,lease=lease)
        need(wire(contexts) == artifacts['contexts.json'], 'deterministic complete current source contexts differ')
        replay = validate_deliveries(output=output,contexts=contexts,deliveries=json.loads(artifacts['deliveries.json']),
                                     descriptor=descriptor,artifacts=artifacts,head=head.to_dict())
    need(wire(result['native_head']) == wire(head.to_dict()) and wire(result['native_capsule_inventory']) == wire(native['complete_inventory'])
         and wire(result['metadata_original_record_counts']) == wire(metadata['family_counts']), 'worker result head/capsule/metadata bindings differ')
    verify_structural_ir(repository=output/'source-repository',output=output/'structural',expected=structural)
    need(inputs()[3] == lineage and read(output/'result.json',1024**2) == result_raw, 'selected worker result/lineage changed during replay')
    end_fault_raw,end_fault_pin = fault_precondition(fault_report,output=output,result=result,result_raw=result_raw)
    need(artifact_check(output,result) == artifacts and end_fault_raw == fault_raw and end_fault_pin == fault_pin,
         'worker artifacts or preceding fault report changed during cold replay')
    return {'schema':'terminal-context-worker-cold-replay@1','qualified':True,'selected_run':output.name,
        'selected_result_sha256':sha(result_raw),'selected_native_head':head.to_dict(),
        'selected_artifact_pins_sha256':sha(wire(result['artifact_pins'])),'preceding_fault_report':fault_pin,
        'qualified_faults_verified_before_positive_replay':True,'current_native_owner_observed_before_and_after':True,
        'complete_duckdb_ducklake_reopened':True,'complete_current_contexts_rebuilt':True,
        'retained_worker_observations_verified':replay['retained_calls'],'retained_sessions_verified':replay['sessions'],
        'retained_births_checked_as_current_authority':False,'new_worker_children_spawned':0,
        'all_selected_payloads_budgets_and_history_replayed':True,'provider_usage':None,
        'actual_external_provider_invocations':0,'source_body_execution':False,**FALSE}


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--report',required=True)
    parser.add_argument('--fault-report',required=True);args=parser.parse_args()
    for name in (args.run,args.report,args.fault_report):
        need(name and Path(name).name == name and name not in {'.','..'}, 'owned local names required')
    report=verify(ROOT/args.run,args.fault_report);write(ROOT/args.report,report)
    print(json.dumps({'qualified':True,'retained_observations':48,'new_worker_children_spawned':0}))
