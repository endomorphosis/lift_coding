"""Read-only originals; bounded native-admitted lossless archival feasibility."""
from __future__ import annotations
import hashlib, json, os, pathlib, resource, selectors, signal, subprocess, time
from datetime import datetime, timezone
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import get_global_resource_scheduler, ResourceLane

OUT = pathlib.Path(__file__).resolve().parent
BASE = pathlib.Path('/home/barberb/lift_coding/artifacts/terminal_bench_supervisor/full-integration-20260929')
REF = BASE/'terminal-native-runtime-full-v4/runtime.tar.gz'
TARGET = BASE/'terminal-native-runtime-full-v5/runtime.tar.gz'
PATCH = OUT/'v5-from-v4.zst'
MIB = 1024**2
LIMITS = {'cpu_slots':2, 'memory_mb':4096, 'child_process_slots':1,
          'child_address_space_bytes':4096*MIB, 'maximum_output_bytes':1536*MIB,
          'child_cpu_seconds':240, 'experiment_wall_seconds':300,
          'acquire_timeout_seconds':30}
report = {'schema':'task-runtime-lossless-archive-experiment@1', 'qualified':False,
          'originals_removed_or_replaced':False, 'limits':LIMITS,
          'started_at':datetime.now(timezone.utc).isoformat(), 'steps':[]}

def save():
    (OUT/'result.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(MIB), b''): h.update(block)
    return h.hexdigest()

def metadata(path):
    st=path.stat()
    if path.is_symlink() or not path.is_file(): raise ValueError('regular nonsymlink original required')
    return dict(path=str(path), bytes=st.st_size, allocated_bytes=st.st_blocks*512,
                device=st.st_dev, inode=st.st_ino, mtime_ns=st.st_mtime_ns,
                mode=oct(st.st_mode & 0o7777), uid=st.st_uid, gid=st.st_gid)

def active_census():
    roots=[str(REF.parent),str(TARGET.parent)]
    matches=[]; denied=[]; scanned=0; own_uid=os.getuid()
    for proc in pathlib.Path('/proc').iterdir():
        if not proc.name.isdigit() or int(proc.name)==os.getpid(): continue
        try: uid=proc.stat().st_uid
        except FileNotFoundError: continue
        scanned+=1
        for kind in ('cwd','fd','maps'):
            try:
                if kind=='cwd': values=[os.readlink(proc/kind)]
                elif kind=='fd':
                    values=[]
                    for fd in (proc/kind).iterdir():
                        try: values.append(os.readlink(fd))
                        except FileNotFoundError: pass
                else: values=(proc/kind).read_text(errors='replace').splitlines()
                for value in values:
                    if any(root in value for root in roots):
                        matches.append({'pid':int(proc.name),'uid':uid,'kind':kind,'reference':value})
            except FileNotFoundError: pass
            except PermissionError: denied.append({'pid':int(proc.name),'uid':uid,'kind':kind})
    return dict(scanned_processes=scanned, process_matches=matches, denied=denied,
                own_uid_denied=sum(v['uid']==own_uid for v in denied),
                note='Point-in-time census; excludes this experiment; requires repeat before any replacement.')

def bounded_run(command, lease, deadline, *, hash_stdout=False, name):
    limits=['prlimit', '--as='+str(LIMITS['child_address_space_bytes']),
            '--fsize='+str(LIMITS['maximum_output_bytes']), '--cpu=240', '--']
    started=time.monotonic(); before=resource.getrusage(resource.RUSAGE_CHILDREN)
    stdout_hash=hashlib.sha256(); output_bytes=0; peak_rss=0
    result=dict(name=name, command=command, limit_command=limits)
    with (OUT/(name+'.stderr')).open('xb') as err:
        p=subprocess.Popen(limits+command, stdout=subprocess.PIPE if hash_stdout else subprocess.DEVNULL,
                           stderr=err, start_new_session=True)
        sel=selectors.DefaultSelector()
        if hash_stdout: sel.register(p.stdout,selectors.EVENT_READ)
        try:
            eof=not hash_stdout
            while p.poll() is None or not eof:
                if time.monotonic()>=deadline: raise TimeoutError('experiment wall deadline')
                if lease.cancelled: raise RuntimeError('native lease cancelled')
                try:
                    values=pathlib.Path('/proc',str(p.pid),'status').read_text().splitlines()
                    peak_rss=max([peak_rss]+[int(v.split()[1])*1024 for v in values if v.startswith('VmRSS:')])
                except FileNotFoundError: pass
                if hash_stdout:
                    for key,_ in sel.select(.05):
                        block=os.read(key.fileobj.fileno(),MIB)
                        if not block: sel.unregister(key.fileobj); eof=True
                        else:
                            output_bytes+=len(block)
                            if output_bytes>TARGET.stat().st_size: raise RuntimeError('restored output exceeded exact original size')
                            stdout_hash.update(block)
                else: time.sleep(.05)
            result['returncode']=p.wait()
            if result['returncode']!=0: raise RuntimeError(name+' child failed '+str(result['returncode']))
        except BaseException:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGKILL)
            p.wait()
            raise
        finally:
            sel.close()
            if p.stdout: p.stdout.close()
            after=resource.getrusage(resource.RUSAGE_CHILDREN)
            result.update(seconds=time.monotonic()-started,
                          cpu_user_seconds=after.ru_utime-before.ru_utime,
                          cpu_system_seconds=after.ru_stime-before.ru_stime,
                          sampled_child_peak_rss_bytes=peak_rss,
                          reaped=p.poll() is not None,
                          stdout_bytes=output_bytes,
                          stdout_sha256=stdout_hash.hexdigest() if hash_stdout else None)
            report['steps'].append(result); save()
    return result

