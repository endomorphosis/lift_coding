"""Review an actual HF gate and complete staged compact increment.

Inert on import. Later authorized execution reads pinned local files and uses
bounded read-only local Git plumbing. It never imports reviewed targets, stages,
commits, pushes, fetches, contacts HTTP, scans credentials, or runs native/model
jobs. Its receipt is external to the staged population.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import stat
import subprocess
import time

W = Path('/home/barberb/lift_coding')
OUT = W / 'maintenance/ranker-objective-scalar-git-final-input-review-20261005-01'
PUBLIC_SOURCE = W / 'maintenance/ranker-objective-scalar-git-helper-source-20261005-01/independent_final_input_review_01.py'
ORIGINAL_STATE = W / 'maintenance/ranker-curvature-private-git-preparation-20261005-01/original-checkout-state-01.json'
Q = W / 'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
P6 = W / 'qualification/codebase_ir/ranker-objective-ir-source-plan-20261005-01'
P7 = W / 'qualification/codebase_ir/ranker-objective-container-source-plan-20261005-01'
S = W / 'maintenance/ranker-objective-scalar-publication-20261005-01'
R = W / 'maintenance/ranker-objective-scalar-publication-root-20261005-01'
HF_PARENT = 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e'
MAX_FILE = 16 * 1024**2
MAX_TOTAL = 256 * 1024**2
HELD = {}
TOTAL = 0
GIT_CALLS = 0
DEADLINE = None
AUTHORITY = ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')


def need(value, message):
    if value is not True:
        raise ValueError(message)


def bounded_int(value, maximum, label, minimum=0):
    need(type(value) is int and minimum <= value <= maximum, 'exact bounded integer: ' + label)
    return value


def digest(value, length=64):
    need(type(value) is str and len(value) == length and re.fullmatch('[0-9a-f]{' + str(length) + '}', value) is not None,
         'exact lowercase digest')
    return value


def shape(row):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and type(row['path']) is str and len(row['path']) <= 4096,
         'exact descriptor')
    bounded_int(row['bytes'], MAX_FILE, 'descriptor bytes')
    digest(row['sha256'])
    path = Path(row['path'])
    need(path.is_absolute() and os.path.normpath(str(path)) == str(path), 'normalized absolute input path')
    return path


def bare(row):
    need(type(row) is dict and {'path', 'bytes', 'sha256'} <= set(row), 'descriptor fields')
    result = {key: row[key] for key in ('path', 'bytes', 'sha256')}
    shape(result)
    return result


def signature(info):
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def read(path, limit=MAX_FILE):
    path = Path(path).absolute()
    need(path.resolve(strict=True) == path and not path.is_symlink(), 'canonical input')
    bounded_int(limit, MAX_FILE, 'read limit', 1)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and 0 <= first.st_size <= limit, 'bounded regular input')
        chunks, total = [], 0
        while block := os.read(fd, min(65536, limit + 1 - total)):
            total += len(block)
            need(total <= limit, 'input grew beyond read limit')
            chunks.append(block)
        need(signature(first) == signature(os.fstat(fd)) == signature(path.lstat()) and total == first.st_size,
             'input changed during read')
        return b''.join(chunks)
    finally:
        os.close(fd)


def descriptor(path, raw):
    return {'path': str(Path(path).absolute()), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def held(row):
    global TOTAL
    path = shape(row)
    raw = read(path)
    need(descriptor(path, raw) == row, 'same-buffer descriptor mismatch')
    if path in HELD:
        need(HELD[path] == (raw, row), 'previously held input changed')
    else:
        TOTAL += len(raw)
        need(TOTAL <= MAX_TOTAL, 'aggregate held-input cap')
        HELD[path] = (raw, row)
    return raw


def observed(path):
    raw = read(path)
    row = descriptor(path, raw)
    held(row)
    return row


def pairs(items):
    result = {}
    for key, value in items:
        need(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def parse(raw):
    def nonfinite(_):
        raise ValueError('nonfinite JSON')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    todo, count = [(value, 0)], 0
    while todo:
        item, depth = todo.pop()
        count += 1
        need(count <= 200000 and depth <= 32, 'JSON node/depth cap')
        children = item.values() if type(item) is dict else item if type(item) is list else ()
        for child in children:
            need(count + len(todo) < 200000, 'pending JSON node cap')
            todo.append((child, depth + 1))
    return value


def load(row):
    return parse(held(row))


def false_authority(body):
    need(all(body[key] is False for key in AUTHORITY), 'four authority flags must be explicitly false')


def relative(value):
    need(type(value) is str and 0 < len(value) <= 4096 and '\0' not in value and '\n' not in value,
         'bounded plain Git path')
    p = Path(value)
    need(not p.is_absolute() and all(part not in ('.', '..') for part in value.split('/')) and str(p) == value,
         'normalized relative Git path')
    return value


def git(repo, *args, limit=MAX_FILE):
    """Bounded read-only local plumbing, called only by main after the HF gate."""
    global GIT_CALLS
    need(args and args[0] in {'rev-parse', 'ls-tree', 'ls-files', 'cat-file'}, 'read-only Git command allowlist')
    bounded_int(limit, MAX_FILE, 'Git output cap', 1)
    remaining = DEADLINE - time.monotonic()
    need(remaining > 0, 'review wall deadline')
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
    cmd = ['/usr/bin/git', '-c', 'core.fsmonitor=false', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-C', str(repo), *args]
    process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    GIT_CALLS += 1
    output = {process.stdout: bytearray(), process.stderr: bytearray()}
    end = min(DEADLINE, time.monotonic() + 30)
    try:
        with selectors.DefaultSelector() as selector:
            for stream in output:
                selector.register(stream, selectors.EVENT_READ)
            while selector.get_map():
                need(time.monotonic() < end, 'bounded Git read deadline')
                for key, _ in selector.select(min(0.25, max(0, end - time.monotonic()))):
                    block = os.read(key.fileobj.fileno(), 65536)
                    if not block:
                        selector.unregister(key.fileobj)
                    else:
                        output[key.fileobj].extend(block)
                        need(len(output[key.fileobj]) <= (limit if key.fileobj is process.stdout else 65536), 'Git output exceeded cap')
        need(process.wait(timeout=max(0.001, end - time.monotonic())) == 0, 'read-only Git command failed')
        return bytes(output[process.stdout])
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()


def tree_rows(raw, index=False):
    result = {}
    for item in raw.split(b'\0'):
        if not item:
            continue
        meta, path_bytes = item.split(b'\t', 1)
        fields = meta.decode('ascii').split()
        need(len(fields) == 3, 'exact Git entry fields')
        mode, second, third = fields
        if index:
            oid, stage = second, third
            need(stage == '0', 'unmerged index refused')
            kind = 'commit' if mode == '160000' else 'blob'
        else:
            kind, oid = second, third
        need(mode in {'100644', '100755', '120000', '160000'} and kind == ('commit' if mode == '160000' else 'blob'), 'Git leaf mode/type')
        digest(oid, 40)
        path = relative(os.fsdecode(path_bytes))
        need(path not in result, 'duplicate Git leaf')
        result[path] = (mode, kind, oid)
    need(len(result) <= 100000, 'Git tree leaf cap')
    return result


def links(rows):
    result = [{'path': name, 'mode': row[0], 'oid': row[2]} for name, row in rows.items() if row[0] == '160000']
    need(len(result) == 9, 'exact nine Git links')
    return sorted(result, key=lambda row: os.fsencode(row['path']))


def guards(expected):
    need(type(expected) is dict and set(expected) == {'root', 'child'}, 'exact original guard roles')
    original = load(observed(ORIGINAL_STATE))
    need(original['schema'] == 'ranker-curvature-private-git-original-state@1', 'original guard source schema')
    result = {}
    for role, cwd in (('root', W), ('child', W / 'external/ipfs_accelerate')):
        row = expected[role]
        need(type(row) is dict and set(row) == {'head', 'index_bytes', 'index_sha256'}, 'exact original guard record')
        digest(row['head'], 40)
        old = original['original_checkouts'][role]
        need(old['path'] == str(cwd) and all(row[key] == old[key] for key in row), 'recorded original baseline')
        head = git(cwd, 'rev-parse', 'HEAD', limit=128).decode().strip()
        index = observed(Path(old['index_path']))
        current = {'head': head, 'index_bytes': index['bytes'], 'index_sha256': index['sha256']}
        need(current == row, 'original checkout HEAD/index changed')
        result[role] = current
    root_index = tree_rows(git(W, 'ls-files', '--stage', '-z'), index=True)
    root_links = [{'path': name, 'mode': mode, 'blob': oid, 'stage': 0}
                  for name, (mode, kind, oid) in root_index.items() if mode == '160000']
    need(sorted(root_links, key=lambda row: os.fsencode(row['path'])) ==
         sorted(original['root_index_gitlinks'], key=lambda row: os.fsencode(row['path'])), 'original index gitlinks unchanged')
    return result


def cache(path):
    return any(part.casefold() in {'.cache', 'cache', 'caches', 'download-cache', 'compiled-cache', 'datasets-cache', '__pycache__'}
               or part.casefold().endswith('-cache') or part.casefold().startswith('cache-') for part in path.relative_to(W).parts)


def omit(row, policy):
    path = Path(row['path'])
    if path.is_relative_to(Q):
        parts = path.relative_to(Q).parts
        if parts and parts[0] == 'evidence' and 'metadata' in parts:
            offset = parts.index('metadata')
            if str(Path(*parts[offset + 1:])) not in {'manifest.json', 'lake/history.json'}:
                return 'native_metadata_payload_body'
    if path == P6 / 'extract_bindings_01.py':
        return 'original_planning_extractor_not_selected_for_Git'
    if path.name in {'environment-manifest.json', 'metadata-inputs.json'}:
        return 'raw_environment_manifest_or_metadata_inputs'
    if path.suffix not in {'.py', '.lean', '.md', '.json', '.xml'}:
        return 'binary_log_or_lock'
    if path.suffix == '.json' and row['bytes'] > 1024**2:
        return 'json_over_1MiB'
    return None


def hf_gate(gate, expected, expected_commit, files, size):
    need(type(gate) is dict and set(gate) == {'commit', 'publication_closed', 'public_readback', 'ledger'} and
         gate['commit'] == expected_commit and all(gate[key] == expected[key] for key in expected), 'exact externally pinned HF gate')
    closed, public, ledger = (load(gate[key]) for key in ('publication_closed', 'public_readback', 'ledger'))
    need(closed['schema'] == 'terminal-ir-HF-successor-publication@1' and closed['status'] == 'PUBLISHED_AND_VERIFIED' and
         closed['remote_readback_verified'] is True and public['schema'] == 'ranker-objective-scalar-public-HF-readback-join@1' and
         public['status'] == 'passed' and public['fresh_public_main_matches_commit'] is True and
         public['fresh_public_main_after_tree_matches_commit'] is True and public['all_selected_local_pins_rechecked'] is True,
         'actual closed and fresh independent HF readback')
    need(ledger['schema'] == 'ranker-objective-scalar-release-publication-ledger@1' and
         ledger['status'] == 'HF_PUBLISHED_AND_VERIFIED_GITHUB_PUBLICATION_PENDING', 'exact pending Git ledger')
    need(closed['commit'] == public['commit'] == ledger['huggingface']['commit'] == expected_commit and
         closed['parent'] == public['parent'] == ledger['huggingface']['parent'] == HF_PARENT, 'actual HF commit/parent joins')
    for body, file_key, byte_key in ((closed, 'files', 'selected_bytes'), (public, 'selected_files', 'selected_bytes'),
                                    (ledger['huggingface'], 'selected_files', 'selected_bytes')):
        need(type(body[file_key]) is int and type(body[byte_key]) is int and body[file_key] == files and body[byte_key] == size,
             'exact actual HF uploaded counts')
    need(closed['prior_immutable_remote_files_preserved'] == public['prior_immutable_files_preserved'] ==
         ledger['huggingface']['prior_immutable_files_preserved'] == 329 and public['committed_total_regular_files'] ==
         ledger['huggingface']['committed_total_regular_files'] == 331 + files - 2, 'whole prior329 and new public census')
    false_authority(ledger)
    need(ledger['github']['commit'] is None and ledger['all32_governing_RPI_exits'] == 'OPEN' and
         ledger['full_task_satisfaction'] == 'unknown' and ledger['official_benchmark_score'] is None, 'open frontier and pending Git')
    scope = ledger['qualified_scope']
    need(scope['numeric_backend'] == 'partial_exact_real' and scope['qualified_native_modules'] == 2 and
         scope['qualified_theorem_queries'] == 14 and scope['pure_test_cases'] == 98 and scope['metadata_payloads'] == 4458 and
         scope['metadata_family_count'] == 32 and scope['additive_metadata_payloads'] == 18 and
         scope['prior4440_payloads_preserved'] is True and scope['prior375_vectors_preserved'] is True and
         scope['projection_domain_contracts_unchanged'] == 2, 'only qualified exact-real scalar leaves')
    for binding in public['receipt_pins_before_after']:
        load(binding)
    for binding in ledger['input_receipts'].values():
        load(binding)
    pins = ledger['input_receipts']
    need(pins['hf_closed'] == gate['publication_closed'] and pins['public_readback'] == gate['public_readback'] ==
         ledger['huggingface']['public_readback'] and pins['hf_plan'] == closed['plan'], 'nested actual HF descriptor joins')
    plan, scan = load(closed['plan']), load(pins['final_scan'])
    root = Path(gate['publication_closed']['path']).parent
    public_pins = {binding['path']: binding for binding in public['receipt_pins_before_after']}
    need(len(public_pins) == len(public['receipt_pins_before_after']), 'unique actual readback receipt pins')
    verified, before, commit = (load(public_pins[str(root / name)]) for name in
                               ('verified-files.json', 'remote-before.json', 'commit-observed.json'))
    outer = load(public_pins[str(root.parent / 'hf-publication-outer-01/closed.json')])
    need(outer['status'] == 'closed_phase' and outer['returncode'] == 0 and outer['input_pins_unchanged'] is True and
         outer['cleanup_errors'] == [], 'clean actual HF outer closure')
    need(plan['expected_parent_commit'] == before['commit'] == commit['parent'] == HF_PARENT and
         commit['commit'] == verified['commit'] == expected_commit and len(before['files']) == 331, 'publisher before/observed joins')
    need(scan['status'] == 'passed' and scan['candidate_hits'] == 0 and scan['plan'] == closed['plan'] and
         scan['selected_files'] == files and scan['selected_bytes'] == size and len(plan['files']) == len(verified['files']) == files and
         sum(row['local']['bytes'] for row in plan['files']) == size and
         [{'local': row['local'], 'remote': row['remote']} for row in scan['files']] == plan['files'], 'complete actual plan/scan/verified census')
    expected_files = {row['remote']: row['local'] for row in plan['files']}
    actual = {row['remote']['path']: row for row in verified['files']}
    need(len(expected_files) == len(actual) == files and set(expected_files) == set(actual), 'unique verified upload population')
    for name, binding in expected_files.items():
        row = actual[name]
        need(row['expected'] == binding and row['remote']['bytes'] == binding['bytes'], 'verified local descriptor/size join')
        if row['remote']['lfs_sha256'] is not None:
            need(row['verification_method'] == 'committed_LFS_SHA256_and_size' and row['remote']['lfs_sha256'] == binding['sha256'], 'LFS full size/SHA join')
        else:
            need(row['verification_method'] == 'downloaded_small_file_SHA256_and_size', 'small-file verification method')
    need(public['verification_methods'] == dict(collections.Counter(row['verification_method'] for row in actual.values())), 'complete verification method census')
    need(set(expected_files) & set(before['files']) == set(closed['mutable_paths_explicitly_updated']) ==
         {'README.md', 'releases/20261004-terminal-codebase-ir-evidence-v1/publication-status.json'}, 'exact two remote pointer updates')
    return ledger


def partition(full, plan, parent_rows, repo, policy):
    selected, omitted = {}, {}
    for source in full['files']:
        row = bare(source)
        path = Path(row['path'])
        need(path.is_relative_to(Q) or path.is_relative_to(P6) or path.is_relative_to(S), 'owned full frozen source population')
        need(row['path'] not in selected and row['path'] not in omitted, 'unique full frozen rows')
        reason = omit(row, policy)
        if reason:
            omitted[row['path']] = {**row, 'reason': reason}
        else:
            selected[row['path']] = row
    for name in ('plan.json', 'closed-inputs.json', 'final-selection.json'):
        row = observed(S / name)
        need(omit(row, policy) is None and row['path'] not in selected and row['path'] not in omitted, 'new bounded final planning receipts')
        selected[row['path']] = row
    return selected, omitted


def safe_extra_census(roots, base_paths, policy):
    need(type(roots) is list and 1 <= len(roots) <= 32 and len(set(roots)) == len(roots), 'bounded unique safe-extra roots')
    result = set()
    visited = 0
    def visit(path, depth=0):
        nonlocal visited
        visited += 1
        need(visited <= 10000 and depth <= 16, 'safe-extra census node/depth cap')
        info = path.lstat()
        need(not stat.S_ISLNK(info.st_mode), 'safe-extra namespace alias')
        if cache(path) or any('private' in part or part == '.git' for part in path.relative_to(W).parts):
            return
        if stat.S_ISDIR(info.st_mode):
            for child in sorted(path.iterdir(), key=lambda item: os.fsencode(item.name)):
                visit(child, depth + 1)
        else:
            need(stat.S_ISREG(info.st_mode), 'regular safe-extra namespace leaf')
            row = {'path': str(path), 'bytes': info.st_size}
            if omit(row, policy) is None and row['bytes'] <= 1024**2 and str(path) not in base_paths:
                result.add(str(path))
    for value in roots:
        path = Path(value)
        rel = path.relative_to(W)
        need(path.resolve(strict=True) == path and path.is_dir() and path.parent == W / 'maintenance' and rel.parts[0] == 'maintenance' and
             rel.parts[1].startswith('ranker-objective-') and not any('private' in part or part == '.git' for part in rel.parts) and
             'git-publication' not in rel.parts[1] and 'git-final-input-review' not in rel.parts[1] and
             not path.is_relative_to(OUT) and not OUT.is_relative_to(path), 'public safe-extra root scope')
        visit(path)
    return result


def main():
    global DEADLINE
    need(__debug__, 'optimized reviewer refused')
    DEADLINE = time.monotonic() + 180
    need(OUT == W / 'maintenance/ranker-objective-scalar-git-final-input-review-20261005-01' and
         not (OUT / 'review-receipt.json').exists(), 'fresh external final-review namespace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparation-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    for key in ('stage', 'candidate', 'base', 'receipts-selection', 'source-policy', 'HF-closed', 'HF-readback', 'HF-ledger'):
        parser.add_argument('--' + key, required=True, type=Path)
        parser.add_argument('--expected-' + key + '-sha256', required=True)
    parser.add_argument('--expected-HF-commit', required=True)
    parser.add_argument('--expected-Git-parent', required=True)
    for key in ('HF-files', 'HF-bytes', 'full-selected-files', 'full-selected-bytes', 'combined-files', 'combined-bytes'):
        parser.add_argument('--expected-' + key, required=True, type=int)
    args = parser.parse_args()
    need(args.output == OUT / 'review-receipt.json' and OUT.resolve(strict=True) == OUT and OUT.is_dir() and
         Path(__file__).resolve() == PUBLIC_SOURCE, 'public reviewer source and fixed external fresh receipt path')
    prep = args.preparation_root
    need(prep.is_absolute() and prep.resolve(strict=True) == prep and prep.parent == W / 'maintenance' and
         prep.name.startswith('ranker-objective-scalar-private-git-preparation-') and prep != OUT, 'fresh isolated preparation scope')
    repo = prep / 'root'
    need(repo.is_dir() and repo.resolve(strict=True) == repo and repo not in (W, W / 'external/ipfs_accelerate'), 'isolated private checkout')
    expected_paths = {'stage': prep / 'final-stage-closed-01.json', 'candidate': prep / 'compact-candidate-selection-01.json',
                      'base': prep / 'compact-base-selection-01.json', 'receipts_selection': prep / 'final-safe-receipts-selection-01.json',
                      'HF_closed': R / 'hf-publication-01/closed.json', 'HF_readback': R / 'hf-public-readback-01.json',
                      'HF_ledger': R / 'release-publication-ledger-01.json',
                      'source_policy': PUBLIC_SOURCE.parent / 'publication-policy.json'}
    pins, docs = {}, {}
    for name in ('stage', 'candidate', 'base', 'receipts_selection', 'source_policy', 'HF_closed', 'HF_readback', 'HF_ledger'):
        path = getattr(args, name)
        if name in expected_paths:
            need(path == expected_paths[name], 'fixed prepared or actual HF input path')
        row = observed(path)
        need(row['sha256'] == digest(getattr(args, 'expected_' + name + '_sha256')), 'external exact input pin')
        pins[name] = row
        docs[name] = load(row)
    policy = docs['source_policy']
    need(policy['schema'] == 'ranker-objective-scalar-private-Git-publication-policy@1' and
         policy['expected_prior_HF_commit'] == HF_PARENT and policy['expected_prior_immutable_HF_files'] == 329 and
         policy['native_accepted_theorem_queries'] == 14 and policy['metadata_payloads'] == 4458 and
         policy['force_push_allowed'] is policy['rebase_allowed'] is False, 'exact objective-scalar policy')
    false_authority(policy)
    for key in ('host_parser_correctness_theorem_proved', 'python_ranker_source_equivalence_proved', 'binary64_error_bound_proved',
                'full_objective_semantics_proved', 'full_preparation_semantics_proved', 'full_training_semantics_proved',
                'whole_IR_semantic_preservation_proved', 'global_autoencoder_convergence_proved'):
        need(policy[key] is False, 'broad source/numeric policy frontier')
    hf_commit, parent = digest(args.expected_HF_commit, 40), digest(args.expected_Git_parent, 40)
    hf_files = bounded_int(args.expected_HF_files, 100, 'HF files', 1)
    hf_size = bounded_int(args.expected_HF_bytes, MAX_TOTAL, 'HF bytes', 1)
    full_count = bounded_int(args.expected_full_selected_files, 10000, 'full files', 1)
    full_size = bounded_int(args.expected_full_selected_bytes, MAX_TOTAL, 'full bytes', 1)
    count = bounded_int(args.expected_combined_files, 10000, 'combined files', 1)
    size = bounded_int(args.expected_combined_bytes, MAX_TOTAL, 'combined bytes', 1)
    stage, candidate, base, extra = (docs[name] for name in ('stage', 'candidate', 'base', 'receipts_selection'))
    gate = extra['verified_HF_publication_gate']
    gate_pins = {'publication_closed': pins['HF_closed'], 'public_readback': pins['HF_readback'], 'ledger': pins['HF_ledger']}
    ledger = hf_gate(gate, gate_pins, hf_commit, hf_files, hf_size)
    need(stage['schema'] == 'ranker-objective-scalar-final-private-git-stage@1' and
         stage['status'] == 'passed_complete_increment_HF_verified_ready_to_commit' and stage['verified_HF_publication_gate'] == gate and
         stage['hf_commit'] == hf_commit and stage['base_selection'] == pins['base'] and stage['safe_receipts_selection'] == pins['receipts_selection'],
         'actual closed stage/base/receipts/HF joins')
    need(candidate['schema'] == 'ranker-objective-scalar-compact-private-git-candidate-selection@1' and
         candidate['status'] == 'prepared_read_only_no_stage_commit_or_push' and base['candidate_selection'] == pins['candidate'] and
         extra['schema'] == 'ranker-objective-scalar-final-safe-Git-receipts@1' and
         extra['status'] == 'prepared_file_only_actual_HF_verified' and extra['base_selection'] == pins['base'], 'exact candidate/base/extra joins')
    expected_base = dict(candidate)
    expected_base.update(schema='ranker-objective-scalar-compact-private-git-base-selection@1',
                         status='closed_exact_frozen_compact_candidate_base', future_safe_package_HF_ledger_receipts_pending=False,
                         candidate_selection=pins['candidate'], safe_selector_request=extra['request'])
    need(base == expected_base and base['parent'] == stage['parent'] == parent and base['private_checkout'] == str(repo), 'unchanged complete candidate base')
    for body in (stage, candidate, base, extra):
        false_authority(body)
    need(candidate['verified_HF_publication_gate'] == gate and candidate['frozen_closed_inputs'] ==
         ledger['input_receipts']['frozen_inputs'] and candidate['final_seal'] == ledger['input_receipts']['seal'] and
         candidate['qualified_review'] == ledger['input_receipts']['qualification'], 'same actual qualified and frozen HF source population')
    need(load(candidate['HF_gate_input']) == gate, 'externally bound original gate input')
    request = load(extra['request'])
    need(type(request) is dict and set(request) == {'schema', 'candidate_selection', 'verified_HF_publication_gate', 'safe_extra_roots', 'files'} and
         request['schema'] == 'ranker-objective-scalar-safe-Git-selector-request@1' and request['candidate_selection'] == pins['candidate'] ==
         extra['candidate_selection'] and request['verified_HF_publication_gate'] == gate and
         request['safe_extra_roots'] == extra['safe_extra_roots'] and request['files'] == extra['files'], 'closed exact safe-root request joins')
    need(base['original_guard_before'] == base['original_guard_after'] == stage['original_guard_before'] == stage['original_guard_after'], 'original guard receipt joins')
    live_guards = guards(stage['original_guard_after'])
    need(git(repo, 'rev-parse', 'HEAD', limit=128).decode().strip() == parent, 'private HEAD remains prepared parent')
    parent_rows = tree_rows(git(repo, 'ls-tree', '-r', '-z', '--full-tree', parent))
    closure, full, plan = load(base['frozen_closed_inputs']), load(base['frozen_full_selection']), None
    need(closure['schema'] == 'ranker-objective-scalar-publication-closed-inputs@1' and
         closure['final_selection'] == base['frozen_full_selection'], 'full frozen closure join')
    plan = load(closure['plan'])
    need(plan['schema'] == 'ranker-objective-scalar-publication-plan@1' and plan['status'] == 'frozen_final_plan' and
         plan['source_and_artifacts_quiet'] is True and plan['source_plan_quiet'] is True and full['exclusions'] == [],
         'quiet frozen whole publication selection')
    need(len(full['files']) == full_count and sum(row['bytes'] for row in full['files']) == full_size and
         len({row['path'] for row in full['files']}) == full_count, 'full frozen denominator')
    seal, review = load(candidate['final_seal']), load(candidate['qualified_review'])
    need(candidate['final_seal']['sha256'] == policy['Q5_seal_sha256'] and candidate['qualified_review']['sha256'] == policy['Q5_review_sha256'] and
         review['status'] == 'passed' and seal['review'] == candidate['qualified_review'] and
         type(seal['regular_file_count']) is int and seal['regular_file_count'] == len(seal['files']) == 276 and
         type(seal['regular_file_bytes']) is int and seal['regular_file_bytes'] == sum(row['bytes'] for row in seal['files']) == 78794802 and
         seal['fixture_symlinks'] == seal['excluded_dependency_roots'] == [] and
         hashlib.sha256(json.dumps(seal['files'], sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest() == seal['file_inventory_sha256'],
         'complete sealed qualification census and independent reviewed seal pins')
    full_by_path = {row['path']: bare(row) for row in full['files']}
    need(all(full_by_path.get(row['path']) == row for row in seal['files']) and
         full_by_path.get(candidate['final_seal']['path']) == candidate['final_seal'], 'entire seal plus sealself retained in full HF denominator')
    selected, omitted = partition(full, plan, parent_rows, repo, policy)
    next_rows = [row for row in base['selected_files'] if row.get('binding_origin') == 'explicit_next_phase_original_with_frozen_capture']
    next_rows += [row for row in base['omitted_full_package_files'] if Path(row['path']).parent == P7 and row['reason'] == 'already_published_unchanged']
    need(len(next_rows) in (0, 3), 'optional next planning originals exactly zero or three')
    if next_rows:
        need({Path(row['path']).name for row in next_rows} == {'source-plan.json', 'source-bindings.json', 'ir-interface.json'}, 'three next plan names')
        provenance = load(plan['provenance_map'])
        clones = {row['original']['path']: row for row in provenance['copies']}
        for source in next_rows:
            row = bare(source)
            need(Path(row['path']).parent == P7 and row['path'] not in selected, 'only P7 planning originals')
            clone = clones[row['path']]
            need(clone['original'] == row and clone['byte_exact_clone'] is True and
                 (row['bytes'], row['sha256']) == (clone['captured']['bytes'], clone['captured']['sha256']) and
                 selected[clone['captured']['path']] == clone['captured'], 'P7 originals join already frozen complete captures')
            selected[row['path']] = row
        proposal = load(selected[str(P7 / 'source-plan.json')])
        need(proposal['schema'] == 'ranker-objective-container-source-plan@1' and proposal['status'] == 'draft_unqualified_source_only_plan', 'next plan remains unqualified')
    for path, row in list(selected.items()):
        name = relative(str(Path(path).relative_to(W)))
        if name in parent_rows:
            mode, kind, oid = parent_rows[name]
            need(mode == '100644' and kind == 'blob', 'existing publication source is regular')
            body = git(repo, 'cat-file', 'blob', oid, limit=MAX_FILE)
            need(len(body) == row['bytes'] and hashlib.sha256(body).hexdigest() == row['sha256'], 'existing parent source changed')
            omitted[path] = {**row, 'reason': 'already_published_unchanged', 'parent_git_blob_oid': oid}
            del selected[path]
    base_rows = {row['path']: bare(row) for row in base['selected_files']}
    bounded_int(base['selected_file_count'], 10000, 'base selected files', 1)
    bounded_int(base['selected_file_bytes'], MAX_TOTAL, 'base selected bytes', 1)
    bounded_int(base['omitted_file_count'], 10000, 'base omitted files')
    bounded_int(base['omitted_file_bytes'], MAX_TOTAL, 'base omitted bytes')
    need(len(base_rows) == len(base['selected_files']) == base['selected_file_count'] and base_rows == selected and
         sum(row['bytes'] for row in selected.values()) == base['selected_file_bytes'], 'independent exact base partition')
    need({row['path']: row for row in base['omitted_full_package_files']} == omitted and base['omitted_file_count'] == len(omitted) and
         base['omitted_file_bytes'] == sum(row['bytes'] for row in omitted.values()) and
         base['omitted_reasons'] == dict(collections.Counter(row['reason'] for row in omitted.values())), 'exact retained HF omission denominator')
    roots = extra['safe_extra_roots']
    sources = dict(selected)
    bounded_int(extra['selected_file_count'], 100, 'safe extra files', 1)
    bounded_int(extra['selected_file_bytes'], MAX_TOTAL, 'safe extra bytes', 1)
    need(type(extra['files']) is list and 0 < len(extra['files']) <= 100, 'bounded safe extras')
    extra_paths = set()
    for row in extra['files']:
        path = shape(row)
        rel = path.relative_to(W)
        need(len(rel.parts) >= 2 and rel.parts[0] == 'maintenance' and rel.parts[1].startswith('ranker-objective-') and
             not any('private' in part or part == '.git' for part in rel.parts) and 'git-publication' not in rel.parts[1] and
             not path.is_relative_to(OUT) and not cache(path) and omit(row, policy) is None and row['bytes'] <= 1024**2,
             'only safe public compact extras')
        need(row['path'] not in sources, 'duplicate or base-overlapping extra')
        sources[row['path']] = row
        extra_paths.add(row['path'])
    need(safe_extra_census(roots, set(selected), policy) == extra_paths and len(extra_paths) == extra['selected_file_count'] and
         sum(row['bytes'] for row in extra['files']) == extra['selected_file_bytes'], 'independent whole safe-extra namespace census')
    need(len(sources) == count and sum(row['bytes'] for row in sources.values()) == size, 'exact combined population')
    need(all(sources.get(row['path']) == row for row in gate_pins.values()), 'all three actual gate receipts selected')
    blobs = {}
    for path, row in sources.items():
        need(omit(row, policy) is None and not cache(Path(path)) and not Path(path).is_relative_to(OUT), 'safe source and external peer separation')
        raw = held(row)
        raw.decode('utf-8')
        need(b'\0' not in raw, 'text blob contains NUL')
        if Path(path).suffix == '.json':
            need(len(raw) <= 1024**2, 'selected JSON exceeds 1 MiB')
            parse(raw)
        name = relative(str(Path(path).relative_to(W)))
        oid = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        blobs[name] = ('100644', 'blob', oid)
    expected_tree = dict(parent_rows)
    need(not set(blobs) & set(parent_rows), 'increment replaces a parent file')
    expected_tree.update(blobs)
    staged_tree = digest(stage['tree'], 40)
    tree = tree_rows(git(repo, 'ls-tree', '-r', '-z', '--full-tree', staged_tree))
    index = tree_rows(git(repo, 'ls-files', '--stage', '-z'), index=True)
    need(tree == index == expected_tree, 'full staged tree/index equals entire parent plus exact increment')
    staged_rows = {row['path']: row for row in stage['staged_source_blobs']}
    bounded_int(stage['staged_file_count'], 10000, 'staged files', 1)
    bounded_int(stage['staged_file_bytes'], MAX_TOTAL, 'staged bytes', 1)
    need(len(staged_rows) == len(stage['staged_source_blobs']) == stage['staged_file_count'] == count and
         stage['staged_file_bytes'] == size and set(staged_rows) == set(blobs), 'closed stage exact blob population')
    for name, expected in blobs.items():
        row = staged_rows[name]
        source = sources[str(W / name)]
        need(row['mode'] == expected[0] and row['git_blob_oid'] == expected[2] and row['bytes'] == source['bytes'] and
             row['sha256'] == source['sha256'], 'closed staged blob/source join')
        body = git(repo, 'cat-file', 'blob', expected[2], limit=MAX_FILE)
        need(body == HELD[W / name][0], 'actual staged object bytes differ from source')
    need(links(parent_rows) == links(tree) == sorted(base['parent_gitlinks'], key=lambda row: os.fsencode(row['path'])) ==
         sorted(stage['parent_gitlinks'], key=lambda row: os.fsencode(row['path'])), 'all nine live staged/parent links preserved')
    need(stage['all_nine_parent_gitlinks_unchanged'] is True and stage['all_new_staged_text_scanned'] is True and
         stage['bounded_complete_PEM_and_cached_credential_veto'] is True and type(stage['credential_candidate_hits']) is int and
         stage['credential_candidate_hits'] == 0 and type(stage['stage_calls']) is int and stage['stage_calls'] == 1 and
         type(stage['commit_calls']) is type(stage['push_calls']) is int and stage['commit_calls'] == stage['push_calls'] == 0 and
         type(stage['native_model_solver_test_fit_codec_jobs']) is type(stage['project_imports']) is int and
         stage['native_model_solver_test_fit_codec_jobs'] == stage['project_imports'] == 0,
         'actual admitted bounded classifier/stage only')
    for path, (raw, row) in list(HELD.items()):
        need(read(path) == raw and descriptor(path, raw) == row, 'final held source/receipt pin changed')
    need(guards(stage['original_guard_after']) == live_guards and git(repo, 'rev-parse', 'HEAD', limit=128).decode().strip() == parent and
         tree_rows(git(repo, 'ls-files', '--stage', '-z'), index=True) == index, 'final live original/private HEAD/index drift')
    need(time.monotonic() < DEADLINE, 'review wall cap')
    own = observed(Path(__file__).resolve())
    result = {'schema': 'ranker-objective-scalar-independent-final-Git-input-review@1',
        'status': 'passed_file_only_actual_HF_gate_and_exact_compact_selection', 'findings': [],
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'reviewer': own,
        'reviewed_input_pins': list(pins.values()), 'actual_HF_commit': hf_commit, 'actual_HF_parent': HF_PARENT,
        'actual_HF_uploaded_files': hf_files, 'actual_HF_uploaded_bytes': hf_size, 'prior_immutable_HF_files_preserved': 329,
        'current_HF_regular_files': 331 + hf_files - 2, 'combined_selected_files': count, 'combined_selected_bytes': size,
        'base_selected_files': len(selected), 'base_selected_bytes': sum(row['bytes'] for row in selected.values()),
        'safe_extra_selected_files': len(extra_paths), 'safe_extra_selected_bytes': extra['selected_file_bytes'],
        'private_Git_parent_recorded': parent, 'exact_staged_tree': staged_tree,
        'all_actual_staged_blob_bytes_independently_read_back': True, 'full_staged_tree_index_and_preserved_parent_compared': True,
        'all_nine_live_parent_and_staged_gitlinks_preserved': True, 'original_HEAD_index_guards_before_after': live_guards,
        'all_selected_source_pins_rehashed_before_after': True, 'independent_full_source_partition_and_safe_extra_census': True,
        'frozen_full_HF_files': full_count, 'frozen_full_HF_bytes': full_size,
        'omitted_full_HF_rows_retained_in_HF_denominator': len(omitted), 'omitted_reasons': base['omitted_reasons'],
        'read_only_local_Git_calls': GIT_CALLS, 'Git_mutations_network_or_HTTP_calls': 0,
        'classifier_codec_native_model_metadata_test_or_target_import_jobs': 0,
        'raw_SDK_log_cache_archive_proof_object_environment_or_metadata_payload_bodies_read': False,
        'original_Git_index_bytes_read_for_guards': True,
        'review_receipt_external_to_staged_population': True,
        'qualified_scope': 'Partial exact-real scalar compiler and emitted stable-loss/sign-split-factor leaves; 14 queries, 98 pure cases, 4458 metadata payloads with prior4440 prefixes, vectors375 and contracts2 unchanged.',
        'host_parser_correctness_proved': False, 'python_source_equivalence_proved': False, 'binary64_refinement_proved': False,
        'full_objective_translation_proved': False, 'computed_gradient_translation_proved': False, 'whole_IR_preservation_proved': False,
        'global_autoencoder_convergence_proved': False, 'proof_authority': False, 'execution_authority': False,
        'completion_authority': False, 'planner_activation': False, 'full_task_satisfaction': 'unknown',
        'all32_governing_RPI_exits': 'OPEN', 'official_benchmark_score': None,
        'limitations': ['Fresh public HTTP state is evidenced by the independently pinned actual HF readback, not queried again here.',
                        'This review reads local Git plumbing only; normal commit/push/fresh remote readback remain the separate publisher gates.',
                        'The final review receipt is deliberately external to this increment to avoid self-reference.']}
    with args.output.open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({'status': result['status'], 'receipt': descriptor(OUT / 'review-receipt.json', read(OUT / 'review-receipt.json'))}))


if __name__ == '__main__':
    main()
