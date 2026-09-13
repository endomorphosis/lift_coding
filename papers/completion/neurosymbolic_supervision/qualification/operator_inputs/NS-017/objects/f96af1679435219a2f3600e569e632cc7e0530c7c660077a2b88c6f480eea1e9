"""Root-owned single-POST development proposer; no CLI, tools or fallback.

The service consumes its durable one-use grant before propose_http. Credentials
are fetched only by the host and sent through Docker stdin, never argv/env/files.
Child executes only this fixed standard-library code, never returned source.
"""
from pathlib import Path
import hashlib,json,os,stat,subprocess,sys,time,uuid
IMAGE='sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6'
ENDPOINT='https://api.x.ai/v1/chat/completions'
PROFILE={'schema':'ns-historical-http-profile/v1','transport':'operator_host_fixed_https_json_edits/v1','endpoint':ENDPOINT,'requested_model':'grok-4.6','expected_served_aliases':['grok-4.6'],'reasoning_effort':None,'reasoning_policy':'parameter omitted; no served-effort attestation','max_tokens':4096,'request_serialized_bytes_max':65536,'response_bytes_max':1048576,'max_patch_bytes':16384,'max_edits':32,'wall_seconds_max':600,'child_absolute_wall_seconds':595,'socket_timeout_seconds':590,'cpu_count':1,'memory_bytes':2147483648,'pids':32,'runtime':'runc','image':IMAGE,'max_http_posts':1,'retries':0,'fallback_allowed':False,'tools':[],'context_policy':'ns-pilot-AB-common-context/v1: same public raw spans; B adds real native source-linked semantic records; exact omissions; no window truncation'}
DOCKER=['/usr/bin/docker','--host=unix:///var/run/docker.sock']
def require(ok,msg):
 if not ok:raise ValueError(msg)
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(data):return hashlib.sha256(data).hexdigest()
SYSTEM_PROMPT = (
 'Produce the final source edits in this single response. Return only the JSON object '
 'required by the response schema, with no plan, commentary, markdown or tool calls. '
 'No filesystem, terminal, web or other tools are available, and there is no later tool round. '
 'The legacy mention of file tools in task text does not apply to this HTTP request. '
 'Use only the supplied public pre-fix source spans and structural facts. Edit only the '
 'listed implementation paths; leave public tests and all other protected inputs unchanged. '
 'Every old string must be nonempty and match exactly once in its complete named file.'
)
RESPONSE_FORMAT = {
 'type': 'json_schema',
 'json_schema': {
  'name': 'historical_source_edits', 'strict': True,
  'schema': {'type': 'object', 'additionalProperties': False, 'required': ['edits'],
   'properties': {'edits': {'type': 'array', 'maxItems': 32,
    'items': {'type': 'object', 'additionalProperties': False,
     'required': ['path', 'old', 'new'],
     'properties': {'path': {'type': 'string'},
                    'old': {'type': 'string', 'minLength': 1},
                    'new': {'type': 'string'}}}}}}
 }
}
PROFILE['response_contract'] = {
 'schema': 'ns-http-json-edits-response-contract/v2',
 'system_prompt_sha256': sha(SYSTEM_PROMPT.encode()),
 'response_format_sha256': sha(canon(RESPONSE_FORMAT)),
 'single_response_no_tools': True,
 'local_candidate_admission_unchanged': True,
}
def validate_request(payload):
 require(type(payload)is dict and set(payload)=={'model','max_tokens','messages','response_format'},'unadmitted HTTP request fields')
 require(payload['model']=='grok-4.6'and type(payload['max_tokens'])is int and payload['max_tokens']==4096,'unadmitted HTTP model/budget')
 require(canon(payload['response_format'])==canon(RESPONSE_FORMAT),'unadmitted response schema')
 messages=payload['messages']
 require(type(messages)is list and len(messages)==2 and messages[0]=={'role':'system','content':SYSTEM_PROMPT},'unadmitted single-response system contract')
 require(type(messages[1])is dict and set(messages[1])=={'role','content'}and messages[1]['role']=='user'and type(messages[1]['content'])is str,'unadmitted public user message')
 require(len(canon(payload))<=65536,'complete request exceeds frozen64KiB cap')
def request_envelope(spec):
 payload={'model':'grok-4.6','max_tokens':4096,
          'messages':[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':canon(spec).decode()}],
          'response_format':json.loads(canon(RESPONSE_FORMAT))}
 validate_request(payload)
 return payload
def fsync_dir(path):
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)

