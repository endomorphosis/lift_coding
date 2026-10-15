#!/usr/bin/env python3
"""Finite continuation of frozen natural100requests, bounded server per shard."""
from pathlib import Path
import argparse,json,os,signal,socket,subprocess,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];STOP=False;CHILD=None

def stopped(signum,frame):
 global STOP
 STOP=True
 if CHILD is not None and CHILD.poll() is None:CHILD.terminate()

def count():
 p=HERE/'natural_model/results.jsonl'
 return len(p.read_text().splitlines()) if p.exists() else 0

def no_listener():
 with socket.socket() as s:s.settimeout(1);return s.connect_ex(('127.0.0.1',8080))!=0

def main():
 global CHILD
 p=argparse.ArgumentParser();p.add_argument('--first-job',type=int,default=2);p.add_argument('--max-jobs',type=int,default=12);a=p.parse_args()
 for sig in [signal.SIGINT,signal.SIGTERM,signal.SIGHUP]:signal.signal(sig,stopped)
 for job in range(a.first_job,a.first_job+a.max_jobs):
  if STOP:return 130
  # Acquire/release is delegated to flock, allowing the current shard to finish.
  if count()>=100:print(json.dumps({'event':'all100complete','count':count()}),flush=True);return 0
  log=HERE/f'natural_job_{job:02d}.log';server=HERE/f'natural_server_{job:02d}.log'
  if log.exists():raise RuntimeError('Refusing to overwrite existing job log')
  command=['flock','-F','-w','930','/tmp/autoformalization-empirical-heavy.lock',sys.executable,'-B',str(ROOT/'scripts/run_leanstral_ephemeral.py'),'--wall-seconds','1800','--startup-seconds','360','--memory-gib','90','--reserve-gib','12','--cpus','4','--context','4096','--chat-template-file',str(HERE/'leanstral_v15.jinja'),'--server-log',str(server),'--',sys.executable,'-B',str(HERE/'run_natural_a.py'),'run','--client-soft-stop','1320']
  before=count();began=time.monotonic();print(json.dumps({'event':'starting_bounded_shard','job':job,'completed_before':before,'log':str(log)}),flush=True)
  with log.open('x') as stream:
   CHILD=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=False)
   try:
    while CHILD.poll() is None:
     if STOP:CHILD.terminate()
     if time.monotonic()-began>2740:CHILD.terminate();raise TimeoutError('finite lockwait+job+cleanup bound')
     time.sleep(.5)
    code=CHILD.returncode
   finally:
    if CHILD.poll() is None:
     CHILD.terminate()
     try:CHILD.wait(timeout=8)
     except subprocess.TimeoutExpired:CHILD.kill();CHILD.wait()
  after=count();closed=no_listener();event={'event':'bounded_shard_finished','job':job,'exit_code':code,'completed_before':before,'completed_after':after,'wall_seconds_including_lock_wait':time.monotonic()-began,'port8080closed':closed}
  print(json.dumps(event),flush=True)
  with (HERE/'natural_job_lifecycle.jsonl').open('a') as f:f.write(json.dumps(event)+'\n')
  if STOP:return 130
  if code!=0 or not closed:return 1
  if after<=before and after<100:return 2
 return 0 if count()==100 else 3
if __name__=='__main__':raise SystemExit(main())
