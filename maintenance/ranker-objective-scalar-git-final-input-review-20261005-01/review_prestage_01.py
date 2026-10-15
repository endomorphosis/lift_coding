"""Independent bounded file-only prestage input review; no Git or target imports."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

W = Path('/home/barberb/lift_coding')
P = W/'maintenance/ranker-objective-scalar-private-git-preparation-20261005-01'
OUT = Path(__file__).resolve().parent
HELD = {}
EXPECTED = {
    'compact-candidate-selection-01.json': 'af96a29efc6ee15992a351c3cb08fe42d53d36d2b84e0e87093a63005c5c720e',
    'compact-base-selection-01.json': '654edc457809472587197cebebc4748d077997eadb7529a0b4be0987b9306ab5',
    'final-safe-receipts-selection-01.json': 'aa827d93ab27a415eaf921b696a0c201acfecac7d47d370c0c477fa984719fc7',
    'safe-selector-request-01.json': '383d1971a931b489ac0662f613bbf503408739f6c31ca9c42d7823702d31f83e',
}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def read(path):
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(), 'canonical source input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        first = os.fstat(fd)
        need(stat.S_ISREG(first.st_mode) and 0 <= first.st_size <= 16*1024**2, 'bounded regular input')
        pieces, count = [], 0
        while block := os.read(fd, 65536):
            count += len(block);need(count <= first.st_size, 'input grew');pieces.append(block)
        keys = ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        sig = lambda value: tuple(getattr(value,key) for key in keys)
        need(sig(first) == sig(os.fstat(fd)) == sig(path.lstat()) and count == first.st_size, 'input changed')
        raw = b''.join(pieces)
    finally:
        os.close(fd)
    need(path not in HELD or HELD[path] == raw, 'held input changed')
    HELD[path] = raw
    need(sum(len(value) for value in HELD.values()) <= 256*1024**2, 'aggregate body cap')
    return raw


def pin(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def bare(row):
    return {key:row[key] for key in ('path','bytes','sha256')}


def pairs(items):
    result={}
    for key,value in items:
        need(key not in result,'duplicate JSON key');result[key]=value
    return result


def parse(raw):
    def nonfinite(value):raise ValueError('nonfinite JSON')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)


def load(row):
    path=Path(row['path']);need(pin(path)==row,'same-buffer input pin');return parse(HELD[path])


def excluded(path):
    return any('private' in part or part=='__pycache__' or part.casefold() in
               {'.cache','cache','caches','download-cache','compiled-cache','datasets-cache'} or
               part.casefold().endswith('-cache') or part.casefold().startswith('cache-') for part in path.parts)


def census(roots):
    need(type(roots) is list and len(roots)==len(set(roots))==17,'exact17 safe roots')
    result={};count=0
    for value in roots:
        root=Path(value)
        need(root.parent==W/'maintenance' and root.resolve(strict=True)==root and root.is_dir() and
             root.name.startswith('ranker-objective-') and not excluded(root) and
             'git-publication' not in root.name and 'git-final-input-review' not in root.name,'public exact root')
        for parent,dirs,files in os.walk(root,followlinks=False):
            parent=Path(parent)
            for name in list(dirs):
                child=parent/name;need(not child.is_symlink(),'directory alias')
                if excluded(child.relative_to(root)):dirs.remove(name)
            for name in files:
                path=parent/name;need(not path.is_symlink(),'leaf alias');count+=1
                need(count<=10000,'physical census cap')
                if path.suffix not in ('.json','.py','.md','.lean','.xml') or path.name in ('environment-manifest.json','metadata-inputs.json') or excluded(path.relative_to(W)):
                    continue
                if path.stat().st_size>1024**2:continue
                row=pin(path);need(result.setdefault(str(path),row)==row,'overlapping pin changed')
    return result


def main():
    need(__debug__,'optimized reviewer refused')
    need(OUT==W/'maintenance/ranker-objective-scalar-git-final-input-review-20261005-01','external review output')
    docs={};inputs=[]
    for name,digest in EXPECTED.items():
        row=pin(P/name);need(row['sha256']==digest,'external input SHA');inputs.append(row);docs[name]=load(row)
    candidate,base,extra,request=(docs[name] for name in EXPECTED)
    candidate_pin,base_pin,extra_pin,request_pin=inputs
    expected_base={**candidate,'schema':'ranker-objective-scalar-compact-private-git-base-selection@1',
                   'status':'closed_exact_frozen_compact_candidate_base','future_safe_package_HF_ledger_receipts_pending':False,
                   'candidate_selection':candidate_pin,'safe_selector_request':request_pin}
    need(base==expected_base and extra['base_selection']==base_pin and extra['candidate_selection']==candidate_pin and
         extra['request']==request_pin,'exact base/candidate/request joins')
    need(request['schema']=='ranker-objective-scalar-safe-Git-selector-request@1' and
         set(request)=={'schema','candidate_selection','verified_HF_publication_gate','safe_extra_roots','files'} and
         request['candidate_selection']==candidate_pin and request['files']==extra['files'] and
         request['safe_extra_roots']==extra['safe_extra_roots'],'complete closed safe request')
    for body in (candidate,base,extra):
        need(all(body[key] is False for key in ('proof_authority','execution_authority','completion_authority','planner_activation')) and
             body['full_task_satisfaction']=='unknown','honest authority frontiers')
    gate=extra['verified_HF_publication_gate']
    need(gate==candidate['verified_HF_publication_gate']==request['verified_HF_publication_gate'] and
         gate['commit']=='57c2bbf12ab14a597148cfbc874947ca17481ca3','one actual HF gate')
    closed,public,ledger=(load(gate[key]) for key in ('publication_closed','public_readback','ledger'))
    parent='fae2e38dc882929edb2bcd2226560f0da3dfcd9e'
    need(closed['status']=='PUBLISHED_AND_VERIFIED' and public['status']=='passed' and
         ledger['status']=='HF_PUBLISHED_AND_VERIFIED_GITHUB_PUBLICATION_PENDING' and
         closed['commit']==public['commit']==ledger['huggingface']['commit']==gate['commit'] and
         closed['parent']==public['parent']==ledger['huggingface']['parent']==parent and
         closed['files']==public['selected_files']==ledger['huggingface']['selected_files']==83 and
         closed['selected_bytes']==public['selected_bytes']==ledger['huggingface']['selected_bytes'] and
         closed['prior_immutable_remote_files_preserved']==public['prior_immutable_files_preserved']==329 and
         public['committed_total_regular_files']==412 and public['all_selected_local_pins_rechecked'] is True and
         public['fresh_public_main_matches_commit'] is public['fresh_public_main_after_tree_matches_commit'] is True,
         'successful actual HF prior329/fulltree/count joins')
    need(ledger['input_receipts']['hf_closed']==gate['publication_closed'] and
         ledger['input_receipts']['public_readback']==gate['public_readback'] and
         ledger['input_receipts']['frozen_inputs']==candidate['frozen_closed_inputs'] and
         all(ledger[key] is False for key in ('proof_authority','execution_authority','completion_authority','planner_activation')),
         'actual immutable ledger input joins')
    base_rows={row['path']:bare(row) for row in base['selected_files']}
    need(len(base_rows)==len(base['selected_files'])==base['selected_file_count']==137 and
         sum(row['bytes'] for row in base_rows.values())==base['selected_file_bytes']==3767845,'base137/3767845')
    physical=census(extra['safe_extra_roots'])
    extras={path:row for path,row in physical.items() if path not in base_rows}
    need(extras=={row['path']:row for row in extra['files']} and
         len(extras)==len(extra['files'])==extra['selected_file_count']==100 and
         sum(row['bytes'] for row in extras.values())==extra['selected_file_bytes']==11102939,'complete exact100 extras')
    sources={**base_rows,**extras}
    need(len(sources)==237 and sum(row['bytes'] for row in sources.values())==14870784,'combined237/14870784')
    for row in sources.values():
        path=Path(row['path']);need(pin(path)==row,'selected body pin')
        raw=HELD[path];raw.decode('utf-8');need(b'\0' not in raw,'plain text source')
        if path.suffix=='.json':need(len(raw)<=1024**2,'JSON1MiB');parse(raw)
    need(all(sources.get(gate[key]['path'])==gate[key] for key in ('publication_closed','public_readback','ledger')),'all3 HF gate receipts selected')
    closure=load(candidate['frozen_closed_inputs']);full=load(candidate['frozen_full_selection']);plan=load(closure['plan'])
    need(closure['final_selection']==candidate['frozen_full_selection'] and len(full['files'])==335 and
         sum(row['bytes'] for row in full['files'])==80792847 and full['exclusions']==[],'whole fullHF denominator')
    expected={row['path']:bare(row) for row in full['files']}
    for row in (closure['plan'],candidate['frozen_closed_inputs'],candidate['frozen_full_selection']):expected[row['path']]=row
    next_dir=W/'qualification/codebase_ir/ranker-objective-container-source-plan-20261005-01'
    provenance=load(plan['provenance_map']);copies={row['original']['path']:row for row in provenance['copies']}
    for name in ('source-plan.json','source-bindings.json','ir-interface.json'):
        row=pin(next_dir/name);copy=copies[row['path']]
        need(copy['original']==row and copy['byte_exact_clone'] is True and
             (row['bytes'],row['sha256'])==(copy['captured']['bytes'],copy['captured']['sha256']) and
             expected[copy['captured']['path']]==copy['captured'],'P7 exact frozen original/copy planning joins')
        expected[row['path']]=row
    omitted={row['path']:bare(row) for row in base['omitted_full_package_files']}
    need(len(omitted)==len(base['omitted_full_package_files'])==base['omitted_file_count']==204 and
         not set(base_rows)&set(omitted) and {**base_rows,**omitted}==expected,'complete341 selected/omitted accounting')
    need(census(extra['safe_extra_roots'])==physical,'final physical census stable')
    for path,raw in list(HELD.items()):need(read(path)==raw,'final held input stable')
    own=pin(Path(__file__).resolve())
    result={'schema':'ranker-objective-scalar-independent-prestage-Git-input-review@1','status':'passed_file_only_actual_HF_gate_and_exact_compact_selection',
        'findings':[],'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':own,'reviewed_input_pins':inputs+[gate[key] for key in ('publication_closed','public_readback','ledger')],
        'actual_HF_commit':gate['commit'],'actual_HF_parent':parent,'actual_HF_uploaded_files':83,
        'combined_selected_files':237,'combined_selected_bytes':14870784,'base_selected_files':137,'base_selected_bytes':3767845,
        'safe_extra_selected_files':100,'safe_extra_selected_bytes':11102939,'explicit_safe_roots':17,'complete_safe_physical_files':len(physical),
        'full_HF_files':335,'full_HF_bytes':80792847,'full_frozen_partition_rows_including6_original_planning_receipts':341,
        'all237_selected_pins_rehashed_and_plain_text_checked':True,'physical_safe_census_and_same_buffer_request_base_candidate_receipts_joins':True,
        'Git_network_classifier_codec_native_model_test_or_target_import_jobs':0,'poststage_peer_still_required':True,
        'all32_governing_RPI_exits':'OPEN','proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
        'full_task_satisfaction':'unknown','official_benchmark_score':None,
        'limitations':['Original guards, full private parent/index/tree, all9 live gitlinks and actual staged blobs remain the admitted stage and independent poststage peer gates.','No new public network read was made; actual HF state is joined through the independently pinned successful receipts.']}
    target=OUT/'prestage-review-01.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode());stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'status':result['status'],'receipt':pin(target),'producer':own}))


if __name__=='__main__':main()
