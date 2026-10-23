"""Independent source-only review of the exact guard-cohort closer03 patch."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

W=Path('/home/barberb/lift_coding')
P=W/'maintenance/ranker-objective-container-core-v1-failure-closure-20261005-01'
Q=W/'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-01'
OUT=W/'maintenance/ranker-objective-container-core-v1-failure-closure-source-review-20261005-03'
EXPECTED={
 P/'close_failed_v1_02.py':(18157,'4e9bbf4766c5b17c1cf4b6db48b464d941244b59f3189d74ad35d56c0ae76be3'),
 P/'close_failed_v1_03.py':(20279,'170d688d043d66d8da4c20e1d56172bc72d5c6031959e30d15ddf395a7fd06c1'),
 P/'attempt-02.json':(984,'b048270eee3d213479f60299eb022dea21b5e66a08a0341c174726362246fb3a'),
 Q/'preparation/request-v3.json':(628543,'b1aba00577a79bb2e2818ddb426c3422d8247124b9fc274ae3a7620a4ff4e90d'),
 W/'maintenance/ranker-objective-container-core-v1-failure-closure-source-review-20261005-02/review-receipt.json':(4084,'109085eae544cb7b91da9e31ae6690f07f065c097308275258cb0968817654f4')}

def need(value,message):
    if value is not True:raise ValueError(message)

def read(path):
    need(path.resolve(strict=True)==path and not path.is_symlink(),'canonical review input')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        first=os.fstat(fd);need(stat.S_ISREG(first.st_mode) and first.st_size<=1024**2,'bounded regular source/receipt')
        parts=[];size=0
        while part:=os.read(fd,65536):
            size+=len(part);need(size<=first.st_size,'body grew');parts.append(part)
        sig=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        need(size==first.st_size and sig(first)==sig(os.fstat(fd))==sig(path.lstat()),'stable same-read source')
        raw=b''.join(parts);pin={'path':str(path),'bytes':size,'sha256':hashlib.sha256(raw).hexdigest()}
        need(path not in EXPECTED or (size,pin['sha256'])==EXPECTED[path],'exact external source/receipt pin')
        return raw,pin
    finally:os.close(fd)

def functions(raw):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}

def main():
    need(__debug__,'optimized review refused')
    inputs={p:read(p) for p in EXPECTED}
    old,new=[inputs[P/n][0].decode() for n in ('close_failed_v1_02.py','close_failed_v1_03.py')]
    a,b=functions(old),functions(new)
    need(set(a)==set(b) and all(a[k]==b[k] for k in a if k!='main'),'all bounded I/O/census/JSON/append helpers unchanged')
    gate=json.loads(inputs[W/'maintenance/ranker-objective-container-core-v1-failure-closure-source-review-20261005-02/review-receipt.json'][0])
    need(gate['status']=='passed_source_only' and gate['findings']==[] and gate['reviewed_source']==inputs[P/'close_failed_v1_02.py'][1],'prior reviewed closer02 join')
    request=json.loads(inputs[Q/'preparation/request-v3.json'][0]);strict={r['path']:r for r in request['strict_old_inputs']};live={r['path']:r for r in request['protected_live_sources']}
    overlap=set(strict)&set(live)
    need(len(request['strict_old_inputs'])==len(strict)==2391 and len(request['protected_live_sources'])==len(live)==4 and
         len(overlap)==4 and len(set(strict)|set(live))==2391 and all(strict[p]==live[p] for p in overlap),'actual unique cohorts and exact cross-cohort equality')
    attempt=json.loads(inputs[P/'attempt-02.json'][0])
    need(attempt['producer']==inputs[P/'close_failed_v1_02.py'][1] and attempt['status']=='failed_before_append_overlapping_guard_cohorts' and
         attempt['new_review_or_seal_written'] is False and attempt['cross_cohort_descriptors_equal'] is True and
         attempt['unique_combined_guard_paths']==2391 and attempt['cross_cohort_shared_paths']==4 and
         all(attempt[k] is False for k in ('proof_authority','execution_authority','completion_authority','planner_activation')) and
         all(type(attempt[k]) is int and attempt[k]==0 for k in ('new_native_invocations','new_test_invocations','project_imports','metadata_mutations')),'exact safe second refusal provenance')
    for token in ("len(overlap)==4", "all(strict_by_path[path]==live_by_path[path] for path in overlap)", "historical_attempt02", "'strict_live_union_count'", "'qualified_native_checks':0", "'qualified_theorem_queries':0", "len(initial)==28", "==10850381", "len(rows)==29", "'only review and seal append complete final census'"):
        need(token in new,'reviewed corrected cohort/history and unchanged zero-qualification/census controls')
    need(all(read(p)[1]==pin for p,(_,pin) in inputs.items()),'all inputs rehashed')
    receipt={'schema':'ranker-objective-container-core-failed-closure-independent-source-review@1','status':'passed_source_only','findings':[],
      'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':read(Path(__file__).resolve())[1],
      'reviewed_source':inputs[P/'close_failed_v1_03.py'][1],'reviewed_input_pins':[pin for _,pin in inputs.values()],
      'reviewed_patch':['Self path03; cohorts individually unique2391 and4; all four cross-cohort descriptors equal; combined physical guard union2391.',
        'Exact immutable closer02 and safe refusal02 provenance retained and verified; output records observed overlap and union.',
        'All bounded reader/descriptor/JSON/census/writer helper ASTs unchanged; native bounds, cleanup/drain, original guards, zero proof qualification and exclusive29-leaf seal/self checks preserved.'],
      'actual_guard_cohorts':{'strict_rows':2391,'live_rows':4,'cross_cohort_overlap':4,'combined_unique_paths':2391,'shared_descriptors_equal':True},
      'mode':'unexecuted_target_source_only','source_execution_calls':0,'native_test_model_metadata_or_remote_jobs':0,
      'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
      'all32_governing_RPI_exits':'OPEN','full_task_satisfaction':'unknown','official_benchmark_score':None,
      'limits':['Root must execute and retain actual closer03 outcome. This independent reviewer executes no closer, target import or native job.']}
    output=OUT/'review-receipt.json'
    with output.open('xb') as stream:
        stream.write((json.dumps(receipt,sort_keys=True,indent=2,allow_nan=False)+'\n').encode());stream.flush();os.fsync(stream.fileno())
    print(json.dumps(read(output)[1],sort_keys=True))

if __name__=='__main__':main()
