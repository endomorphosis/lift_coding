#!/usr/bin/env python3
"""Protected real two-peer pubsub qualifier. Authored/unit data cannot mint live proof."""
from __future__ import annotations
import argparse,base64,contextlib,datetime as dt,hashlib,http.client,importlib,importlib.util,json,math,os,queue,re,secrets,socket,stat,sys,threading,time,uuid
from pathlib import Path
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[2]
SDK='external/ipfs_kit/ipfs_kit_py/assurance/pinned_pubsub.py'
BRIDGE='scripts/svf_backends/native_pubsub_backend.py'
SERVICE='scripts/svf_backends/native_kit_service.py'
OWNERSHIP='scripts/svf_backends/foundation_service_ownership.py'
OBSERVER='scripts/svf_backends/foundation_native_entrypoint.py'
REGISTRATION='config/swissknife_visual_functional_foundation_owners.json'
PROFILE='config/swissknife_visual_functional_supervisor.json'
OUTPUT='data/agent_supervisor/swissknife_visual_functional/tasks/SVF-043/qualification'
BASE_SDK='external/ipfs_kit/ipfs_kit_py/assurance/pinned_ipfs.py'
SOURCES=(SDK,BRIDGE,'scripts/svf_backends/owned_pubsub_peers.py',SERVICE,'swissknife/scripts/ipfs-kit-native-forwarder.cjs','swissknife/scripts/start-ipfs-kit-mcp-compat.cjs')
SDK_CLASS='ipfs_kit_py.assurance.pinned_pubsub.LivePinnedPubsubAdapter'
MAX_FRAME=16384
MAX_BYTES=65536
MAX_FRAMES=4
class QualificationError(ValueError):pass
def need(value,code):
 if not value:raise QualificationError(code)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def sha(data):return hashlib.sha256(data).hexdigest()
def bounded(path,limit=2097152):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  info=os.fstat(fd);need(stat.S_ISREG(info.st_mode) and 0<=info.st_size<=limit,'bounded_regular_file_required');data=os.read(fd,limit+1);need(len(data)<=limit,'file_grew');return data
 finally:os.close(fd)
def confined(root,relative):
 p=Path(relative);need(not p.is_absolute() and '..' not in p.parts,'source_path_invalid');out=root/p;need(out.resolve()==out and out.is_relative_to(root),'source_symlink_or_escape');return out
def snapshot_sources(root):return {rel:sha(bounded(confined(root,rel))) for rel in SOURCES}
def multibase(value):
 need(type(value) is str and 1<len(value)<=MAX_FRAME,'multibase_invalid')
 prefix,text=value[0],value[1:];need(prefix in 'uUmM','multibase_unsupported')
 url=prefix in 'uU';padded=prefix in 'UM';alphabet=r'[A-Za-z0-9_\-]*={0,2}' if url else r'[A-Za-z0-9+/]*={0,2}'
 need(re.fullmatch(alphabet,text) is not None and (padded or '=' not in text),'multibase_invalid')
 try:data=base64.b64decode(text+('' if padded else '='*((-len(text))%4)),altchars=b'-_' if url else None,validate=True)
 except Exception as exc:raise QualificationError('multibase_invalid') from exc
 expected=(base64.urlsafe_b64encode(data) if url else base64.b64encode(data)).decode();expected=expected if padded else expected.rstrip('=')
 need(text==expected,'multibase_noncanonical');return data
def encode_topic(topic):return 'u'+base64.urlsafe_b64encode(topic.encode()).decode().rstrip('=')
def strict_json(raw):
 def pairs(items):
  value={}
  for key,item in items:
   need(key not in value,'json_duplicate_key');value[key]=item
  return value
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(QualificationError('json_nonfinite')))
def validate_publish_arguments(value):
 need(type(value) is dict and set(value)=={'fixture_scope','topic','message_id','message','dry_run','correlation_id'},'publish_arguments_shape')
 need(value['fixture_scope']=='svf-pubsub-043' and value['dry_run'] is False,'publish_scope_or_preview')
 need(type(value['topic']) is str and re.fullmatch(r'svf\.pubsub\.[0-9a-f]{32}',value['topic']) is not None,'publish_topic_invalid')
 try:need(str(uuid.UUID(value['message_id']))==value['message_id'],'publish_message_id_invalid')
 except Exception as exc:raise QualificationError('publish_message_id_invalid') from exc
 need(type(value['message']) is str and 1<=len(value['message'].encode('utf8'))<=4096,'publish_message_bounds')
 need(type(value['correlation_id']) is str and 1<=len(value['correlation_id'])<=128 and re.fullmatch('[A-Za-z0-9:_-]+',value['correlation_id']) is not None,'publish_correlation_invalid')
 return value

def decode_frame(raw,*,sender,topic,data):
 need(type(raw) is bytes and 0<len(raw)<=MAX_FRAME and b'\x00' not in raw,'frame_bounds')
 try:frame=strict_json(raw.decode('utf-8'))
 except Exception as exc:raise QualificationError('frame_malformed') from exc
 need(type(frame) is dict and {'from','data','seqno','topicIDs'}<=set(frame) and set(frame)<={'from','data','seqno','topicIDs','signature','key'},'frame_shape')
 need(frame['from']==sender,'frame_sender_mismatch');need(type(frame['topicIDs']) is list and len(frame['topicIDs'])==1,'frame_topic_count')
 try:observed_topic=multibase(frame['topicIDs'][0]).decode('utf-8')
 except UnicodeError as exc:raise QualificationError('frame_topic_invalid') from exc
 need(observed_topic==topic,'frame_topic_mismatch');seqno=multibase(frame['seqno']);need(1<=len(seqno)<=32,'frame_seqno_bounds')
 actual=multibase(frame['data']);need(actual==data,'frame_data_mismatch')
 return {'sender_peer_id':sender,'topic':topic,'seqno_base64':base64.b64encode(seqno).decode(),'data_sha256':sha(actual),'data_bytes':len(actual),'raw_sha256':sha(raw)}
