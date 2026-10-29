"""Protected authored protocol tests. Never run services or mint live qualification."""
from pathlib import Path
import base64,copy,datetime as dt,importlib.util,io,json,os,tempfile,unittest,uuid
from contextlib import redirect_stdout
FILE=Path(__file__).resolve().parents[1]/'scripts/svf_backends/validate_pubsub_foundation.py'
spec=importlib.util.spec_from_file_location('protected_pubsub_gate',FILE);gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)

def encoded(data,prefix='u'):
 if prefix in 'uU':value=base64.urlsafe_b64encode(data).decode()
 else:value=base64.b64encode(data).decode()
 return prefix+(value if prefix in 'UM' else value.rstrip('='))
def frame(sender,topic,data,seq=b'\x00\x01'):
 return gate.canonical({'from':sender,'topicIDs':[encoded(topic.encode())],'data':encoded(data),'seqno':encoded(seq)})+b'\n'
def peers(root=Path('/owned')):
 return [{'role':letter,'api_url':f'http://127.0.0.1:{5032+i}','unit':f'swissknife-visual-functional-pubsub-{letter}.service','node_id':'12D3KooW'+letter*40,'pid':100+i,'start_ticks':str(1000+i),'uid':os.getuid(),'repo_path':str(root/'data/agent_supervisor/swissknife_visual_functional/backends/native-pubsub'/letter),'swarm_multiaddr':f'/ip4/127.0.0.1/tcp/{40032+i}/p2p/12D3KooW'+letter*40,'cgroup':f'/user.slice/swissknife-visual-functional-pubsub-{letter}.service','executable_path':'/owned/ipfs','executable_sha256':'a'*64} for i,letter in enumerate('ab')]
def fixture():
 p=peers();topic='svf.pubsub.'+'1'*32;message_id=str(uuid.UUID(int=12));message=gate.canonical({'schema':'swissknife.pubsub-message.v1','message_id':message_id,'nonce':'unit-unique-nonce'});correlation='svf-pubsub:unit';sources={name:str(i+1)*64 for i,name in enumerate(gate.SOURCES)};now=1700000000
 receive=frame(p[0]['node_id'],topic,message);ack=frame(p[1]['node_id'],topic+'.ack',gate.ack_bytes(message_id,topic,message,p))
 provenance={'schema':'swissknife.native-kit-pubsub-execution.v1','owner':'ipfs_kit_py','sdk_class':gate.SDK_CLASS,'sdk_method':'pubsub_publish','sdk_source_sha256':sources[gate.SDK],'bridge_source_sha256':sources[gate.BRIDGE],'service_source_sha256':sources[gate.SERVICE],'transport':'http','simulated':False,'cache_fallback':False,'effect_kind':'EXTERNAL_NOTIFY','durable':False,'state':'ACCEPTED','correlation_id':correlation,'observed_at':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),'sdk_request_id':'request-unit','sdk_operation_id':'operation-unit','work_complete':False,'completion_authority':False}
 payload={'schema':'swissknife.native-pubsub-exchange.v1','backend':'ipfs_kit_py.assurance.pinned_pubsub:live-kubo-http','success':True,'accepted':True,'durable':False,'delivery_state':'delivered','replayed':False,'message_id':message_id,'topic':topic,'message_sha256':gate.sha(message),'sender_peer_id':p[0]['node_id'],'receiver_peer_id':p[1]['node_id'],'receiver_frame_base64':base64.b64encode(receive).decode(),'ack_frame_base64':base64.b64encode(ack).decode(),'native_provenance':provenance}
 context=dict(message_id=message_id,topic=topic,message=message,correlation=correlation,peers=p,sources=sources,receiver_raw=receive,ack_raw=ack,now=now)
 return payload,context

