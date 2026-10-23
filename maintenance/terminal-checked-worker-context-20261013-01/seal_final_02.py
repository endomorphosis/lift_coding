"""Seal explicitly named public evidence after independent review; no jobs."""
import hashlib,json,os,sys
from pathlib import Path
from inventory_current import Retained,write_exclusive
Z=Path(__file__).resolve().parent;os.umask(0o077)
def load(name):return json.loads((Z/name).read_bytes())
def allowed(path):
 return path.is_absolute() and not set(path.parts)&{'cas','lake','.git'} and path.suffix not in {'.duckdb','.db','.sqlite','.sqlite3','.parquet','.wal'}
def verify_only():
 m=load('evidence-manifest.json');r=Retained()
 try:
  for p in m['files']:assert allowed(Path(p['path']));r.read(p['path'],p)
  r.recheck();print(json.dumps({'verified':True,'files':len(m['files']),'manifest_sha256':hashlib.sha256((Z/'evidence-manifest.json').read_bytes()).hexdigest(),'read_only':True}))
 finally:r.close()
if sys.argv[1:]==['--verify']:
 verify_only();raise SystemExit(0)
review=load('independent-review.json')
assert review.get('passed') is True or review.get('qualified') is True, 'independent review must pass before sealing'
r=Retained();files={};occurrences=0;private_descriptors=0;container_descriptors=0;system_toolchain_descriptors=0
def capture(path,expected=None):
 global occurrences
 path=Path(path);assert allowed(path),str(path)
 p,b=r.read(path,expected);occurrences+=1
 if str(path) in files:assert files[str(path)]==p
 files[str(path)]=p;return b
def declared(value):
 global private_descriptors,container_descriptors,system_toolchain_descriptors
 if isinstance(value,dict):
  if isinstance(value.get('path'),str) and Path(value['path']).is_absolute() and isinstance(value.get('sha256'),str) and ('bytes' in value or 'size_bytes' in value):
   path=Path(value['path'])
   if str(path)=='/usr/bin/python3.12':system_toolchain_descriptors+=1
   elif not allowed(path):private_descriptors+=1
   elif str(path).startswith(('/app/','/opt/ipfs-supervisor/')):container_descriptors+=1
   else:
    p={'path':str(path),'bytes':value.get('bytes',value.get('size_bytes')),'sha256':value['sha256'].removeprefix('sha256:')}
    capture(path,p)
  for child in value.values():declared(child)
 elif isinstance(value,list):
  for child in value:declared(child)
