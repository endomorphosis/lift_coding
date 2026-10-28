#!/usr/bin/env python3
"""Protected same-process SDK observations; not an authenticated security boundary.

Only fixed native services run. Instrumented methods always delegate to the
original pinned SDK code. Immutable observations complement independent HTTP,
DB, output and kernel evidence; they cannot replace those checks. Same-UID code
can interfere with this observer, so events do not prove hostile-code isolation.
"""
from __future__ import annotations
import argparse, dataclasses, datetime as dt, enum, functools, hashlib
import importlib.abc, importlib.machinery, importlib.util, inspect, json, marshal
import math, os, re, runpy, stat, subprocess, sys, threading, time, uuid
from pathlib import Path
from collections.abc import Mapping

ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = 'scripts/svf_backends/foundation_native_entrypoint.py'
REGISTRATION = 'config/swissknife_visual_functional_foundation_owners.json'
RUNTIME = 'data/agent_supervisor/swissknife_visual_functional'
EVENT_SCHEMA = 'swissknife.foundation-sdk-call-event.v1'
SNAPSHOT_SCHEMA = 'swissknife.foundation-sdk-call-snapshot.v1'
MAX_EVENTS, MAX_EVENT_BYTES, MAX_TOTAL_BYTES = 8192, 16384, 32 * 1024 * 1024
FAMILIES = {
 'kit-pubsub': ('swissknife-visual-functional-native-kit.service', 'scripts/svf_backends/native_kit_service.py',
  ['--host','127.0.0.1','--port','18314','--kubo-api','http://127.0.0.1:5031']),
 'accelerate-supervisor': ('swissknife-visual-functional-native-accelerate.service', 'scripts/svf_backends/native_accelerate_service.py',
  ['--host','127.0.0.1','--port','18313','--runtime-dir',RUNTIME+'/backends/native_accelerate']),
}
TARGETS = {
 'ipfs_kit_py.assurance.pinned_pubsub': ('kit-pubsub','external/ipfs_kit/ipfs_kit_py/assurance/pinned_pubsub.py',
  {'LivePinnedPubsubAdapter': ('__init__','subscribe','pubsub_publish','pubsub_peers','swarm_connect')}),
 'ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository': ('accelerate-supervisor',
  'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/intent_repository.py',
  {'IntentRepository': ('__init__','upsert_objective','upsert_goal','link_goal_edge','upsert_plan','upsert_task',
   'record_validation_result','cas_task_status','record_attempt','get_task')}),
 'ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source': ('accelerate-supervisor',
  'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/task_sources/database_task_source.py',
  {'DatabaseTaskSource': ('__init__','ready_tasks','compare_and_set_status','record_validation_result','get_task')}),
 'ipfs_accelerate_py.agent_supervisor.verification.process_runner': ('accelerate-supervisor',
  'external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/verification/process_runner.py',
  {'VerificationProcessRunner': ('run',)}),
}
_ID_KEYS = {'objective_id','objective_alias','parent_objective_id','goal_cid','goal_alias','parent_goal_cid','child_goal_cid',
 'plan_cid','plan_alias','task_cid','task_alias','task_cid_or_alias','attempt_id','request_id','operation_id','receipt_cid',
 'edge_kind','status','new_status','previous_status','outcome','evidence_digest','lease_id','cancellation_id',
 'terminal_status','disposition','state','effect_kind','request_id','operation_id','event_id','event_type','subject_id','recorded_at'}
_SCALAR_KEYS = _ID_KEYS | {'expected_revision','revision','changed','event_cursor','accepted','durable','publication_allowed',
 'timed_out','cancelled','unavailable','process_started','pid','process_group_id','exit_code','duration_ms',
 'allow_completion_without_evidence','global_sequence','success','simulated','limit','automatic_only','task_shard_count','task_shard_index'}
_LIST_KEYS = {'dependencies','evidence_digests','task_cids','task_aliases','completed_ids','blocked_ids'}


def sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def canonical(value) -> bytes:
 return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def _regular(path):
 info=path.lstat()
 if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o022 or path.is_symlink():
  raise ValueError('observer needs an owner-controlled regular file')
 return info

def _path(root,relative):
 root=Path(root);p=Path(relative)
 if not root.is_absolute() or root.resolve()!=root or p.is_absolute() or '..'in p.parts or not p.parts:
  raise ValueError('unsafe observer path')
 target=root/p
 if target.resolve()!=target:raise ValueError('observer symlink path refused')
 return target

def _read(root,relative,limit=MAX_EVENT_BYTES):
 p=_path(root,relative);info=_regular(p)
 if info.st_size>limit:raise ValueError('observer input exceeds byte bound')
 raw=p.read_bytes()
 if len(raw)>limit:raise ValueError('observer input grew beyond bound')
 return raw

def _mkdir(root,path):
 relative=path.relative_to(root);current=root
 for part in relative.parts:
  current/=part
  if current.exists():
   info=current.lstat()
   if not stat.S_ISDIR(info.st_mode) or current.is_symlink() or info.st_uid!=os.getuid() or (current.is_relative_to(root/RUNTIME/'backends/foundation-call-witness') and info.st_mode&0o022):
    raise ValueError('unsafe witness directory')
  else:current.mkdir(mode=0o700)

def _immutable(root,path,value):
 data=canonical(value)
 if len(data)>MAX_EVENT_BYTES:raise ValueError('observer event exceeds byte bound')
 _mkdir(root,path.parent);tmp=path.parent/('.pending-'+uuid.uuid4().hex)
 try:
  fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb')as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
  os.link(tmp,path,follow_symlinks=False)
  parent=os.open(path.parent,os.O_DIRECTORY|os.O_NOFOLLOW)
  try:os.fsync(parent)
  finally:os.close(parent)
 finally:tmp.unlink(missing_ok=True)
 return {'path':path.relative_to(root).as_posix(),'sha256':sha(data),'bytes':len(data)}

def _birth():return Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
def _directory(root,family,invocation_id):
 if family not in FAMILIES or type(invocation_id)is not str or re.fullmatch('[0-9a-f]{32}',invocation_id)is None:
  raise ValueError('unknown family or invalid systemd invocation identity')
 return _path(root,RUNTIME+'/backends/foundation-call-witness/'+family+'/'+invocation_id)

def _scalar(value):
 if isinstance(value,enum.Enum):value=value.value
 if value is None or type(value)in(bool,int):return value
 if type(value)is str and len(value)<=512 and not any(ord(c)<32 for c in value):return value
 return None

def _fields(value):
 if isinstance(value,Mapping):return value
 if dataclasses.is_dataclass(value)and not isinstance(value,type):
  return {field.name:getattr(value,field.name)for field in dataclasses.fields(value)if field.name in _SCALAR_KEYS|{'stdout','stderr','task','tasks','command_argv','digest','sha256','bytes','byte_count','captured_byte_count','total_bytes','truncated','cid'}}
 return {}

def _argv(value,root):
 if not isinstance(value,(list,tuple))or not 4<=len(value)<=24 or not all(type(x)is str and len(x)<=512 for x in value):return {}
 raw=canonical(list(value));worker=str(root/'scripts/svf_backends/fixed_supervisor_worker.py');validator=str(root/'scripts/svf_backends/fixed_supervisor_output_validator.py')
 result={'command_argv_sha256':sha(raw),'command_argv_bytes':len(raw)}
 if tuple(value[1:3])!=('-I','-B')or value[3]not in {worker,validator}or len(value[4:])%2:return result
 pairs=list(zip(value[4::2],value[5::2]));params=dict(pairs)
 required={'--runtime-root','--run-id','--stage','--challenge'}|({'--mode'}if value[3]==worker else set())
 if len(params)!=len(pairs)or set(params)!=required:return result
 runtime=root/RUNTIME/'backends/supervisor-fixtures'
 try:run_id=str(uuid.UUID(params['--run-id']))
 except ValueError:return result
 if params['--runtime-root']!=str(runtime)or params['--run-id']!=run_id or params['--stage']not in {'a','b'}or re.fullmatch('[0-9a-f]{32}',params['--challenge'])is None or params.get('--mode','normal')not in {'normal','timeout','cancel'}:return result
 result.update(command_argv=list(value),run_id=run_id,database_path=(runtime/run_id/'control.duckdb').relative_to(root).as_posix())
 return result

