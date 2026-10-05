"""Stage the exact compact increment only after the verified HF receipt gate.

This source is prepared before publication but must not run until the root
supplies the actual verified HF commit, ledger, and exact safe receipt selection.
Only the reused isolated private checkout is mutated. Original guards and all
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
import subprocess
import tempfile
import types

WORKSPACE = Path('/home/barberb/lift_coding')
ROOT = Path(__file__).resolve().parent
REPO = ROOT / 'root'
BASE_SHA = '552a90051a73cf2c1abe6726bca6cccaec1a998c7fe1af83b055a6c76ec0f371'
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
    return subprocess.check_output(['git', '-C', str(REPO), *args], input=input, env=ENV)


def held_module(path, expected, name):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical held helper required')
    raw = path.read_bytes()
    need(len(raw) <= 16*1024**2 and hashlib.sha256(raw).hexdigest() == expected, 'held helper source pin differs')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def validate_HF_gate(api, gate):
    need(type(gate) is dict and set(gate) == {'commit', 'publication_closed', 'public_readback', 'ledger'} and
        re.fullmatch('[0-9a-f]{40}', gate['commit']) is not None, 'actual complete verified HF gate required')
    documents = {}
    for key in ('publication_closed', 'public_readback', 'ledger'):
        row = gate[key]
        path = Path(row['path'])
        need(path.is_relative_to(WORKSPACE / 'maintenance/ranker-convergence-publication-root-20261005-01') and
            path.suffix == '.json' and not path.name.endswith(('.log', '.zst')), 'safe new HF JSON gate descriptor required')
        raw = api.read(path)
        need({'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == row, 'HF gate parsed bytes differ from exact descriptor')
        documents[key] = json.loads(raw)
    closed, public, ledger = documents['publication_closed'], documents['public_readback'], documents['ledger']
    need(closed.get('status') == 'PUBLISHED_AND_VERIFIED' and closed.get('commit') == gate['commit'] and closed.get('remote_readback_verified') is True,
        'actual successful HF commit and remote readback required before Git staging')
    need(public.get('status') == 'passed' and public.get('commit') == gate['commit'] and public.get('fresh_public_main_matches_commit') is True and
        public.get('prior_immutable_files_preserved') == 225 and public.get('all_selected_local_pins_rechecked') is True, 'independent public HF readback and all prior225 preservation required')
    need(ledger.get('huggingface', {}).get('commit') == gate['commit'] and all(ledger.get(key) is False for key in
        ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')), 'actual safe release ledger and closed authority boundaries required')
    return documents


def main(args):
    need(re.fullmatch('[0-9a-f]{64}', args.expected_receipts_selection_sha256 or '') is not None, 'independent safe receipt selection SHA256 required')
    candidate_raw = (ROOT / 'compact-candidate-selection-01.json').read_bytes()
    need(hashlib.sha256(candidate_raw).hexdigest() == 'c32e32ac9e161486efc62c73602df07abdeb4ccc3ed3aaf698c24151a13ac9ff', 'prepared candidate receipt changed')
    candidate = json.loads(candidate_raw)
    api = held_module(Path(candidate['producer']['path']), candidate['producer']['sha256'], 'held_convergence_compact_source_reader')
    base_path = ROOT / 'compact-base-selection-01.json'
    base_raw = api.read(base_path)
    need(hashlib.sha256(base_raw).hexdigest() == BASE_SHA, 'parsed root-authorized base changed')
    base = json.loads(base_raw)
    before = api.guards()
    need(before == base['original_guard_after'], 'original guards differ from prepared closed base baseline')
    raw = api.read(args.receipts_selection)
    receipts_pin = {'path': str(args.receipts_selection), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    need(receipts_pin['sha256'] == args.expected_receipts_selection_sha256, 'actual safe receipt selection differs')
    receipts = json.loads(raw)
    need(receipts.get('schema') == 'ranker-convergence-final-safe-Git-receipts@1' and type(receipts.get('files')) is list and
        1 <= len(receipts['files']) <= 100, 'exact bounded final safe receipt selection required')
    gate = receipts.get('verified_HF_publication_gate')
    validate_HF_gate(api, gate)
    parent = base['parent']
    need(git('rev-parse', 'HEAD').decode().strip() == parent and git('status', '--porcelain=v1', '--untracked-files=all') == b'', 'clean prepared isolated parent required')
    need(git('ls-remote', 'origin', 'refs/heads/main').decode().strip().split() == [parent, 'refs/heads/main'], 'remote advanced; preserve new parent before staging')
    sources = {row['path']: {key: row[key] for key in ('path', 'bytes', 'sha256')} for row in base['selected_files']}
    for row in receipts['files']:
        need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}, 'exact safe receipt descriptor required')
        path = Path(row['path'])
        relative = path.relative_to(WORKSPACE)
        need(relative.parts[0] == 'maintenance' and relative.parts[1].startswith('ranker-convergence-') and path.suffix in ('.json', '.py', '.md', '.lean', '.xml') and
            not any('private' in part or part == '__pycache__' for part in relative.parts) and 'git-publication' not in relative.parts[1] and
            api.omitted_reason(row) is None and row['bytes'] <= 1024**2, 'only new compact public source/receipts; raw logs/caches/archive bodies refused')
        old = sources.setdefault(str(path), row)
        need(old == row, 'conflicting duplicate source pin')
    need(all(gate[key] in list(sources.values()) for key in ('publication_closed', 'public_readback', 'ledger')), 'all actual HF gate receipts must be in the Git increment')
    rows = sorted(sources.values(), key=lambda row: os.fsencode(str(Path(row['path']).relative_to(WORKSPACE))))
    parent_paths = set(git('ls-tree', '-r', '--name-only', parent).decode().splitlines())
    scanner_module = held_module(*HELPERS['archive'], 'held_convergence_git_archive')
    classifier = held_module(*HELPERS['classifier'], 'held_convergence_git_classifier')
    scanner = scanner_module.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in scanner_module.PATTERNS if name != 'private_key_pem']
    budget = classifier.Budget(seconds=120, decoded_bytes=16*1024**2, container_bytes=16*1024**2, members=1, depth=0)
    with tempfile.TemporaryDirectory(prefix='convergence-Git-text-scan-', dir=ROOT) as temporary:
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
    validate_HF_gate(api,gate)
    after = api.guards()
    need(before == after, 'original checkout guards changed during staging')
    result = {'schema':'ranker-convergence-final-private-git-stage@1','status':'passed_complete_increment_HF_verified_ready_to_commit','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'producer':api.pin(Path(__file__).resolve()),'base_selection':api.pin(base_path),'safe_receipts_selection':receipts_pin,'parent':parent,'tree':git('write-tree').decode().strip(),
        'verified_HF_publication_gate':gate,'hf_commit':gate['commit'],'staged_source_blobs':staged,'staged_file_count':len(staged),'staged_file_bytes':sum(row['bytes'] for row in staged),
        'parent_gitlinks':links,'all_nine_parent_gitlinks_unchanged':True,'all_new_staged_text_scanned':True,'credential_candidate_hits':0,'bounded_complete_PEM_and_cached_credential_veto':True,
        'original_guard_before':before,'original_guard_after':after,'raw_SDK_logs_archives_caches_private_worktrees_excluded':True,'native_model_solver_test_fit_codec_jobs':0,'project_imports':0,'stage_calls':1,'commit_calls':0,'push_calls':0,
        'proof_authority':False,'execution_authority':False,'completion_authority':False,'full_task_satisfaction':'unknown'}
    target = ROOT/'final-stage-closed-01.json'
    with target.open('xb') as handle:
        handle.write((json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode());handle.flush();os.fsync(handle.fileno())
    print(json.dumps({'status':result['status'],'receipt':api.pin(target),'staged_files':len(staged),'staged_bytes':result['staged_file_bytes'],'tree':result['tree']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipts-selection',required=True,type=Path)
    parser.add_argument('--expected-receipts-selection-sha256',required=True)
    main(parser.parse_args())
