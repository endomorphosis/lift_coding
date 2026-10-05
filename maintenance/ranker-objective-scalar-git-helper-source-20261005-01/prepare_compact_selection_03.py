"""Prepare a compact source/receipt candidate inventory using only reads.

No Git mutation, staging, classifier, codec, native or remote publication call
is present. Full omitted bodies remain in the separately qualified HF package.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = None  # Explicit fresh preparation root is required at execution.
PRIOR_PREP = WORKSPACE / 'maintenance/ranker-curvature-private-git-preparation-20261005-01'
REPO = None
ORIGINAL_STATE = PRIOR_PREP / 'original-checkout-state-01.json'
Q5 = WORKSPACE / 'qualification/codebase_ir/ranker-objective-ir-candidate-20261005-01'
P6 = WORKSPACE / 'qualification/codebase_ir/ranker-objective-ir-source-plan-20261005-01'
S4 = WORKSPACE / 'maintenance/ranker-objective-scalar-publication-20261005-01'
PARENT = None  # Required fresh parent is supplied by the final isolated checkout.
SEAL_SHA = '874b51a3358dee5dbd18b70c66770f4e3fdf3553c2fac3fb644075c37273f43d'
REVIEW_SHA = '590163443db860ac03bc2d3fde0f07ac44626e8b6e7cc57a3d6c770c4da87f00'
CLOSURE_SHA = None
EXPECTED_SELECTION_COUNT = None
EXPECTED_SELECTION_BYTES = None
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
FILE_MAX = 16 * 1024**2


def need(value, message):
    if value is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical regular source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= FILE_MAX, 'bounded regular source required')
        blocks, count = [], 0
        while block := os.read(fd, 1024**2):
            count += len(block)
            need(count <= FILE_MAX, 'source grew beyond bound')
            blocks.append(block)
        keys = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        signature = lambda info: tuple(getattr(info, key) for key in keys)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and count == before.st_size, 'source changed during read')
        return b''.join(blocks)
    finally:
        os.close(fd)


def pin(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def document(path, expected_sha256=None):
    raw = read(path)
    row = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    need(expected_sha256 is None or row['sha256'] == expected_sha256, 'parsed document pin differs')
    return json.loads(raw), row


def git(*args, repo=None):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-C', str(REPO if repo is None else repo), *args], env=ENV)


def guards():
    original = json.loads(read(ORIGINAL_STATE))
    now = {}
    for name, old in original['original_checkouts'].items():
        raw = read(Path(old['index_path']))
        row = {'head': git('rev-parse', 'HEAD', repo=old['path']).decode().strip(), 'index_bytes': len(raw), 'index_sha256': hashlib.sha256(raw).hexdigest()}
        need(all(row[key] == old[key] for key in row), 'original root/child HEAD or index changed')
        now[name] = row
    links = []
    for line in git('ls-files', '--stage', repo=WORKSPACE).decode().splitlines():
        if line.startswith('160000 '):
            metadata, path = line.split('\t', 1)
            mode, oid, stage = metadata.split()
            links.append({'mode': mode, 'blob': oid, 'stage': int(stage), 'path': path})
    need(links == original['root_index_gitlinks'], 'original index Git links changed')
    return now


def omitted_reason(row):
    path = Path(row['path'])
    if path == P6 / 'extract_bindings_01.py':
        return 'original_planning_extractor_not_selected_for_Git'
    if path.is_relative_to(Q5):
        relative = path.relative_to(Q5)
        safe_metadata_receipts = {
            'manifest.json',
            'lake/history.json',
        }
        if relative.parts[0] == 'evidence' and 'metadata' in relative.parts:
            metadata_offset = relative.parts.index('metadata')
            if str(Path(*relative.parts[metadata_offset + 1:])) not in safe_metadata_receipts:
                return 'native_metadata_payload_body'
    if path.name in ('environment-manifest.json', 'metadata-inputs.json'):
        return 'raw_environment_manifest_or_metadata_inputs'
    if path.suffix not in ('.py', '.lean', '.md', '.json', '.xml'):
        return 'binary_log_or_lock'
    if path.suffix == '.json' and row['bytes'] > 1024**2:
        return 'json_over_1MiB'
    return None


def validate_HF_gate(read_file, gate):
    need(type(gate) is dict and set(gate) == {'commit', 'publication_closed', 'public_readback', 'ledger'} and
         type(gate['commit']) is str and re.fullmatch('[0-9a-f]{40}', gate['commit']) is not None,
         'actual complete verified HF gate required')
    gate_root = WORKSPACE / 'maintenance/ranker-objective-scalar-publication-root-20261005-01'
    expected_paths = {'publication_closed': gate_root / 'hf-publication-01/closed.json',
                      'public_readback': gate_root / 'hf-public-readback-01.json',
                      'ledger': gate_root / 'release-publication-ledger-01.json'}
    documents = {}
    for key, path in expected_paths.items():
        row = gate[key]
        need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'} and row['path'] == str(path) and
             type(row['bytes']) is int and 0 < row['bytes'] <= 16 * 1024**2 and
             type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None,
             'exact safe HF gate descriptor required')
        raw = read_file(path)
        need({'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == row,
             'HF gate parsed bytes differ from exact descriptor')
        documents[key] = json.loads(raw)
    closed, public, ledger = [documents[key] for key in ('publication_closed', 'public_readback', 'ledger')]
    parent = 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e'
    commit = gate['commit']
    files, total = closed.get('files'), closed.get('selected_bytes')
    need(type(files) is int and 0 < files <= 100 and type(total) is int and 0 < total <= 256 * 1024**2,
         'bounded exact actual HF upload population')
    need(closed.get('schema') == 'terminal-ir-HF-successor-publication@1' and closed.get('status') == 'PUBLISHED_AND_VERIFIED' and
         closed.get('commit') == commit and closed.get('parent') == parent and closed.get('remote_readback_verified') is True and
         type(closed.get('prior_immutable_remote_files_preserved')) is int and closed['prior_immutable_remote_files_preserved'] == 329,
         'actual successful HF publication and prior329 preservation required')
    need(public.get('schema') == 'ranker-objective-scalar-public-HF-readback-join@1' and public.get('status') == 'passed' and
         public.get('commit') == commit and public.get('parent') == parent and public.get('fresh_public_main_matches_commit') is True and
         public.get('fresh_public_main_after_tree_matches_commit') is True and public.get('all_selected_local_pins_rechecked') is True and
         type(public.get('prior_immutable_files_preserved')) is int and public['prior_immutable_files_preserved'] == 329 and
         type(public.get('selected_files')) is int and public['selected_files'] == files and
         type(public.get('selected_bytes')) is int and public['selected_bytes'] == total and
         type(public.get('committed_total_regular_files')) is int and public['committed_total_regular_files'] == 331 + files - 2,
         'independent public HF tree and exact population join required')
    hf = ledger.get('huggingface', {}); inputs = ledger.get('input_receipts', {})
    need(ledger.get('schema') == 'ranker-objective-scalar-release-publication-ledger@1' and
         ledger.get('status') == 'HF_PUBLISHED_AND_VERIFIED_GITHUB_PUBLICATION_PENDING' and
         hf.get('commit') == commit and hf.get('parent') == parent and hf.get('status') == 'PUBLISHED_AND_VERIFIED' and
         type(hf.get('selected_files')) is int and hf['selected_files'] == files and type(hf.get('selected_bytes')) is int and
         hf['selected_bytes'] == total and type(hf.get('prior_immutable_files_preserved')) is int and
         hf['prior_immutable_files_preserved'] == 329 and hf.get('committed_total_regular_files') == 331 + files - 2 and
         hf.get('public_readback') == gate['public_readback'] and inputs.get('hf_closed') == gate['publication_closed'] and
         inputs.get('public_readback') == gate['public_readback'] and inputs.get('hf_plan') == closed.get('plan') and
         all(ledger.get(key) is False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')) and
         ledger.get('full_task_satisfaction') == 'unknown' and ledger.get('all32_governing_RPI_exits') == 'OPEN',
         'actual HF ledger exact joins and unchanged authority boundaries required')
    return documents


def main():
    need(__debug__, 'optimized Python refused')
    gate, gate_pin = document(HF_GATE_PATH, HF_GATE_SHA)
    gate_documents = validate_HF_gate(read, gate)
    need(gate_documents['ledger']['input_receipts']['frozen_inputs']['sha256'] == CLOSURE_SHA, 'HF gate joins this frozen closure')
    before = guards()
    need(git('rev-parse', 'HEAD').decode().strip() == PARENT, 'private parent changed')
    need(git('status', '--porcelain=v1', '--untracked-files=all') == b'', 'fresh private checkout must be clean')
    remote = git('ls-remote', 'origin', 'refs/heads/main').decode().strip().split()
    need(remote == [PARENT, 'refs/heads/main'], 'GitHub main advanced; preserve fresh parent before staging')
    seal_path = Q5 / 'file-only-seal-01.json'
    review_path = Q5 / 'qualified-review-01.json'
    seal, seal_pin = document(seal_path, SEAL_SHA)
    review, review_pin = document(review_path, REVIEW_SHA)
    closure, closure_pin = document(S4 / 'closed-inputs.json', CLOSURE_SHA)
    need(review.get('status') == 'passed' and seal['review'] == review_pin, 'exact final qualified review join')
    need(seal['regular_file_count'] == len(seal['files']) == 276 and seal['regular_file_bytes'] == sum(row['bytes'] for row in seal['files']) == 78794802 and
        hashlib.sha256(wire(seal['files'])).hexdigest() == seal['file_inventory_sha256'] and seal['fixture_symlinks'] == [] and seal['excluded_dependency_roots'] == [], 'exact complete no-alias final Q5 census required')
    selection, selection_pin = document(S4 / 'final-selection.json', closure['final_selection']['sha256'])
    need(selection_pin == closure['final_selection'], 'frozen final selection pin differs')
    plan, plan_pin = document(S4 / 'plan.json', closure['plan']['sha256'])
    need(plan_pin == closure['plan'] and closure.get('schema') == 'ranker-objective-scalar-publication-closed-inputs@1' and
         plan.get('schema') == 'ranker-objective-scalar-publication-plan@1' and plan.get('status') == 'frozen_final_plan' and
         plan.get('source_and_artifacts_quiet') is True and plan.get('source_plan_quiet') is True,
         'same-buffer final closure/selection/plan joins required')
    need(len(selection['files']) == EXPECTED_SELECTION_COUNT and sum(row['bytes'] for row in selection['files']) == EXPECTED_SELECTION_BYTES and selection['exclusions'] == [], 'complete frozen publication population differs')
    selected, omitted = [], []
    sealed_by_path = {row['path']: row for row in seal['files']}
    for row in selection['files']:
        path = Path(row['path'])
        need(path.is_relative_to(Q5) or path.is_relative_to(P6) or path.is_relative_to(S4), 'new owned selected source scope required')
        bound = {key: row[key] for key in ('path', 'bytes', 'sha256')}
        if str(path) in sealed_by_path:
            need(bound == sealed_by_path[str(path)], 'package selection changed a final sealed descriptor')
        reason = omitted_reason(bound)
        if reason:
            omitted.append({**bound, 'reason': reason})
        else:
            need(pin(path) == bound, 'compact source pin differs')
            selected.append({**bound, 'binding_origin': 'frozen_full_package_selection'})
    for name in ('plan.json', 'closed-inputs.json', 'final-selection.json'):
        path = S4 / name
        row = pin(path)
        bound = {'plan.json': plan_pin, 'closed-inputs.json': closure_pin, 'final-selection.json': selection_pin}[name]
        need(row == bound, 'final planning receipt changed after parsed binding')
        need(omitted_reason(row) is None and str(path) not in {item['path'] for item in selected}, 'new safe final planning receipt required')
        selected.append({**row, 'binding_origin': 'externally_pinned_frozen_planning_receipt'})
    # The optional next planning originals must already have exact frozen copies.
    if INCLUDE_NEXT_PLANS:
        next_plan = WORKSPACE / 'qualification/codebase_ir/ranker-objective-container-source-plan-20261005-01'
        provenance, _ = document(Path(plan['provenance_map']['path']), plan['provenance_map']['sha256'])
        copies = {row['original']['path']: row for row in provenance['copies']}
        proposal, _ = document(next_plan / 'source-plan.json')
        need(proposal['schema'] == 'ranker-objective-container-source-plan@1' and
             proposal['status'] == 'draft_unqualified_source_only_plan', 'unqualified next container planning only')
        for name in ('source-plan.json', 'source-bindings.json', 'ir-interface.json'):
            original = next_plan / name; original_pin = pin(original)
            clone = copies[str(original)]; captured_pin = clone['captured']
            need(clone['original'] == original_pin and clone['byte_exact_clone'] is True and
                 all(original_pin[key] == captured_pin[key] for key in ('bytes', 'sha256')) and
                 any(row['path'] == captured_pin['path'] and all(row[key] == captured_pin[key] for key in ('bytes', 'sha256'))
                     for row in selected), 'optional original planning document requires a complete frozen byte-exact capture')
            selected.append({**original_pin, 'binding_origin': 'explicit_next_phase_original_with_frozen_capture',
                             'claim_role': 'source_only_unqualified_objective_container_plan'})
    selected.sort(key=lambda row: os.fsencode(str(Path(row['path']).relative_to(WORKSPACE))))
    need(len(selected) == len({row['path'] for row in selected}), 'unique compact candidates required')
    parent_paths = set(git('ls-tree', '-r', '--name-only', PARENT).decode().splitlines())
    new = []
    for row in selected:
        relative = str(Path(row['path']).relative_to(WORKSPACE))
        if relative in parent_paths:
            tree_row = git('ls-tree', PARENT, '--', relative).decode().strip().split('\t')
            need(len(tree_row) == 2 and tree_row[1] == relative, 'single existing parent leaf')
            mode, kind, oid = tree_row[0].split()
            need(mode == '100644' and kind == 'blob', 'existing source path must remain a regular blob')
            body = git('cat-file', 'blob', oid)
            need(len(body) == row['bytes'] and hashlib.sha256(body).hexdigest() == row['sha256'],
                 'fresh parent contains a conflicting publication source; retain failure and inspect')
            omitted.append({**{key: row[key] for key in ('path', 'bytes', 'sha256')},
                            'reason': 'already_published_unchanged', 'parent_git_blob_oid': oid})
        else:
            new.append(row)
    selected = new
    need(len(selected) > 0, 'no new compact increment remains after preserving fresh parent')
    links = []
    for line in git('ls-tree', '-r', PARENT).decode().splitlines():
        if line.startswith('160000 '):
            metadata, path = line.split('\t', 1)
            mode, kind, oid = metadata.split()
            links.append({'path': path, 'mode': mode, 'oid': oid})
    need(len(links) == 9, 'fresh parent nine Git links required')
    for row in selected:
        need(pin(Path(row['path'])) == {key: row[key] for key in ('path', 'bytes', 'sha256')},
             'final selected source/captured/original planning input changed')
    need(pin(seal_path) == seal_pin and pin(review_path) == review_pin and pin(S4 / 'closed-inputs.json') == closure_pin and
         pin(S4 / 'plan.json') == plan_pin and pin(S4 / 'final-selection.json') == selection_pin,
         'final parsed document pins changed')
    validate_HF_gate(read, gate)
    need(pin(HF_GATE_PATH) == gate_pin, 'HF gate descriptor input changed')
    after = guards()
    need(before == after, 'original checkouts changed during read-only preparation')
    result = {'schema': 'ranker-objective-scalar-compact-private-git-candidate-selection@1', 'status': 'prepared_read_only_no_stage_commit_or_push',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': pin(Path(__file__).resolve()), 'parent': PARENT,
        'private_checkout': str(REPO), 'private_checkout_clean': True, 'reuse_prior_private_checkout_recommended': False, 'fresh_private_checkout_required': True,
        'verified_HF_publication_gate': gate, 'HF_gate_input': gate_pin, 'final_seal': seal_pin, 'qualified_review': review_pin, 'frozen_closed_inputs': closure_pin, 'frozen_full_selection': selection_pin,
        'selected_files': selected, 'selected_file_count': len(selected), 'selected_file_bytes': sum(row['bytes'] for row in selected),
        'omitted_full_package_files': omitted, 'omitted_file_count': len(omitted), 'omitted_file_bytes': sum(row['bytes'] for row in omitted),
        'omitted_reasons': dict(collections.Counter(row['reason'] for row in omitted)), 'full_omitted_bodies': 'retained in the separately frozen full HF increment; never omitted from its denominator',
        'parent_gitlinks': links, 'original_guard_before': before, 'original_guard_after': after, 'future_safe_package_HF_ledger_receipts_pending': True,
        'required_verified_HF_commit_before_stage_or_publish': True, 'raw_SDK_logs_excluded': True, 'native_classifier_codec_calls': 0,
        'Git_index_HEAD_or_ref_mutations': 0, 'stage_calls': 0, 'commit_calls': 0, 'push_calls': 0,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False, 'full_task_satisfaction': 'unknown'}
    target = ROOT / 'compact-candidate-selection-01.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False)+'\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': result['status'], 'receipt': pin(target), 'selected_files': len(selected), 'selected_bytes': result['selected_file_bytes'],
        'omitted_files': len(omitted), 'omitted_bytes': result['omitted_file_bytes'], 'original_guards_unchanged': True, 'parent': PARENT}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparation-root', required=True, type=Path)
    parser.add_argument('--include-frozen-next-plan-originals', action='store_true')
    parser.add_argument('--expected-parent', required=True)
    parser.add_argument('--hf-gate', required=True, type=Path)
    parser.add_argument('--expected-hf-gate-sha256', required=True)
    parser.add_argument('--expected-closed-inputs-sha256', required=True)
    parser.add_argument('--expected-selected-count', required=True, type=int)
    parser.add_argument('--expected-selected-bytes', required=True, type=int)
    args = parser.parse_args()
    ROOT = args.preparation_root
    need(ROOT.is_absolute() and ROOT.resolve(strict=True) == ROOT and ROOT.parent == WORKSPACE / 'maintenance' and
         re.fullmatch('ranker-objective-scalar-private-git-preparation-20261005-[0-9]{2}', ROOT.name) is not None, 'fresh canonical private preparation namespace')
    REPO = ROOT / 'root'
    need(REPO.resolve(strict=True) == REPO and REPO.is_dir(), 'isolated private checkout required')
    INCLUDE_NEXT_PLANS = args.include_frozen_next_plan_originals
    PARENT = args.expected_parent
    HF_GATE_PATH = args.hf_gate
    HF_GATE_SHA = args.expected_hf_gate_sha256
    need(re.fullmatch('[0-9a-f]{64}', HF_GATE_SHA) is not None, 'external actual HF gate document pin')
    CLOSURE_SHA = args.expected_closed_inputs_sha256
    EXPECTED_SELECTION_COUNT = args.expected_selected_count
    EXPECTED_SELECTION_BYTES = args.expected_selected_bytes
    need(len(PARENT) == 40 and all(c in '0123456789abcdef' for c in PARENT), 'fresh exact parent OID required')
    need(len(CLOSURE_SHA) == 64 and all(c in '0123456789abcdef' for c in CLOSURE_SHA), 'exact closure SHA256 required')
    need(0 < EXPECTED_SELECTION_COUNT <= 10000 and 0 < EXPECTED_SELECTION_BYTES <= 256 * 1024**2, 'bounded full selection census required')
    main()