def _database(value,root):
 if not isinstance(value,(str,Path)):return {}
 p=Path(value);base=root/RUNTIME/'backends/supervisor-fixtures'
 if not p.is_absolute():p=root/p
 try:parts=p.relative_to(base).parts
 except ValueError:return {'database_scope':'outside_fixture'}
 if len(parts)!=2 or parts[1]!='control.duckdb':return {'database_scope':'outside_fixture'}
 try:identity=str(uuid.UUID(parts[0]))
 except ValueError:return {'database_scope':'outside_fixture'}
 if identity!=parts[0]or p.resolve()!=p:return {'database_scope':'outside_fixture'}
 return {'database_path':p.relative_to(root).as_posix(),'run_id':identity}

def _runner_policy(instance,root):
 runner=sys.modules.get('ipfs_accelerate_py.agent_supervisor.verification.process_runner')
 resources=sys.modules.get('ipfs_accelerate_py.agent_supervisor.runtime.resource_scheduler')
 scheduler=getattr(instance,'_scheduler',None)
 relative='external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/resource_scheduler.py'
 policy={'require_resource_lease':getattr(instance,'_require_resource_lease',None)is True,
  'host_snapshot_is_none':getattr(instance,'_host_snapshot','missing')is None,
  'popen_is_subprocess_popen':getattr(instance,'_popen',None)is subprocess.Popen,
  'clock_is_time_monotonic':getattr(instance,'_clock',None)is time.monotonic,
  'sleep_is_time_sleep':getattr(instance,'_sleep',None)is time.sleep,
  'scheduler_is_sdk_type':runner is not None and type(scheduler)is getattr(runner,'ResourceScheduler',None),
  'host_sampler_is_sdk_function':resources is not None and getattr(scheduler,'host_sampler',None)is getattr(resources,'sample_host_resources','missing')}
 if resources is not None and Path(resources.__file__).resolve()==root/relative:
  policy.update(resource_scheduler_source_path=relative,resource_scheduler_source_sha256=sha(_read(root,relative,16*1024*1024)))
 return policy

def _arguments(bound,root):
 args=dict(bound.arguments);instance=args.pop('self',None);out={}
 for key,value in args.items():
  if key in _SCALAR_KEYS and (value is None or _scalar(value)is not None):out[key]=_scalar(value)
  elif key in _LIST_KEYS and isinstance(value,(list,tuple,set))and len(value)<=64:
   if all(type(x)is str and len(x)<=256 for x in value):out[key]=sorted(value)if isinstance(value,set)else list(value)
  elif key=='argv':
   command=_argv(value,root);out.update(command)
   if 'command_argv'in command:out['argv']=command['command_argv']
  elif key=='command':
   command=getattr(value,'argv',None)
   if command is not None:out.update(_argv(command,root))
  elif key=='validations'and isinstance(value,(list,tuple))and len(value)<=8:
   out['validations_sha256']=sha(canonical(value)) if all(isinstance(x,(list,tuple,str,dict))for x in value)else None
 if instance is not None:
  out.update(_database(getattr(instance,'database_path',None),root))
  if 'command'in args:out['runner_policy']=_runner_policy(instance,root)
 out.update(_database(args.get('database_path'),root))
 if args.get('intent')is not None:out.update(_database(getattr(args['intent'],'database_path',None),root))
 for key in ['api_url','_api_url']:
  api=args.get('api_url') if 'api_url'in args else getattr(instance,key,None)
  if type(api)is str and api in {'http://127.0.0.1:5032','http://127.0.0.1:5033'}:out['api_url']=api;break
 topic=args.get('topic')
 if type(topic)is str and re.fullmatch(r'svf\.pubsub\.[0-9a-f]{32}(?:\.ack)?',topic):out['topic']=topic
 data=args.get('data')
 if type(data)is bytes:
  out.update(data_sha256=sha(data),data_bytes=len(data))
  if len(data)<=4096:
   try:message=json.loads(data)
   except(ValueError,UnicodeError):message=None
   if type(message)is dict:
    value=message.get('message_id')
    if type(value)is str:
     try:
      if str(uuid.UUID(value))==value:out['message_id']=value
     except ValueError:pass
 # Never retain payload/body/SQL/environment/prompt/stdout text or arbitrary locals.
 return out

