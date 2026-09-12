"""Root-owned single-POST development proposer; no CLI, tools or fallback.

The service consumes its durable one-use grant before propose_http. Credentials
are fetched only by the host and sent through Docker stdin, never argv/env/files.
Child executes only this fixed standard-library code, never returned source.
"""
from pathlib import Path
import hashlib,json,os,stat,subprocess,sys,time,uuid
IMAGE='sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6'
ENDPOINT='https://api.x.ai/v1/chat/completions'
PROFILE={'schema':'ns-historical-http-profile/v1','transport':'operator_host_fixed_https_json_edits/v1','endpoint':ENDPOINT,'requested_model':'grok-4.6','expected_served_aliases':['grok-4.6'],'reasoning_effort':None,'reasoning_policy':'parameter omitted; no served-effort attestation','max_tokens':4096,'request_serialized_bytes_max':65536,'response_bytes_max':1048576,'max_patch_bytes':16384,'max_edits':32,'wall_seconds_max':180,'socket_timeout_seconds':175,'cpu_count':1,'memory_bytes':2147483648,'pids':32,'runtime':'runc','image':IMAGE,'max_http_posts':1,'retries':0,'fallback_allowed':False,'tools':[],'context_policy':'whole admitted implementation files plus public visible-node test files and conftest; auto-collected baseline includes all upstream Python test files; fixed for every arm; no truncation'}
DOCKER=['/usr/bin/docker','--host=unix:///var/run/docker.sock']
def require(ok,msg):
 if not ok:raise ValueError(msg)
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(data):return hashlib.sha256(data).hexdigest()
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
def build_request(private,manifest):
 A=adapter();m=A.validate_manifest(manifest);p=Path(private);binding=A.candidate_binding(p/'proposal',m);require(not binding['changed_paths'],'HTTP request source is not pristine')
 require(A.read(p/'prompt.txt')==m['prompt'].encode(),'HTTP prompt changed')
 paths=context_paths(m);files={f:A.read(p/'proposal'/f).decode('utf-8')for f in paths}
 spec={'instruction':m['prompt'],'public_pre_fix_files':files,'allowed_edit_paths':m['allowed_edit_paths'],'response_contract':{'format':'JSON object with exactly one key edits, a list of {path,old,new}. Every old string must be nonempty and occur exactly once in the current named allowed file. Use no other keys, tools, markdown, or added files. Do not execute code.','max_edits':32,'max_patch_bytes':16384}}
 payload={'model':PROFILE['requested_model'],'max_tokens':PROFILE['max_tokens'],'messages':[{'role':'user','content':canon(spec).decode()}]};wire=canon(payload)
 require(len(wire)<=PROFILE['request_serialized_bytes_max'],'serialized public request exceeds frozen 64KiB limit; no truncation or dispatch')
 return payload,{'request_sha256':sha(wire),'request_bytes':len(wire),'manifest_sha256':A.digest(m),'source_preimage_sha256':binding['sha256'],'visible_context_paths':paths,'context_policy':PROFILE['context_policy']}
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

def propose_http(private,manifest,*,inert_fixture=None,credential_loader=None):
 """Call only after a durable service reservation; no automatic repeat exists."""
 A=adapter();m=A.validate_manifest(manifest);private=Path(private);require(private.is_absolute()and private.resolve()==private and private.stat().st_mode&0o077==0,'unsafe HTTP private root')
 require((private/'reservation.json').is_file(),'HTTP proposal requires consumed host grant reservation')
 payload,binding=build_request(private,m);target=private/'http_proposer';require(not target.exists(),'HTTP effect attempted/uncertain; never automatically repeat');target.mkdir(mode=0o700)
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
  scalar={k:result.get(k)for k in ['status','http_status','attempted_posts','response_bytes','response_sha256','request_sha256','served_model','served_revision','runtime_receipt_id','usage','finish_reason','elapsed_seconds','inert_observed_posts']if k in result}
  response={'schema':'ns-historical-http-proposal-result/v1','success':candidate is not None,'candidate_applied':candidate is not None,'candidate_binding':candidate,'parse_error':parse_error,'provider_invoked':not inert and result.get('attempted_posts')==1,'provider_dispatch_may_have_occurred':not inert,'possibly_charged':None if not inert else False,'settled_provider_cost':{'status':'unavailable','reason':'No settlement receipt; API usage metadata retained separately.'},'container_exit_code':rc,'timed_out':timed_out,'provider':scalar,'profile':PROFILE,'profile_sha256':sha(canon(PROFILE)),'request_binding':binding,'source_sha256':A.sha(source),'boundary_sha256':A.sha(target/'boundary.json'),'elapsed_seconds':time.monotonic()-started,'inert_fixture':inert,'historical_oracle_executed':False}
  A.write(target/'result.json',canon(response));fsync_dir(target);return response
 finally:
  cleanup=subprocess.run(DOCKER+['rm','-f',cid],capture_output=True,timeout=20);A.write(target/'cleanup.json',canon({'container':cid,'returncode':cleanup.returncode}));fsync_dir(target);require(cleanup.returncode==0,'HTTP exact-container cleanup failed')

