#!/usr/bin/env python3
"""Isolated native accelerator MCP: cached CPU generation, no external fallback."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import select
import time
import sys
import threading
import uuid

from native_accelerate_backend import (MODEL_ID, SNAPSHOT, MAX_NEW_TOKENS, validate_request,
 process_birth, worker_sources, WORKER_PROTOCOL, WORKER_MAX_INPUT, WORKER_MAX_OUTPUT)

ROOT=Path(__file__).resolve().parents[2]
NAMESPACE=Path('data/agent_supervisor/swissknife_visual_functional')
SDK_PATH='external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py'
BACKEND_PATH='scripts/svf_backends/native_accelerate_backend.py'
SERVICE_PATH='scripts/svf_backends/native_accelerate_service.py'
OBSERVATION_PATH='scripts/svf_backends/native_accelerate_observation.py'
OBSERVATION_TOOLS={
 'HealthChecker.check_detailed':('external/ipfs_accelerate/ipfs_accelerate_py/hf_model_server/monitoring/health.py',
  'ipfs_accelerate_py.hf_model_server.monitoring.health.HealthChecker','check_detailed'),
 'PrometheusMetrics.generate_metrics':('external/ipfs_accelerate/ipfs_accelerate_py/hf_model_server/monitoring/metrics.py',
  'ipfs_accelerate_py.hf_model_server.monitoring.metrics.PrometheusMetrics','generate_metrics'),
}
SDK_CLASS='ipfs_accelerate_py.inference_backend_manager.InferenceBackendManager'
PYTHON_PATH='external/ipfs_datasets/.venv/bin/python'
MAX_REQUEST_BYTES=8192
CONTEXT_ARGS={'dry_run','correlation_id','fixture_scope','scope','limit','cursor'}
SCHEMA='swissknife.native-accelerate-execution.v1'
TOOLS=[
 {'name':'run_inference_job','description':'Execute1..4 new GPT-2 tokens on actual CPU via native accelerator manager, using only qualified cached weights. Synchronous execution; no external provider.',
  'inputSchema':{'type':'object','properties':{'model':{'type':'string','enum':[MODEL_ID]},'model_id':{'type':'string','enum':[MODEL_ID]},'input':{'type':'string','maxLength':512},'input_data':{'type':'string','maxLength':512},'max_new_tokens':{'type':'integer','minimum':1,'maximum':4},'dry_run':{'type':'boolean'}},'additionalProperties':True}},
 {'name':'list_models','description':'List the actual cached, qualified CPU model registered by this service.','inputSchema':{'type':'object','additionalProperties':True}},
 {'name':'hardware_profile','description':'Report the actual CPU execution placement; no GPU capacity claim.','inputSchema':{'type':'object','additionalProperties':True}},
 {'name':'job_status','description':'Read an actual completed synchronous execution record by its returned job ID.','inputSchema':{'type':'object','properties':{'job_id':{'type':'string'},'task_id':{'type':'string'}},'additionalProperties':True}},
]
ALIASES={'submit_task':'run_inference_job','get_task':'job_status','detect_hardware':'hardware_profile'}
for alias,canonical in ALIASES.items():
 original=next(row for row in TOOLS if row['name']==canonical)
 description={
  'submit_task':'Execute a supported GPT-2 text-generation request synchronously through the real native manager; return its completed execution record. No queue or training is claimed.',
  'get_task':'Read an actual completed native execution record by its returned task/job UUID.',
  'detect_hardware':'Read actual CPU execution placement and logical processor count; no GPU capacity claim.'}[alias]
 TOOLS.append({'name':alias,'description':description,'inputSchema':original['inputSchema']})
for name in OBSERVATION_TOOLS:
 TOOLS.append({'name':name,'description':'Execute the actual pinned SDK observation in a bounded local subprocess; liveness or measured host telemetry, never inference or invented utilization.',
  'inputSchema':{'type':'object','properties':{'fixture_scope':{'type':'string'},'correlation_id':{'type':'string'},'dry_run':{'type':'boolean'}},'additionalProperties':False}})
TOOLS.append({'name':'WorkflowCoordinator.submit_task','description':'Run the explicit svf-goal-worker-v1 fixture through the real supervisor SDK. Ordinary submit_task remains CPU inference.','inputSchema':{'type':'object','additionalProperties':True}})

def inference_arguments(args,*,submission=False):
 """Normalize reviewed aliases without silently dropping task data."""
 allowed=CONTEXT_ARGS|{'model','model_id','model_name','input','input_data','prompt','max_new_tokens','max_length','backend','task'}
 if submission:allowed|={'task_type','payload'}
 if set(args)-allowed:raise ValueError('Unsupported native inference arguments')
 levels=[args]
 nested=args.get('payload') if submission else None
 if nested is not None:
  if type(nested) is not dict or set(nested)-{'model','model_id','model_name','input','input_data','prompt','context','code','max_new_tokens','max_length','backend','task'}:
   raise ValueError('Unsupported bounded submission payload')
  levels.append(nested)
 def coherent(keys,default=None):
  values=[level[key] for level in levels for key in keys if key in level]
  if not values:return default
  if any(value!=values[0] for value in values):raise ValueError('Conflicting native request aliases')
  return values[0]
 model=coherent(['model','model_id','model_name']);text=coherent(['input','input_data','prompt'])
 task_type=args.get('task_type','inference')
 if submission and task_type not in {'inference','text-generation'}:
  raise ValueError('Native submit_task supports text-generation inference only; no training or queue simulation')
 validate_request(model,text,coherent(['max_new_tokens'],MAX_NEW_TOKENS))
 if nested is not None:
  context=nested.get('context');code=nested.get('code')
  if context not in (None,{},[], ''):
   if not isinstance(context,(str,dict,list)):raise ValueError('Unsupported submission context type')
   text='Context:\n'+json.dumps(context,ensure_ascii=False,separators=(',',':'))+'\n\n'+text
  if code not in (None,''):
   if type(code) is not str:raise ValueError('Submission code context must be text')
   text='Code:\n'+code+'\n\n'+text
 validate_request(model,text,coherent(['max_new_tokens'],MAX_NEW_TOKENS))
 result={key:args[key] for key in CONTEXT_ARGS if key in args}
 result.update(model=model,input=text)
 for key in ['max_new_tokens','max_length','backend','task']:
  value=coherent([key])
  if value is not None:result[key]=value
 return result

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def safe_runtime(root,path):
 path=Path(path)
 if not path.is_absolute():path=root/path
 if not path.resolve().is_relative_to(root/NAMESPACE):raise ValueError('Native accelerator runtime escaped campaign namespace')
 for ancestor in [path,*path.parents]:
  if ancestor==root:break
  if ancestor.is_symlink():raise ValueError('Native accelerator runtime cannot use symlinks')
 return path

class WarmInferenceWorker:
 """One exact owned, source-pinned child; bounded JSONL, never answer caching."""
 def __init__(self,root,sources,*,startup_timeout=45,request_timeout=30):
  if not 0<startup_timeout<=45 or not 0<request_timeout<=30:raise ValueError('Invalid bounded worker deadline')
  self.root=Path(root);self.sources=dict(sources);self.startup_timeout=startup_timeout;self.request_timeout=request_timeout
  self.process=None;self.birth=None;self.session=None;self.worker_id=None;self.ready=False;self.closed=False
  self.lock=threading.RLock();self.recovery_lock=threading.Lock();self.recovery=None;self.retry_at=0;self.buffer=b'';self.stderr_bytes=0;self.stderr_eof=False
 def is_ready(self):
  process=self.process
  try:return bool(not self.closed and self.ready and process and process.poll() is None
    and process_birth(process.pid)==self.birth and os.getsid(process.pid)==self.session
    and worker_sources(self.root)==self.sources)
  except (OSError,ValueError):return False
 def _command(self):return [str(self.root/PYTHON_PATH),str(self.root/BACKEND_PATH),'--worker']
 def _identity(self):
  return {'protocol':WORKER_PROTOCOL,'worker_id':self.worker_id,'pid':self.process.pid,'pid_birth':self.birth,
   'session_id':self.session,'parent_pid':os.getpid(),'parent_birth':process_birth(os.getpid()),'source_sha256':self.sources}
 def _write(self,value,deadline):
  raw=json.dumps(value,ensure_ascii=False,allow_nan=False).encode()+b'\n'
  if len(raw)>WORKER_MAX_INPUT:raise RuntimeError('worker_input_limit')
  view=memoryview(raw)
  while view:
   if self.closed:raise RuntimeError('worker_closed')
   remaining=deadline-time.monotonic()
   if remaining<=0:raise TimeoutError('worker_write_timeout')
   if not select.select([], [self.process.stdin], [], min(remaining,.2))[1]:continue
   try:written=os.write(self.process.stdin.fileno(),view)
   except BlockingIOError:continue
   if written<=0:raise RuntimeError('worker_input_closed')
   view=view[written:]
 def _read(self,deadline):
  while b'\n' not in self.buffer:
   if self.closed:raise RuntimeError('worker_closed')
   remaining=deadline-time.monotonic()
   if remaining<=0:raise TimeoutError('worker_response_timeout')
   readable=select.select([self.process.stdout]+([] if self.stderr_eof else [self.process.stderr]),[],[],min(remaining,.2))[0]
   if not readable:continue
   for stream in readable:
    try:chunk=os.read(stream.fileno(),65536)
    except BlockingIOError:continue
    if stream is self.process.stderr:
     if not chunk:self.stderr_eof=True
     self.stderr_bytes+=len(chunk)
     if self.stderr_bytes>131072:raise RuntimeError('worker_diagnostic_limit')
    elif not chunk:raise RuntimeError('worker_output_closed')
    else:
     self.buffer+=chunk
     if len(self.buffer)>WORKER_MAX_OUTPUT:raise RuntimeError('worker_output_limit')
  raw,self.buffer=self.buffer.split(b'\n',1)
  if self.buffer:raise RuntimeError('worker_unsolicited_extra_frame')
  if time.monotonic()>deadline:raise TimeoutError('worker_response_timeout')
  value=json.loads(raw)
  if type(value) is not dict:raise RuntimeError('worker_invalid_frame')
  return value
 def _retire(self):
  self.ready=False;process=self.process
  if process is None:return True
  if process.poll() is None:
   try:
    if process_birth(process.pid)!=self.birth or os.getsid(process.pid)!=self.session:return False
    process.terminate()
    try:process.wait(timeout=2)
    except subprocess.TimeoutExpired:
     if process_birth(process.pid)!=self.birth or os.getsid(process.pid)!=self.session:return False
     process.kill();process.wait(timeout=2)
   except (OSError,subprocess.TimeoutExpired):
    if process.poll() is None:return False
  for stream in [process.stdin,process.stdout,process.stderr]:
   if stream:stream.close()
  self.process=None;self.birth=None;self.session=None;self.buffer=b''
  return True
 def close(self):
  self.closed=True
  with self.lock:return self._retire()
 def start(self):
  with self.lock:
   if self.closed:raise RuntimeError('worker_closed')
   if self.is_ready():return
   if not self._retire():raise RuntimeError('worker_identity_unresolved')
   if worker_sources(self.root)!=self.sources:raise RuntimeError('worker_source_drift')
   self.worker_id=str(uuid.uuid4());self.stderr_bytes=0;self.stderr_eof=False
   env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1',
    'TOKENIZERS_PARALLELISM':'false','OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','IPFS_ACCEL_SKIP_CORE':'1'}
   deadline=time.monotonic()+self.startup_timeout
   try:
    self.process=subprocess.Popen(self._command(),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
     bufsize=0,start_new_session=True,cwd=self.root,env=env)
    self.birth=process_birth(self.process.pid);self.session=os.getsid(self.process.pid)
    if self.session!=self.process.pid:raise RuntimeError('worker_session_not_owned')
    for stream in [self.process.stdin,self.process.stdout,self.process.stderr]:os.set_blocking(stream.fileno(),False)
    self._write({'protocol':WORKER_PROTOCOL,'type':'initialize','worker_id':self.worker_id,
     'parent_pid':os.getpid(),'parent_birth':process_birth(os.getpid()),'source_sha256':self.sources},deadline)
    value=self._read(deadline);expected={**self._identity(),'type':'ready','engine_loaded':True,'model':MODEL_ID,'model_snapshot':SNAPSHOT}
    if json.dumps(value,sort_keys=True,allow_nan=False)!=json.dumps(expected,sort_keys=True,allow_nan=False):raise RuntimeError('worker_readiness_identity_mismatch')
    if worker_sources(self.root)!=self.sources:raise RuntimeError('worker_source_drift')
    self.ready=True
   except Exception:
    self._retire();self.retry_at=time.monotonic()+3;raise
 def recover_async(self):
  if self.closed or self.is_ready() or time.monotonic()<self.retry_at:return
  with self.recovery_lock:
   if self.recovery and self.recovery.is_alive():return
   def recover():
    try:self.start()
    except Exception:self.retry_at=time.monotonic()+3
   self.recovery=threading.Thread(target=recover,daemon=True,name='native-accelerate-warm-recovery');self.recovery.start()
 def request(self,request_id,job,model,text,tokens,correlation):
  if not self.is_ready():
   self.recover_async();raise RuntimeError('Native CPU model is warming or unavailable; no generation started')
  with self.lock:
   if not self.is_ready():raise RuntimeError('worker_not_ready')
   self.stderr_bytes=0;deadline=time.monotonic()+self.request_timeout
   context={**self._identity(),'request_id':request_id,'correlation_id':correlation}
   try:
    # No unsolicited/stale frame may satisfy a later request.
    try:stray=os.read(self.process.stdout.fileno(),WORKER_MAX_OUTPUT+1)
    except BlockingIOError:stray=b''
    if stray:raise RuntimeError('worker_unsolicited_frame')
    self._write({'protocol':WORKER_PROTOCOL,'type':'execute','worker_id':self.worker_id,'request_id':request_id,
     'source_sha256':self.sources,'job_dir':str(job),'model':model,'input_data':text,
     'max_new_tokens':tokens,'correlation_id':correlation},deadline)
    value=self._read(deadline)
    if (set(value)!=set(context)|{'type','native','retiring'} or json.dumps({k:value.get(k) for k in context},sort_keys=True,allow_nan=False)!=json.dumps(context,sort_keys=True,allow_nan=False)
        or value.get('type')!='completed' or type(value.get('retiring')) is not bool
        or type(value.get('native')) is not dict
        or json.dumps(value['native'].get('warm_worker'),sort_keys=True,allow_nan=False)!=json.dumps(context,sort_keys=True,allow_nan=False)
        or worker_sources(self.root)!=self.sources or (not value.get('retiring') and not self.is_ready())):raise RuntimeError('worker_result_identity_mismatch')
    native=value['native']
    if value['retiring']:
     if not self._retire():raise RuntimeError('worker_retirement_unresolved')
     self.recover_async()
    return native
   except Exception:
    if self._retire():self.recover_async()
    raise


class NativeAccelerate:
 def __init__(self,runtime_dir,*,root=ROOT):
  self.root=Path(root).resolve();self.runtime=safe_runtime(self.root,runtime_dir)
  self.runtime.mkdir(parents=True,exist_ok=True)
  owner=self.runtime/'owner.json'
  if owner.exists():
   if owner.is_symlink() or json.loads(owner.read_text()).get('owner')!='swissknife-native-accelerate':raise ValueError('Foreign native accelerator runtime')
  elif any(self.runtime.iterdir()):raise ValueError('Refuse nonempty unowned accelerator runtime')
  else:owner.write_text(json.dumps({'owner':'swissknife-native-accelerate','work_complete':False,'completion_authority':False})+'\n')
  self.sdk_sha=digest(self.root/SDK_PATH);self.backend_sha=digest(self.root/BACKEND_PATH)
  self.service_sha=digest(self.root/SERVICE_PATH)
  self.observation_sources={name:digest(self.root/name) if (self.root/name).is_file() else None
    for name in [OBSERVATION_PATH,*[value[0] for value in OBSERVATION_TOOLS.values()]]}
  self.observation_slot=threading.Lock()
  self.slot=threading.Lock()
  self.worker=WarmInferenceWorker(self.root,{SDK_PATH:self.sdk_sha,BACKEND_PATH:self.backend_sha,SERVICE_PATH:self.service_sha})
 def cached(self):
  snapshot=Path.home()/'.cache/huggingface/hub/models--gpt2/snapshots'/SNAPSHOT
  return all((snapshot/name).is_file() for name in ['config.json','tokenizer.json','model.safetensors'])
 def sources_current(self):
  try:return (digest(self.root/SDK_PATH)==self.sdk_sha and digest(self.root/BACKEND_PATH)==self.backend_sha
              and digest(self.root/SERVICE_PATH)==self.service_sha
              and all((digest(self.root/name) if (self.root/name).is_file() else None)==expected
                      for name,expected in getattr(self,'observation_sources',{}).items()))
  except OSError:return False
 def health(self):
  current=self.sources_current()
  ready=current and self.cached() and self.worker.is_ready()
  return {'status':'ok' if ready else 'degraded','owner':'ipfs_accelerate_py','server':'swissknife-native-accelerate',
   'native_python_backend':True,'sdk_class':SDK_CLASS,'sdk_source_sha256':self.sdk_sha,'backend_source_sha256':self.backend_sha,
   'service_source_sha256':self.service_sha,'source_contract_current':current,
   'observability_sources_available':all(getattr(self,'observation_sources',{}).values()) and bool(getattr(self,'observation_sources',{})),
   'model':MODEL_ID,'model_snapshot':SNAPSHOT,'device':'cpu','engine_loaded':self.worker.is_ready(),'execution_mode':'bounded-warm-worker',
   'execution_timeout_seconds':30,'offline':True,'simulated':False,'echo_fallback':False,'external_provider_allowed':False,
   'work_complete':False,'completion_authority':False}
 def observe_native(self,tool,args,request_id,correlation):
  if set(args)-{'fixture_scope','correlation_id','dry_run'}:raise ValueError('Unsupported native observation arguments')
  if 'fixture_scope' in args and (type(args['fixture_scope']) is not str or not 0<len(args['fixture_scope'])<=256):raise ValueError('Invalid observation fixture scope')
  if args.get('dry_run') is True:raise ValueError('Preview is not an actual native SDK observation')
  sdk_path,sdk_class,method=OBSERVATION_TOOLS[tool]
  expected=getattr(self,'observation_sources',{})
  if not expected.get(OBSERVATION_PATH) or not expected.get(sdk_path):
   raise RuntimeError('Actual SDK observation sources are unavailable')
  if not self.observation_slot.acquire(blocking=False):raise RuntimeError('Native observation is busy; no duplicate sampling started')
  try:
   env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','IPFS_ACCEL_SKIP_CORE':'1'}
   completed=subprocess.run([str(self.root/PYTHON_PATH),str(self.root/OBSERVATION_PATH),'--tool',tool],
     text=True,capture_output=True,timeout=6,env=env,cwd=self.root)
   if completed.returncode:raise RuntimeError('Actual SDK observation failed: '+completed.stderr[-1500:])
   if not 0<len(completed.stdout.encode())<=65536:raise RuntimeError('Native observation exceeds its response bound')
   observed=json.loads(completed.stdout)
   if (not self.sources_current() or observed.get('schema')!='swissknife.native-accelerate-observation-result.v1'
       or observed.get('tool')!=tool or observed.get('sdk_class')!=sdk_class or observed.get('sdk_method')!=method
       or observed.get('sdk_source_path')!=sdk_path or observed.get('sdk_source_sha256')!=expected[sdk_path]
       or observed.get('observation_source_sha256')!=expected[OBSERVATION_PATH]
       or observed.get('parent_pid')!=os.getpid() or type(observed.get('pid')) is not int or observed['pid']<=0
       or observed.get('simulated') is not False or observed.get('inference_executed') is not False
       or observed.get('external_provider_called') is not False or type(observed.get('result')) is not dict):
    raise RuntimeError('Actual SDK observation provenance is invalid')
  finally:self.observation_slot.release()
  provenance={'schema':'swissknife.native-accelerate-observation.v1','owner':'ipfs_accelerate_py',
   'sdk_class':sdk_class,'sdk_method':method,'sdk_source_path':sdk_path,'sdk_source_sha256':expected[sdk_path],
   'observation_source_sha256':expected[OBSERVATION_PATH],'service_source_sha256':self.service_sha,
   'request_id':request_id,'observation_pid':observed['pid'],'service_pid':os.getpid(),
   'scope':observed['scope'],'correlation_id':correlation,'observed_at':dt.datetime.now(dt.timezone.utc).isoformat(),
   'simulated':False,'echo_fallback':False,'external_provider_called':False,'inference_executed':False,
   'work_complete':False,'completion_authority':False}
  payload={**observed['result'],'success':True,'tool':tool,'inference_executed':False,
   'backend':'ipfs_accelerate_py.hf_model_server.monitoring:actual-sdk-observation','native_provenance':provenance}
  if tool=='HealthChecker.check_detailed':payload['native_runtime']=self.health()
  return {'isError':False,'content':[{'type':'json','json':payload}],
   'receipt':{'adapter':'swissknife-native-accelerate','owner':'ipfs_accelerate_py','tool':tool,'status':'ok','native_provenance':provenance}}
 def call(self,tool,args):
  if tool == 'WorkflowCoordinator.submit_task' or (type(args) is dict and 'fixture_mode' in args):
   from native_supervisor_backend import supervise
   return supervise(self,tool,args)
  if not self.sources_current():
   raise RuntimeError('Native accelerator sources changed; reload the owned service before execution')
  if type(args) is not dict:raise ValueError('Tool arguments must be an object')
  requested_tool=tool;tool=ALIASES.get(tool,tool)
  if tool=='run_inference_job':args=inference_arguments(args,submission=requested_tool=='submit_task')
  if 'dry_run' in args and type(args['dry_run']) is not bool:raise ValueError('dry_run must be boolean')
  correlation=args.get('correlation_id')
  if correlation is not None and (type(correlation) is not str or len(correlation)>256):raise ValueError('Invalid correlation ID')
  request_id=str(uuid.uuid4());native=None
  if requested_tool in OBSERVATION_TOOLS:return self.observe_native(requested_tool,args,request_id,correlation)
  if tool=='run_inference_job':
   if set(args)-(CONTEXT_ARGS|{'model','model_id','input','input_data','max_new_tokens','max_length','backend','task'}):raise ValueError('Unsupported native inference arguments')
   models=[args[k] for k in ['model','model_id'] if k in args]
   inputs=[args[k] for k in ['input','input_data'] if k in args]
   if not models or not inputs or any(x!=models[0] for x in models) or any(x!=inputs[0] for x in inputs):
    raise ValueError('Explicit model/model_id and input/input_data are required; duplicate aliases must agree')
   model,text=models[0],inputs[0];tokens=args.get('max_new_tokens',MAX_NEW_TOKENS)
   requested_length=args.get('max_length',MAX_NEW_TOKENS)
   if type(requested_length) is not int or not 1<=requested_length<=64:raise ValueError('max_length must be1..64; server emits at most4newtokens')
   validate_request(model,text,tokens)
   tokens=min(tokens,requested_length)
   if args.get('backend','cpu')!='cpu':raise ValueError('Only the qualified CPU backend is supported')
   if args.get('task','text-generation')!='text-generation':raise ValueError('Only text-generation is supported')
   if args.get('dry_run') is True:raise ValueError('Preview is not actual native inference execution')
   if not self.slot.acquire(blocking=False):raise RuntimeError('Native CPU inference is busy; no duplicate generation started')
   try:
    job=self.runtime/'jobs'/request_id;safe_runtime(self.root,job)
    native=self.worker.request(request_id,job,model,text,tokens,correlation)
    payload=dict(native['result'])
    if not self.sources_current():
     raise RuntimeError('Native accelerator sources changed during execution')
    if (native.get('schema')!='swissknife.native-accelerate-execution-result.v1' or native.get('inference_executed') is not True
        or native.get('source_sha256')!=self.backend_sha or native.get('model')!=MODEL_ID
        or native.get('manager_source_sha256')!=self.sdk_sha
        or native.get('input')!=text or native.get('offline') is not True or native.get('external_provider_called') is not False
        or type(payload.get('generated_token_count')) is not int or not 1<=payload['generated_token_count']<=tokens
        or type(payload.get('generated_token_ids')) is not list or any(type(token) is not int or token<0 for token in payload['generated_token_ids'])
        or len(payload['generated_token_ids'])!=payload['generated_token_count'] or not payload.get('generated_text')
        or payload.get('simulated') is not False or payload.get('echo_fallback') is not False):raise RuntimeError('Native execution evidence is invalid')
    payload.update(job_id=request_id,task_id=request_id,model_id=MODEL_ID,status='completed',state='completed',inference_executed=True,
        execution_semantics='synchronous_completed_execution',queue_used=False,requested_tool=requested_tool,
        completed_at=dt.datetime.now(dt.timezone.utc).isoformat(),requested_max_length=requested_length,
        effective_max_new_tokens=tokens,server_max_new_tokens=MAX_NEW_TOKENS)
    method='execute_task'
   finally:self.slot.release()
  elif tool=='list_models':
   if set(args)-CONTEXT_ARGS:raise ValueError('Unsupported model-catalog arguments')
   if not self.cached():raise RuntimeError('Qualified cached model is unavailable')
   payload={'models':[{'id':MODEL_ID,'model_id':MODEL_ID,'task':'text-generation','device':'cpu','snapshot':SNAPSHOT}],
     'count':1,'backend_available':self.worker.is_ready(),'inference_executed':False};method='qualified_cached_model_catalog'
  elif tool=='hardware_profile':
   if set(args)-CONTEXT_ARGS:raise ValueError('Unsupported hardware-profile arguments')
   payload={'device':'cpu','cpu':{'available':True,'logical_cpu_count':os.cpu_count(),'worker_threads':2},'inference_executed':False};method='cpu_execution_placement'
  elif tool=='job_status':
   if set(args)-(CONTEXT_ARGS|{'job_id','task_id'}):raise ValueError('Unsupported job-status arguments')
   ids=[args[key] for key in ['job_id','task_id'] if key in args]
   if not ids or any(value!=ids[0] for value in ids):raise ValueError('Actual task/job UUID aliases must agree')
   job_id=ids[0]
   if type(job_id) is not str or str(uuid.UUID(job_id))!=job_id:raise ValueError('Actual returned job UUID required')
   path=safe_runtime(self.root,self.runtime/'jobs'/job_id/'mcp-result.json')
   if not path.is_file() or path.stat().st_size>131072:raise ValueError('Native execution record not found')
   saved=json.loads(path.read_text());payload=saved['content'][0]['json']
   if payload.get('job_id')!=job_id:raise ValueError('Native execution record identity mismatch')
   payload={**payload,'read_from_execution_record':True};method='completed_execution_record'
  else:raise ValueError('Unsupported native accelerator tool')
  provenance={'schema':SCHEMA,'owner':'ipfs_accelerate_py','sdk_class':SDK_CLASS,'sdk_method':method,
   'sdk_source_path':SDK_PATH,'sdk_source_sha256':self.sdk_sha,'backend_source_sha256':self.backend_sha,
   'service_source_sha256':self.service_sha,'request_id':request_id,'model':MODEL_ID,'model_snapshot':SNAPSHOT,
   'device':'cpu','offline':True,'simulated':False,'echo_fallback':False,'external_provider_called':False,
   'correlation_id':correlation,'observed_at':dt.datetime.now(dt.timezone.utc).isoformat(),'work_complete':False,'completion_authority':False}
  if native is not None:
   provenance['model_cache_path']=native.get('model_cache_path')
   provenance['generated_token_count']=payload['generated_token_count']
   provenance['warm_worker']=native['warm_worker']
  payload={**payload,'success':True,'backend':'ipfs_accelerate_py.inference_backend_manager:offline-gpt2-cpu','native_provenance':provenance}
  result={'isError':False,'content':[{'type':'json','json':payload}],'receipt':{'adapter':'swissknife-native-accelerate','owner':'ipfs_accelerate_py','tool':requested_tool,'status':'ok','native_provenance':provenance}}
  if native is not None:(self.runtime/'jobs'/request_id/'mcp-result.json').write_text(json.dumps(result,indent=2)+'\n')
  return result

def dispatch(backend,request):
 if type(request) is not dict or request.get('jsonrpc')!='2.0':raise ValueError('JSON-RPC2.0 required')
 method=request.get('method');params=request.get('params',{})
 if type(params) is not dict:raise ValueError('Params must be an object')
 if method=='notifications/initialized':return None
 if method=='initialize':result={'protocolVersion':'2024-11-05','capabilities':{'tools':{}},'serverInfo':{'name':'swissknife-native-accelerate','version':'1.0.0'}}
 elif method=='tools/list':result={'tools':TOOLS}
 elif method=='tools/call':result=backend.call(params.get('name'),params.get('arguments',{}))
 elif method=='ping':result={}
 else:raise ValueError('Unsupported native MCP method')
 return {'jsonrpc':'2.0','id':request.get('id'),'result':result}

class Server(ThreadingHTTPServer):
 daemon_threads=True;allow_reuse_address=False;request_queue_size=8
 def __init__(self,address,backend):self.backend=backend;super().__init__(address,Handler)
 def service_actions(self):
  # Only the installed, explicitly supervised campaign unit opts into exit.
  # systemd Restart=on-failure reloads this owned process and its cgroup.
  if os.environ.get('SVF_RESTART_ON_SOURCE_DRIFT')=='1' and not self.backend.sources_current():
   os._exit(75)
  if self.backend.sources_current():self.backend.worker.recover_async()
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def setup(self):super().setup();self.connection.settimeout(35)
 def send(self,code,value):
  raw=json.dumps(value).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_GET(self):
  if self.path not in ['/health','/mcp/health']:self.send(404,{'error':'not_found'});return
  self.send(200,self.server.backend.health())
 def do_POST(self):
  if self.path!='/mcp':self.send(404,{'error':'not_found'});return
  request={}
  try:
   length=int(self.headers.get('Content-Length','0'))
   if not 0<length<=MAX_REQUEST_BYTES:raise ValueError('Invalid bounded request length')
   request=json.loads(self.rfile.read(length));result=dispatch(self.server.backend,request)
   self.send(200,result if result is not None else {})
  except Exception as error:self.send(200,{'jsonrpc':'2.0','id':request.get('id') if isinstance(request,dict) else None,'error':{'code':-32000,'message':str(error)}})

def main():
 p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=18313);p.add_argument('--runtime-dir',default=str(NAMESPACE/'backends/native_accelerate'));args=p.parse_args()
 if args.host!='127.0.0.1' or not 1024<=args.port<=65535:raise ValueError('Native service requires a loopback port')
 os.umask(0o077);backend=NativeAccelerate(args.runtime_dir)
 backend.worker.start()
 if backend.health()['status']!='ok':raise RuntimeError('Native cached model/dependencies are unavailable')
 try:Server((args.host,args.port),backend).serve_forever()
 finally:backend.worker.close()
if __name__=='__main__':main()
