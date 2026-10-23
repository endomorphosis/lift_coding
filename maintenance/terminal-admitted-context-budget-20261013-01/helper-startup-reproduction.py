"""Finite owned Docker fixture; authored metadata only, never admitted authority."""
import ast
import hashlib
import json
import pathlib
import subprocess

AREA = pathlib.Path(__file__).resolve().parent
SOURCE = AREA / "checkout/benchmarks/agent_supervisor/container_coding/container_worker_deployment.py"
TEST = AREA / "checkout/test/api/test_checked_context_native_integration.py"
IMAGE = "ipfs-supervisor-preview-worker:20261005-r3"
NAME = "ipfs-worker-helper-startup-aa18-metadata"

values = {}
def literal(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return values[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return literal(node.left) + literal(node.right)
    raise ValueError("nonliteral deployment entry")
for node in ast.parse(SOURCE.read_text()).body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        try:
            values[node.targets[0].id] = literal(node.value)
        except (ValueError, KeyError):
            pass

TARGET = r'''
import ctypes,json,os,pathlib,sys,time
status=lambda:dict(line.split(':',1) for line in pathlib.Path('/proc/self/status').read_text().splitlines() if ':' in line)
print(json.dumps({'pid':os.getpid(),'nnp':status()['NoNewPrivs'].strip()}),flush=True)
line=sys.stdin.readline().strip()
if line=='ready':
 if ctypes.CDLL(None).prctl(38,1,0,0,0)!=0:raise SystemExit(3)
elif line=='cwd':os.chdir('/opt/ipfs-supervisor/worktrees/other')
time.sleep(5)
'''

RUNNER = r'''
import hashlib,json,os,pathlib,stat,subprocess,sys,threading,time
root=pathlib.Path('/opt/ipfs-supervisor')
root.mkdir(parents=True,exist_ok=True)
for path in [root,*root.parents]:os.chown(path,0,0);os.chmod(path,0o755)
(root/'bin').mkdir(exist_ok=True);os.chown(root/'bin',0,0);os.chmod(root/'bin',0o755)
for name in ('state-fixture','home-fixture','auth-fixture'):
 path=root/name;path.mkdir(exist_ok=True);os.chown(path,1000,1000);os.chmod(path,0o700)
worktrees=root/'worktrees';worktrees.mkdir(exist_ok=True);os.chown(worktrees,0,1000);os.chmod(worktrees,0o750)
for name in ('authored','other'):
 path=worktrees/name;path.mkdir(exist_ok=True);os.chown(path,1001,1001);os.chmod(path,0o700)
target=root/'bin/worker-entry';target.write_text(TARGET);os.chown(target,0,0);os.chmod(target,0o555)
helper=root/'bin/metadata-observer-fixture';helper.write_text(ENTRY);os.chown(helper,0,0);os.chmod(helper,0o555)
namespaces={key:os.readlink('/proc/self/ns/'+key) for key in ('pid','mnt','net')}
boundary={'schema':'supervisor-container-worker-boundary@1','container_id':'a'*64,'image_id':'sha256:'+'b'*64,
 'namespaces':namespaces,'owner_uid':1000,'worker_uid':1001,'single_worker':True,
 'allowed_worktree_roots':[str(worktrees)],'owner_private_paths':[str(root/name) for name in ('state-fixture','home-fixture','auth-fixture')],
 'validation_repository_roots':['/app']}
wire=lambda value:(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
raw=wire(boundary)
for name,data in [('container-boundary.json',raw),('worker-profile.json',wire({'schema':'container-worker-deployment-profile@1','observer_only':True,'boundary_sha256':hashlib.sha256(raw).hexdigest()}))]:
 path=root/name;path.write_bytes(data);os.chown(path,0,0);os.chmod(path,0o444)
def worker_uid():
 os.setgroups([1000]);os.setgid(1001);os.setuid(1001)
results=[]
for mode in ('ready','never','cwd'):
 child=subprocess.Popen([sys.executable,'-I',str(target),'--authored-metadata-only'],cwd=worktrees/'authored',
  stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,preexec_fn=worker_uid)
 try:
  initial=json.loads(child.stdout.readline());pid=initial['pid']
  status=pathlib.Path('/proc/'+str(pid)+'/status').read_text()
  facts=pathlib.Path('/proc/'+str(pid)+'/stat').read_text().rsplit(') ',1)[1].split();ticks=int(facts[19]);parent=int(facts[1])
  boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
  birth='birth:'+hashlib.sha256((str(pid)+':'+str(ticks)+':'+boot+':'+str(parent)).encode()).hexdigest()[:32]
  if initial['nnp']!='0':raise RuntimeError('fixture target must begin NNP0')
  def transition():
   time.sleep(.25)
   if mode!='never':child.stdin.write(mode+'\n');child.stdin.flush()
  thread=threading.Thread(target=transition);thread.start()
  started=time.monotonic()
  response=subprocess.run([sys.executable,'-I',str(helper),'--observe-worker-worktree',str(pid),str(ticks),birth,str(worktrees/'authored')],
    cwd='/',env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
    timeout=3.0,preexec_fn=worker_uid)
  elapsed=time.monotonic()-started;thread.join(timeout=1)
  value=json.loads(response.stdout)
  current=dict(line.split(':',1) for line in pathlib.Path('/proc/'+str(pid)+'/status').read_text().splitlines() if ':' in line)
  expected=(mode=='ready' and response.returncode==0 and value['schema']=='checked-worker-kernel-worktree-observation@1'
    and value['pid']==pid and value['process_birth_id']==birth and current['NoNewPrivs'].strip()=='1'
    and .20<=elapsed<3) or (mode in ('never','cwd') and response.returncode==1
      and value['schema']=='checked-worker-kernel-worktree-refusal@1'
      and value['stage']==('readiness' if mode=='never' else 'target_birth_worktree'))
  if not expected:raise RuntimeError('closed real-kernel fixture predicate mismatch')
  results.append({'mode':mode,'initial_nnp':0,'final_nnp':int(current['NoNewPrivs'].strip()),
   'uid_fields':[int(x) for x in current['Uid'].split()], 'caps':{key:current[key].strip() for key in ('CapEff','CapPrm','CapAmb')},
   'elapsed_seconds':elapsed,'returncode':response.returncode,'response':value,'qualified':True})
 finally:
  child.terminate()
  try:child.wait(timeout=2)
  except subprocess.TimeoutExpired:child.kill();child.wait(timeout=2)
print(json.dumps({'cases':results,'all_authored_children_stopped':True},sort_keys=True))
'''

image_id = subprocess.check_output(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"], text=True).strip()
cid = None
cleanup = None
result = None
try:
    cid = subprocess.check_output(["docker", "run", "-d", "--name", NAME, "--network", "none",
        "--user", "0", "--entrypoint", "/bin/sleep", IMAGE, "45"], text=True, timeout=15).strip()
    wrapper = """
try:
 exec(compile(RUNNER,'<authored-metadata-runner>','exec'))
except BaseException as error:
 import hashlib,json,traceback
 print(json.dumps({'authored_fixture_error_type':type(error).__name__,
  'message_sha256':hashlib.sha256(str(error).encode()).hexdigest(),
  'frames':[{'file':x.filename.rsplit('/',1)[-1],'function':x.name,'line':x.lineno} for x in traceback.extract_tb(error.__traceback__)][-16:]}))
 raise SystemExit(1)
"""
    code = "ENTRY=" + repr(values["WORKER_ENTRY"]) + "\nTARGET=" + repr(TARGET) + "\nRUNNER=" + repr(RUNNER) + "\n" + wrapper
    run = subprocess.run(["docker", "exec", "-i", cid, "python3", "-I", "-"], input=code.encode(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    if run.returncode != 0:
        print(run.stdout.decode())
        raise RuntimeError("authored metadata fixture failed: " + str(run.returncode) + " stderr_sha256=" + hashlib.sha256(run.stderr).hexdigest())
    result = json.loads(run.stdout)
finally:
    if cid is not None:
        removed = subprocess.run(["docker", "rm", "-f", cid], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        check = subprocess.run(["docker", "inspect", cid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        cleanup = {"exact_container_id": cid, "remove_returncode": removed.returncode, "inspect_absent": check.returncode != 0}

def pin(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
report = {"schema": "authored-worker-metadata-readiness-reproduction@1",
    "sources": {"deployment": pin(SOURCE), "integration_tests": pin(TEST), "writer": pin(pathlib.Path(__file__).resolve())},
    "image_id": image_id, "fixture": result, "cleanup": cleanup,
    "scope": "real-kernel exact-PID same-UID metadata observation over authored target startup only",
    "installed_owner_helper_custody_exercised": False, "admitted_native_origin": False,
    "actual17_failure_cause_established": False,
    "repository_code_executed": False, "model_calls": 0, "provider_calls": 0,
    "execution_authority": False, "proof_authority": False, "completion_authority": False,
    "source_model_equivalence": False, "training_convergence_proved": False, "full_task_satisfaction": False}
path = AREA / "helper-startup-reproduction.json"
assert not path.exists(), "do not overwrite existing evidence"
path.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
print(json.dumps({"report": str(path), "qualified": True, "cases": len(result["cases"]), "cleanup": cleanup}))
