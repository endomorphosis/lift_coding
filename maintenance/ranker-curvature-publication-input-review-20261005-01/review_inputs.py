"""Independent file-only plan and frozen-selection review; stdlib only.

Never imports production/project sources or invokes classifiers, decoders,
provers, tests, models, SQL, dependency setup, Git, or network operations.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = WORKSPACE / 'maintenance/ranker-curvature-publication-source-plan-20261005-01'
Q = WORKSPACE / 'qualification/codebase_ir/ranker-real-curvature-20261005-01'
OWN = WORKSPACE / 'maintenance/ranker-curvature-publication-input-review-20261005-01'
PLAN_SHA = '80c269c217d867be827060d50fc86cf272b53e9607c397d54055effcb20783a7'
POLICY_SHA = '50deb4972264d45a543de861d9c51e72b9862d10c5ce7664810e3f3e277aeecf'
SEAL_SHA = '6c281bd21da026b27797f78f98d0932bad4e7a115779a4fc348ee6987f30af15'
REVIEW_SHA = '2c98df30a37fecffff99340d447dcf548c6c244a53223cbed39c914bb0e9238c'
SOURCE_PINS = {
    'build_package.py': '4e14c08fc6d680e5fcbf755f649284f750353b73b42dd08b926398f4c43c9a93',
    'review_package.py': 'cdb6dbea925e3bc3ae8d62c6b7c069bfcbe1fd79bf07282e32ed06a68daf88f9',
    'freeze_inputs.py': '830d457108a95a8ccd29ee8a75af9742bc749336df1e87dabccaf8327aa2c041',
    'API.md': '3e66da5ea15246cb27cfefe79514cd533e14342b763614446cc6c9cacf0039ca',
    'publication-profile-authorization.json': '3b0c8fd91ccd62fdc65e2cf557da6175eb6e48aef8b95996315113ff534bc638',
}
EXTERNAL = (Q / 'environment/mathlib4', Q / 'environment/cache')
FILE_MAX = 16 * 1024**2
deadline = None


def need(value, reason):
    if value is not True:
        raise ValueError(reason)
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError('bounded file-only review deadline')


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def signature(info):
    return {key: getattr(info, 'st_' + key) for key in ('dev', 'ino', 'mode', 'nlink', 'uid', 'gid', 'size', 'mtime_ns', 'ctime_ns')}


def pin(path, retain=False):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path, 'canonical regular path required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= FILE_MAX, 'bounded regular file required')
        digest, count, blocks = hashlib.sha256(), 0, []
        while block := os.read(fd, 1024**2):
            count += len(block)
            need(count <= FILE_MAX, 'file growth bound')
            digest.update(block)
            if retain:
                blocks.append(block)
        need(count == before.st_size and signature(before) == signature(os.fstat(fd)) == signature(path.lstat()), 'input changed during read')
        return {'path': str(path), 'bytes': count, 'sha256': digest.hexdigest()}, b''.join(blocks)
    finally:
        os.close(fd)


def document(row):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}, 'exact descriptor required')
    observed, raw = pin(row['path'], True)
    need(observed == row, 'document descriptor mismatch')
    return json.loads(raw)


def pointer(value, text):
    need(type(text) is str and (text == '' or text.startswith('/')), 'valid JSON pointer required')
    for part in text.strip('/').split('/') if text else []:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if type(value) is list else value[part]
    return value


def alias(row):
    need(type(row) is dict and set(row) == {'path', 'target', 'bytes', 'sha256', 'stat'}, 'exact fixture alias row required')
    path = Path(row['path'])
    before = path.lstat()
    seven = lambda info: [getattr(info, 'st_' + key) for key in ('dev', 'ino', 'mode', 'nlink', 'size', 'mtime_ns', 'ctime_ns')]
    relative = path.relative_to(Q)
    need(stat.S_ISLNK(before.st_mode) and len(relative.parts) == 4 and relative.parts[0] == 'evidence' and
         relative.parts[1].startswith('pure-tests') and relative.parts[2] == 'fixtures' and relative.parts[3].endswith('current'),
         'only declared direct fixture links permitted')
    literal = os.readlink(path)
    raw = literal.encode('utf-8')
    target = Path(literal) if Path(literal).is_absolute() else path.parent / literal
    need(literal == row['target'] and len(raw) == row['bytes'] == before.st_size and
         hashlib.sha256(raw).hexdigest() == row['sha256'] and seven(before) == row['stat'], 'fixture link literal/stat mismatch')
    need(path.parent.resolve(strict=True) == path.parent and target.parent == path.parent and target.resolve(strict=True) == target and
         stat.S_ISDIR(target.lstat().st_mode) and not target.is_symlink(), 'real canonical sibling fixture target required')
    need(os.readlink(path) == literal and seven(path.lstat()) == row['stat'], 'fixture link changed during read')
    return {'path': str(path), 'kind': 'transient_fixture_symlink',
            'reason': 'sealed literal pytest convenience alias; real sibling bodies selected once',
            'target': literal, 'bytes': len(raw), 'sha256': row['sha256'], 'stat': row['stat']}


def inventory(plan):
    regular, exclusions, directories = [], [], []
    aliases = {row['path']: row for row in plan['excluded_fixture_symlinks']}
    locks = set(plan['excluded_zero_byte_locks'])
    def visit(path):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            need(str(path) in aliases, 'undeclared symlink refused')
            exclusions.append(alias(aliases[str(path)]))
        elif path in EXTERNAL:
            need(path.resolve(strict=True) == path and stat.S_ISDIR(info.st_mode), 'actual excluded external directory required')
            exclusions.append({'path': str(path), 'kind': 'external_dependency_subtree',
                'reason': 'exact retained dependency profiles and official source revision; raw bodies not published', 'stat': signature(info)})
        elif stat.S_ISDIR(info.st_mode):
            need(path.resolve(strict=True) == path, 'canonical owned directory required')
            directories.append({'path': str(path), 'stat': signature(info)})
            for child in sorted(path.iterdir(), key=lambda item: os.fsencode(item.name)):
                visit(child)
        elif stat.S_ISREG(info.st_mode):
            if str(path) in locks:
                need(path.name.endswith('.lock') and info.st_size == 0, 'only exact empty runtime locks excluded')
                exclusions.append({'path': str(path), 'kind': 'transient_lock',
                    'reason': 'exact sealed closed-runtime zero-byte lock', 'stat': signature(info)})
            else:
                regular.append(path)
        else:
            raise ValueError('unsupported owned node')
    visit(Q)
    for text in plan['explicit_addition_paths']:
        path = Path(text)
        if not path.is_relative_to(Q):
            visit(path)
    need(len(regular) == len(set(regular)), 'unique complete selected regular inventory required')
    return sorted(regular, key=lambda item: os.fsencode(str(item.relative_to(WORKSPACE)))), exclusions, directories


def source_constants():
    held = {}
    trees = {}
    for name, expected in SOURCE_PINS.items():
        row, raw = pin(ROOT / name, True)
        need(row['sha256'] == expected, 'reviewed publication source differs')
        held[name] = row
        if name.endswith('.py'):
            trees[name] = ast.parse(raw, filename=name)
    for function in ('validate_semantics', 'fixture_alias'):
        nodes = [next(node for node in trees[name].body if isinstance(node, ast.FunctionDef) and node.name == function)
                 for name in ('build_package.py', 'review_package.py')]
        need(ast.dump(nodes[0], include_attributes=False) == ast.dump(nodes[1], include_attributes=False), 'source-reviewed validators differ')
    constants = {}
    for node in trees['build_package.py'].body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('BOUNDARIES', 'REQUIRED_THEOREMS', 'SOURCE_AUTHORED_EXTRA_AXIOM_QUERY'):
            constants[node.targets[0].id] = ast.literal_eval(node.value)
    return held, constants


def actual_native_and_cache(plan, documents, seal_files, constants):
    roles = plan['semantic_roles']
    need(len(roles['positive_native_checks']) == 10 and len(roles['negative_native_checks']) == 1 and
         len(roles['qualified_cache_acceptances']) == 10, 'exact actual10/1/10 role population required')
    native, theorem_union, reconstructed_bytes, chunk_count = {}, set(), 0, 0
    bounds = {'timeout_seconds': 20, 'cpu_seconds': 20, 'max_input_bytes': 262144, 'max_output_bytes': 65536, 'max_workspace_bytes': 16777216}
    for name in roles['positive_native_checks']:
        check = documents[name]
        need(check['status'] == 'passed' and check['expected_success'] is True and check['matches_expectation'] is True and
             check['returncode'] == 0 and check['native_invocations'] == 1 and wire(check['native_bounds']) == wire(bounds) and
             check['workspace_cleaned'] is True and check['artifact_anomalies'] == [] and check['axiom_report_error'] is None and
             check['post_call_binding_error'] is None and all(check[key] is False for key in
                 ('timed_out', 'cancelled', 'unavailable', 'resource_exhausted', 'output_truncated', 'workspace_limit_exceeded')),
             'clean actual bounded positive receipt required')
        registry = check['theorem_axiom_output']
        for row in registry:
            need(set(row['axioms']) <= {'propext', 'Classical.choice', 'Quot.sound'} and row['report_occurrences'] > 0,
                 'actual queried standard axioms required')
            theorem_union.add(row['theorem'])
        extra = constants['SOURCE_AUTHORED_EXTRA_AXIOM_QUERY']
        label = re.escape("'" + extra + "'")
        reports = re.findall(label + r' depends on axioms: \[([^\]]*)\]', check['stdout'])
        empties = len(re.findall(label + ' does not depend on any axioms', check['stdout']))
        if reports or empties:
            observed = [[part.strip() for part in text.split(',') if part.strip()] for text in reports] + [[]] * empties
            need(all(parts == observed[0] for parts in observed) and set(observed[0]) <= {'propext', 'Classical.choice', 'Quot.sound'},
                 'separate source-authored mean-L stdout query must be consistent and standard')
            theorem_union.add(extra)
        for field in ('source', 'augmented_source', 'environment_manifest'):
            need(check[field] == seal_files[check[field]['path']], 'actual checked source/profile must be sealed')
        objects = check['compiled_artifacts']
        for row in objects:
            base = {key: row[key] for key in ('path', 'bytes', 'sha256')}
            need(row['complete'] is True and seal_files[row['path']] == base, 'complete actual compiled object must be sealed')
        if check['schema'].endswith('@2'):
            manifest_row = check['retention_manifest']
            base = {key: manifest_row[key] for key in ('path', 'bytes', 'sha256')}
            manifest_body = check['retention_manifest_body']
            raw_manifest = wire(manifest_body) + b'\n'
            need(manifest_row['complete'] is True and seal_files[base['path']] == base and len(raw_manifest) == base['bytes'] and
                 hashlib.sha256(raw_manifest).hexdigest() == base['sha256'], 'exact actual chunk manifest bytes required')
            chunks = check['retained_chunk_artifacts']
            by_name = {}
            for index, row in enumerate(chunks):
                base = {key: row[key] for key in ('path', 'bytes', 'sha256')}
                actual, raw = pin(row['path'], True)
                name = Path(row['path']).name
                need(row['complete'] is True and actual == base == seal_files[base['path']] and len(raw) <= 65536 and
                     name == 'LeanProofChunk%03d.bin' % index, 'actual complete ordered bounded chunks required')
                by_name[name] = raw
            need(len(chunks) == len(manifest_body['chunks']) <= 61 and manifest_body['status'] == 'complete', 'complete chunk population required')
            total, used = 0, []
            for descriptor, object_row in zip(manifest_body['objects'], objects):
                raw = b''.join(by_name[name] for name in descriptor['chunks'])
                need(descriptor['bytes'] == len(raw) == object_row['bytes'] and
                     hashlib.sha256(raw).hexdigest() == descriptor['sha256'] == object_row['sha256'],
                     'fresh file-only concatenation must match complete actual object')
                total += len(raw)
                used.extend(descriptor['chunks'])
            need(total == manifest_body['aggregate_raw_object_bytes'] <= 3997696 and used == list(by_name), 'complete chunk partition bound required')
            reconstructed_bytes += total
            chunk_count += len(chunks)
        native[hashlib.sha256(wire(check)).hexdigest()] = check
    need(constants['REQUIRED_THEOREMS'] <= theorem_union, 'all required actual theorem endpoints and separate mean-L query covered')
    negative = documents[roles['negative_native_checks'][0]]
    need(negative['status'] == 'rejected' and negative['expected_success'] is False and negative['matches_expectation'] is True and
         negative['stdout'].count('error:') == 1 and negative['stderr'] == '' and
         'Tactic `decide` proved that the proposition' in negative['stdout'] and
         re.search(r'proposition\s+False\s+is false', negative['stdout']) is not None, 'genuine logical false control required')
    numeric = documents[roles['original_numeric_binding']]
    numeric_sha = hashlib.sha256(wire(numeric)).hexdigest()
    need(numeric['corpus_sha256'] == 'sha256:d4aa22b9a7bfe796c31adbcf78f9b72987549a85117b8f08534f5a06c032a3df' and
         numeric['dimension'] == 80 and numeric['pair_count'] == 4, 'original numeric corpus and4x80 shape required')
    for name in roles['qualified_cache_acceptances']:
        entry = documents[name]
        need(entry['schema'] == 'terminal-ranker-real-curvature-proof-cache-entry@2' and
             entry['status'] == 'qualified_advisory_real_model_theorem' and entry['native_check_sha256'] in native,
             'actualV2 advisory cache/native check join required')
        dimensions, check = entry['cache_dimensions'], native[entry['native_check_sha256']]
        need(dimensions['numeric_binding_sha256'] == numeric_sha and dimensions['corpus_sha256'] == numeric['corpus_sha256'] and
             dimensions['proof_source_sha256'] == check['source']['sha256'] and dimensions['environment_manifest_sha256'] == check['environment_manifest']['sha256'] and
             dimensions['theorem'] in {row['theorem'] for row in check['theorem_axiom_output']}, 'actual canonical numeric/source/theorem cache dimensions required')
    return {'actual_positive_checks': 10, 'genuine_false_control_checks': 1, 'actual_advisory_cache_entries': 10,
            'fresh_file_only_chunk_concatenations_verified_bytes': reconstructed_bytes, 'physical_chunks_verified': chunk_count,
            'additional_meanL_source_stdout_query_claimed_as_parsed_registry': False}


def review(phase, output, expected_closed=None, expected_selection=None):
    global deadline
    deadline = time.monotonic() + 120
    own_pin = pin(Path(__file__).resolve())[0]
    plan_pin, raw = pin(ROOT / 'plan.json', True)
    policy_pin, facts_raw = pin(ROOT / 'required-facts.json', True)
    need(plan_pin['sha256'] == PLAN_SHA and policy_pin['sha256'] == POLICY_SHA, 'exact root-frozen plan/policy pins required')
    plan, facts = json.loads(raw), json.loads(facts_raw)
    need(plan['schema'] == 'ranker-curvature-publication-plan@1' and plan['source_and_artifacts_quiet'] is True and
         plan['expected_sealed_file_count'] == 1080 and plan['expected_sealed_file_bytes'] == 273066128 and len(facts) == 240 and
         len(plan['documents']) == 29 and len(plan['excluded_fixture_symlinks']) == 19 and len(plan['excluded_zero_byte_locks']) == 40,
         'exact observed plan/fact/seal/alias/lock population required')
    source_pins, constants = source_constants()
    documents = {name: document(row) for name, row in plan['documents'].items()}
    need(plan['semantic_policy'] == policy_pin and plan['documents']['file_seal']['sha256'] == SEAL_SHA and
         plan['documents']['qualified_review']['sha256'] == REVIEW_SHA, 'exact actual qualification closure pins required')
    for fact in facts:
        need(type(fact) is dict and set(fact) == {'document', 'pointer', 'equals'} and
             wire(pointer(documents[fact['document']], fact['pointer'])) == wire(fact['equals']), 'actual typed semantic fact mismatch')
    qualified = documents['qualified_review']
    need(qualified['schema'] == 'ranker-real-curvature-closed-qualification-review@1' and qualified['status'] == 'passed' and
         qualified['native_lean_calls'] == 19, 'actual qualified19-call review required')
    for name, value in constants['BOUNDARIES'].items():
        need(wire(qualified[name]) == wire(value) and {'document': 'qualified_review', 'pointer': '/' + name, 'equals': value} in facts,
             'all conservative boundaries explicitly fact-gated')
    seal = documents['file_seal']
    need(seal['review'] == plan['documents']['qualified_review'] and len(seal['files']) == 1080 and
         sum(row['bytes'] for row in seal['files']) == 273066128 and
         hashlib.sha256(wire(seal['files'])).hexdigest() == seal['file_inventory_sha256'] and
         wire(seal['fixture_symlinks']) == wire(plan['excluded_fixture_symlinks']) and
         hashlib.sha256(wire(seal['fixture_symlinks'])).hexdigest() == seal['fixture_symlink_inventory_sha256'], 'complete actual regular/alias seal digests required')
    seal_files = {row['path']: row for row in seal['files']}
    need(len(seal_files) == 1080, 'unique sealed leaves required')
    for row in seal['files']:
        need(pin(row['path'])[0] == row, 'sealed file changed before review')
    lock_set = {row['path'] for row in seal['files'] if Path(row['path']).name.endswith('.lock') and row['bytes'] == 0}
    need(lock_set == set(plan['excluded_zero_byte_locks']) and len(lock_set) == 40, 'all and only40empty*.lock exclusions required')
    for row in seal['fixture_symlinks']:
        alias(row)
    snapshot = inventory(plan)
    selected, excluded, directories = snapshot
    expected = (set(seal_files) - lock_set) | set(plan['explicit_addition_paths'])
    need({str(path) for path in selected} == expected and len(selected) == len(expected), 'complete seal plus exact fixed additions required')
    selected_rows = [{**pin(path)[0], 'stat': signature(path.lstat())} for path in selected]
    selected_map = {row['path']: row for row in selected_rows}
    for row in plan['documents'].values():
        need({key: selected_map[row['path']][key] for key in ('path', 'bytes', 'sha256')} == row, 'every pinned outcome document selected')
    need(sum(row['bytes'] for row in selected_rows) <= 320 * 1024**2 and plan['publication_profile']['raw_population_max'] == 320 * 1024**2 and
         plan['publication_profile']['aggregate_decoded_work_max'] == 1024**3 and plan['publication_profile']['per_file_max'] == FILE_MAX and
         plan['publication_profile']['per_decoded_container_max'] == FILE_MAX and plan['publication_profile']['wall_seconds'] == 180,
         'exact publication-only resource envelope required')
    semantic = actual_native_and_cache(plan, documents, seal_files, constants)
    metadata = documents[plan['semantic_roles']['native_metadata_readback']]
    need(type(metadata['fresh_process_readback']) is dict and metadata['fresh_process_readback']['verified'] is True,
         'actual fresh-process metadata verified dictionary required')
    frozen = None
    if phase == 'selection':
        need(type(expected_closed) is str and type(expected_selection) is str and re.fullmatch('[0-9a-f]{64}', expected_closed) is not None and
             re.fullmatch('[0-9a-f]{64}', expected_selection) is not None, 'independent final closure/selection pins required')
        closed_pin, closed_raw = pin(ROOT / 'closed-inputs.json', True)
        selection_pin, selection_raw = pin(ROOT / 'final-selection.json', True)
        need(closed_pin['sha256'] == expected_closed and selection_pin['sha256'] == expected_selection, 'actual external final closure/selection pins differ')
        closed, selection = json.loads(closed_raw), json.loads(selection_raw)
        need(closed['schema'] == 'ranker-curvature-publication-closed-inputs@1' and closed['final_selection'] == selection_pin and
             closed['externally_pinned_plan'] == plan_pin and wire(closed['required_facts']) == wire(facts) and
             closed['preparation_source'] == source_pins['freeze_inputs.py'], 'exact prepared plan/policy/source join required')
        for key in set(plan) - {'schema', 'explicit_addition_paths'}:
            need(wire(closed[key]) == wire(plan[key]), 'closed input differs from exact reviewed plan field')
        need(closed['explicit_additions'] == [pin(text)[0] for text in plan['explicit_addition_paths']] and
             selection['schema'] == 'ranker-curvature-publication-final-selection@1' and selection['files'] == selected_rows and
             selection['exclusions'] == excluded and selection['directories'] == directories, 'exact complete prepared selection/inventory/stat required')
        frozen = {'closed_inputs': closed_pin, 'final_selection': selection_pin}
    for row in seal['files']:
        need(pin(row['path'])[0] == row, 'sealed leaf changed after review')
    for row in seal['fixture_symlinks']:
        alias(row)
    need(inventory(plan) == snapshot and all(pin(row['path'])[0] == {key: row[key] for key in ('path', 'bytes', 'sha256')} for row in selected_rows),
         'full selected population/hash/stat changed after review')
    need(pin(ROOT / 'plan.json')[0] == plan_pin and pin(ROOT / 'required-facts.json')[0] == policy_pin and
         source_constants()[0] == source_pins and pin(Path(__file__).resolve())[0] == own_pin, 'reviewed plan/policy/source drift')
    output = Path(output)
    need(output.is_absolute() and output.parent == OWN and not output.exists(), 'fresh owned review receipt required')
    result = {'schema': 'ranker-curvature-publication-final-input-file-only-review@1', 'status': 'passed', 'phase': phase,
        'plan': plan_pin, 'semantic_policy': policy_pin, 'qualified_review': plan['documents']['qualified_review'],
        'file_seal': plan['documents']['file_seal'], 'reviewer': own_pin, 'publication_source_pins': source_pins,
        'typed_actual_pointer_facts_verified': 240, 'actual_documents_verified': 29,
        'sealed_regular_leaves_verified_before_after': 1080, 'sealed_regular_bytes': 273066128,
        'literal_fixture_aliases_verified_before_after': 19, 'empty_runtime_lock_bindings_verified_before_after': 40,
        'selected_regular_files': len(selected), 'selected_regular_bytes': sum(row['bytes'] for row in selected_rows),
        'selected_inventory_sha256': hashlib.sha256(wire(selected_rows)).hexdigest(),
        'actual_semantic_joins': semantic, 'frozen_selection_join': frozen,
        'fresh_process_metadata_verified': True, 'native_Lean_calls_in_closed_historical_attempts': 19,
        'new_prover_or_test_or_classifier_or_codec_calls': 0, 'project_imports': 0,
        'new_fits': 0, 'new_ranker_replays': 0, 'raw_external_dependency_bodies_read': False,
        'source_atomic': False, 'remote_mutations': 0, **constants['BOUNDARIES']}
    with output.open('xb') as stream:
        stream.write(wire(result) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return pin(output)[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('plan', 'selection'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-closed-inputs-sha256')
    parser.add_argument('--expected-final-selection-sha256')
    args = parser.parse_args()
    print(json.dumps(review(args.phase, args.output, args.expected_closed_inputs_sha256, args.expected_final_selection_sha256), sort_keys=True))
