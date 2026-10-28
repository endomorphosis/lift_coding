"""Explicit isolated observer fixtures; no service controls/RPC/browser/provider."""
from pathlib import Path
import contextlib,dataclasses,importlib.util,io,json,os,sys,tempfile,threading,time,unittest,uuid
from unittest.mock import patch
STAGE=Path(__file__).resolve().parents[1];SOURCE=STAGE/'scripts/svf_backends/foundation_native_entrypoint.py'
spec=importlib.util.spec_from_file_location('native_witness_subject',SOURCE);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
FIXTURE='''
class LivePinnedPubsubAdapter:
 def __init__(self,api_url):self.api_url=api_url;self.calls=0
 def pubsub_publish(self,topic,data,**kw):
  self.calls+=1
  if data==b'error':raise RuntimeError('SECRET-error-body')
  return {'accepted':True,'durable':False,'state':'ACCEPTED','effect_kind':'EXTERNAL_NOTIFY','request_id':'request','operation_id':'operation','private_key':'SECRET'}
 def subscribe(self,topic,**kw):return Stream()
 def pubsub_peers(self,topic,**kw):return ['peer-a','peer-b']
 def swarm_connect(self,multiaddr,**kw):return {'success':True}
class Stream:
 def __init__(self):self.closed=False;self.frames=iter([{'raw_frame':b'{"data":"actual-fixture"}\\n'}])
 def __enter__(self):return self
 def __exit__(self,*args):self.closed=True
 def __iter__(self):return self
 def __next__(self):return next(self.frames)
 def close(self):self.closed=True
'''
class ObserverTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='svf-native-witness-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.invocation='a'*32;self.family='kit-pubsub';self.relative='external/ipfs_kit/ipfs_kit_py/assurance/pinned_pubsub.py';self.module_name='explicit_pubsub_fixture_'+uuid.uuid4().hex
  p=self.root/self.relative;p.parent.mkdir(parents=True);p.write_text(FIXTURE);p.chmod(0o600);self.original_sha=m.sha(p.read_bytes())
  s=importlib.util.spec_from_file_location(self.module_name,p);self.module=importlib.util.module_from_spec(s);sys.modules[s.name]=self.module;self.addCleanup(sys.modules.pop,s.name,None);s.loader.exec_module(self.module)
  self.sink=m.WitnessSink(self.root,family=self.family,invocation_id=self.invocation,identity={'pid':os.getpid(),'start_ticks':m._birth()},observer_sha256=m.sha(SOURCE.read_bytes()),source_sha256={self.relative:self.original_sha})
  self.authorization={'schema':'swissknife.foundation-sdk-call-capture.v1','capture_id':str(uuid.uuid4()),'family':self.family,'invocation_id':self.invocation,'task_id':'SVF-043','native_process':self.sink.identity,'lease_id':str(uuid.uuid4()),'foreground_birth':'1234','issued_at':time.time()-1,'expires_at':time.time()+120,'expected_sources':{self.relative:self.original_sha},'observational_only':True,'completion_authority':False}
  m._immutable(self.root,self.sink.directory/'capture.json',self.authorization)
 def snapshot(self):return m.read_snapshot(self.root,family=self.family,invocation_id=self.invocation)
 def events(self):return [r['event']for r in self.snapshot()['events']]
 def instrument(self):
  def check():
   if m.sha((self.root/self.relative).read_bytes())!=self.original_sha:raise ValueError('changed source')
  m.instrument_class(self.module.LivePinnedPubsubAdapter,('__init__','pubsub_publish','subscribe','pubsub_peers','swarm_connect'),sink=self.sink,sdk_module=self.module_name,source_path=self.relative,source_sha256=self.original_sha,check=check)
 def test_original_method_delegate_and_safe_return_fields(self):
  original=self.module.LivePinnedPubsubAdapter.pubsub_publish;self.instrument();client=self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5032');message_id=str(uuid.uuid4());data=json.dumps({'message_id':message_id,'secret':'SECRET'}).encode();topic='svf.pubsub.'+'b'*32
  actual=client.pubsub_publish(topic,data);self.assertEqual(client.calls,1);self.assertTrue(actual['accepted']);self.assertIs(client.pubsub_publish.__wrapped__,original)
  events=[e for e in self.events()if e['sdk']['method']=='pubsub_publish'];self.assertEqual([e['phase']for e in events],['enter','return']);self.assertEqual(events[0]['call_id'],events[1]['call_id']);self.assertEqual(events[0]['arguments']['data_sha256'],m.sha(data));self.assertEqual(events[0]['arguments']['message_id'],message_id);self.assertEqual(events[1]['result']['request_id'],'request');self.assertNotIn('SECRET',json.dumps(self.events()))
 def test_original_exception_type_and_private_message_not_logged(self):
  self.instrument();client=self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5032')
  with self.assertRaisesRegex(RuntimeError,'SECRET-error-body'):client.pubsub_publish('svf.pubsub.'+'b'*32,b'error')
  events=self.events();self.assertEqual(events[-1]['phase'],'error');self.assertEqual(events[-1]['error_type'],'RuntimeError');self.assertNotIn('SECRET',json.dumps(events))
 def test_stream_context_iteration_exact_raw_bytes_and_close(self):
  self.instrument();client=self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5033');subscription=client.subscribe('svf.pubsub.'+'b'*32)
  with subscription as active:items=list(active)
  self.assertTrue(subscription.wrapped.closed);self.assertEqual(len(items),1);event=[e for e in self.events()if e['phase']=='stream'][0];enter=[e for e in self.events()if e['sdk']['method']=='subscribe'and e['phase']=='enter'][0];self.assertEqual(event['call_id'],enter['call_id']);self.assertEqual(event['frame'],{'sha256':m.sha(items[0]['raw_frame']),'bytes':len(items[0]['raw_frame'])})
  subscription.close();self.assertTrue(subscription.wrapped.closed)
 def test_context_manager_returning_distinct_iterator_is_preserved(self):
  class Context:
   def __enter__(self):return iter([{'raw_frame':b'exact\n'}])
   def __exit__(self,*args):pass
   def close(self):pass
  proxy=m.SubscriptionObservation(Context(),self.sink,str(uuid.uuid4()),None,{'method':'subscribe'},{},lambda:None,self.sink.capture())
  with proxy as it:self.assertEqual(list(it),[{'raw_frame':b'exact\n'}])
 def test_changed_sdk_source_refused_before_call(self):
  self.instrument();client=self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5032');before=len(self.events());(self.root/self.relative).write_text(FIXTURE+'\n# changed')
  with self.assertRaises(ValueError):client.pubsub_publish('svf.pubsub.'+'b'*32,b'payload')
  self.assertEqual(client.calls,0);self.assertEqual(len(self.events()),before)
 def test_wrong_source_code_origin_refuses_instrumentation(self):
  with self.assertRaises(ValueError):m.instrument_class(self.module.LivePinnedPubsubAdapter,('pubsub_publish',),sink=self.sink,sdk_module='foreign',source_path=self.relative,source_sha256=self.original_sha,check=lambda:None)
 def test_threaded_calls_have_unique_ids_and_thread_local_parentage(self):
  self.instrument();client=self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5032');errors=[]
  def call():
   try:client.pubsub_publish('svf.pubsub.'+'b'*32,b'fixture')
   except Exception as e:errors.append(e)
  workers=[threading.Thread(target=call)for _ in range(6)]
  for t in workers:t.start()
  for t in workers:t.join(timeout=5);self.assertFalse(t.is_alive())
  self.assertEqual(errors,[]);events=[e for e in self.events()if e['sdk']['method']=='pubsub_publish'];self.assertEqual(len(events),12);self.assertEqual(len({e['call_id']for e in events}),6);self.assertTrue(all(e['parent_call_id']is None for e in events))
 def test_contextlib_decorator_uses_original_sdk_generator_pin_and_closes_yielded_stream(self):
  text=FIXTURE.replace('class LivePinnedPubsubAdapter:', 'import contextlib\nclass LivePinnedPubsubAdapter:').replace(' def subscribe(self,topic,**kw):return Stream()', ' @contextlib.contextmanager\n def subscribe(self,topic,**kw):\n  stream=Stream();self.last_stream=stream\n  try:yield stream\n  finally:stream.close()')
  p=self.root/self.relative;p.write_text(text);self.original_sha=m.sha(p.read_bytes());self.sink.source_sha256[self.relative]=self.original_sha;self.sink.manifest['source_sha256'][self.relative]=self.original_sha
  manifest=self.sink.directory/'observer.json';manifest.write_bytes(m.canonical(self.sink.manifest));self.authorization['expected_sources'][self.relative]=self.original_sha;(self.sink.directory/'capture.json').write_bytes(m.canonical(self.authorization))
  s=importlib.util.spec_from_file_location(self.module_name,p);self.module=importlib.util.module_from_spec(s);sys.modules[s.name]=self.module;s.loader.exec_module(self.module)
  outer=self.module.LivePinnedPubsubAdapter.subscribe;underlying=__import__('inspect').unwrap(outer);self.assertNotEqual(outer.__code__.co_filename,underlying.__code__.co_filename)
  self.instrument();client=self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5033');subscription=client.subscribe('svf.pubsub.'+'b'*32)
  with subscription as active:
   self.assertEqual(len(list(active)),1);subscription.close();subscription.close()
  self.assertTrue(client.last_stream.closed);self.assertTrue(subscription.exited)
  event=[e for e in self.events()if e['sdk']['method']=='subscribe'and e['phase']=='enter'][0];self.assertEqual(event['sdk']['code_sha256'],m.sha(__import__('marshal').dumps(underlying.__code__)))
 def test_normal_sdk_lazy_loader_executes_original_bytes_then_installs_wrappers(self):
  name='ipfs_kit_py.assurance.pinned_pubsub';original=importlib.util.spec_from_file_location(name,self.root/self.relative);finder=m.SDKObserverFinder(self.root,family=self.family,sink=self.sink,pin=lambda p:self.original_sha)
  with patch.object(m.importlib.machinery.PathFinder,'find_spec',return_value=original):wrapped=finder.find_spec(name,[])
  module=importlib.util.module_from_spec(wrapped);wrapped.loader.exec_module(module);client=module.LivePinnedPubsubAdapter('http://127.0.0.1:5032');self.assertTrue(client.pubsub_publish('svf.pubsub.'+'b'*32,b'fixture')['accepted']);self.assertTrue(any(e['sdk']['module']==name for e in self.events()))
 def test_no_double_wrap_or_changed_signature(self):
  self.instrument();fn=self.module.LivePinnedPubsubAdapter.pubsub_publish;self.instrument();self.assertIs(fn,self.module.LivePinnedPubsubAdapter.pubsub_publish)
 def test_capture_bound_records_fault_and_delegates_without_permanent_sdk_fault(self):
  self.instrument();client=self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5032');self.sink.sequence=m.MAX_EVENTS
  self.assertTrue(client.pubsub_publish('svf.pubsub.'+'b'*32,b'fixture')['accepted']);self.assertEqual(client.calls,1)
  self.assertEqual(len(self.snapshot()['capture_faults']),1)
  self.assertTrue(client.pubsub_publish('svf.pubsub.'+'b'*32,b'fixture')['accepted']);self.assertEqual(client.calls,2);self.assertEqual(len(self.snapshot()['capture_faults']),1)
 def test_missing_capture_delegates_original_methods_without_event_writes(self):
  (self.sink.directory/'capture.json').unlink();self.instrument();client=self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5032');client.pubsub_publish('svf.pubsub.'+'b'*32,b'fixture');self.assertEqual(client.calls,1);self.assertEqual(self.events(),[])
 def test_expired_or_invalid_capture_does_not_break_ordinary_sdk_calls(self):
  self.instrument()
  for change in [{'issued_at':time.time()-400,'expires_at':time.time()-100},{'native_process':{'pid':999,'start_ticks':'wrong'}},{'expires_at':time.time()+600},{'expected_sources':{'foreign.py':'a'*64}}]:
   (self.sink.directory/'capture.json').write_bytes(m.canonical({**self.authorization,**change}))
   with self.subTest(change=change):
    before=self.sink.sequence;client=self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5032');self.assertTrue(client.pubsub_publish('svf.pubsub.'+'b'*32,b'fixture')['accepted']);self.assertEqual(self.sink.sequence,before)
 def test_capture_expiry_during_subscription_preserves_actual_iteration(self):
  self.instrument();client=self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5032');subscription=client.subscribe('svf.pubsub.'+'b'*32);before=len(self.events())
  with patch.object(m.time,'time',return_value=self.authorization['expires_at']+1):
   with subscription as it:self.assertEqual(len(list(it)),1)
  self.assertTrue(subscription.wrapped.closed);self.assertEqual(len(self.events()),before)
 def test_snapshot_ref_hashes_identity_and_scope(self):
  self.instrument();self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5032');snapshot=self.snapshot()
  for row in snapshot['events']:
   raw=(self.root/row['reference']['path']).read_bytes();self.assertEqual(m.sha(raw),row['reference']['sha256']);self.assertEqual(len(raw),row['reference']['bytes']);self.assertEqual(json.loads(raw),row['event'])
  self.assertFalse(snapshot['observer']['authenticated_origin']);self.assertFalse(snapshot['completion_authority'])
 def test_snapshot_event_symlink_or_identity_tamper_rejected(self):
  self.instrument();self.module.LivePinnedPubsubAdapter('http://127.0.0.1:5032');path=self.root/self.snapshot()['events'][0]['reference']['path'];raw=path.read_bytes();value=json.loads(raw);value['pid']+=100;path.write_text(json.dumps(value))
  with self.assertRaises(ValueError):self.snapshot()
  path.unlink();foreign=self.root/'foreign';foreign.write_bytes(raw);foreign.chmod(0o600);path.symlink_to(foreign)
  with self.assertRaises(ValueError):self.snapshot()
 def test_existing_invocation_manifest_never_overwritten(self):
  before=(self.sink.directory/'observer.json').read_bytes()
  with self.assertRaises(FileExistsError):m.WitnessSink(self.root,family=self.family,invocation_id=self.invocation,identity={'pid':999,'start_ticks':'fake'},observer_sha256='x'*64,source_sha256={})
  self.assertEqual((self.sink.directory/'observer.json').read_bytes(),before)
 def test_invalid_family_or_traversal_invocation_refused(self):
  for family,identity in [('foreign','a'*32),(self.family,'../escape'),(self.family,'A'*32)]:
   with self.subTest(family=family,identity=identity),self.assertRaises(ValueError):m._directory(self.root,family,identity)
 def test_future_sdk_missing_does_not_fabricate_or_import_module(self):
  finder=m.SDKObserverFinder(self.root,family=self.family,sink=self.sink,pin=lambda p:(_ for _ in()).throw(AssertionError('must not pin absent module')))
  with patch.object(m.importlib.machinery.PathFinder,'find_spec',return_value=None):self.assertIsNone(finder.find_spec('ipfs_kit_py.assurance.pinned_pubsub',[]))
 def test_same_timestamp_size_stale_pyc_never_replaces_current_pinned_source(self):
  import py_compile
  p=self.root/self.relative;old=p.stat();py_compile.compile(str(p),doraise=True);updated=FIXTURE.replace("['peer-a','peer-b']","['peer-x','peer-y']");self.assertEqual(len(updated.encode()),len(FIXTURE.encode()));p.write_text(updated);os.utime(p,ns=(old.st_atime_ns,old.st_mtime_ns));fingerprint=m.sha(p.read_bytes());(self.sink.directory/'capture.json').unlink()
  name='ipfs_kit_py.assurance.pinned_pubsub';spec=importlib.util.spec_from_file_location(name,p);finder=m.SDKObserverFinder(self.root,family=self.family,sink=self.sink,pin=lambda rel:fingerprint)
  with patch.object(m.importlib.machinery.PathFinder,'find_spec',return_value=spec):wrapped=finder.find_spec(name,[])
  module=importlib.util.module_from_spec(wrapped);wrapped.loader.exec_module(module);self.assertEqual(module.LivePinnedPubsubAdapter('http://127.0.0.1:5032').pubsub_peers('topic'),['peer-x','peer-y'])
 def test_foreign_sdk_loader_origin_refused(self):
  finder=m.SDKObserverFinder(self.root,family=self.family,sink=self.sink,pin=lambda p:self.original_sha)
  with patch.object(m.importlib.machinery.PathFinder,'find_spec',return_value=type('S',(),{'origin':'/foreign/sdk.py'})()):
   with self.assertRaises(ImportError):finder.find_spec('ipfs_kit_py.assurance.pinned_pubsub',[])
 def test_bad_source_hash_prevents_loader_execution(self):
  from importlib.machinery import SourceFileLoader,ModuleSpec
  finder=m.SDKObserverFinder(self.root,family=self.family,sink=self.sink,pin=lambda p:'0'*64);name='ipfs_kit_py.assurance.pinned_pubsub';loader=SourceFileLoader(name,str(self.root/self.relative));actual=ModuleSpec(name,loader,origin=str(self.root/self.relative))
  with patch.object(m.importlib.machinery.PathFinder,'find_spec',return_value=actual):wrapped=finder.find_spec(name,[])
  with patch.object(loader,'exec_module')as execute:
   with self.assertRaises(ImportError):wrapped.loader.exec_module(type('Module',(),{})())
   execute.assert_not_called()
 def test_command_summary_only_exposes_exact_owned_fixed_arguments(self):
  run=str(uuid.uuid4());argv=['python','-I','-B',str(self.root/'scripts/svf_backends/fixed_supervisor_worker.py'),'--runtime-root',str(self.root/m.RUNTIME/'backends/supervisor-fixtures'),'--run-id',run,'--stage','a','--challenge','a'*32,'--mode','normal'];safe=m._argv(argv,self.root);self.assertEqual(safe['command_argv'],argv);self.assertEqual(safe['run_id'],run)
  bad=argv[:];bad[bad.index('--challenge')+1]='SECRET';unsafe=m._argv(bad,self.root);self.assertNotIn('command_argv',unsafe);self.assertNotIn('SECRET',json.dumps(unsafe))
 def test_actual_sdk_stdout_artifact_and_taskpage_shape(self):
  @dataclasses.dataclass
  class Stream:digest:str;byte_count:int;preview:str='SECRET'
  @dataclasses.dataclass
  class Result:pid:int;process_group_id:int;stdout:Stream;publication_allowed:bool
  out=m._result(Result(1,2,Stream('sha256:'+'a'*64,7),False),self.root);self.assertEqual(out['stdout'],{'digest':'sha256:'+'a'*64,'byte_count':7});self.assertNotIn('SECRET',json.dumps(out))
  @dataclasses.dataclass
  class Task:task_cid:str;status:str;body:dict
  @dataclasses.dataclass
  class Page:tasks:tuple;revision:int
  out=m._result(Page((Task('cid-a','ready',{'secret':'SECRET'}),),1),self.root);self.assertEqual(out['task_cids'],['cid-a']);self.assertNotIn('SECRET',json.dumps(out))
class StartupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='svf-native-startup-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.entry=self.root/m.ENTRYPOINT;self.entry.parent.mkdir(parents=True);self.entry.write_bytes(SOURCE.read_bytes());self.entry.chmod(0o600)
  self.invocation='d'*32;self.helper=self.root/'scripts/svf_backends/foundation_service_ownership.py'
  self.helper.write_text("import os,json\nfrom pathlib import Path\nclass ServicePortsNotReady(ValueError):\n def __init__(self,identity):self.identity=identity\ndef _registration(root):\n cfg=json.loads((root/'config/swissknife_visual_functional_foundation_owners.json').read_text())\n if cfg['status']!='REGISTERED':raise ValueError('draft')\n return cfg\ndef unit_identity(root,name,expected):\n from pathlib import Path\n identity={'pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],'invocation_id':os.environ.get('FIXTURE_OBSERVED_INVOCATION',os.environ['INVOCATION_ID'])}\n if os.environ.get('FIXTURE_PENDING_PORT'):raise ServicePortsNotReady(identity)\n return identity\n")
  self.helper.chmod(0o600);self.cfg={'status':'REGISTERED','protected_sha256':{m.ENTRYPOINT:m.sha(self.entry.read_bytes()),'scripts/svf_backends/foundation_service_ownership.py':m.sha(self.helper.read_bytes())},'families':{name:{'required_sources':[m.FAMILIES[name][1],'future_absent_sdk.py']}for name in m.FAMILIES},'units':{family[0]:{}for family in m.FAMILIES.values()}}
  for family in m.FAMILIES.values():
   p=self.root/family[1];p.write_text('# explicit fixed service fixture\n');p.chmod(0o600)
  self.config=self.root/m.REGISTRATION;self.config.parent.mkdir();self.config.write_text(json.dumps(self.cfg));self.config.chmod(0o600)
  self.old_argv=sys.argv[:];self.old_path=sys.path[:];self.old_meta=sys.meta_path[:];self.addCleanup(lambda:setattr(sys,'argv',self.old_argv));self.addCleanup(lambda:setattr(sys,'path',self.old_path));self.addCleanup(lambda:setattr(sys,'meta_path',self.old_meta))
  for p in [patch.object(m,'ROOT',self.root),patch.object(m,'__file__',str(self.entry)),patch.dict(os.environ,{'INVOCATION_ID':self.invocation},clear=False)]:p.start();self.addCleanup(p.stop)
 def update(self):self.config.write_text(json.dumps(self.cfg))
 def test_fixed_native_service_runs_same_pid_with_literal_args_and_absent_future_sdk(self):
  with patch.object(m.runpy,'run_path')as execute:
   self.assertEqual(m.main(['--family','kit-pubsub']),0);execute.assert_called_once_with(str(self.root/m.FAMILIES['kit-pubsub'][1]),run_name='__main__');self.assertEqual(sys.argv,[str(self.root/m.FAMILIES['kit-pubsub'][1]),*m.FAMILIES['kit-pubsub'][2]])
  snapshot=m.read_snapshot(self.root,family='kit-pubsub',invocation_id=self.invocation);self.assertEqual(snapshot['events'],[]);self.assertIsNone(snapshot['observer']['source_sha256']['future_absent_sdk.py']);self.assertEqual(snapshot['identity']['pid'],os.getpid())
 def test_startup_accepts_own_typed_pending_listener_before_service_binds(self):
  with patch.dict(os.environ,{'FIXTURE_PENDING_PORT':'1'}),patch.object(m.runpy,'run_path')as execute:
   m.main(['--family','accelerate-supervisor']);execute.assert_called_once()
 def test_self_hash_change_or_missing_pin_refuses_before_native_service(self):
  for value in ['0'*64,None]:
   self.cfg['protected_sha256'][m.ENTRYPOINT]=value;self.update()
   with self.subTest(pin=value),patch.object(m.runpy,'run_path')as execute:
    with self.assertRaises(ValueError):m.main(['--family','kit-pubsub'])
    execute.assert_not_called()
 def test_helper_source_hash_change_refuses_before_service(self):
  self.helper.write_text('# changed helper')
  with patch.object(m.runpy,'run_path')as execute:
   with self.assertRaises(ValueError):m.main(['--family','kit-pubsub'])
   execute.assert_not_called()
 def test_draft_registration_refuses_before_service(self):
  self.cfg['status']='DRAFT_NOT_DEPLOYED';self.update()
  with patch.object(m.runpy,'run_path')as execute:
   with self.assertRaises(ValueError):m.main(['--family','kit-pubsub'])
   execute.assert_not_called()
 def test_wrong_actual_native_invocation_refuses_before_service(self):
  with patch.dict(os.environ,{'FIXTURE_OBSERVED_INVOCATION':'e'*32}),patch.object(m.runpy,'run_path')as execute:
   with self.assertRaises(ValueError):m.main(['--family','kit-pubsub'])
   execute.assert_not_called()
 def test_no_caller_service_command_or_extra_args_are_accepted(self):
  with patch.object(m.runpy,'run_path')as execute,contextlib.redirect_stderr(io.StringIO()):
   with self.assertRaises(SystemExit):m.main(['--family','kit-pubsub','--service','/foreign/program'])
   execute.assert_not_called()
 def test_runner_policy_detects_injected_runtime_without_calling_it(self):
  from types import SimpleNamespace,ModuleType
  class Scheduler:pass
  sample=lambda:(_ for _ in()).throw(AssertionError('must not sample host'))
  resources=ModuleType('resources');resources.sample_host_resources=sample;resources.__file__=str(self.root/'not-pinned.py')
  runner=ModuleType('runner');runner.ResourceScheduler=Scheduler;scheduler=Scheduler();scheduler.host_sampler=sample
  instance=SimpleNamespace(_scheduler=scheduler,_host_snapshot=None,_popen=m.subprocess.Popen,_clock=m.time.monotonic,_sleep=m.time.sleep,_require_resource_lease=True)
  with patch.dict(sys.modules,{'ipfs_accelerate_py.agent_supervisor.verification.process_runner':runner,'ipfs_accelerate_py.agent_supervisor.runtime.resource_scheduler':resources}):
   policy=m._runner_policy(instance,self.root);self.assertTrue(all(v is True for v in policy.values()))
   instance._host_snapshot={'fake':True};instance._popen=lambda *a:None;instance._clock=lambda:0;instance._scheduler.host_sampler=lambda:None
   policy=m._runner_policy(instance,self.root);self.assertFalse(policy['host_snapshot_is_none']);self.assertFalse(policy['popen_is_subprocess_popen']);self.assertFalse(policy['clock_is_time_monotonic']);self.assertFalse(policy['host_sampler_is_sdk_function'])
 def test_mappingproxy_readback_preserves_only_declared_keys(self):
  from types import MappingProxyType
  out=m._result(MappingProxyType({'task_cid':'actual-cid','status':'ready','revision':3,'body':{'secret':'SECRET'}}),self.root)
  self.assertEqual(out,{'task_cid':'actual-cid','status':'ready','revision':3})

if __name__=='__main__':unittest.main()
