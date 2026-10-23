"""Append a review and complete file-only seal of the failed Q6v1 attempt.

Inert stdlib source. Root execution requires external source/source-review
SHA256 pins and the fixed actual input/attempt pins. No old byte is edited; only two exclusive new
receipts are appended in Q6v1 after the original complete census is rechecked.
No Git, network, native, project import, model, test or metadata job occurs.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

W=Path('/home/barberb/lift_coding')
Q=W/'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-01'
SOURCE=W/'maintenance/ranker-objective-container-core-v1-failure-closure-20261005-01/close_failed_v1_01.py'
MODE='lean-objective-container-core-01'
MAX_JSON=32*1024**2
MAX_FILE=256*1024**2
HELD={}
DEADLINE=None
QUERIES=['RankerObjectiveContainerIR.map_exact_ofFn_success','RankerObjectiveContainerIR.mean_exact_ofFn_success',
         'RankerObjectiveContainerIR.mean_exact_empty_refuses','RankerObjectiveContainerIR.indexed_zip_fsum_ofFn_eq']
FIXED={
 'request':(Q/'preparation/request-v3.json',628543,'b1aba00577a79bb2e2818ddb426c3422d8247124b9fc274ae3a7620a4ff4e90d'),
 'specification':(Q/'preparation/lean-objective-container-core-01-check-specification.json',18883,'36098ccd6c52833fef43f675aa990d3e9d2f96ff6d296169a0dfd6881f20cca7'),
 'profile':(Q/'preparation/lean-objective-container-core-01-producer/environment-manifest.json',9976569,'ccd64014d7b3c9df828d25b28a6d27fb0a68fd4adac60c660b9a294bdd6f3d79'),
 'invocation':(Q/'preparation/lean-objective-container-core-01-invocation.json',6942,'307d3eff4cb2f2794f137adedb385af0e514f2ea32e9348baa8bd16a459e6c59'),
 'owned':(Q/'evidence/lean-objective-container-core-01/closed.json',18690,'37b775169ca4c2cc34a94b1dedfe33d30a5f438af63bb468536218da89168464'),
 'outer':(Q/'evidence/lean-objective-container-core-01-closed.json',1493,'5155fef0434a8e0651b8acf3d2451940dbbbcb11ada27786b7e8e95fcc2907f1'),
 'check':(Q/'evidence/lean-objective-container-core-01/check-result.json',10128,'9eea43fd7e1a67da9b135b84e3ad2646d5cbb42488baa3c31a8f74bcd86e4d80'),
}


def need(value,message):
    if value is not True:raise ValueError(message)


def digest(value):
    need(type(value) is str and len(value)==64 and re.fullmatch('[0-9a-f]{64}',value) is not None,'external lowercase SHA256')
    return value


def shape(row):
    need(type(row) is dict and set(row)=={'path','bytes','sha256'} and type(row['path']) is str and len(row['path'])<=4096 and
         type(row['bytes']) is int and 0<=row['bytes']<=MAX_FILE,'exact bounded descriptor')
    digest(row['sha256']);path=Path(row['path']);need(path.is_absolute() and str(path)==os.path.normpath(str(path)),'normalized absolute input')
    return path


def read_pin(path,capture=False):
    need(time.monotonic()<DEADLINE,'file-only close wall cap')
    path=Path(path);need(path.is_absolute() and path.resolve(strict=True)==path and not path.is_symlink(),'canonical regular input')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        first=os.fstat(fd);limit=MAX_JSON if capture else MAX_FILE
        need(stat.S_ISREG(first.st_mode) and 0<=first.st_size<=limit,'bounded input body')
        pieces=[];size=0;sha=hashlib.sha256()
        while block:=os.read(fd,65536):
            size+=len(block);need(size<=first.st_size and size<=limit,'body grew');sha.update(block)
            if capture:pieces.append(block)
        sig=lambda x:tuple(getattr(x,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
        need(sig(first)==sig(os.fstat(fd))==sig(path.lstat()) and size==first.st_size,'input changed during read')
        row={'path':str(path),'bytes':size,'sha256':sha.hexdigest()}
        need(path not in HELD or HELD[path]==row,'held input changed');HELD[path]=row
        return b''.join(pieces),row
    finally:os.close(fd)


def exact(row,capture=False):
    raw,actual=read_pin(shape(row),capture);need(actual==row,'same-buffer descriptor mismatch');return raw


def parse(raw):
    def pairs(items):
        result={}
        for key,value in items:need(key not in result,'duplicate JSON key');result[key]=value
        return result
    def nonfinite(value):raise ValueError('nonfinite JSON')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)
    todo=[(value,0)];count=0
    while todo:
        node,depth=todo.pop();count+=1;need(count<=300000 and depth<=32,'JSON node/depth limit')
        for child in node.values() if type(node) is dict else node if type(node) is list else ():
            need(count+len(todo)<300000,'pending JSON node bound');todo.append((child,depth+1))
    return value


def document(row):return parse(exact(row,True))


def authority_false(body):
    need(all(body[key] is False for key in ('proof_authority','execution_authority','completion_authority','planner_activation')),'four authority flags false')


def census():
    rows=[]
    need(Q.resolve(strict=True)==Q and Q.is_dir(),'fixed original Q6v1 root')
    for directory,dirs,files in os.walk(Q,followlinks=False):
        directory=Path(directory)
        for name in dirs:
            child=directory/name
            need(not child.is_symlink() and name not in ('.git','.lake','__pycache__','node_modules'),'no aliases or dependency/cache trees')
        for name in files:
            path=directory/name;need(not path.is_symlink(),'no leaf alias')
            _,row=read_pin(path);rows.append(row);need(len(rows)<=10000,'regular census cap')
    rows.sort(key=lambda row:os.fsencode(str(Path(row['path']).relative_to(Q))))
    need(len(rows)==len({row['path'] for row in rows}) and sum(row['bytes'] for row in rows)<=256*1024**2,'unique complete bounded census')
    return rows


def save(path,body):
    with path.open('xb') as stream:
        stream.write((json.dumps(body,sort_keys=True,indent=2,allow_nan=False)+'\n').encode());stream.flush();os.fsync(stream.fileno())
    fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return read_pin(path)[1]


def main():
    global DEADLINE
    need(__debug__,'optimized closure refused');DEADLINE=time.monotonic()+180
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-source-sha256',required=True)
    parser.add_argument('--source-review',required=True,type=Path)
    parser.add_argument('--expected-source-review-sha256',required=True)
    args=parser.parse_args();need(Path(__file__).resolve()==SOURCE,'fixed reviewed closure producer')
    own=read_pin(SOURCE)[1];need(own['sha256']==digest(args.expected_source_sha256),'exact externally reviewed source')
    source_review_pin=read_pin(args.source_review)[1]
    need(source_review_pin['sha256']==digest(args.expected_source_review_sha256),'external independent source-review pin')
    source_review=document(source_review_pin)
    need(source_review['status']=='passed_source_only' and source_review['findings']==[] and source_review['reviewed_source']==own,
         'independent exact closure source gate')
    docs={};pins={}
    for name,(path,size,sha) in FIXED.items():
        row={'path':str(path),'bytes':size,'sha256':sha};pins[name]=row;docs[name]=document(row)
    request,spec,profile,invocation,owned,outer,check=[docs[name] for name in FIXED]
    prepared_pin={'path':str(W/'maintenance/ranker-objective-container-core-input-review-20261005-01/review-receipt.json'),
        'bytes':2616,'sha256':'4c003a3cdaa3dda51bd07137b30e181af748dee5b29399cfa0ebbaf0beb1512b'}
    prepared=document(prepared_pin)
    need(prepared['schema']=='ranker-objective-container-core-independent-prepared-input-review@1' and
         prepared['status']=='passed_file_only' and prepared['findings']==[] and
         all(prepared['prepared_input_pins'][key]==pins[name] for key,name in
             (('request','request'),('profile','profile'),('specification','specification'))),'actual prepared input gate joins')
    authority_false(prepared)
    for row in (prepared['core_source_review'],prepared['tooling_source_review']):
        peer=document(row);need(peer['status']=='passed_source_only' and peer['findings']==[],'actual math/tooling source gates');authority_false(peer)
    exact(prepared['prepared_input_pins']['driver'])
    need(request['schema']=='terminal-ranker-objective-container-core-request@1' and request['exact_native_mode']==MODE and
         request['exact_theorem_names']==spec['theorem_names']==QUERIES and spec['mode']==invocation['mode']==owned['mode']==MODE,
         'fixed actual mode/fourquery source interfaces')
    need(spec['environment_manifest']==check['environment_manifest']==pins['profile'] and spec['source']==check['source'] and
         invocation['request']==pins['request'] and invocation['specification']==pins['specification'] and
         owned['invocation']==outer['invocation']==pins['invocation'] and owned['native_proof_checks']==[pins['check']] and
         owned['native_checker_attempts']==[{'specification':pins['specification'],'native_invocations_observed':1}],
         'actual captured/native/phase/invocation pin joins')
    source=exact(spec['source'],True);original=Q/'math/ObjectiveContainerCore.lean'
    need(source==read_pin(original,True)[0] and spec['source']['bytes']==6368 and
         spec['source']['sha256']=='9f6f36352ec1b45bb8d797cae03683455fcd03d1c3e7663a1991378baeb8da14','original reviewed source exactly retained')
    augmented=exact({key:check['augmented_source'][key] for key in ('path','bytes','sha256')},True)
    need(augmented==source+b'\n'+b'\n'.join(('#print axioms _root_.'+name).encode() for name in QUERIES)+b'\n','actual augmented literal query source')
    need(check['status']=='inconclusive' and check['matches_expectation'] is False and
         type(check['native_invocations']) is type(check['native_lean_invocations']) is int and
         check['native_invocations']==check['native_lean_invocations']==1 and check['native_lean_returncode']==check['returncode']==1 and
         check['compiled_artifacts']==check['retained_chunk_artifacts']==[] and
         check['retention_manifest_body']['status']=='native_nonzero','failed native with zero compiled proof objects')
    retained=document({key:check['retention_manifest'][key] for key in ('path','bytes','sha256')})
    need(retained==check['retention_manifest_body'] and retained['native_lean_returncode']==1,'complete retained nonzero diagnostic manifest')
    need(check['native_bounds']=={'cpu_seconds':20,'max_input_bytes':262144,'max_output_bytes':65536,'max_workspace_bytes':16777216,'timeout_seconds':20} and
         check['workspace_cleaned'] is True and check['native_elapsed_seconds']<=20 and
         check['allowed_standard_axioms']==['Classical.choice','Quot.sound','propext'],'fixed bounds and cleanup')
    reports=check['theorem_axiom_output']
    need([row['theorem'] for row in reports]==QUERIES and all(type(row['report_occurrences']) is int and row['report_occurrences']==2 and
         set(row['axioms'])<={'Classical.choice','Quot.sound','propext'} for row in reports),'four stdout reports are evidence only, never admission')
    need(owned['status']=='failed' and outer['returncode']==1 and owned['cleanup_errors']==outer['cleanup_errors']==[] and
         owned['root_release_returned'] is True and owned['all_strict_old_and_protected_live_inputs_unchanged'] is True and
         owned['strict_old_input_count']==2391 and owned['protected_live_source_count']==4 and
         owned['final_resource_state']['active_lease_count']==owned['final_resource_state']['waiting_request_count']==0,
         'actual failed phase is guarded and drained')
    wanted=request['original_checkout_guards']
    need(owned['original_checkout_guards_before']==owned['original_checkout_guards_after']==
         outer['original_checkout_guards_before']==outer['original_checkout_guards_after']==wanted,'original HEAD/index receipt joins')
    for body in (request,owned,check):authority_false(body)
    for name in ('native_preparation_calls','gradient_evaluations','optimizer_updates','fit_calls','autoencoder_fit_calls','test_cases',
                 'metadata_hydration_calls','source_function_executions','dependency_setup_calls'):
        need(type(owned[name]) is int and owned[name]==0,'zero forbidden call counter')
    guards=request['strict_old_inputs']+request['protected_live_sources']
    need(len(request['strict_old_inputs'])==2391 and len(request['protected_live_sources'])==4 and
         len({row['path'] for row in guards})==2395,'complete unique strict/live guard descriptors')
    for row in guards:exact(row)
    for role in wanted:exact(wanted[role]['index'])
    for row in invocation['inputs']:exact(row)
    review_path=Q/'failed-review-01.json';seal_path=Q/'file-only-seal-01.json'
    need(not review_path.exists() and not seal_path.exists(),'only fresh exclusive append-only outputs')
    initial=census();need(len(initial)==28 and sum(row['bytes'] for row in initial)==10850381,'complete immutable original28 census')
    for path,row in list(HELD.items()):exact(row)
    need(census()==initial,'quiet original census before append')
    review={'schema':'ranker-objective-container-core-failed-v1-closure@1','status':'closed_failed_native_attempt_without_qualification',
        'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producer':own,'source_review':source_review_pin,
        'prepared_input_review':prepared_pin,'native_attempts':1,'qualified_native_checks':0,'qualified_theorem_queries':0,
        'candidate_native_qualified':False,'captured_source':spec['source'],'specification':pins['specification'],'profile':pins['profile'],
        'request':pins['request'],'invocation':pins['invocation'],'owned_closed':pins['owned'],'outer_closed':pins['outer'],'check_result':pins['check'],
        'strict_input_count':2391,'protected_live_source_count':4,'guards_same':True,'leases_drained':True,
        'original_checkout_guards':wanted,'prior_regular_file_count':28,'prior_regular_file_bytes':10850381,
        'retained_stdout_query_reports':4,'reports_per_query':2,'stdout_reports_are_native_qualification':False,
        'complete_native_objects_retained':0,'reason':'Lean returned 1 at the redundant induction generalization; no complete compiled module exists.',
        'independent_full_semantic_native_review_remains_separate':True,
        'native_model_test_metadata_preparation_or_target_import_jobs_in_this_closure':0,
        'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
        'all32_governing_RPI_exits':'OPEN','full_task_satisfaction':'unknown','official_benchmark_score':None}
    review_pin=save(review_path,review)
    rows=census();expected=sorted([*initial,review_pin],key=lambda row:os.fsencode(str(Path(row['path']).relative_to(Q))))
    need(rows==expected and len(rows)==29,'only the authorized review was appended')
    for path,row in list(HELD.items()):exact(row)
    need(census()==rows,'complete quiet census before seal save')
    seal={'schema':'ranker-objective-container-core-failed-v1-file-only-seal@1','scope_root':str(Q),'review':review_pin,
        'files':rows,'regular_file_count':len(rows),'regular_file_bytes':sum(row['bytes'] for row in rows),
        'file_inventory_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest(),
        'fixture_symlinks':[],'excluded_dependency_roots':[],'seal_self_excluded_from_files':True,
        'qualified_native_checks':0,'qualified_theorem_queries':0,'native_attempts_retained':1,
        'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
        'full_task_satisfaction':'unknown','all32_governing_RPI_exits':'OPEN','official_benchmark_score':None}
    seal_pin=save(seal_path,seal)
    need(census()==sorted([*rows,seal_pin],key=lambda row:os.fsencode(str(Path(row['path']).relative_to(Q)))),'only review and seal append complete final census')
    print(json.dumps({'status':review['status'],'review':review_pin,'seal':seal_pin,'sealed_regular_files':29,'sealed_regular_bytes':seal['regular_file_bytes']}))


if __name__=='__main__':main()