def trace_fixture():
 payload,ctx=fixture();owner={'pid':512,'start_ticks':'321','invocation_id':'a'*32};observer_sha='b'*64;sequence=0;events=[]
 observer={'schema':'swissknife.foundation-sdk-call-observer.v1','family':'kit-pubsub','invocation_id':owner['invocation_id'],'identity':{'pid':owner['pid'],'start_ticks':owner['start_ticks']},'observer_sha256':observer_sha,'source_sha256':ctx['sources'],'observational_only':True,'authenticated_origin':False,'completion_authority':False}
 stamp=gate.time.time();lease_id=str(uuid.uuid4());foreground_birth='901';capture_id=str(uuid.uuid4());capture_value={'schema':'swissknife.foundation-sdk-call-capture.v1','capture_id':capture_id,'family':'kit-pubsub','invocation_id':owner['invocation_id'],'task_id':'SVF-043','native_process':observer['identity'],'lease_id':lease_id,'foreground_birth':foreground_birth,'issued_at':stamp-1,'expires_at':stamp+299,'expected_sources':ctx['sources'],'observational_only':True,'completion_authority':False};capture_raw=gate.canonical(capture_value)+b'\n';capture_ref={'path':'data/agent_supervisor/swissknife_visual_functional/backends/foundation-call-witness/kit-pubsub/'+owner['invocation_id']+'/capture.json','sha256':gate.sha(capture_raw),'bytes':len(capture_raw)};descriptor={'schema':'swissknife.foundation-sdk-call-capture-ref.v1','family':'kit-pubsub','invocation_id':owner['invocation_id'],'capture':{**capture_ref,'capture_id':capture_id,'expires_at':capture_value['expires_at']},'capture_id':capture_id,'observer_source':{'path':gate.OBSERVER,'sha256':observer_sha}}
 before={'schema':'swissknife.foundation-sdk-call-snapshot.v1','family':'kit-pubsub','invocation_id':owner['invocation_id'],'identity':observer['identity'],'observer':observer,'events':[],'capture':{'reference':capture_ref,'value':capture_value},'capture_faults':[],'observational_only':True,'completion_authority':False}
 def event(call_id,method,phase,api,topic,*,data=None,result=None,raw=None):
  nonlocal sequence
  sequence+=1;args={'api_url':api,'topic':topic}
  if data is not None:args.update(data_sha256=gate.sha(data),data_bytes=len(data),message_id=ctx['message_id'])
  value={'schema':'swissknife.foundation-sdk-call-event.v1','family':'kit-pubsub','invocation_id':owner['invocation_id'],'pid':owner['pid'],'start_ticks':owner['start_ticks'],'thread_id':9,'sequence':sequence,'call_id':call_id,'parent_call_id':None,'phase':phase,'capture_id':capture_id,'capture_sha256':capture_ref['sha256'],'at':'2026-10-27T00:00:00Z','monotonic_ns':100+sequence,'sdk':{'module':'ipfs_kit_py.assurance.pinned_pubsub','class':'LivePinnedPubsubAdapter','method':method,'source_path':gate.SDK,'source_sha256':ctx['sources'][gate.SDK],'code_sha256':'c'*64},'arguments':args,'result':result or {},'observational_only':True,'completion_authority':False}
  if raw is not None:value['frame']={'sha256':gate.sha(raw),'bytes':len(raw)}
  encoded=gate.canonical(value)+b'\n';events.append({'reference':{'path':'events/'+str(sequence)+'.json','sha256':gate.sha(encoded),'bytes':len(encoded)},'event':value})
 def publish(api,topic,data,request,operation):
  call=str(uuid.uuid4());result={'accepted':True,'durable':False,'effect_kind':'EXTERNAL_NOTIFY','state':'ACCEPTED','request_id':request,'operation_id':operation}
  event(call,'pubsub_publish','enter',api,topic,data=data);event(call,'pubsub_publish','return',api,topic,data=data,result=result)
 publish(ctx['peers'][0]['api_url'],ctx['topic'],ctx['message'],'request-unit','operation-unit')
 publish(ctx['peers'][1]['api_url'],ctx['topic']+'.ack',gate.ack_bytes(ctx['message_id'],ctx['topic'],ctx['message'],ctx['peers']),'ack-request','ack-operation')
 for peer,topic,raw in ((ctx['peers'][1],ctx['topic'],ctx['receiver_raw']),(ctx['peers'][0],ctx['topic']+'.ack',ctx['ack_raw'])):
  call=str(uuid.uuid4());event(call,'subscribe','enter',peer['api_url'],topic);event(call,'subscribe','stream',peer['api_url'],topic,raw=raw)
 after={**before,'events':events};kwargs={**{k:ctx[k] for k in ('message_id','topic','message','peers','sources')},'owner':owner,'observer_sha':observer_sha,'capture_descriptor':descriptor,'lease_id':lease_id,'foreground_birth':foreground_birth,'now':stamp,'joined':gate.validate_exchange(payload,**ctx),'sdk_message':ctx['receiver_raw'],'sdk_ack':ctx['ack_raw'],'started_ns':100,'finished_ns':200}
 return before,after,kwargs