def adapter():
 import adapter as A
 return A

def context_paths(m):
 files=m['proposal_files'];paths=set(m['allowed_edit_paths'])
 if m['visible_nodes']:paths.update(x.split('::',1)[0]for x in m['visible_nodes'])
 else:paths.update(p for p,v in files.items()if v.get('kind')=='file'and p.endswith('.py')and (Path(p).name.startswith('test_')or any(x in ('tests','test','testing')for x in Path(p).parts[:-1])))
 paths.update(p for p,v in files.items()if Path(p).name=='conftest.py'and v.get('kind')=='file')
 require(paths<=set(files)and all(files[p]['kind']=='file'for p in paths),'context not regular pre-fix source')
 return sorted(paths)
def build_request(private,manifest,arm='A'):
 A=adapter();m=A.validate_manifest(manifest);p=Path(private);binding=A.candidate_binding(p/'proposal',m);require(not binding['changed_paths'],'HTTP request source is not pristine')
 require(A.read(p/'prompt.txt')==m['prompt'].encode(),'HTTP prompt changed')
 import semantic_context as C
 paths=context_paths(m);files={name:A.read(p/'proposal'/name).decode('utf-8')for name in paths}
 tests=[name for name in paths if name not in m['allowed_edit_paths']]
 meta=m.get('public_context_preparation');require(type(meta)is dict and set(meta)=={'path','sha256'},'reviewed native public preparation required for paired pilot')
 q=Path(meta['path']);require(q.is_absolute()and q.resolve()==q and q.stat().st_mode&0o077==0 and q.parent.stat().st_mode&0o077==0,'private canonical preparation required')
 raw=A.read(q,16*1024*1024);require(sha(raw)==meta['sha256'],'public context preparation changed');packet=json.loads(raw)
 require(packet.get('schema')=='ns-pilot-AB-prepared-public-context/v1'and packet.get('unit_id')==m['unit_id']and packet.get('source_archive_sha256')==m['source_archive']['sha256'],'prepared historical unit differs')
 require(packet.get('semantic_source_sha256')==A.sha(Path(C.__file__).resolve()),'native context adapter source changed')
 payload,context=C.request(m['prompt'],files,m['allowed_edit_paths'],tests,arm,packet['native_preparation'])
 require(context==packet['bindings'][arm]and sha(canon(payload))==packet['request_sha256'][arm],'prepared request did not rebind')
 require(len(canon(payload))<=PROFILE['request_serialized_bytes_max'],'selected public request exceeds fixed byte cap')
 return payload,{'request_sha256':sha(canon(payload)),'request_bytes':len(canon(payload)),'manifest_sha256':A.digest(m),'source_preimage_sha256':binding['sha256'],'visible_context_paths':paths,'context_policy':PROFILE['context_policy'],'context_binding_sha256':C.digest(context),'context_binding':context,'public_context_preparation_sha256':meta['sha256'],'arm':arm}

def load_credential():
 """No search: approved primary env names or exact private Grok auth file."""
 for k in ('XAI_API_KEY','GROK_API_KEY','ipfs_accelerate_py_XAI_API_KEY'):
  value=os.environ.get(k,'').strip()
  if value:require(len(value)<=32768 and '\n'not in value and '\r'not in value,'invalid primary credential');return value
 A=adapter();p=Path(os.environ.get('GROK_HOME',str(Path.home()/'.grok')))/'auth.json'
 require(p.is_absolute()and p.resolve()==p and p.stat().st_uid==os.getuid()and not(p.stat().st_mode&0o077),'primary credential file not private/canonical')
 obj=json.loads(A.read(p,1048576));records=list(obj.values())if isinstance(obj,dict)else[]
 values={x.get('key','').strip()for x in records if isinstance(x,dict)and isinstance(x.get('key'),str)and x['key'].strip()}
 require(len(values)==1,'primary credential selection ambiguous or unavailable');value=values.pop();require(len(value)<=32768 and '\n'not in value and '\r'not in value,'invalid primary credential');return value

def strict_json(raw):
 def pairs(rows):
  out={}
  for k,v in rows:require(k not in out,'duplicate response key');out[k]=v
  return out
 return json.loads(raw,object_pairs_hook=pairs)