def _result(value,root):
 source=_fields(value);out={}
 for key,item in source.items():
  if key in _SCALAR_KEYS and (item is None or _scalar(item)is not None):out[key]=_scalar(item)
  elif key in {'command_argv'}:out.update(_argv(item,root))
  elif key in {'stdout','stderr'}:
   fields=_fields(item)
   out[key]={k:fields[k]for k in ['digest','cid','sha256','bytes','byte_count','captured_byte_count','total_bytes','truncated']if k in fields and(type(fields[k])in(int,bool)or type(fields[k])is str and len(fields[k])<=256)}
  elif key=='task':out['task']=_result(item,root)
  elif key=='tasks'and isinstance(item,(list,tuple))and len(item)<=64:
   out['tasks']=[_result(x,root)for x in item];out['task_cids']=[row['task_cid']for row in out['tasks']if 'task_cid'in row]
 if isinstance(value,(list,tuple))and len(value)<=64:out['items']=[_result(x,root)if not isinstance(x,str)else _scalar(x)for x in value]
 return out

def _capture(root,base,manifest,*,active):
 path=base/'capture.json'
 if not path.exists()and not path.is_symlink():return None
 raw=_read(root,path.relative_to(root));value=json.loads(raw)
 keys={'schema','capture_id','family','invocation_id','task_id','native_process','lease_id','foreground_birth','issued_at','expires_at','expected_sources','observational_only','completion_authority'}
 if type(value)is not dict or set(value)!=keys or value['schema']!='swissknife.foundation-sdk-call-capture.v1':raise ValueError('invalid capture authorization')
 if value['family']!=manifest['family']or value['invocation_id']!=manifest['invocation_id']or value['native_process']!=manifest['identity']or value['task_id']!={'kit-pubsub':'SVF-043','accelerate-supervisor':'SVF-044'}[value['family']]:raise ValueError('foreign capture authorization')
 for key in ['capture_id','lease_id']:
  if type(value[key])is not str or str(uuid.UUID(value[key]))!=value[key]:raise ValueError('invalid capture owner identity')
 if type(value['foreground_birth'])is not str or not value['foreground_birth'].isdigit()or value['observational_only']is not True or value['completion_authority']is not False:raise ValueError('invalid capture owner flags')
 issued,expires=value['issued_at'],value['expires_at']
 if any(type(x)not in(int,float)or not math.isfinite(x)for x in [issued,expires])or not 0<expires-issued<=300:raise ValueError('capture deadline is not bounded')
 expected=value['expected_sources']
 if type(expected)is not dict or not expected or any(type(h)is not str or re.fullmatch('[0-9a-f]{64}',h)is None or manifest['source_sha256'].get(name)!=h for name,h in expected.items()):raise ValueError('capture source contract differs from loaded service')
 if active and not issued<=time.time()<=expires:return None
 return {'reference':{'path':path.relative_to(root).as_posix(),'sha256':sha(raw),'bytes':len(raw)},'value':value}

