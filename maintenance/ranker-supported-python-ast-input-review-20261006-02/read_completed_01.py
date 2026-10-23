"""Root-only file readback of a completed frozen tail batch; no target imports."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path('/home/barberb/lift_coding')
QUAL = ROOT / 'qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-02'
OUT = ROOT / 'maintenance/ranker-supported-python-ast-input-review-20261006-02'

def need(condition, message):
    if not condition:
        raise ValueError(message)

def pin(path):
    path = Path(path)
    digest, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            digest.update(block)
            size += len(block)
    return {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}

def canonical(row):
    return {key: row[key] for key in ('path', 'bytes', 'sha256')}

def document(row):
    need(pin(row['path']) == canonical(row), 'exact body descriptor required')
    return json.loads(Path(row['path']).read_bytes())

def main():
    need(__debug__, 'optimized Python execution is refused')
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', required=True)
    parser.add_argument('--expected-check-sha256', required=True)
    parser.add_argument('--expected-request-sha256', required=True)
    args = parser.parse_args()
    maprow = pin(QUAL / 'module-map-01.json')
    need((maprow['bytes'], maprow['sha256']) == (1131, 'ec08cd958dd9747751a0b6d0b3773d683a973ecdd572bd8cb38cfc5e44dcf9a2'), 'frozen map required')
    modules = document(maprow)
    need(args.mode in modules, 'finite frozen mode required')
    selected = modules[args.mode]
    mode = args.mode
    requestrow = pin(QUAL / 'preparation' / (mode + '-request.json'))
    checkrow = pin(QUAL / 'evidence' / mode / 'check-result.json')
    need(requestrow['sha256'] == args.expected_request_sha256 and checkrow['sha256'] == args.expected_check_sha256, 'external completed request/check pins required')
    request, check = document(requestrow), document(checkrow)
    need(request['combined_source_gate_expected_qualified_queries'] == 3, 'fresh accurate aggregate query metadata required')
    ownedrow = pin(QUAL / 'evidence' / mode / 'closed.json')
    outerrow = pin(QUAL / 'evidence' / (mode + '-closed.json'))
    invocationrow = pin(QUAL / 'preparation' / (mode + '-invocation.json'))
    owned, outer, invocation = document(ownedrow), document(outerrow), document(invocationrow)
    specification = document(invocation['specification'])
    gaterow = specification['independent_core_source_review']
    need((gaterow['bytes'], gaterow['sha256']) == (6822, '5f7cb7f95a8bb2dee4b9ab24eb88b0a455ede7cfbc48c07e5b3155a8aa6d430f'), 'independent frozen source gate required')
    gate = document(gaterow)
    need(gate['status'] == 'passed_source_only' and gate['findings'] == [] and gate['reviewed_modules'][mode] == specification['selected_module'] == selected, 'exact selected source-review join required')
    need(check['status'] == owned['status'] == 'passed' and outer['returncode'] == check['native_lean_returncode'] == 0, 'successful owned native result required')
    need(check['source'] == specification['source'] and canonical(check['source'])['bytes'] == selected['source']['bytes'] and check['source']['sha256'] == selected['source']['sha256'] and check['environment_manifest'] == specification['environment_manifest'], 'source/spec/environment joins required')
    for row in (selected['source'], check['source'], check['augmented_source'], check['environment_manifest']):
        need(pin(row['path']) == canonical(row), 'source/environment body unchanged')
    need(check['native_invocations'] == check['native_lean_invocations'] == 1 and not check['timed_out'] and not check['resource_exhausted'] and not check['output_truncated'] and check['axiom_report_error'] is None, 'exact bounded single native call required')
    need(check['native_bounds'] == {'timeout_seconds': 20, 'cpu_seconds': 20, 'max_input_bytes': 262144, 'max_output_bytes': 65536, 'max_workspace_bytes': 16777216}, 'unchanged native caps required')
    need(owned['invocation'] == outer['invocation'] == invocationrow and owned['native_proof_checks'] == [checkrow] and owned['native_checker_attempts'] == [{'specification': invocation['specification'], 'native_invocations_observed': 1}] and owned['mode'] == invocation['mode'] == mode, 'actual invocation/check ownership required')
    need(check['actual_root_lease'] == owned['root_lease'] and owned['root_lease']['owner_pid'] == outer['child_pid'], 'actual PID/lease binding required')
    queries = selected['queries']
    need([row['theorem'] for row in check['theorem_axiom_output']] == queries, 'exact query set required')
    reports = re.findall(r"'([^']+)' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])", check['stdout'], re.S)
    need([row[0] for row in reports] == queries + queries, 'two actual ordered reports per query required')
    for row in check['theorem_axiom_output']:
        need(row['report_occurrences'] == 2 and set(row['axioms']) <= {'propext', 'Classical.choice', 'Quot.sound'}, 'standard axiom policy required')
        actual = [set(part.strip() for part in item[1].split(',') if part.strip()) for item in reports if item[0] == row['theorem']]
        need(len(actual) == 2 and all(value == set(row['axioms']) for value in actual), 'actual stdout/axiom metadata join required')
    final = owned['final_resource_state']
    need(final['active_lease_count'] == final['waiting_request_count'] == 0 and final['counters']['acquisitions_total'] == final['counters']['releases_total'] == 1 and owned['root_release_returned'] and owned['cleanup_errors'] == outer['cleanup_errors'] == [] and owned['all_strict_old_and_protected_live_inputs_unchanged'], 'one released/drained clean lease required')
    for key in ('native_preparation_calls', 'gradient_evaluations', 'optimizer_updates', 'fit_calls', 'autoencoder_fit_calls', 'test_cases', 'metadata_hydration_calls', 'source_function_executions', 'dependency_setup_calls'):
        need(owned[key] == 0, 'prohibited callback observed')
    authority = ('execution_authority', 'proof_authority', 'planner_activation', 'completion_authority')
    for key in authority:
        need(check[key] is owned[key] is gate[key] is False, 'authority must remain false')
    need(len(request['strict_old_inputs']) == request['strict_guard_count'] == 4114 and len(request['protected_live_sources']) == 4, 'complete guard population required')
    for row in request['strict_old_inputs'] + request['protected_live_sources']:
        need(pin(row['path']) == row, 'guard body changed')
    guards = request['original_checkout_guards']
    need(owned['original_checkout_guards_before'] == owned['original_checkout_guards_after'] == outer['original_checkout_guards_before'] == outer['original_checkout_guards_after'] == guards, 'checkout guard joins required')
    for name, where in (('root', ROOT), ('child', ROOT / 'external/ipfs_accelerate')):
        need(subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-C', str(where), 'rev-parse', 'HEAD'], text=True).strip() == guards[name]['head'] and pin(guards[name]['index']['path']) == guards[name]['index'], 'actual HEAD/index unchanged required')
    manifest = document(check['retention_manifest'])
    need(manifest == check['retention_manifest_body'] and manifest['status'] == 'complete' and manifest['native_lean_invocations'] == 1 and manifest['native_lean_returncode'] == 0 and manifest['retention_profile_sha256'] == check['retention_profile_sha256'], 'complete exact retention manifest required')
    objects, chunks = check['compiled_artifacts'], check['retained_chunk_artifacts']
    need(len(objects) == len(manifest['objects']) == 1 and 0 < len(chunks) <= 61 and len(chunks) == len(manifest['chunks']), 'one whole module and bounded exact chunk population required')
    obj = objects[0]
    need(Path(obj['path']).name == selected['module'] + '.olean' and obj['complete'] is True and obj['retention_format'] == 'bounded_lean_chunks@1' and pin(obj['path']) == canonical(obj), 'exact complete compiled module required')
    parts = []
    for index, (chunk, declared) in enumerate(zip(chunks, manifest['chunks'])):
        name = 'LeanProofChunk%03d.bin' % index
        need(Path(chunk['path']).name == name and chunk['complete'] is True and 0 < chunk['bytes'] <= 65536 and pin(chunk['path']) == canonical(chunk) and declared == {'name': name, 'bytes': chunk['bytes'], 'sha256': chunk['sha256']}, 'exact consecutive raw chunk required')
        parts.append(Path(chunk['path']).read_bytes())
    raw = b''.join(parts)
    need(len(raw) == obj['bytes'] == manifest['aggregate_raw_object_bytes'] <= 3997696 and hashlib.sha256(raw).hexdigest() == obj['sha256'], 'raw chunks must reconstruct exact whole module')
    need(manifest['objects'][0] == {'name': Path(obj['path']).name, 'bytes': obj['bytes'], 'sha256': obj['sha256'], 'chunks': [Path(row['path']).name for row in chunks]}, 'exact object manifest required')
    output = OUT / (mode + '-completed-readback-01.json')
    receipt = {'schema': 'ranker-supported-python-scalar-ast-completed-file-only-readback@1', 'status': 'passed_scoped', 'mode': mode, 'check_result': checkrow, 'owned': ownedrow, 'outer': outerrow, 'invocation': invocationrow, 'request': requestrow, 'native_attempts': 1, 'qualified_queries': len(queries), 'actual_queries': queries, 'two_actual_standard_axiom_reports_per_query': True, 'actual_whole_module': obj, 'ordered_chunks': chunks, 'all4114_plus4_guard_bodies_unchanged': True, 'original_checkout_guards': guards, 'root_resources_drained': True, 'review_new_jobs': 0, 'full_task_satisfaction': 'unknown', 'python_ranker_source_equivalence_proved': False, 'global_autoencoder_convergence_proved': False, **{key: False for key in authority}}
    with output.open('xb') as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode())
    print(json.dumps({'status': 'passed_file_only', 'receipt': pin(output), 'native_calls': 0, 'queries_readback': len(queries)}))

if __name__ == '__main__':
    main()
