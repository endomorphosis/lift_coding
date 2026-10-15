#!/usr/bin/env python3
"""Reuse an owned live model for a finite100source workload; no server launch."""
from pathlib import Path
import datetime,importlib.util,json,os,resource,signal,socket,subprocess,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
UNIT='leanstral-job-8b9fe90657f3440b8fefe811afebe081.service'
SERVER=2849431;WORKER=2849313;OUTER=2849113;FIRST_CLIENT=3092006
START=783092.787230;DEADLINE=START+10000
EXPECTED_START_TICKS={2849431: '78309289', 2849313: '78309277', 2849113: '78309248'}
STOP=False;CHILD=None
spec=importlib.util.spec_from_file_location('runner',ROOT/'scripts/run_leanstral_ephemeral.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def emit(record):
 record['at']=stamp()
 with (HERE/'warm_lifecycle.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
 print(json.dumps(record),flush=True)
def same_adopted_process(pid):
 try:return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]==EXPECTED_START_TICKS[pid]
 except (FileNotFoundError,KeyError):return False
def alive(pid):
 if pid in EXPECTED_START_TICKS and not same_adopted_process(pid):return False
 try:return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]!='Z'
 except FileNotFoundError:return False
def count():
 p=HERE/'natural_model/results.jsonl';return len(p.read_text().splitlines()) if p.exists() else 0
def stop(signum,frame):
 global STOP
 STOP=True
 if CHILD and CHILD.poll() is None:CHILD.terminate()
def guard():
 if STOP:raise InterruptedError('user_or_parent_stop')
 if time.monotonic()>=DEADLINE:raise TimeoutError('10000second_original_unit_deadline')
 if not alive(SERVER):raise RuntimeError('warm_server_exited')
 tree=runner.proc_tree(SERVER)
 if CHILD is not None and CHILD.poll() is None:tree.update(runner.proc_tree(CHILD.pid))
 if sum(x['rss'] for x in tree.values())>90*1024**3:raise MemoryError('90GiBaggregate_resident_guard')
 if runner.mem_available()<12*1024**3:raise MemoryError('12GiBhost_reserve_guard')
 if sum(x['threads'] for x in tree.values())>128:raise RuntimeError('128taskguard')
def child_limits():
 os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
 resource.setrlimit(resource.RLIMIT_CPU,(10000,10000));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(1024**3,1024**3))
def cleanup():
 if CHILD is not None and CHILD.poll() is None:
  CHILD.terminate()
  try:CHILD.wait(timeout=8)
  except subprocess.TimeoutExpired:CHILD.kill();CHILD.wait()
 # Restores original supervisor cleanup path: its client has finished or its
 # original deadline has elapsed, so it immediately removes all owned children.
 for pid in [WORKER,OUTER]:
  try:
   if same_adopted_process(pid):os.kill(pid,signal.SIGCONT)
  except ProcessLookupError:pass
 try:subprocess.run(['systemctl','--user','stop',UNIT],capture_output=True,timeout=10)
 except subprocess.TimeoutExpired:subprocess.run(['systemctl','--user','kill',UNIT],capture_output=True,timeout=5)
 # Remove only this task's volatile drop-in, never permanent service settings.
 drop=Path('/run/user/1000/systemd/transient')/(UNIT+'.d')/'50-active-batch-runtime.conf'
 if drop.exists():drop.unlink()
 try:drop.parent.rmdir()
 except OSError:pass
 subprocess.run(['systemctl','--user','daemon-reload'],capture_output=True,timeout=10)
 with socket.socket() as s:s.settimeout(1);closed=s.connect_ex(('127.0.0.1',8080))!=0
 emit(dict(event='warm_cleanup',server_alive=alive(SERVER),port8080closed=closed,completed=count()))
def main():
 global CHILD
 if (HERE/'warm_lifecycle.jsonl').exists():raise RuntimeError('One-shot adoption already recorded; refuse rerun against potentially recycled PIDs; use portable run_natural_workload.py')
 if not all(same_adopted_process(pid) for pid in EXPECTED_START_TICKS):raise RuntimeError('Adopted process identities no longer match')
 mainpid=subprocess.check_output(['systemctl','--user','show',UNIT,'--value','-p','MainPID'],text=True).strip()
 if mainpid!=str(WORKER):raise RuntimeError('Transient unit no longer belongs to expected worker')
 cmdline=Path(f'/proc/{SERVER}/cmdline').read_bytes().split(b'\x00')
 expected_model=str(runner.DEFAULT_MODEL).encode()
 if expected_model not in cmdline or b'--model' not in cmdline:raise RuntimeError('Server model identity does not match')
 for sig in [signal.SIGINT,signal.SIGTERM,signal.SIGHUP]:signal.signal(sig,stop)
 emit(dict(event='warm_continuation_started',same_server_pid=SERVER,completed=count(),original_unit_start_monotonic=START,hard_wall_seconds=10000,hard_deadline_utc='2026-09-14T10:56:26+00:00',memory_gib=90,cpus=4))
 try:
  while alive(FIRST_CLIENT):guard();time.sleep(.2)
  emit(dict(event='original_client_complete_model_retained',completed=count()))
  env=os.environ.copy();env.update(LEANSTRAL_BASE_URL='http://127.0.0.1:8080/v1',LEANSTRAL_ENDPOINT='http://127.0.0.1:8080/v1',IPFS_ACCELERATE_LLAMA_CPP_AUTOSTART='0',IPFS_ACCELERATE_PY_LLAMA_CPP_AUTOSTART='0',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
  for batch in range(1,8):
   if count()>=100:emit(dict(event='all100_complete_same_model',completed=count()));return 0
   guard();before=count();log=HERE/f'natural_warm_client_{batch:02d}.log';emit(dict(event='warm_client_started',batch=batch,completed_before=before))
   with log.open('x') as f:
    CHILD=subprocess.Popen([sys.executable,'-B',str(HERE/'run_natural_a.py'),'run','--client-soft-stop','1320'],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,preexec_fn=child_limits)
    while CHILD.poll() is None:guard();time.sleep(.2)
   emit(dict(event='warm_client_finished_model_retained',batch=batch,returncode=CHILD.returncode,completed=count()))
   if CHILD.returncode or count()<=before:return 1
  return 0 if count()==100 else 2
 except BaseException as exc:emit(dict(event='warm_continuation_failed',error=type(exc).__name__+': '+str(exc),completed=count()));return 3
 finally:cleanup()
if __name__=='__main__':raise SystemExit(main())
