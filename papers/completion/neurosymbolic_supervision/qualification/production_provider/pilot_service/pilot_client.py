"""Worker-side exact pilot offer/request and signed receipt verification.

No credential, model, Docker, historical source or oracle access. The caller must
load binding from the reviewed committed pilot profile, never a worker offer.
"""
import base64,hashlib,json,os,stat,subprocess,tempfile
from pathlib import Path
PREFIX=Path('papers/completion/neurosymbolic_supervision/qualification/production_provider/pilot_service/host_handoff')
REQUEST_KEYS={'schema','batch_sha256','cell_id','cache','repetition','record_kind','grant_sha256','grant_id','request_id','unit','arm','amendment_sha256'}
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
 require(set(request)==REQUEST_KEYS and request['schema']=='operator-pilot-request/v1'and request['record_kind']=='pilot'and request['arm']=='A'and request['cache']=='local_cold'and request['repetition']==0,'pilot-A request scope differs')
 for key in REQUEST_KEYS-{'schema','request_id'}:require(request[key]==binding[key],'host cell binding differs: '+key)
 require(offer['profile']==binding['profile']and offer['source_sha256']==binding['source_sha256'],'host source/profile differs')
 return queue,offer

def verify(root,binding):
 queue,offer=selected(root,binding);raw=read(queue/'response.json');signed=json.loads(raw);body=signed['receipt'];key=offer['public_verifier']
 require(set(key)=={'algorithm','encoding','data'}and key['algorithm']=='Ed25519'and key['encoding']=='spki_der_base64','unknown verifier')
 public=base64.b64decode(key['data'],validate=True);require(sha(public)==offer['public_key_sha256']==signed['public_key_sha256'],'public key differs')
 with tempfile.TemporaryDirectory(prefix='pilot-public-signature-')as t:
  p=Path(t);(p/'public.der').write_bytes(public);(p/'receipt').write_bytes(canon(body));(p/'signature').write_bytes(base64.b64decode(signed['signature'],validate=True))
  checked=subprocess.run(['/usr/bin/openssl','pkeyutl','-verify','-pubin','-keyform','DER','-rawin','-inkey',str(p/'public.der'),'-in',str(p/'receipt'),'-sigfile',str(p/'signature')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
  require(checked.returncode==0,'pilot signature invalid')
 require(body['schema']=='operator-pilot-receipt/v1'and body['inert_qualification']is False and body['final_scientific_run']is False and body['production_final_admitted']is False and body['historical_population_admitted']is False,'non-pilot or inert receipt')
 for key in REQUEST_KEYS-{'schema','request_id'}:require(body[key]==offer['request'][key],'receipt cell differs: '+key)
 require(body['request_sha256']==sha(canon(offer['request']))and body['profile']==binding['profile']and body['source_sha256']==binding['source_sha256']and body['manifest_sha256']==binding['manifest_sha256'],'receipt source/request differs')
 completed=body.get('status')=='completed'and body.get('error')is None
 if completed:
  require(body.get('operator_review_kind')=='ai_operator'and body.get('trust_scope')=='specific_reviewed_pilot_candidate_only'and body.get('operator_review_sha256')and body.get('automatic_adversarial_scorer_integrity_qualified')is False,'exact candidate review absent')
  score=body['scorer'];require(score['schema']=='ns-historical-cold-host-result/v1'and score['split']=='pilot'and score['unit_id']==body['unit']and score['candidate_sha256']==body['candidate_sha256']and score['manifest_sha256']==body['manifest_sha256'],'cold score differs')
  require(body.get('served_profile_admitted')is True and body.get('historical_pilot_unit_admitted')is True and body.get('provider_invoked')is True and body.get('provider_termination',{}).get('termination_proven')is True,'actual served and terminated proposal missing')
 return {'schema':'paper-ns-host-historical-pilot/v1','receipt':body,'binding':dict(binding),'response_sha256':sha(raw),'signature_and_scope_verified':True,'admitted_historical_pilot':completed,'admitted_final':False,'useful_completion':bool(completed and body['scorer'].get('success')is True),'host_measurements_scope':'use signed remote stage values; client verification CPU is separate'}

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
 if not(queue/'response.json').exists():return {'schema':'paper-ns-host-handoff-pending/v1','batch_sha256':binding['batch_sha256'],'cell_id':binding['cell_id'],'terminal':False,'provider_invoked_by_client':False}
 return verify(root,binding)