def tuple_of(frame):return {k:v for k,v in frame.items() if k!='raw_sha256'}
def raw_base64(value):
 need(type(value) is str and len(value)<=4*((MAX_FRAME+2)//3),'frame_base64_bounds')
 try:raw=base64.b64decode(value,validate=True)
 except Exception as exc:raise QualificationError('frame_base64_invalid') from exc
 need(base64.b64encode(raw).decode()==value,'frame_base64_noncanonical');return raw
def ack_bytes(message_id,topic,message,peers):
 return canonical({'schema':'swissknife.pubsub-ack.v1','message_id':message_id,'topic':topic,'message_sha256':sha(message),'sender_peer_id':peers[1]['node_id'],'receiver_peer_id':peers[0]['node_id']})
def validate_publish_acceptance(value):
 need(type(value) is dict and set(value)=={'accepted','durable','effect_kind','state','request_id','operation_id'} and value.get('accepted') is True and value.get('durable') is False and value.get('effect_kind')=='EXTERNAL_NOTIFY' and value.get('state')=='ACCEPTED','sdk_publish_not_nondurable_acceptance')
 need(not value.get('delivered') and value.get('delivery_state')!='delivered' and value.get('publication_allowed') is not False,'sdk_publish_ack_is_not_delivery')
 for field in ('request_id','operation_id'):need(type(value.get(field)) is str and 0<len(value[field])<=128,'sdk_publish_identity_missing')
 return value

def validate_peers(peers,root):
 need(type(peers) is list and len(peers)==2,'two_registered_peers_required')
 for i,p in enumerate(peers):
  need(type(p) is dict and p.get('role')=='ab'[i],'peer_role_invalid')
  need(p.get('api_url')==f'http://127.0.0.1:{5032+i}' and p.get('unit')==f'swissknife-visual-functional-pubsub-{p["role"]}.service','peer_endpoint_or_unit_invalid')
  need(type(p.get('node_id')) is str and re.fullmatch('[A-Za-z0-9]{16,128}',p['node_id']) is not None,'peer_node_id_invalid')
  need(type(p.get('pid')) is int and p['pid']>1 and type(p.get('start_ticks')) is str and p['start_ticks'].isdigit() and p.get('uid')==os.getuid(),'peer_process_invalid')
  repo=Path(p.get('repo_path',''));need(repo.is_absolute() and repo.is_relative_to(root/'data/agent_supervisor/swissknife_visual_functional/backends/native-pubsub') and '..' not in repo.parts,'peer_repo_invalid')
  need(p.get('swarm_multiaddr')==f'/ip4/127.0.0.1/tcp/{40032+i}/p2p/{p["node_id"]}','peer_swarm_invalid')
  need(type(p.get('cgroup')) is str and p['cgroup'].endswith('/'+p['unit']),'peer_cgroup_invalid')
  need(type(p.get('executable_path')) is str and Path(p['executable_path']).is_absolute() and re.fullmatch('[0-9a-f]{64}',p.get('executable_sha256','')) is not None,'peer_executable_invalid')
 need(len({p['node_id'] for p in peers})==len({p['pid'] for p in peers})==len({p['repo_path'] for p in peers})==2,'peers_not_distinct');return peers

def verify_kernel_peer(peer):
 proc=Path('/proc')/str(peer['pid']);before=(proc/'stat').read_text().rsplit(')',1)[1].split();need(before[0] not in ('Z','X') and before[19]==peer['start_ticks'] and proc.stat().st_uid==peer['uid'],'peer_process_changed')
 need(str((proc/'exe').resolve())==peer['executable_path'] and sha((proc/'exe').read_bytes())==peer['executable_sha256'],'peer_binary_changed')
 groups=(proc/'cgroup').read_text().splitlines();need('0::'+peer['cgroup'] in groups,'peer_cgroup_changed')
 env=dict(row.split(b'=',1) for row in (proc/'environ').read_bytes().split(b'\0') if b'=' in row);need(env.get(b'IPFS_PATH')==os.fsencode(peer['repo_path']),'peer_repo_changed')
 after=(proc/'stat').read_text().rsplit(')',1)[1].split();need(after[19]==before[19],'peer_pid_reused')

def validate_exchange(payload,*,message_id,topic,message,correlation,peers,sources,receiver_raw,ack_raw,replayed=False,now=None):
 need(type(payload) is dict,'exchange_shape');required={'schema','backend','success','accepted','durable','delivery_state','replayed','message_id','topic','message_sha256','sender_peer_id','receiver_peer_id','receiver_frame_base64','ack_frame_base64','native_provenance'}
 need(set(payload)==required,'exchange_shape')
 need(payload['schema']=='swissknife.native-pubsub-exchange.v1' and payload['backend']=='ipfs_kit_py.assurance.pinned_pubsub:live-kubo-http' and payload['success'] is True and payload['accepted'] is True and payload['durable'] is False and payload['delivery_state']=='delivered' and payload['replayed'] is replayed,'exchange_not_observed_delivery')
 need(payload['message_id']==message_id and payload['topic']==topic and payload['message_sha256']==sha(message),'exchange_message_mismatch')
 need(payload['sender_peer_id']==peers[0]['node_id'] and payload['receiver_peer_id']==peers[1]['node_id'],'exchange_peer_mismatch')
 ack=ack_bytes(message_id,topic,message,peers)
 observed=decode_frame(receiver_raw,sender=peers[0]['node_id'],topic=topic,data=message)
 acknowledged=decode_frame(ack_raw,sender=peers[1]['node_id'],topic=topic+'.ack',data=ack)
 claimed=decode_frame(raw_base64(payload['receiver_frame_base64']),sender=peers[0]['node_id'],topic=topic,data=message)
 claimed_ack=decode_frame(raw_base64(payload['ack_frame_base64']),sender=peers[1]['node_id'],topic=topic+'.ack',data=ack)
 need(tuple_of(observed)==tuple_of(claimed) and tuple_of(acknowledged)==tuple_of(claimed_ack),'implementation_raw_frames_differ')
 p=payload['native_provenance'];need(type(p) is dict,'pubsub_provenance_missing')
 expected={'schema':'swissknife.native-kit-pubsub-execution.v1','owner':'ipfs_kit_py','sdk_class':SDK_CLASS,'sdk_method':'pubsub_publish','sdk_source_sha256':sources[SDK],'bridge_source_sha256':sources[BRIDGE],'service_source_sha256':sources[SERVICE],'transport':'http','simulated':False,'cache_fallback':False,'effect_kind':'EXTERNAL_NOTIFY','durable':False,'state':'ACCEPTED','correlation_id':correlation,'work_complete':False,'completion_authority':False}
 need(set(p)==set(expected)|{'sdk_request_id','sdk_operation_id','observed_at'},'pubsub_provenance_shape')
 for key,value in expected.items():need(type(p.get(key)) is type(value) and p[key]==value,'pubsub_provenance_mismatch:'+key)
 for key in ('sdk_request_id','sdk_operation_id'):need(type(p.get(key)) is str and 0<len(p[key])<=128,'pubsub_provenance_identity')
 try:
  observed_time=dt.datetime.fromisoformat(p['observed_at'].replace('Z','+00:00'));need(observed_time.tzinfo is not None and observed_time.utcoffset()==dt.timedelta(0),'pubsub_provenance_time');stamp=observed_time.timestamp()
 except Exception as exc:raise QualificationError('pubsub_provenance_time') from exc
 need(abs((time.time() if now is None else now)-stamp)<=120,'pubsub_provenance_stale')
 return {'receiver':observed,'acknowledgement':acknowledged,'request_id':p['sdk_request_id'],'operation_id':p['sdk_operation_id']}

class HTTPFrames:
 """Independent protected Kubo NDJSON witness, never a candidate SDK wrapper."""
 def __init__(self,peer,topic,deadline):self.peer,self.topic,self.deadline=peer,topic,deadline;self.frames=[];self.error=None;self.ready=threading.Event();self.stopped=threading.Event();self.conn=None;self.sock=None;self.thread=None
 def start(self):
  self.thread=threading.Thread(target=self._read,name='protected-pubsub-witness',daemon=True);self.thread.start();need(self.ready.wait(min(10,max(.01,self.deadline-time.monotonic()))),'witness_open_timeout');need(self.error is None,'witness_open_failed');return self
 def _read(self):
  try:
   self.conn=http.client.HTTPConnection('127.0.0.1',int(self.peer['api_url'].rsplit(':',1)[1]),timeout=max(.1,self.deadline-time.monotonic()));self.conn.connect();self.sock=self.conn.sock
   self.conn.request('POST','/api/v0/pubsub/sub?'+urlencode({'arg':encode_topic(self.topic)}),body=b'');response=self.conn.getresponse();need(response.status==200,'witness_http_error');self.ready.set();total=0
   while not self.stopped.is_set() and time.monotonic()<self.deadline:
    line=response.readline(MAX_FRAME+1)
    if not line:break
    total+=len(line);need(len(line)<=MAX_FRAME and total<=MAX_BYTES and len(self.frames)<MAX_FRAMES,'witness_stream_bounds');self.frames.append(line)
  except Exception as error:
   if not self.stopped.is_set():self.error=type(error).__name__
  finally:self.ready.set()
 def first(self):
  while not self.frames and not self.error and time.monotonic()<self.deadline:time.sleep(.01)
  need(self.frames and not self.error,'witness_receive_missing');return self.frames[0]
 def close(self):
  self.stopped.set()
  if self.sock:
   try:self.sock.shutdown(socket.SHUT_RDWR)
   except OSError:pass
  if self.conn:self.conn.close()
  if self.thread:self.thread.join(2);need(not self.thread.is_alive(),'witness_cleanup_failed')

class SDKFrames:
 def __init__(self,client,topic,deadline,cancel):self.client,self.topic,self.deadline,self.cancel=client,topic,deadline,cancel;self.frames=[];self.error=None;self.ready=threading.Event();self.stopped=threading.Event();self.context=None;self.subscription=None;self.thread=None
 def start(self):
  self.context=self.client.subscribe(self.topic,deadline=self.deadline,cancel_event=self.cancel,max_frames=MAX_FRAMES,max_bytes=MAX_BYTES);self.subscription=self.context.__enter__();self.thread=threading.Thread(target=self._read,name='actual-sdk-pubsub-reader',daemon=True);self.thread.start();return self
 def _read(self):
  total=0
  try:
   for value in self.subscription:
    need(type(value) is dict and type(value.get('raw_frame')) is bytes,'sdk_raw_frame_missing');raw=value['raw_frame'];total+=len(raw);need(len(raw)<=MAX_FRAME and total<=MAX_BYTES and len(self.frames)<MAX_FRAMES,'sdk_stream_bounds');self.frames.append(raw)
    if self.stopped.is_set():break
  except Exception as error:
   if not self.stopped.is_set():self.error=type(error).__name__
 def first(self):
  while not self.frames and not self.error and time.monotonic()<self.deadline:time.sleep(.01)
  need(self.frames and not self.error,'sdk_receive_missing');return self.frames[0]
 def close(self):
  self.stopped.set()
  if self.subscription is not None:self.subscription.close();self.context.__exit__(None,None,None)
  if self.thread:self.thread.join(2);need(not self.thread.is_alive(),'sdk_subscription_cleanup_failed')

def rpc_envelope(params,*,audit=None,deadline=None):
 request_id='svf-pubsub:'+str(uuid.uuid4());body=canonical({'jsonrpc':'2.0','id':request_id,'method':'tools/call','params':params});need(len(body)<=16384,'rpc_input_bounds')
 remaining=30 if deadline is None else deadline-time.monotonic();need(remaining>0,'qualification_deadline');conn=http.client.HTTPConnection('127.0.0.1',18316,timeout=min(30,remaining))
 try:
  conn.request('POST','/mcp',body,{'Content-Type':'application/json'});response=conn.getresponse();raw=response.read(131073);need(response.status==200 and len(raw)<=131072,'rpc_response_bounds');value=strict_json(raw)
  if audit is not None:audit.setdefault('rpc',[]).append((body,raw))
  need(type(value) is dict and value.get('jsonrpc')=='2.0' and value.get('id')==request_id and not value.get('error') and type(value.get('result')) is dict,'rpc_identity_or_error');return body,raw,value['result']
 finally:conn.close()
def rpc(params,*,audit=None,deadline=None):
 body,raw,result=rpc_envelope(params,audit=audit,deadline=deadline);return body,raw,extract_payload(result)
def validate_refusal(result):
 need(type(result) is dict and result.get('isError') is True,'invalid_request_not_mcp_error')
 def inspect(value,depth=0):
  need(depth<=12,'refusal_result_depth')
  if type(value) is dict:
   need(not any(value.get(k) is True for k in ('success','accepted','delivered','durable')) and value.get('delivery_state')!='delivered' and value.get('state')!='COMMITTED','refusal_has_positive_claim')
   for item in value.values():inspect(item,depth+1)
  elif type(value) is list:
   need(len(value)<=256,'refusal_result_bounds')
   for item in value:inspect(item,depth+1)
 inspect(result);return True
def refusal_cases():
 cases=[]
 for name in ('unknown_scope','preview','wrong_topic','malformed_uuid','oversized_utf8','api_url','argv','path'):
  message_id=str(uuid.uuid4());topic='svf.pubsub.'+uuid.uuid4().hex;message=canonical({'schema':'swissknife.pubsub-message.v1','message_id':message_id,'nonce':secrets.token_hex(16)}).decode()
  args={'fixture_scope':'svf-pubsub-043','topic':topic,'message_id':message_id,'message':message,'dry_run':False,'correlation_id':'svf-pubsub-negative:'+str(uuid.uuid4())}
  update={'unknown_scope':{'fixture_scope':'unregistered-svf-scope'},'preview':{'dry_run':True},'wrong_topic':{'topic':'svf.refused.'+uuid.uuid4().hex},'malformed_uuid':{'message_id':'invalid-'+message_id},'oversized_utf8':{'message':'\U0001f642'*1025},'api_url':{'api_url':'http://127.0.0.1:5031'},'argv':{'argv':['/bin/true']},'path':{'path':'/not-an-authorized-fixture'}}[name]
  args.update(update);cases.append((name,args))
 return cases

def extract_payload(value):
 for _ in range(8):
  need(type(value) is dict and value.get('isError') is not True and value.get('success') is not False and value.get('ok') is not False and not value.get('error'),'mcp_owner_error')
  if value.get('schema')=='swissknife.native-pubsub-exchange.v1':return value
  if type(value.get('content')) is list:
   blocks=value['content'];need(len(blocks)==1 and blocks[0].get('type')=='json' and type(blocks[0].get('json')) is dict,'mcp_ambiguous_result');value=blocks[0]['json']
  else:need(type(value.get('result')) is dict,'mcp_native_payload_missing');value=value['result']
 raise QualificationError('mcp_native_payload_missing')

def protected_helper(root):
 registration=json.loads(bounded(confined(root,REGISTRATION)));need(registration.get('schema')=='swissknife.foundation-service-registration.v1' and registration.get('status')=='REGISTERED' and registration.get('root')==str(root),'protected_registration_required')
 pins=registration.get('protected_sha256',{});need(type(pins) is dict,'protected_registration_required')
 for relative in (OWNERSHIP,OBSERVER,'scripts/svf_backends/validate_pubsub_foundation.py'):
  need(pins.get(relative)==sha(bounded(confined(root,relative))),'protected_source_unpinned')
 location=confined(root,OWNERSHIP);spec=importlib.util.spec_from_file_location('svf_protected_foundation_ownership',location);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def protected_observer(root):
 registration=strict_json(bounded(confined(root,REGISTRATION)));need(registration.get('protected_sha256',{}).get(OBSERVER)==sha(bounded(confined(root,OBSERVER))),'observer_source_unpinned')
 spec=importlib.util.spec_from_file_location('svf_protected_foundation_observer',confined(root,OBSERVER));module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);return module

def verify_native_process(owner):
 need(type(owner) is dict and type(owner.get('pid')) is int and owner['pid']>1 and type(owner.get('start_ticks')) is str and owner['start_ticks'].isdigit() and re.fullmatch('[0-9a-f]{32}',owner.get('invocation_id','')) is not None,'native_process_identity_invalid')
 proc=Path('/proc')/str(owner['pid']);fields=(proc/'stat').read_text().rsplit(')',1)[1].split();need(fields[0] not in ('Z','X') and fields[19]==owner['start_ticks'] and proc.stat().st_uid==os.getuid(),'native_process_changed')
 need('0::'+owner['control_group'] in (proc/'cgroup').read_text().splitlines(),'native_cgroup_changed')
 env=dict(row.split(b'=',1) for row in (proc/'environ').read_bytes().split(b'\0') if b'=' in row);need(env.get(b'INVOCATION_ID')==owner['invocation_id'].encode(),'native_invocation_changed')
 need((proc/'stat').read_text().rsplit(')',1)[1].split()[19]==owner['start_ticks'],'native_pid_reused')

def ownership_capture(root,ownership,owner,sources,observer_sha,directory):
 path=Path(ownership.get('witness_path',''));need(path.is_absolute() and path.is_relative_to(directory) and path.resolve()==path,'ownership_witness_path');raw=bounded(path,131072);need(sha(raw)==ownership.get('witness_sha256'),'ownership_witness_hash');sealed=strict_json(raw)
 need(sealed.get('schema')=='swissknife.foundation-service-source-attestation.v1' and sealed.get('family')=='kit-pubsub' and sealed.get('expected_sources')==sources and sealed.get('work_complete') is False and sealed.get('completion_authority') is False,'ownership_witness_binding')
 need(any(type(p) is dict and all(type(p.get(k)) is type(owner[k]) and p[k]==owner[k] for k in ('pid','start_ticks','invocation_id')) for p in sealed.get('processes',[])),'ownership_witness_native_identity')
 lease=sealed.get('lease_id');birth=sealed.get('foreground_birth');need(type(lease) is str and 0<len(lease)<=128 and type(birth) is str and birth.isdigit(),'ownership_witness_lease_identity')
 descriptor=ownership.get('sdk_call_witness');need(type(descriptor) is dict and set(descriptor)=={'schema','family','invocation_id','capture','capture_id','observer_source'},'capture_descriptor_missing')
 need(canonical(descriptor)==canonical(sealed.get('sdk_call_witness')),'capture_descriptor_not_sealed')
 need(descriptor['schema']=='swissknife.foundation-sdk-call-capture-ref.v1' and descriptor['family']=='kit-pubsub' and descriptor['invocation_id']==owner['invocation_id'] and descriptor['observer_source']=={'path':OBSERVER,'sha256':observer_sha},'capture_descriptor_binding')
 return descriptor,lease,birth

def validate_capture(snapshot,*,owner,sources,observer_sha,descriptor,lease_id,foreground_birth,now=None):
 need(type(descriptor) is dict and descriptor.get('schema')=='swissknife.foundation-sdk-call-capture-ref.v1' and descriptor.get('family')=='kit-pubsub' and descriptor.get('invocation_id')==owner['invocation_id'] and descriptor.get('observer_source')=={'path':OBSERVER,'sha256':observer_sha},'capture_descriptor_binding')
 capture=snapshot.get('capture');need(type(capture) is dict and set(capture)=={'reference','value'},'sdk_trace_capture_missing');ref=capture['reference'];value=capture['value'];claimed=descriptor.get('capture')
 need(type(ref) is dict and set(ref)=={'path','sha256','bytes'} and type(claimed) is dict and set(claimed)=={'path','sha256','bytes','capture_id','expires_at'},'sdk_trace_capture_reference_shape')
 need(all(type(ref.get(k)) is type(claimed[k]) and ref[k]==claimed[k] for k in ('path','sha256','bytes')),'sdk_trace_capture_reference_binding')
 keys={'schema','capture_id','family','invocation_id','task_id','native_process','lease_id','foreground_birth','issued_at','expires_at','expected_sources','observational_only','completion_authority'}
 need(type(value) is dict and set(value)==keys and value['schema']=='swissknife.foundation-sdk-call-capture.v1','sdk_trace_capture_shape')
 need(value['family']=='kit-pubsub' and value['invocation_id']==owner['invocation_id'] and value['task_id']=='SVF-043' and canonical(value['native_process'])==canonical({k:owner[k] for k in ('pid','start_ticks')}),'sdk_trace_capture_owner')
 try:need(type(value['capture_id']) is str and str(uuid.UUID(value['capture_id']))==value['capture_id'],'sdk_trace_capture_id')
 except Exception as error:raise QualificationError('sdk_trace_capture_id') from error
 need(value['capture_id']==descriptor.get('capture_id')==claimed['capture_id'] and value['expires_at']==claimed['expires_at'],'sdk_trace_capture_reference_binding')
 need(type(value['lease_id']) is str and value['lease_id']==lease_id and type(value['foreground_birth']) is str and value['foreground_birth'].isdigit() and value['foreground_birth']==foreground_birth,'sdk_trace_capture_lease_binding')
 issued,expires=value['issued_at'],value['expires_at'];stamp=time.time() if now is None else now
 need(all(type(v) in (int,float) and math.isfinite(v) for v in (issued,expires,stamp)) and 0<expires-issued<=300 and issued<=stamp<=expires,'sdk_trace_capture_expired_or_unbounded')
 need(value['expected_sources']==sources and value['observational_only'] is True and value['completion_authority'] is False,'sdk_trace_capture_source_authority')
 need(snapshot.get('capture_faults')==[],'sdk_trace_capture_fault');return capture

def verify_capture_file(root,snapshot,owner):
 capture=snapshot['capture'];ref=capture['reference'];expected=root/'data/agent_supervisor/swissknife_visual_functional/backends/foundation-call-witness/kit-pubsub'/owner['invocation_id']/'capture.json';path=confined(root,ref['path']);need(path==expected,'sdk_trace_capture_path');info=path.lstat();need(info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o600,'sdk_trace_capture_permissions');raw=bounded(path,16384)
 need(len(raw)==ref['bytes'] and sha(raw)==ref['sha256'] and canonical(strict_json(raw))==canonical(capture['value']),'sdk_trace_capture_file_changed')

def snapshot_events(value,owner,sources,observer_sha,*,descriptor,lease_id,foreground_birth,now=None):
 need(type(value) is dict and value.get('schema')=='swissknife.foundation-sdk-call-snapshot.v1' and value.get('family')=='kit-pubsub' and value.get('invocation_id')==owner['invocation_id'],'sdk_trace_snapshot_identity')
 capture=validate_capture(value,owner=owner,sources=sources,observer_sha=observer_sha,descriptor=descriptor,lease_id=lease_id,foreground_birth=foreground_birth,now=now)
 need(value.get('observational_only') is True and value.get('completion_authority') is False,'sdk_trace_snapshot_authority')
 identity={'pid':owner['pid'],'start_ticks':owner['start_ticks']};need(canonical(value.get('identity'))==canonical(identity),'sdk_trace_process_identity')
 observed=value.get('observer');need(type(observed) is dict and observed.get('schema')=='swissknife.foundation-sdk-call-observer.v1' and observed.get('family')=='kit-pubsub' and observed.get('invocation_id')==owner['invocation_id'] and canonical(observed.get('identity'))==canonical(identity),'sdk_trace_observer_identity')
 need(observed.get('observer_sha256')==observer_sha and observed.get('source_sha256',{}).get(SDK)==sources[SDK] and observed.get('observational_only') is True and observed.get('authenticated_origin') is False and observed.get('completion_authority') is False,'sdk_trace_observer_binding')
 rows=value.get('events');need(type(rows) is list and len(rows)<=4096,'sdk_trace_event_bounds');events={};sequences=set()
 for row in rows:
  need(type(row) is dict and type(row.get('reference')) is dict and type(row.get('event')) is dict,'sdk_trace_event_shape');event=row['event'];ref=row['reference']
  need(type(ref.get('path')) is str and re.fullmatch('[0-9a-f]{64}',ref.get('sha256','')) is not None and type(ref.get('bytes')) is int and 1<=ref['bytes']<=24576,'sdk_trace_reference_shape')
  need(event.get('schema')=='swissknife.foundation-sdk-call-event.v1' and event.get('family')=='kit-pubsub' and event.get('invocation_id')==owner['invocation_id'] and type(event.get('pid')) is int and event['pid']==owner['pid'] and event.get('start_ticks')==owner['start_ticks'],'sdk_trace_event_identity')
  need(type(event.get('thread_id')) is int and event['thread_id']>0 and type(event.get('sequence')) is int and event['sequence']>0 and event['sequence'] not in sequences and type(event.get('monotonic_ns')) is int and event['monotonic_ns']>0,'sdk_trace_event_order')
  need(event.get('phase') in ('enter','return','error','stream') and type(event.get('call_id')) is str and re.fullmatch('[0-9a-f-]{36}',event['call_id']) is not None and event.get('observational_only') is True and event.get('completion_authority') is False,'sdk_trace_event_authority')
  sequences.add(event['sequence'])
  if event.get('capture_id')!=capture['value']['capture_id']:continue
  need(event.get('capture_sha256')==capture['reference']['sha256'],'sdk_trace_event_capture_binding');key=(event['call_id'],event['phase'],event['sequence']);need(key not in events,'sdk_trace_duplicate_event');events[key]=row
 return events

def verify_trace_files(root,snapshot,owner):
 verify_capture_file(root,snapshot,owner)
 runtime=root/'data/agent_supervisor/swissknife_visual_functional/backends/foundation-call-witness/kit-pubsub'/owner['invocation_id']/'events'
 for row in snapshot['events']:
  ref=row['reference'];path=Path(ref['path']);path=path if path.is_absolute() else root/path
  need(path.is_relative_to(runtime) and path.parent==runtime and path.resolve()==path,'sdk_trace_reference_escape');info=path.lstat();need(info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o600,'sdk_trace_reference_permissions');raw=bounded(path,24576);need(len(raw)==ref['bytes'] and sha(raw)==ref['sha256'] and canonical(strict_json(raw))==canonical(row['event']),'sdk_trace_reference_mismatch')

def validate_sdk_trace(before,after,*,owner,sources,observer_sha,capture_descriptor,lease_id,foreground_birth,message_id,topic,message,peers,joined,sdk_message,sdk_ack,started_ns,finished_ns,negative_arguments=(),now=None):
 prior=snapshot_events(before,owner,sources,observer_sha,descriptor=capture_descriptor,lease_id=lease_id,foreground_birth=foreground_birth,now=now);current=snapshot_events(after,owner,sources,observer_sha,descriptor=capture_descriptor,lease_id=lease_id,foreground_birth=foreground_birth,now=now)
 need(canonical(before['capture'])==canonical(after['capture']),'sdk_trace_capture_changed')
 for key,row in prior.items():need(key in current and canonical(current[key])==canonical(row),'sdk_trace_history_changed')
 events=[row['event'] for key,row in current.items() if key not in prior];need(events,'native_sdk_call_trace_missing')
 relevant=[]
 for event in events:
  if not started_ns<=event['monotonic_ns']<=finished_ns:continue
  sdk=event.get('sdk',{});args=event.get('arguments',{})
  if sdk.get('module')=='ipfs_kit_py.assurance.pinned_pubsub':
   need(sdk.get('class')=='LivePinnedPubsubAdapter' and sdk.get('source_path')==SDK and sdk.get('source_sha256')==sources[SDK] and re.fullmatch('[0-9a-f]{64}',sdk.get('code_sha256','')) is not None,'sdk_trace_source_binding');relevant.append(event)
 def calls(method,api,selected_topic,data=None):
  selected=[event for event in relevant if event['sdk'].get('method')==method and event.get('arguments',{}).get('api_url')==api and event.get('arguments',{}).get('topic')==selected_topic]
  if data is not None:selected=[event for event in selected if event['arguments'].get('data_sha256')==sha(data) and type(event['arguments'].get('data_bytes')) is int and event['arguments']['data_bytes']==len(data)]
  return selected
 def publish(api,selected_topic,data,request_id=None,operation_id=None):
  selected=calls('pubsub_publish',api,selected_topic,data);need(all(e['arguments'].get('message_id')==message_id for e in selected),'native_sdk_message_identity');enters=[e for e in selected if e['phase']=='enter'];need(len(enters)==1,'native_sdk_publish_enter_missing_or_duplicate');enter=enters[0]
  returns=[e for e in selected if e['phase']=='return' and e['call_id']==enter['call_id'] and e['monotonic_ns']>=enter['monotonic_ns']];need(len(returns)==1 and not any(e['phase']=='error' and e['call_id']==enter['call_id'] for e in relevant),'native_sdk_publish_return_missing')
  result=validate_publish_acceptance(returns[0].get('result'));need(request_id is None or result['request_id']==request_id,'native_sdk_request_identity');need(operation_id is None or result['operation_id']==operation_id,'native_sdk_operation_identity');return enter['call_id']
 def subscription(api,selected_topic,raw):
  selected=calls('subscribe',api,selected_topic);enters=[e for e in selected if e['phase']=='enter'];need(len(enters)==1,'native_sdk_subscription_missing_or_duplicate');enter=enters[0]
  streams=[e for e in selected if e['phase']=='stream' and e['call_id']==enter['call_id'] and e['monotonic_ns']>=enter['monotonic_ns'] and e.get('frame',{}).get('sha256')==sha(raw) and type(e['frame'].get('bytes')) is int and e['frame']['bytes']==len(raw)]
  need(len(streams)==1,'native_sdk_raw_stream_missing');return enter['call_id']
 ack=ack_bytes(message_id,topic,message,peers)
 # These events come from the independently identified native service, not gate's SDK probes.
 message_call=publish(peers[0]['api_url'],topic,message,joined['request_id'],joined['operation_id']);ack_call=publish(peers[1]['api_url'],topic+'.ack',ack)
 message_stream=subscription(peers[1]['api_url'],topic,sdk_message);ack_stream=subscription(peers[0]['api_url'],topic+'.ack',sdk_ack);need(len({message_call,ack_call,message_stream,ack_stream})==4,'native_sdk_call_ids_not_distinct')
 for args in negative_arguments:
  data=args['message'].encode();need(not any(e['sdk'].get('method')=='pubsub_publish' and e.get('arguments',{}).get('data_sha256')==sha(data) and e['arguments'].get('data_bytes')==len(data) for e in relevant),'rejected_request_reached_sdk_publish')
 return {'schema':'swissknife.pubsub-sdk-chain-join.v1','invocation_id':owner['invocation_id'],'capture_id':capture_descriptor['capture_id'],'capture_sha256':capture_descriptor['capture']['sha256'],'identity':after['identity'],'message_call_id':message_call,'ack_call_id':ack_call,'receiver_subscribe_call_id':message_stream,'ack_subscribe_call_id':ack_stream,'novel_events':len(events),'observer_sha256':observer_sha,'observational_only':True,'authenticated_origin':False,'completion_authority':False}

def write_artifact(directory,name,data):
 need(Path(name).name==name,'artifact_name_invalid');path=directory/name
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
 return {'path':str(path),'sha256':sha(data),'bytes':len(data)}
def independent_topic_peers(peer,topic):
 conn=http.client.HTTPConnection('127.0.0.1',int(peer['api_url'].rsplit(':',1)[1]),timeout=5)
 try:
  conn.request('POST','/api/v0/pubsub/peers?'+urlencode({'arg':encode_topic(topic)}),body=b'');response=conn.getresponse();raw=response.read(16385);need(response.status==200 and len(raw)<=16384,'independent_topic_peers_http');value=strict_json(raw)
  need(type(value) is dict and 'Strings' in value and (value['Strings'] is None or type(value['Strings']) is list),'independent_topic_peers_shape');peers=value['Strings'] or [];need(len(peers)<=16 and all(type(item) is str for item in peers),'independent_topic_peers_shape');return peers,raw
 finally:conn.close()

def independent_topic_ready(peer,topic,other,deadline):
 while time.monotonic()<deadline:
  observed,_=independent_topic_peers(peer,topic)
  if other in observed:return
  time.sleep(.1)
 raise QualificationError('independent_topic_peer_not_ready')

def topic_ready(client,peer,topic,other,deadline,cancel):
 while time.monotonic()<deadline:
  peers=client.pubsub_peers(topic,deadline=deadline,cancel_event=cancel);need(type(peers) is list and len(peers)<=16 and all(type(p) is str for p in peers),'sdk_peer_response_invalid')
  observed,_=independent_topic_peers(peer,topic)
  if other in peers and other in observed:return
  time.sleep(.1)
 raise QualificationError('actual_topic_peer_not_ready')

def _qualify(root,*,output_root,ensure,audit):
 helper=protected_helper(root);sources=snapshot_sources(root);base_before=sha(bounded(confined(root,BASE_SDK)));directory=output_root/('attempt-'+str(uuid.uuid4()));directory.mkdir(mode=0o700,parents=True,exist_ok=False);audit.update(directory=directory,sources=sources,captures=[])
 # Every runtime qualifier uses the protected caller/lease check, even when no reload is needed.
 need(ensure,'explicit_owned_service_admission_required');ownership=helper.ensure_owned_services(root,family='kit-pubsub',expected_sources=sources,output_dir=directory)
 peers=validate_peers(helper.inspect_registered_pubsub_peers(root),root);audit['peers']=peers
 for peer in peers:verify_kernel_peer(peer)
 need(ownership.get('expected_sources')==sources,'ownership_source_binding');native=ownership.get('native_process');verify_native_process(native);observer=protected_observer(root);observer_sha=sha(bounded(confined(root,OBSERVER)))
 capture_descriptor,lease_id,foreground_birth=ownership_capture(root,ownership,native,sources,observer_sha,directory)
 trace_before=observer.read_snapshot(root,family='kit-pubsub',invocation_id=native['invocation_id']);snapshot_events(trace_before,native,sources,observer_sha,descriptor=capture_descriptor,lease_id=lease_id,foreground_birth=foreground_birth);verify_trace_files(root,trace_before,native)
 sys.path.insert(0,str(root/'external/ipfs_kit'));sdk=importlib.import_module('ipfs_kit_py.assurance.pinned_pubsub');need(Path(sdk.__file__).resolve()==confined(root,SDK),'sdk_import_path_mismatch');need(snapshot_sources(root)==sources,'source_changed_before_sdk')
 clients=[]
 try:
  for peer in peers:clients.append(sdk.LivePinnedPubsubAdapter(api_url=peer['api_url'],timeout=10))
  for client in clients:need(client.simulated is False and client.live_provider is True and client.transport_kind=='http' and getattr(client,'_transport',None) is None,'injected_or_simulated_sdk')
  artifacts=[];deadline=time.monotonic()+30;cancel=threading.Event();message_id=str(uuid.uuid4());topic='svf.pubsub.'+uuid.uuid4().hex;message=canonical({'schema':'swissknife.pubsub-message.v1','message_id':message_id,'nonce':secrets.token_hex(16)});correlation='svf-pubsub:'+str(uuid.uuid4())
  clients[0].swarm_connect(peers[1]['swarm_multiaddr'],deadline=deadline,cancel_event=cancel)
  # A fresh unsubscribed topic demonstrates accepted HTTP publication is NOT delivery.
  empty_topic=topic+'.unsubscribed';sdk_empty=clients[0].pubsub_peers(empty_topic,deadline=deadline,cancel_event=cancel);http_empty,empty_before=independent_topic_peers(peers[0],empty_topic);need(sdk_empty==[] and http_empty==[],'fresh_topic_has_subscribers')
  unsubscribed_acceptance=validate_publish_acceptance(clients[0].pubsub_publish(empty_topic,message,deadline=deadline,cancel_event=cancel));http_empty,empty_after=independent_topic_peers(peers[0],empty_topic);need(http_empty==[],'unsubscribed_topic_changed')
  artifacts.append(write_artifact(directory,'unsubscribed-peers-before.json',empty_before));artifacts.append(write_artifact(directory,'unsubscribed-peers-after.json',empty_after))
  with contextlib.ExitStack() as stack:
   # Independent protected HTTP observers and real candidate SDK subscribers.
   def capture(obj):audit['captures'].append(obj);stack.callback(obj.close);obj.start();return obj
   sdk_probe=capture(SDKFrames(clients[1],topic+'.sdk',deadline,cancel));raw_probe=capture(HTTPFrames(peers[1],topic+'.sdk',deadline));topic_ready(clients[0],peers[0],topic+'.sdk',peers[1]['node_id'],deadline,cancel)
   accepted=validate_publish_acceptance(clients[0].pubsub_publish(topic+'.sdk',message,deadline=deadline,cancel_event=cancel))
   probe_a=decode_frame(raw_probe.first(),sender=peers[0]['node_id'],topic=topic+'.sdk',data=message);probe_b=decode_frame(sdk_probe.first(),sender=peers[0]['node_id'],topic=topic+'.sdk',data=message);need(tuple_of(probe_a)==tuple_of(probe_b),'sdk_and_independent_receive_differ')
   received=capture(HTTPFrames(peers[1],topic,deadline));acked=capture(HTTPFrames(peers[0],topic+'.ack',deadline));sdk_received=capture(SDKFrames(clients[1],topic,deadline,cancel));sdk_acked=capture(SDKFrames(clients[0],topic+'.ack',deadline,cancel));topic_ready(clients[0],peers[0],topic,peers[1]['node_id'],deadline,cancel)
   arguments=validate_publish_arguments({'fixture_scope':'svf-pubsub-043','topic':topic,'message_id':message_id,'message':message.decode(),'dry_run':False,'correlation_id':correlation})
   trace_start=time.monotonic_ns();request,response,payload=rpc({'name':'ipfs_pubsub_publish','arguments':arguments},audit=audit,deadline=deadline);receiver_raw=received.first();ack_raw=acked.first();sdk_message=sdk_received.first();sdk_ack=sdk_acked.first()
   joined=validate_exchange(payload,message_id=message_id,topic=topic,message=message,correlation=correlation,peers=peers,sources=sources,receiver_raw=receiver_raw,ack_raw=ack_raw)
   need(tuple_of(decode_frame(sdk_message,sender=peers[0]['node_id'],topic=topic,data=message))==tuple_of(joined['receiver']),'sdk_message_differs');need(tuple_of(decode_frame(sdk_ack,sender=peers[1]['node_id'],topic=topic+'.ack',data=ack_bytes(message_id,topic,message,peers)))==tuple_of(joined['acknowledgement']),'sdk_ack_differs')
   retry_request,retry_response,retry=rpc({'name':'ipfs_pubsub_publish','arguments':arguments},audit=audit,deadline=deadline);validate_exchange(retry,message_id=message_id,topic=topic,message=message,correlation=correlation,peers=peers,sources=sources,receiver_raw=receiver_raw,ack_raw=ack_raw,replayed=True)
   time.sleep(.5);need(len(received.frames)==1 and len(sdk_received.frames)==1,'duplicate_receiver_delivery')
   refusals=[];negative_arguments=[]
   for name,args in refusal_cases():
    negative_arguments.append(args);rejected=capture(HTTPFrames(peers[1],args['topic'],deadline));independent_topic_ready(peers[0],args['topic'],peers[1]['node_id'],deadline)
    bad_request,bad_response,bad_result=rpc_envelope({'name':'ipfs_pubsub_publish','arguments':args},audit=audit,deadline=deadline);validate_refusal(bad_result)
    need(time.monotonic()+.25<deadline,'qualification_deadline');time.sleep(.25);need(not rejected.frames and rejected.error is None,'rejected_request_delivered_to_peer');rejected.close()
    refs=[write_artifact(directory,'refusal-'+name+'-request.json',bad_request),write_artifact(directory,'refusal-'+name+'-response.json',bad_response)];artifacts.extend(refs);refusals.append({'case':name,'isError':True,'independent_receiver_events':0,'observation_window_ms':250,'artifacts':refs})
   trace_after=observer.read_snapshot(root,family='kit-pubsub',invocation_id=native['invocation_id']);verify_trace_files(root,trace_after,native)
   sdk_chain=validate_sdk_trace(trace_before,trace_after,owner=native,sources=sources,observer_sha=observer_sha,capture_descriptor=capture_descriptor,lease_id=lease_id,foreground_birth=foreground_birth,message_id=message_id,topic=topic,message=message,peers=peers,joined=joined,sdk_message=sdk_message,sdk_ack=sdk_ack,started_ns=trace_start,finished_ns=time.monotonic_ns(),negative_arguments=negative_arguments)
   artifacts.append(write_artifact(directory,'native-sdk-trace-before.json',canonical(trace_before)+b'\n'));artifacts.append(write_artifact(directory,'native-sdk-trace-after.json',canonical(trace_after)+b'\n'))
   for name,data in [('sdk-probe.raw.ndjson',raw_probe.first()),('sdk-probe-sdk.raw.ndjson',sdk_probe.first()),('receiver.raw.ndjson',receiver_raw),('receiver-sdk.raw.ndjson',sdk_message),('ack.raw.ndjson',ack_raw),('ack-sdk.raw.ndjson',sdk_ack),('mcp-request.json',request),('mcp-response.json',response),('mcp-retry-request.json',retry_request),('mcp-retry-response.json',retry_response)]:artifacts.append(write_artifact(directory,name,data))
 finally:
  cancel.set() if 'cancel' in locals() else None
  for client in clients:
   if callable(getattr(client,'close',None)):client.close()
 need(snapshot_sources(root)==sources and sha(bounded(confined(root,BASE_SDK)))==base_before and sha(bounded(confined(root,OBSERVER)))==observer_sha,'source_drift');verify_native_process(native)
 after=validate_peers(helper.inspect_registered_pubsub_peers(root),root)
 for before,current in zip(peers,after):
  for key in ('pid','start_ticks','node_id','repo_path','api_url','executable_sha256','cgroup'):need(before[key]==current[key],'peer_identity_changed')
  verify_kernel_peer(current)
 report={'schema':'swissknife.pubsub-foundation-qualification.v1','passed':True,'actual_live_sdk':True,'independent_receiver_http_witness':True,'message_id':message_id,'topic':topic,'message_sha256':sha(message),'sdk_publish_acceptance':accepted,'unsubscribed_publish_acceptance':unsubscribed_acceptance,'node_offline_bridge_recovery_qualified':False,'joined_observations':joined,'native_sdk_chain':sdk_chain,'canonical_mcp_refusals':refusals,'peers':peers,'source_sha256':sources,'base_storage_sdk_sha256':base_before,'ownership':ownership,'artifacts':artifacts,'duplicate_retry_unique_receiver_events':1,'dedup_observation_window_ms':500,'scope':'two-owned-peer foundation only; original chat UI/visual/policy/receipt gates remain','work_complete':False,'completion_authority':False}
 artifact=write_artifact(directory,'qualification.json',canonical(report)+b'\n');return {'schema':'swissknife.pubsub-foundation-capsule.v1','passed':True,'artifact':artifact,'source_sha256':sources,'work_complete':False,'completion_authority':False}

def qualify(root,*,output_root,ensure):
 audit={}
 try:return _qualify(root,output_root=output_root,ensure=ensure,audit=audit)
 except Exception as error:
  directory=audit.get('directory')
  if directory is not None:
   try:
    artifacts=[]
    for i,capture in enumerate(audit.get('captures',[])):
     for j,raw in enumerate(capture.frames):artifacts.append(write_artifact(directory,f'failure-stream-{i}-{j}.ndjson',raw))
    for i,(request,response) in enumerate(audit.get('rpc',[])):
     artifacts.append(write_artifact(directory,f'failure-rpc-{i}-request.json',request));artifacts.append(write_artifact(directory,f'failure-rpc-{i}-response.json',response))
    report={'schema':'swissknife.pubsub-foundation-failure.v1','passed':False,'error_code':str(error)[:200] if isinstance(error,QualificationError) else type(error).__name__,'source_sha256':audit.get('sources',{}),'peers':audit.get('peers',[]),'artifacts':artifacts,'work_complete':False,'completion_authority':False}
    error.failure_artifact=write_artifact(directory,'failure.json',canonical(report)+b'\n')
   except Exception:pass  # Diagnostic failure never replaces the original refusal.
  raise


def main(argv=None):
 parser=argparse.ArgumentParser();parser.add_argument('--profile',default=PROFILE);parser.add_argument('--ensure-owned-services',action='store_true');parser.add_argument('--verify',action='store_true');parser.add_argument('--output-root',default=OUTPUT);args=parser.parse_args(argv)
 try:
  need(args.verify and args.ensure_owned_services and args.profile==PROFILE and args.output_root==OUTPUT,'fixed_qualification_arguments_required');need(ROOT.resolve()==ROOT,'physical_checkout_required');out=confined(ROOT,args.output_root)
  print(json.dumps(qualify(ROOT,output_root=out,ensure=args.ensure_owned_services),sort_keys=True));return 0
 except Exception as error:print(json.dumps({'schema':'swissknife.pubsub-foundation-capsule.v1','passed':False,'error_code':str(error)[:200] if isinstance(error,QualificationError) else type(error).__name__,'failure_artifact':getattr(error,'failure_artifact',None),'work_complete':False,'completion_authority':False},sort_keys=True));return 1
if __name__=='__main__':raise SystemExit(main())
