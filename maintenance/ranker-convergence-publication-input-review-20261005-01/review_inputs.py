#!/usr/bin/env python3
"""Independent input review using only source/JSON and standard filesystem reads."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

WORKSPACE = Path('/home/barberb/lift_coding')
S2 = WORKSPACE / 'maintenance/ranker-convergence-publication-20261005-01'
OUT = WORKSPACE / 'maintenance/ranker-convergence-publication-input-review-20261005-01'
Q3 = WORKSPACE / 'qualification/codebase_ir/ranker-real-convergence-20261005-01'
P4 = WORKSPACE / 'qualification/codebase_ir/ranker-real-convergence-source-plan-20261005-01'
MAX_FILE = 14680064
EXPECTED_INPUTS = {
    'plan.json': (9736, '44674a6e9901d49db15acac1264706cb0aa5ed6a5136ad3dcd38354dd1ef594b'),
    'required-facts.json': (67665, '6312761c32e8c4aa63dca576c19c24b08a5221de0ce68cbb17807b28297dc632'),
    'closed-inputs.json': (1183, '3721e16edddb301d9832001995fb9e685226cb9665852b31732bb148f8e7cdab'),
    'final-selection.json': (178614, '9877c6ef83bc9e554fdd12209152eb749067d47730b294e0928356cf86fc773b'),
}
PROFILE = {'aggregate_decoded_work_max': 1073741824, 'complete_decoded_tar_max': 16777216,
           'compressed_shard_max': 16777216, 'depth_max': 6,
           'duplicate_verification_decoder_invocations': 0,
           'member_readback_profile': 'same_first_decoded_tar_and_member_streams@1',
           'members_max': 10000, 'native_qualification_limits_changed': False,
           'per_file_max': MAX_FILE, 'raw_member_sum_per_shard_max': MAX_FILE,
           'raw_population_max': 268435456, 'shards_max': 64, 'wall_seconds': 180,
           'zstd_args': ['-T1', '-3']}
NATIVE = {'cpu_seconds': 20, 'max_input_bytes': 262144, 'max_output_bytes': 65536,
          'max_workspace_bytes': 16777216, 'timeout_seconds': 20}
input_pins = {}
reads = 0


def need(condition, message):
    if condition is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode()


def signature(info):
    return {name: getattr(info, 'st_' + name)
            for name in ('dev', 'ino', 'mode', 'nlink', 'uid', 'gid', 'size', 'mtime_ns', 'ctime_ns')}


def read_regular(path):
    global reads
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
         'Canonical no-alias absolute input required: ' + str(path))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_FILE,
             'Bounded regular input required: ' + str(path))
        parts = []
        size = 0
        while True:
            block = os.read(fd, 1048576)
            if not block:
                break
            size += len(block)
            need(size <= MAX_FILE, 'Input grew beyond the fixed per-file bound')
            parts.append(block)
        after = os.fstat(fd)
        at_path = path.lstat()
        need(wire(signature(before)) == wire(signature(after)) == wire(signature(at_path))
             and size == before.st_size, 'Input changed during held-byte read: ' + str(path))
        raw = b''.join(parts)
        row = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
               'stat': signature(at_path)}
        reads += 1
        return raw, row
    finally:
        os.close(fd)


def descriptor(row):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}
         and type(row['path']) is str and type(row['bytes']) is int
         and 0 <= row['bytes'] <= MAX_FILE
         and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None,
         'Exact typed regular-file descriptor required')
    raw, observed = read_regular(row['path'])
    need(wire({k: observed[k] for k in ('path', 'bytes', 'sha256')}) == wire(row),
         'Held parsed bytes differ from declared descriptor: ' + row['path'])
    return raw


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'Duplicate JSON key refused')
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw, object_pairs_hook=no_duplicate_keys,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON value: ' + value)))


def pointer(value, address):
    need(type(address) is str and (address == '' or address.startswith('/')), 'JSON pointer required')
    for part in address[1:].split('/') if address else []:
        need(re.search(r'~(?![01])', part) is None, 'Invalid JSON pointer escape')
        key = part.replace('~1', '/').replace('~0', '~')
        if type(value) is list:
            need(re.fullmatch('0|[1-9][0-9]*', key) is not None, 'Canonical array pointer required')
            value = value[int(key)]
        else:
            need(type(value) is dict, 'Pointer traversal requires an object or array')
            value = value[key]
    return value


def json_type(value):
    return {type(None): 'null', bool: 'boolean', int: 'integer', float: 'number',
            str: 'string', list: 'array', dict: 'object'}[type(value)]


def census():
    found = []
    directories = []
    root_counts = {}
    def visit(path):
        info = path.lstat()
        need(not stat.S_ISLNK(info.st_mode) and path.resolve(strict=True) == path,
             'Undeclared alias or referral refused: ' + str(path))
        if stat.S_ISDIR(info.st_mode):
            directories.append({'path': str(path), 'stat': signature(info)})
            for child in sorted(path.iterdir(), key=lambda item: os.fsencode(item.name)):
                visit(child)
        else:
            need(stat.S_ISREG(info.st_mode), 'Nonregular population leaf refused: ' + str(path))
            found.append(path)
    visit(Q3)
    root_counts['Q3'] = len(found)
    visit(P4)
    root_counts['P4'] = len(found) - root_counts['Q3']
    for row in PLAN['explicit_additions']:
        path = Path(row['path'])
        need(path.is_relative_to(S2) or path.is_relative_to(Q3), 'Explicit addition left declared roots')
        need(path.name not in ('plan.json', 'closed-inputs.json', 'final-selection.json'),
             'Self-referential frozen control output selected')
        if path not in found:
            visit(path)
    need(len(found) == len(set(found)), 'Duplicate selected file')
    rows = []
    raw_by_path = {}
    for path in sorted(found, key=lambda item: os.fsencode(str(item.relative_to(WORKSPACE)))):
        raw, row = read_regular(path)
        rows.append(row)
        raw_by_path[str(path)] = raw
    return rows, directories, root_counts, raw_by_path


def main():
    global PLAN
    for name, (size, expected) in EXPECTED_INPUTS.items():
        raw, row = read_regular(S2 / name)
        need(row['bytes'] == size and row['sha256'] == expected, 'Externally supplied input pin changed: ' + name)
        input_pins[name] = {k: row[k] for k in ('path', 'bytes', 'sha256')}
    PLAN = parse(descriptor(input_pins['plan.json']))
    closure = parse(descriptor(input_pins['closed-inputs.json']))
    selection = parse(descriptor(input_pins['final-selection.json']))
    need(PLAN['schema'] == 'ranker-convergence-publication-plan@1' and PLAN['status'] == 'frozen_final_plan'
         and PLAN['source_and_artifacts_quiet'] is True and PLAN['source_plan_quiet'] is True,
         'Quiet final publication plan required')
    need(PLAN['scope_root'] == str(Q3) and PLAN['source_plan_root'] == str(P4), 'Exact Q3/P4 roots required')
    need(wire(PLAN['publication_profile']) == wire(closure['publication_profile']) == wire(PROFILE),
         'Exact fixed publication profile required')
    need(closure['schema'] == 'ranker-convergence-publication-closed-inputs@1'
         and wire(closure['plan']) == wire(input_pins['plan.json'])
         and wire(closure['final_selection']) == wire(input_pins['final-selection.json']), 'Exact control joins required')
    descriptor(closure['preparation_source'])
    documents = {name: parse(descriptor(row)) for name, row in PLAN['documents'].items()}
    need(len(documents) == 15, 'Exact pinned-document denominator required')
    need(wire(PLAN['semantic_policy']) == wire(input_pins['required-facts.json']), 'Exact fact-policy pin required')
    facts = parse(descriptor(PLAN['semantic_policy']))
    need(type(facts) is list and len(facts) == 329, 'Exact fact denominator required')
    seen = set()
    observed_facts = []
    type_counts = {}
    for fact in facts:
        need(type(fact) is dict and set(fact) == {'document', 'pointer', 'equals'}
             and type(fact['document']) is str and fact['document'] in documents,
             'Exact fact role/pointer/value required')
        key = (fact['document'], fact['pointer'])
        need(key not in seen, 'Duplicate fact pointer')
        seen.add(key)
        actual = pointer(documents[fact['document']], fact['pointer'])
        need(wire(actual) == wire(fact['equals']), 'Exact typed fact mismatch: ' + repr(key))
        value_type = json_type(actual)
        type_counts[value_type] = type_counts.get(value_type, 0) + 1
        observed_facts.append({'document': key[0], 'pointer': key[1], 'type': value_type,
                               'equal_json_wire_sha256': hashlib.sha256(wire(actual)).hexdigest()})
    seal = documents['file_seal']
    need(seal['schema'] == PLAN['seal_schema'] and seal['regular_file_count'] == len(seal['files']) == 378
         and seal['regular_file_bytes'] == sum(row['bytes'] for row in seal['files']) == 147093916,
         'Exact complete Q3 seal census required')
    need(hashlib.sha256(wire(seal['files'])).hexdigest() == seal['file_inventory_sha256'], 'Seal inventory digest differs')
    need(PLAN['excluded_dependency_subtrees'] == [] and seal.get('excluded_dependency_roots', []) == []
         and seal.get('excluded_dependency_subtrees', []) == [] and selection['exclusions'] == []
         and seal['fixture_symlinks'] == [], 'Zero exclusions and aliases required')
    need(wire(seal['review']) == wire(PLAN['documents']['qualified_review']), 'Seal/review join differs')
    review = documents['qualified_review']
    need(review['status'] == 'passed' and review['full_task_satisfaction'] == 'unknown'
         and review['all32_governing_RPI_exits'] == 'OPEN'
         and all(review[k] is False for k in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')),
         'No operational/full-task authority may be inferred')
    checks = {row['path'] for row in seal['files'] if Path(row['path']).name == 'check-result.json'}
    need(len(PLAN['native_checks']) == len(set(PLAN['native_checks'])) == len(checks) == 9
         and {PLAN['documents'][role]['path'] for role in PLAN['native_checks']} == checks,
         'All nine native attempts, including failures, must be selected and fact-gated')
    native_statuses = {}
    query_count = 0
    for role in PLAN['native_checks']:
        check = documents[role]
        need((role, '/status') in seen and wire(check['native_bounds']) == wire(NATIVE)
             and check['native_invocations'] == 1, 'Exact native facts and unchanged native caps required')
        native_statuses[role] = check['status']
        query_count += len(check['theorem_axiom_output'])
    need(list(native_statuses.values()).count('passed') == 7
         and list(native_statuses.values()).count('inconclusive') == 2 and query_count == 39,
         'Exact native acceptance/failure/query census required')
    need(len(PLAN['explicit_additions']) == len({row['path'] for row in PLAN['explicit_additions']}) == 13,
         'Exact explicit-addition census required')
    for row in PLAN['explicit_additions']:
        descriptor(row)
    source_review = parse(descriptor(next(row for row in PLAN['explicit_additions'] if row['path'].endswith('/source-review-01.json'))))
    need(source_review['status'] == 'passed_source_only_review' and source_review['outstanding_issues'] == [],
         'Passed publication source review required')
    for row in source_review['sources']:
        descriptor(row)
    before_rows, before_dirs, counts, bodies = census()
    need(wire(selection['files']) == wire(before_rows) and wire(selection['directories']) == wire(before_dirs),
         'Whole selected byte/stat/directory population differs before review')
    need(len(before_rows) == 401 and sum(row['bytes'] for row in before_rows) == 147838468
         and counts == {'Q3': 379, 'P4': 10}, 'Exact full Q3/P4/explicit population required')
    selected = {row['path']: row for row in before_rows}
    need({path for path in selected if Path(path).is_relative_to(Q3)} ==
         {row['path'] for row in seal['files']} | {PLAN['documents']['file_seal']['path']},
         'Every Q3 sealed regular file and seal self-file must be selected')
    for row in seal['files']:
        need(wire(row) == wire({k: selected[row['path']][k] for k in ('path', 'bytes', 'sha256')}),
             'Selected Q3 file does not equal its sealed descriptor')
    required_selected = []
    for role in PLAN['native_checks']:
        check = documents[role]
        for field in ('source', 'augmented_source', 'environment_manifest', 'retention_manifest'):
            row = check[field]
            need(row['path'] in selected, 'Native frozen source/profile/retention member omitted')
            need(wire({k: row[k] for k in ('path', 'bytes', 'sha256')}) ==
                 wire({k: selected[row['path']][k] for k in ('path', 'bytes', 'sha256')}),
                 'Native member does not equal its selected complete pin')
            required_selected.append(row['path'])
        for row in check['compiled_artifacts'] + check['retained_chunk_artifacts']:
            need(row['path'] in selected and row['complete'] is True and
                 wire({k: row[k] for k in ('path', 'bytes', 'sha256')}) ==
                 wire({k: selected[row['path']][k] for k in ('path', 'bytes', 'sha256')}),
                 'Complete native chunk/object omitted or changed')
            required_selected.append(row['path'])
    provenance_path = S2 / 'captured-provenance/provenance-map.json'
    need(str(provenance_path) in selected, 'Provenance map must be selected')
    provenance = parse(bodies[str(provenance_path)])
    need(provenance['schema'] == 'ranker-convergence-publication-provenance-byte-copies@1'
         and len(provenance['copies']) == 4 and provenance['remote_mutations'] == 0
         and provenance['whole_live_atomic_snapshot'] is False, 'Exact held-byte provenance scope required')
    for row in provenance['copies']:
        original = descriptor(row['original'])
        captured = descriptor(row['captured'])
        need(original == captured and row['original']['bytes'] == row['captured']['bytes']
             and row['original']['sha256'] == row['captured']['sha256']
             and row['captured']['path'] in selected,
             'Every provenance capture must be a selected exact original-byte clone')
    math_copy = next(row for row in provenance['copies'] if row['original']['path'] == PLAN['documents']['math_review']['path'])
    need(wire(math_copy['original']) == wire(PLAN['documents']['math_review']), 'Math review document/capture join differs')
    math_report = parse(descriptor(math_copy['captured']))
    source_copy = next(row for row in provenance['copies'] if row['original']['path'] == math_report['review_source']['path'])
    need(wire(source_copy['original']) == wire(math_report['review_source']), 'Nested math-review source provenance differs')
    need(PLAN['old_HF_bundle_reuploaded'] is False
         and PLAN['prior_HF_commit'] == '8b7b8c896749e0ca3884114cedbed782a88f4702'
         and PLAN['external_dependencies']['raw_bodies_published'] is False,
         'Prior release/external-body scope differs')
    after_rows, after_dirs, after_counts, _ = census()
    need(wire(before_rows) == wire(after_rows) == wire(selection['files'])
         and wire(before_dirs) == wire(after_dirs) == wire(selection['directories'])
         and counts == after_counts, 'Whole before/after selection/stat/census changed')
    for name, row in input_pins.items():
        descriptor(row)
    for row in PLAN['documents'].values():
        descriptor(row)
    for row in provenance['copies']:
        need(descriptor(row['original']) == descriptor(row['captured']), 'Provenance originals/captures changed during review')
    inode_keys = [(row['stat']['dev'], row['stat']['ino']) for row in before_rows]
    zero_members = [row['path'] for row in before_rows if row['bytes'] == 0]
    own_raw, own = read_regular(Path(__file__).resolve())
    report = {
        'schema': 'ranker-convergence-publication-input-independent-file-review@1',
        'status': 'passed_file_only_final_publication_input_review',
        'review_source': {k: own[k] for k in ('path', 'bytes', 'sha256')},
        'external_input_pins': input_pins,
        'review_work': {'publication_helper_or_project_imports': 0, 'native_model_test_classifier_codec_jobs': 0,
                        'Git_or_remote_mutations': 0, 'S2_Q3_P4_writes': 0,
                        'method': 'No-follow held-byte reads with fstat/path before-after identity, JSON wire/type comparison, source reads only'},
        'typed_facts': {'count': 329, 'pinned_documents': 15, 'explicit_fact_document_roles': len({x['document'] for x in facts}),
                        'native_roles': 9, 'duplicates': 0, 'value_type_counts': type_counts,
                        'all_exact_json_wire_matches': True, 'observations': observed_facts,
                        'seal_document_checked_structurally': True},
        'selection': {'regular_files': 401, 'regular_bytes': 147838468,
                      'Q3_regular_files_including_seal_self': 379, 'Q3_sealed_regular_files': 378,
                      'P4_quiet_regular_files': 10, 'explicit_additions': 13,
                      'explicit_additions_already_in_Q3': 1, 'directories': len(before_dirs),
                      'aliases': 0, 'exclusions': 0, 'duplicate_selected_inodes': len(inode_keys) - len(set(inode_keys)),
                      'all_regular_Q3_files_selected': True, 'whole_before_after_byte_stat_census_equal': True,
                      'whole_selection_json_wire_sha256': hashlib.sha256(wire(before_rows)).hexdigest(),
                      'zero_byte_member_count': len(zero_members), 'zero_byte_members': zero_members},
        'native_evidence_included': {'attempts': 9, 'passed': 7, 'inconclusive_retained': 2,
                                     'qualified_queries': 39, 'statuses': native_statuses,
                                     'all_frozen_profiles_failed_attempts_chunks_and_full_objects_selected': True,
                                     'required_native_selected_member_count': len(set(required_selected)),
                                     'unchanged_native_caps': NATIVE},
        'provenance': {'map_pin': {k: selected[str(provenance_path)][k] for k in ('path', 'bytes', 'sha256')},
                       'copies': provenance['copies'], 'four_original_byte_clones_equal_before_after': True,
                       'nested_math_review_source_and_original_captured_descriptor_joins_verified': True,
                       'no_live_atomic_snapshot_claim': True},
        'publication_profile': PROFILE,
        'scope': {'archive_codec_classification_or_member_review_performed_here': False,
                  'remote_publication_performed_here': False, 'proof_authority': False,
                  'execution_authority': False, 'completion_authority': False,
                  'whole_source_runtime_equivalence_proved': False, 'full_task_satisfaction': 'unknown',
                  'source_drafts_promoted_to_native_qualification_here': False,
                  'prior_HF_bundle_reuploaded': False},
        'held_regular_reads': reads, 'outstanding_issues': [],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'review-receipt.json'
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': report['status'], 'receipt': str(path), 'typed_fact_count': 329,
                      'pinned_documents': 15, 'explicit_fact_document_roles': report['typed_facts']['explicit_fact_document_roles'],
                      'selected_files': 401, 'selected_bytes': 147838468,
                      'before_after_stat_and_byte_census_equal': True, 'aliases': 0, 'exclusions': 0,
                      'native_attempts': 9, 'provenance_original_byte_clones': 4}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
