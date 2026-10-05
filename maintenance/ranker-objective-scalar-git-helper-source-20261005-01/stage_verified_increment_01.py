"""Stage the exact compact increment only after the verified HF receipt gate.

This source is prepared before publication but must not run until the root
supplies the actual verified HF commit, ledger, and exact safe receipt selection.
Only the new isolated private checkout is mutated. Original guards and all
fresh-parent Git links are checked, and every final new Git text blob is scanned.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import types

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = None  # Explicit fresh preparation root is required at execution.
REPO = None
BASE_SHA = None  # Required final base pin is supplied at execution.
HF = WORKSPACE / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
HELPERS = {
    'archive': (HF / 'build_evidence_archive_02.py', 'f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036'),
    'classifier': (HF / 'classify_and_prepare_public_archive_07.py', 'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8'),
}
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS='0')


def need(value, message):
    if value is not True:
        raise ValueError(message)


def git(*args, input=None):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-C', str(REPO), *args], input=input, env=ENV)


def read_bounded(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical bounded source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= 16*1024**2, 'bounded regular source required')
        pieces, size = [], 0
        while block := os.read(fd, 1024**2):
            size += len(block)
            need(size <= 16*1024**2, 'source grew beyond read bound')
            pieces.append(block)
        fields = ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        signature = lambda value: tuple(getattr(value, field) for field in fields)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat()) and size == before.st_size,
             'bounded source changed during read')
        return b''.join(pieces)
    finally:
        os.close(fd)


def held_module(path, expected, name):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical held helper required')
    raw = read_bounded(path)
    need(len(raw) <= 16*1024**2 and hashlib.sha256(raw).hexdigest() == expected, 'held helper source pin differs')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


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


def main(args):
    need(__debug__, 'optimized Python refused')
    need(re.fullmatch('[0-9a-f]{64}', args.expected_receipts_selection_sha256 or '') is not None, 'independent safe receipt selection SHA256 required')
    need(re.fullmatch('[0-9a-f]{64}', args.expected_candidate_selection_sha256 or '') is not None and
         re.fullmatch('[0-9a-f]{64}', args.expected_base_selection_sha256 or '') is not None, 'independent candidate/base pins required')
    candidate_raw = read_bounded(ROOT / 'compact-candidate-selection-01.json')
    need(hashlib.sha256(candidate_raw).hexdigest() == args.expected_candidate_selection_sha256, 'prepared candidate receipt changed')
    candidate = json.loads(candidate_raw)
    api = held_module(Path(candidate['producer']['path']), candidate['producer']['sha256'], 'held_objective_scalar_compact_source_reader')
    base_path = ROOT / 'compact-base-selection-01.json'
    base_raw = api.read(base_path)
    need(hashlib.sha256(base_raw).hexdigest() == BASE_SHA, 'parsed root-authorized base changed')
    base = json.loads(base_raw)
    need(base['schema'] == 'ranker-objective-scalar-compact-private-git-base-selection@1' and
         base['candidate_selection'] == {'path': str(ROOT/'compact-candidate-selection-01.json'), 'bytes': len(candidate_raw),
          'sha256': args.expected_candidate_selection_sha256} and base['parent'] == candidate['parent'] and
         base['selected_files'] == candidate['selected_files'] and base['parent_gitlinks'] == candidate['parent_gitlinks'],
         'base must retain exact entire reviewed compact candidate')
    before = api.guards()
    need(before == base['original_guard_after'], 'original guards differ from prepared closed base baseline')
    raw = api.read(args.receipts_selection)
    receipts_pin = {'path': str(args.receipts_selection), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    need(receipts_pin['sha256'] == args.expected_receipts_selection_sha256, 'actual safe receipt selection differs')
    receipts = json.loads(raw)
    need(receipts.get('schema') == 'ranker-objective-scalar-final-safe-Git-receipts@1' and type(receipts.get('files')) is list and
        1 <= len(receipts['files']) <= 100, 'exact bounded final safe receipt selection required')
    gate = receipts.get('verified_HF_publication_gate')
    gate_docs = validate_HF_gate(api.read, gate)
    need(gate == candidate['verified_HF_publication_gate'] and
         gate_docs['ledger']['input_receipts']['frozen_inputs'] == candidate['frozen_closed_inputs'], 'same actual HF gate and frozen closure joins')
    parent = base['parent']
    need(git('rev-parse', 'HEAD').decode().strip() == parent and git('status', '--porcelain=v1', '--untracked-files=all') == b'', 'clean prepared isolated parent required')
    need(git('ls-remote', 'origin', 'refs/heads/main').decode().strip().split() == [parent, 'refs/heads/main'], 'remote advanced; preserve new parent before staging')
    sources = {row['path']: {key: row[key] for key in ('path', 'bytes', 'sha256')} for row in base['selected_files']}
    for row in receipts['files']:
        need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}, 'exact safe receipt descriptor required')
        path = Path(row['path'])
        relative = path.relative_to(WORKSPACE)
        need(relative.parts[0] == 'maintenance' and relative.parts[1].startswith('ranker-objective-') and path.suffix in ('.json', '.py', '.md', '.lean', '.xml') and
            not any('private' in part or part == '__pycache__' for part in relative.parts) and 'git-publication' not in relative.parts[1] and
            not any(part.casefold() in {'.cache','cache','caches','download-cache','compiled-cache','datasets-cache'} or
                    part.casefold().endswith('-cache') or part.casefold().startswith('cache-') for part in relative.parts[:-1]) and
            api.omitted_reason(row) is None and row['bytes'] <= 1024**2, 'only new compact public source/receipts; raw logs/caches/archive bodies refused')
        old = sources.setdefault(str(path), row)
        need(old == row, 'conflicting duplicate source pin')
    need(all(gate[key] in list(sources.values()) for key in ('publication_closed', 'public_readback', 'ledger')), 'all actual HF gate receipts must be in the Git increment')
    rows = sorted(sources.values(), key=lambda row: os.fsencode(str(Path(row['path']).relative_to(WORKSPACE))))
    need(0 < len(rows) <= 10000 and sum(row['bytes'] for row in rows) <= 256*1024**2, 'bounded compact Git text population')
    parent_paths = set(git('ls-tree', '-r', '--name-only', parent).decode().splitlines())
    scanner_module = held_module(*HELPERS['archive'], 'held_objective_scalar_git_archive')
    classifier = held_module(*HELPERS['classifier'], 'held_objective_scalar_git_classifier')
    scanner = scanner_module.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in scanner_module.PATTERNS if name != 'private_key_pem']
    budget = classifier.Budget(seconds=120, decoded_bytes=16*1024**2, container_bytes=16*1024**2, members=1, depth=0)
    with tempfile.TemporaryDirectory(prefix='objective-scalar-Git-text-scan-', dir=ROOT) as temporary:
        for row in rows:
            path = Path(row['path'])
            relative = path.relative_to(WORKSPACE)
            need(str(relative) not in parent_paths and api.pin(path) == row, 'only exact new source pins required')
            raw = api.read(path)
            need(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], 'scanned raw source differs from exact descriptor')
            need(classifier.Classifier.format(raw[:512]) is None, 'all compact Git bodies must be plain source or receipts')
            inspection = classifier.Classifier(scanner, budget, Path(temporary))
            inspection.inspect(io.BytesIO(raw))
            need(not inspection.hits, 'complete cached-credential/PEM classifier veto refused new Git text')
    need(budget.decoded == 0 and budget.members == 0, 'no codec/container jobs needed for Git text')
    for row in rows:
        source = Path(row['path'])
        target = REPO / source.relative_to(WORKSPACE)
        need(not target.exists() and not target.is_symlink(), 'new private destination required')
        target.parent.mkdir(parents=True, exist_ok=True)
        need(target.parent.resolve(strict=True) == target.parent, 'canonical private destination parent required')
        with target.open('xb') as stream:
            stream.write(api.read(source))
        target.chmod(0o644)
        need(api.pin(target)['sha256'] == row['sha256'], 'private source copy differs')
    paths = [str(Path(row['path']).relative_to(WORKSPACE)) for row in rows]
    git('-c', 'core.autocrlf=false', 'add', '--pathspec-from-file=-', '--pathspec-file-nul', input=b''.join(os.fsencode(path)+b'\0' for path in paths))
    wire = git('diff', '--cached', '--name-status', '-z').split(b'\0')
    need([(wire[i].decode(), os.fsdecode(wire[i+1])) for i in range(0,len(wire)-1,2)] == [('A',path) for path in paths], 'only exact complete new additions may be staged')
    index, links = {}, []
    for line in git('ls-files', '--stage').decode().splitlines():
        metadata, path = line.split('\t',1)
        mode, oid, stage = metadata.split()
        need(stage == '0', 'unmerged index refused')
        index[path] = (mode,oid)
        if mode == '160000':
            links.append({'path':path,'mode':mode,'oid':oid})
    need(links == base['parent_gitlinks'], 'all nine fresh parent Git links must remain unchanged')
    stream = io.BytesIO(git('cat-file','--batch',input=''.join(index[path][1]+'\n' for path in paths).encode()))
    staged = []
    for path, original in zip(paths,rows):
        oid,kind,size = stream.readline().decode().strip().split()
        raw = stream.read(int(size))
        need(stream.read(1) == b'\n' and kind == 'blob' and index[path] == ('100644',oid), 'exact regular staged Git blob required')
        row = {'path':path,'mode':'100644','git_blob_oid':oid,'bytes':int(size),'sha256':hashlib.sha256(raw).hexdigest()}
        need(all(row[key] == original[key] for key in ('bytes','sha256')), 'staged blob differs from scanned source')
        need(api.pin(WORKSPACE/path)['sha256'] == row['sha256'], 'source changed during staging')
        staged.append(row)
    need(stream.read() == b'', 'unexpected staged blob tail')
    validate_HF_gate(api.read,gate)
    after = api.guards()
    need(before == after, 'original checkout guards changed during staging')
    result = {'schema':'ranker-objective-scalar-final-private-git-stage@1','status':'passed_complete_increment_HF_verified_ready_to_commit','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'producer':api.pin(Path(__file__).resolve()),'base_selection':api.pin(base_path),'safe_receipts_selection':receipts_pin,'parent':parent,'tree':git('write-tree').decode().strip(),
        'verified_HF_publication_gate':gate,'hf_commit':gate['commit'],'staged_source_blobs':staged,'staged_file_count':len(staged),'staged_file_bytes':sum(row['bytes'] for row in staged),
        'parent_gitlinks':links,'all_nine_parent_gitlinks_unchanged':True,'all_new_staged_text_scanned':True,'credential_candidate_hits':0,'bounded_complete_PEM_and_cached_credential_veto':True,
        'original_guard_before':before,'original_guard_after':after,'raw_SDK_logs_archives_caches_private_worktrees_excluded':True,'native_model_solver_test_fit_codec_jobs':0,'project_imports':0,'stage_calls':1,'commit_calls':0,'push_calls':0,
        'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,'full_task_satisfaction':'unknown'}
    target = ROOT/'final-stage-closed-01.json'
    with target.open('xb') as handle:
        handle.write((json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode());handle.flush();os.fsync(handle.fileno())
    print(json.dumps({'status':result['status'],'receipt':api.pin(target),'staged_files':len(staged),'staged_bytes':result['staged_file_bytes'],'tree':result['tree']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparation-root',required=True,type=Path)
    parser.add_argument('--receipts-selection',required=True,type=Path)
    parser.add_argument('--expected-receipts-selection-sha256',required=True)
    parser.add_argument('--expected-candidate-selection-sha256',required=True)
    parser.add_argument('--expected-base-selection-sha256',required=True)
    args = parser.parse_args()
    ROOT = args.preparation_root
    need(ROOT.is_absolute() and ROOT.resolve(strict=True)==ROOT and ROOT.parent==WORKSPACE/'maintenance' and
         re.fullmatch('ranker-objective-scalar-private-git-preparation-20261005-[0-9]{2}',ROOT.name) is not None, 'fresh canonical private preparation namespace')
    REPO = ROOT/'root'
    need(REPO.resolve(strict=True)==REPO and REPO.is_dir(), 'isolated private checkout required')
    BASE_SHA = args.expected_base_selection_sha256
    main(args)