class PubsubContract(unittest.TestCase):
 def test_valid_actual_frame_join_requires_both_receiver_and_ack(self):
  payload,ctx=fixture();observed=gate.validate_exchange(payload,**ctx);self.assertEqual(observed['receiver']['data_sha256'],gate.sha(ctx['message']));self.assertNotEqual(observed['receiver']['sender_peer_id'],observed['acknowledgement']['sender_peer_id'])
 def test_all_supported_multibase_encodings_are_canonical(self):
  for prefix in ('u','U','m','M'):
   with self.subTest(prefix=prefix):self.assertEqual(gate.multibase(encoded(b'actual\x00bytes',prefix)),b'actual\x00bytes')
 def test_noncanonical_or_malformed_multibase_rejected(self):
  for value in ('xabc','uYQ=','u!@@','mYQ==','Uab','mA','u'):
   with self.subTest(value=value),self.assertRaises(gate.QualificationError):gate.multibase(value)
 def test_missing_malformed_or_oversized_frame_rejected(self):
  _,ctx=fixture()
  for raw in (b'',b'{}',b'[]',b'not-json',b'\xff',b'\x00',b'x'*(gate.MAX_FRAME+1)):
   with self.subTest(raw=raw[:8]),self.assertRaises(gate.QualificationError):gate.decode_frame(raw,sender=ctx['peers'][0]['node_id'],topic=ctx['topic'],data=ctx['message'])
 def test_duplicate_json_keys_do_not_override_raw_event(self):
  _,ctx=fixture();raw=ctx['receiver_raw'].rstrip();raw=raw[:-1]+b',"data":"uZmFrZQ"}'
  with self.assertRaises(gate.QualificationError):gate.decode_frame(raw,sender=ctx['peers'][0]['node_id'],topic=ctx['topic'],data=ctx['message'])
 def test_wrong_peer_self_echo_wrong_topic_stale_and_wrong_bytes_fail(self):
  _,ctx=fixture()
  for sender,topic,data in ((ctx['peers'][1]['node_id'],ctx['topic'],ctx['message']),(ctx['peers'][0]['node_id'],ctx['topic']+'.old',ctx['message']),(ctx['peers'][0]['node_id'],ctx['topic'],b'old message')):
   with self.subTest(sender=sender,topic=topic),self.assertRaises(gate.QualificationError):gate.decode_frame(frame(sender,topic,data),sender=ctx['peers'][0]['node_id'],topic=ctx['topic'],data=ctx['message'])
 def test_multiple_topics_and_missing_seqno_fail(self):
  _,ctx=fixture();value=json.loads(ctx['receiver_raw'])
  for update in ({'topicIDs':value['topicIDs']*2},{'seqno':'u'},{'from':False},{'delivered':True}):
   raw=gate.canonical({**value,**update})
   with self.subTest(update=update),self.assertRaises(gate.QualificationError):gate.decode_frame(raw,sender=ctx['peers'][0]['node_id'],topic=ctx['topic'],data=ctx['message'])
 def test_delivered_flag_without_independent_raw_evidence_is_never_proof(self):
  payload,ctx=fixture()
  for name in ('receiver_raw','ack_raw'):
   broken={**ctx,name:b''}
   with self.subTest(name=name),self.assertRaises(gate.QualificationError):gate.validate_exchange(payload,**broken)
 def test_claimed_raw_event_must_match_independent_sender_topic_seqno_and_bytes(self):
  payload,ctx=fixture();payload['receiver_frame_base64']=base64.b64encode(frame(ctx['peers'][0]['node_id'],ctx['topic'],ctx['message'],b'new-sequence')).decode()
  with self.assertRaises(gate.QualificationError):gate.validate_exchange(payload,**ctx)
 def test_native_payload_identity_and_boolean_types_are_exact(self):
  payload,ctx=fixture()
  for key,value in (('success',1),('accepted',1),('durable',0),('replayed',0),('message_id',str(uuid.uuid4())),('message_sha256','0'*64),('delivery_state','queued'),('delivery_state','cancelled'),('delivery_state','offline'),('extra','anything')):
   with self.subTest(key=key,value=value),self.assertRaises(gate.QualificationError):gate.validate_exchange({**payload,key:value},**ctx)
 def test_sdk_source_process_claims_never_override_raw_or_source_fence(self):
  payload,ctx=fixture()
  for key,value in (('sdk_class','fake.SDK'),('sdk_method','echo'),('sdk_source_sha256','0'*64),('simulated',1),('cache_fallback',True),('durable',True),('state','COMMITTED'),('effect_kind','BACKEND_DURABLE'),('correlation_id','old')):
   broken=copy.deepcopy(payload);broken['native_provenance'][key]=value
   with self.subTest(key=key),self.assertRaises(gate.QualificationError):gate.validate_exchange(broken,**ctx)
 def test_stale_and_naive_provenance_times_fail(self):
  payload,ctx=fixture()
  for stamp in ('2020-01-01T00:00:00Z','2023-11-14T22:13:20','invalid'):
   broken=copy.deepcopy(payload);broken['native_provenance']['observed_at']=stamp
   with self.subTest(stamp=stamp),self.assertRaises(gate.QualificationError):gate.validate_exchange(broken,**ctx)
 def test_retry_joins_same_real_frames_and_requires_replayed_true(self):
  payload,ctx=fixture()
  with self.assertRaises(gate.QualificationError):gate.validate_exchange(payload,replayed=True,**ctx)
  payload['replayed']=True;gate.validate_exchange(payload,replayed=True,**ctx)
 def test_publish_http_ack_is_only_accepted_nondurable_notification(self):
  value={'accepted':True,'durable':False,'state':'ACCEPTED','effect_kind':'EXTERNAL_NOTIFY','request_id':'r','operation_id':'o'};self.assertEqual(gate.validate_publish_acceptance(value),value)
  for update in ({'durable':True},{'state':'COMMITTED'},{'effect_kind':'BACKEND_DURABLE'},{'delivered':True},{'delivery_state':'delivered'},{'accepted':1}):
   with self.subTest(update=update),self.assertRaises(gate.QualificationError):gate.validate_publish_acceptance({**value,**update})
 def test_fixed_wire_rejects_foreign_scope_preview_urls_paths_and_code(self):
  payload,ctx=fixture();value={'fixture_scope':'svf-pubsub-043','topic':ctx['topic'],'message_id':ctx['message_id'],'message':ctx['message'].decode(),'dry_run':False,'correlation_id':ctx['correlation']};gate.validate_publish_arguments(value)
  for update in ({'dry_run':True},{'dry_run':0},{'fixture_scope':'other'},{'topic':'public-global-topic'},{'message':'x'*4097},{'message_id':'not-uuid'},{'url':'http://foreign'},{'argv':['sh']},{'path':'/foreign'}):
   with self.subTest(update=str(update)[:80]),self.assertRaises(gate.QualificationError):gate.validate_publish_arguments({**value,**update})
 def test_owned_peer_roles_ports_repos_pids_and_node_ids_are_exact(self):
  value=peers();gate.validate_peers(value,Path('/owned'))
  for key,new in (('api_url','http://127.0.0.1:5031'),('role','b'),('unit','foreign.service'),('repo_path','/foreign'),('pid',True),('start_ticks','reused'),('swarm_multiaddr','/ip4/1.2.3.4/tcp/4001'),('cgroup','/foreign')):
   broken=copy.deepcopy(value);broken[0][key]=new
   with self.subTest(key=key),self.assertRaises(gate.QualificationError):gate.validate_peers(broken,Path('/owned'))
  for key in ('node_id','pid','repo_path'):
   broken=copy.deepcopy(value);broken[1][key]=broken[0][key]
   with self.subTest(duplicate=key),self.assertRaises(gate.QualificationError):gate.validate_peers(broken,Path('/owned'))
 def test_output_and_source_paths_refuse_escape_and_symlinks(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'link').symlink_to('/tmp')
   for path in ('../foreign','/tmp/foreign','link/foreign'):
    with self.subTest(path=path),self.assertRaises(gate.QualificationError):gate.confined(root,path)
 def test_missing_draft_or_unpinned_registration_cannot_import_candidate_sdk(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);p=root/gate.REGISTRATION;p.parent.mkdir();p.write_text('{}')
   with self.assertRaises(gate.QualificationError):gate.protected_helper(root)
   p.write_text(json.dumps({'schema':'swissknife.foundation-service-registration.v1','status':'REGISTERED','root':str(root),'protected_sha256':{}}))
   with self.assertRaises((gate.QualificationError,FileNotFoundError)):gate.protected_helper(root)
 def test_cli_without_explicit_owned_verify_admission_fails_before_any_live_work(self):
  for args in ([],['--verify'],['--verify','--ensure-owned-services','--profile','foreign.json']):
   output=io.StringIO()
   with self.subTest(args=args),redirect_stdout(output):code=gate.main(args)
   self.assertEqual(code,1);value=json.loads(output.getvalue());self.assertIs(value['passed'],False);self.assertIs(value['completion_authority'],False)
 def test_unobserved_sdk_or_http_stream_cannot_pass(self):
  peer=peers()[0];witness=gate.HTTPFrames(peer,'svf.pubsub.'+'1'*32,0)
  with self.assertRaises(gate.QualificationError):witness.first()
 def test_actual_refusal_cases_are_bounded_fresh_and_all_fail_protected_grammar(self):
  cases=gate.refusal_cases();self.assertEqual([name for name,args in cases],['unknown_scope','preview','wrong_topic','malformed_uuid','oversized_utf8','api_url','argv','path']);self.assertEqual(len({args['topic'] for _,args in cases}),len(cases))
  for name,args in cases:
   with self.subTest(name=name),self.assertRaises(gate.QualificationError):gate.validate_publish_arguments(args)
   self.assertLess(len(gate.canonical({'name':'ipfs_pubsub_publish','arguments':args})),16384)
 def test_actual_mcp_refusal_requires_error_boolean_and_no_nested_delivery(self):
  gate.validate_refusal({'isError':True,'content':[{'type':'json','json':{'success':False,'error':{'code':'invalid_arguments'}}}]})
  for value in ({},{'isError':1},{'isError':False},{'isError':True,'success':True},{'isError':True,'content':[{'type':'json','json':{'accepted':True}}]},{'isError':True,'result':{'delivery_state':'delivered'}}):
   with self.subTest(value=value),self.assertRaises(gate.QualificationError):gate.validate_refusal(value)
 def test_native_sdk_chain_joins_both_real_streams_and_publish_identities(self):
  before,after,kwargs=trace_fixture();joined=gate.validate_sdk_trace(before,after,**kwargs);self.assertEqual(joined['novel_events'],8);self.assertIs(joined['authenticated_origin'],False);self.assertNotEqual(joined['message_call_id'],joined['ack_call_id'])
 def test_native_trace_cannot_be_replaced_by_bridge_flags_or_old_snapshot(self):
  before,after,kwargs=trace_fixture()
  for current in ({**after,'events':[]},before):
   with self.subTest(current=current['events']),self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,current,**kwargs)
  with self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(after,after,**kwargs)
 def test_native_trace_wrong_pid_birth_invocation_source_or_authority_fails(self):
  before,after,kwargs=trace_fixture()
  updates=[('pid',True),('pid',999),('start_ticks','old'),('invocation_id','d'*32),('observational_only',False),('completion_authority',True)]
  for field,value in updates:
   broken=copy.deepcopy(after);broken['events'][0]['event'][field]=value
   with self.subTest(field=field),self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,broken,**kwargs)
  for field,value in (('class','Fake'),('source_path','/foreign/sdk.py'),('source_sha256','d'*64),('code_sha256','unknown')):
   broken=copy.deepcopy(after);broken['events'][0]['event']['sdk'][field]=value
   with self.subTest(sdk=field),self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,broken,**kwargs)
 def test_native_trace_ack_stream_and_publish_cannot_be_omitted(self):
  before,after,kwargs=trace_fixture()
  for i in range(len(after['events'])):
   broken={**after,'events':[row for index,row in enumerate(after['events']) if index!=i]}
   with self.subTest(missing=i),self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,broken,**kwargs)
 def test_native_trace_modified_raw_bytes_or_request_identity_fails(self):
  before,after,kwargs=trace_fixture()
  for i,field,value in ((1,'request_id','old'),(1,'operation_id','other'),(3,'durable',True)):
   broken=copy.deepcopy(after);broken['events'][i]['event']['result'][field]=value
   with self.subTest(i=i,field=field),self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,broken,**kwargs)
  for field,value in (('sha256','0'*64),('bytes',True)):
   broken=copy.deepcopy(after);broken['events'][-1]['event']['frame'][field]=value
   with self.subTest(frame=field),self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,broken,**kwargs)
 def test_native_trace_duplicate_publish_and_stale_window_fail(self):
  before,after,kwargs=trace_fixture();duplicate=copy.deepcopy(after);row=copy.deepcopy(duplicate['events'][0]);row['event']['sequence']=20;row['event']['call_id']=str(uuid.uuid4());duplicate['events'].append(row)
  with self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,duplicate,**kwargs)
  with self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,after,**{**kwargs,'started_ns':10000,'finished_ns':20000})
 def test_native_trace_rejected_payload_must_not_reach_public_publish(self):
  before,after,kwargs=trace_fixture();case={'topic':kwargs['topic'],'message':kwargs['message'].decode()}
  with self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,after,negative_arguments=[case],**kwargs)
 def test_native_trace_reference_hash_bytes_and_scoped_path_are_independent(self):
  before,after,kwargs=trace_fixture()
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);base=root/'data/agent_supervisor/swissknife_visual_functional/backends/foundation-call-witness/kit-pubsub'/kwargs['owner']['invocation_id']/'events';base.mkdir(parents=True);capture_path=root/after['capture']['reference']['path'];capture_path.write_bytes(gate.canonical(after['capture']['value'])+b'\n');capture_path.chmod(0o600)
   for i,row in enumerate(after['events']):
    raw=gate.canonical(row['event'])+b'\n';path=base/(str(i)+'.json');path.write_bytes(raw);path.chmod(0o600);row['reference']={'path':str(path),'sha256':gate.sha(raw),'bytes':len(raw)}
   gate.verify_trace_files(root,after,kwargs['owner']);path.write_bytes(b'{}')
   with self.assertRaises(gate.QualificationError):gate.verify_trace_files(root,after,kwargs['owner'])
   row['reference']['path']=str(root/'outside.json')
   with self.assertRaises(gate.QualificationError):gate.verify_trace_files(root,after,kwargs['owner'])
 def test_missing_capture_or_fault_cannot_grant_sdk_qualification(self):
  before,after,kwargs=trace_fixture()
  for update in ({'capture':None},{'capture_faults':[{'event':{'error_type':'OSError'}}]},{'capture_faults':None}):
   with self.subTest(update=update),self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,{**after,**update},**kwargs)
 def test_capture_binding_to_task_native_owner_lease_and_sources_is_exact(self):
  before,after,kwargs=trace_fixture()
  for field,value in (('task_id','SVF-044'),('lease_id',str(uuid.uuid4())),('foreground_birth','other'),('native_process',{'pid':True,'start_ticks':'321'}),('expected_sources',{}),('observational_only',False),('completion_authority',True)):
   broken=copy.deepcopy(after);broken['capture']['value'][field]=value
   with self.subTest(field=field),self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,broken,**kwargs)
 def test_capture_expired_future_or_unbounded_window_is_refused(self):
  before,after,kwargs=trace_fixture();stamp=kwargs['now']
  for issue,expiry in ((stamp-301,stamp-1),(stamp+1,stamp+300),(stamp-1,stamp+400),(True,stamp+299),(stamp-1,float('nan'))):
   broken=copy.deepcopy(after);broken['capture']['value'].update(issued_at=issue,expires_at=expiry);broken_kwargs=copy.deepcopy(kwargs);broken_kwargs['capture_descriptor']['capture']['expires_at']=expiry
   with self.subTest(issue=issue,expiry=expiry),self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,broken,**broken_kwargs)
 def test_event_from_other_capture_or_wrong_capture_sha_cannot_satisfy_trace(self):
  before,after,kwargs=trace_fixture()
  for key,value in (('capture_id',str(uuid.uuid4())),('capture_sha256','0'*64)):
   broken=copy.deepcopy(after)
   for row in broken['events']:row['event'][key]=value
   with self.subTest(field=key),self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,broken,**kwargs)
 def test_capture_reference_must_match_helper_and_actual_immutable_file(self):
  before,after,kwargs=trace_fixture();broken=copy.deepcopy(kwargs);broken['capture_descriptor']['capture']['sha256']='0'*64
  with self.assertRaises(gate.QualificationError):gate.validate_sdk_trace(before,after,**broken)
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);path=root/after['capture']['reference']['path'];path.parent.mkdir(parents=True);path.write_bytes(gate.canonical(after['capture']['value'])+b'\n');path.chmod(0o600);gate.verify_capture_file(root,after,kwargs['owner']);path.write_bytes(b'{}')
   with self.assertRaises(gate.QualificationError):gate.verify_capture_file(root,after,kwargs['owner'])
 def test_ownership_witness_source_and_native_birth_bind_capture_owner(self):
  before,after,kwargs=trace_fixture()
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);attempt=root/'attempt';attempt.mkdir();path=attempt/'ownership.json';value={'schema':'swissknife.foundation-service-source-attestation.v1','family':'kit-pubsub','processes':[kwargs['owner']],'expected_sources':kwargs['sources'],'lease_id':kwargs['lease_id'],'foreground_birth':kwargs['foreground_birth'],'sdk_call_witness':kwargs['capture_descriptor'],'work_complete':False,'completion_authority':False};raw=gate.canonical(value);path.write_bytes(raw)
   ownership={'witness_path':str(path),'witness_sha256':gate.sha(raw),'sdk_call_witness':kwargs['capture_descriptor']};actual=gate.ownership_capture(root,ownership,kwargs['owner'],kwargs['sources'],kwargs['observer_sha'],attempt);self.assertEqual(actual,(kwargs['capture_descriptor'],kwargs['lease_id'],kwargs['foreground_birth']))
   path.write_bytes(b'{}')
   with self.assertRaises(gate.QualificationError):gate.ownership_capture(root,ownership,kwargs['owner'],kwargs['sources'],kwargs['observer_sha'],attempt)
if __name__=='__main__':unittest.main(verbosity=2)
