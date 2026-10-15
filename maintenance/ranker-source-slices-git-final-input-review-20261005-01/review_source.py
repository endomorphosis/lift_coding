"""Independent file-only actual HF gate and compact Git input review.

Targets are never imported or executed. No Git, HTTP, classifier, codec,
native, model, or test job is run. Raw omitted/log/cache bodies are not read.
Only this fresh external review namespace receives a receipt.
"""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat

W = Path('/home/barberb/lift_coding')
PREP = W / 'maintenance/ranker-source-slices-private-git-preparation-20261005-01'
R3 = W / 'maintenance/ranker-source-slices-publication-root-20261005-01'
S3 = W / 'maintenance/ranker-source-slices-publication-20261005-01'
Q4 = W / 'qualification/codebase_ir/ranker-source-semantics-20261005-01'
P5 = W / 'qualification/codebase_ir/ranker-source-semantics-source-plan-20261005-01'
P6 = W / 'qualification/codebase_ir/ranker-objective-ir-source-plan-20261005-01'
OUT = Path(__file__).resolve().parent
COMMIT = 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e'
PARENT = 'd6b6e333f3b1bcfe9028a8ca5ac3be6b12256e8a'
EXPECTED = {
    PREP / 'compact-candidate-selection-01.json': (124254, '9b8a4c3bda6e27235af49597297adaa24c61c985f9ca93f9ac09c1225e728b0f'),
    PREP / 'compact-base-selection-01.json': (124530, '6cea9375254289c31bc5f71451f8bcc8f66dfc6939e5b2450fe110d5655a75bb'),
    PREP / 'final-safe-receipts-selection-01.json': (32779, 'e077c409fa876ec62112027908e7a6193cd7c3a7c1cb044a26786d307dbc03f0'),
    R3 / 'hf-publication-01/closed.json': (887, '25893c408afc28cb6f14ee67a335488271c347b7d7c0a5e2153ca1f6a71edef0'),
    R3 / 'hf-public-readback-01.json': (3467, '59093213bb8558b7087d9a17a020ddda46b7036e4dee98d1a2dee5581badec66'),
    R3 / 'release-publication-ledger-01.json': (4979, '6dabae4b018ff8c803099b47609813c1a4c89e4bc9f7d5147984c4e2ca9711c4'),
}
HELD = {}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path, 'canonical read required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and first.st_size <= 2 * 1024**2, 'bounded compact input required')
        chunks, total = [], 0
        while block := os.read(fd, 65536):
            total += len(block)
            need(total <= 2 * 1024**2, 'compact input grew beyond cap')
            chunks.append(block)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda value: tuple(getattr(value, key) for key in keys)
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and total == first.st_size, 'compact input changed during read')
        return b''.join(chunks)
    finally:
        os.close(fd)


def descriptor(path, raw):
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def shape(row):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and type(row['path']) is str and type(row['bytes']) is int and 0 <= row['bytes'] <= 2 * 1024**2 and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None, 'exact bounded descriptor required')


def held(row):
    shape(row)
    path = Path(row['path'])
    raw = read(path)
    need(descriptor(path, raw) == row, 'parsed/read bytes differ from exact descriptor')
    if path in HELD:
        need(HELD[path] == (raw, row), 'previously held input changed')
    HELD[path] = (raw, row)
    return raw


def object_pairs(pairs):
    value = {}
    for key, item in pairs:
        need(key not in value, 'duplicate JSON key refused')
        value[key] = item
    return value


def parse(raw):
    def nonfinite(_):
        raise ValueError('nonfinite JSON refused')
    value = json.loads(raw, object_pairs_hook=object_pairs, parse_constant=nonfinite)
    todo, count = [(value, 0)], 0
    while todo:
        item, depth = todo.pop()
        count += 1
        need(count <= 100000 and depth <= 32, 'bounded compact JSON tree required')
        children = item.values() if type(item) is dict else item if type(item) is list else ()
        for child in children:
            need(count + len(todo) < 100000, 'bounded pending JSON tree required')
            todo.append((child, depth + 1))
    return value


def load(row):
    return parse(held(row))


def own_pin(path):
    raw = read(path)
    row = descriptor(path, raw)
    held(row)
    return row


