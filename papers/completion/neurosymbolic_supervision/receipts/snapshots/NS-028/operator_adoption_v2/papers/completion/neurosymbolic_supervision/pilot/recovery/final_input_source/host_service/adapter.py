"""Host-only historical source/cold-scorer adapter. Worker input is a unit ID only.

Registry manifests are private operator authority. Only separately admitted final registry inputs are
accepted by this final adapter, and no reference patch is ever consumed.
"""
from pathlib import Path,PurePosixPath
import difflib,hashlib,json,os,shutil,stat,subprocess,tarfile,tempfile,time,uuid
IMAGE='sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6'
DOCKER=['/usr/bin/docker','--host=unix:///var/run/docker.sock']
MAX_BYTES=64*1024*1024
MAX_PATCH_BYTES=16*1024
SCORER_PROFILE={'image':IMAGE,'cpu_count':1,'memory_bytes':2147483648,'pids':128,'wall_seconds_max':120,'child_shared_wall_seconds_max':115,'network':'none','runtime':'runc'}

def require(ok,message):
 if not ok:raise ValueError(message)
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def read(path,limit=MAX_BYTES):
 p=Path(path);require(p.is_absolute() and p.resolve()==p,'noncanonical private input')
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  s=os.fstat(fd);require(stat.S_ISREG(s.st_mode) and s.st_size<=limit,'nonregular/oversized input')
  with os.fdopen(fd,'rb',closefd=False) as h:data=h.read(limit+1)
  require(len(data)<=limit,'oversized input');return data
 finally:os.close(fd)
def sha(path):return hashlib.sha256(read(path)).hexdigest()
def write(path,data,mode=0o600):
 p=Path(path);require(p.parent.resolve()==p.parent,'unsafe write parent');fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
 try:
  os.fchmod(fd,mode)  # Preserve exact source mode regardless of the private host umask.
  with os.fdopen(fd,'wb',closefd=False) as h:h.write(data);h.flush();os.fsync(h.fileno())
 finally:os.close(fd)
def safe_rel(value):
 require(type(value)is str and value and '\\'not in value and not any(ord(c)<32 or ord(c)==127 for c in value),'unsafe relative path')
 p=PurePosixPath(value);require(not p.is_absolute() and str(p)==value and not any(x in ('.','..','.git') for x in p.parts),'unsafe relative path');return value

def inventory(root):
 root=Path(root);require(root.is_absolute() and root.resolve()==root and root.is_dir(),'unsafe tree')
 result={};total=0
 for p in sorted(root.rglob('*')):
  rel=safe_rel(p.relative_to(root).as_posix());s=p.lstat()
  if p.is_symlink():
   require(not os.path.isabs(os.readlink(p)) and p.resolve(strict=True).is_relative_to(root) and p.resolve().is_file(),'escaping/non-file source symlink')
   result[rel]={'kind':'symlink','target':os.readlink(p)};continue
  require(stat.S_ISDIR(s.st_mode)or stat.S_ISREG(s.st_mode),'special file in export')
  if p.is_file():
   require(s.st_nlink==1,'multiply linked export file');total+=s.st_size;require(total<=MAX_BYTES and len(result)<20000,'tree exceeds bound')
   result[rel]={'kind':'file','sha256':sha(p),'bytes':s.st_size,'mode':stat.S_IMODE(s.st_mode)}
 return result

def archive_tree(archive,expected_sha,destination):
 require(sha(archive)==expected_sha,'pre-fix archive changed');destination=Path(destination);destination.mkdir(mode=0o700)
 total=0;names=set();links=[]
 with tarfile.open(archive,'r:gz') as tf:
  members=tf.getmembers();require(len(members)<=20000,'archive member bound')
  for m in members:
   parts=PurePosixPath(m.name).parts;require(parts and not m.name.startswith('/'),'unsafe archive member')
   if len(parts)==1:continue
   rel=safe_rel('/'.join(parts[1:]));require(rel not in names,'duplicate archive member');names.add(rel)
   if m.issym():
    require(not os.path.isabs(m.linkname),'absolute archive link');links.append((rel,m.linkname));continue
   require(m.isdir() or m.isfile(),'unsupported archive hardlink/special file')
   if any(x=='.git' for x in PurePosixPath(rel).parts):continue
   p=destination/rel;p.parent.mkdir(parents=True,exist_ok=True)
   if m.isdir():p.mkdir(exist_ok=True);continue
   total+=m.size;require(total<=MAX_BYTES,'archive byte bound')
   with tf.extractfile(m) as h:data=h.read(MAX_BYTES+1)
   require(len(data)==m.size,'archive member differs');write(p,data,0o755 if m.mode&0o111 else 0o644)
 for rel,target in links:
  p=destination/rel;p.parent.mkdir(parents=True,exist_ok=True);require(not p.exists() and (p.parent/target).resolve(strict=True).is_relative_to(destination),'archive link escape');p.symlink_to(target)
 return inventory(destination)

