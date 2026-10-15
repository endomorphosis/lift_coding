"""Seal named public Y evidence after independent review; no native jobs."""
import hashlib,json,os,stat
from pathlib import Path
Y=Path(__file__).resolve().parent
os.umask(0o077)
def read(p):return json.loads(p.read_bytes())
def pin(p):
 r=p.read_bytes();return {'path':str(p),'bytes':len(r),'sha256':hashlib.sha256(r).hexdigest()}
def wire(v):return json.dumps(v,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False).encode()+b'\n'
def save(p,v):
 with p.open('xb') as f:f.write(wire(v))
base=read(Y/'baseline-manifest.json');pres=read(Y/'preservation-before-package.json')
inv=read(Y/'actual-public-inventory.json');package=read(Y/'package-report.json')
tests=read(Y/'test-final-run.json');actual=read(Y/'preview-run-02/summary.json')
review=read(Y/'independent-review.json');qual=read(Y/'qualification-report.json')
assert review['passed'] is True and review['failed_checks']==0
assert tests['tests']==tests['unique_identities']==162
assert tests['exit_code']==tests['failures']==tests['errors']==tests['skipped']==0 and tests['all_sources_unchanged']
assert qual['qualified'] and actual['qualified'] and len(actual['controls'])==13 and all(x['rejected'] for x in actual['controls'])
assert actual['traces']['expanded']['initial_tokens']==70977 and actual['traces']['view']['initial_tokens']==47215
assert actual['traces']['view']['totals']['rendered_input_tokens']==95678
assert actual['actual_current_expansion_calls']==['native_block']
assert actual['native_basis_equal'] and actual['native_projection_equal']
assert actual['resources_after']['active_lease_count']==actual['resources_after']['waiting_request_count']==0
assert package['source_count']==4 and package['patch_check_passed'] and package['patch_exact_apply_passed']
assert inv['explicit_named_file_count']==len(inv['files'])==113
assert pres['checked_occurrences']==len(pres['occurrences'])==296 and pres['all_expected_pins_unchanged']
for item in pres['occurrences']:assert item['expected']==item['actual']==pin(Path(item['expected']['path']))
for item in package['files']:
 assert item['source']==pin(Path(item['source']['path'])) and item['packaged']==pin(Path(item['packaged']['path']))
 assert item['source']['sha256']==item['packaged']['sha256']
for item in inv['files']+tests['sources_after']+review['read_pins']:assert item==pin(Path(item['path']))
save(Y/'preservation-final.json',{**pres,'schema':'terminal-semantic-context-budget-final-preservation@1'})
names=['preservation-baseline.json','baseline-manifest.json','test-basis.json','boundary-review-criteria.json',
 'boundary-source-review.json','entrypoint-model-input-review.json','qualification-report.json','improvement-status.json',
 'development-history.json','qualification-claims-review.json','actual-public-inventory.json','preservation-before-package.json','preservation-final.json',
 'package-report.json','stage-y.patch','env_run.py','qualify_current.py','run_current.py','report_current.py',
 'package_current.py','inventory_current.py','run_unit_suite.py','seal_current.py','test-final.xml','test-final-run.json',
 'context-budget-focused-report.json','context-budget-atomic-followup-report.json',
 'agent-semantic-budget-delivery-00-setupfailure.json','agent-semantic-budget-delivery-01.xml',
 'agent-semantic-budget-delivery-01-run.json','independent-review.py','independent-review.json']
paths={Y/name for name in names}
paths.add(Path(base['sealed_predecessor']['path']))
paths.update(Path(x['path']) for x in base['dependencies']+inv['files'])
for item in package['files']:
 paths.add(Path(item['source']['path']));paths.add(Path(item['packaged']['path']))
for i in range(1,5):
 paths.add(Y/f'budget-focused-{i:02d}'/'tests.xml');paths.add(Y/f'budget-focused-{i:02d}'/'run.log')
# A failed preliminary run is retained only as excluded development evidence.
paths.add(Y/'preview-run-01/expanded-trace.json');paths.add(Y/'preview-run-01/view-trace.json')
selected=['intent-profile.json','policy.json','query.json','checked-call-capsule.json',
 'observed-manifest.json','native-semantic-capsules.json','code-views.json','pre-capacity-binding.json',
 'capacity.json','audit-view.json','budget-binding.json','budget-policy.json','expanded-packet.json','view-packet.json',
 'expanded-preview.json','view-preview.json','expanded-initial-delivery.json','view-initial-delivery.json',
 'view-block-delivery.json','expanded-trace.json','view-trace.json','failed-retry-delivery.json',
 'failure-trace.json','proof-mutation-failure-trace.json','late-input-failure-trace.json','summary.json']
for label in ('failure','custody','late'):
 selected.extend(label+'-'+name for name in ('capacity.json','budget-binding.json','audit-view.json','view-packet.json'))
