"""Actual offline Docker boundary qualification, distinct from native admission."""
import asyncio,hashlib,io,json,os,shlex,stat,subprocess,sys,tarfile,time
from pathlib import Path
Z=Path(__file__).resolve().parent
C=Z/'checkout'
E=Path('/home/barberb/lift_coding/maintenance/terminal-compact-retrieval-20261011-01/pinned-dependencies-v10')
OUT=Z/'docker-boundary-02'
NAME='ipfs-checked-worker-context-z02'
IMAGE='ipfs-supervisor-preview-worker:20261005-r3'
OUT.mkdir(mode=0o700)
def pin(path):
 raw=Path(path).read_bytes();return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def write(name,value):
 path=OUT/name
 with path.open('x') as stream:json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n')
def command(label,argv,timeout=180):
 started=time.monotonic()
 result=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
 (OUT/(label+'.stdout')).write_text(result.stdout)
 (OUT/(label+'.stderr')).write_text(result.stderr)
 write(label+'.json',{'argv':argv,'returncode':result.returncode,'seconds':time.monotonic()-started,
  'stdout':pin(OUT/(label+'.stdout')),'stderr':pin(OUT/(label+'.stderr'))})
 if result.returncode:raise RuntimeError('actual Docker step failed: '+label)
 return result
class DockerEnvironment:
 def __init__(self):self.calls=0
 async def exec(self,*,command,cwd,user,env=None,timeout_sec=180):
  self.calls+=1;label='exec-'+str(self.calls).zfill(2)
  argv=['docker','exec','--user',user,'--workdir',cwd]
  for key,value in sorted((env or {}).items()):argv+=['--env',key+'='+value]
  argv += [NAME,'/bin/sh','-c',command]
  started=time.monotonic()
  result=await asyncio.to_thread(subprocess.run,argv,capture_output=True,text=True,timeout=timeout_sec)
  (OUT/(label+'.stdout')).write_text(result.stdout);(OUT/(label+'.stderr')).write_text(result.stderr)
  write(label+'.json',{'argv':argv,'returncode':result.returncode,'seconds':time.monotonic()-started,
   'stdout':pin(OUT/(label+'.stdout')),'stderr':pin(OUT/(label+'.stderr'))})
  return type('DockerExecResult',(),{'stdout':result.stdout,'stderr':result.stderr,'return_code':result.returncode})()
 async def upload_file(self,source,destination):
  self.calls+=1;label='upload-'+str(self.calls).zfill(2)
  await asyncio.to_thread(command,label,['docker','cp',str(source),NAME+':'+destination])
 async def stop(self,*,delete):
  command('stop',['docker','stop','--time','10',NAME],30)
  if delete:command('delete',['docker','rm',NAME],30)
