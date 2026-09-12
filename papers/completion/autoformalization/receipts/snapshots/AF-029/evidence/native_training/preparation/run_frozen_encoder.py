"""Exact offline Docker execution of one frozen encoder preparation."""
from pathlib import Path
import subprocess,json,hashlib,time,os,sys
BASE=Path(__file__).resolve().parent
ref=json.loads((BASE/'encoder_preparation_frozen.private.json').read_text());private=Path(ref['private_root']);manifest_path=private/'job/preprocessing_manifest.json';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();manifest=json.loads(manifest_path.read_text());assert sha(manifest_path)==ref['manifest_sha256']
DOCKER=['docker','--host','unix:///var/run/docker.sock'];name='af-native-training-encoder-20260912-'+ref['manifest_sha256'][:12]
cmd=DOCKER+['create','--name',name,'--cidfile',str(private/'container.cid'),'--runtime','runc','--network','none','--cpus','1','--memory','2g','--memory-swap','2g','--pids-limit','64','--user','1000:1000','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,nodev,size=128m','--workdir','/job']
mounts=[(Path('/usr'),'/usr',False),(private/'job','/job',False),(Path(ref['assets_root'])/'encoder','/encoder',False),(Path(ref['python_dependency_root']),'/encoder-python',False),(Path(manifest['runtime']['research_runtime_root']),'/research',False),(private/'output','/output',True)]
for source,dest,rw in mounts:cmd+=['--mount',f'type=bind,source={source},target={dest}'+(''if rw else',readonly')]
env={'HOME':'/tmp','PATH':'/usr/bin:/bin','PYTHONPATH':'/research/python:/encoder-python','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','HF_HOME':'/tmp/hf','CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','TOKENIZERS_PARALLELISM':'false','USE_TORCH':'1','USE_TF':'0','TORCH_DEVICE_BACKEND_AUTOLOAD':'0'}
for k,v in env.items():cmd+=['--env',k+'='+v]
assert sha('/usr/bin/python3.12')==manifest['runtime']['python_executable_sha256']
cmd +=['--entrypoint','/usr/bin/python3.12',manifest['runtime']['image'],'-S','/job/encode_train_selection.py']
def save(name,value):
 p=private/name
 with p.open('xb')as f:f.write((json.dumps(value,sort_keys=True,indent=2)+'\n').encode());f.flush();os.fsync(f.fileno())
save('command.json',cmd);save('launch_binding.json',{'manifest_sha256':sha(manifest_path),'producer_sha256':sha(private/'job/encode_train_selection.py'),'launcher_sha256':sha(Path(__file__)),'env':env,'created_before_inference':True})
created=subprocess.run(cmd,capture_output=True,text=True,timeout=30);save('create.json',{'exit_code':created.returncode,'stdout':created.stdout.strip(),'stderr':created.stderr});assert created.returncode==0
cid=(private/'container.cid').read_text().strip();assert len(cid)==64
result={'status':'incomplete','container':cid,'provider_calls':0,'manifest_sha256':sha(manifest_path),'start_monotonic':time.monotonic()}
try:
 inspection=json.loads(subprocess.run(DOCKER+['inspect',cid],check=True,capture_output=True,text=True,timeout=20).stdout)[0];h=inspection['HostConfig'];actual={(m['Source'],m['Destination'],m['RW'])for m in inspection['Mounts']}
 assert actual=={(str(s),d,w)for s,d,w in mounts};assert h['NetworkMode']=='none'and h['NanoCpus']==1000000000 and h['Memory']==h['MemorySwap']==2147483648 and h['PidsLimit']==64 and h['ReadonlyRootfs'] and not h['Privileged'] and inspection['Image']==manifest['runtime']['image'];assert set(h['CapDrop'])=={'ALL'}and h['SecurityOpt']==['no-new-privileges']
 save('boundary.json',{'image':inspection['Image'],'user':inspection['Config']['User'],'entrypoint':inspection['Config']['Entrypoint'],'cmd':inspection['Config']['Cmd'],'mounts':inspection['Mounts'],'resources':{k:h[k]for k in ['NetworkMode','NanoCpus','Memory','MemorySwap','PidsLimit','ReadonlyRootfs','Runtime','CapDrop','SecurityOpt','Tmpfs']},'checked_before_start':True})
 with(private/'stdout.log').open('xb')as out,(private/'stderr.log').open('xb')as err:
  try:code=subprocess.run(DOCKER+['start','--attach',cid],stdout=out,stderr=err,timeout=1800).returncode
  except subprocess.TimeoutExpired:subprocess.run(DOCKER+['kill',cid],capture_output=True,timeout=15);code=124
  out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
 state=json.loads(subprocess.run(DOCKER+['inspect',cid],check=True,capture_output=True,text=True,timeout=20).stdout)[0]['State'];save('exit_state.json',state)
 assert not state['Running'];result.update(exit_code=code,container_state=state,status='completed'if code==0 else'stopped_failed',wall_seconds=time.monotonic()-result['start_monotonic'])
finally:
 cleanup=subprocess.run(DOCKER+['rm','-f',cid],capture_output=True,text=True,timeout=20);save('cleanup.json',{'container':cid,'exit_code':cleanup.returncode,'stderr':cleanup.stderr});result['cleanup_exit_code']=cleanup.returncode;save('execution_status.json',result)
print(json.dumps(result))
