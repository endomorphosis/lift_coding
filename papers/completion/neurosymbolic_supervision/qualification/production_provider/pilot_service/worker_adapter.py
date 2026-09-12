"""NS028 pilot handoff only. Missing host input stays pending before local work."""
import hashlib,importlib.util,json,re
from pathlib import Path
PAPER=Path('papers/completion/neurosymbolic_supervision')
SERVICE=PAPER/'qualification/production_provider/pilot_service'
HOST_PACKAGE='243df6b66dd84fff5c825c31d4976b008660c697bf56a4a03cc3dea80f31b1ea'
CLIENT_SHA='da488a896c59c9e8fd03303ad9fb2bd81c6c1f9148e8d0782f6e5fd5baea5454'
UNITS={'ns-hist-05-dnspython','ns-hist-06-bottle','ns-hist-07-idna','ns-hist-08-protego'}
def require(ok,msg):
 if not ok:raise ValueError(msg)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def valid_sha(s):return type(s)is str and re.fullmatch('[0-9a-f]{64}',s)is not None

def client(root):
 path=Path(root)/SERVICE/'pilot_client.py';require(path.is_absolute()and path.resolve()==path and sha(path.read_bytes())==CLIENT_SHA,'approved pilot client changed')
 spec=importlib.util.spec_from_file_location('ns028_reviewed_pilot_client',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def configuration(root):
 cfg=json.loads((Path(root)/PAPER/'experiments/production_profile.json').read_text()).get('pilot_host_handoff')
 if cfg is None:return None
 require(cfg.get('schema')=='paper-ns-pilot-A-worker-profile/v1'and cfg.get('host_package_sha256')==HOST_PACKAGE and cfg.get('client_sha256')==CLIENT_SHA,'pilot profile source binding differs')
 require(cfg.get('planned_cells')==48 and cfg.get('enabled_cells')==4 and cfg.get('arm')=='A'and cfg.get('cache')=='local_cold'and cfg.get('record_kind')=='pilot'and cfg.get('final_admitted')is False,'pilot profile scope differs')
 require(cfg.get('offer_drop_relative')==str(SERVICE/'host_handoff/offer_drop.json'),'pilot drop location differs')
 return cfg

def offer_binding(root,task_id,arm,cache,repetition,record_kind):
 require(record_kind=='pilot'and task_id in UNITS,'only four frozen pilot units admitted')
 require(arm=='A'and cache=='local_cold'and repetition==0,'real mechanism/cache not implemented by pilot-A client')
 cfg=configuration(root)
 if cfg is None or cfg.get('offer_drop_sha256')is None or cfg.get('scientific_activation_review_sha256')is None:return None
 require(valid_sha(cfg['offer_drop_sha256'])and valid_sha(cfg['scientific_activation_review_sha256']),'invalid root activation binding')
 pc=client(root);raw=pc.read(Path(root)/cfg['offer_drop_relative']);require(sha(raw)==cfg['offer_drop_sha256'],'root offer drop changed');drop=json.loads(raw)
 require(drop.get('schema')=='ns028-pilot-A-offer-drop/v1'and drop.get('host_package_sha256')==HOST_PACKAGE and drop.get('client_sha256')==CLIENT_SHA and drop.get('scientific_activation_review_sha256')==cfg['scientific_activation_review_sha256'],'offer activation scope changed')
 require(drop.get('worker_root')==str(Path(root).resolve()),'offer belongs to a different worker workspace')
 base_profile=json.loads((Path(root)/PAPER/'experiments/production_profile.json').read_text());base_profile.pop('pilot_host_handoff',None)
 require(drop.get('base_profile_sha256')==sha(canon(base_profile)),'original development/profile binding changed')
 required={str(PAPER/'experiments'/name)for name in ('production_gateway.py','run_comparison.py','score_runs.py')}|{str(SERVICE/name)for name in ('worker_adapter.py','pilot_client.py')}
 require(set(drop.get('worker_source_files',{}))==required,'worker source inventory differs')
 for name,digest in drop['worker_source_files'].items():
  require(valid_sha(digest)and sha(pc.read(Path(root)/name))==digest,'reviewed worker source changed: '+name)
 require(drop.get('planned_cells')==48 and drop.get('final_admitted')is False and len(drop['bindings'])==4 and {b['unit']for b in drop['bindings']}==UNITS,'pilot offer population changed')
 for b in drop['bindings']:
  require(b.get('batch_sha256')==drop['batch_sha256']and b.get('record_kind')=='pilot'and b.get('arm')=='A'and b.get('cache')=='local_cold'and b.get('repetition')==0,'drop includes unqualified scope')
 selected=[b for b in drop['bindings']if b['unit']==task_id];require(len(selected)==1,'ambiguous pilot grant')
 return {**selected[0],'task_id':task_id}

def verify(root,binding):
 selected=offer_binding(root,binding['task_id'],binding['arm'],binding['cache'],binding['repetition'],binding['record_kind']);require(selected==binding,'pilot grant/source/profile no longer admitted')
 return client(root).verify(root,binding)

def dispatch(root,request):
 binding=offer_binding(root,str(request['task_id']),str(request['arm']),str(request.get('cache','local_cold')),int(request.get('repetition',0)),str(request['record_kind']))
 if binding is None:return {'schema':'paper-ns-host-handoff-pending/v1','status':'pending_operator_inputs','terminal':False,'reason':'Awaiting reviewed root offer-drop/profile and pre-outcome scientific activation. No model, scorer or local historical materialization has run.','provider_dispatched_by_client':False}
 pc=client(root);queue,_=pc.selected(root,binding)
 # Durable final evidence is verified without trying to recreate its queue request.
 result=pc.verify(root,binding)if(queue/'response.json').exists()else pc.dispatch(root,binding)
 if result['schema']=='paper-ns-host-handoff-pending/v1':return {**result,'status':'pending_operator','grant_binding':binding,'provider_dispatched_by_client':False}
 body=result['receipt'];return {'schema':'paper-ns-host-historical-pilot/v1','status':'completed','admitted_historical_pilot':result['admitted_historical_pilot'],'admitted_production':False,'admitted_final':False,'dispatched':body.get('provider_dispatch_may_have_occurred')is True,'dispatch_confirmed':body.get('provider_invoked')is True,'served_provider':'grok','served_model':(body.get('provider_stream_metadata',{}).get('served_models')or[None])[0],'served_revision':None,'possibly_charged':body.get('unknown_external_charge')is True,'proposal_effect_count':1 if body.get('provider_dispatch_may_have_occurred')else 0,'host_verified':result}

def oracle(verified):
 body=verified['receipt'];score=body.get('scorer')or{};binding=body.get('operator_review_binding')or{}
 require(verified.get('signature_and_scope_verified')is True and verified.get('admitted_historical_pilot')is True and body.get('status')=='completed'and body.get('error')is None,'signed reviewed pilot score absent')
 require(body.get('operator_review_kind')=='ai_operator'and body.get('trust_scope')=='specific_reviewed_pilot_candidate_only'and body.get('automatic_adversarial_scorer_integrity_qualified')is False and body.get('production_final_admitted')is False,'pilot reviewer scope differs')
 require(body.get('operator_review_sha256')and all(binding.get(k)==body.get(k)for k in ('grant_sha256','candidate_sha256','source_sha256','batch_sha256','cell_id')),'review candidate/cell binding differs')
 require(score.get('schema')=='ns-historical-cold-host-result/v1'and score.get('split')=='pilot'and score.get('unit_id')==body['unit']and score.get('manifest_sha256')==body['manifest_sha256']and score.get('candidate_sha256')==body['candidate_sha256'],'cold score identity differs')
 details=score.get('scorer')or{};collected=all(type(details.get(k))is int and details[k]>0 for k in ('visible_collected','hidden_collected'));passed=score.get('success')is True and details.get('success')is True and score.get('container_exit_code')==0 and score.get('timed_out')is False
 return {'status':'passed'if passed and collected else'failed'if collected else'unavailable','independent_scorer_id':'operator-cold-scorer-reviewed-pilot','receipt_id':'sha256:'+verified['response_sha256'],'cold_full_validation':collected,'candidate_valid':passed if collected else None,'hidden_access_incident':False,'reason':'Exact signed cold score for this reviewed pilot-A candidate; no final comparison or adversarial scorer-integrity admission.','operator_review_sha256':body['operator_review_sha256'],'trust_scope':body['trust_scope'],'automatic_adversarial_scorer_integrity_qualified':False,'human_annotation':False,**{k:details.get(k)for k in ('visible_collected','visible_passed','hidden_collected','hidden_passed')}}
