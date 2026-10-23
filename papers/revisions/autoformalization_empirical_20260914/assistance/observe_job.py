#!/usr/bin/env python3
"""Read-only, finite cgroup accounting observer; never starts a model."""
from pathlib import Path
import argparse,json,time,datetime
p=argparse.ArgumentParser();p.add_argument('pid',type=int);p.add_argument('output',type=Path);a=p.parse_args()
proc=Path('/proc')/str(a.pid);start_ticks=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]
group=next(x.split(':',2)[2] for x in proc.joinpath('cgroup').read_text().splitlines() if x.startswith('0:'))
cgroup=Path('/sys/fs/cgroup'+group);began=time.monotonic();samples=0;last=None
with a.output.open('x') as f:
 while time.monotonic()-began<920:
  try:
   if proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]!=start_ticks:break
   row={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_observer_seconds':time.monotonic()-began,'server_pid':a.pid,'cgroup':group}
   for key in ['memory.current','memory.peak','memory.swap.current','pids.current']:
    row[key]=int((cgroup/key).read_text())
   for key in ['cpu.stat','memory.events']:
    row[key]={k:int(v) for k,v in (line.split() for line in (cgroup/key).read_text().splitlines())}
   f.write(json.dumps(row)+'\n');f.flush();last=row;samples+=1
  except FileNotFoundError:break
  time.sleep(2)
summary={'observed_samples':samples,'observation_interval_seconds':2,'last_observation':last,'server_pid':a.pid,'server_still_present':proc.exists(),'note':'Cgroup accounting sampled every2seconds; last CPU cost can miss teardown/final2seconds. memory.peak is kernel-maintained peak as of last sample.'}
a.output.with_suffix('.summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
