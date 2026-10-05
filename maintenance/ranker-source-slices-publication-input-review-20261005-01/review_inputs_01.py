#!/usr/bin/env python3
"""Independent final input audit: stdlib JSON/file reads only; no target imports."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import time

ROOT = Path('/home/barberb/lift_coding')
S3 = ROOT / 'maintenance/ranker-source-slices-publication-20261005-01'
OUT = ROOT / 'maintenance/ranker-source-slices-publication-input-review-20261005-01'
BOUNDS = {'cpu_seconds': 20, 'timeout_seconds': 20, 'max_input_bytes': 262144,
          'max_output_bytes': 65536, 'max_workspace_bytes': 16777216}
ALLOWED = {'propext', 'Classical.choice', 'Quot.sound'}
BASE_SHA = 'c9cf0ff47f85d562eb3c2f3dcd604f2f850f99b8f8e8e42a9bd063f668ed3084'
PINS = {
    'closed': {'path': str(S3 / 'closed-inputs.json'), 'bytes': 1192,
               'sha256': '4a22f424af31259af6f9914a98452ae365f8d5da2354b3b4c5cc34c2fe00e2aa'},
    'plan': {'path': str(S3 / 'plan.json'), 'bytes': 14321,
             'sha256': '8f97dc8e9ca3fefed4aa0bebfa681975535e2caaad2f57664ee39f7665a63160'},
    'selection': {'path': str(S3 / 'final-selection.json'), 'bytes': 150701,
                  'sha256': '8f3798da8008ca665e188fe51b45836d8692fca0030f146b90f2c9e9bc2f7264'},
}
CHECKED = {}
READ_BYTES = 0


def need(condition, message):
    if not condition:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw.decode('utf-8'), object_pairs_hook=no_duplicate_keys,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON: ' + value)))


def identity(path):
    s = Path(path).lstat()
    return {'dev': s.st_dev, 'ino': s.st_ino, 'mode': s.st_mode, 'nlink': s.st_nlink,
            'uid': s.st_uid, 'gid': s.st_gid, 'size': s.st_size,
            'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns}


def bare(binding):
    need(isinstance(binding, dict) and {'path', 'bytes', 'sha256'} <= set(binding), 'missing byte descriptor')
    return {key: binding[key] for key in ['path', 'bytes', 'sha256']}


def check_pin(binding, complete=False):
    global READ_BYTES
    if complete:
        need(binding.get('complete') is True, 'artifact is not explicitly complete')
    p = bare(binding)
    need(type(p['path']) is str and type(p['bytes']) is int and p['bytes'] >= 0,
         'invalid byte descriptor types')
    need(type(p['sha256']) is str and len(p['sha256']) == 64
         and all(c in '0123456789abcdef' for c in p['sha256']), 'invalid descriptor digest')
    path = Path(p['path'])
    before = identity(path)
    need(stat.S_ISREG(before['mode']) and before['size'] == p['bytes'], 'not regular or wrong size: ' + p['path'])
    cached = CHECKED.get(p['path'])
    if cached is not None:
        need(cached == (p, before), 'pinned file changed or conflicting identity: ' + p['path'])
        return p
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            chunk = stream.read(1048576)
            if not chunk:
                break
            h.update(chunk)
            READ_BYTES += len(chunk)
    need(h.hexdigest() == p['sha256'], 'digest mismatch: ' + p['path'])
    need(identity(path) == before, 'file changed while hashing: ' + p['path'])
    CHECKED[p['path']] = (p, before)
    return p


def load(binding):
    check_pin(binding)
    raw = Path(binding['path']).read_bytes()
    need(len(raw) == binding['bytes'] and hashlib.sha256(raw).hexdigest() == binding['sha256'],
         'same-read JSON bytes differ from pin')
    return parse(raw)


def actual_pin(path):
    path = Path(path)
    raw = path.read_bytes()
    p = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    check_pin(p)
    return p


def pointer(document, ptr):
    need(type(ptr) is str and (ptr == '' or ptr.startswith('/')), 'invalid JSON pointer')
    value = document
    if ptr:
        for token in ptr[1:].split('/'):
            token = token.replace('~1', '/').replace('~0', '~')
            value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def regular_tree(root):
    files, dirs = set(), set()
    for current, names, leaves in os.walk(root, followlinks=False):
        current = Path(current)
        need(stat.S_ISDIR(current.lstat().st_mode), 'non-directory in source scope')
        dirs.add(str(current))
        for name in names:
            need(stat.S_ISDIR((current / name).lstat().st_mode), 'symlink or special directory in source scope')
        for name in leaves:
            path = current / name
            need(stat.S_ISREG(path.lstat().st_mode), 'symlink or special leaf in source scope')
            files.add(str(path))
    return files, dirs


def authority_false(document):
    for key in ['proof_authority', 'execution_authority', 'completion_authority', 'planner_activation']:
        if key in document:
            need(document[key] is False, 'authority flag promoted: ' + key)


def closed_phase(owned_pin, outer_pin):
    owned, outer = load(owned_pin), load(outer_pin)
    need(owned['cleanup_errors'] == outer['cleanup_errors'] == [], 'lease cleanup errors')
    need(owned['root_release_returned'] is True, 'root lease not released')
    state = owned['final_resource_state']
    need(state['active_lease_count'] == state['waiting_request_count'] == 0, 'lease population not drained')
    need(outer['primary_error'] is None and outer['elapsed_seconds_outer'] < 120, 'outer closure failed')
    need(owned['invocation'] == outer['invocation'], 'outer/owned invocation mismatch')
    invocation = load(owned['invocation'])
    for binding in invocation['inputs']:
        check_pin(binding)
    for binding in owned['selected_owned_imports']:
        need(binding['matches'] is True and binding['before'] == binding['after'], 'owned producer source drift')
        check_pin(binding['before'])
    for field in ['native_preparation_calls', 'gradient_evaluations', 'optimizer_updates', 'fit_calls', 'autoencoder_fit_calls']:
        need(owned[field] == 0, 'new model/numerical execution: ' + field)
    authority_false(owned)
    return owned, outer


def native(entry):
    check = load(entry['qualification'])
    owned, outer = closed_phase(entry['owned_closed'], entry['outer_closed'])
    accepted = entry['mode'] != 'lean-typed-scalar-01'
    need(check['status'] == entry['status'] == ('passed' if accepted else 'inconclusive'), 'native actual status')
    need(owned['mode'] == entry['mode'] and owned['status'] == ('passed' if accepted else 'failed'), 'native owned mode/status')
    need(outer['returncode'] == (0 if accepted else 1), 'outer native result')
    need(entry['qualification'] in owned['native_proof_checks'] or not accepted, 'native check/owned receipt join')
    spec = load(actual_pin(ROOT / 'qualification/codebase_ir/ranker-source-semantics-20261005-01/preparation' / (entry['mode'] + '-check-specification.json')))
    need(check['expected_success'] is True and spec['expected_success'] is True, 'positive query expected success')
    need(check['source'] == spec['source'] == entry['source'], 'native source/spec/review pin join')
    need(check['environment_manifest'] == spec['environment_manifest'] == entry['environment_manifest'], 'native profile/spec/review pin join')
    need(check['native_bounds'] == BOUNDS and check['native_invocations'] == check['native_lean_invocations'] == 1, 'native cap or call count changed')
    need(check['native_elapsed_seconds'] <= 20 and check['timed_out'] is False
         and check['cancelled'] is False and check['output_truncated'] is False, 'native bounded execution failure')
    authority_false(check)
    for role in ['source', 'augmented_source', 'retention_helper', 'python_executable']:
        check_pin(check[role])
    profile = load(check['environment_manifest'])
    need(profile['profile_parent']['sha256'] == BASE_SHA, 'wrong prior qualified dependency closure')
    check_pin(profile['profile_parent'])
    need(profile['external_file_count'] == len(profile['files'])
         and profile['external_file_bytes'] == sum(x['bytes'] for x in profile['files']), 'profile inventory denominator')
    need(profile['native_per_file_capture_bytes_unchanged'] == 65536
         and profile['root_reconstructed_external_module_aggregate_max_bytes'] == 3997696, 'dependency retention bounds changed')
    for binding in profile['files']:
        check_pin(binding)
    manifest = load(check_pin(check['retention_manifest'], complete=True))
    need(manifest == check['retention_manifest_body'], 'retention body/file mismatch')
    if accepted:
        need(check['native_lean_returncode'] == 0 and check['matches_expectation'] is True
             and check['axiom_report_error'] is None and check['post_call_binding_error'] is None, 'accepted native report incomplete')
        actual_queries = check['theorem_axiom_output']
        need([x['theorem'] for x in actual_queries] == spec['theorem_names'], 'actual query names differ from specification')
        need(len(actual_queries) == (14 if entry['mode'] == 'lean-typed-scalar-02' else 7), 'qualified query denominator')
        need(all(set(x['axioms']) <= ALLOWED and x['report_occurrences'] >= 1 for x in actual_queries), 'nonstandard accepted axiom')
        need(manifest['status'] == 'complete' and manifest['native_lean_returncode'] == 0, 'accepted object manifest incomplete')
        chunks = {Path(x['path']).name: x for x in check['retained_chunk_artifacts']}
        objects = {Path(x['path']).name: x for x in check['compiled_artifacts']}
        need(len(chunks) == len(check['retained_chunk_artifacts']) and set(chunks) == {x['name'] for x in manifest['chunks']}, 'chunk population mismatch')
        need(len(objects) == len(check['compiled_artifacts']) and set(objects) == {x['name'] for x in manifest['objects']}, 'object population mismatch')
        for chunk in manifest['chunks']:
            binding = chunks[chunk['name']]
            need((binding['bytes'], binding['sha256']) == (chunk['bytes'], chunk['sha256']) and binding['bytes'] <= 65536, 'chunk body/cap mismatch')
            check_pin(binding, complete=True)
        for obj in manifest['objects']:
            binding = objects[obj['name']]
            check_pin(binding, complete=True)
            joined = b''.join(Path(chunks[name]['path']).read_bytes() for name in obj['chunks'])
            need(len(joined) == obj['bytes'] == binding['bytes']
                 and hashlib.sha256(joined).hexdigest() == obj['sha256'] == binding['sha256'], 'complete object/chunk join mismatch')
            need(Path(binding['path']).read_bytes() == joined, 'whole native object differs from RAM chunk join')
        count = len(actual_queries)
    else:
        need(check['matches_expectation'] is False and check['native_lean_returncode'] != 0
             and check['compiled_artifacts'] == check['retained_chunk_artifacts'] == [], 'failed native attempt admitted')
        need(manifest['status'] == 'native_nonzero' and 'sorryAx' in check['stdout'], 'inconclusive elaboration evidence not retained')
        count = 0
    return {'mode': entry['mode'], 'status': check['status'], 'query_count_qualified': count,
            'environment_file_count': len(profile['files']), 'complete_objects': len(check['compiled_artifacts']),
            'chunks': len(check['retained_chunk_artifacts']), 'source': check['source'], 'check': entry['qualification']}


def main():
    started = time.monotonic()
    closed, plan, selection = (load(PINS[key]) for key in ['closed', 'plan', 'selection'])
    need(closed['plan'] == PINS['plan'] and closed['final_selection'] == PINS['selection'], 'fixed closed-plan-selection joins')
    check_pin(closed['preparation_source'])
    need(closed['publication_profile'] == plan['publication_profile'], 'publication profile join')
    need(plan['status'] == 'frozen_final_plan' and plan['source_and_artifacts_quiet'] is True
         and plan['source_plan_quiet'] is True, 'plan not final quiet input')
    need(plan['excluded_dependency_subtrees'] == selection['exclusions'] == [], 'unexpected exclusions')
    documents = {role: load(binding) for role, binding in plan['documents'].items()}
    facts = load(plan['semantic_policy'])
    need(type(facts) is list and len(facts) == 157, 'typed fact denominator')
    for row in facts:
        need(set(row) == {'document', 'pointer', 'equals'}, 'unknown typed fact fields')
        need(wire(pointer(documents[row['document']], row['pointer'])) == wire(row['equals']), 'typed fact mismatch: ' + row['document'] + row['pointer'])
    seal, review = documents['file_seal'], documents['qualified_review']
    need(seal['schema'] == plan['seal_schema'] and review['schema'] == plan['review_schema'], 'seal/review schemas')
    need(seal['status'] == 'sealed_quiet_regular_file_scope' and review['status'] == 'passed', 'final qualification not sealed/passed')
    need(seal['regular_file_count'] == len(seal['files']) == 299
         and seal['regular_file_bytes'] == sum(x['bytes'] for x in seal['files']) == 86451989, 'sealed population denominator')
    need(hashlib.sha256(wire(seal['files'])).hexdigest() == seal['file_inventory_sha256'], 'sealed inventory digest')
    need(seal['review'] == plan['documents']['qualified_review'], 'seal qualified review join')
    need(seal['excluded_dependency_roots'] == seal['fixture_symlinks'] == [], 'sealed exclusions/fixtures')
    q4 = Path(plan['scope_root']); p5 = Path(plan['source_plan_root'])
    qfiles, qdirs = regular_tree(q4); pfiles, pdirs = regular_tree(p5)
    expected_q4 = {x['path'] for x in seal['files']} | {plan['documents']['file_seal']['path']}
    need(len(expected_q4) == 300 and qfiles == expected_q4, 'whole Q4 regular tree differs from sealed population plus seal')
    need(len(pfiles) == 2, 'whole P5 draft file denominator')
    additions = plan['explicit_additions']
    need(len(additions) == 35 and len({x['path'] for x in additions}) == 35, 'explicit addition denominator/duplicate path')
    expected = qfiles | pfiles | {x['path'] for x in additions}
    selected = selection['files']; selected_map = {x['path']: x for x in selected}
    need(len(selected) == len(selected_map) == len(expected) == 336
         and set(selected_map) == expected and sum(x['bytes'] for x in selected) == 87119741, 'whole exact final selection population')
    dirs = {x['path']: x['stat'] for x in selection['directories']}
    need(len(dirs) == len(selection['directories']) == 33 and set(dirs) == qdirs | pdirs, 'whole selected directory inventory')
    aliases = set()
    for row in selected:
        path = Path(row['path'])
        need(path.resolve(strict=True) == path, 'selected path is not canonical')
        check_pin(row)
        need(identity(path) == row['stat'], 'selected file stat differs from frozen selection')
        inode = (row['stat']['dev'], row['stat']['ino'])
        need(inode not in aliases, 'selected hardlink or alias denominator')
        aliases.add(inode)
    for path, stamp in dirs.items():
        need(identity(path) == stamp, 'selected directory stat differs')
    for binding in seal['files'] + additions:
        check_pin(binding)
        need(bare(binding) == bare(selected_map[binding['path']]), 'selection byte pin differs from frozen role')
    provenance = load(actual_pin(S3 / 'captured-provenance/provenance-map.json'))
    need(provenance['rawExternalDependenciesIncluded'] is False and provenance['rawSDKlogsIncluded'] is False, 'raw dependencies/logs included')
    clones = []
    for row in provenance['sources']:
        check_pin(row['original']); check_pin(row['captured'])
        need(row['captured']['path'] in selected_map and bare(row['captured']) == bare(selected_map[row['captured']['path']]), 'captured provenance not selected exactly')
        need((row['original']['bytes'], row['original']['sha256']) == (row['captured']['bytes'], row['captured']['sha256'])
             and Path(row['original']['path']).read_bytes() == Path(row['captured']['path']).read_bytes(), 'provenance clone bytes differ')
        if row.get('role') == 'unimplemented_and_unqualified_next_objective_plan':
            clones.append(row)
    need(len(clones) == 4, 'captured next-objective draft denominator')
    for row in clones:
        if row['captured']['path'].endswith('-source-plan.json'):
            draft = load(row['captured'])
            need(draft['status'] == 'source_only_design_unimplemented_uncompiled_unqualified', 'next-objective plan promoted')
            need(draft['first_bounded_acceptance']['qualified_queries'] == 0, 'next-objective queries promoted')
            for field in ['implemented', 'compiled', 'theorem_qualified', 'objective_source_equivalence_proved', 'gradient_source_equivalence_proved', 'optimizer_source_convergence_proved', 'proof_authority']:
                need(draft['frontier_flags'][field] is False, 'next-objective draft claim promoted')
    source_review = load(actual_pin(S3 / 'source-review-01.json'))
    need(actual_pin(S3 / 'source-review-01.json')['sha256'] == 'fbfef37641d60af2e94439b53faa71a5dcfbcbfb35ea632ca9882f84561f4257', 'source-six receipt identity')
    need(source_review['status'] == 'passed_source_only' and source_review['findings'] == []
         and 'issues' not in source_review, 'actual source-six review schema/status/findings')
    need(len(source_review['reviewed_sources']) == 6, 'source-six source denominator')
    for binding in source_review['reviewed_sources']:
        check_pin(binding)
        need(binding['target_execution'] is False, 'source review executed target')
    check_pin(source_review['reviewer'])
    authority_false(source_review)
    semantic = documents['semantic_review']
    need(semantic['status'] == 'passed_file_only_source_slice_semantic_native_review'
         and semantic['outstanding_issues'] == [], 'independent semantic/native review failed')
    semantic_plan = load(actual_pin(ROOT / 'maintenance/ranker-source-semantic-native-review-20261005-01/final-plan.json'))
    for binding in semantic_plan['documents'].values():
        check_pin(binding)
    request = load(semantic_plan['documents']['request'])
    need(len(request['strict_old_inputs']) == 1808 and len(request['protected_live_sources']) == 4, 'old/live guard denominator')
    for binding in request['strict_old_inputs'] + request['protected_live_sources']:
        check_pin(binding)
    for guard in review['original_checkout_guards'].values():
        check_pin(guard['index'])
    source_spec = load(semantic_plan['documents']['source_specification'])
    check_pin(source_spec['source'])
    shape = load(source_spec['difference_artifact'])
    need(len(shape['differences']) == 4 and all(len(row) == 80 for row in shape['differences']),
         'original exact supplied difference artifact is not 4x80')
    need(wire(load(semantic_plan['documents']['slices_v1'])) == wire(load(semantic_plan['documents']['slices_v2'])), 'old and current IR schema or trees differ')
    observations = [native(entry) for entry in review['native_checks']]
    need(len(observations) == 3 and sum(x['status'] == 'passed' for x in observations) == 2
         and sum(x['query_count_qualified'] for x in observations) == 21, 'actual native census')
    for phase in review['phases']:
        phase_body = load(phase)
        outer_pin = actual_pin(q4 / 'evidence' / (phase_body['mode'] + '-closed.json'))
        closed_phase(phase, outer_pin)
    metadata = documents['metadata_readback']
    need(metadata['status'] == 'passed' and metadata['metadata_family_count'] == 32
         and metadata['metadata_row_count'] == 4440 and metadata['additive_payload_rows'] == 23, 'metadata result denominator')
    authority_false(metadata)
    built = load(review['metadata_build_receipt']); current = load(built['metadata_inputs']); prior = load(built['prior_metadata'])
    need(current == load(metadata['metadata_inputs']), 'metadata built/run input mismatch')
    need(set(current) == set(prior) and len(current) == 32
         and sum(map(len, prior.values())) == 4417 and sum(map(len, current.values())) == 4440, 'metadata family/payload denominator')
    for family, rows in prior.items():
        need(wire(current[family][:len(rows)]) == wire(rows), 'prior metadata payload prefix drift: ' + family)
    need(wire(current['vectors']) == wire(prior['vectors']) and len(current['vectors']) == 375, 'vector payloads changed')
    need(len(prior['contracts']) == 0 and len(current['contracts']) == 2, 'contract projection row denominator')
    for row in current['contracts']:
        need(row['contract_kind'] == 'mathematical_projection_domain' and row['runtime_enforced'] is False
             and row['python_source_contract_proved'] is False, 'contract scope promoted')
        authority_false(row)
    manifest_path = q4 / 'evidence/metadata-source-slices-01/metadata/manifest.json'
    manifest_pin = actual_pin(manifest_path); manifest = load(manifest_pin)
    report = metadata['native_report']; fresh = metadata['fresh_process_readback']
    need(report['manifest_sha256'] == fresh['manifest_sha256'] == 'sha256:' + manifest_pin['sha256'], 'native metadata manifest joins')
    need(report['limits']['families'] == manifest['limits']['families'] == 32 and report['row_count'] == manifest['row_count'] == fresh['row_count'] == 4440, 'metadata native limits/row count')
    need(fresh['verified'] is True and report['row_root_sha256'] == fresh['row_root_sha256'] == manifest['row_root_sha256']
         and report['lake_snapshot_digest'] == fresh['lake_snapshot_digest'] == manifest['lake_snapshot_digest'], 'metadata fresh-process receipt joins')
    base = manifest_path.parent
    for family, info in manifest['families'].items():
        export = info['export']; path = base / export['relative_path']
        raw = path.read_bytes()
        need(len(raw) == export['bytes'] and 'sha256:' + hashlib.sha256(raw).hexdigest() == export['sha256'], 'export bytes mismatch: ' + family)
        rows = [parse(line) for line in raw.splitlines()]
        need(len(rows) == info['count'] == len(current[family]) and all(x['family'] == family for x in rows), 'export family/count mismatch')
        need(wire([x['payload'] for x in rows]) == wire(current[family]), 'export payload readback differs: ' + family)
    false_scopes = ['CPython_math_fsum_semantics_proved', 'binary64_error_bound_proved',
                    'feature_preparation_to_IR_translation_proved', 'full_training_loop_to_IR_translation_proved',
                    'global_autoencoder_convergence_proved', 'host_parser_correctness_theorem_proved',
                    'native_Float_optimizer_convergence_proved', 'objective_to_IR_translation_proved',
                    'python_ranker_source_equivalence_proved', 'whole_codebase_IR_semantic_preservation_proved',
                    'projection_domains_runtime_enforced']
    for field in false_scopes:
        need(review[field] is False, 'broad scope promoted: ' + field)
    for field in ['new_autoencoder_fits', 'new_feature_preparations', 'new_gradient_evaluations',
                  'new_optimizer_updates', 'new_public_fits', 'new_ranker_training_trace_replays']:
        need(review[field] == 0, 'forbidden new numerical work: ' + field)
    need(review['full_task_satisfaction'] == 'unknown' and review['all32_governing_RPI_exits'] == 'OPEN', 'task/RPI scope promoted')
    authority_false(review); authority_false(seal); authority_false(documents['open_obligations'])
    for path, stamp in dirs.items():
        need(identity(path) == stamp, 'directory changed during review')
    for row in selected:
        check_pin(row)
        need(identity(row['path']) == row['stat'], 'selected file changed during review')
    need(regular_tree(q4) == (qfiles, qdirs) and regular_tree(p5) == (pfiles, pdirs), 'whole source trees changed during review')
    for binding in PINS.values():
        check_pin(binding)
    receipt = {
        'schema': 'ranker-source-slices-final-publication-input-review@1',
        'status': 'passed_file_only_final_publication_input_review',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': actual_pin(Path(__file__).resolve()), 'fixed_inputs': PINS,
        'outstanding_issues': [], 'typed_facts_verified': len(facts),
        'selected_regular_files': len(selected), 'selected_regular_bytes': sum(x['bytes'] for x in selected),
        'selected_directories': len(dirs), 'selected_aliases': 0, 'exclusions': [],
        'sealed_regular_files_without_seal_self': 299, 'sealed_regular_bytes_without_seal_self': 86451989,
        'whole_Q4_regular_files_with_seal_self': 300, 'whole_P5_draft_regular_files': 2,
        'explicit_additions': 35, 'captured_next_objective_draft_byte_clones': 4,
        'provenance_clones_verified': len(provenance['sources']), 'source_review_helpers': 6,
        'native_checks': observations, 'actual_native_calls': 3, 'qualified_native_checks': 2,
        'inconclusive_native_attempts_retained_unadmitted': 1, 'qualified_theorem_queries': 21,
        'complete_chunk_object_joins_verified_in_memory': True, 'native_bounds': BOUNDS,
        'prior_protected_input_files': 1808, 'protected_live_source_files': 4,
        'metadata_families': 32, 'metadata_payloads': 4440, 'prior4417_payload_prefixes_verified': True,
        'vectors375_unchanged': True, 'new_domain_contract_rows': 2, 'runtime_contracts_claimed': False,
        'whole_before_after_selection_pins_and_stats_verified': True,
        'file_pins_rehashed': len(CHECKED), 'raw_file_bytes_read_for_digest': READ_BYTES,
        'elapsed_seconds': time.monotonic() - started,
        'target_imports_or_executions': 0, 'native_or_model_jobs': 0, 'codec_calls': 0,
        'Git_or_HTTP_calls': 0, 'remote_mutations': 0, 'Q4_S3_P5_P6_writes': 0,
        'python_source_equivalence_proved': False, 'python_Float_semantics_proved': False,
        'objective_source_translation_proved': False, 'gradient_source_translation_proved': False,
        'full_training_loop_proved': False, 'whole_IR_equivalence_proved': False,
        'global_autoencoder_convergence_proved': False, 'full_task_satisfaction': 'unknown',
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
        'planner_activation': False, 'all32_governing_RPI_exits': 'OPEN',
    }
    destination = OUT / 'review-receipt.json'
    need(not destination.exists(), 'fresh independent receipt required')
    destination.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': receipt['status'], 'receipt': actual_pin(destination),
                      'outstanding_issues': [], 'selected_files': len(selected),
                      'selected_bytes': receipt['selected_regular_bytes']}, sort_keys=True))


if __name__ == '__main__':
    main()