class WitnessSink:
 def __init__(self,root,*,family,invocation_id,identity,observer_sha256,source_sha256):
  self.root=Path(root);self.family=family;self.invocation_id=invocation_id;self.identity=dict(identity);self.directory=_directory(self.root,family,invocation_id)
  self.observer_sha256=observer_sha256;self.source_sha256=dict(source_sha256);self.lock=threading.RLock();self.local=threading.local();self.sequence=0;self.total_bytes=0;self.disabled=set()
  self.manifest={'schema':'swissknife.foundation-sdk-call-observer.v1','family':family,'invocation_id':invocation_id,'identity':self.identity,'observer_sha256':observer_sha256,'source_sha256':self.source_sha256,'observational_only':True,'authenticated_origin':False,'completion_authority':False}
  _immutable(self.root,self.directory/'observer.json',self.manifest)
 def capture(self):
  try:authorization=_capture(self.root,self.directory,self.manifest,active=True)
  except (ValueError,OSError,KeyError,TypeError):return None
  if authorization is None or authorization['value']['capture_id']in self.disabled:return None
  return authorization
 def _fault(self,capture,error):
  identity=capture['value']['capture_id'];self.disabled.add(identity)
  value={'schema':'swissknife.foundation-sdk-call-capture-fault.v1','family':self.family,'invocation_id':self.invocation_id,**self.identity,'capture_id':identity,'capture_sha256':capture['reference']['sha256'],'at':dt.datetime.now(dt.timezone.utc).isoformat(),'error_type':type(error).__name__,'observational_only':True,'completion_authority':False}
  try:_immutable(self.root,self.directory/'faults'/(identity+'.json'),value)
  except Exception:pass  # Failure never changes ordinary SDK behavior; missing trace still cannot qualify.
 def emit(self,*,capture,call_id,parent_call_id,phase,sdk,arguments,result=None,error_type=None,frame=None,caller=None):
  with self.lock:
   current=self.capture()
   if current is None or current['reference']!=capture['reference']:return None
   try:
    if self.sequence>=MAX_EVENTS:raise ValueError('observer event-count bound reached')
    self.sequence+=1
    value={'schema':EVENT_SCHEMA,'family':self.family,'invocation_id':self.invocation_id,**self.identity,'capture_id':capture['value']['capture_id'],'capture_sha256':capture['reference']['sha256'],'thread_id':threading.get_ident(),'sequence':self.sequence,'call_id':call_id,'parent_call_id':parent_call_id,'phase':phase,'at':dt.datetime.now(dt.timezone.utc).isoformat(),'monotonic_ns':time.monotonic_ns(),'sdk':sdk,'arguments':arguments,'observational_only':True,'completion_authority':False}
    if result is not None:value['result']=result
    if error_type is not None:value['error_type']=error_type
    if frame is not None:value['frame']=frame
    if caller is not None:value['caller']=caller
    size=len(canonical(value))
    if self.total_bytes+size>MAX_TOTAL_BYTES:raise ValueError('observer total byte bound reached')
    ref=_immutable(self.root,self.directory/'events'/f'{self.sequence:08d}-{call_id}-{phase}.json',value);self.total_bytes+=size
    return ref
   except Exception as error:self._fault(capture,error);return None