selected.extend(f'control-{i:02d}.json' for i in range(1,14))
paths.update(Y/'preview-run-02'/name for name in selected)
occurrences=[]
for name in ('expanded-preview.json','view-preview.json'):
 v=read(Y/'preview-run-02'/name)
 occurrences.extend(v['producer']['files']);occurrences.extend(v['native_review']['producer']['files'])
 occurrences.extend(v['native_review']['capacity']['producer']['files'])
for name in ('expanded-initial-delivery.json','view-initial-delivery.json','view-block-delivery.json','failed-retry-delivery.json'):
 receipt=read(Y/'preview-run-02'/name)['receipt'];occurrences.extend(receipt['producer']['files'])
 if receipt['expansion_receipt']:occurrences.extend(receipt['expansion_receipt']['producer']['files'])
for name in ('query.json','checked-call-capsule.json'):
 occurrences.extend(read(Y/'preview-run-02'/name)['producer']['files'])
for item in occurrences:assert item==pin(Path(item['path']))
paths.update(Path(x['path']) for x in occurrences)
sig=lambda s:tuple(getattr(s,k) for k in ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))
witnesses=[]
try:
 files=[]
 for p in sorted(paths):
  assert p.is_absolute() and p.resolve(strict=True)==p
  assert p.suffix not in {'.duckdb','.wal','.parquet'} and '/cas/' not in str(p)
  fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK);before=os.fstat(fd)
  assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_uid==os.geteuid()
  with os.fdopen(os.dup(fd),'rb') as f:r=f.read(8*1024*1024+1)
  assert len(r)==before.st_size<=8*1024*1024 and sig(before)==sig(os.fstat(fd))==sig(p.lstat())
  row={'path':str(p),'bytes':len(r),'sha256':hashlib.sha256(r).hexdigest()};files.append(row)
  witnesses.append((p,fd,sig(before),row))
 manifest={'schema':'terminal-semantic-context-budget-evidence-manifest@1','stage':str(Y),
  'explicit_named_file_count':len(files),'files':files,'selected_run':'preview-run-02',
  'unique_tests':162,'live_negative_controls':13,'selected_qualification':pin(Y/'qualification-report.json'),
  'direct_producer_pin_occurrences':len(occurrences),'predecessor_preservation_occurrences':296,
  'preservation_deduplicated':False,'development_failures_retained_and_excluded':True,
  'public_inventory_only_no_recursive_storage_walk':True,'database_bodies_included':False,
  'private_cas_bodies_included':False,'ducklake_parquet_bodies_included':False,
  'authored_local_planning_input_text_included':True,'provider_or_worker_transcripts_included':False,
  'native_storage_verified_by_actual_cold_readback':True,'retained_file_witnesses_rechecked':True,
  'native_review_forecast_accepted':True,'admitted_execution_width':0,'production_admitted':False,
  'native_planning_renderer_used':True,'native_worker_observer_used':False,'full_supervisor_entrypoint_used':False,
  'initial_native_expanded_tokens':70977,'initial_native_view_tokens':47215,
  'view_plus_block_cumulative_rendered_tokens':95678,'fixed_cumulative_token_limit':100000,
  'global_task_budget_enforced':False,'durable_budget_resume_supported':False,
  'worker_launched':False,'loaded_module_code_attested':False,'transitive_dependency_closure_attested':False,
  'completion_authority':False,'omission_authority':False,'caller_record_origin_verified':False,
  'provider_calls':0,'provider_output_tokens':None,'provider_usage_measured':False,'provider_savings_measured':False,
  'cumulative_task_token_savings_measured':False,'training_steps':0,'source_body_executed':False,
  'runtime_behavior_verified':False,'source_to_model_equivalence_proved':False,
  'convergence_proved':False,'full_task_satisfaction':False}
 for p,fd,s,row in witnesses:
  assert sig(os.fstat(fd))==s==sig(p.lstat());os.lseek(fd,0,os.SEEK_SET)
  with os.fdopen(os.dup(fd),'rb') as f:r=f.read(8*1024*1024+1)
  assert len(r)==row['bytes'] and hashlib.sha256(r).hexdigest()==row['sha256']
  assert sig(os.fstat(fd))==s==sig(p.lstat())
 for item in pres['occurrences']:assert item['expected']==pin(Path(item['expected']['path']))
 for item in review['read_pins']:assert item==pin(Path(item['path']))
 raw=wire(manifest)
 with (Y/'evidence-manifest.json').open('xb') as f:f.write(raw)
 print(json.dumps({'sealed_files':len(files),'manifest_sha256':hashlib.sha256(raw).hexdigest(),
  'tests':162,'preserved_occurrences':296,'cumulative_view_tokens':95678}))
finally:
 for _,fd,_,_ in witnesses:os.close(fd)
