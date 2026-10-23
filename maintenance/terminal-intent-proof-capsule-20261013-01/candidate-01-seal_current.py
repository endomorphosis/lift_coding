"""Seal only explicitly named public evidence after independent review."""
import hashlib
import json
import os
from pathlib import Path
import stat

U = Path(__file__).resolve().parent
os.umask(0o077)

def read(path):
    return json.loads(path.read_bytes())

def wire(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).encode()+b'\n'

def pin(path):
    raw = path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

baseline = read(U/'baseline-manifest.json')
preservation = read(U/'preservation-before-package.json')
package = read(U/'package-report.json')
tests = read(U/'test-final-run.json')
actual = read(U/'preview-run-04/summary.json')
review = read(U/'independent-review.json')
assert review.get('passed') is True, 'independent evidence review did not pass'
gap_review = read(U/'execution-admission-gap-review.json')
assert gap_review.get('qualified') is True
assert tests['tests']==tests['unique_identities']==223
assert tests['exit_code']==tests['failures']==tests['errors']==tests['skipped']==0
assert tests['all_sources_unchanged'] is True
assert package['patch_check_passed'] and package['patch_exact_apply_passed']
assert actual['qualified'] and actual['native_plan_identities_equal'] and actual['normalized_capsules_equal']
assert len(actual['selected_task_ids'])==3 and len(actual['controls'])==9
assert all(item['rejected'] is True for item in actual['controls'])
for value in preservation['files']:
    assert pin(Path(value['path']))==value, value['path']
for value in package['files']:
    assert pin(Path(value['source']['path']))==value['source']
    assert pin(Path(value['packaged']['path']))==value['packaged']
    assert value['source']['sha256']==value['packaged']['sha256']
final_preservation={**preservation,'schema':'terminal-intent-proof-capsule-final-preservation@1'}
(U/'preservation-final.json').write_bytes(wire(final_preservation))
(U/'preservation-final.json').chmod(0o600)
summary={'schema':'terminal-intent-proof-capsule-qualification@1','qualified_conditional_preview':True,
    'selected_run':'preview-run-04','selected_current_source_count':6,'unique_tests':223,
    'negative_live_controls':9,'fresh_native_metadata_rows':49,'fresh_native_metadata_families':20,
    'fresh_lean_qualification_processes':3,'provider_calls':0,'training_steps':0,
    'checker_invocations_during_planning':0,'source_body_executed':False,
    'offline_expanded_tokens':44770,'offline_capsule_tokens':6627,'offline_reduction_basis_points':8519,
    'tokenizer_method':pin(U/'tokenizer-method.json'),'provider_token_savings_measured':False,
    'scope':'exact closed CNL to native IntentIR and current conditional model; genuine native deterministic planning-service preview',
    'native_candidate_and_critique_passed':True,'all_three_review_tasks_retained':True,
    'native_execution_admitted':False,'native_parallel_plan_admitted':False,
    'execution_gap_review':pin(U/'execution-admission-gap-review.json'),
    'independent_review':pin(U/'independent-review.json'),'package':pin(U/'package-report.json'),
    'preserved_predecessor_occurrences':245,'preservation_deduplicated':False,
    'proof_authority':False,'completion_authority':False,'mutation_authority':False,
    'runtime_behavior_verified':False,'source_origin_proved':False,'convergence_proved':False,
    'public_terminal_bench_task_satisfied':False,'production_admitted':False,'worker_launched':False,
    'quack_transport_used':False,'network_isolation_enforced':False,'commits_created':0,'pushes':0}
(U/'qualification-report.json').write_bytes(wire(summary));(U/'qualification-report.json').chmod(0o600)
names=['baseline-manifest.json','experiment-plan.json','preservation-before-package.json','preservation-final.json',
    'actual-public-inventory.json','tokenizer-method.json','improvement-status.json','package-report.json',
    'stage-u.patch','qualify_current.py','run_current.py','run_unit_suite.py','package_current.py','seal_current.py',
    'independent-review.py','independent-review.json','execution-admission-gap-review.json','qualification-report.json',
    'development-history.json','candidate-01-intent-planning.py','candidate-02-intent-planning.py',
    'candidate-03-intent-planning.py','candidate-01-package_current.py','candidate-01-stage-u.patch',
    'agent-call-intent-profile-01.xml','agent-call-intent-profile-01-run.json','agent-call-proof-capsule-01.xml',
    'agent-call-intent-planning-01.xml','agent-call-intent-planning-01-run.json','test-final.xml','test-final-run.json']