def apply_edits(private,m,text):
 A=adapter();root=Path(private)/'proposal';before=A.candidate_binding(root,m);require(not before['changed_paths'],'proposal drifted before HTTP edits')
 obj=strict_json(text);require(type(obj)is dict and set(obj)=={'edits'}and type(obj['edits'])is list and len(obj['edits'])<=PROFILE['max_edits'],'unapproved edit response')
 changed={}
 for row in obj['edits']:
  require(type(row)is dict and set(row)=={'path','old','new'}and all(type(x)is str for x in row.values()),'untyped edit response')
  path=A.safe_rel(row['path']);require(path in m['allowed_edit_paths'],'edit outside frozen authority');old=row['old'];new=row['new'];require(old and '\0'not in old+new,'empty/binary edit')
  value=changed.get(path,A.read(root/path).decode('utf-8'));require(value.count(old)==1,'edit preimage not unique');changed[path]=value.replace(old,new,1)
 # Validate all changes in a private copy before replacing any proposal bytes.
 import shutil,tempfile
 with tempfile.TemporaryDirectory(prefix='http-proposal-edits-')as td:
  staged=Path(td)/'tree';shutil.copytree(root,staged,symlinks=True)
  for path,value in changed.items():(staged/path).write_text(value,encoding='utf-8')
  binding=A.candidate_binding(staged,m)
  for path,value in changed.items():
   dest=root/path;require(A.sha(dest)==m['proposal_files'][path]['sha256'],'source drifted during edit staging');fd=os.open(dest,os.O_WRONLY|os.O_TRUNC|os.O_NOFOLLOW)
   try:
    with os.fdopen(fd,'wb',closefd=False)as h:h.write(value.encode());h.flush();os.fsync(h.fileno())
   finally:os.close(fd)
 require(A.candidate_binding(root,m)==binding,'applied HTTP edits differ');return binding

