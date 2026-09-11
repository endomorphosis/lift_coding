from pathlib import Path
import json,os,sys,subprocess,tempfile,hashlib,datetime,shutil
root=Path('/home/barberb/lift_coding');lane=root/'.worktrees/vericodegen-autoformalization-2026';out=root/'papers/completion/runtime_bootstrap/native_submodule_proof.json'
for k,v in {'IPFS_ACCEL_SKIP_CORE':'1','IPFS_AUTO_INSTALL':'false','IPFS_DATASETS_AUTO_INSTALL':'false','PYTHONDONTWRITEBYTECODE':'1'}.items():os.environ[k]=v
sys.path.insert(0,str(lane/'external/ipfs_accelerate'))
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon
paths=['external/ipfs_accelerate','external/ipfs_datasets','external/ipfs_kit']
parent=Path(tempfile.mkdtemp(prefix='vericodegen-native-submodule-proof-'));child=parent/'child'
def git(args,cwd):
 p=subprocess.run(['git',*args],cwd=cwd,capture_output=True,text=True)
 if p.returncode:raise RuntimeError(json.dumps({'args':args,'cwd':str(cwd),'code':p.returncode,'stderr':p.stderr[-2000:]}))
 return p.stdout.strip()
report={'schema':'vericodegen-native-submodule-proof/v1','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'lane':str(lane),'parent_commit':git(['rev-parse','HEAD'],lane),'test_worktree':str(child),'native_module':str(Path(sys.modules[PortalImplementationDaemon.__module__].__file__)),'native_method':'PortalImplementationDaemon._initialize_worktree_submodules','offline_local_only':True,'daemon_loop_started':False,'provider_invoked':False,'network_fetch_permitted':False,'root_index_sha256_before':hashlib.sha256((root/'.git/index').read_bytes()).hexdigest(),'results':[],'events':[],'cleanup':[]}
try:
 git(['worktree','add','--detach',str(child),report['parent_commit']],lane)
 daemon=object.__new__(PortalImplementationDaemon)
 daemon.repo_root=lane
 daemon.worktree_submodule_paths=tuple(paths)
 daemon._record_event=lambda name,payload:report['events'].append({'name':name,'payload':payload})
 daemon._initialize_worktree_submodules(child,branch_name='',offline_local_only=True,submodule_paths=paths)
 for rel in paths:
  wanted=git(['rev-parse',f'HEAD:{rel}'],child);actual=git(['rev-parse','HEAD'],child/rel)
  assert actual==wanted,(rel,wanted,actual)
  status=git(['status','--porcelain'],child/rel);assert not status,(rel,status)
  source_common=git(['rev-parse','--git-common-dir'],lane/rel)
  child_common=git(['rev-parse','--git-common-dir'],child/rel)
  source_common_path=(lane/rel/source_common).resolve() if not Path(source_common).is_absolute() else Path(source_common).resolve()
  child_common_path=(child/rel/child_common).resolve() if not Path(child_common).is_absolute() else Path(child_common).resolve()
  assert source_common_path==child_common_path,(rel,source_common_path,child_common_path)
  report['results'].append({'path':rel,'expected_pin':wanted,'actual_head':actual,'exact_pin_match':True,'clean':True,'source_common_gitdir':str(source_common_path),'child_common_gitdir':str(child_common_path),'source_is_lane_local':True})
 report['parent_child_status']=git(['status','--porcelain'],child);assert not report['parent_child_status']
 report['success']=True
except Exception as e:
 report['success']=False;report['error']=str(e)
 raise
finally:
 for rel in reversed(paths):
  target=child/rel
  if (target/'.git').exists():
   p=subprocess.run(['git','worktree','remove','--force',str(target)],cwd=lane/rel,capture_output=True,text=True)
   report['cleanup'].append({'path':str(target),'returncode':p.returncode,'removed':not target.exists(),'stderr':p.stderr[-1500:]})
 if child.exists():
  p=subprocess.run(['git','worktree','remove','--force',str(child)],cwd=lane,capture_output=True,text=True)
  report['cleanup'].append({'path':str(child),'returncode':p.returncode,'removed':not child.exists(),'stderr':p.stderr[-1500:]})
 if parent.exists() and not any(parent.iterdir()):parent.rmdir()
 report['temporary_parent_removed']=not parent.exists()
 report['root_index_bytes_unchanged']=hashlib.sha256((root/'.git/index').read_bytes()).hexdigest()==report['root_index_sha256_before']
 report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'report':str(out),'success':report['success'],'checked_submodules':len(report['results']),'temporary_parent_removed':report['temporary_parent_removed'],'root_index_bytes_unchanged':report['root_index_bytes_unchanged']},indent=2))
