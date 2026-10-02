from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,time
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler,ResourceLane

parser=argparse.ArgumentParser();parser.add_argument('slugs',nargs='+');args=parser.parse_args()
root=Path(__file__).resolve().parent
inventory=json.loads((root.parent/'manifest-overlap.json').read_text())
by_name={Path(r['path']).name:r for r in inventory['bundles']}
for slug in args.slugs:
    row=by_name[slug];source=Path(row['path']);out=root/'runs'/slug;out.mkdir(parents=True,exist_ok=False)
    report={'schema':'native-runtime-member-cas-envelope@1','qualified':False,'source':str(source),
        'source_manifest_sha256':row['manifest_sha256'],'source_archive_sha256':row['archive_sha256_recorded'],
        'limits':dict(cpu_slots=1,memory_mb=512,child_process_slots=1,wall_seconds=300,acquire_seconds=30,
                      staging_allocated_bytes=5*1024**3,staging_apparent_bytes=4*1024**3,maximum_tar_bytes=4*1024**3),
        'implementation_sha256':hashlib.sha256((root/'archive_cas.py').read_bytes()).hexdigest()}
    lease=None;child=None;started=time.monotonic()
    try:
        assert hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest()==row['manifest_sha256']
        scheduler=get_global_resource_scheduler()
        lease=scheduler.acquire(ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=512,child_process_slots=1,timeout=30,
            request_id='runtime-member-cas-07:'+slug)
        report['native_admission']={'lease_id':lease.lease_id,'lane':lease.lane,'acquire_seconds':time.monotonic()-started,
            'policy_sha256':hashlib.sha256(json.dumps(scheduler.config.persisted_dict(),sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        command=['prlimit','--as=536870912','--fsize=536870912','--cpu=300','--','/usr/bin/python3.12',str(root/'archive_cas.py'),
            '--archive',str(source/'runtime.tar.gz'),'--manifest',str(source/'manifest.json'),
            '--store',str(root/'store'),'--slug',slug,'--result',str(out/'worker-result.json')]
        report['command']=command;deadline=time.monotonic()+300
        with (out/'worker.log').open('xb') as log:
            child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            while child.poll() is None:
                if time.monotonic()>=deadline:raise TimeoutError('wall deadline')
                if lease.cancelled:raise RuntimeError('native resource cancellation')
                time.sleep(.1)
            report['returncode']=child.wait()
        if child.returncode!=0:raise RuntimeError('member CAS worker failed')
        result=json.loads((out/'worker-result.json').read_text())
        assert result['qualified'] and result['reconstruction']['exact']
        assert result['reconstruction']['archive_sha256']==row['archive_sha256_recorded']
        report['qualified']=True
    except BaseException as error:report['error']={'type':type(error).__name__,'message':str(error)}
    finally:
        if child is not None and child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
        if lease is not None:lease.release();report['native_admission']['released']=lease.released
        report['reaped']=child is None or child.poll() is not None;report['seconds']=time.monotonic()-started
        (out/'envelope.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'slug':slug,'qualified':report['qualified'],'seconds':report['seconds'],'error':report.get('error')}),flush=True)
    if not report['qualified']:break
