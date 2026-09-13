"""Worker-side exact final offer/request and signed receipt verification.

No credential, model, Docker, historical source or oracle access. The caller must
load binding from the reviewed committed pilot profile, never a worker offer.
"""
import base64,hashlib,json,math,os,stat,subprocess,tempfile
from pathlib import Path
PREFIX=Path('papers/completion/neurosymbolic_supervision/qualification/production_provider/pilot_service/final_service/host_handoff')
REQUEST_KEYS={'schema','batch_sha256','cell_id','cache','repetition','record_kind','grant_sha256','grant_id','request_id','unit','arm','amendment_sha256','final_freeze_sha256'}
UNITS=('ns-hist-09-tomlkit','ns-hist-10-installer','ns-hist-11-tornado','ns-hist-12-more-itertools','ns-hist-13-charset_normalizer','ns-hist-14-iniconfig','ns-hist-15-wheel','ns-hist-16-jinja')
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def read(p):
 p=Path(p);require(p.is_absolute()and p.resolve()==p,'noncanonical handoff path')
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  info=os.fstat(fd);require(stat.S_ISREG(info.st_mode)and info.st_size<=1048576,'handoff file bound')
  with os.fdopen(fd,'rb',closefd=False)as f:return f.read(1048577)
 finally:os.close(fd)
def selected(root,binding):
 root=Path(root);rel=Path(binding['queue_relative']);require(not rel.is_absolute()and '..'not in rel.parts and rel.is_relative_to(PREFIX),'queue outside exact pilot reservation')
 queue=root/rel;raw=read(queue/'offer.json');require(sha(raw)==binding['offer_sha256'],'offer hash changed');offer=json.loads(raw);request=offer['request']
 require(set(request)==REQUEST_KEYS and request['schema']=='operator-final-request/v1'and request['record_kind']=='final'and request['arm']in('A','B')and request['cache']=='local_cold'and type(request['repetition'])is int and request['repetition']in(104729,130363)and request['unit']in UNITS,'pilot-AB request scope differs')
 expected_cell=sha(canon({k:request[k]for k in ('unit','arm','cache','repetition','record_kind')}))
 require(request['cell_id']==expected_cell,'request cell identity differs')
 for key in REQUEST_KEYS-{'schema','request_id'}:require(request[key]==binding[key],'host cell binding differs: '+key)
 require(offer['profile']==binding['profile']and offer['source_sha256']==binding['source_sha256'],'host source/profile differs')
 return queue,offer

