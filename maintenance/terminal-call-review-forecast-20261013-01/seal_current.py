"""Explicit current review-forecast evidence seal after independent audit."""
import hashlib
import json
import os
from pathlib import Path
import stat

V=Path(__file__).resolve().parent
os.umask(0o077)
def read(path):return json.loads(path.read_bytes())
def wire(value):return json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False).encode()+b'\n'
def pin(path):
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
baseline=read(V/'baseline-manifest.json')
preservation=read(V/'preservation-before-package.json')
inventory=read(V/'actual-public-inventory.json')
package=read(V/'package-report.json')
tests=read(V/'test-final-run.json')
actual=read(V/'preview-run-04/summary.json')
review=read(V/'independent-review.json')
assert preservation['qualified'] is True and preservation['all_expected_pins_unchanged'] is True
assert preservation['checked_occurrences']==len(preservation['occurrences'])==231
preservation_pins=[]
for occurrence in preservation['occurrences']:
    assert occurrence['unchanged'] is True and occurrence['actual']==occurrence['expected']
    preservation_pins.append(occurrence['expected'])
assert review['passed'] is True and review['failed_checks']==0
assert tests['tests']==tests['unique_identities']==159
assert tests['exit_code']==tests['failures']==tests['errors']==tests['skipped']==0
assert tests['all_sources_unchanged'] is True
assert package['patch_check_passed'] and package['patch_exact_apply_passed'] and package['source_count']==6
assert actual['qualified'] and len(actual['selected_task_ids'])==3
assert actual['native_parallel_outcome']=='review_only' and actual['admitted_execution_width']==0
assert actual['remaining_admission_blockers']==['ir_admission_materials_absent']
assert actual['stable_review_projection_equal'] and actual['normalized_forecasts_equal'] and actual['exact_each_native_parallel_replay']
assert actual['complete_parallel_plan_ids_equal'] is False
assert len(actual['controls'])==10 and all(item['rejected'] is True for item in actual['controls'])
assert actual['resources_after']['active_lease_count']==actual['resources_after']['waiting_request_count']==0
assert actual['held_resources_before_release']['active_lease_count']==1
for item in preservation_pins:assert pin(Path(item['path']))==item,item['path']
for item in package['files']:
    assert pin(Path(item['source']['path']))==item['source']
    assert pin(Path(item['packaged']['path']))==item['packaged']
    assert item['source']['sha256']==item['packaged']['sha256']
for item in inventory['files']:assert pin(Path(item['path']))==item,item['path']
final_preservation={**preservation,'schema':'terminal-call-review-final-preservation@1'}
(V/'preservation-final.json').write_bytes(wire(final_preservation));(V/'preservation-final.json').chmod(0o600)
summary={'schema':'terminal-call-review-forecast-qualification@1','qualified_conditional_review_forecast':True,
    'selected_run':'preview-run-04','source_count':6,'unique_tests':159,'live_negative_controls':10,
    'native_stages_passed':['scan','query','evidence','obligation','candidate','critique','parallel_plan'],
    'native_admission_passed':False,'remaining_admission_blockers':['ir_admission_materials_absent'],
    'native_parallel_outcome':'review_only','admitted_execution_width':0,'execution_waves':[],
    'assignments':[],'merge_order':[],'parallel_issues':[],
    'review_tasks':actual['selected_task_ids'],'held_native_quota':{'cpu_slots':1,'process_slots':1,'memory_mb':64},
    'held_lease_count':1,'leases_after_release':0,'source_metadata_rows':49,'source_metadata_families':20,
    'fresh_qualification_lean_processes':3,'checker_invocations_during_planning':0,
    'offline_expanded_tokens':47608,'offline_capsule_tokens':9708,'offline_reduction_basis_points':7960,
    'tokenizer':actual['tokenizer'],'provider_token_savings_measured':False,
    'stable_input_candidate_critique_projection_identities':True,'exact_each_native_parallel_replay':True,
    'complete_parallel_plan_ids_equal':False,'temporal_normalization_exclusions':actual['normalization_exclusions'],
    'identity_scope':'only independently sampled compile time and its derived receipt hashes differ; every source/capacity/deadline/resource/task binding retained',
    'extension_validation':'closed application projection and CID validated; native critic applies structural checks without builtin custom-schema parser',
    'next_token_reduction_recommendation':pin(V/'semantic-capsule-gap-review.json'),
    'native_semantic_capsule_compiler_or_code_minifier_used_in_this_qualification':False,
    'independent_review':pin(V/'independent-review.json'),'independent_review_checks':review['check_count'],
    'package':pin(V/'package-report.json'),'predecessor_preservation_occurrences':231,'preservation_deduplicated':False,
    'proof_authority':False,'execution_authority':False,'completion_authority':False,'mutation_authority':False,
    'review_task_completion_proved':False,'production_admitted':False,'worker_launched':False,
    'source_body_executed':False,'runtime_behavior_verified':False,'source_origin_proved':False,
    'training_steps':0,'provider_calls':0,'convergence_proved':False,'full_task_satisfaction':False,
    'quack_transport_used':False,'network_isolation_enforced':False,
    'project_commits_created':0,'project_pushes':0,'authored_fixture_commits_created':1}
