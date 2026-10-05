"""Prepare a pinned source-slice upload from closed local evidence. File-only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

W=Path('/home/barberb/lift_coding')
R=Path(__file__).resolve().parent
S=W/'maintenance/ranker-source-slices-publication-20261005-01'
P=W/'maintenance/ranker-source-slices-publication-package-20261005-01'
Q=W/'qualification/codebase_ir/ranker-source-semantics-20261005-01'
PARENT='d6b6e333f3b1bcfe9028a8ca5ac3be6b12256e8a'
PREFIX='releases/20261004-terminal-codebase-ir-evidence-v1'
NS=PREFIX+'/successor-ranker-source-slices-v1'
HELD={}


def need(v,message):
    if v is not True:raise ValueError(message)


def read(path):
    path=Path(path).absolute();need(path.resolve(strict=True)==path and not path.is_symlink(),'canonical input')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_size<=32*1024**2,'bounded regular input')
        parts=[];total=0
        while block:=os.read(fd,1024**2):
            total+=len(block);need(total<=32*1024**2,'input grew beyond bound');parts.append(block)
        raw=b''.join(parts)
        sig=lambda v:tuple(getattr(v,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
        need(sig(a)==sig(os.fstat(fd))==sig(path.lstat()) and len(raw)==a.st_size,'input changed')
    finally:os.close(fd)
    return raw


def read_bound(path,expected=None):
    raw=read(path);binding={'path':str(Path(path).absolute()),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    if expected is not None:need(binding==expected,'exact same-buffer descriptor')
    if binding['path'] in HELD:need(HELD[binding['path']]==binding,'previously parsed/selected input changed')
    HELD[binding['path']]=binding
    return raw,binding


def pin(path):return read_bound(path)[1]


def load_bound(path,sha=None):
    raw,binding=read_bound(path)
    if sha is not None:need(binding['sha256']==sha,'independent document pin')
    return json.loads(raw),binding


def load(path,sha=None):return load_bound(path,sha)[0]

def save(path,raw):
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    return pin(path)


def encoded(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def main():
    need(__debug__,'optimized Python refused')
    parser=argparse.ArgumentParser()
    for n in ('baseline','manifest','package-review','qualification'):parser.add_argument('--expected-'+n+'-sha256',required=True)
    a=parser.parse_args()
    own=pin(Path(__file__).resolve())
    baseline,baseline_pin=load_bound(R/'HF-parent-preflight-01.json',a.expected_baseline_sha256)
    need(baseline['status']=='passed' and baseline['parent_commit']==PARENT and baseline['complete_regular_file_count']==276 and baseline['prior_immutable_files']==274 and baseline['namespace']==NS and baseline['namespace_unoccupied'] is True,'exact unoccupied parent baseline')
    need(all(pin(x['path'])==x for x in baseline['mutable_pointer_source_pins']),'prior mutable body drift')
    manifest,manifest_pin=load_bound(P/'package/manifest.json',a.expected_manifest_sha256)
    closed,closed_pin=load_bound(P/'closed.json');review,review_pin=load_bound(S/'package-review-01.json',a.expected_package_review_sha256)
    need(review['package_closure']==closed_pin,'decoded review exact package closure join')
    need(closed['status']=='passed_local_frozen_package' and closed['manifest']==manifest_pin and review['status']=='passed' and review['manifest']==manifest_pin,'closed package and complete decoded review')
    need(manifest['all_sealed_regular_files_retained'] is True and manifest['all_failed_attempts_retained'] is True and manifest['scan_hits']==[] and manifest['native_attempt_count_fact_gated']==3 and manifest['raw_external_dependency_bodies_published'] is False,'complete qualified evidence population')
    qual,qual_pin=load_bound(Q/'qualified-review-01.json',a.expected_qualification_sha256)
    need(qual['status']=='passed' and qual['native_lean_calls']==3 and qual['qualified_positive_native_lean_checks']==2 and qual['inconclusive_native_lean_checks_retained']==1 and qual['qualified_theorem_queries']==21 and qual['metadata_payloads']==4440 and qual['metadata_family_count']==32 and qual['additive_metadata_payloads']==23,'actual source-slice qualification')
    need(all(qual[k] is False for k in ('proof_authority','execution_authority','completion_authority','planner_activation','python_ranker_source_equivalence_proved','binary64_error_bound_proved','native_Float_optimizer_convergence_proved','global_autoencoder_convergence_proved','objective_to_IR_translation_proved','full_training_loop_to_IR_translation_proved')),'source/frontier authority')
    need(qual['all32_governing_RPI_exits']=='OPEN' and qual['full_task_satisfaction']=='unknown' and qual['official_benchmark_score'] is None,'task frontier')
    prior_by_name={Path(x['path']).name:x for x in baseline['mutable_pointer_source_pins']}
    card=read_bound(R/'prior-HF-README-01.md',prior_by_name['prior-HF-README-01.md'])[0]+b'''\n\n## Typed arithmetic source slices\n\nThis successor links the pinned ranker's dot multiplication and weight-update\nexpressions to a closed, typed scalar IR and to the previously proved exact-real\nranker step. Two accepted Lean modules provide 21 theorem queries; one earlier\nelaboration failure remains retained and unqualified. Only the standard Lean\naxioms are admitted. Each compiler version passed 137 pure controls, with no\nnative tools or subprocesses allowed during those tests. Complete compiled\nobjects, chunks and all three environment profiles are retained. No ranker\nimport, fit, feature preparation, gradient evaluation, optimizer update or\ntraining trace replay occurred in this increment.\n\nDuckDB/DuckLake hydration and fresh-process readback verify all 4,440 payloads\nacross the same 32 families. All 4,417 preceding payloads are exact canonical\nprefixes and all 375 vectors are unchanged. The 23 additions include AST/IR\nrecords, two mathematical projection-domain contracts, two accepted modules,\nthree actual attempt records and KG links. Contracts are not runtime-enforced\nand do not certify Python source contracts. No strict-cache admission or\noperational authority is added.\n\nThe exact-real backend defines ordered mathematical reduction and an equal-size\nFin80 projection domain. Python zip truncation is represented explicitly. The\noriginal-step theorem receives the mathematical gradient as an input; Python\n_objective's gradient computation is still open. Host-parser correctness, full\nPython source equivalence, math.fsum/binary64/libm refinement, feature preparation,\nthe full training loop, general codebase autoencoder convergence and Terminal\nBench task satisfaction remain open. All 32 RPI exits stay OPEN, all authority\nflags stay false, and no benchmark score is claimed.\n\nThe complete sealed increment and retained source planning history live in\nreleases/20261004-terminal-codebase-ir-evidence-v1/successor-ranker-source-slices-v1.\nEarlier immutable evidence and archive exclusions are preserved; prior large\narchives and raw external dependency bodies are not reuploaded.\n'''
    new_card=save(R/'HF-README-01.md',card)
    status,status_pin=load_bound(R/'prior-HF-publication-status-01.json',prior_by_name['prior-HF-publication-status-01.json']['sha256'])
    need(status_pin==prior_by_name['prior-HF-publication-status-01.json'],'prior status same-buffer join')
    status['status']='PUBLISHED_PRIOR_EVIDENCE_WITH_TYPED_SOURCE_SLICE_SUCCESSOR'
    status['ranker_typed_source_slice_qualification']={'qualified_review':qual_pin,'file_seal':pin(Q/'file-only-seal-01.json'),'package_manifest':manifest_pin,'decoded_package_review':review_pin,'namespace':NS,'native_attempts':3,'accepted_modules':2,'retained_inconclusive_attempts':1,'qualified_theorem_queries':21,'metadata_payloads':4440,'metadata_families':32,'new_projection_domain_contracts':2,'runtime_enforced_contracts_added':0,'unchanged_prior_payloads':4417,'unchanged_vectors':375,'new_training_calls':0,'python_source_equivalence_proved':False,'objective_gradient_translation_proved':False,'binary64_refinement_proved':False,'general_autoencoder_convergence_proved':False,'full_task_satisfaction':'unknown','all32_governing_RPI_exits':'OPEN','official_benchmark_score':None,'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False}
    new_status=save(R/'HF-publication-status-01.json',encoded(status))
    files=[]
    def add(path,remote):files.append({'local':pin(path),'remote':remote})
    for path in sorted((P/'package').iterdir()):
        need(path.is_file() and not path.is_symlink(),'regular package leaf');add(path,NS+'/package/'+path.name)
    for path in sorted(S.rglob('*')):
        if path.is_file():add(path,NS+'/publication/'+str(path.relative_to(S)))
    for name in ('README.md','qualified-review-01.json','file-only-seal-01.json','source-model-obligations-01.json'):
        add(Q/name,NS+'/qualification/'+name)
    for name in ('prepare_hf_plan_02.py','scan_final_upload_01.py','review_hf_readback_01.py','HF-parent-preflight-01.json'):
        add(R/name,NS+'/publication-root/'+name)
    files.extend([{'local':new_card,'remote':'README.md'},{'local':new_status,'remote':PREFIX+'/publication-status.json'}])
    need(0<len(files)<=100 and len({x['remote'] for x in files})==len(files),'bounded unique upload population')
    need(all(x['remote'] in ('README.md',PREFIX+'/publication-status.json') or x['remote'].startswith(NS+'/') for x in files),'new immutable namespace')
    need(all(x['remote'] not in baseline['files'] for x in files if x['remote'].startswith(NS+'/')),'namespace occupied')
    need(pin(Path(__file__).resolve())==own,'plan producer changed')
    plan={'schema':'terminal-ir-successor-evidence-publication-plan@1','repo_id':'Publicus/codebase-ir-proof-index','expected_parent_commit':PARENT,'immutable_namespace':NS,'files':files,'scope':'Pinned dot/update arithmetic slices projected to exactReal, supplied original mathematical gradient only','old_immutable_files_preserved':True,'large_prior_archive_reupload':False}
    need(all(pin(path)==binding for path,binding in list(HELD.items())),'all parsed/selected/prior inputs changed before plan closure')
    binding=save(R/'hf-plan-01.json',encoded(plan));print(json.dumps({'plan':binding,'files':len(files),'bytes':sum(x['local']['bytes'] for x in files)}))


if __name__=='__main__':main()
