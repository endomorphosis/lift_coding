"""Independent source/JSON-only review of the isolated induction tactic patch."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat

W=Path('/home/barberb/lift_coding')
OLD=W/'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-01'
NEW=W/'qualification/codebase_ir/ranker-objective-container-core-candidate-20261005-02'
OUT=Path(__file__).resolve().parent
EXPECTED={
 'math/ObjectiveContainerCore.lean':(6340,'9c3761eb4b778ed04349ae29ef84a4b93f1da36c0f8ef9b59e806805ff10c9b3'),
 'candidate-interface.json':(11720,'3dcd00fba002d0ad3e2ecb06a4146bbcc4a2d0212c212d5f71fae8562d85e7ac'),
 'source-model-obligations-01.json':(6615,'f35f270b7cc77f41a62d52a30e8c1bf2da78ffdc9474fc1e70d3d02e2c1299b7')}
QUERIES=['RankerObjectiveContainerIR.map_exact_ofFn_success','RankerObjectiveContainerIR.mean_exact_ofFn_success',
         'RankerObjectiveContainerIR.mean_exact_empty_refuses','RankerObjectiveContainerIR.indexed_zip_fsum_ofFn_eq']
HELD={}


def need(value,message):
 if value is not True:raise ValueError(message)


def read(path):
 need(path.is_absolute() and path.resolve(strict=True)==path and not path.is_symlink(),'canonical source')
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  first=os.fstat(fd);need(stat.S_ISREG(first.st_mode) and first.st_size<=1024**2,'bounded regular review input')
  parts=[];size=0
  while block:=os.read(fd,65536):
   size+=len(block);need(size<=first.st_size,'input grew');parts.append(block)
  sig=lambda value:tuple(getattr(value,key) for key in ('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
  need(sig(first)==sig(os.fstat(fd))==sig(path.lstat()) and size==first.st_size,'input changed')
  raw=b''.join(parts)
 finally:os.close(fd)
 need(path not in HELD or HELD[path]==raw,'previous input changed');HELD[path]=raw
 return raw


def pin(path):
 raw=read(path);return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def load(row):
 path=Path(row['path']);need(pin(path)==row,'exact descriptor');return json.loads(HELD[path])


def main():
 need(__debug__,'optimized review refused')
 need(OUT==W/'maintenance/ranker-objective-container-core-patch-source-review-20261005-02' and
      not (OUT/'review-receipt.json').exists(),'fresh independent patch-review namespace')
 candidate={}
 for name,(size,digest) in EXPECTED.items():
  row=pin(NEW/name);need((row['bytes'],row['sha256'])==(size,digest),'new source pin');candidate[name]=row
 oldpin=pin(OLD/'math/ObjectiveContainerCore.lean')
 need((oldpin['bytes'],oldpin['sha256'])==(6368,'9f6f36352ec1b45bb8d797cae03683455fcd03d1c3e7663a1991378baeb8da14'),'immutable old math')
 old=HELD[Path(oldpin['path'])];new=HELD[NEW/'math/ObjectiveContainerCore.lean']
 previous=b'  induction n generalizing inputs outputs with\n';replacement=b'  induction n with\n'
 need(old.count(previous)==1 and old.replace(previous,replacement)==new and len(old)-len(new)==28,
      'exact single redundant generalizing phrase removal; every other source byte unchanged')
 need(re.findall(rb'^#print axioms ([^\n]+)$',new,re.M)==[name.removeprefix('RankerObjectiveContainerIR.').encode() for name in QUERIES],
      'same four kernel-query declarations')
 interface=load(candidate['candidate-interface.json']);obligations=load(candidate['source-model-obligations-01.json'])
 need(interface['math_source']==obligations['math_source']==candidate['math/ObjectiveContainerCore.lean'] and
      obligations['candidate_interface']==candidate['candidate-interface.json'],'new same-buffer math/interface joins')
 need([row['name'] for row in interface['proposed_query_batch']]==QUERIES and interface['proposed_native_query_count']==4,
      'same query names and generic premise domains')
 for body in (interface,obligations):
  need(body['status']=='uncompiled_unqualified_source_only_candidate' and body['candidate_compiled'] is False and
       body['candidate_native_qualified'] is False and body['theorem_qualified'] is False and
       body['all32_governing_RPI_exits']=='OPEN' and body['full_task_satisfaction']=='unknown' and
       body['official_benchmark_score'] is None,'unqualified current candidate boundary')
  for name in ('proof_authority','execution_authority','completion_authority','planner_activation',
               'Python_Float_semantics_proved','CPython_math_fsum_semantics_proved','Python_libm_semantics_proved',
               'python_ranker_source_equivalence_proved','full_objective_semantics_proved','full_gradient_semantics_proved',
               'full_preparation_semantics_proved','full_training_semantics_proved','global_autoencoder_convergence_proved',
               'host_parser_correctness_theorem_proved','generic_container_semantic_preservation_proved',
               'whole_codebase_IR_semantic_preservation_proved','optimizer_source_convergence_proved','task_satisfaction_proved'):
   need(body[name] is False,'remaining proof/authority frontier')
 prior=interface['prior_retained_inconclusive_attempt'];need(prior==obligations['prior_retained_inconclusive_attempt'],'same exact historical failed attempt')
 check,owned,outer,invocation=[load(prior[name]) for name in ('check','owned','outer','invocation')]
 need(prior['check']['sha256']=='9eea43fd7e1a67da9b135b84e3ad2646d5cbb42488baa3c31a8f74bcd86e4d80' and
      prior['owned']['sha256']=='37b775169ca4c2cc34a94b1dedfe33d30a5f438af63bb468536218da89168464' and
      prior['outer']['sha256']=='5155fef0434a8e0651b8acf3d2451940dbbbcb11ada27786b7e8e95fcc2907f1' and
      prior['invocation']['sha256']=='307d3eff4cb2f2794f137adedb385af0e514f2ea32e9348baa8bd16a459e6c59','exact old attempt root descriptors')
 need(check['status']=='inconclusive' and check['native_lean_returncode']==1 and check['matches_expectation'] is False and
      check['compiled_artifacts']==[] and check['retention_manifest_body']['status']=='native_nonzero' and
      owned['status']=='failed' and outer['returncode']==1 and owned['cleanup_errors']==outer['cleanup_errors']==[] and
      owned['invocation']==outer['invocation']==prior['invocation'],'prior failed/nonqualified native state')
 need([row['theorem'] for row in check['theorem_axiom_output']]==QUERIES and
      all(row['report_occurrences']==2 and set(row['axioms'])<={'Classical.choice','Quot.sound','propext'} for row in check['theorem_axiom_output']),
      'reports observed but do not qualify a nonzero module')
 need('Unnecessary' in check['stdout'] and 'generalizing' in check['stdout'] and
      obligations['prior_failed_attempt_qualified_queries']==0,'actual tactic diagnostic and zero prior qualification')
 need(owned['strict_old_input_count']==2391 and owned['protected_live_source_count']==4 and
      owned['all_strict_old_and_protected_live_inputs_unchanged'] is True and
      owned['final_resource_state']['active_lease_count']==owned['final_resource_state']['waiting_request_count']==0,
      'retained prior clean guarded drained attempt')
 oldreview=W/'maintenance/ranker-objective-container-core-source-review-20261005-01/review-receipt.json'
 oldreviewpin=pin(oldreview);need(oldreviewpin['sha256']=='a874e5bbf40e11e37e7754b7c9efe5ea95ef60d2a6958ee893671a002d62ee4c','previous full source review')
 for path,raw in list(HELD.items()):need(read(path)==raw,'final reviewed bytes changed')
 own=pin(Path(__file__).resolve())
 result={'schema':'ranker-objective-container-core-independent-source-review@1','status':'passed_source_only','findings':[],
  'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'producer':own,'candidate_pins':candidate,
  'reviewed_input_pins':[oldpin,oldreviewpin,*candidate.values(),*prior.values()],
  'reviewed_query_names':QUERIES,'candidate_compiled':False,'candidate_native_qualified':False,'theorem_qualified':False,
  'actual_new_qualified_queries':0,'prior_failed_attempt_qualified_queries':0,'exact_patch_removed_bytes':28,
  'every_definition_statement_premise_import_query_and_other_math_byte_unchanged':True,
  'prior_failed_attempt_retained_and_not_promoted_from_stdout':True,'prior_source_review':oldreviewpin,
  'reviewed_semantics':['The generic pointwise body-success premise is unchanged; it is not a desired source objective or gradient identity.',
    'The positive mean-length domain, explicit empty refusal and shared finite-index zip shape are unchanged.',
    'Only the rejected redundant induction generalization phrase was removed; actual v2 native checking remains pending.'],
  'native_jobs':0,'project_imports_or_source_function_executions':0,'test_or_model_jobs':0,'remote_mutations':0,
  'proof_authority':False,'execution_authority':False,'completion_authority':False,'planner_activation':False,
  'all32_governing_RPI_exits':'OPEN','full_task_satisfaction':'unknown','official_benchmark_score':None,
  'full_source_Python_Float_training_AE_or_task_equivalence':False,'task_satisfaction_proved':False,
  'limitations':['Exact source reconstruction and static mathematical interface review are not Lean execution or native qualification.']}
 target=OUT/'review-receipt.json'
 with target.open('xb') as stream:
  stream.write((json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode());stream.flush();os.fsync(stream.fileno())
 print(json.dumps({'status':result['status'],'producer':own,'receipt':pin(target)}))


if __name__=='__main__':main()
