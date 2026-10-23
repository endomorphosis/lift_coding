"""Independent file-only review of one actual Q6v1 native attempt.

Inert stdlib source; run only after the root reviews its exact source SHA256.
This never imports targets or invokes Git, Lean, tests, models or metadata jobs.
Printed axiom reports never qualify a nonzero/inconclusive native attempt.
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
OUT=W/'maintenance/ranker-objective-container-core-semantic-native-review-20261005-01'
MODE='lean-objective-container-core-01'
CAP=32*1024**2
STREAM_CAP=256*1024**2
HELD={}
DEADLINE=None
QUERIES=['RankerObjectiveContainerIR.map_exact_ofFn_success','RankerObjectiveContainerIR.mean_exact_ofFn_success',
         'RankerObjectiveContainerIR.mean_exact_empty_refuses','RankerObjectiveContainerIR.indexed_zip_fsum_ofFn_eq']
AXIOMS=['Classical.choice','Quot.sound','propext']
AUTHORITY=('proof_authority','execution_authority','completion_authority','planner_activation')


def need(value,message):
    if value is not True:raise ValueError(message)


def integer(value,minimum,maximum,label):
    need(type(value) is int and minimum<=value<=maximum,'exact integer '+label);return value


def sha(value):
    need(type(value) is str and len(value)==64 and re.fullmatch('[0-9a-f]{64}',value) is not None,'exact lowercase SHA256');return value


def bare(row):
    need(type(row) is dict and {'path','bytes','sha256'}<=set(row),'descriptor fields')
    result={key:row[key] for key in ('path','bytes','sha256')};shape(result);return result


def shape(row):
    need(type(row) is dict and set(row)=={'path','bytes','sha256'} and type(row['path']) is str and len(row['path'])<=4096,'exact descriptor')
    integer(row['bytes'],0,STREAM_CAP,'file bytes');sha(row['sha256'])
    path=Path(row['path']);need(path.is_absolute() and str(path)==os.path.normpath(str(path)),'normalized absolute path');return path


def read(path,capture=False):
    need(time.monotonic()<DEADLINE,'file-only review180s deadline')
    path=Path(path);need(path.is_absolute() and path.resolve(strict=True)==path and not path.is_symlink(),'canonical regular file')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        first=os.fstat(fd);maximum=CAP if capture else STREAM_CAP
        need(stat.S_ISREG(first.st_mode) and 0<=first.st_size<=maximum,'bounded body')
        pieces=[];total=0;h=hashlib.sha256()
        while block:=os.read(fd,65536):
            total+=len(block);need(total<=first.st_size and total<=maximum,'input grew during read');h.update(block)
            if capture:pieces.append(block)
        sig=lambda value:tuple(getattr(value,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
        need(sig(first)==sig(os.fstat(fd))==sig(path.lstat()) and total==first.st_size,'stable FD/path signature')
        row={'path':str(path),'bytes':total,'sha256':h.hexdigest()}
        need(path not in HELD or HELD[path]==row,'repeated input changed');HELD[path]=row
        return b''.join(pieces),row
    finally:os.close(fd)


def exact(row,capture=False):
    raw,actual=read(shape(row),capture);need(actual==row,'same-buffer exact pin');return raw


def parse(raw):
    def pairs(items):
        result={}
        for key,value in items:need(key not in result,'duplicate JSON key');result[key]=value
        return result
    def nonfinite(value):raise ValueError('nonfinite JSON')
    result=json.loads(raw,object_pairs_hook=pairs,parse_constant=nonfinite)
    todo=[(result,0)];count=0
    while todo:
        value,depth=todo.pop();count+=1;need(count<=300000 and depth<=32,'JSON nodes/depth bound')
        children=value.values() if type(value) is dict else value if type(value) is list else ()
        for child in children:
            need(count+len(todo)<300000,'pending JSON node bound');todo.append((child,depth+1))
    return result


def document(row):return parse(exact(row,True))


def false_authority(body):
    need(all(body[key] is False for key in AUTHORITY),'four authority fields false')


def reports(check,source):
    need(check['allowed_standard_axioms']==AXIOMS and check['axiom_report_error'] is None,'genuine Std-only report parser')
    rows=check['theorem_axiom_output']
    need(type(rows) is list and [row['theorem'] for row in rows]==QUERIES,'exact ordered four queried theorem names')
    for row in rows:
        need(type(row['axioms']) is list and len(row['axioms'])==len(set(row['axioms'])) and set(row['axioms'])<=set(AXIOMS),'onlyStd report axioms')
        integer(row['report_occurrences'],2,2,'query occurrence count')
    need(type(check['stdout']) is str and type(check['stderr']) is str and
         len(check['stdout'].encode())+len(check['stderr'].encode())<=65536,'bounded complete native output strings')
    observed=[(name,[] if terms=='' else [term.strip() for term in terms.split(',')]) for name,terms in
              re.findall(r"'([^']+)' (?:depends on axioms:\s*\[([^]]*)\]|does not depend on any axioms)",check['stdout'])]
    expected=[(row['theorem'],row['axioms']) for row in rows]
    need(observed==expected+expected,'raw stdout exact full two report populations')
    source_queries=re.findall(rb'^#print axioms ([^\n]+)$',source,re.M)
    need(source_queries==[name.removeprefix('RankerObjectiveContainerIR.').encode() for name in QUERIES],'source literal query population')
    return rows


def retention(check,require_complete):
    row=bare(check['retention_manifest']);manifest=document(row)
    need(manifest==check['retention_manifest_body'] and manifest['schema']=='bounded_lean_chunks@1' and
         manifest['retention_profile_sha256']==check['retention_profile_sha256'] and
         manifest['native_lean_invocations']==check['native_lean_invocations'] and
         manifest['native_lean_returncode']==check['native_lean_returncode'],'retention manifest/native/profile joins')
    if not require_complete:
        need(check['compiled_artifacts']==check['retained_chunk_artifacts']==[] and
             manifest['status']=='native_nonzero' and check['native_lean_returncode']!=0 and
             check['reconstruction_validation'] is None,'retained nonzero native attempt has no complete module')
        return {'manifest':row,'complete_objects':0,'complete_object_bytes':0,'chunks':0,'module_qualified':False}
    need(manifest['status']=='complete' and check['reconstruction_validation_error'] is None and
         check['reconstruction_validation']['status']=='passed','full reconstruction accepted')
    objects=manifest['objects'];chunks=manifest['chunks'];artifacts=check['compiled_artifacts']
    need(type(objects) is list and len(objects)==len(artifacts)==1 and type(chunks) is list,'one complete owned module')
    integer(len(chunks),1,61,'retention chunk count')
    directory=Path(row['path']).parent;by_name={};chunk_pins=[]
    for index,chunk in enumerate(chunks):
        name='LeanProofChunk'+str(index).zfill(3)+'.bin'
        need(chunk['name']==name,'fixed complete chunk order');integer(chunk['bytes'],1,65536,'chunk bytes');sha(chunk['sha256'])
        pin={'path':str(directory/name),'bytes':chunk['bytes'],'sha256':chunk['sha256']};body=exact(pin,True)
        need({**pin,'complete':True} in check['retained_chunk_artifacts'],'complete chunk descriptor present')
        by_name[name]=body;chunk_pins.append(pin)
    need(len(check['retained_chunk_artifacts'])==len(chunks) and
         sorted(path.name for path in directory.glob('LeanProofChunk*.bin'))==sorted(by_name),'no omitted/additional actual chunks')
    obj=objects[0];artifact=artifacts[0]
    need(obj['name']=='ObjectiveContainerCore.olean' and obj['chunks']==list(by_name) and
         artifact['path']==str(directory/obj['name']) and artifact['complete'] is True and
         artifact['retention_format']=='bounded_lean_chunks@1','one actual complete module and chunk order')
    integer(obj['bytes'],1,3997696,'complete module bytes');sha(obj['sha256'])
    body=b''.join(by_name[name] for name in obj['chunks']);actual=bare(artifact)
    need(len(body)==obj['bytes']==actual['bytes']==manifest['aggregate_raw_object_bytes'] and
         hashlib.sha256(body).hexdigest()==obj['sha256']==actual['sha256'] and exact(actual,True)==body,
         'whole actual module equals all ordered full retained chunks')
    return {'manifest':row,'artifact':actual,'complete_objects':1,'complete_object_bytes':len(body),'chunks':len(chunks),
            'chunk_pins':chunk_pins,'full_raw_equals_ordered_chunks':True,'module_qualified':True}


def imports(spec,profile):
    expected_names=['ObjectiveScalarIR','RealStableFactor','TypedNumericSlice']
    rows=spec['qualified_imports'];need([row['module'] for row in rows]==expected_names,'exact three qualified historical imports')
    files={row['path']:row for row in profile['files']};result=[]
    for row in rows:
        check=document(row['qualification'])
        need(check['status']=='passed' and check['matches_expectation'] is True and check['native_lean_returncode']==0 and
             check['source']==row['source'] and check['augmented_source']==row['augmented_source'],'actual historical accepted import joins')
        compiled=[bare(item) for item in check['compiled_artifacts']]
        need(row['compiled']==compiled and row['historical_complete_object_join_verified'] is True,'whole historical object descriptors')
        manifest=document(bare(check['retention_manifest']));need(manifest==check['retention_manifest_body'] and manifest['status']=='complete','complete historical retention')
        need(row['retention_manifest']==bare(check['retention_manifest']) and row['retained_chunks']==[bare(item) for item in check['retained_chunk_artifacts']],
             'historical retention/chunk descriptor joins')
        directory=Path(row['retention_manifest']['path']).parent;chunks={}
        for index,chunk in enumerate(manifest['chunks']):
            need(chunk['name']=='LeanProofChunk'+str(index).zfill(3)+'.bin','ordered historical chunks')
            integer(chunk['bytes'],1,65536,'historical chunk bytes')
            chunks[chunk['name']]=exact({'path':str(directory/chunk['name']),'bytes':chunk['bytes'],'sha256':chunk['sha256']},True)
        need(len(manifest['objects'])==len(compiled)==1,'one actual complete historical import object')
        obj=manifest['objects'][0];need(obj['chunks']==list(chunks),'full historical chunk concatenation order')
        body=b''.join(chunks[name] for name in obj['chunks']);pin=compiled[0]
        need(len(body)==obj['bytes']==pin['bytes'] and hashlib.sha256(body).hexdigest()==obj['sha256']==pin['sha256'] and
             exact(pin,True)==body and all(files.get(item['path'])==item for item in [row['augmented_source'],*compiled]),'whole historical object body/profile join')
        registry=[item for item in profile['source_import_modules'] if item['module']==row['module']]
        need(len(registry)==1 and registry[0]['source']==row['augmented_source'] and registry[0]['compiled']==compiled,
             'frozen qualified import registry exact source/compiled join')
        result.append({'module':row['module'],'qualification':row['qualification'],'compiled':compiled,'chunks':len(chunks),
                       'whole_raw_equals_complete_ordered_chunks':True})
    return result


def main():
    global DEADLINE
    need(__debug__,'optimized review refused');DEADLINE=time.monotonic()+180
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path);parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--expected-source-sha256',required=True);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();need(Path(__file__).resolve()==OUT/'review_semantic_native_01.py' and
         args.output==OUT/'semantic-native-review-01.json' and not args.output.exists(),'fixed fresh external review output')
    own=read(Path(__file__).resolve())[1];need(own['sha256']==sha(args.expected_source_sha256),'root-reviewed actual reviewer source')
    planraw,planpin=read(args.plan,True);need(planpin['sha256']==sha(args.plan_sha256) and len(planraw)<=1024**2,'external frozen review plan')
    plan=parse(planraw)
    keys={'schema','mode','math_source','math_source_review','tooling_source_review','prepared_input_review',
          'request','specification','invocation','owned','outer','check','expected_native_status'}
    need(type(plan) is dict and set(plan)==keys and plan['schema']=='ranker-objective-container-core-semantic-native-review-plan@1' and
         plan['mode']==MODE and plan['expected_native_status'] in ('passed','inconclusive'),'closed exact actual native review plan')
    fixed={'request':Q/'preparation/request-v3.json','specification':Q/'preparation'/ (MODE+'-check-specification.json'),
           'invocation':Q/'preparation'/ (MODE+'-invocation.json'),'owned':Q/'evidence'/MODE/'closed.json',
           'outer':Q/'evidence'/(MODE+'-closed.json'),'check':Q/'evidence'/MODE/'check-result.json',
           'math_source':Q/'math/ObjectiveContainerCore.lean'}
    for key,path in fixed.items():need(plan[key]['path']==str(path),'fixed actual source/phase path')
    docs={name:document(plan[name]) for name in keys-{'schema','mode','expected_native_status','math_source'}}
    math_review,tool_review,prepared=[docs[key] for key in ('math_source_review','tooling_source_review','prepared_input_review')]
    need(math_review['schema']=='ranker-objective-container-core-independent-source-review@1' and
         math_review['status']=='passed_source_only' and math_review['findings']==[] and
         math_review['candidate_pins']['math/ObjectiveContainerCore.lean']==plan['math_source'] and math_review['reviewed_query_names']==QUERIES,
         'actual independently reviewed math source/query gate')
    need(tool_review['schema']=='ranker-objective-container-core-independent-tooling-source-review@1' and
         tool_review['status']=='passed_source_only' and tool_review['findings']==[] and
         tool_review['independent_math_source_review']==plan['math_source_review'],'actual tooling source gate')
    need(prepared['schema']=='ranker-objective-container-core-independent-prepared-input-review@1' and
         prepared['status']=='passed_file_only' and prepared['findings']==[] and prepared['core_source_review']==plan['math_source_review'] and
         prepared['tooling_source_review']==plan['tooling_source_review'],'actual prepared input gate joins')
    request,spec,invocation,owned,outer,check=[docs[key] for key in ('request','specification','invocation','owned','outer','check')]
    need(request['schema']=='terminal-ranker-objective-container-core-request@1' and request['exact_native_mode']==MODE and
         spec['schema']=='ranker-objective-container-core-native-check-specification@1' and spec['mode']==MODE and
         request['exact_theorem_names']==spec['theorem_names']==QUERIES,'one exact four-query native-only interface')
    need(invocation['schema']=='ranker-objective-container-core-frozen-invocation@1' and invocation['mode']==MODE and
         invocation['request']==plan['request'] and invocation['specification']==plan['specification'] and
         invocation['independent_core_source_review']==plan['math_source_review'] and invocation['outer_timeout_seconds']==120 and
         owned['schema']=='ranker-objective-container-core-owned-native-control@1' and owned['mode']==MODE and
         outer['schema']=='ranker-objective-container-core-outer-native-control@1' and
         owned['invocation']==outer['invocation']==plan['invocation'],'actual owned/outer/invocation/source gate joins')
    need(owned['native_proof_checks']==[plan['check']] and owned['native_checker_attempts']==
         [{'specification':plan['specification'],'native_invocations_observed':1}],'exact single native check attempt')
    for key in ('request','specification'):need(prepared['prepared_input_pins'][key]==plan[key],'prepared exact input descriptor')
    profilepin=spec['environment_manifest'];profile=document(profilepin)
    need(prepared['prepared_input_pins']['profile']==profilepin==check['environment_manifest'] and check['source']==spec['source'] and
         check['retention_helper']==spec['retention_helper'] and check['python_executable']==spec['python_executable'],'actual check/spec/profile/retention/python joins')
    original=exact(plan['math_source'],True);source=exact(spec['source'],True)
    need(source==original and profile['selected_proof_sources']==[spec['source']],'reviewed mathematical draft exactly equals actual captured native source')
    augmented=exact(bare(check['augmented_source']),True)
    need(augmented==source+b'\n'+b'\n'.join(('#print axioms _root_.'+name).encode() for name in QUERIES)+b'\n','actual augmented source literal byte equality')
    for row in invocation['inputs']:exact(row)
    driver=exact(invocation['driver'],True);original_driver=exact(prepared['prepared_input_pins']['driver'],True)
    need(driver==original_driver and invocation['driver']['path']==str(Q/('captured-driver-'+MODE+'.py')) and
         prepared['prepared_input_pins']['driver'] in tool_review['reviewed_input_pins'],'actual admitted original and captured driver same bytes')
    for key in ('freeze_producer','checker_wrapper','retention_helper','file_helpers','python_executable'):exact(spec[key])
    need(check['status']==plan['expected_native_status'] and check['native_bounds']==
         {'cpu_seconds':20,'max_input_bytes':262144,'max_output_bytes':65536,'max_workspace_bytes':16777216,'timeout_seconds':20},'actual native status and unchanged five caps')
    integer(check['native_invocations'],1,1,'actual native calls');integer(check['native_lean_invocations'],1,1,'actual Lean calls')
    need(check['actual_root_lease']==owned['root_lease'] and check['workspace_cleaned'] is True and
         type(check['native_elapsed_seconds']) in (int,float) and 0<=check['native_elapsed_seconds']<=20,'actual lease/cleanup/time')
    for flag in ('timed_out','unavailable','resource_exhausted','cancelled','workspace_limit_exceeded','output_truncated'):
        need(check[flag] is False,'bounded actual attempt no refusal/truncation flag')
    need(check['post_call_binding_error'] is None and check['artifact_anomalies']==[],'no native binding/artifact anomaly')
    query_reports=reports(check,source)
    accepted=check['status']=='passed'
    if accepted:
        need(check['matches_expectation'] is True and check['native_lean_returncode']==check['returncode']==0 and
             owned['status']=='passed' and owned['primary_error'] is None and outer['returncode']==0,'native success, never stdout-only qualification')
    else:
        need(check['matches_expectation'] is False and check['native_lean_returncode']==check['returncode']==1 and
             owned['status']=='failed' and owned['primary_error'] is not None and outer['returncode']==1,'retained inconclusive nonzero attempt')
    native_module=retention(check,accepted)
    need(owned['cleanup_errors']==outer['cleanup_errors']==[] and outer['primary_error'] is None and
         outer['native_model_test_metadata_or_codec_callbacks']=='native_only' and
         type(outer['elapsed_seconds_outer']) in (int,float) and outer['elapsed_seconds_outer']<=120,'clean actual native-only outer closure')
    for name in ('native_preparation_calls','gradient_evaluations','optimizer_updates','fit_calls','autoencoder_fit_calls','test_cases',
                 'metadata_hydration_calls','source_function_executions','dependency_setup_calls'):
        integer(owned[name],0,0,'forbidden counter '+name)
    integer(owned['strict_old_input_count'],2391,2391,'strict old count');integer(owned['protected_live_source_count'],4,4,'live count')
    need(owned['all_strict_old_and_protected_live_inputs_unchanged'] is True and owned['root_release_returned'] is True,'actual guarded and released phase')
    state=owned['final_resource_state']
    for name in ('active_lease_count','active_root_lease_count','active_child_lease_count','waiting_request_count'):
        integer(state[name],0,0,'drained '+name)
    lease=owned['root_lease'];need(lease['lane']=='orchestration' and lease['cpu_slots']==1 and lease['memory_mb']==2048 and lease['child_process_slots']==4,'unchanged root lease capacity')
    policy=owned['resource_policy']
    need(policy['proof_safety_enabled'] is True and policy['proof_memory_stall_percent']==2.0 and
         policy['proof_cpu_stall_percent']==50.0 and policy['proof_io_stall_percent']==10.0 and policy['proof_backoff_seconds']==2.0,'unchanged proof pressure')
    wanted=request['original_checkout_guards']
    need(owned['original_checkout_guards_before']==owned['original_checkout_guards_after']==
         outer['original_checkout_guards_before']==outer['original_checkout_guards_after']==wanted,'actual original root/child HEAD/index before-after joins')
    for row in wanted.values():exact(row['index'])
    guards=request['strict_old_inputs']+request['protected_live_sources']
    need(len(request['strict_old_inputs'])==2391 and len(request['protected_live_sources'])==4 and
         len({row['path'] for row in guards})==2395,'exact complete unique guard union')
    for row in guards:exact(row)
    for item in owned['selected_owned_imports']:
        need(item['before']==item['after'] and item['matches'] is True,'all actually owned source imports unchanged');exact(item['after'])
    need(owned['blocked_imports']==[],'no unreviewed import admission attempt')
    for body in (math_review,tool_review,prepared,request,check):false_authority(body)
    need(all(owned[key] is False for key in AUTHORITY[:3]) and 'planner_activation' not in owned,
         'actual v1 owned authority format is three explicit false fields with absent planner field')
    need(request['planner_activation'] is False and check['planner_activation'] is False and
         prepared['planner_activation'] is False, 'independently pinned actual native-only inputs deny planner activation')
    for name in ('python_ranker_source_equivalence_proved','binary64_error_bound_proved','optimizer_convergence_proved'):
        need(check[name] is False,'broad native claim remains false')
    need(check['full_task_satisfaction']=='unknown' and check['all32_governing_RPI_exits']=='OPEN' and
         check['official_benchmark_score'] is None and check['environment_actual_runtime_open_trace_claimed'] is False,'task and runtime tracing frontiers')
    old_profile=document(spec['profile_parent']);files={row['path']:row for row in profile['files']}
    need(len(files)==len(profile['files'])==profile['external_file_count']==check['environment_file_count']==20114 and
         sum(row['bytes'] for row in files.values())==profile['external_file_bytes']==3546337372 and
         len(old_profile['files'])==20109 and all(files.get(row['path'])==row for row in old_profile['files']),
         'complete physical declared environment and historical file-prefix preservation')
    need(profile['source_import_modules']==old_profile['source_import_modules'] and profile['local_checked_modules']==old_profile['local_checked_modules'] and
         profile['lean_path']==old_profile['lean_path'] and profile['requested_imports']==old_profile['requested_imports'] and
         profile['native_per_file_capture_bytes_unchanged']==65536 and profile['root_reconstructed_external_module_aggregate_max_bytes']==3997696,'unchanged loader/dependency/capture limits')
    historical=imports(spec,profile)
    print(json.dumps({'progress':'file_only_environment_body_hashes','files':len(files),'bytes':profile['external_file_bytes']}),flush=True)
    for row in files.values():exact(row)
    for row in guards:exact(row)
    environment_paths=set(files)
    for path,row in list(HELD.items()):
        if str(path) not in environment_paths:exact(row)
    descriptor_digest=hashlib.sha256(json.dumps([files[name] for name in sorted(files)],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    reviewed=[plan[name] for name in ('math_source','math_source_review','tooling_source_review','prepared_input_review','request',
              'specification','invocation','owned','outer','check')]+[profilepin]
    result={'schema':'ranker-objective-container-core-independent-semantic-native-review@1',
        'status':'passed_file_only_actual_receipt_review' if accepted else 'passed_file_only_retained_inconclusive_native_attempt',
        'findings':[],'outstanding_review_issues':[],'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'review_source':own,'frozen_review_plan':planpin,'reviewed_input_pins':reviewed,
        'actual_native_status':check['status'],'actual_native_invocations':1,'native_qualification_observed':accepted,
        'qualified_native_checks':1 if accepted else 0,'qualified_theorem_queries':4 if accepted else 0,
        'observed_query_reports':query_reports,'actual_report_occurrences_per_query':2,'only_allowed_standard_axioms':AXIOMS,
        'stdout_only_axiom_reports_suffice_for_qualification':False,'actual_retained_module':native_module,
        'complete_historical_import_objects_and_ordered_chunks':historical,'actual_source':spec['source'],'actual_augmented_source':check['augmented_source'],
        'actual_source_equals_independently_reviewed_math_and_augmented_literal':True,
        'actual_each_phase_guard_counts':{'strict_old_inputs':2391,'protected_live_sources':4},
        'all_guard_descriptor_bodies_rehashed_before_after':True,'actual_original_HEAD_index_guard_evidence':wanted,
        'HEAD_observation_origin':'Both actual owned and outer native receipts; no Git command rerun by this reviewer.',
        'actual_leases_drained_and_forbidden_counters_zero':True,'native_caps':check['native_bounds'],
        'owned_planner_flag_present':False,'planner_activation_denied_by_exact_frozen_request_check_and_source_gates':True,
        'physical_environment':{'manifest':profilepin,'files':len(files),'bytes':profile['external_file_bytes'],
              'all_declared_file_bodies_independently_hashed':True,'sorted_descriptor_map_sha256':descriptor_digest,
              'each_fd_read_and_path_stat_stable':True,'whole_live_atomic_snapshot_claimed':False,'actual_runtime_open_trace_claimed':False},
        'narrow_semantic_scope':'Only the four generic finite-index ordered-map/positive-mean/empty-refusal/indexed-zip-sum mathematical bridges may be qualified after an actually successful complete native module; no source objective/gradient compiler is qualified.',
        'full_objective_semantics_proved':False,'full_gradient_semantics_proved':False,'python_ranker_source_equivalence_proved':False,
        'host_parser_correctness_theorem_proved':False,'Python_Float_semantics_proved':False,'CPython_math_fsum_semantics_proved':False,
        'full_training_semantics_proved':False,'whole_codebase_IR_semantic_preservation_proved':False,'global_autoencoder_convergence_proved':False,
        'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
        'all32_governing_RPI_exits':'OPEN','full_task_satisfaction':'unknown','official_benchmark_score':None,
        'reviewer_target_imports_or_Git_network_native_test_model_training_metadata_preparation_jobs':0,
        'limitations':['This independently reads actual retained evidence; no native attempt or project callback is rerun.',
             'A nonzero Lean process and absent full module always qualify zero queries, even when all requested stdout reports appear.',
             'Descriptor body reads are stable individually, with compact inputs/guard bodies rechecked; no simultaneous whole-live snapshot or runtime-open trace is claimed.']}
    with args.output.open('xb') as stream:
        stream.write((json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode());stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'status':result['status'],'qualified_queries':result['qualified_theorem_queries'],'receipt':read(args.output)[1]}),flush=True)


if __name__=='__main__':main()
