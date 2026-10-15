"""Root-executed file-only closure for four qualified generic container queries.

Consumes an externally pinned actual-input plan and actual successful native
objects. The only loaded source is the previously source-reviewed inert driver
and its file-validation definitions. No owned/outer/native callback is called.
No project, target, model, test, metadata, codec or publication job is run.
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
Q=W/'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-02'
V1=Q.with_name('ranker-objective-container-core-candidate-20261005-01')
SOURCE=W/'maintenance/ranker-objective-container-core-v2-root-review-20261005-02/close_qualification_01.py'
MODE='lean-objective-container-core-02'
MAX_JSON=32*1024**2
MAX_FILE=256*1024**2
HELD={}
DEADLINE=None
QUERIES=['RankerObjectiveContainerIR.map_exact_ofFn_success','RankerObjectiveContainerIR.mean_exact_ofFn_success',
         'RankerObjectiveContainerIR.mean_exact_empty_refuses','RankerObjectiveContainerIR.indexed_zip_fsum_ofFn_eq']
DRIVER={'path':str(Q/'run_container_core_controls_01.py'),'bytes':26231,
        'sha256':'53571082744f4c1c076456d70e83e6aa741ae13881c736d1859a3d738405754a'}
MATH_GATE={'path':str(W/'maintenance/ranker-objective-container-core-patch-source-review-20261005-02/review-receipt.json'),
           'bytes':5852,'sha256':'1cdfea8f580bc113a190a56720eef2b0baa335b7b5f59491aaaa7493fcdd8359'}
TOOL_GATE={'path':str(W/'maintenance/ranker-objective-container-core-tooling-source-review-20261005-02/review-receipt.json'),
           'bytes':9173,'sha256':'bb1f7df2dd76f37349480094cdf3181d93e53b5886a263bca4fc3bc3b0f57b4e'}
PREPARED_SOURCE_GATE={'path':str(W/'maintenance/ranker-objective-container-core-prepared-input-source-review-20261005-02/review-receipt.json'),
    'bytes':3827,'sha256':'b85b9f1087eb585d53d24dc5bb5d777426932f1953986d727722e5939127e3a5'}
PREPARED_PRODUCER={'path':str(W/'maintenance/ranker-objective-container-core-input-review-20261005-02/review_inputs_02.py'),
    'bytes':11732,'sha256':'50adfa733b6b12d54c9c4d1f83c4e079782b298b4af047a697b750395595e47c'}
V1_SEAL={'path':str(V1/'file-only-seal-01.json'),'bytes':9646,
         'sha256':'3af962a5e6e6de238fe5c553224890466e3222e2b1a241f9484e2cba7fdb61d2'}
V1_REVIEW={'path':str(V1/'failed-review-01.json'),'bytes':6392,
           'sha256':'e896db907881e737075863e68ef90c7d09310a0b5529f99431b508fd64cc6170'}

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
    need(Q.resolve(strict=True)==Q and Q.is_dir(),'fixed actual Q6v2 root')
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


def positive_object_join(check):
    need(check['status']=='passed' and check['matches_expectation'] is True and check['expected_success'] is True
         and type(check['native_invocations']) is type(check['native_lean_invocations']) is int
         and check['native_invocations']==check['native_lean_invocations']==1
         and check['native_lean_returncode']==check['returncode']==0
         and check['axiom_report_error'] is check['post_call_binding_error'] is check['reconstruction_validation_error'] is None
         and check['reconstruction_validation']['status']=='passed'
         and check['workspace_cleaned'] is True and check['output_truncated'] is False
         and check['timed_out'] is False and check['resource_exhausted'] is False
         and check['workspace_limit_exceeded'] is False and check['cancelled'] is False,
         'actual successful native object qualification required')
    need(check['artifact_anomalies']==[]
         and check['allowed_standard_axioms']==['Classical.choice','Quot.sound','propext'],
         'unchanged exact standard-axiom admission and clean artifact census required')
    need(check['native_bounds']=={'cpu_seconds':20,'max_input_bytes':262144,'max_output_bytes':65536,
         'max_workspace_bytes':16777216,'timeout_seconds':20} and check['native_elapsed_seconds']<=20,
         'unchanged actual native bounds required')
    queries=check['theorem_axiom_output']
    need([row['theorem'] for row in queries]==QUERIES
         and all(type(row['report_occurrences']) is int and row['report_occurrences']==2
                 and set(row['axioms'])<={'Classical.choice','Quot.sound','propext'} for row in queries),
         'four exact actual standard-axiom query reports required')
    objects=check['compiled_artifacts'];chunks=check['retained_chunk_artifacts']
    need(type(objects) is list and len(objects)==1 and objects[0]['complete'] is True
         and Path(objects[0]['path']).name=='ObjectiveContainerCore.olean', 'one complete native module object required')
    whole={key:objects[0][key] for key in ('path','bytes','sha256')};exact(whole)
    retention=check['retention_manifest']
    need(retention['complete'] is True, 'complete retained manifest required')
    manifest_pin={key:retention[key] for key in ('path','bytes','sha256')}
    manifest=document(manifest_pin)
    need(manifest==check['retention_manifest_body'] and manifest['schema']=='bounded_lean_chunks@1'
         and manifest['status']=='complete' and manifest['native_lean_returncode']==0
         and len(manifest['objects'])==1 and len(chunks)==len(manifest['chunks'])<=61,
         'complete actual ordered object/chunk manifest required')
    obj=manifest['objects'][0]
    need(obj['name']=='ObjectiveContainerCore.olean' and obj['bytes']==whole['bytes']
         and obj['sha256']==whole['sha256'] and manifest['aggregate_raw_object_bytes']==whole['bytes']<=3997696,
         'native whole object and unchanged aggregate bound required')
    names=[];pins=[];joined=hashlib.sha256();total=0
    for actual,declared in zip(chunks,manifest['chunks']):
        need(actual['complete'] is True and Path(actual['path']).name==declared['name']
             and 0<actual['bytes']==declared['bytes']<=65536 and actual['sha256']==declared['sha256'],
             'complete bounded native chunk descriptor differs')
        row={key:actual[key] for key in ('path','bytes','sha256')};raw=exact(row,True)
        names.append(declared['name']);pins.append(row);joined.update(raw);total+=len(raw)
    need(len(names)==len(set(names)) and obj['chunks']==names
         and total==whole['bytes'] and joined.hexdigest()==whole['sha256'],
         'ordered chunks must reconstruct the actual retained whole object')
    return whole,manifest_pin,pins


def main():
    global DEADLINE
    need(__debug__,'optimized file-only qualification closure refused');DEADLINE=time.monotonic()+180
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path)
    parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--expected-source-sha256',required=True)
    args=parser.parse_args();need(Path(__file__).resolve()==SOURCE,'fixed external qualification closer source')
    own=read_pin(SOURCE)[1];need(own['sha256']==digest(args.expected_source_sha256),'reviewed closer source differs')
    plan_pin=read_pin(args.plan)[1];need(plan_pin['sha256']==digest(args.plan_sha256),'externally frozen actual closure plan differs')
    plan=document(plan_pin)
    names={'request','specification','profile','invocation','owned_closed','outer_closed','check_result',
           'prepared_input_review','math_source_review','tooling_source_review','closure_source_review',
           'prior_failed_seal','prior_failed_review'}
    need(set(plan)==names|{'schema','scope_root','mode'}
         and plan['schema']=='ranker-objective-container-core-qualified-closure-plan@1'
         and plan['scope_root']==str(Q) and plan['mode']==MODE, 'closed exact four-query actual-input plan required')
    need(plan['math_source_review']==MATH_GATE and plan['tooling_source_review']==TOOL_GATE
         and plan['prior_failed_seal']==V1_SEAL and plan['prior_failed_review']==V1_REVIEW,
         'actual reviewed candidate/tooling and full failed-v1 history pins required')
    docs={name:document(plan[name]) for name in names}
    peer=docs['closure_source_review']
    need(peer['status']=='passed_source_only' and peer['findings']==[] and peer['reviewed_source']==own,
         'independent exact closer source gate required')
    authority_false(peer)
    for key in ('math_source_review','tooling_source_review'):
        need(docs[key]['status']=='passed_source_only' and docs[key]['findings']==[], 'actual source gate must remain passed')
        authority_false(docs[key])
    need(docs['prior_failed_review']['status']=='closed_failed_native_attempt_without_qualification'
         and docs['prior_failed_review']['qualified_native_checks']==docs['prior_failed_review']['qualified_theorem_queries']==0
         and docs['prior_failed_review']['native_attempts']==1, 'failed first attempt must never be promoted')
    namespace={'__file__':DRIVER['path'],'__name__':'held_v2_pass_closure_file_validators'}
    exec(compile(exact(DRIVER,True),DRIVER['path'],'exec'),namespace)
    f=namespace['files']()
    request,spec,profile,invocation,owned,outer,check=[docs[name] for name in
        ('request','specification','profile','invocation','owned_closed','outer_closed','check_result')]
    namespace['validate_request'](f,request)
    need(namespace['validate_specification'](f,plan['specification'])==spec, 'same actual prepared specification required')
    need(spec['environment_manifest']==plan['profile'] and profile['external_file_count']==len(profile['files'])==20119
         and spec['independent_core_source_review']==MATH_GATE
         and request['prior_failed_container_seal']==V1_SEAL and request['prior_failed_container_review']==V1_REVIEW,
         'actual prepared v2 environment and complete failed-v1 history joins required')
    prepared=docs['prepared_input_review']
    need(prepared['schema']=='ranker-objective-container-core-independent-prepared-input-review@2'
         and prepared['status']=='passed_file_only' and prepared['findings']==[]
         and all(prepared['prepared_input_pins'][key]==plan[key] for key in ('request','specification','profile'))
         and prepared['prepared_input_pins']['driver']==DRIVER
         and prepared['core_source_review']==MATH_GATE and prepared['tooling_source_review']==TOOL_GATE,
         'independent actual prepared inputs must join all actual source and runtime roles')
    authority_false(prepared)
    prepared_peer=document(PREPARED_SOURCE_GATE)
    exact(PREPARED_PRODUCER)
    need(prepared['producer']==PREPARED_PRODUCER and prepared_peer['reviewed_source']==PREPARED_PRODUCER
         and prepared_peer['status']=='passed_source_only' and prepared_peer['findings']==[],
         'exact prepared reviewer producer and independent source gate required')
    authority_false(prepared_peer)
    need(invocation['schema']=='ranker-objective-container-core-frozen-invocation@1' and invocation['mode']==MODE
         and invocation['request']==plan['request'] and invocation['specification']==plan['specification']
         and invocation['independent_core_source_review']==MATH_GATE
         and owned['invocation']==outer['invocation']==plan['invocation']
         and owned['native_proof_checks']==[plan['check_result']]
         and owned['native_checker_attempts']==[{'specification':plan['specification'],'native_invocations_observed':1}]
         and (invocation['driver']['bytes'],invocation['driver']['sha256'])==(DRIVER['bytes'],DRIVER['sha256'])
         and invocation['driver']['path']==str(Q/('captured-driver-'+MODE+'.py')), 'actual owned/native/outer and driver joins required')
    for row in invocation['inputs']:exact(row)
    need(check['environment_manifest']==plan['profile'] and check['source']==spec['source']
         and check['retention_helper']==spec['retention_helper'] and check['python_executable']==spec['python_executable']
         and check['environment_file_count']==20119 and check['source_direct_imports']==['ObjectiveScalarIR'],
         'actual native source, loader profile and bounded wrapper inputs must join')
    source=exact(spec['source'],True)
    need(source==read_pin(Q/'math/ObjectiveContainerCore.lean',True)[0]
         and spec['source']['bytes']==6340 and spec['source']['sha256']=='9c3761eb4b778ed04349ae29ef84a4b93f1da36c0f8ef9b59e806805ff10c9b3',
         'exact independently reviewed patched math source required')
    augmented=exact({key:check['augmented_source'][key] for key in ('path','bytes','sha256')},True)
    need(augmented==source+b'\n'+b'\n'.join(('#print axioms _root_.'+name).encode() for name in QUERIES)+b'\n',
         'actual augmented source must contain only the exact four query literals')
    whole,manifest,chunks=positive_object_join(check)
    need(owned['mode']==MODE and owned['status']=='passed' and outer['returncode']==0
         and owned['cleanup_errors']==outer['cleanup_errors']==[] and owned['primary_error'] is outer['primary_error'] is None
         and owned['root_release_returned'] is True and owned['all_strict_old_and_protected_live_inputs_unchanged'] is True
         and owned['strict_old_input_count']==2421 and owned['protected_live_source_count']==4
         and owned['final_resource_state']['active_lease_count']==owned['final_resource_state']['waiting_request_count']==0,
         'actual accepted owned native phase must be fully guarded and drained')
    need(check['actual_root_lease']==owned['root_lease'] and invocation['outer_timeout_seconds']==120
         and owned['root_lease']['cpu_slots']==1 and owned['root_lease']['memory_mb']==2048
         and owned['root_lease']['child_process_slots']==4, 'actual unchanged parent-owned native root lease required')
    wanted=request['original_checkout_guards']
    need(owned['original_checkout_guards_before']==owned['original_checkout_guards_after']==
         outer['original_checkout_guards_before']==outer['original_checkout_guards_after']==wanted,
         'actual original checkout HEAD/index receipt joins required')
    for body in (request,owned,check):authority_false(body)
    for name in ('native_preparation_calls','gradient_evaluations','optimizer_updates','fit_calls','autoencoder_fit_calls','test_cases',
                 'metadata_hydration_calls','source_function_executions','dependency_setup_calls'):
        need(type(owned[name]) is int and owned[name]==0, 'zero forbidden native/test/model/source/metadata call counter required')
    h=namespace['sealed_helpers'](f)
    need(namespace['verify'](h,f,request)==wanted, 'all inherited strict/live and original checkout guards required')
    for row in profile['files']:f['exact'](row)
    for key in ('prior_failed_seal','prior_failed_review'):authority_false(docs[key])
    review_path=Q/'qualified-review-01.json';seal_path=Q/'file-only-seal-01.json'
    need(not review_path.exists() and not seal_path.exists(), 'exclusive fresh qualification review/seal outputs required')
    initial=census()
    need(len(initial)==33 and sum(row['bytes'] for row in initial)==11281368,
         'complete actual quiet 33-file native scope denominator differs')
    f['verify_held']()
    for row in list(HELD.values()):exact(row)
    need(namespace['verify'](h,f,request)==wanted and census()==initial, 'all actual bodies and complete census quiet before append')
    review={'schema':'ranker-objective-container-core-qualified-review@1','status':'passed',
        'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producer':own,'source_review':plan['closure_source_review'],
        'closure_plan':plan_pin,'scope_root':str(Q),'exact_native_mode':MODE,'qualified_theorem_queries':4,'queried_theorems':QUERIES,
        'qualified_native_checks':1,'actual_native_attempts_in_this_scope':1,'prior_failed_native_attempts':1,'prior_failed_qualified_queries':0,
        'prior_failed_seal':V1_SEAL,'prior_failed_review':V1_REVIEW,'prepared_input_review':plan['prepared_input_review'],
        'prepared_input_source_review':PREPARED_SOURCE_GATE,'prepared_input_producer':PREPARED_PRODUCER,
        'math_source_review':MATH_GATE,'tooling_source_review':TOOL_GATE,'request':plan['request'],'specification':plan['specification'],
        'profile':plan['profile'],'invocation':plan['invocation'],'owned_closed':plan['owned_closed'],'outer_closed':plan['outer_closed'],
        'check_result':plan['check_result'],'whole_native_object':whole,'retention_manifest':manifest,'ordered_native_chunks':chunks,
        'whole_object_and_ordered_chunks_reconstructed':True,'environment_files_rehashed':20119,
        'strict_input_count':2421,'protected_live_source_count':4,'guards_same':True,'leases_drained':True,'original_checkout_guards':wanted,
        'proof_scope':'Four generic ordered map/index/zip exact-real sum and partial-mean primitive bridges only.',
        'original_candidate_docs_remain_historical_uncompiled_source_gate_inputs':True,
        'closure_native_test_model_metadata_or_codec_jobs':0,'new_metadata_rows':0,'new_cache_entries':0,
        'full_source_runtime_equivalence':False,'objective_source_equivalence_proved':False,'gradient_source_equivalence_proved':False,
        'native_Float_optimizer_convergence_proved':False,'binary64_error_bound_proved':False,'global_optimizer_convergence':False,
        'global_autoencoder_convergence_proved':False,'all32_governing_RPI_exits':'OPEN','full_task_satisfaction':'unknown',
        'official_benchmark_score':None,'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False}
    review_pin=save(review_path,review)
    rows=census();expected=sorted([*initial,review_pin],key=lambda row:os.fsencode(str(Path(row['path']).relative_to(Q))))
    need(rows==expected, 'only the approved qualified review may be appended before seal')
    f['verify_held']()
    for row in list(HELD.values()):exact(row)
    need(namespace['verify'](h,f,request)==wanted and census()==rows, 'complete census and all guards quiet before seal')
    seal={'schema':'ranker-objective-container-core-qualified-file-only-seal@1','scope_root':str(Q),'review':review_pin,
        'files':rows,'regular_file_count':len(rows),'regular_file_bytes':sum(row['bytes'] for row in rows),
        'file_inventory_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest(),
        'fixture_symlinks':[],'excluded_dependency_roots':[],'seal_self_excluded_from_files':True,
        'qualified_native_checks':1,'qualified_theorem_queries':4,'prior_failed_seal':V1_SEAL,
        'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
        'full_task_satisfaction':'unknown','all32_governing_RPI_exits':'OPEN','official_benchmark_score':None}
    seal_pin=save(seal_path,seal)
    need(census()==sorted([*rows,seal_pin],key=lambda row:os.fsencode(str(Path(row['path']).relative_to(Q)))), 'only review and seal appended')
    print(json.dumps({'status':'passed','review':review_pin,'seal':seal_pin,'qualified_native_checks':1,'qualified_theorem_queries':4,
        'prior_failed_qualified_queries':0,'sealed_regular_files':len(rows),'sealed_regular_bytes':seal['regular_file_bytes']}))


if __name__=='__main__':main()
