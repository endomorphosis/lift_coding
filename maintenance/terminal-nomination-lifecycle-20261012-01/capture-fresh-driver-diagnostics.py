"""Read one named fresh driver report, exporting bounded existing diagnostics.

This independent read observation does not run the driver, extend its budget,
read owner databases/keys, or invoke target code. It records polling overhead.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import time

M=Path(__file__).resolve().parent
output=M/'actual-harbor-02-additional-diagnostics.json'
assert not output.exists()
boundary=json.loads((M/'actual-harbor-lifecycle-02/worker-boundary/installation/installation.json').read_bytes())['boundary']
container=boundary['container_id']
started=time.monotonic();attempts=0
report='/opt/ipfs-supervisor/state/retained-lifecycle-source-nomination-resume-result.json'
code=r'''import hashlib,json,os,pathlib,stat
p=pathlib.Path('/opt/ipfs-supervisor/state/retained-lifecycle-source-nomination-resume-result.json')
assert os.geteuid()==1000
fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
try:
 s=os.fstat(fd);assert stat.S_ISREG(s.st_mode) and s.st_uid==1000 and s.st_nlink==1 and s.st_size<=2000000
 raw=os.read(fd,2000001);assert len(raw)==s.st_size
 witness=lambda v:(v.st_dev,v.st_ino,v.st_size,v.st_mtime_ns,v.st_ctime_ns)
 assert witness(s)==witness(os.fstat(fd))==witness(p.lstat())
finally:os.close(fd)
v=json.loads(raw);assert v['schema']=='terminal-admitted-supervisor-run@1' and v['source_nomination_phase']=='resume'
keys=('phases','native_diagnostics','task_state','implementation_route','unavailable_settlement',
 'coding_dispatch_possible','provider_route_observed','context_input_audit','model_input_observation_audit')
print(json.dumps({'report_sha256':hashlib.sha256(raw).hexdigest(),'report_bytes':len(raw),
 'diagnostics':{k:v.get(k) for k in keys}},sort_keys=True,allow_nan=False))'''
result={'schema':'additional-fresh-named-phase-diagnostics@1','captured':False,
 'container_id':container,'same_phase_report_only':True,'driver_budget_extended':False,
 'target_code_imported_or_executed_by_this_probe':False,'owner_database_key_or_rollout_read':False}
try:
 while time.monotonic()-started<80:
  attempts+=1
  probe=subprocess.run(['docker','exec','--user','supervisor',container,'/bin/sh','-c','test -f '+report],capture_output=True,timeout=3)
  if probe.returncode==0:
   exported=subprocess.run(['docker','exec','--user','supervisor',container,'/opt/ipfs-supervisor/venv/bin/python','-I','-c',code],capture_output=True,timeout=5)
   assert len(exported.stdout)<=262144
   if exported.returncode==0:
    result.update(captured=True,**json.loads(exported.stdout))
   else:result['error_type']='ReportExportFailed'
   break
  if b'No such container' in probe.stderr:break
  time.sleep(1)
except Exception as error:result['error_type']=type(error).__name__
finally:
 result.update(poll_attempts=attempts,seconds=time.monotonic()-started)
 output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'captured':result['captured'],'attempts':attempts,'seconds':result['seconds']}))
