"""Prepare exact safe receipt selectors only from a pinned explicit request.

File-only; no Git, classifier, codec, network or target/project import occurs.
Inputs are the admitted compact candidate, complete safe-root census and actual HF gate.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat

WORKSPACE = Path('/home/barberb/lift_coding')
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


def safe_extra(path):
    relative = path.relative_to(WORKSPACE)
    return (len(relative.parts) >= 3 and relative.parts[0] == 'maintenance' and
            relative.parts[1].startswith('ranker-objective-') and 'git-publication' not in relative.parts[1] and
            path.suffix in ('.json', '.py', '.md', '.lean', '.xml') and
            path.name not in ('environment-manifest.json', 'metadata-inputs.json') and
            not any('private' in part or part == '__pycache__' or part.casefold() in
                {'.cache', 'cache', 'caches', 'download-cache', 'compiled-cache', 'datasets-cache'} or
                part.casefold().endswith('-cache') or part.casefold().startswith('cache-') for part in relative.parts) and
            path.stat().st_size <= 1024**2)


def census(roots):
    need(type(roots) is list and 0 < len(roots) <= 32 and len(set(roots)) == len(roots), 'bounded unique explicit safe-extra roots')
    rows = {}
    for item in roots:
        root = Path(item)
        need(root.is_absolute() and root.resolve(strict=True) == root and root.is_dir() and
             root.parent == WORKSPACE / 'maintenance' and root.name.startswith('ranker-objective-') and
             'private' not in root.name and 'git-publication' not in root.name and
             'git-final-input-review' not in root.name, 'only public current scope roots; external final peer refused')
        for parent, dirs, files in os.walk(root, followlinks=False):
            parent = Path(parent)
            for name in list(dirs):
                child = parent/name
                need(not child.is_symlink(), 'safe roots forbid directory aliases')
                if any('private' in part or part == '__pycache__' or part.casefold() in
                    {'.cache','cache','caches','download-cache','compiled-cache','datasets-cache'} or
                    part.casefold().endswith('-cache') or part.casefold().startswith('cache-') for part in child.relative_to(root).parts):
                    dirs.remove(name)
            for name in files:
                path = parent/name
                need(not path.is_symlink(), 'safe roots forbid file aliases')
                if safe_extra(path):
                    row = pin(path); old = rows.setdefault(str(path), row)
                    need(old == row, 'overlapping safe roots changed pin')
    return rows


def save(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode())
        stream.flush();os.fsync(stream.fileno())
    return pin(path)


def main():
    need(__debug__, 'optimized Python refused')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparation-root', required=True, type=Path)
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--expected-request-sha256', required=True)
    a = parser.parse_args(); root = a.preparation_root
    need(root.is_absolute() and root.resolve(strict=True) == root and root.parent == WORKSPACE/'maintenance' and
         re.fullmatch('ranker-objective-scalar-private-git-preparation-20261005-[0-9]{2}', root.name) is not None, 'canonical fresh preparation namespace')
    need(re.fullmatch('[0-9a-f]{64}', a.expected_request_sha256) is not None, 'external request SHA256 required')
    request, request_pin = document(a.request, a.expected_request_sha256)
    need(type(request) is dict and set(request) == {'schema','candidate_selection','verified_HF_publication_gate','safe_extra_roots','files'} and
         request['schema'] == 'ranker-objective-scalar-safe-Git-selector-request@1', 'closed explicit selector request')
    candidate, candidate_pin = document(root/'compact-candidate-selection-01.json')
    need(candidate_pin == request['candidate_selection'] and candidate['schema'] == 'ranker-objective-scalar-compact-private-git-candidate-selection@1' and
         candidate['status'] == 'prepared_read_only_no_stage_commit_or_push', 'exact admitted compact candidate')
    gate = request['verified_HF_publication_gate']; docs = validate_HF_gate(read, gate)
    need(gate == candidate['verified_HF_publication_gate'] and docs['ledger']['input_receipts']['frozen_inputs'] == candidate['frozen_closed_inputs'],
         'same actual HF and frozen source population')
    base_paths = {row['path'] for row in candidate['selected_files']}
    physical = census(request['safe_extra_roots'])
    extras = [row for path,row in physical.items() if path not in base_paths]
    extras.sort(key=lambda row: os.fsencode(str(Path(row['path']).relative_to(WORKSPACE))))
    need(type(request['files']) is list and extras == request['files'] and 0 < len(extras) <= 100,
         'complete explicitly pinned physical safe-extra census differs')
    need(all(gate[key] in extras or gate[key]['path'] in base_paths for key in ('publication_closed','public_readback','ledger')),
         'all actual HF gate receipts must be included')
    need(sum(row['bytes'] for row in candidate['selected_files']+extras) <= 256*1024**2, 'bounded compact Git text population')
    base = {**candidate, 'schema': 'ranker-objective-scalar-compact-private-git-base-selection@1',
            'status': 'closed_exact_frozen_compact_candidate_base', 'future_safe_package_HF_ledger_receipts_pending': False,
            'candidate_selection': candidate_pin, 'safe_selector_request': request_pin}
    receipts = {'schema':'ranker-objective-scalar-final-safe-Git-receipts@1','status':'prepared_file_only_actual_HF_verified',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': pin(Path(__file__).resolve()),
        'request':request_pin, 'candidate_selection':candidate_pin, 'safe_extra_roots':request['safe_extra_roots'],
        'verified_HF_publication_gate':gate, 'files':extras, 'selected_file_count':len(extras), 'selected_file_bytes':sum(row['bytes'] for row in extras),
        'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,'full_task_satisfaction':'unknown'}
    need(census(request['safe_extra_roots']) == physical and pin(a.request) == request_pin and
         pin(root/'compact-candidate-selection-01.json') == candidate_pin, 'safe sources or selection request changed')
    validate_HF_gate(read, gate)
    base_pin = save(root/'compact-base-selection-01.json', base)
    receipts['base_selection'] = base_pin
    receipt_pin = save(root/'final-safe-receipts-selection-01.json', receipts)
    print(json.dumps({'base':base_pin,'safe_receipts':receipt_pin,'extra_files':len(extras),'extra_bytes':receipts['selected_file_bytes']}))


if __name__ == '__main__':
    main()
