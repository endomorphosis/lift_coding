"""Authored lightweight protocol/process fixtures; never load GPT2 or call a provider."""
import asyncio
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

import native_accelerate_backend as backend
import native_accelerate_service as service

class WarmWorkerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  for name in backend.WORKER_SOURCE_PATHS:
   p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# authored pinned test source\n')
  self.sources=backend.worker_sources(self.root)
 def init(self):return {'protocol':backend.WORKER_PROTOCOL,'type':'initialize','worker_id':str(uuid.uuid4()),
  'parent_pid':os.getppid(),'parent_birth':backend.process_birth(os.getppid()),'source_sha256':self.sources}
 def request(self,init,request_id=None):
  request_id=request_id or str(uuid.uuid4())
  return {'protocol':backend.WORKER_PROTOCOL,'type':'execute','worker_id':init['worker_id'],'request_id':request_id,
   'source_sha256':self.sources,'job_dir':str(self.root/service.NAMESPACE/'backends/test/jobs'/request_id),
   'model':'gpt2','input_data':'unit input','max_new_tokens':4,'correlation_id':'unit-correlation:'+request_id}
 def stream(self,frames):return io.BytesIO(b''.join(json.dumps(x).encode()+b'\n' for x in frames))
 def fake_engine(self,calls):
  root=self.root
  class Engine:
   def __init__(self):calls.append('load');self.model=object();self.tokenizer=object();self.snapshot=root/'authored-cache';print('SDK startup noise')
   def generate_text(self,**kwargs):return {'output':kwargs['inputs']+' generated','generated_text':' generated',
    'generated_token_count':1,'generated_token_ids':[42],'simulated':False,'echo_fallback':False}
  return Engine
 def sdk(self,calls):
  module=ModuleType('ipfs_accelerate_py.inference_backend_manager');module.__file__=str(self.root/backend.WORKER_SOURCE_PATHS[2])
  class Manager:
   def __init__(self,*args,**kwargs):pass
   def register_backend(self,*args,**kwargs):self.engine=kwargs['instance'];return True
   async def execute_task(self,**kwargs):calls.append(kwargs);return self.engine.generate_text(inputs=kwargs['inputs'][0])
  module.InferenceBackendManager=Manager;module.BackendType=SimpleNamespace(MCP='mcp');module.BackendStatus=SimpleNamespace(HEALTHY='healthy');module.BackendCapabilities=lambda **kwargs:kwargs
  return module
 def test_model_loads_once_but_each_uuid_runs_actual_executor_manager_path_and_fresh_job(self):
  init=self.init();frames=[init,self.request(init),self.request(init)];output=io.BytesIO();loads=[];calls=[];noise=io.StringIO()
  with patch.object(backend,'ROOT',self.root),patch.dict(sys.modules,{'ipfs_accelerate_py.inference_backend_manager':self.sdk(calls)}),patch.object(sys,'stderr',noise):
   backend.serve_worker(self.stream(frames),output,root=self.root,engine_factory=self.fake_engine(loads),max_requests=2)
  values=[json.loads(x) for x in output.getvalue().splitlines()];self.assertEqual(loads,['load']);self.assertEqual(len(calls),2)
  self.assertEqual([x['type'] for x in values],['ready','completed','completed']);self.assertTrue(values[-1]['retiring'])
  self.assertNotEqual(values[1]['request_id'],values[2]['request_id']);self.assertEqual(values[1]['worker_id'],values[2]['worker_id'])
  self.assertEqual(len(list((self.root/service.NAMESPACE).glob('backends/test/jobs/*/execution.json'))),2)
  self.assertIn('SDK startup noise',noise.getvalue());self.assertNotIn(b'SDK startup noise',output.getvalue())
 def test_replayed_uuid_never_generates_twice(self):
  init=self.init();request=self.request(init);calls=[]
  async def execute(job,**kwargs):calls.append(1);return {'warm_worker':kwargs['worker_context']}
  with self.assertRaisesRegex(ValueError,'replayed'):
   backend.serve_worker(self.stream([init,request,request]),io.BytesIO(),root=self.root,engine_factory=self.fake_engine([]),executor=execute)
  self.assertEqual(calls,[1])
 def test_invalid_request_or_source_never_executes(self):
  for mutation in ['source','token','unicode','job','correlation']:
   init=self.init();request=self.request(init);calls=[]
   if mutation=='source':request['source_sha256']={}
   elif mutation=='token':request['max_new_tokens']=True
   elif mutation=='unicode':request['input_data']='🙂'*129
   elif mutation=='job':request['job_dir']=str(self.root/'outside'/request['request_id'])
   else:request['correlation_id']=[]
   async def execute(*args,**kwargs):calls.append(1)
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):
    backend.serve_worker(self.stream([init,request]),io.BytesIO(),root=self.root,engine_factory=self.fake_engine([]),executor=execute)
   self.assertEqual(calls,[])
 def test_ascii512_and_all_one_to_four_tokens_remain_valid(self):
  for tokens in [1,2,3,4]:backend.validate_request('gpt2','x'*512,tokens)
  for text in ['x'*513,'🙂'*129]:
   with self.assertRaises(ValueError):backend.validate_request('gpt2',text,4)
 def test_drift_during_model_start_never_advertises_ready(self):
  init=self.init();output=io.BytesIO()
  def load():
   (self.root/backend.WORKER_SOURCE_PATHS[2]).write_text('changed');return SimpleNamespace(model=object(),tokenizer=object())
  with self.assertRaisesRegex(RuntimeError,'readiness'):
   backend.serve_worker(self.stream([init]),output,root=self.root,engine_factory=load)
  self.assertEqual(output.getvalue(),b'')
 def fixture(self,mode='valid'):
  # Explicit subprocess fixture implements framing only, never SDK inference.
  return r'''
import sys,json,os,time
birth=lambda pid:open('/proc/%s/stat'%pid).read().rsplit(')',1)[1].split()[19]
init=json.loads(sys.stdin.buffer.readline());identity={k:init[k] for k in ['protocol','worker_id','parent_pid','parent_birth','source_sha256']}
identity.update(pid=os.getpid(),pid_birth=birth(os.getpid()),session_id=os.getsid(0))
mode=MODE
if mode=='startup_timeout':time.sleep(60)
ready={**identity,'type':'ready','engine_loaded':True,'model':'gpt2','model_snapshot':SNAPSHOT}
if mode=='bad_ready':ready['engine_loaded']=False
if mode=='numeric_ready':ready['engine_loaded']=1
print(json.dumps(ready),flush=True)
for line in sys.stdin.buffer:
 req=json.loads(line);context={**identity,'request_id':req['request_id'],'correlation_id':req['correlation_id']}
 if mode=='timeout':time.sleep(60)
 if mode=='crash':os._exit(7)
 if mode=='oversize':sys.stdout.write('x'*131073+'\n');sys.stdout.flush();continue
 if mode=='noise':sys.stderr.write('x'*131073);sys.stderr.flush();time.sleep(60)
 native={'warm_worker':context,'input':req['input_data']}
 response={**context,'type':'completed','native':native,'retiring':mode=='retiring'}
 if mode=='stale':response['request_id']='old'
 if mode=='source':response['source_sha256']={}
 if mode=='extra':print(json.dumps(response)+'\n'+json.dumps(response),flush=True)
 else:print(json.dumps(response),flush=True)
 if mode=='retiring':break
'''.replace('MODE',repr(mode)).replace('SNAPSHOT',repr(backend.SNAPSHOT))
 def worker(self,mode='valid',startup=1,deadline=.2):
  worker=service.WarmInferenceWorker(self.root,self.sources,startup_timeout=startup,request_timeout=deadline)
  worker._command=lambda:[sys.executable,'-u','-c',self.fixture(mode)]
  recovery=patch.object(worker,'recover_async');recovery.start();self.addCleanup(recovery.stop);self.addCleanup(worker.close)
  return worker
 def invoke(self,worker):
  request_id=str(uuid.uuid4());return worker.request(request_id,self.root/service.NAMESPACE/'jobs'/request_id,'gpt2','fresh unit input',4,'unit:'+request_id)
 def test_parent_reuses_same_owned_ready_process_for_distinct_requests(self):
  worker=self.worker();self.assertFalse(worker.is_ready());worker.start();self.assertTrue(worker.is_ready());pid=worker.process.pid
  first=self.invoke(worker);second=self.invoke(worker);self.assertEqual(worker.process.pid,pid)
  self.assertNotEqual(first['warm_worker']['request_id'],second['warm_worker']['request_id']);self.assertEqual(first['warm_worker']['worker_id'],second['warm_worker']['worker_id'])
  self.assertEqual(worker.startup_timeout,1);self.assertEqual(service.WarmInferenceWorker(self.root,self.sources).request_timeout,30)
 def test_startup_and_request_timeout_reap_owned_child_before_replacement(self):
  worker=self.worker('startup_timeout',startup=.05)
  with self.assertRaises(TimeoutError):worker.start()
  self.assertIsNone(worker.process);worker._command=lambda:[sys.executable,'-u','-c',self.fixture('timeout')];worker.start();old=worker.process.pid
  with self.assertRaises(TimeoutError):self.invoke(worker)
  self.assertIsNone(worker.process);self.assertFalse(Path('/proc',str(old)).exists());worker.recover_async.assert_called_once()
  worker._command=lambda:[sys.executable,'-u','-c',self.fixture()];worker.start();self.assertNotEqual(worker.process.pid,old);self.invoke(worker)
 def test_malformed_stale_oversized_extra_crash_and_noise_retire_without_replay(self):
  for mode in ['stale','source','oversize','extra','crash','noise']:
   with self.subTest(mode=mode):
    worker=self.worker(mode);worker.start()
    with self.assertRaises((ValueError,RuntimeError,TimeoutError)):self.invoke(worker)
    self.assertIsNone(worker.process);worker.recover_async.assert_called_once()
 def test_wrong_ready_source_and_loaded_claim_never_grant_health(self):
  for mode in ['bad_ready','numeric_ready']:
   worker=self.worker(mode)
   with self.subTest(mode=mode),self.assertRaisesRegex(RuntimeError,'readiness_identity'):worker.start()
   self.assertFalse(worker.is_ready());self.assertIsNone(worker.process)
 def test_identity_mismatch_refuses_signals_and_replacement(self):
  worker=self.worker();worker.start();original=worker.birth;process=worker.process;worker.birth='unowned'
  self.assertFalse(worker._retire());self.assertIs(worker.process,process);self.assertIsNone(process.poll())
  with self.assertRaisesRegex(RuntimeError,'identity_unresolved'):worker.start()
  worker.birth=original;self.assertTrue(worker.close());self.assertIsNotNone(process.poll())
 def test_source_drift_after_ready_refuses_request_and_never_relabels_loaded_code(self):
  worker=self.worker();worker.start();(self.root/backend.WORKER_SOURCE_PATHS[0]).write_text('drift')
  self.assertFalse(worker.is_ready())
  with self.assertRaisesRegex(RuntimeError,'warming or unavailable'):self.invoke(worker)
  self.assertIsNotNone(worker.process);self.assertTrue(worker.close())
 def test_retiring_completed_frame_is_accepted_and_exact_child_reaped(self):
  worker=self.worker('retiring');worker.start();native=self.invoke(worker)
  self.assertIn('warm_worker',native);self.assertIsNone(worker.process);worker.recover_async.assert_called_once()
 def test_close_interrupts_startup_without_waiting_for_the45second_deadline(self):
  worker=self.worker('startup_timeout',startup=45);errors=[]
  def start():
   try:worker.start()
   except Exception as error:errors.append(type(error).__name__)
  thread=threading.Thread(target=start);thread.start();deadline=time.monotonic()+1
  while worker.process is None and time.monotonic()<deadline:time.sleep(.005)
  self.assertIsNotNone(worker.process);started=time.monotonic();self.assertTrue(worker.close());thread.join(1)
  self.assertLess(time.monotonic()-started,1);self.assertFalse(thread.is_alive());self.assertIsNone(worker.process);self.assertTrue(errors)
 def test_worker_cli_reserves_protocol_fd_and_redirects_native_stdout_noise(self):
  script="import sys,os;sys.path.insert(0,sys.argv[1]);import native_accelerate_backend as b;\ndef fixture(i,o):\n os.write(1,b'native noise\\n');o.write(b'protocol-only\\n');o.flush()\nb.serve_worker=fixture;b.worker_main()"
  result=subprocess.run([sys.executable,'-c',script,str(Path(backend.__file__).parent)],capture_output=True,timeout=3)
  self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,b'protocol-only\n');self.assertEqual(result.stderr,b'native noise\n')

if __name__=='__main__':unittest.main()