class SubscriptionObservation:
 def __init__(self,wrapped,sink,call_id,parent,sdk,args,check,capture):self.wrapped=wrapped;self.sink=sink;self.call_id=call_id;self.parent=parent;self.sdk=sdk;self.args=args;self.check=check;self.capture=capture;self.iterator=None;self.active=wrapped;self.entered=False;self.exited=False;self.closed=False
 def __enter__(self):
  self.active=self.wrapped.__enter__();self.entered=True;return self
 def __exit__(self,*args):
  if self.exited:return False
  self.exited=True;self.closed=True
  return self.wrapped.__exit__(*args)
 def __iter__(self):self.iterator=iter(self.active);return self
 def __next__(self):
  if self.closed:raise StopIteration
  if self.sink.capture()is not None:self.check()
  value=next(self.iterator if self.iterator is not None else self.active)
  raw=value.get('raw_frame')if isinstance(value,dict)else None
  if type(raw)is bytes:
   self.sink.emit(capture=self.capture,call_id=self.call_id,parent_call_id=self.parent,phase='stream',sdk=self.sdk,arguments=self.args,frame={'sha256':sha(raw),'bytes':len(raw)})
  return value
 def close(self):
  if self.closed:return None
  self.closed=True
  try:
   closer=getattr(self.active,'close',None)
   if callable(closer):closer()
   elif self.active is not self.wrapped:
    closer=getattr(self.wrapped,'close',None)
    if callable(closer):closer()
   elif not self.entered:
    generator=getattr(self.wrapped,'gen',None)
    if inspect.isgenerator(generator):generator.close()
  finally:
   if self.entered and not self.exited:self.__exit__(None,None,None)
 def __getattr__(self,name):return getattr(self.active,name)

def _caller(root):
 result=[];frame=inspect.currentframe().f_back
 try:
  for _ in range(10):
   if frame is None:break
   p=Path(frame.f_code.co_filename)
   if p.is_absolute()and p.is_relative_to(root)and p.is_file():
    result.append({'path':p.relative_to(root).as_posix(),'line':frame.f_lineno,'function':frame.f_code.co_name,'sha256':sha(p.read_bytes())})
   frame=frame.f_back
 finally:del frame
 return result[:6]

def instrument_class(cls,methods,*,sink,sdk_module,source_path,source_sha256,check):
 for method in methods:
  original=getattr(cls,method,None)
  if not inspect.isfunction(original)or getattr(original,'__svf_observed__',False):
   if getattr(original,'__svf_observed__',False):continue
   raise ValueError('SDK method is missing or not an ordinary original function')
  unwrapped=inspect.unwrap(original)
  if not inspect.isfunction(unwrapped)or unwrapped.__module__!=sdk_module or Path(unwrapped.__code__.co_filename).resolve()!=sink.root/source_path:
   raise ValueError('SDK original method code is not from its pinned source')
  sdk={'module':sdk_module,'class':cls.__name__,'method':method,'source_path':source_path,'source_sha256':source_sha256,'code_sha256':sha(marshal.dumps(unwrapped.__code__))}
  signature=inspect.signature(original)
  def decorate(fn,description,signature):
   @functools.wraps(fn)
   def observed(*args,**kwargs):
    capture=sink.capture()
    if capture is None:return fn(*args,**kwargs)
    check();bound=signature.bind(*args,**kwargs);bound.apply_defaults();safe=_arguments(bound,sink.root);call_id=str(uuid.uuid4());stack=getattr(sink.local,'stack',[]);parent=stack[-1]if stack else None
    recorded=sink.emit(capture=capture,call_id=call_id,parent_call_id=parent,phase='enter',sdk=description,arguments=safe,caller=_caller(sink.root))
    if recorded is None:return fn(*args,**kwargs)
    sink.local.stack=[*stack,call_id]
    try:
     value=fn(*args,**kwargs)
     if sink.capture()is not None:check()
     returned=sink.emit(capture=capture,call_id=call_id,parent_call_id=parent,phase='return',sdk=description,arguments=safe,result=_result(value,sink.root))
     if description['method']=='subscribe'and returned is not None:value=SubscriptionObservation(value,sink,call_id,parent,description,safe,check,capture)
     return value
    except BaseException as error:
     try:sink.emit(capture=capture,call_id=call_id,parent_call_id=parent,phase='error',sdk=description,arguments=safe,error_type=type(error).__name__)
     except Exception:pass
     raise
    finally:sink.local.stack=stack
   observed.__svf_observed__=True
   return observed
  setattr(cls,method,decorate(original,sdk,signature))

