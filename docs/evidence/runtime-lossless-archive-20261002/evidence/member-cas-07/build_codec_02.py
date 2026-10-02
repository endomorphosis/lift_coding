from pathlib import Path
import hashlib,json,os,shutil,signal,subprocess,time
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler,ResourceLane
root=Path(__file__).resolve().parent;out=root/'store/codec';lease=None;child=None
report=dict(schema='native-static-zlib-codec-build@1',qualified=False,limits=dict(cpu_slots=1,memory_mb=512,child_process_slots=4,wall_seconds=60))
try:
    scheduler=get_global_resource_scheduler();started=time.monotonic()
    lease=scheduler.acquire(ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=512,child_process_slots=4,timeout=30,request_id='runtime-static-codec-build-02')
    report['native_admission']=dict(lease_id=lease.lease_id,acquire_seconds=time.monotonic()-started)
    command=['prlimit','--as=536870912','--fsize=16777216','--cpu=45','--','/usr/bin/cc','-O2','-static','-Wl,--build-id=none',str(out/'deflate1.c'),'/usr/lib/aarch64-linux-gnu/libz.a','-o',str(out/'deflate1')]
    report['command']=command;deadline=time.monotonic()+60
    with (root/'codec-build-02.log').open('xb') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        while child.poll() is None:
            if lease.cancelled or time.monotonic()>=deadline:raise TimeoutError('codec build cancelled/deadline')
            time.sleep(.05)
        report['returncode']=child.wait()
    assert child.returncode==0
    program_headers=subprocess.check_output(['readelf','-l',str(out/'deflate1')],text=True)
    assert 'INTERP' not in program_headers
    report['static_no_program_interpreter']=True
    report['version']=subprocess.check_output([str(out/'deflate1'),'--version'],text=True).strip()
    assert 'zlib-compile=1.3 zlib-runtime=1.3' in report['version']
    pins=[]
    for path in [Path('/usr/bin/cc').resolve(),Path('/usr/lib/aarch64-linux-gnu/libz.a'),Path('/usr/lib/aarch64-linux-gnu/libc.a'),out/'deflate1.c',out/'deflate1']:
        pins.append(dict(path=str(path),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    for name,source in [('zlib-copyright','/usr/share/doc/zlib1g/copyright'),('libc-copyright','/usr/share/doc/libc6/copyright')]:
        target=out/name;shutil.copyfile(source,target);pins.append(dict(path=str(target),bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    report['pins']=pins;report['qualified']=True;report['platform']='Linux ARM64; static libc/zlib, no dynamic loader/library dependency'
    (out/'codec-manifest.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
except BaseException as error:report['error']=dict(type=type(error).__name__,message=str(error))
finally:
    if child is not None and child.poll() is None:os.killpg(child.pid,signal.SIGKILL);child.wait()
    if lease is not None:lease.release();report['native_admission']['released']=lease.released
    (root/'codec-build-02-result.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(qualified=report['qualified'],error=report.get('error'))),flush=True)
