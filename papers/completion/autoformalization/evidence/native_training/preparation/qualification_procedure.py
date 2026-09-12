from pathlib import Path
import json,hashlib,shutil,importlib.util,copy,datetime,math
BASE=Path(__file__).resolve().parent
ref=json.loads((BASE/'encoder_preparation_frozen.private.json').read_text());root=Path(ref['assets_root']);private=Path(ref['private_root']);job=private/'job';out=private/'output'
DEST=BASE/'source_candidate/papers/completion/autoformalization';prep=DEST/'evidence/native_training/preparation';prep.mkdir(parents=True,exist_ok=False);(DEST/'data').mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):
 with p.open('x')as f:json.dump(obj,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
m=json.loads((job/'preprocessing_manifest.json').read_text());data=json.loads((out/'native_training_inputs.json').read_text());windows=json.loads((out/'window_inventory.json').read_text());sources={s:[json.loads(l)for l in (job/'inputs'/(s+'.sources.jsonl')).read_text().splitlines()if l.strip()]for s in ['train','selection']}
spec=importlib.util.spec_from_file_location('V',BASE/'verify_prepared_inputs.py');V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
assert sha(job/'preprocessing_manifest.json')==ref['manifest_sha256'];assert sha(job/'encode_train_selection.py')==ref['source_sha256']
for split in sources:assert sha(job/'inputs'/(split+'.sources.jsonl'))==m['inputs'][split]['sha256']
for rel,meta in m['model_files'].items():assert sha(root/'encoder'/rel)==meta['sha256']
for rel,meta in m['runtime']['copied_dependency_files'].items():assert sha(Path(ref['python_dependency_root'])/rel)==meta['sha256']
positive=V.verify(data,m,windows,sources,ref['manifest_sha256'])
controls=[]
for kind in ['missing_row','unexpected_id','altered_vector','nonfinite_vector','window_gap','wrong_source','gold_claim']:
 d=copy.deepcopy(data);w=copy.deepcopy(windows)
 if kind=='missing_row':d['rows'].pop()
 elif kind=='unexpected_id':d['rows'][0]['record_id']='constructed-invalid-id'
 elif kind=='altered_vector':d['rows'][0]['embedding_vector'][0]+=0.001
 elif kind=='nonfinite_vector':d['rows'][0]['embedding_vector'][0]=float('nan')
 elif kind=='window_gap':w['rows'][0]['windows'][0]['offset']=1
 elif kind=='wrong_source':d['rows'][0]['text_sha256']='0'*64
 elif kind=='gold_claim':d['rows'][0]['independent_gold']=True
 try:V.verify(d,m,w,sources,ref['manifest_sha256'])
 except (AssertionError,ValueError):controls.append({'case':kind,'rejected':True})
 else:raise AssertionError(kind)
assert len({r['embedding_vector_sha256']for r in data['rows']})==84
receipt=json.loads((out/'execution_receipt.json').read_text());status=json.loads((private/'execution_status.json').read_text());assert receipt['status']=='completed'and status['status']=='completed'and status['cleanup_exit_code']==0 and not status['container_state']['OOMKilled']
for n,meta in receipt['outputs'].items():assert sha(out/n)==meta['sha256']
for source,name in [(out/'native_training_inputs.json','data/native_training_inputs.json'),(out/'window_inventory.json','evidence/native_training/preparation/window_inventory.json'),(job/'preprocessing_manifest.json','evidence/native_training/preparation/preprocessing_manifest.json'),(job/'encode_train_selection.py','evidence/native_training/preparation/encode_train_selection.py'),(BASE/'verify_prepared_inputs.py','evidence/native_training/preparation/verify_prepared_inputs.py'),(BASE/'run_frozen_encoder.py','evidence/native_training/preparation/run_frozen_encoder.py')]:shutil.copy2(source,DEST/name)
shutil.copy2(BASE/'encoder_preparation_frozen.private.json',prep/'encoder_preparation_frozen.private.json')
attempts=[]
for i,p in enumerate([root]+[root/f'attempt-{i:03}'for i in range(2,6)],1):
 a=prep/'attempts'/f'{i:03}';a.mkdir(parents=True)
 for n in ['command.json','launch_binding.json','create.json','boundary.json','exit_state.json','cleanup.json','execution_status.json','stdout.log','stderr.log']:
  shutil.copy2(p/n,a/n)
 shutil.copy2(p/'output/execution_receipt.json',a/'execution_receipt.json')
 if i<5:shutil.copy2(p/'job/preprocessing_manifest.json',a/'preprocessing_manifest.json')
 e=json.loads((p/'output/execution_receipt.json').read_text());s=json.loads((p/'execution_status.json').read_text());assert s['cleanup_exit_code']==0
 attempts.append({'attempt':i,'status':e['status'],'phase':'successful_encoder_preparation'if i==5 else'failed_before_inference','process_wall_seconds':e['elapsed_seconds'],'process_cpu_seconds':e['cpu_seconds'],'container_attach_wall_seconds':s['wall_seconds'],'peak_rss_bytes':e['peak_rss_bytes'],'new_model_api_calls':e['new_model_api_calls'],'error':e.get('error'),'execution_receipt_sha256':sha(a/'execution_receipt.json'),'boundary_sha256':sha(a/'boundary.json'),'cleanup_sha256':sha(a/'cleanup.json')})
cost={'schema':'af-native-training-preparation-costs/v1','attempts':attempts,'sum_nonoverlapping_process_wall_seconds':sum(a['process_wall_seconds']for a in attempts),'sum_process_cpu_seconds':sum(a['process_cpu_seconds']for a in attempts),'sum_container_attach_wall_seconds':sum(a['container_attach_wall_seconds']for a in attempts),'nested_cost_rule':'container attach wall includes process wall; never add those two quantities','asset_copy_setup_cost':{'status':'unmeasured','value':None,'reason':'no independent timer retained for asset staging or source review'},'successful_encoder_process_wall_seconds':receipt['elapsed_seconds'],'successful_encoder_cpu_seconds':receipt['cpu_seconds'],'preparation_run_once_shared_across_training_seeds':True,'charged_provider_cost':0,'provider_calls':0,'currency_cost':None,'fitting_updates':0,'future_AF029_training_costs_not_included':True}
save(prep/'cost_receipt.json',cost)
q={'schema':'af-native-training-input-qualification/v1','completed':True,'qualified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest_sha256':ref['manifest_sha256'],'input_artifact_sha256':sha(out/'native_training_inputs.json'),'producer_sha256':ref['source_sha256'],'verifier_sha256':sha(BASE/'verify_prepared_inputs.py'),'positive':positive,'negative_controls':controls,'unique_vectors':84,'model_files_verified':len(m['model_files']),'runtime_dependency_files_verified':len(m['runtime']['copied_dependency_files']),'real_offline_encoder_execution':True,'container_exit_code':0,'all_five_containers_removed':True,'input_population_unchanged':True,'grouping_vectors_reused':False,'final_sources_or_labels_accessed':False,'no_source_gold_or_compiler_target_credit':True,'scientific_training_completed':False}
save(prep/'qualification.json',q)
print(json.dumps({'inputs_sha256':sha(DEST/'data/native_training_inputs.json'),'manifest_sha256':ref['manifest_sha256'],'qualification_sha256':sha(prep/'qualification.json'),'counts':positive,'costs':{k:v for k,v in cost.items()if k.startswith('sum_')}}))