class SDKObserverFinder(importlib.abc.MetaPathFinder):
 def __init__(self,root,*,family,sink,pin):self.root=Path(root);self.family=family;self.sink=sink;self.pin=pin
 def instrument(self,module,name):
  family,relative,classes=TARGETS[name];expected=self.pin(relative);path=_path(self.root,relative)
  if Path(module.__file__).resolve()!=path or sha(_read(self.root,relative,16*1024*1024))!=expected:raise ValueError('SDK import source differs from its pinned owner')
  def check():
   if self.pin(relative)!=expected:raise ValueError('SDK pin changed since import; reload owned service')
   if sha(_read(self.root,relative,16*1024*1024))!=expected:raise ValueError('SDK source changed since import; reload owned service')
  for name,methods in classes.items():instrument_class(getattr(module,name),methods,sink=self.sink,sdk_module=module.__name__,source_path=relative,source_sha256=expected,check=check)
 def find_spec(self,fullname,path=None,target=None):
  if fullname not in TARGETS or TARGETS[fullname][0]!=self.family:return None
  original=importlib.machinery.PathFinder.find_spec(fullname,path)
  if original is None:return None  # Absent future SDK remains absent; no fabricated module.
  expected=_path(self.root,TARGETS[fullname][1])
  if original.origin!=str(expected):raise ImportError('SDK import escaped pinned owner checkout')
  loader=original.loader;observer=self
  class Loader(importlib.abc.Loader):
   def create_module(self,spec):return loader.create_module(spec)if hasattr(loader,'create_module')else None
   def exec_module(self,module):
    relative=TARGETS[fullname][1];fingerprint=observer.pin(relative)
    raw=_read(observer.root,relative,16*1024*1024)
    if sha(raw)!=fingerprint:raise ImportError('SDK source differs before execution')
    code=compile(raw,str(_path(observer.root,relative)),'exec',dont_inherit=True)
    exec(code,module.__dict__);observer.instrument(module,fullname)
  original.loader=Loader();return original