def propose_http(private,manifest,*,arm='A',inert_fixture=None,credential_loader=None):
 """Call only after a durable service reservation; no automatic repeat exists."""
 A=adapter();m=A.validate_manifest(manifest);private=Path(private);require(private.is_absolute()and private.resolve()==private and private.stat().st_mode&0o077==0,'unsafe HTTP private root')
 require((private/'reservation.json').is_file(),'HTTP proposal requires consumed host grant reservation')
 payload,binding=build_request(private,m,arm);target=private/'http_proposer';require(not target.exists(),'HTTP effect attempted/uncertain; never automatically repeat');target.mkdir(mode=0o700)
 inert=inert_fixture is not None
 if inert:require(m.get('qualification_fixture')is True and m['unit_id'].startswith('constructed-'),'inert HTTP mode accepts constructed units only')
 token='constructed-http-secret-never-emit'if inert else(credential_loader or load_credential)();require(type(token)is str and token and len(token)<=32768,'missing bound credential')
 envelope={'schema':'ns-http-child-input/v1','request':payload,'credential':token,'inert_fixture':inert_fixture};wire=canon(envelope)
 A.write(target/'request.private.json',canon(payload));A.write(target/'request_binding.json',canon(binding));A.write(target/'profile.json',canon(PROFILE))
 A.write(target/'pending.json',canon({'status':'possible_external_effect','attempted_http_posts_upper_bound':1,'inert':inert,'no_retries':True,'credential_persisted':False}))
 fsync_dir(target);fsync_dir(private)
 name='ns-historical-http-'+uuid.uuid4().hex;cidfile=target/'container.cid';source=Path(__file__).resolve()
 cmd=DOCKER+['create','-i','--name',name,'--cidfile',str(cidfile),'--runtime=runc','--network=none'if inert else'--network=bridge','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user',f'{os.getuid()}:{os.getgid()}','--cpus=1','--memory=2g','--memory-swap=2g','--pids-limit=32','--tmpfs',f'/tmp:rw,nosuid,nodev,size=16777216,mode=0700,uid={os.getuid()},gid={os.getgid()}','--workdir=/tmp','--entrypoint=/usr/bin/env','--mount',f'type=bind,src={source},dst=/runner/http_proposer.py,readonly',IMAGE,'-i','HOME=/tmp','PATH=/usr/bin:/bin','/usr/bin/python3','-I','-B','/runner/http_proposer.py','--child']
 A.write(target/'command.private.json',canon(cmd));created=subprocess.run(cmd,capture_output=True,timeout=30);require(created.returncode==0,'HTTP container create failed');cid=A.read(cidfile,100).decode().strip();require(len(cid)==64 and all(c in'0123456789abcdef'for c in cid),'HTTP container ID invalid');started=time.monotonic();result=None;rc=None;timed_out=False
 try:
  inspect=json.loads(subprocess.check_output(DOCKER+['inspect',cid],timeout=20))[0];h=inspect['HostConfig'];mounts=[x for x in inspect['Mounts']if x['Type']=='bind'];config=inspect['Config']
  require(inspect['Image']==IMAGE and not inspect['State']['Running']and len(mounts)==1 and mounts[0]['Source']==str(source)and mounts[0]['Destination']=='/runner/http_proposer.py'and not mounts[0]['RW'],'HTTP filesystem boundary mismatch')
  require(h['Runtime']=='runc'and h['NetworkMode']==('none'if inert else'bridge')and h['NanoCpus']==1000000000 and h['Memory']==2147483648 and h['MemorySwap']==2147483648 and h['PidsLimit']==32 and h['ReadonlyRootfs']and not h['Privileged']and set(h['CapDrop'])=={'ALL'}and h['SecurityOpt']==['no-new-privileges']and not h.get('Devices')and not h.get('DeviceRequests'),'HTTP resource boundary mismatch')
  require(config['User']==f'{os.getuid()}:{os.getgid()}'and config['Entrypoint']==['/usr/bin/env']and config['WorkingDir']=='/tmp','HTTP child identity differs');require(not any(token in str(x)for x in [cmd,config]),'credential exposed in container metadata')
  A.write(target/'boundary.json',canon({'image':IMAGE,'source_sha256':A.sha(source),'mounts':[{'source':mounts[0]['Source'],'destination':mounts[0]['Destination'],'writable':False}],'resources':{k:h[k]for k in ['Runtime','NetworkMode','NanoCpus','Memory','MemorySwap','PidsLimit','ReadonlyRootfs','CapDrop','SecurityOpt','Tmpfs']},'credential_in_argv_env_mounts':False,'checked_before_start':True}))
  with(target/'stdout.private.json').open('xb')as out,(target/'stderr.private.log').open('xb')as err:
   os.fchmod(out.fileno(),0o600);os.fchmod(err.fileno(),0o600)
   try:rc=subprocess.run(DOCKER+['start','--attach','--interactive',cid],input=wire,stdout=out,stderr=err,timeout=PROFILE['wall_seconds_max']).returncode
   except subprocess.TimeoutExpired:timed_out=True;rc=124;subprocess.run(DOCKER+['kill',cid],capture_output=True,timeout=15)
   out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
  raw=A.read(target/'stdout.private.json',PROFILE['response_bytes_max']*2);require(token.encode()not in raw and token.encode()not in A.read(target/'stderr.private.log'),'credential appeared in child output')
  result=strict_json(raw)if raw else {'schema':'ns-http-child-result/v1','status':'no_child_result','attempted_posts':None}
  require(result.get('schema')=='ns-http-child-result/v1'and result.get('attempted_posts')in (None,0,1),'HTTP child result differs')
  candidate=None;parse_error=None
  if result.get('status')=='response'and result.get('served_model')=='grok-4.6'and rc==0 and not timed_out:
   try:candidate=apply_edits(private,m,result['content'])
   except (ValueError,KeyError,UnicodeError,TypeError):parse_error='candidate_response_rejected'
  scalar={k:result.get(k)for k in ['status','http_status','attempted_posts','response_bytes','response_sha256','request_sha256','served_model','served_revision','runtime_receipt_id','usage','finish_reason','elapsed_seconds','inert_observed_posts','exception_class','errno','failed_phase','absolute_timeout']if k in result}
  response={'schema':'ns-historical-http-proposal-result/v1','success':candidate is not None,'candidate_applied':candidate is not None,'candidate_binding':candidate,'parse_error':parse_error,'provider_invoked':not inert and result.get('attempted_posts')==1,'provider_dispatch_may_have_occurred':not inert,'possibly_charged':None if not inert else False,'settled_provider_cost':{'status':'unavailable','reason':'No settlement receipt; API usage metadata retained separately.'},'container_exit_code':rc,'timed_out':timed_out,'provider':scalar,'profile':PROFILE,'profile_sha256':sha(canon(PROFILE)),'request_binding':binding,'source_sha256':A.sha(source),'boundary_sha256':A.sha(target/'boundary.json'),'elapsed_seconds':time.monotonic()-started,'inert_fixture':inert,'historical_oracle_executed':False}
  A.write(target/'result.json',canon(response));fsync_dir(target);return response
 finally:
  cleanup=subprocess.run(DOCKER+['rm','-f',cid],capture_output=True,timeout=20);A.write(target/'cleanup.json',canon({'container':cid,'returncode':cleanup.returncode}));fsync_dir(target);require(cleanup.returncode==0,'HTTP exact-container cleanup failed')

