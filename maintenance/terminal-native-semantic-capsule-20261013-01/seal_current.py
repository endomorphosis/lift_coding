"""Seal explicit W public evidence after independent audit; no native jobs."""
import hashlib,json,os,stat
from pathlib import Path
W=Path(__file__).resolve().parent
os.umask(0o077)
def read(p):return json.loads(p.read_bytes())
def wire(x):return json.dumps(x,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False).encode()+b'\n'
def pin(p):
    raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def save(p,x):
    with p.open('xb') as f:f.write(wire(x))
base=read(W/'baseline-manifest.json')
pres=read(W/'preservation-before-package.json')
inv=read(W/'actual-public-inventory.json')
package=read(W/'package-report.json')
tests=read(W/'test-final-run.json')
actual=read(W/'preview-run-05/summary.json')
review=read(W/'independent-review.json')
qual=read(W/'qualification-report.json')
assert review['passed'] is True and review['failed_checks']==0
assert tests['tests']==tests['unique_identities']==197
assert tests['exit_code']==tests['failures']==tests['errors']==tests['skipped']==0
assert tests['all_sources_unchanged'] is True
assert actual['qualified'] is True and len(actual['controls'])==11 and all(x['rejected'] is True for x in actual['controls'])
assert actual['native_symbol_count']==6 and actual['native_block_count']==45
assert actual['native_parallel_outcome']=='review_only' and actual['admitted_execution_width']==0
assert actual['remaining_admission_blockers']==['ir_admission_materials_absent']
assert actual['stable_review_projection_equal'] and actual['normalized_forecasts_equal'] and actual['exact_each_native_parallel_replay']
assert actual['measures']['full']['tokens']==56923 and actual['measures']['dictionary']['tokens']==58301
assert actual['measures']['call_capsule_without_native']['tokens']==9791 and actual['selected_transport']=='full'
assert actual['decoded_model_visible_token_delta']==0 and actual['provider_token_savings_measured'] is False
assert actual['resources_after']['active_lease_count']==actual['resources_after']['waiting_request_count']==0
assert package['source_count']==6 and package['patch_check_passed'] and package['patch_exact_apply_passed']
assert inv['explicit_named_file_count']==len(inv['files'])==113
assert pres['checked_occurrences']==len(pres['occurrences'])==269 and pres['all_expected_pins_unchanged']
for item in pres['occurrences']:
    assert item['expected']==item['actual']==pin(Path(item['expected']['path']))
for item in package['files']:
    assert item['source']==pin(Path(item['source']['path']))
    assert item['packaged']==pin(Path(item['packaged']['path']))
    assert item['source']['sha256']==item['packaged']['sha256']
for item in inv['files']:assert item==pin(Path(item['path']))
for item in tests['sources_after']:assert item==pin(Path(item['path']))
for item in review['read_pins']:assert item==pin(Path(item['path']))
save(W/'preservation-final.json',{**pres,'schema':'terminal-native-semantic-final-preservation@1'})
names=['preservation-baseline.json','baseline-manifest.json','boundary-review-criteria.json',
    'qualification-report.json','improvement-status.json','development-history.json','governed-capsule-gap-review.json',
    'actual-public-inventory.json','preservation-before-package.json','preservation-final.json',
    'package-report.json','stage-w.patch','env_run.py','qualify_current.py','run_current.py',
    'candidate-01-run_current.py','package_current.py','inventory_current.py','run_unit_suite.py',
    'seal_current.py','test-final.xml','test-final-run.json','native-focused-report.json',
    'native-focused-followup-report.json','package-attempt-01-failure.json',
    'independent-review.py','independent-review.json']
paths={W/x for x in names}
paths.add(Path(base['sealed_predecessor']['path']))
paths.update(Path(x['path']) for x in base['dependencies'])
paths.update(Path(x['path']) for x in inv['files'])
for item in package['files']:
    paths.add(Path(item['source']['path']));paths.add(Path(item['packaged']['path']))
for i in range(1,6):paths.add(W/f'native-focused-{i:02d}'/'tests.xml')
for family,count in [('context-transport-tests',2),('semantic-review-tests',3)]:
    for i in range(1,count+1):
        paths.add(W/f'{family}-{i:02d}'/'tests.xml');paths.add(W/f'{family}-{i:02d}'/'run.json')