lease=None
try:
    report['reference']=metadata(REF); report['target']=metadata(TARGET)
    report['process_census_before']=active_census(); save()
    if report['process_census_before']['process_matches'] or report['process_census_before']['own_uid_denied']:
        raise RuntimeError('originals process inspection not clear')
    scheduler=get_global_resource_scheduler()
    acquired=time.monotonic()
    lease=scheduler.acquire(ResourceLane.PERSISTENCE,cpu_slots=2,memory_mb=4096,child_process_slots=1,
        timeout=30,request_id='runtime-lossless-archive-experiment-01')
    deadline=time.monotonic()+300
    report['native_admission']={'lease_id':lease.lease_id,'lane':lease.lane,
        'state_path':str(scheduler.state_path),'acquire_seconds':time.monotonic()-acquired,
        'policy_sha256':hashlib.sha256(json.dumps(scheduler.config.persisted_dict(),sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    report['zstd_version']=subprocess.check_output(['zstd','--version'],text=True).strip()
    for key,path in [('reference',REF),('target',TARGET)]:
        report[key]['sha256']=sha(path)
        manifest=json.loads((path.parent/'manifest.json').read_text())
        report[key]['manifest_sha256']=sha(path.parent/'manifest.json')
        report[key]['manifest_archive_sha256']=manifest['archive_sha256']
        if report[key]['sha256']!=manifest['archive_sha256']: raise RuntimeError('manifest/original hash mismatch')
    save()
    bounded_run(['zstd','--single-thread','--mmap-dict','-3','--patch-from='+str(REF),str(TARGET),'-o',str(PATCH)],lease,deadline,name='compression')
    report['patch']=metadata(PATCH); report['patch']['sha256']=sha(PATCH); save()
    restored=bounded_run(['zstd','--single-thread','--mmap-dict','-d','--patch-from='+str(REF),str(PATCH),'-c'],lease,deadline,hash_stdout=True,name='reconstruction')
    report['reconstruction_verified']=(restored['stdout_sha256']==report['target']['sha256'] and restored['stdout_bytes']==report['target']['bytes'])
    if not report['reconstruction_verified']: raise RuntimeError('restoration hash or length mismatch')
    for key,path in [('reference',REF),('target',TARGET)]:
        after=metadata(path)
        if any(after[k]!=report[key][k] for k in after): raise RuntimeError('original metadata changed during experiment')
    report['process_census_after']=active_census()
    report['possible_logical_saved_bytes']=report['target']['bytes']-report['patch']['bytes']
    report['possible_allocated_saved_bytes']=report['target']['allocated_bytes']-report['patch']['allocated_bytes']
    report['fraction_saved']=1-report['patch']['bytes']/report['target']['bytes']
    report['qualified']=True
except BaseException as error:
    report['error']={'type':type(error).__name__,'message':str(error)}
finally:
    if lease is not None:
        lease.release(); report['native_admission']['released']=lease.released
    report['completed_at']=datetime.now(timezone.utc).isoformat(); save()
    print(json.dumps({k:report[k] for k in ('qualified','error','possible_logical_saved_bytes','fraction_saved') if k in report},sort_keys=True),flush=True)