class _ChildAbsoluteDeadline(TimeoutError):
 pass

def child():
 """One final JSON stdout; bounded metadata stderr and absolute child budget."""
 import signal
 started=time.monotonic();deadline=started+PROFILE['child_absolute_wall_seconds'];phase_name='child_started';phase_count=0
 def emit(name,**metadata):
  nonlocal phase_name,phase_count
  phase_name=name;phase_count+=1;require(phase_count<=26,'HTTP diagnostic metadata line cap')
  row={'schema':'ns-http-child-phase/v1','phase':name,'elapsed_seconds':round(time.monotonic()-started,6),**metadata}
  sys.stderr.buffer.write(canon(row)+b'\n');sys.stderr.buffer.flush()
 def alarm(*_):raise _ChildAbsoluteDeadline('absolute HTTP child budget')
 def remaining():
  value=deadline-time.monotonic()
  if value<=0:raise _ChildAbsoluteDeadline('absolute HTTP child budget')
  return value
 def fixture_deadline(seconds):
  nonlocal deadline
  deadline=min(deadline,started+seconds);signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
 previous=signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,PROFILE['child_absolute_wall_seconds'])
 try:
  emit('child_started')
  return _child_request(started,emit,remaining,fixture_deadline)
 except Exception as exc:
  number=getattr(exc,'errno',None)
  emit('child_exception',failed_phase=phase_name,exception_class=type(exc).__name__[:64],errno=number if type(number)is int else None,absolute_timeout=isinstance(exc,_ChildAbsoluteDeadline))
  raise
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)

