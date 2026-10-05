#!/usr/bin/env python3
"""Independent final input audit: stdlib JSON/file reads only; no target imports."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import time

ROOT = Path('/home/barberb/lift_coding')
S4 = ROOT / 'maintenance/ranker-objective-scalar-publication-20261005-01'
R4 = ROOT / 'maintenance/ranker-objective-scalar-publication-root-20261005-01'
Q = ROOT / 'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
P6 = ROOT / 'qualification/codebase_ir/ranker-objective-ir-source-plan-20261005-01'
OUT = ROOT / 'maintenance/ranker-objective-scalar-publication-input-review-20261005-01'
BOUNDS = {'cpu_seconds': 20, 'timeout_seconds': 20, 'max_input_bytes': 262144,
          'max_output_bytes': 65536, 'max_workspace_bytes': 16777216}
ALLOWED = {'propext', 'Classical.choice', 'Quot.sound'}
BASE_SHA = 'c9cf0ff47f85d562eb3c2f3dcd604f2f850f99b8f8e8e42a9bd063f668ed3084'
PINS = {}
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


def stat_identity(s):
    return {'dev': s.st_dev, 'ino': s.st_ino, 'mode': s.st_mode, 'nlink': s.st_nlink,
            'uid': s.st_uid, 'gid': s.st_gid, 'size': s.st_size,
            'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns}


def identity(path):
    return stat_identity(Path(path).lstat())


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
    need(path.is_absolute() and path.resolve(strict=True) == path, 'canonical pinned file required')
    before = identity(path)
    need(stat.S_ISREG(before['mode']) and before['size'] == p['bytes'], 'not regular or wrong size: ' + p['path'])
    cached = CHECKED.get(p['path'])
    if cached is not None:
        need(cached == (p, before), 'pinned file changed or conflicting identity: ' + p['path'])
        return p
    h = hashlib.sha256(); total = 0
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        need(stat_identity(os.fstat(fd)) == before, 'pinned input changed before FD read')
        while chunk := os.read(fd, 1048576):
            total += len(chunk)
            need(total <= p['bytes'], 'pinned stream grew beyond declared size')
            h.update(chunk); READ_BYTES += len(chunk)
        need(stat_identity(os.fstat(fd)) == before and total == p['bytes'], 'pinned input changed during stream read')
    finally:
        os.close(fd)
    need(h.hexdigest() == p['sha256'], 'digest mismatch: ' + p['path'])
    need(identity(path) == before, 'file changed while hashing: ' + p['path'])
    CHECKED[p['path']] = (p, before)
    return p


def bounded_read(binding, limit):
    check_pin(binding)
    need(type(limit) is int and 0 < limit <= 32 * 1024**2 and binding['bytes'] <= limit, 'bounded body read')
    path = Path(binding['path']); fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = stat_identity(os.fstat(fd))
        need(before == identity(path) and before['size'] == binding['bytes'] and stat.S_ISREG(before['mode']), 'stable parsed regular file')
        chunks, total = [], 0
        while block := os.read(fd, min(1048576, limit + 1 - total)):
            total += len(block); need(total <= limit, 'parsed input grew beyond bound'); chunks.append(block)
        need(stat_identity(os.fstat(fd)) == identity(path) == before, 'parsed file changed during bounded read')
        raw = b''.join(chunks)
    finally:
        os.close(fd)
    need(len(raw) == binding['bytes'] and hashlib.sha256(raw).hexdigest() == binding['sha256'],
         'same-read JSON bytes differ from pin')
    return raw


def load(binding):
    return parse(bounded_read(binding, 32 * 1024**2))


def actual_pin(path):
    global READ_BYTES
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path, 'canonical observed input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = stat_identity(os.fstat(fd)); need(stat.S_ISREG(before['mode']), 'observed regular input')
        digest, total = hashlib.sha256(), 0
        while block := os.read(fd, 1048576):
            total += len(block); need(total <= before['size'], 'observed stream grew beyond initial size')
            digest.update(block); READ_BYTES += len(block)
        need(stat_identity(os.fstat(fd)) == identity(path) == before and total == before['size'], 'observed input changed during stream hash')
    finally:
        os.close(fd)
    p = {'path': str(path), 'bytes': total, 'sha256': digest.hexdigest()}
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
    need(entry['mode'] in {'lean-objective-scalar-01', 'lean-objective-generated-01'}, 'exact actual native mode')
    accepted = True
    need(check['status'] == entry['status'] == ('passed' if accepted else 'inconclusive'), 'native actual status')
    need(owned['mode'] == entry['mode'] and owned['status'] == ('passed' if accepted else 'failed'), 'native owned mode/status')
    need(outer['returncode'] == (0 if accepted else 1), 'outer native result')
    need(entry['qualification'] in owned['native_proof_checks'] or not accepted, 'native check/owned receipt join')
    spec = load(actual_pin(Q / 'preparation' / (entry['mode'] + '-check-specification.json')))
    need(check['expected_success'] is True and spec['expected_success'] is True, 'positive query expected success')
    need(check['source'] == spec['source'] == entry['source'], 'native source/spec/review pin join')
    need(check['environment_manifest'] == spec['environment_manifest'] == entry['environment_manifest'], 'native profile/spec/review pin join')
    need(check['native_bounds'] == BOUNDS and type(check['native_invocations']) is int and type(check['native_lean_invocations']) is int and check['native_invocations'] == check['native_lean_invocations'] == 1, 'native cap or call count changed')
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
        need(len(actual_queries) == (5 if entry['mode'] == 'lean-objective-scalar-01' else 9), 'qualified query denominator')
        need(all(set(x['axioms']) <= ALLOWED and x['report_occurrences'] == 2 for x in actual_queries), 'nonstandard accepted axiom')
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
            need(obj['bytes'] <= 16 * 1024**2 and sum(chunks[name]['bytes'] for name in obj['chunks']) <= 16 * 1024**2,
                 'bounded complete native object reconstruction')
            joined = b''.join(bounded_read(chunks[name], 65536) for name in obj['chunks'])
            need(len(joined) == obj['bytes'] == binding['bytes']
                 and hashlib.sha256(joined).hexdigest() == obj['sha256'] == binding['sha256'], 'complete object/chunk join mismatch')
            need(bounded_read(binding, 16 * 1024**2) == joined, 'whole native object differs from RAM chunk join')
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
    global PINS
    need(__debug__, 'optimized Python refused')
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ['closed', 'plan', 'selection', 'guards']:
        parser.add_argument('--expected-' + key + '-sha256', required=True)
    for key in ['sealed-files', 'sealed-bytes', 'selected-files', 'selected-bytes']:
        parser.add_argument('--expected-' + key, required=True, type=int)
    args = parser.parse_args()
    fixed_paths = {'closed': S4 / 'closed-inputs.json', 'plan': S4 / 'plan.json',
                   'selection': S4 / 'final-selection.json', 'guards': R4 / 'inherited-publication-guards-01.json'}
    for role, path in fixed_paths.items():
        p = actual_pin(path)
        need(p['sha256'] == getattr(args, 'expected_' + role + '_sha256'), 'independent exact ' + role + ' digest')
        PINS[role] = p
    need(0 < args.expected_sealed_files <= args.expected_selected_files <= 10000 and
         0 < args.expected_sealed_bytes <= args.expected_selected_bytes <= 256 * 1024**2,
         'external bounded final population values')
    closed, plan, selection, guards = (load(PINS[key]) for key in ['closed', 'plan', 'selection', 'guards'])
    need(closed['schema'] == 'ranker-objective-scalar-publication-closed-inputs@1' and
         closed['plan'] == PINS['plan'] and closed['final_selection'] == PINS['selection'], 'exact closure-plan-selection joins')
    check_pin(closed['preparation_source'])
    need(closed['preparation_source'] == actual_pin(S4 / 'freeze_inputs.py'), 'executed selection freezer source')
    need(plan['schema'] == 'ranker-objective-scalar-publication-plan@1' and
         selection['schema'] == 'ranker-objective-scalar-publication-final-selection@1' and
         closed['publication_profile'] == plan['publication_profile'], 'exact plan/selection/profile schemas')
    expected_profile = {'raw_population_max': 268435456, 'raw_member_sum_per_shard_max': 14680064,
        'per_file_max': 14680064, 'complete_decoded_tar_max': 16777216, 'compressed_shard_max': 16777216,
        'aggregate_decoded_work_max': 1073741824, 'wall_seconds': 180, 'members_max': 10000,
        'depth_max': 6, 'shards_max': 64, 'zstd_args': ['-T1', '-3'],
        'duplicate_verification_decoder_invocations': 0, 'member_readback_profile': 'same_first_decoded_tar_and_member_streams@1',
        'native_qualification_limits_changed': False}
    need(wire(plan['publication_profile']) == wire(expected_profile), 'unchanged publication caps')
    need(plan['status'] == 'frozen_final_plan' and plan['source_and_artifacts_quiet'] is True and
         plan['source_plan_quiet'] is True and plan['scope_root'] == str(Q) and plan['source_plan_root'] == str(P6), 'fixed quiet owned roots')
    need(plan['excluded_dependency_subtrees'] == selection['exclusions'] == [], 'no denominator exclusions')
    need(plan['old_HF_bundle_reuploaded'] is False and plan['prior_HF_commit'] == 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e', 'no prior archive reupload')
    need(guards['schema'] == 'ranker-objective-scalar-inherited-publication-guards@1' and
         guards['prior_pins_revalidated'] is True and len(guards['files']) == 2393 and
         len({row['path'] for row in guards['files']}) == 2393 and guards['strict_old_input_count'] == 2108 and
         guards['protected_live_source_count'] == 4, 'whole immutable guard census')
    guard_map = {row['path']: bare(row) for row in guards['files']}
    for row in guards['files']:
        check_pin(row)
    for row in guards['sources']:
        check_pin(row)
    documents = {role: load(binding) for role, binding in plan['documents'].items()}
    facts = load(plan['semantic_policy'])
    need(type(facts) is list and 0 < len(facts) <= 5000, 'bounded nonempty typed fact policy')
    seen = set()
    for row in facts:
        need(set(row) == {'document', 'pointer', 'equals'} and row['document'] in documents, 'exact typed fact fields')
        key = (row['document'], row['pointer'])
        need(key not in seen, 'duplicate typed fact pointer'); seen.add(key)
        need(wire(pointer(documents[row['document']], row['pointer'])) == wire(row['equals']), 'typed observed fact differs')
    seal, review = documents['file_seal'], documents['qualified_review']
    need(seal['schema'] == plan['seal_schema'] == 'ranker-objective-scalar-file-only-seal@1' and
         review['schema'] == plan['review_schema'] == 'ranker-objective-scalar-closed-qualification@1' and
         review['status'] == 'passed' and seal['scope_root'] == str(Q), 'passed closed qualification schema')
    need(type(seal['regular_file_count']) is int and seal['regular_file_count'] == len(seal['files']) == args.expected_sealed_files and
         type(seal['regular_file_bytes']) is int and seal['regular_file_bytes'] == sum(row['bytes'] for row in seal['files']) == args.expected_sealed_bytes,
         'exact external sealed population denominator')
    need(hashlib.sha256(wire(seal['files'])).hexdigest() == seal['file_inventory_sha256'] and
         seal['review'] == plan['documents']['qualified_review'] and seal.get('excluded_dependency_roots', []) == seal['fixture_symlinks'] == [],
         'seal inventory/review/no-alias joins')
    qfiles, qdirs = regular_tree(Q); pfiles, pdirs = regular_tree(P6)
    need(qfiles == {row['path'] for row in seal['files']} | {plan['documents']['file_seal']['path']}, 'whole Q5 equals seal plus seal self-file')
    need(len(pfiles) == 4, 'whole retained P6 planning population')
    additions = plan['explicit_additions']
    need(0 < len(additions) <= 100 and len({row['path'] for row in additions}) == len(additions), 'bounded unique explicit additions')
    expected = qfiles | pfiles | {row['path'] for row in additions}
    selected = selection['files']; selected_map = {row['path']: row for row in selected}
    need(len(selected) == len(selected_map) == len(expected) == args.expected_selected_files and set(selected_map) == expected and
         sum(row['bytes'] for row in selected) == args.expected_selected_bytes, 'whole exact selected population')
    directories = {row['path']: row['stat'] for row in selection['directories']}
    need(len(directories) == len(selection['directories']) and set(directories) == qdirs | pdirs, 'whole selected directory census')
    aliases = set()
    for row in selected:
        check_pin(row); need(identity(row['path']) == row['stat'], 'selected file stat differs from frozen selection')
        inode = (row['stat']['dev'], row['stat']['ino'])
        need(inode not in aliases, 'selected hardlink or alias'); aliases.add(inode)
        need(row['bytes'] <= 14 * 1024**2, 'selected member exceeds fixed cap')
    for path, stamp in directories.items():
        need(identity(path) == stamp, 'frozen directory stat changed')
    for row in seal['files'] + additions:
        check_pin(row); need(bare(row) == bare(selected_map[row['path']]), 'selected role byte pin differs')
    check_pin(plan['final_plan_producer']); check_pin(plan['final_plan_request'])
    need(plan['final_plan_producer'] == actual_pin(S4 / 'freeze_final_plan_01.py') and
         plan['final_plan_producer']['path'] in selected_map, 'executed final-plan producer selected exactly')
    provenance = load(plan['provenance_map'])
    need(provenance['schema'] == 'ranker-objective-scalar-publication-provenance-map@1' and
         provenance['request'] == plan['final_plan_request'] and
         provenance['copies_are_source_or_receipt_history_not_new_qualification'] is True, 'exact source-only provenance map')
    need(len({row['original']['path'] for row in provenance['copies']}) == len(provenance['copies']), 'unique original provenance census')
    for row in provenance['copies']:
        check_pin(row['original']); check_pin(row['captured'])
        need(row['byte_exact_clone'] is True and row['captured']['path'] in selected_map and
             bare(row['captured']) == bare(selected_map[row['captured']['path']]) and
             (row['original']['bytes'], row['original']['sha256']) == (row['captured']['bytes'], row['captured']['sha256']) and
             bounded_read(row['original'], 14 * 1024**2) == bounded_read(row['captured'], 14 * 1024**2), 'captured provenance differs')
    final_request = load(plan['final_plan_request'])
    need(final_request['file_seal'] == plan['documents']['file_seal'] and
         final_request['qualified_review'] == plan['documents']['qualified_review'] and
         final_request['sealed_regular_files'] == args.expected_sealed_files and
         final_request['sealed_regular_bytes'] == args.expected_sealed_bytes, 'final request seal/count joins')
    peers = final_request['peer_reviews']; peer_map = {row['role']: row for row in peers}
    need(len(peer_map) == len(peers) and len({row['receipt']['path'] for row in peers}) == len(peers), 'distinct peer-review roles and receipts')
    for peer in peers:
        body = load(peer['receipt']); check_pin(peer['producer'])
        need(body['status'] == peer['expected_status'] and body[peer['issue_field']] == [] and
             any(body.get(key) == peer['producer'] for key in ['review_source', 'reviewer', 'producer']), 'passed source-bound peer review')
        authority_false(body)
    source_review = load(peer_map['publication_source']['receipt'])
    need(source_review['schema'] == 'ranker-objective-scalar-publication-independent-source-review@1' and
         source_review['status'] == 'passed_source_only' and source_review['outstanding_source_issues'] == [], 'actual publication source review')
    source_paths = [S4 / name for name in ['SOURCE_API.md', 'build_package.py', 'freeze_inputs.py', 'review_package.py', 'freeze_final_plan_01.py']]
    source_paths += [R4 / name for name in ['prepare_hf_plan_01.py', 'prepare_invocation_01.py', 'scan_final_upload_01.py', 'review_hf_readback_01.py']]
    reviewed = {row['path']: bare(row) for row in source_review['reviewed_sources']}
    need(len(reviewed) == len(source_review['reviewed_sources']) == 9 and
         reviewed == {str(path): actual_pin(path) for path in source_paths}, 'source review joins all nine actual publication source pins')
    semantic = documents['peer_semantic_native']
    need(semantic['schema'] == 'ranker-objective-scalar-independent-semantic-native-review@1' and
         semantic['status'] == 'passed_file_only_actual_receipt_review' and semantic['outstanding_review_issues'] == [] and
         semantic['actual_distinct_kernel_queries'] == 14 and semantic['actual_native_invocations'] == 2 and
         semantic['actual_AST_phase']['slices'] == plan['documents']['source_IR'], 'actual independent semantic/kernel scope')
    request = load(actual_pin(Q / 'preparation/request-v3.json'))
    need(len(request['strict_old_inputs']) == 2108 and len(request['protected_live_sources']) == 4, 'old/live guard denominator')
    for row in request['strict_old_inputs'] + request['protected_live_sources']:
        check_pin(row); need(guard_map.get(row['path']) == bare(row), 'request guard omitted or changed in publication guard census')
    for guard in review['original_checkout_guards'].values():
        check_pin(guard['index'])
    need({entry['mode'] for entry in review['native_checks']} == {'lean-objective-scalar-01', 'lean-objective-generated-01'} and
         len(review['native_checks']) == 2, 'all actual native attempts')
    observations = [native(entry) for entry in review['native_checks']]
    need(sum(row['query_count_qualified'] for row in observations) == 14 and all(row['status'] == 'passed' for row in observations), 'actual qualified query census')
    need({row['path'] for row in plan['documents'].values() if Path(row['path']).name == 'check-result.json'} ==
         {str(path) for path in (Q / 'evidence').glob('*/check-result.json')}, 'no omitted actual native check')
    phase_modes = []
    for phase in review['phases']:
        body = load(phase); outer_pin = actual_pin(Q / 'evidence' / (body['mode'] + '-closed.json'))
        phase_modes.append(body['mode'])
        owned, outer = closed_phase(phase, outer_pin)
        need(owned['status'] == 'passed' and outer['returncode'] == 0 and owned['strict_old_input_count'] == 2108 and
             owned['protected_live_source_count'] == 4 and owned['all_strict_old_and_protected_live_inputs_unchanged'] is True,
             'actual phase passed with complete unchanged guards')
    expected_modes = {'compile-source-objective-01', 'pure-tests-objective-01', 'lean-objective-scalar-01',
                      'lean-objective-generated-01', 'metadata-objective-01'}
    need(len(phase_modes) == len(set(phase_modes)) == 5 and set(phase_modes) == expected_modes and
         {path.parent.name for path in (Q / 'evidence').glob('*/closed.json')} == expected_modes, 'complete unique actual owned phase modes')
    pure = load(actual_pin(Q / 'evidence/pure-tests-objective-01/closed.json'))
    pure_phases = load(actual_pin(Q / 'evidence/pure-tests-objective-01/phases.json'))
    need(pure['selected_test_count'] == 98 and pure['pytest_returncode'] == 0 and len(pure_phases) == 294 and
         all(row['outcome'] == 'passed' for row in pure_phases) and pure['native_runner_calls_refused'] ==
         pure['direct_process_calls_refused'] == 0, 'actual 98 pure controls with no process/native calls')
    compile_receipt = load(actual_pin(Q / 'evidence/compile-source-objective-01/closed.json'))
    need(type(compile_receipt['source_AST_parse_calls']) is int and compile_receipt['source_AST_parse_calls'] == 2 and
         type(compile_receipt['source_function_execution_calls']) is int and compile_receipt['source_function_execution_calls'] == 0,
         'actual two AST parses and zero ranker source execution')
    slices = documents['source_IR']
    need(slices['schema'] == 'ranker-objective-scalar-source-slices@1' and slices['status'] == 'compiled_source_only_kernel_pending' and
         slices['source']['sha256'] == '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a' and
         slices['source_function_execution_calls'] == 0 and slices['host_AST_parse_calls'] == 1 and slices['theorem_qualified'] is False,
         'source-only AST receipt remains unpromoted')
    metadata = documents['metadata_readback']
    need(metadata['status'] == 'passed' and metadata['metadata_family_count'] == 32 and metadata['metadata_row_count'] == 4458 and
         metadata['additive_payload_rows'] == 18 and metadata['metadata_build_receipt'] == review['metadata_build_receipt'], 'metadata native/readback/closure joins')
    built = load(review['metadata_build_receipt']); current = load(built['metadata_inputs']); prior = load(built['prior_metadata'])
    need(built['schema'] == 'ranker-objective-scalar-metadata-file-build@1' and built['status'] == 'passed' and
         built['frozen_build_plan'] == metadata['frozen_build_plan'] and
         wire(current) == wire(load(metadata['metadata_inputs'])) and set(current) == set(prior) and len(current) == 32 and
         sum(map(len, prior.values())) == 4440 and sum(map(len, current.values())) == 4458, 'complete metadata family/input census')
    for family, rows in prior.items():
        need(wire(current[family][:len(rows)]) == wire(rows), 'old canonical metadata prefix changed')
    need(wire(current['vectors']) == wire(prior['vectors']) and len(current['vectors']) == 375 and
         wire(current['contracts']) == wire(prior['contracts']) and len(current['contracts']) == 2, 'vectors and domain contracts unchanged')
    manifest_path = Q / 'evidence/metadata-objective-01/metadata/manifest.json'
    manifest_pin = actual_pin(manifest_path); manifest = load(manifest_pin)
    report, fresh = metadata['native_report'], metadata['fresh_process_readback']
    need(report['manifest_sha256'] == fresh['manifest_sha256'] == 'sha256:' + manifest_pin['sha256'] and
         report['limits']['families'] == manifest['limits']['families'] == 32 and
         report['row_count'] == manifest['row_count'] == fresh['row_count'] == 4458 and fresh['verified'] is True and
         report['row_root_sha256'] == fresh['row_root_sha256'] == manifest['row_root_sha256'] and
         report['lake_snapshot_digest'] == fresh['lake_snapshot_digest'] == manifest['lake_snapshot_digest'], 'complete native fresh-process joins')
    for family, info in manifest['families'].items():
        export = info['export']; path = manifest_path.parent / export['relative_path']
        raw = bounded_read({'path': str(path), 'bytes': export['bytes'], 'sha256': export['sha256'].removeprefix('sha256:')}, 14 * 1024**2)
        need(len(raw) == export['bytes'] and 'sha256:' + hashlib.sha256(raw).hexdigest() == export['sha256'], 'export byte pin mismatch')
        rows = [parse(line) for line in raw.splitlines()]
        need(len(rows) == info['count'] == len(current[family]) and all(row['family'] == family for row in rows) and
             wire([row['payload'] for row in rows]) == wire(current[family]), 'whole family export payload differs')
    for field in ['CPython_math_fsum_semantics_proved', 'binary64_error_bound_proved', 'feature_preparation_to_IR_translation_proved',
                  'full_training_loop_to_IR_translation_proved', 'global_autoencoder_convergence_proved', 'host_parser_correctness_theorem_proved',
                  'native_Float_optimizer_convergence_proved', 'objective_to_IR_translation_proved', 'computed_gradient_source_equivalence_proved',
                  'python_ranker_source_equivalence_proved', 'whole_codebase_IR_semantic_preservation_proved']:
        need(review[field] is False, 'broad source/numeric scope promoted')
    for field in ['new_autoencoder_fits', 'new_feature_preparations', 'new_gradient_evaluations', 'new_optimizer_updates', 'new_public_fits', 'new_ranker_training_trace_replays']:
        need(type(review[field]) is int and review[field] == 0, 'new numerical/model work outside scope')
    need(review['full_task_satisfaction'] == 'unknown' and review['all32_governing_RPI_exits'] == 'OPEN', 'task and RPI remain open')
    for body in [review, seal, slices, metadata, documents['open_obligations']]:
        authority_false(body)
    for path, stamp in directories.items():
        need(identity(path) == stamp, 'selected directory changed during review')
    for row in selected:
        check_pin(row); need(identity(row['path']) == row['stat'], 'selected file changed during review')
    need(regular_tree(Q) == (qfiles, qdirs) and regular_tree(P6) == (pfiles, pdirs), 'whole selected source roots changed')
    for row, stamp in CHECKED.values():
        need(identity(row['path']) == stamp, 'observed input changed before receipt')
    for row in PINS.values():
        check_pin(row)
    receipt = {'schema': 'ranker-objective-scalar-final-publication-input-review@1',
        'status': 'passed_file_only_final_publication_input_review', 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': actual_pin(Path(__file__).resolve()), 'fixed_inputs': PINS, 'outstanding_issues': [],
        'typed_facts_verified': len(facts), 'selected_regular_files': len(selected), 'selected_regular_bytes': sum(row['bytes'] for row in selected),
        'selected_directories': len(directories), 'selected_aliases': 0, 'exclusions': [],
        'sealed_regular_files_without_seal_self': args.expected_sealed_files, 'sealed_regular_bytes_without_seal_self': args.expected_sealed_bytes,
        'whole_candidate_regular_files_with_seal_self': len(qfiles), 'whole_source_plan_regular_files': len(pfiles),
        'explicit_additions': len(additions), 'provenance_clones_verified': len(provenance['copies']), 'peer_reviews_verified': len(peers),
        'native_checks': observations, 'actual_native_calls': 2, 'qualified_native_checks': 2, 'qualified_theorem_queries': 14,
        'complete_chunk_object_joins_verified_in_memory': True, 'native_bounds': BOUNDS,
        'prior_protected_input_files': 2108, 'protected_live_source_files': 4, 'inherited_guard_population': 2393,
        'metadata_families': 32, 'metadata_payloads': 4458, 'prior4440_payload_prefixes_verified': True,
        'vectors375_unchanged': True, 'contracts2_unchanged': True, 'new_domain_contract_rows': 0, 'runtime_contracts_claimed': False,
        'whole_before_after_selection_pins_and_stats_verified': True, 'file_pins_rehashed': len(CHECKED), 'raw_file_bytes_read_for_digest': READ_BYTES,
        'elapsed_seconds': time.monotonic() - started, 'target_imports_or_executions': 0, 'native_or_model_jobs': 0,
        'codec_calls': 0, 'Git_or_HTTP_calls': 0, 'remote_mutations': 0, 'sealed_scope_writes': 0,
        'python_source_equivalence_proved': False, 'python_Float_semantics_proved': False, 'objective_source_translation_proved': False,
        'gradient_source_translation_proved': False, 'whole_IR_equivalence_proved': False, 'global_autoencoder_convergence_proved': False,
        'full_task_satisfaction': 'unknown', 'official_benchmark_score': None, 'proof_authority': False, 'execution_authority': False,
        'completion_authority': False, 'planner_activation': False, 'all32_governing_RPI_exits': 'OPEN'}
    destination = OUT / 'review-receipt.json'
    with destination.open('xb') as stream:
        stream.write((json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())
        stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({'status': receipt['status'], 'receipt': actual_pin(destination), 'selected_files': len(selected),
                      'selected_bytes': receipt['selected_regular_bytes']}))


if __name__ == '__main__':
    main()
