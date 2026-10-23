"""Explicit public runtime/source readback and disposal of the owned fixture."""
import base64,hashlib,json,os,subprocess
from pathlib import Path
Z=Path(__file__).resolve().parent;os.umask(0o077)
NAME='ipfs-checked-worker-context-z02'
def save(name,value):
 with (Z/name).open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
def docker(user,program,payload):
 r=subprocess.run(['docker','exec','-i','--user',user,NAME,'/opt/ipfs-supervisor/venv/bin/python','-B','-I','-c',program],input=json.dumps(payload).encode(),capture_output=True,timeout=45)
 assert r.returncode==0,r.stderr.decode()
 return json.loads(r.stdout)
pins=json.loads((Z/'final-runtime-update-03.json').read_bytes())['files']
readback=docker('root', '''import hashlib,json,os,pathlib,stat,sys
p=json.load(sys.stdin);out=[]
for r in p:
 q=pathlib.Path('/opt/ipfs-supervisor/source')/r['relative_path'];s=q.lstat();raw=q.read_bytes()
 assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_uid==0 and stat.S_IMODE(s.st_mode)==0o444
 assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
 out.append(dict(r,container_path=str(q),uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)),singlelink=True))
print(json.dumps(out))''',pins)
for row in readback:
 row['path']=str(Z/'checkout'/row['relative_path'])
 raw=Path(row['path']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
save('deployed-runtime-source-pins-02.json',{'schema':'checked-worker-deployed-public-source-readback@1','files':readback,'exact_copies':True,'credential_bodies_included':False,'loaded_module_code_attested':False,'transitive_dependency_closure_attested':False})
pre=json.loads((Z/'checked-worker-run-04/native-preflight.json').read_bytes())
paths=[pre['descriptor']['artifact'],pre['instruction_receipt']['artifact']]
out=Z/'native-worker-public-readback-02';out.mkdir(mode=0o700)
values=docker('root', '''import base64,hashlib,json,pathlib,stat,sys
out=[]
for name in json.load(sys.stdin):
 p=pathlib.Path(name);raw=p.read_bytes();s=p.lstat();assert stat.S_ISREG(s.st_mode)and s.st_nlink==1
 out.append({'container_path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'uid':s.st_uid,'gid':s.st_gid,'mode':oct(stat.S_IMODE(s.st_mode)),'body_base64':base64.b64encode(raw).decode()})
print(json.dumps(out))''',paths)
for row,name in zip(values,['checked-context.json','public-instruction.json']):
 raw=base64.b64decode(row.pop('body_base64'));assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
 path=out/name;path.write_bytes(raw);path.chmod(0o600);row['path']=str(path)
save('native-worker-public-readback-02.json',{'schema':'checked-worker-immutable-public-artifacts-readback@1','files':values,'database_bodies_included':False,'credentials_included':False})
owner=json.loads((Z/'native-fixture-05/public/owner-receipt.json').read_bytes())
task=docker('supervisor', '''import json,sys
sys.path[:0]=['/opt/ipfs-supervisor/source','/opt/ipfs-supervisor/datasets','/opt/ipfs-supervisor/kit']
from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository
p=json.load(sys.stdin)
with IntentRepository('/opt/ipfs-supervisor/state/native-fixture-05/intent.duckdb') as i:
 t=i.get_task(p['task_cid']);print(json.dumps({'task_cid':p['task_cid'],'task_alias':t['task_alias'],'status':t['status'],'revision':t['revision'],'event_watermark':i.event_watermark()}))''',{'task_cid':owner['task_cid']})
before=json.loads((Z/'native-fixture-05/public/task-readback.json').read_bytes())
assert all(task[k]==before[k] for k in task)
save('native-task-final-readback-02.json',{'schema':'checked-worker-public-task-readback@1','before':before,'after':task,'unchanged':True,'completion_authority':False})
r=subprocess.run(['docker','stop','--time','5',NAME],capture_output=True,timeout=30);assert r.returncode==0
s=subprocess.run(['docker','rm',NAME],capture_output=True,timeout=30);assert s.returncode==0
gone=subprocess.run(['docker','inspect','--format','{{.Id}}',NAME],capture_output=True,timeout=15);assert gone.returncode!=0
save('container-disposal-02.json',{'schema':'checked-worker-owned-container-disposal-02@1','container':NAME,'stop_returncode':r.returncode,'remove_returncode':s.returncode,'container_absent':True,'worker_cleanup_previously_verified':True,'only_owned_fixture_removed':True})
print(json.dumps({'exact_runtime_files':len(readback),'public_artifacts':len(values),'native_task_unchanged':True,'owned_container_removed':True}))