def read_snapshot(root,*,family,invocation_id):
 root=Path(root);base=_directory(root,family,invocation_id);manifest=json.loads(_read(root,(base/'observer.json').relative_to(root)))
 if manifest.get('schema')!='swissknife.foundation-sdk-call-observer.v1'or manifest.get('family')!=family or manifest.get('invocation_id')!=invocation_id or manifest.get('observational_only')is not True or manifest.get('authenticated_origin')is not False or manifest.get('completion_authority')is not False:
  raise ValueError('observer manifest does not match requested bounded scope')
 paths=sorted((base/'events').glob('*.json'))if(base/'events').exists()else[]
 if len(paths)>MAX_EVENTS:raise ValueError('observer event count exceeded')
 capture=_capture(root,base,manifest,active=False)
 faults=[]
 for path in sorted((base/'faults').glob('*.json'))if(base/'faults').exists()else[]:
  raw=_read(root,path.relative_to(root));fault=json.loads(raw)
  if len(faults)>=16:raise ValueError('too many capture fault records')
  faults.append({'reference':{'path':path.relative_to(root).as_posix(),'sha256':sha(raw),'bytes':len(raw)},'event':fault})
 events=[];total=0;seen=set()
 for path in paths:
  raw=_read(root,path.relative_to(root));total+=len(raw)
  if total>MAX_TOTAL_BYTES:raise ValueError('observer snapshot byte bound exceeded')
  value=json.loads(raw);sequence=value.get('sequence')
  if value.get('schema')!=EVENT_SCHEMA or value.get('family')!=family or value.get('invocation_id')!=invocation_id or any(value.get(k)!=v for k,v in manifest['identity'].items())or type(sequence)is not int or sequence in seen or value.get('observational_only')is not True or value.get('completion_authority')is not False:
   raise ValueError('observer event identity mismatch')
  seen.add(sequence);events.append({'reference':{'path':path.relative_to(root).as_posix(),'sha256':sha(raw),'bytes':len(raw)},'event':value})
 return {'schema':SNAPSHOT_SCHEMA,'family':family,'invocation_id':invocation_id,'identity':manifest['identity'],'observer':manifest,'capture':capture,'capture_faults':faults,'events':events,'observational_only':True,'completion_authority':False}

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--family',choices=sorted(FAMILIES),required=True);args=parser.parse_args(argv);root=ROOT
 if Path(__file__).resolve()!=root/ENTRYPOINT:raise ValueError('protected entrypoint must run from its fixed checkout path')
 config_raw=_read(root,REGISTRATION,512*1024);cfg=json.loads(config_raw);protected=cfg.get('protected_sha256',{})
 if protected.get(ENTRYPOINT)!=sha(Path(__file__).read_bytes()):raise ValueError('entrypoint lacks its independently registered self pin')
 helper_path='scripts/svf_backends/foundation_service_ownership.py'
 if protected.get(helper_path)!=sha(_read(root,helper_path,256*1024)):raise ValueError('ownership helper pin differs')
 spec=importlib.util.spec_from_file_location('_svf_fixed_foundation_ownership',root/helper_path);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper);helper._registration(root)
 unit,service,service_args=FAMILIES[args.family];invocation=os.environ.get('INVOCATION_ID','')
 try:identity=helper.unit_identity(root,unit,cfg['units'][unit])
 except helper.ServicePortsNotReady as pending:identity=pending.identity
 if identity['pid']!=os.getpid()or identity['start_ticks']!=_birth()or identity['invocation_id']!=invocation:raise ValueError('entrypoint is not its exact registered native process')
 registry_sha=sha(config_raw);source_contract={}
 manifest_sources=set(cfg['families'][args.family]['required_sources'])
 manifest_sources.update(rule[1]for rule in TARGETS.values()if rule[0]==args.family)
 if args.family=='accelerate-supervisor':manifest_sources.update({'scripts/svf_backends/fixed_supervisor_worker.py','scripts/svf_backends/fixed_supervisor_output_validator.py','external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/runtime/resource_scheduler.py'})
 for name in sorted(manifest_sources):
  p=_path(root,name);source_contract[name]=sha(_read(root,name,16*1024*1024))if p.exists()else None
 sink=WitnessSink(root,family=args.family,invocation_id=invocation,identity={'pid':os.getpid(),'start_ticks':_birth()},observer_sha256=protected[ENTRYPOINT],source_sha256=source_contract)
 def pin(relative):
  if sha(_read(root,REGISTRATION,512*1024))!=registry_sha or sha(_read(root,ENTRYPOINT,256*1024))!=protected[ENTRYPOINT]:raise ValueError('observer registration/source changed; reload owned service')
  for name,fingerprint in source_contract.items():
   if fingerprint is not None and sha(_read(root,name,16*1024*1024))!=fingerprint:raise ValueError('loaded native service source changed; reload owned service')
  if relative in protected:return protected[relative]
  ledger=json.loads(_read(root,RUNTIME+'/owned-source-hashes.json',4*1024*1024));expected=ledger.get(relative)
  if type(expected)is not str or re.fullmatch('[0-9a-f]{64}',expected)is None:raise ValueError('future SDK source lacks independent current ownership pin')
  return expected
 finder=SDKObserverFinder(root,family=args.family,sink=sink,pin=pin);sys.meta_path.insert(0,finder)
 for name,module in list(sys.modules.items()):
  if name in TARGETS and TARGETS[name][0]==args.family:finder.instrument(module,name)
 for relative in ['scripts/svf_backends','external/ipfs_kit','external/ipfs_accelerate']:sys.path.insert(0,str(root/relative))
 sys.argv=[str(root/service),*service_args];runpy.run_path(str(root/service),run_name='__main__');return 0
if __name__=='__main__':raise SystemExit(main())