root_names='''preservation-baseline.json native-source-snapshot.json source-assets.json entrypoint-integration-review.json actual-public-inventory.json preservation-final.json final-runtime-update-03.json deployed-runtime-source-pins-02.json native-worker-public-readback-02.json native-task-final-readback-02.json container-disposal-02.json coding-input-comparison-02.json review-package-02.json final-combined-02-report.json qualification-report.json improvement-status.json development-history.json independent-review.json env_run.py qualify_current.py refresh_container.py run_checked_worker_04.py prepare_native_fixture_05.py run_boundary_current_02.py run_native_integration_tests.py run_final_combined_tests_02.py inventory_current.py write_final_reports.py count_coding_inputs_02.py final_container_readback_02.py independent-review.py seal_final.py seal_final_02.py sealer-successor-review.json checked-worker-run-02.log checked-worker-run-04.log offline-duckdb-prerequisite.json provision_offline_ducklake.py refresh_container_03.py native-fixture-04/result.json native-fixture-04/native-prepare.stderr'''.split()
run_names='''worker-01.stderr final-cleanup.stdout view-packet.json 01-snapshot.stderr native-semantic-capsules.json 03-snapshot-command.json budget-binding.json 06-snapshot.stdout 02-prepare-command.json expanded-packet.json native-budget-preparation.json cleanup.json 01-snapshot.stdout policy.json 08-historical-command.json final-cleanup.stderr control-02.json native-observation.json 05-snapshot-command.json worker-01-launch.json query.json 02-prepare.stdout checked-call-capsule.json observed-manifest.json intent-profile.json 04-snapshot.stdout native-preflight.json 06-snapshot-command.json 02-prepare.stderr 06-snapshot.stderr control-01.json final-cleanup.json 08-historical.stdout code-views.json audit-view.json budgeted-native-observation.json budget-policy.json 01-snapshot-command.json historical-replay.json transport-producer.json final-budget-state.json 04-snapshot-command.json 07-cleanup.stderr pre-capacity-binding.json 05-snapshot.stdout 05-snapshot.stderr 03-snapshot.stdout summary.json native-budget-trace.json 07-cleanup.stdout 04-snapshot.stderr worker-01.stdout 03-snapshot.stderr 08-historical.stderr 07-cleanup-command.json'''.split()
other_names='''native-fixture-05/public/source.gitbundle native-fixture-05/public/manifest.json native-fixture-05/public/graph.json native-fixture-05/public/admission.json native-fixture-05/public/materialization.json native-fixture-05/public/context-preparation.json native-fixture-05/public/task-readback.json native-fixture-05/public/native-prompt.txt native-fixture-05/public/native-capsule.json native-fixture-05/public/compilation-receipt.json native-fixture-05/public/instruction-descriptor.json native-fixture-05/public/context-bundle.json native-fixture-05/public/owner-receipt.json native-fixture-05/result.json native-worker-public-readback-02/checked-context.json native-worker-public-readback-02/public-instruction.json docker-boundary-02/result.json docker-boundary-02/launch.json docker-boundary-02/container-public-identity.json docker-boundary-02/final-public-identity.json docker-boundary-02/installation/installation.json docker-boundary-02/qualification/qualification.json docker-boundary-02/qualification/probe.log checked-worker-run-01/worker-01-launch.json checked-worker-run-01/worker-01.stdout checked-worker-run-01/worker-01.stderr checked-worker-run-01/cleanup-after-failure.json checked-worker-run-02/02-prepare-command.json checked-worker-run-02/02-prepare.stderr checked-worker-run-02/final-budget-state.json final-combined-02/results.xml final-combined-02/pytest.log'''.split()
try:
 for name in root_names+['checked-worker-run-04/'+n for n in run_names]+other_names:
  raw=capture(Z/name)
  if name.endswith('.json'):declared(json.loads(raw))
 for pin in load('actual-public-inventory.json')['files']:capture(pin['path'],pin)
 for occurrence in load('preservation-final.json')['occurrences']:capture(occurrence['actual']['path'],occurrence['actual'])
 for item in load('review-package-02.json')['sources']:
  declared(item)
 for item in load('source-assets.json')['files']:
  for key in ('source','target'):
   capture(item[key],{'path':item[key],'bytes':item['bytes'],'sha256':item['sha256']})
 # The public instruction is a separate signed source, outside the datasets' default build-directory index.
 capture(Z/'actual-public-checked-01/repository/build/task-instruction.txt')
 bpe=Path('/tmp/data-gym-cache')/hashlib.sha1(b'https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken').hexdigest()
 capture(bpe,{'path':str(bpe),'bytes':bpe.stat().st_size,'sha256':load('coding-input-comparison-02.json')['bpe_sha256']})
 for name in ['final-combined-01-report.json','final-combined-01/results.xml','checked-worker-run-03/summary.json','checked-worker-run-03.log']:
  capture(Z/name)
 r.recheck()
 m={'schema':'terminal-checked-worker-context-evidence-manifest@1','selected_run':'checked-worker-run-04','qualified':True,
  'explicit_named_file_count':len(files),'files':sorted(files.values(),key=lambda p:p['path']),
  'named_capture_occurrences':occurrences,'preservation_occurrences':len(load('preservation-final.json')['occurrences']),
  'retained_file_witnesses_rechecked':True,'recursive_traversal':False,
  'private_storage_descriptors_retained_as_metadata_only':private_descriptors,
  'system_toolchain_descriptors_retained_as_metadata_only':system_toolchain_descriptors,
  'system_toolchain_metadata_only_paths':['/usr/bin/python3.12'],
  'sealer_successor_reason':'Original owned-public-file reader correctly refused root-owned system interpreter. Exact interpreter descriptors remain in independently checked public metadata; source/evidence custody policy is unchanged.',
  'container_path_descriptors_not_reinterpreted_as_host_files':container_descriptors,
  'database_bodies_included':False,'private_cas_bodies_included':False,'ducklake_parquet_bodies_included':False,
  'public_observer_stdout_included':True,'provider_transcripts_included':False,
  'native_worker_observer_used':True,'native_admitted_benchmark_runtime_START_used':False,
  'full_supervisor_entrypoint_used':False,'Terminal_Bench_harness_used':False,
  'actual_worker_observer_invocations':1,'provider_calls':0,'provider_usage_measured':False,
  'whole_coding_input_tokens':load('coding-input-comparison-02.json')['observed']['tokens'],'expanded_counterfactual_tokens':load('coding-input-comparison-02.json')['expanded_counterfactual']['tokens'],'local_input_token_difference':load('coding-input-comparison-02.json')['local_input_token_difference'],
  'counterfactual_dispatched':False,'provider_or_task_billing_savings_measured':False,
  'global_task_budget_enforced':False,'durable_budget_resume_supported':False,
  'source_body_executed':False,'training_steps':0,'source_to_model_equivalence_proved':False,
  'convergence_proved':False,'full_task_satisfaction':False,'completion_authority':False,
  'proof_authority':False,'omission_authority':False,'production_admitted':False,
  'loaded_module_code_attested':False,'transitive_dependency_closure_attested':False,
  'project_pushes':0,'owned_experiment_container_removed':True,
  'selected_qualification':files[str(Z/'qualification-report.json')],
  'independent_review':files[str(Z/'independent-review.json')],
  'development_failures_retained_and_excluded':True}
 out=write_exclusive(Z/'evidence-manifest.json',m);r.recheck();print(json.dumps({'sealed':True,'files':len(files),'manifest':out}))
finally:r.close()