(V/'qualification-report.json').write_bytes(wire(summary));(V/'qualification-report.json').chmod(0o600)
names=['baseline-manifest.json','experiment-plan.json','preservation-before-package.json','preservation-final.json',
    'actual-public-inventory.json','inventory_current.py','improvement-status.json','package-report.json','stage-v.patch',
    'qualify_current.py','run_current.py','run_unit_suite.py','package_current.py','seal_current.py',
    'independent-review.py','independent-review.json','qualification-report.json','development-history.json',
    'semantic-capsule-gap-review.json',
    'agent-call-review-capacity-01.xml','agent-call-review-capacity-02.xml',
    'agent-review-projection-01.xml','agent-review-projection-01-run.json',
    'agent-review-projection-02.xml','agent-review-projection-02-run.json',
    'agent-review-projection-03.xml','agent-review-projection-03-run.json',
    'root-focused.xml','test-final.xml','test-final-run.json',
    'candidate-01-test-final.xml','candidate-01-test-final-run.json',
    'candidate-02-test-final.xml','candidate-02-test-final-run.json',
    'candidate-01-review-planning.py','candidate-02-review-projection.py',
    'candidate-03-run_current.py','candidate-02-run_unit_suite.py']
paths={V/name for name in names}
paths.update(V/f'preview-run-{number:02d}/failure.json' for number in (1,2,3))
paths.add(V/'preview-run-03/expanded-preview.json')
paths.update(V/'preview-run-04'/name for name in ('intent-profile.json','policy.json','query.json','capsule.json',
    'pre-capacity-binding.json','capacity.json','expanded-packet.json','capsule-packet.json',
    'expanded-preview.json','capsule-preview.json','final-current-preview.json','summary.json'))
paths.update(Path(item['source']['path']) for item in package['files'])
paths.update(Path(item['packaged']['path']) for item in package['files'])
paths.update(Path(item['path']) for item in inventory['files'])
current=read(V/'preview-run-04/final-current-preview.json')
query=read(V/'preview-run-04/query.json')
producer_occurrences=current['producer']['files']+current['capsule']['producer']['files']+query['producer']['files']+current['capacity']['producer']['files']
for item in producer_occurrences:assert pin(Path(item['path']))==item,item['path']
paths.update(Path(item['path']) for item in producer_occurrences)
paths.add(Path(baseline['sealed_predecessor']['path']))
paths.update(Path(item['path']) for item in baseline['dependencies'])
signature=lambda info:tuple(getattr(info,key) for key in ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
witnesses=[]
try:
    files=[]
    for path in sorted(paths):
        assert path.is_absolute() and path.resolve(strict=True)==path
        assert path.suffix not in {'.duckdb','.wal','.parquet'} and '/cas/' not in str(path)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(8*1024*1024+1)
        assert len(raw)==before.st_size<=8*1024*1024
        assert signature(before)==signature(os.fstat(fd))==signature(path.lstat())
        item={'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        files.append(item);witnesses.append((path,fd,signature(before),item))
    manifest={'schema':'terminal-call-review-forecast-evidence-manifest@1','stage':str(V),'files':files,
        'explicit_named_file_count':len(files),'selected_run':'preview-run-04','unique_tests':159,
        'live_negative_controls':10,'selected_qualification':pin(V/'qualification-report.json'),
        'selected_direct_producer_pin_occurrences':len(producer_occurrences),
        'predecessor_preservation_occurrences':231,'preservation_deduplicated':False,
        'development_failures_and_cached_skips_retained_and_excluded':True,'recursive_traversal':False,
        'database_bodies_included':False,'cas_bodies_included':False,'ducklake_parquet_bodies_included':False,
        'raw_worker_or_model_transcripts_included':False,'native_storage_verified_by_actual_readback':True,
        'retained_file_witnesses_rechecked':True,'native_review_forecast_accepted':True,'admitted_execution_width':0,
        'production_admitted':False,'worker_launched':False,'completion_authority':False,
        'loaded_module_code_attested':False,'transitive_dependency_closure_attested':False,
        'caller_record_origin_verified':False,'provider_calls':0,'training_steps':0,'source_body_executed':False,
        'runtime_behavior_verified':False,'convergence_proved':False,'full_task_satisfaction':False}
    raw=wire(manifest)
    for path,fd,sig,item in witnesses:
        assert signature(os.fstat(fd))==sig==signature(path.lstat())
        os.lseek(fd,0,os.SEEK_SET)
        with os.fdopen(os.dup(fd),'rb') as stream:data=stream.read(8*1024*1024+1)
        assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
        assert signature(os.fstat(fd))==sig==signature(path.lstat())
    for item in preservation_pins:assert pin(Path(item['path']))==item,item['path']
    with (V/'evidence-manifest.json').open('xb') as stream:stream.write(raw)
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':hashlib.sha256(raw).hexdigest(),
        'tests':159,'preserved_occurrences':231,'offline_token_reduction_basis_points':7960}))
finally:
    for _,fd,_,_ in witnesses:os.close(fd)