def _child_request(started,emit,remaining,fixture_deadline):
 """No adapter import, project execution, tools, retries or extra HTTP calls."""
 import urllib.request,urllib.error,ssl
 raw=sys.stdin.buffer.read(1114113);require(len(raw)<=1114112,'child input bound');x=strict_json(raw);require(x['schema']=='ns-http-child-input/v1','child schema');payload=x['request'];token=x['credential'];body=canon(payload)
 validate_request(payload)
 require(type(token)is str and token and len(token)<=32768 and '\n'not in token and '\r'not in token,'invalid HTTP auth')
 emit('request_validated',request_bytes=len(body),request_sha256=sha(body))
 fixture=x.get('inert_fixture');url=ENDPOINT;server=None;thread=None;timeout=PROFILE['socket_timeout_seconds']
 if fixture is not None:
  import http.server,threading,socket
  require(type(fixture)is dict and fixture.get('schema')=='constructed-http-fixture/v1','unapproved fixture');data=fixture.get('response','').encode();status=int(fixture.get('status',200));delay=float(fixture.get('delay',0));timeout=float(fixture.get('timeout',2));mode=fixture.get('mode','normal');absolute=fixture.get('absolute_timeout_seconds')
  require(0<timeout<=2 and 0<=delay<=1 and len(data)<=1048577 and status in (200,302,400,401,429,500)and mode in ('normal','reset','partial_stall'),'fixture bound')
  if absolute is not None:require(type(absolute)in (int,float)and 0<absolute<=2,'fixture deadline bound');fixture_deadline(float(absolute))
  class Handler(http.server.BaseHTTPRequestHandler):
   def do_POST(self):
    server.posts+=1;n=int(self.headers.get('Content-Length','0'));server.request_sha=sha(self.rfile.read(n))
    if mode=='reset':self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
    if mode!='partial_stall':time.sleep(delay)
    self.send_response(status)
    if status==302:self.send_header('Location','http://127.0.0.1:'+str(server.server_port)+'/must-not-follow')
    if mode=='partial_stall':self.send_header('Content-Length',str(len(data)))
    self.end_headers()
    try:
     if mode=='partial_stall':self.wfile.write(data[:1]);self.wfile.flush();time.sleep(delay)
     else:self.wfile.write(data)
    except (BrokenPipeError,ConnectionResetError):pass
   def log_message(self,*args):pass
  server=http.server.HTTPServer(('127.0.0.1',0),Handler);server.posts=0;thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url='http://127.0.0.1:'+str(server.server_port)+'/fixture'
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs):return None
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()));request=urllib.request.Request(url,data=body,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/json'},method='POST');out={'schema':'ns-http-child-result/v1','attempted_posts':0,'request_sha256':sha(body),'status':'transport_error'};read_bytes=0;phase='open_entered'
 try:
  out['attempted_posts']=1;emit('open_entered',attempted_posts_upper_bound=1)
  with opener.open(request,timeout=min(timeout,remaining()))as response:
   out['http_status']=response.status;emit('headers_received',http_status=response.status);phase='body_read';parts=[];next_progress=65536
   while read_bytes<1048577:
    remaining();part=response.read1(min(65536,1048577-read_bytes))
    if not part:break
    parts.append(part);read_bytes+=len(part)
    if read_bytes>=next_progress:emit('read_progress',response_bytes=read_bytes);next_progress+=65536
   data=b''.join(parts);out.update(response_bytes=len(data),response_sha256=sha(data));emit('body_read_complete',response_bytes=len(data));phase='response_parse'
   if len(data)>1048576:out['status']='response_too_large'
   elif token.encode()in data:out['status']='credential_echo_rejected'
   else:
    try:
     value=strict_json(data);choices=value.get('choices',[]);require(type(choices)is list and len(choices)==1,'response choice count');choice=choices[0];message=choice['message'];require(not message.get('tool_calls')and not message.get('function_call')and type(message.get('content'))is str,'tools or absent content');content=message['content'];require(len(content.encode())<=262144,'response content cap')
     def text_field(v,n):return v if type(v)is str and len(v)<=n and all(ord(c)>=32 and ord(c)!=127 for c in v)else None
     usage={};u=value.get('usage')or{};require(type(u)is dict,'malformed usage')
     for key in ('prompt_tokens','completion_tokens','total_tokens','reasoning_tokens','cost_in_usd_ticks'):
      if type(u.get(key))is int and 0<=u[key]<=1000000000000:usage[key]=u[key]
     for key in ('prompt_tokens_details','completion_tokens_details'):
      details=u.get(key)or{}
      if type(details)is dict:usage[key]={k:v for k,v in details.items()if k in ('cached_tokens','reasoning_tokens','accepted_prediction_tokens','rejected_prediction_tokens')and type(v)is int and 0<=v<=1000000000}
     out.update(status='response',served_model=text_field(value.get('model'),128),served_revision=text_field(value.get('system_fingerprint'),128),runtime_receipt_id=text_field(value.get('id'),256),finish_reason=text_field(choice.get('finish_reason'),32),usage=usage or None,content=content)
    except (ValueError,KeyError,TypeError,UnicodeError):out['status']='malformed_response'
 except urllib.error.HTTPError as exc:
  out.update(status='http_error',http_status=exc.code);emit('headers_received',http_status=exc.code)
 except Exception as exc:
  number=getattr(exc,'errno',None)
  if type(number)is not int:number=getattr(getattr(exc,'reason',None),'errno',None)
  out.update(status='transport_error',response_bytes=read_bytes,failed_phase=phase,exception_class=type(exc).__name__[:64],errno=number if type(number)is int else None,absolute_timeout=isinstance(exc,_ChildAbsoluteDeadline))
  emit('exception',failed_phase=phase,exception_class=out['exception_class'],errno=out['errno'],absolute_timeout=out['absolute_timeout'],response_bytes=read_bytes)
 finally:
  if server is not None:out['inert_observed_posts']=server.posts;server.server_close()
 out['elapsed_seconds']=time.monotonic()-started;emit('final_result',status=out['status'],http_status=out.get('http_status'),response_bytes=out.get('response_bytes',0));sys.stdout.buffer.write(canon(out));sys.stdout.buffer.flush();return 0
if __name__=='__main__':
 if sys.argv[1:]==['--child']:
  try:raise SystemExit(child())
  except Exception:sys.stdout.buffer.write(canon({'schema':'ns-http-child-result/v1','status':'child_input_or_transport_error','attempted_posts':None}));raise SystemExit(2)
 raise SystemExit('Host API only; no standalone live invocation entrypoint')