async def main():
 result={'schema':'checked-worker-actual-Docker-boundary-qualification@1','qualified':False,
  'container_name':NAME,'network':'none','provider_calls':0,'credentials_transferred':False,
  'native_admission_created':False,'native_checked_context_transport_qualified':False,
  'full_supervisor_entrypoint_qualified':False,'full_deployment_helper_qualified':False,
  'task_source_body_executed':False,'training_steps':0,'task_completed':False,
  'source_copy_scope':'sequential public Python source snapshot for boundary-only imports; not frozen checked-route or process-origin attestation',
  'environment_adapter':'real docker exec/cp/stop API adapter; Harbor runtime not invoked'}
 try:
  image=command('image-public-identity',['docker','image','inspect','--format','{{json .Id}} {{json .Architecture}} {{json .Os}} {{json .Config.User}}',IMAGE])
  result['image_public_fields']=image.stdout.strip()
  exists=command('name-absence',['docker','ps','-a','--filter','name=^/'+NAME+'$','--format','{{.Names}}'])
  if exists.stdout.strip():raise ValueError('fresh exact container name required')
  launched=command('launch',['docker','run','--detach','--network','none','--name',NAME,'--entrypoint','/bin/sleep',IMAGE,'infinity'])
  result['container_id']=launched.stdout.strip()
  public=command('container-public-identity',['docker','inspect','--format','{{json .Id}} {{json .Image}} {{json .State.Pid}} {{json .State.Running}} {{json .HostConfig.Privileged}} {{json .HostConfig.NetworkMode}}',NAME])
  result['container_public_fields']=public.stdout.strip()
  setup=r"""import os,pathlib,pwd,subprocess
root=pathlib.Path('/opt/ipfs-supervisor')
owner=pwd.getpwnam('supervisor');worker=pwd.getpwnam('benchmarkworker')
assert owner.pw_uid==1000 and worker.pw_uid==1001 and worker.pw_gid==owner.pw_gid
home=root/'worker-home'
assert home.is_dir() and not any(home.iterdir()),'only empty cached worker home may be reused'
subprocess.run(['userdel','benchmarkworker'],check=True)
for p in (root/'home',root/'home/.codex',root/'codex-auth',root/'state'):
 p.mkdir(parents=True,exist_ok=True);p.chown if False else None;os.chown(p,1000,owner.pw_gid);p.chmod(0o700)
repo=pathlib.Path('/app');repo.mkdir(exist_ok=True)
assert not any(repo.iterdir()),'fresh empty synthetic permission repository required'
os.chown(repo,1000,owner.pw_gid)
subprocess.run(['git','init','-q',str(repo)],check=True)
subprocess.run(['git','-C',str(repo),'-c','safe.directory=/app','-c','user.name=Boundary qualification','-c','user.email=boundary@localhost','commit','--allow-empty','-qm','Synthetic permission-only baseline'],check=True)
for base,dirs,files in os.walk(repo):
 os.chown(base,1000,owner.pw_gid)
 for name in files:os.chown(pathlib.Path(base)/name,1000,owner.pw_gid)
print('Actual empty-account and synthetic Git permission setup complete; no task source executed')
"""
  command('setup',['docker','exec','--user','root',NAME,'python3','-I','-c',setup])
  archive=OUT/'boundary-source.tar.gz';inventory=[]
  with tarfile.open(archive,'w:gz',compresslevel=1) as bundle:
   for base,roots,prefix in [(C,['ipfs_accelerate_py','benchmarks'],'source'),(E/'datasets',['ipfs_datasets_py'],'datasets'),(E/'kit',['ipfs_kit_py'],'kit')]:
    paths=subprocess.check_output(['rg','--files','-g','*.py',*roots],cwd=base,text=True).splitlines()
    for name in sorted(paths):
     path=base/name;before=path.lstat()
     if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1:raise ValueError('source copy requires regular single-link file')
     raw=path.read_bytes();after=path.lstat()
     if (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('source changed during snapshot')
     target=prefix+'/'+name;info=tarfile.TarInfo(target);info.size=len(raw);info.mode=0o444;info.uid=info.gid=0;bundle.addfile(info,io.BytesIO(raw))
     inventory.append({'source':str(path),'target':target,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
  write('source-copy-inventory.json',{'files':inventory,'archive':pin(archive),'scope':result['source_copy_scope']})
  command('source-upload',['docker','cp',str(archive),NAME+':/tmp/boundary-source.tar.gz'])
  command('source-extract',['docker','exec','--user','root',NAME,'/bin/sh','-c','tar -xzf /tmp/boundary-source.tar.gz -C /opt/ipfs-supervisor && rm /tmp/boundary-source.tar.gz && chown -R root:root /opt/ipfs-supervisor/source /opt/ipfs-supervisor/datasets /opt/ipfs-supervisor/kit && find /opt/ipfs-supervisor/source /opt/ipfs-supervisor/datasets /opt/ipfs-supervisor/kit -type d -exec chmod 0755 {} +'])
  sys.path.insert(0,str(C))
  from benchmarks.agent_supervisor.container_coding.container_worker_deployment import install_worker_boundary,qualify_worker_boundary
  environment=DockerEnvironment()
  result['installation']=await install_worker_boundary(environment,container_name=NAME,output=OUT/'installation',observer_only=True)
  result['qualification']=await qualify_worker_boundary(environment,output=OUT/'qualification')
  final=command('final-public-identity',['docker','inspect','--format','{{json .Id}} {{json .Image}} {{json .State.Running}} {{json .HostConfig.NetworkMode}}',NAME])
  result['final_container_public_fields']=final.stdout.strip()
  result['qualified']=result['qualification']['qualified'] is True
  result['ready_for_root']=result['qualified']
  result['container_left_running']=True
  result['native_installer_source']=pin(C/'benchmarks/agent_supervisor/container_coding/container_worker_deployment.py')
 except BaseException as error:
  result['failure']={'type':type(error).__name__,'message':str(error)[:2048]}
  result['container_left_for_failure_review']=True
 finally:
  write('result.json',result)
  print(json.dumps({'qualified':result['qualified'],'failure':result.get('failure'),'container':NAME,'result':str(OUT/'result.json')}))
 return 0 if result['qualified'] else 1
if __name__=='__main__':raise SystemExit(asyncio.run(main()))