def validate_manifest(manifest):
 require(manifest['schema']=='ns-historical-host-unit/v1' and manifest['split']=='final','only frozen pilot units admitted')
 require(manifest['image']==IMAGE and manifest['source_archive']['sha256'] and manifest['proposal_files'],'missing bound source')
 require(set(manifest['allowed_edit_paths'])<=set(manifest['proposal_files']),'edit authority outside export')
 for path in manifest['allowed_edit_paths']:safe_rel(path)
 require(manifest['hidden_oracle_loaded_in_proposal'] is False,'proposal oracle authority forbidden')
 require(manifest['scorer_profile']==SCORER_PROFILE,'scorer profile changed')
 require(manifest['max_patch_bytes']==MAX_PATCH_BYTES,'historical patch budget changed')
 require(len(manifest['prompt'].encode())<=64*1024,'prompt exceeds visible-request budget')
 require(sha(manifest['source_archive']['path'])==manifest['source_archive']['sha256'],'archive identity changed')
 return manifest

def lookup_unit(registry_path,registry_sha256,unit_id):
 """Only the root-admitted private registry maps a worker's opaque unit ID."""
 p=Path(registry_path);require(p.stat().st_mode&0o077==0 and p.parent.stat().st_mode&0o077==0,'registry is not private')
 require(sha(p)==registry_sha256,'registry identity changed');registry=json.loads(read(p));require(registry['schema']=='ns-historical-private-final-registry/v1'and registry.get('pilot_execution_admitted')is False and registry.get('final_execution_admitted')is True,'explicit isolated pilot registry required')
 require(set(registry['units'])==set(__import__('batch_control').UNITS)and all(m.get('split')=='final'for m in registry['units'].values()),'pilot registry population differs')
 for path,expected in registry['source_bindings'].items():require(sha(path)==expected,'registry dependency changed')
 require(type(unit_id)is str and unit_id in registry['units'],'unit not admitted')
 return validate_manifest(registry['units'][unit_id])


def prepare_admitted_unit(private,admitted_manifest):
 """Host-only: return clean proposal+prompt; grant must pin this manifest digest."""
 m=validate_manifest(admitted_manifest);private=Path(private);require(private.is_absolute()and private.resolve()==private,'private directory not canonical');private.mkdir(mode=0o700,parents=True,exist_ok=True)
 require(not(private/'proposal').exists(),'existing proposal cannot be overwritten')
 with tempfile.TemporaryDirectory(prefix='historical-prefixed-export-') as td:
  tree=Path(td)/'tree';observed=archive_tree(m['source_archive']['path'],m['source_archive']['sha256'],tree);require(observed==m['full_source_files'],'pre-fix tree differs')
  proposal=private/'proposal';proposal.mkdir(mode=0o700)
  for rel,spec in m['proposal_files'].items():
   p=proposal/rel;p.parent.mkdir(parents=True,exist_ok=True)
   if spec.get('kind')=='symlink':p.symlink_to(spec['target'])
   else:write(p,read(tree/rel),spec['mode'])
  require(inventory(proposal)==m['proposal_files'],'proposal export differs')
 write(private/'prompt.txt',m['prompt'].encode());write(private/'unit_manifest.private.json',canonical(m))
 return {'unit_id':m['unit_id'],'split':m['split'],'proposal_root':str(proposal),'source_preimage_sha256':digest(m['proposal_files']),'prompt_sha256':hashlib.sha256(m['prompt'].encode()).hexdigest(),'manifest_sha256':digest(m),'allowed_edit_paths':m['allowed_edit_paths'],'historical_evaluation_executed':False}

def candidate_binding(sealed,manifest):
 m=validate_manifest(manifest);actual=inventory(Path(sealed));before=m['proposal_files'];require(set(actual)==set(before),'candidate path population changed')
 changed=[]
 for path,spec in actual.items():
  require(spec.get('mode')==before[path].get('mode') and spec.get('kind')==before[path].get('kind'),'candidate mode/type changed')
  if spec!=before[path]:require(path in m['allowed_edit_paths'],'candidate changed non-admitted source');changed.append(path)
 patch=b''
 if changed:
  with tempfile.TemporaryDirectory(prefix='historical-patch-preimage-')as td:
   tree=Path(td)/'tree';require(archive_tree(m['source_archive']['path'],m['source_archive']['sha256'],tree)==m['full_source_files'],'patch preimage changed')
   for path in sorted(changed):
    require(actual[path]['kind']=='file','symlink edits not admitted')
    old=read(tree/path).decode('utf-8');new=read(Path(sealed)/path).decode('utf-8');require('\0'not in old+new,'binary source edit forbidden')
    lines=difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path,n=3)
    patch+=('diff --git a/'+path+' b/'+path+'\n'+''.join(line if line.endswith('\n')else line+'\n\\ No newline at end of file\n'for line in lines)).encode()
    require(len(patch)<=MAX_PATCH_BYTES,'historical patch exceeds frozen 16KiB budget')
 return {'files':actual,'sha256':digest(actual),'changed_paths':changed,'patch_bytes':len(patch),'patch_sha256':hashlib.sha256(patch).hexdigest()}