def child():
 """No adapter import, project code execution, terminal, tools or retries."""
 import urllib.request,urllib.error,ssl
 raw=sys.stdin.buffer.read(1114113);require(len(raw)<=1114112,'child input bound');x=strict_json(raw);require(x['schema']=='ns-http-child-input/v1','child schema');payload=x['request'];token=x['credential'];body=canon(payload)
 require(len(body)<=65536 and set(payload)=={'model','max_tokens','messages'}and payload['model']=='grok-4.6'and payload['max_tokens']==4096,'unadmitted HTTP request')
 require(type(token)is str and token and len(token)<=32768 and '\n'not in token and '\r'not in token,'invalid HTTP auth')
 fixture=x.get('inert_fixture');url=ENDPOINT;server=None;thread=None;timeout=175
 if fixture is not None:
  import http.server,threading
  require(type(fixture)is dict and fixture.get('schema')=='constructed-http-fixture/v1','unapproved fixture');data=fixture.get('response','').encode();status=int(fixture.get('status',200));delay=float(fixture.get('delay',0));timeout=float(fixture.get('timeout',2));require(0<timeout<=2 and 0<=delay<=1 and len(data)<=1048577 and status in (200,302,401,429,500),'fixture bound')
  class Handler(http.server.BaseHTTPRequestHandler):
   def do_POST(self):
    server.posts+=1;n=int(self.headers.get('Content-Length','0'));server.request_sha=sha(self.rfile.read(n));time.sleep(delay);self.send_response(status)
    if status==302:self.send_header('Location','http://127.0.0.1:'+str(server.server_port)+'/must-not-follow')
    self.end_headers()
    try:self.wfile.write(data)
    except BrokenPipeError:pass
   def log_message(self,*args):pass
  server=http.server.HTTPServer(('127.0.0.1',0),Handler);server.posts=0;thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url='http://127.0.0.1:'+str(server.server_port)+'/fixture'
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs):return None
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=ssl.create_default_context()));request=urllib.request.Request(url,data=body,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/json'},method='POST');started=time.monotonic();out={'schema':'ns-http-child-result/v1','attempted_posts':1,'request_sha256':sha(body),'status':'transport_error'}
 try:
  with opener.open(request,timeout=timeout)as response:
   data=response.read(1048577);out.update(http_status=response.status,response_bytes=len(data),response_sha256=sha(data))
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
 except urllib.error.HTTPError as e:out.update(status='http_error',http_status=e.code)
 except Exception:out['status']='transport_error'
 finally:
  if server is not None:out['inert_observed_posts']=server.posts;server.shutdown();server.server_close()
 out['elapsed_seconds']=time.monotonic()-started;sys.stdout.buffer.write(canon(out));return 0
if __name__=='__main__':
 if sys.argv[1:]==['--child']:
  try:raise SystemExit(child())
  except Exception:sys.stdout.buffer.write(canon({'schema':'ns-http-child-result/v1','status':'child_input_or_transport_error','attempted_posts':None}));raise SystemExit(2)
 raise SystemExit('Host API only; no standalone live invocation entrypoint')
