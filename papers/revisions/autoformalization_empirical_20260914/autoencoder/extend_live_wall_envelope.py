#!/usr/bin/env python3
"""Replace only a live GNU timeout watchdog, retaining its bounded worker.

Prepare a total-age deadline and cleanup handler before killing the old timer.
This changes no scientific code, parameters, input, output, or worker process.
The postprocessor must follow worker identity/receipts, not the old timeout PID.
"""
import argparse,hashlib,json,os,signal,time
from pathlib import Path

def proc(pid):
 p=Path(f'/proc/{pid}');raw=(p/'stat').read_text();parts=raw[raw.rfind(')')+2:].split();return {'pid':pid,'state':parts[0],'ppid':int(parts[1]),'pgrp':int(parts[2]),'start_ticks':int(parts[19]),'cmdline':(p/'cmdline').read_bytes().decode().replace('\0',' ')}
def alive(identity):
 try:p=proc(identity['pid'])
 except (FileNotFoundError,ProcessLookupError):return False
 return p['start_ticks']==identity['start_ticks'] and p['state']!='Z'
def main():
 p=argparse.ArgumentParser();p.add_argument('--timeout-pid',required=True,type=int);p.add_argument('--worker-pid',required=True,type=int);p.add_argument('--expected-token',required=True);p.add_argument('--total-age-seconds',required=True,type=float);p.add_argument('--record',required=True,type=Path);a=p.parse_args();timer=proc(a.timeout_pid);worker=proc(a.worker_pid)
 if 'timeout' not in timer['cmdline'] or a.expected_token not in worker['cmdline'] or worker['ppid']!=timer['pid'] or worker['pgrp']!=timer['pid']:raise ValueError('Worker/timer custody mismatch')
 hz=os.sysconf(os.sysconf_names['SC_CLK_TCK']);start=timer['start_ticks']/hz;now=time.clock_gettime(time.CLOCK_BOOTTIME);deadline=start+a.total_age_seconds
 if deadline<=now or a.total_age_seconds>10000:raise ValueError('Deadline must be live and at most authorized10000seconds total age')
 def cleanup(_signum,_frame):
  if alive(worker):os.killpg(worker['pgrp'],signal.SIGTERM)
  raise SystemExit(143)
 signal.signal(signal.SIGTERM,cleanup);signal.signal(signal.SIGINT,cleanup)
 record={'schema':'autoformalization-live-wall-envelope-extension/v1','watchdog_pid':os.getpid(),'watchdog_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'old_timeout':timer,'unchanged_worker':worker,'total_age_seconds':a.total_age_seconds,'age_at_install_seconds':now-start,'deadline_clock_boottime':deadline,'grace_seconds':10,'scientific_process_restarted':False,'scientific_state_changed':False,'status':'replacement_guard_installed_before_old_timer_removal'}
 with a.record.open('x') as f:json.dump(record,f,indent=2);f.write('\n')
 # SIGKILL affects only the old timer; SIGTERM would be forwarded to the worker.
 if not alive(worker) or proc(timer['pid'])['start_ticks']!=timer['start_ticks']:raise ValueError('Processes changed before watchdog handoff')
 os.kill(timer['pid'],signal.SIGKILL)
 try:
  record['status']='active';Path(str(a.record)+'.active.json').write_text(json.dumps(record,indent=2)+'\n')
  while alive(worker):
   remaining=deadline-time.clock_gettime(time.CLOCK_BOOTTIME)
   if remaining<=0:
    os.killpg(worker['pgrp'],signal.SIGTERM);grace=time.monotonic()+10
    while alive(worker) and time.monotonic()<grace:time.sleep(.2)
    if alive(worker):os.killpg(worker['pgrp'],signal.SIGKILL)
    record['status']='new_total_age_deadline_enforced';break
   time.sleep(min(2,remaining))
  else:record['status']='worker_exited_before_new_deadline'
  record['finished_clock_boottime']=time.clock_gettime(time.CLOCK_BOOTTIME);Path(str(a.record)+'.finished.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'status':record['status'],'worker_pid':worker['pid']}))
 finally:
  # If this replacement guard exits unexpectedly after removing the old timer,
  # it cannot leave the active worker without an enforced resource deadline.
  if alive(worker):
   try:os.killpg(worker['pgrp'],signal.SIGTERM)
   except ProcessLookupError:pass
   grace=time.monotonic()+10
   while alive(worker) and time.monotonic()<grace:time.sleep(.2)
   if alive(worker):
    try:os.killpg(worker['pgrp'],signal.SIGKILL)
    except ProcessLookupError:pass
if __name__=='__main__':main()