def score_sealed_candidate(private,sealed,admitted_manifest):
 """Host-only cold scorer. Real hidden tests are loaded inside the container.

Caller first terminates the proposal process and binds the sealed inventory in
its one-use grant. This function starts no model/provider and returns no bodies.
"""
 m=validate_manifest(admitted_manifest);private=Path(private);sealed=Path(sealed);binding=candidate_binding(sealed,m)
 target=private/'historical_scorer';require(not target.exists(),'preserve prior score; no automatic rerun');target.mkdir(mode=0o700)
 source=target/'source';require(archive_tree(m['source_archive']['path'],m['source_archive']['sha256'],source)==m['full_source_files'],'scorer source differs')
 custody=target/'custody';custody.mkdir(mode=0o700)
 for key,spec in m['custody_objects'].items():
  require(key==spec['sha256'] and sha(spec['path'])==key,'opaque custody identity changed');write(custody/key,read(spec['path']),0o444)
 driver=Path(__file__).with_name('cold_scorer.py').resolve();require(sha(driver)==m['scorer_driver_sha256'],'scorer driver changed')
 recipe={'schema':'ns-historical-cold-recipe/v1','unit_id':m['unit_id'],'source_files':m['full_source_files'],'proposal_files':m['proposal_files'],'candidate':binding,'allowed_edit_paths':m['allowed_edit_paths'],'visible_nodes':m['visible_nodes'],'oracle_metadata_sha256':m['oracle_metadata_sha256'],'custody_files':m['custody_files'],'hidden_test_sha256':m['hidden_test_sha256'],'expected_hidden_nodes_sha256':m['expected_hidden_nodes_sha256'],'expected_hidden_count':m['expected_hidden_count'],'expected_visible_collected_count':m['expected_visible_collected_count']}
 write(target/'recipe.json',canonical(recipe),0o444);results=target/'results';results.mkdir(mode=0o700)
 capture=Path(m['capture_plugin']['path']);wheel=Path(m['dependency_wheel']['path']);require(sha(capture)==m['capture_plugin']['sha256']and sha(wheel)==m['dependency_wheel']['sha256'],'scorer dependency changed')
 name='ns-historical-cold-'+uuid.uuid4().hex;cid=target/'container.cid'
 argv=DOCKER+['create','--name',name,'--cidfile',str(cid),'--network=none','--read-only','--runtime=runc','--cap-drop=ALL','--security-opt=no-new-privileges','--user',f'{os.getuid()}:{os.getgid()}','--cpus=1','--memory=2g','--memory-swap=2g','--pids-limit=128','--tmpfs',f'/tmp:rw,nosuid,nodev,size=268435456,mode=0700,uid={os.getuid()},gid={os.getgid()}','--tmpfs',f'/work:rw,nosuid,nodev,size=134217728,mode=0700,uid={os.getuid()},gid={os.getgid()}','--workdir=/work','--entrypoint=/usr/bin/env']
 mounts=[(source,'/preimage'),(sealed,'/candidate'),(custody,'/custody'),(driver,'/runner/cold_scorer.py'),(target/'recipe.json','/runner/recipe.json'),(capture,'/capture/baseline_capture.py'),(wheel,'/railroad.whl')]
 for src,dst in mounts:argv+=['--mount',f'type=bind,src={src},dst={dst},readonly']
 argv+=['--mount',f'type=bind,src={results},dst=/results',IMAGE,'-i','HOME=/tmp','PATH=/usr/local/bin:/usr/bin:/bin','PYTHONDONTWRITEBYTECODE=1','PYTEST_DISABLE_PLUGIN_AUTOLOAD=1','python3','-I','-B','/runner/cold_scorer.py']
 write(target/'command.private.json',canonical(argv));created=subprocess.run(argv,capture_output=True,timeout=30);require(created.returncode==0,'scorer create failed');exact=read(cid,100).decode().strip();require(len(exact)==64 and all(c in'0123456789abcdef'for c in exact),'scorer identity invalid')
 try:
  inspect=json.loads(subprocess.check_output(DOCKER+['inspect',exact],timeout=20))[0];h=inspect['HostConfig'];actual={x['Source']:x for x in inspect['Mounts']if x['Type']=='bind'}
  require(inspect['Image']==IMAGE and not inspect['State']['Running']and set(actual)=={str(x[0])for x in mounts}|{str(results)},'scorer mount/image admission failed')
  require(all(not actual[str(src)]['RW']for src,_ in mounts)and h['NetworkMode']=='none'and h['NanoCpus']==1000000000 and h['Memory']==2147483648 and h['PidsLimit']==128 and h['ReadonlyRootfs']and not h.get('Privileged'),'scorer boundary/resource mismatch')
  require(all(actual[str(src)]['Destination']==dst for src,dst in mounts)and actual[str(results)]['Destination']=='/results'and actual[str(results)]['RW'],'scorer destination admission failed')
  require(h['Runtime']=='runc'and h['MemorySwap']==h['Memory']and set(h['CapDrop'])=={'ALL'}and h['SecurityOpt']==['no-new-privileges']and not h.get('Devices')and not h.get('DeviceRequests'),'scorer privilege boundary mismatch')
  require(inspect['Config']['User']==f'{os.getuid()}:{os.getgid()}'and inspect['Config']['WorkingDir']=='/work'and inspect['Config']['Entrypoint']==['/usr/bin/env'],'scorer execution identity differs')
  require(set(h['Tmpfs'])=={'/tmp','/work'}and all('nosuid'in options and 'nodev'in options for options in h['Tmpfs'].values()),'scorer scratch boundary differs')
  write(target/'boundary.private.json',canonical({'image':inspect['Image'],'resources':{k:h[k]for k in['NetworkMode','NanoCpus','Memory','MemorySwap','PidsLimit','ReadonlyRootfs','Runtime','CapDrop','SecurityOpt','Tmpfs']},'mounts':[{'source':s,'destination':v['Destination'],'writable':v['RW']}for s,v in actual.items()],'checked_before_start':True}))
  timedout=False
  with (target/'stdout.private.log').open('xb')as out,(target/'stderr.private.log').open('xb')as err:
   os.chmod(out.name,0o600);os.chmod(err.name,0o600)
   try:r=subprocess.run(DOCKER+['start','--attach',exact],stdout=out,stderr=err,timeout=SCORER_PROFILE['wall_seconds_max']);rc=r.returncode
   except subprocess.TimeoutExpired:timedout=True;rc=124;subprocess.run(DOCKER+['kill',exact],capture_output=True,timeout=15)
  require(candidate_binding(sealed,m)==binding,'sealed candidate drifted while scoring')
  result=json.loads(read(results/'result.json')) if (results/'result.json').exists()else {'schema':'ns-historical-cold-result/v1','success':False,'classification':'scorer_no_result'}
  allowed={'schema','success','classification','visible_collected','visible_passed','visible_skipped','hidden_collected','hidden_passed','hidden_skipped','baseline_exit','hidden_exit','observation_hashes'}
  require(set(result)<=allowed and result.get('schema')=='ns-historical-cold-result/v1' and type(result.get('success'))is bool,'scorer returned unapproved result')
  require(result.get('classification')in {'passed','visible_regression_failed','hidden_acceptance_failed','scorer_input_or_execution_error','scorer_no_result'},'scorer classification unapproved')
  for key,value in result.items():
   if key in {'visible_collected','visible_passed','visible_skipped','hidden_collected','hidden_passed','hidden_skipped'}:require(type(value)is int and 0<=value<=100000,'scorer count invalid')
   if key in {'baseline_exit','hidden_exit'}:require(type(value)is int and -128<=value<=255,'scorer exit invalid')
  hashes=result.get('observation_hashes',{});require(type(hashes)is dict and set(hashes)<={'visible','hidden'} and all(value is None or (type(value)is str and len(value)==64 and all(c in '0123456789abcdef'for c in value))for value in hashes.values()),'scorer digest invalid')
  response={'schema':'ns-historical-cold-host-result/v1','unit_id':m['unit_id'],'split':m['split'],'manifest_sha256':digest(m),'candidate_sha256':binding['sha256'],'container_exit_code':rc,'timed_out':timedout,'scorer':result,'success':rc==0 and not timedout and result.get('success')is True,'provider_invoked':False,'classification_scope':'historical_final_AB_cold_only','private_log_sha256':{n:sha(target/n)for n in['stdout.private.log','stderr.private.log']},'boundary_sha256':sha(target/'boundary.private.json')}
  write(target/'host_result.json',canonical(response));return response
 finally:
  cleanup=subprocess.run(DOCKER+['rm','-f',exact],capture_output=True,timeout=20);write(target/'cleanup.json',canonical({'container':exact,'returncode':cleanup.returncode}));require(cleanup.returncode==0,'scorer cleanup failed')
