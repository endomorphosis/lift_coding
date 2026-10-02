from pathlib import Path
import hashlib,json,os,signal,subprocess,time
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler,ResourceLane

out=Path(__file__).resolve().parent
source='/home/barberb/lift_coding/artifacts/terminal_bench_supervisor/full-integration-20260929/terminal-native-runtime-full-v5/runtime.tar.gz'
command=['prlimit','--as=536870912','--fsize=1048576','--cpu=300','--','/usr/bin/python3.12',str(out/'worker.py'),source,str(out/'roundtrip.json')]
report={'schema':'native-runtime-gzip-roundtrip-envelope@1','command':command,'qualified':False,'limits':dict(cpu_slots=1,memory_mb=512,child_process_slots=1,wall_seconds=300,acquire_seconds=30)}
lease=None;p=None;started=time.monotonic()
try:
    scheduler=get_global_resource_scheduler()
    lease=scheduler.acquire(ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=512,child_process_slots=1,timeout=30,request_id='runtime-gzip-roundtrip-06')
    report['native_admission']={'lease_id':lease.lease_id,'lane':lease.lane,'acquire_seconds':time.monotonic()-started,
        'policy_sha256':hashlib.sha256(json.dumps(scheduler.config.persisted_dict(),sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    deadline=time.monotonic()+300
    with (out/'worker.log').open('xb') as log:
        p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        while p.poll() is None:
            if time.monotonic()>=deadline:raise TimeoutError('wall deadline')
            if lease.cancelled:raise RuntimeError('native lease cancelled')
            time.sleep(.1)
        report['worker_returncode']=p.wait()
    if p.returncode!=0:raise RuntimeError('gzip roundtrip worker failed')
    child=json.loads((out/'roundtrip.json').read_text());assert child['exact']
    report['qualified']=True
except BaseException as error:report['error']={'type':type(error).__name__,'message':str(error)}
finally:
    if p is not None and p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait()
    if lease is not None:lease.release();report['native_admission']['released']=lease.released
    report['reaped']=p is None or p.poll() is not None
    report['seconds']=time.monotonic()-started
    (out/'result.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'qualified':report['qualified'],'error':report.get('error'),'seconds':report['seconds']}),flush=True)
