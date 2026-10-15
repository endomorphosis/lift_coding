#!/usr/bin/env python3
from pathlib import Path
import json,os,time,datetime
HERE=Path(__file__).resolve().parent;PID=2849431;HZ=os.sysconf('SC_CLK_TCK');PROC=Path(f'/proc/{PID}/stat');start=PROC.read_text().rsplit(')',1)[1].split()[19];deadline=783092.787230+10000
with (HERE/'warm_cpu_observations.jsonl').open('x') as out:
 while time.monotonic()<deadline:
  try:
   fields=PROC.read_text().rsplit(')',1)[1].split()
   if fields[19]!=start or fields[0]=='Z':break
   rows=(HERE/'natural_model/results.jsonl').read_text().splitlines()
   row={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'monotonic':time.monotonic(),'completed':len(rows),'server_cpu_seconds':(int(fields[11])+int(fields[12]))/HZ,'server_rss_bytes':int(fields[21])*os.sysconf('SC_PAGE_SIZE'),'server_pid':PID,'server_start_ticks':start}
   out.write(json.dumps(row)+'\n');out.flush()
  except FileNotFoundError:break
  time.sleep(2)
