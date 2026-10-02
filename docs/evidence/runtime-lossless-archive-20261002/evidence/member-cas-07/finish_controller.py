from pathlib import Path
import hashlib,json,os,signal,subprocess,time
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler,ResourceLane
root=Path(__file__).resolve().parent;lease=None;child=None;started=time.monotonic()
pins={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ('archive_cas.py','seal_store.py','finish_store.py')}
report={'schema':'native-runtime-store-final-seal-envelope@1','qualified':False,'producer_sha256':pins,
    'limits':dict(cpu_slots=3,memory_mb=1024,child_process_slots=3,wall_seconds=600,acquire_seconds=30,
                  store_and_materialized_restore_bytes=5*1024**3),'original_archives_removed':False}
try:
    scheduler=get_global_resource_scheduler()
    lease=scheduler.acquire(ResourceLane.PERSISTENCE,cpu_slots=3,memory_mb=1024,child_process_slots=3,timeout=30,request_id='runtime-cas-final-seal-01')
    report['native_admission']=dict(lease_id=lease.lease_id,acquire_seconds=time.monotonic()-started,
        policy_sha256=hashlib.sha256(json.dumps(scheduler.config.persisted_dict(),sort_keys=True,separators=(',',':')).encode()).hexdigest())
    assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==value for name,value in pins.items())
    command=['prlimit','--as=805306368','--fsize=1610612736','--cpu=600','--','/usr/bin/python3.12',str(root/'finish_store.py')]
    report['command']=command;deadline=time.monotonic()+600
    with (root/'finish-worker.log').open('xb') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);report['worker_pid']=child.pid
        while child.poll() is None:
            if time.monotonic()>=deadline:raise TimeoutError('finish deadline')
            if lease.cancelled:raise RuntimeError('native finish cancelled')
            time.sleep(.1)
        report['returncode']=child.wait()
    assert child.returncode==0
    report['result']=str(root/'complete-qualification.json');value=json.loads((root/'complete-qualification.json').read_bytes())
    assert value['qualified'] and value['archive_count']==15
    assert all(hashlib.sha256((root/name).read_bytes()).hexdigest()==value for name,value in pins.items())
    report['qualified']=True
except BaseException as error:report['error']=dict(type=type(error).__name__,message=str(error))
finally:
    if child is not None and child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
    if lease is not None:lease.release();report['native_admission']['released']=lease.released
    report['reaped']=child is None or child.poll() is not None;report['seconds']=time.monotonic()-started
    (root/'finish-envelope.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:report.get(k) for k in ('qualified','seconds','error')}),flush=True)