def omit(row):
    path = Path(row['path'])
    if path.is_relative_to(Q4):
        relative = path.relative_to(Q4)
        if relative.parts[0] == 'evidence' and 'metadata' in relative.parts:
            offset = relative.parts.index('metadata')
            if str(Path(*relative.parts[offset + 1:])) not in {'manifest.json', 'lake/history.json'}:
                return 'native_metadata_payload_body'
    if path.name in {'environment-manifest.json', 'metadata-inputs.json'}:
        return 'raw_environment_manifest_or_metadata_inputs'
    if path.suffix not in {'.py', '.lean', '.md', '.json', '.xml'}:
        return 'binary_log_or_lock'
    if path.suffix == '.json' and row['bytes'] > 1024**2:
        return 'json_over_1MiB'
    return None


def cache_directory(path):
    return any(part.casefold() in {'.cache', 'cache', 'caches', 'download-cache', 'compiled-cache', 'datasets-cache', '__pycache__'} or part.casefold().endswith('-cache') or part.casefold().startswith('cache-') for part in path.relative_to(W).parts[:-1])


def main():
    need(OUT == W / 'maintenance/ranker-source-slices-git-final-input-review-20261005-01', 'fresh external sibling review namespace required')
    own_raw = read(Path(__file__).resolve())
    own = descriptor(Path(__file__).resolve(), own_raw)
    docs = {}
    for path, expected in EXPECTED.items():
        docs[path] = load({'path': str(path), 'bytes': expected[0], 'sha256': expected[1]})
    candidate = docs[PREP / 'compact-candidate-selection-01.json']
    base = docs[PREP / 'compact-base-selection-01.json']
    extra = docs[PREP / 'final-safe-receipts-selection-01.json']
    closed = docs[R3 / 'hf-publication-01/closed.json']
    public = docs[R3 / 'hf-public-readback-01.json']
    ledger = docs[R3 / 'release-publication-ledger-01.json']
    gate = extra['verified_HF_publication_gate']
    need(set(gate) == {'commit', 'publication_closed', 'public_readback', 'ledger'} and gate['commit'] == COMMIT, 'exact actual HF gate required')
    for key, path in (('publication_closed', R3 / 'hf-publication-01/closed.json'), ('public_readback', R3 / 'hf-public-readback-01.json'), ('ledger', R3 / 'release-publication-ledger-01.json')):
        need(gate[key] == HELD[path][1], 'gate descriptor differs from supplied actual pin')
    need(closed['status'] == 'PUBLISHED_AND_VERIFIED' and closed['remote_readback_verified'] is True and public['status'] == 'passed' and public['fresh_public_main_matches_commit'] is True and public['fresh_public_main_after_tree_matches_commit'] is True and public['all_selected_local_pins_rechecked'] is True, 'actual closed and independently public-read-back HF gate required')
    need(closed['commit'] == public['commit'] == ledger['huggingface']['commit'] == COMMIT and closed['parent'] == public['parent'] == ledger['huggingface']['parent'] == PARENT, 'actual HF commit/parent joins required')
    need(closed['files'] == public['selected_files'] == ledger['huggingface']['selected_files'] == 57 and closed['selected_bytes'] == public['selected_bytes'] == ledger['huggingface']['selected_bytes'] == 15799007, 'exact actual HF population required')
    need(type(public['prior_immutable_files_preserved']) is int and closed['prior_immutable_remote_files_preserved'] == public['prior_immutable_files_preserved'] == ledger['huggingface']['prior_immutable_files_preserved'] == 274 and public['committed_total_regular_files'] == ledger['huggingface']['committed_total_regular_files'] == 331, 'complete prior274/current331 join required')
    need(public['verification_methods'] == {'committed_LFS_SHA256_and_size': 8, 'downloaded_small_file_SHA256_and_size': 49}, 'complete actual verification method counts required')
    need(all(ledger[key] is False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')) and ledger['all32_governing_RPI_exits'] == 'OPEN' and ledger['full_task_satisfaction'] == 'unknown' and ledger['official_benchmark_score'] is None and ledger['github']['commit'] is None, 'honest pending Git and open authority/task scope required')
    need(ledger['next_objective_IR_plan_status'] == 'source_only_uncompiled_unqualified' and ledger['qualified_scope']['numeric_backend'] == 'exact_real' and ledger['qualified_scope']['qualified_native_modules'] == 2 and ledger['qualified_scope']['qualified_theorem_queries'] == 21 and ledger['qualified_scope']['metadata_payloads'] == 4440 and ledger['qualified_scope']['metadata_family_count'] == 32 and ledger['qualified_scope']['projection_domains_runtime_enforced'] is False, 'honest arithmetic projection scope required')
    for row in public['receipt_pins_before_after']:
        load(row)
    for row in ledger['input_receipts'].values():
        load(row)
    need(ledger['input_receipts']['hf_closed'] == gate['publication_closed'] and ledger['input_receipts']['public_readback'] == ledger['huggingface']['public_readback'] == gate['public_readback'] and ledger['input_receipts']['hf_plan'] == closed['plan'], 'nested actual release descriptor joins required')
    plan = load(closed['plan'])
    scan = load(ledger['input_receipts']['final_scan'])
    verified = parse(HELD[R3 / 'hf-publication-01/verified-files.json'][0])
    before = parse(HELD[R3 / 'hf-publication-01/remote-before.json'][0])
    observed = parse(HELD[R3 / 'hf-publication-01/commit-observed.json'][0])
    outer = parse(HELD[R3 / 'hf-publication-outer-01/closed.json'][0])
    need(outer['status'] == 'closed_phase' and outer['returncode'] == 0 and outer['input_pins_unchanged'] is True and outer['cleanup_errors'] == [], 'clean actual HF outer closure required')
    need(scan['status'] == 'passed' and scan['candidate_hits'] == 0 and scan['plan'] == closed['plan'] and scan['selected_files'] == 57 and scan['selected_bytes'] == 15799007, 'exact actual final scan join required')
    need(plan['expected_parent_commit'] == before['commit'] == observed['parent'] == PARENT and observed['commit'] == verified['commit'] == COMMIT, 'actual publisher observed/before/verified joins required')
    need(len(plan['files']) == len(verified['files']) == 57 and sum(row['local']['bytes'] for row in plan['files']) == 15799007 and [{'local': row['local'], 'remote': row['remote']} for row in scan['files']] == plan['files'], 'complete plan/scan/verified population required')
    remote_expected = {row['remote']: row['local'] for row in plan['files']}
    remote_actual = {row['remote']['path']: row for row in verified['files']}
    need(len(remote_expected) == len(remote_actual) == 57 and set(remote_expected) == set(remote_actual), 'unique exact verified upload paths required')
    for name, row in remote_expected.items():
        actual = remote_actual[name]
        need(actual['expected'] == row and actual['remote']['bytes'] == row['bytes'], 'committed local descriptor join differs')
        if actual['remote']['lfs_sha256'] is not None:
            need(actual['remote']['lfs_sha256'] == row['sha256'] and actual['verification_method'] == 'committed_LFS_SHA256_and_size', 'complete LFS descriptor join differs')
        else:
            need(actual['verification_method'] == 'downloaded_small_file_SHA256_and_size', 'small-file verification method differs')
    need(len(before['files']) == 276 and set(remote_expected) & set(before['files']) == set(closed['mutable_paths_explicitly_updated']) == {'README.md', 'releases/20261004-terminal-codebase-ir-evidence-v1/publication-status.json'}, 'exact prior baseline and two mutable paths required')
    need(extra['schema'] == 'ranker-source-slices-final-safe-Git-receipts@1' and extra['base_selection'] == HELD[PREP / 'compact-base-selection-01.json'][1], 'final safe selection/base pin join required')
    need(base['candidate_selection'] == HELD[PREP / 'compact-candidate-selection-01.json'][1], 'base/candidate exact descriptor join required')
    expected_base_document = dict(candidate)
    expected_base_document.update(schema='ranker-source-slices-compact-private-git-base-selection@1', status='closed_exact_frozen_compact_candidate_base', future_safe_package_HF_ledger_receipts_pending=False, candidate_selection=base['candidate_selection'])
    need(base == expected_base_document, 'closed base altered prepared candidate content')
    need(base['original_guard_before'] == base['original_guard_after'] and len(base['parent_gitlinks']) == 9 and len({row['path'] for row in base['parent_gitlinks']}) == 9 and re.fullmatch('[0-9a-f]{40}', base['parent']) is not None, 'prepared original guards and fresh nine-link parent data required')
    closure = load(base['frozen_closed_inputs'])
    full = load(base['frozen_full_selection'])
    need(closure['final_selection'] == base['frozen_full_selection'], 'full selection/frozen closure join required')
    load(closure['plan'])
    load(base['final_seal'])
    load(base['qualified_review'])
    independently_selected, independently_omitted = {}, {}
    reasons = collections.Counter()
    for source in full['files']:
        row = {key: source[key] for key in ('path', 'bytes', 'sha256')}
        path = Path(row['path'])
        need(path.is_relative_to(Q4) or path.is_relative_to(P5) or path.is_relative_to(S3), 'only frozen owned base source required')
        reason = omit(row)
        if reason is None:
            independently_selected[row['path']] = row
        else:
            independently_omitted[row['path']] = {**row, 'reason': reason}
            reasons[reason] += 1
    need(len(full['files']) == 336 and len(independently_selected) == 144 and len(independently_omitted) == 192, 'independent complete compact/omitted denominator differs')
    for name in ('plan.json', 'closed-inputs.json', 'final-selection.json'):
        row = own_pin(S3 / name)
        independently_selected[row['path']] = row
    p6_rows = []
    for name in ('source-plan.json', 'source-bindings.json', 'ir-interface.json'):
        original = own_pin(P6 / name)
        captured = own_pin(S3 / 'captured-provenance' / (P6.name + '-' + name))
        need(all(original[key] == captured[key] for key in ('bytes', 'sha256')) and independently_selected[captured['path']] == captured, 'P6 original/frozen captured byte join differs')
        independently_selected[original['path']] = original
        p6_rows.append(original)
    base_rows = {row['path']: {key: row[key] for key in ('path', 'bytes', 'sha256')} for row in base['selected_files']}
    need(len(base_rows) == len(base['selected_files']) == 150 and base_rows == independently_selected and sum(row['bytes'] for row in base_rows.values()) == base['selected_file_bytes'] == 2742633, 'independent compact base census differs')
    need({row['path']: row for row in base['omitted_full_package_files']} == independently_omitted and base['omitted_file_count'] == 192 and base['omitted_file_bytes'] == sum(row['bytes'] for row in independently_omitted.values()) == 84597690 and base['omitted_reasons'] == dict(reasons), 'exact omitted full-HF denominator differs')
    need(extra['selected_file_count'] == len(extra['files']) == 60 and extra['selected_file_bytes'] == sum(row['bytes'] for row in extra['files']) == 9174801 and extra['new_objective_implementation_drafts_added'] is False, 'exact safe extra count/scope differs')
    all_rows = dict(base_rows)
    for row in extra['files']:
        shape(row)
        path = Path(row['path'])
        rel = path.relative_to(W)
        need(rel.parts[0] == 'maintenance' and rel.parts[1].startswith('ranker-source-') and not any('private' in part or part == '__pycache__' for part in rel.parts) and not cache_directory(path) and omit(row) is None and row['bytes'] <= 1024**2, 'unsafe extra receipt/source path or body bound')
        need(row['path'] not in all_rows, 'base/extra overlap or duplicate source refused')
        all_rows[row['path']] = row
    need(len(all_rows) == 210 and sum(row['bytes'] for row in all_rows.values()) == 11917434, 'complete combined compact count/bytes differs')
    for key in ('publication_closed', 'public_readback', 'ledger'):
        need(all_rows[gate[key]['path']] == gate[key], 'actual gate receipt omitted from Git increment')
    allowed_extra_roots = [R3, W / 'maintenance/ranker-source-slices-publication-package-20261005-01', S3, W / 'maintenance/ranker-source-slices-publication-input-review-20261005-01', W / 'maintenance/ranker-source-slices-git-helper-review-20261005-01', W / 'maintenance/ranker-source-slices-publication-source-review-20261005-01', W / 'maintenance/ranker-source-slices-git-helper-source-20261005-01']
    independently_extra = set()
    def visit(path):
        info = path.lstat()
        need(not stat.S_ISLNK(info.st_mode), 'safe source namespace alias refused')
        if stat.S_ISDIR(info.st_mode):
            if path != path.anchor and any(part.casefold() in {'.cache', 'cache', 'caches', 'download-cache', 'compiled-cache', 'datasets-cache', '__pycache__'} or part.casefold().endswith('-cache') or part.casefold().startswith('cache-') for part in path.relative_to(W).parts):
                return
            for child in sorted(path.iterdir()):
                visit(child)
        else:
            need(stat.S_ISREG(info.st_mode), 'only regular safe namespace leaves required')
            row = {'path': str(path), 'bytes': info.st_size}
            if omit(row) is None and not cache_directory(path) and str(path) not in base_rows:
                independently_extra.add(str(path))
    for root in allowed_extra_roots:
        visit(root)
    need(independently_extra == {row['path'] for row in extra['files']}, 'safe extra physical namespace census has omission/addition')
    maximum_json_bytes = 0
    for row in all_rows.values():
        need(omit(row) is None and not cache_directory(Path(row['path'])), 'unsafe selected body refused')
        raw = held(row)
        raw.decode('utf-8')
        if Path(row['path']).suffix == '.json':
            need(len(raw) <= 1024**2, 'Git JSON exceeds 1MiB')
            parse(raw)
            maximum_json_bytes = max(maximum_json_bytes, len(raw))
    capture_map = load(all_rows[str(W / 'maintenance/ranker-source-slices-git-helper-source-20261005-01/provenance-map.json')])
    need(len(capture_map['files']) == 4 and capture_map['private_worktree_bodies_included'] is False and capture_map['status'] == 'byte_identical_reviewed_source_copies', 'only public exact helper source captures required')
    for row in capture_map['files']:
        need(row['byte_identical'] is True and all(row['original'][key] == row['captured'][key] for key in ('bytes', 'sha256')) and all_rows[row['captured']['path']] == row['captured'], 'helper capture provenance differs')
        need(held(row['original']) == held(row['captured']), 'actual helper source capture bytes differ')
    load(capture_map['source_review'])
    for path, (raw, row) in list(HELD.items()):
        need(read(path) == raw and descriptor(path, raw) == row, 'final held input changed')
    need(read(Path(__file__).resolve()) == own_raw, 'review producer changed')
    result = {
        'schema': 'ranker-source-slices-independent-final-Git-input-review@1',
        'status': 'passed_file_only_actual_HF_gate_and_exact_compact_selection',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'reviewer': own,
        'reviewed_input_pins': [HELD[path][1] for path in EXPECTED],
        'findings': [],
        'actual_HF_commit': COMMIT,
        'actual_HF_parent': PARENT,
        'actual_HF_uploaded_files': 57,
        'actual_HF_uploaded_bytes': 15799007,
        'prior_immutable_HF_files_preserved': 274,
        'current_HF_regular_files': 331,
        'nested_HF_receipt_descriptor_joins_rechecked': True,
        'private_Git_parent_recorded': base['parent'],
        'original_guard_before_after_receipt_join': True,
        'fresh_parent_nine_gitlinks_recorded': True,
        'frozen_full_HF_files': 336,
        'safe_full_HF_source_rows': 144,
        'omitted_full_HF_rows_retained_in_HF_denominator': 192,
        'omitted_full_HF_bytes': 84597690,
        'omitted_reasons': dict(reasons),
        'base_selected_files': 150,
        'base_selected_bytes': 2742633,
        'safe_extra_selected_files': 60,
        'safe_extra_selected_bytes': 9174801,
        'combined_selected_files': 210,
        'combined_selected_bytes': 11917434,
        'all_combined_selected_source_pins_rehashed_before_after': True,
        'all_selected_JSON_parsed_under_1MiB_depth32_node100000_caps': True,
        'maximum_selected_JSON_bytes': maximum_json_bytes,
        'safe_extra_namespace_census_no_omissions': True,
        'original_P6_planning_document_pins': p6_rows,
        'P6_role': 'source_only_uncompiled_unqualified; exactly three originals, no original extractor.py',
        'public_Git_helper_byte_identical_copies': 4,
        'public_Git_helper_provenance_map': all_rows[str(W / 'maintenance/ranker-source-slices-git-helper-source-20261005-01/provenance-map.json')],
        'preserved_superseded_publication_source_history_is_present': True,
        'new_objective_implementation_drafts_added': False,
        'raw_log_cache_archive_binary_environment_or_metadata_input_bodies_read': False,
        'limitations': [
            'File-only local receipt/source review. No target import/execution or Git/classifier/codec/native/model/test/HTTP/remote job ran.',
            'Actual live Git parent/HEAD/index, staged tree, normal push and remote Git blob checks remain the separately authorized helper execution gates.',
            'Fresh public HTTP verification is evidenced by the exact independently pinned readback receipt, not repeated by this local audit.',
            'This external final review is intentionally outside the same increment to avoid self-reference.',
        ],
        'proof_authority': False,
        'execution_authority': False,
        'completion_authority': False,
        'planner_activation': False,
        'full_task_satisfaction': 'unknown',
        'all32_governing_RPI_exits': 'OPEN',
        'official_benchmark_score': None,
    }
    target = OUT / 'review-receipt.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': result['status'], 'receipt': descriptor(target, read(target)), 'reviewer': own, 'combined_files': 210, 'combined_bytes': 11917434}))


if __name__ == '__main__':
    main()