paths={U/name for name in names}
paths.update(U/f'preview-run-{number:02d}/failure.json' for number in (1,2,3))
paths.update(U/'preview-run-04'/name for name in ('intent-profile.json','policy.json','query.json','capsule.json',
    'expanded-packet.json','capsule-packet.json','expanded-preview.json','capsule-preview.json',
    'final-current-preview.json','summary.json'))
paths.update(Path(item['source']['path']) for item in package['files'])
paths.update(Path(item['packaged']['path']) for item in package['files'])
inventory=read(U/'actual-public-inventory.json')
paths.update(Path(item['path']) for item in inventory['files'])
current=read(U/'preview-run-04/final-current-preview.json')
producer_occurrences=current['producer']['files']+current['capsule']['producer']['files']
query=read(U/'preview-run-04/query.json')
producer_occurrences+=query['producer']['files']
paths.update(Path(item['path']) for item in producer_occurrences)
paths.add(Path(baseline['sealed_predecessor']['path']))
paths.update(Path(item['path']) for item in baseline['dependencies'])
paths.update(Path(item['path']) for item in gap_review['named_source_pins'])
for item in inventory['files']+producer_occurrences+gap_review['named_source_pins']:
    assert pin(Path(item['path']))==item, item['path']
witnesses=[]
try:
    files=[]
    signature=lambda info:tuple(getattr(info,name) for name in ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
    for path in sorted(paths):
        assert path.is_absolute() and path.resolve(strict=True)==path
        assert path.suffix not in {'.duckdb','.wal','.parquet'} and '/cas/' not in str(path)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1
        with os.fdopen(os.dup(fd),'rb') as stream: raw=stream.read(8*1024*1024+1)
        assert len(raw)==before.st_size<=8*1024*1024
        assert signature(before)==signature(os.fstat(fd))==signature(path.lstat())
        value={'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        files.append(value);witnesses.append((path,fd,signature(before),value))
    manifest={'schema':'terminal-intent-proof-capsule-evidence-manifest@1','stage':str(U),
        'files':files,'explicit_named_file_count':len(files),'unique_tests':223,'live_negative_controls':9,
        'selected_run':'preview-run-04','selected_qualification':pin(U/'qualification-report.json'),
        'selected_direct_producer_pin_occurrences':len(producer_occurrences),
        'predecessor_preservation_occurrences':245,'preservation_occurrences_deduplicated':False,
        'development_failures_retained_and_excluded':True,'recursive_traversal':False,
        'private_database_bodies_included':False,'ducklake_parquet_bodies_included':False,
        'cas_bodies_included':False,'raw_worker_or_model_transcripts_included':False,
        'native_storage_verified_by_actual_readback':True,'retained_file_witnesses_rechecked':True,
        'loaded_module_code_attested':False,'transitive_dependency_closure_attested':False,
        'caller_record_origin_verified':False,'provider_calls':0,'training_steps':0,
        'source_body_executed':False,'proof_authority':False,'runtime_behavior_verified':False,
        'convergence_proved':False,'full_task_satisfaction':False,'native_execution_admitted':False}
    raw=wire(manifest)
    for path,fd,sig,value in witnesses:
        assert signature(os.fstat(fd))==sig==signature(path.lstat())
        os.lseek(fd,0,os.SEEK_SET)
        with os.fdopen(os.dup(fd),'rb') as stream: current_raw=stream.read(8*1024*1024+1)
        assert hashlib.sha256(current_raw).hexdigest()==value['sha256'] and len(current_raw)==value['bytes']
        assert signature(os.fstat(fd))==sig==signature(path.lstat())
    for value in preservation['files']:assert pin(Path(value['path']))==value
    path=U/'evidence-manifest.json'
    with path.open('xb') as stream:stream.write(raw)
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':hashlib.sha256(raw).hexdigest(),
        'tests':223,'preserved_occurrences':245,'offline_token_reduction_basis_points':8519}))
finally:
    for _,fd,_,_ in witnesses:os.close(fd)