def verify_signature(offer,signed):
 key=offer['public_verifier'];body=signed['receipt']
 require(set(key)=={'algorithm','encoding','data'}and key['algorithm']=='Ed25519'and key['encoding']=='spki_der_base64','unknown verifier')
 public=base64.b64decode(key['data'],validate=True);require(sha(public)==offer['public_key_sha256']==signed['public_key_sha256'],'public key differs')
 with tempfile.TemporaryDirectory(prefix='pilot-public-signature-')as t:
  p=Path(t);(p/'public.der').write_bytes(public);(p/'receipt').write_bytes(canon(body));(p/'signature').write_bytes(base64.b64decode(signed['signature'],validate=True))
  checked=subprocess.run(['/usr/bin/openssl','pkeyutl','-verify','-pubin','-keyform','DER','-rawin','-inkey',str(p/'public.der'),'-in',str(p/'receipt'),'-sigfile',str(p/'signature')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
  require(checked.returncode==0,'pilot signature invalid')
 return body

def receipt_scope(body,offer,binding):
 require(body['schema']=='operator-final-receipt/v1'and body['inert_qualification']is False and body['final_scientific_run']is True and body['production_final_admitted']is True and body['historical_population_admitted']is True,'non-pilot or inert receipt')
 for key in REQUEST_KEYS-{'schema','request_id'}:require(body[key]==offer['request'][key],'receipt cell differs: '+key)
 require(body['request_sha256']==sha(canon(offer['request']))and body['profile']==binding['profile']and body['source_sha256']==binding['source_sha256']and body['manifest_sha256']==binding['manifest_sha256'],'receipt source/request differs')

def resource_compliance(body,*,scoring=True):
 """Measured limits, without replacing raw stage observations or missing costs."""
 values=dict(body.get('proposal_resource_measurements')or{})
 limits={'provider_child_seconds':595,'http_wrapper_seconds':600,'gateway_proposal_seconds':600}
 if scoring:
  values['scorer_invocation_seconds']=body.get('score_elapsed_seconds')
  limits['scorer_invocation_seconds']=120
 unavailable=[];exceeded=[]
 for key,cap in limits.items():
  value=values.get(key)
  if type(value)not in(int,float)or not math.isfinite(value)or value<0:unavailable.append(key)
  elif value>cap:exceeded.append(key)
 return {'schema':'ns-final-measured-resource-compliance/v1','compliant':not unavailable and not exceeded,
         'measured_seconds':{k:values.get(k)for k in limits},'limits_seconds':limits,
         'exceeded':exceeded,'unavailable':unavailable,'missing_is_zero':False,
         'scope':'Actual signed phase clocks, separately nested; excludes preparation, operator review and client verification. No postprocessing exclusion inside measured gateway/wrapper phases.'}

def verify_disposition(offer,signed,original_raw,binding):
 """An additive terminal accounting record never converts its original to success."""
 original=verify_signature(offer,json.loads(original_raw));receipt_scope(original,offer,binding)
 d=verify_signature(offer,signed)
 require(d.get('schema')=='operator-final-failure-disposition/v1'and d.get('status')=='terminal_failed'and d.get('terminal')is True,'unknown disposition')
 require(d.get('original_receipt_sha256')==sha(original_raw),'original signed evidence changed')
 require(d.get('original_filename')in('proposal_result.json','result.json'),'unknown original evidence path')
 for key in ('grant_sha256','request_sha256','batch_sha256','cell_id','source_sha256','manifest_sha256','amendment_sha256'):
  require(d.get('binding',{}).get(key)==original.get(key),'disposition binding differs: '+key)
 require(d['binding'].get('profile_sha256')==sha(canon(original['profile'])),'disposition profile differs')
 require(d.get('provider_termination')==original.get('provider_termination')and d['provider_termination'].get('termination_proven')is True,'unknown provider termination remains blocked')
 require(d.get('preserved_original_body_sha256')==sha(canon(original)),'original cost/error/usage binding differs')
 require(d.get('new_provider_calls')==0 and type(d['new_provider_calls'])is int and d.get('new_scorer_calls')==0 and type(d['new_scorer_calls'])is int,'disposition cannot execute an effect')
 require(all(d.get(k)is False for k in ('retry_allowed','success_credit','score_credit','historical_final_unit_admitted','final_admitted','human_annotation')),'failure disposition overclaims authority')
 require(d.get('operator_record',{}).get('binding')==d['binding']and d['operator_record'].get('approved')is True and sha(canon(d['operator_record']))==d.get('operator_record_sha256'),'operator disposition record differs')
 record=d['operator_record'];require(record.get('schema')=='operator-final-failure-accounting-review/v1'and record.get('reviewer_kind')=='ai_operator'and record.get('scope')=='terminal_failure_accounting_only'and record.get('human_annotation')is False and record.get('final_admission')is False,'operator accounting scope differs')
 kind=d.get('classification');require(kind==record.get('classification'),'disposition class differs')
 if kind=='known_proposal_failure':
  require(d['original_filename']=='result.json'and original.get('status')=='operator_reconciliation_required'and original.get('error')is not None and original.get('scorer',{}).get('executed')is False,'not a known proposal failure')
 elif kind=='candidate_rejected':
  require(d['original_filename']=='proposal_result.json'and original.get('status')=='awaiting_operator_candidate_review'and original.get('error')is None and original.get('scorer',{}).get('executed')is False,'not a pending candidate')
  review=d.get('candidate_review',{});require(review.get('approved')is False and review.get('binding')==d['binding'].get('candidate_review_binding')and sha(canon(review))==d['binding'].get('candidate_review_sha256'),'exact rejected candidate review missing')
 elif kind=='known_scorer_failure':
  require(d['original_filename']=='result.json'and original.get('status')=='scorer_reconciliation_required'and original.get('error')is not None and d.get('scorer_termination',{}).get('termination_proven')is True,'unknown scorer termination remains blocked')
 else:raise ValueError('unsupported failure class')
 return original,d

def verify(root,binding):
 queue,offer=selected(root,binding)
 if(queue/'disposition.json').exists():
  raw=read(queue/'disposition.json');signed=json.loads(raw);d=signed['receipt']
  filename='proposal.json'if d.get('original_filename')=='proposal_result.json'else'response.json'
  body,d=verify_disposition(offer,signed,read(queue/filename),binding)
  return {'schema':'paper-ns-host-historical-final/v1','receipt':body,'binding':dict(binding),'response_sha256':sha(raw),'response_sha256_scope':'append_only_failure_disposition','signature_and_scope_verified':True,'admitted_historical_final':False,'admitted_final':False,'useful_completion':False,'terminal_failure':True,'failure_disposition':d,'host_measurements_scope':'all original signed stage values and unknown charges retained; disposition adds no experiment effects'}
 if not(queue/'response.json').exists():return pending(binding)
 raw=read(queue/'response.json');signed=json.loads(raw);body=verify_signature(offer,signed);receipt_scope(body,offer,binding)
 completed=body.get('status')=='completed'and body.get('error')is None
 if not completed:return pending(binding)
 require(body.get('operator_review_kind')=='ai_operator'and body.get('trust_scope')=='specific_reviewed_final_candidate_only'and body.get('operator_review_sha256')and body.get('automatic_adversarial_scorer_integrity_qualified')is False,'exact candidate review absent')
 score=body['scorer'];require(score['schema']=='ns-historical-cold-host-result/v1'and score['split']=='final'and score['unit_id']==body['unit']and score['candidate_sha256']==body['candidate_sha256']and score['manifest_sha256']==body['manifest_sha256'],'cold score differs')
 require(body.get('served_profile_admitted')is True and body.get('historical_final_unit_admitted')is True and body.get('provider_invoked')is True and body.get('provider_termination',{}).get('termination_proven')is True,'actual served and terminated proposal missing')
 compliance=resource_compliance(body)
 require(body.get('resource_compliance')==compliance,'signed resource summary differs from its measured values')
 return {'schema':'paper-ns-host-historical-final/v1','receipt':body,'binding':dict(binding),'response_sha256':sha(raw),'signature_and_scope_verified':True,'admitted_historical_final':True,'admitted_final':True,'native_task_completed':False,'useful_completion':bool(score.get('success')is True and compliance['compliant']),'resource_compliance':compliance,'host_measurements_scope':'use signed remote stage values; client verification CPU is separate; measured budget failures receive no useful-success credit'}

def pending(binding):
 return {'schema':'paper-ns-host-handoff-pending/v1','batch_sha256':binding['batch_sha256'],'cell_id':binding['cell_id'],'terminal':False,'provider_invoked_by_client':False,'reason':'Awaiting scoring or exact append-only failure disposition; unresolved termination never publishes a terminal outcome.'}

def dispatch(root,binding):
 queue,offer=selected(root,binding);path=queue/'request.json';raw=canon(offer['request'])
 try:
  fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 except FileExistsError:require(read(path)==raw,'existing request differs; do not replace')
 else:
  with os.fdopen(fd,'wb')as f:f.write(raw);f.flush();os.fsync(f.fileno())
  fd=os.open(queue,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(fd)
  finally:os.close(fd)
 if not(queue/'response.json').exists()and not(queue/'disposition.json').exists():return pending(binding)
 return verify(root,binding)