for i in range(1,5):paths.add(W/f'preview-run-{i:02d}'/'failure.json')
selected=['intent-profile.json','policy.json','query.json','checked-call-capsule.json',
    'observed-manifest.json','native-semantic-capsules.json','code-views.json',
    'pre-capacity-binding.json','capacity.json','original-call-context.json',
    'full-packet.json','dictionary-packet.json','full-preview.json','dictionary-preview.json',
    'final-current-preview.json','summary.json']
paths.update(W/'preview-run-05'/name for name in selected)
current=read(W/'preview-run-05/final-current-preview.json')
query=read(W/'preview-run-05/query.json')
checked=read(W/'preview-run-05/checked-call-capsule.json')
occurrences=current['producer']['files']+current['capacity']['producer']['files']+query['producer']['files']+checked['producer']['files']
for item in occurrences:assert item==pin(Path(item['path']))
paths.update(Path(x['path']) for x in occurrences)
sig=lambda s:tuple(getattr(s,x) for x in ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
witnesses=[]
try:
    files=[]
    for p in sorted(paths):
        assert p.is_absolute() and p.resolve(strict=True)==p
        assert p.suffix not in {'.duckdb','.wal','.parquet'} and '/cas/' not in str(p)
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1
        with os.fdopen(os.dup(fd),'rb') as f:raw=f.read(8*1024*1024+1)
        assert len(raw)==before.st_size<=8*1024*1024
        assert sig(before)==sig(os.fstat(fd))==sig(p.lstat())
        item={'path':str(p),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        files.append(item);witnesses.append((p,fd,sig(before),item))
    manifest={'schema':'terminal-native-semantic-evidence-manifest@1','stage':str(W),
        'explicit_named_file_count':len(files),'files':files,'selected_run':'preview-run-05',
        'unique_tests':197,'live_negative_controls':11,'selected_qualification':pin(W/'qualification-report.json'),
        'selected_direct_producer_pin_occurrences':len(occurrences),'predecessor_preservation_occurrences':269,
        'preservation_deduplicated':False,'development_failures_retained_and_excluded':True,
        'public_inventory_only_no_recursive_storage_walk':True,'database_bodies_included':False,
        'private_cas_bodies_included':False,'ducklake_parquet_bodies_included':False,
        'full_native_in_memory_bundle_retained_as_public_JSON':True,
        'raw_worker_or_model_transcripts_included':False,'native_storage_verified_by_actual_cold_readback':True,
        'retained_file_witnesses_rechecked':True,'native_review_forecast_accepted':True,
        'admitted_execution_width':0,'production_admitted':False,'worker_launched':False,
        'loaded_module_code_attested':False,'transitive_dependency_closure_attested':False,
        'completion_authority':False,'omission_authority':False,'caller_record_origin_verified':False,
        'provider_calls':0,'training_steps':0,'source_body_executed':False,'runtime_behavior_verified':False,
        'convergence_proved':False,'full_task_satisfaction':False,
        'offline_full_tokens':56923,'offline_dictionary_tokens':58301,'selected_transport':'full',
        'provider_token_savings_measured':False,'decoded_model_visible_token_saving':0}
    for p,fd,s,item in witnesses:
        assert sig(os.fstat(fd))==s==sig(p.lstat())
        os.lseek(fd,0,os.SEEK_SET)
        with os.fdopen(os.dup(fd),'rb') as f:data=f.read(8*1024*1024+1)
        assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
        assert sig(os.fstat(fd))==s==sig(p.lstat())
    for item in pres['occurrences']:assert item['expected']==pin(Path(item['expected']['path']))
    for item in review['read_pins']:assert item==pin(Path(item['path']))
    raw=wire(manifest)
    with (W/'evidence-manifest.json').open('xb') as f:f.write(raw)
    print(json.dumps({'sealed_files':len(files),'manifest_sha256':hashlib.sha256(raw).hexdigest(),
        'tests':197,'preserved_occurrences':269,'selected_transport':'full'}))
finally:
    for _,fd,_,_ in witnesses:os.close(fd)
