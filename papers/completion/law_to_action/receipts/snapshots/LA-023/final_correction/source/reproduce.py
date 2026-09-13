#!/usr/bin/env python3
"""Verify the anonymous package, then reproduce retained analysis without a new study."""
from __future__ import annotations
import argparse, functools, hashlib, json, os, resource, signal, stat, subprocess, sys, tempfile, time, zipfile
from pathlib import Path, PurePosixPath

PREFIX = 'law_to_action_final_supplement/'
MAX_ZIP = 100_000_000
MAX_EXPANDED = 150_000_000
MAX_FILES = 200

def require(value, message):
    if not value: raise RuntimeError(message)

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def check_tree(root):
    manifest=json.loads((root/'manifest.json').read_bytes())
    require(manifest['schema']=='law-anonymous-final-artifact/v1','Wrong manifest schema')
    files=manifest['files']
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    require(actual==set(files)|{'manifest.json'},'Bundle inventory differs')
    for name,record in files.items():
        p=root/name
        require(not p.is_symlink() and p.stat().st_size==record['bytes'] and sha(p)==record['sha256'],'Bundle bytes differ: '+name)
    require(manifest['scope']['scientific_rows']==900 and manifest['scope']['host_attempts']==902,'Wrong fixed denominators')
    require(manifest['scope']['new_scientific_executions']==0,'Analysis route must not claim a new study')
    return manifest

def extract_checked(archive, dest):
    require(archive.stat().st_size<=MAX_ZIP,'ZIP exceeds workshop limit')
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist(); names=[i.filename for i in infos]
        require(0<len(infos)<=MAX_FILES and len(set(names))==len(names),'Invalid ZIP inventory')
        require(sum(i.file_size for i in infos)<=MAX_EXPANDED,'ZIP expanded size exceeds bounded package limit')
        for i in infos:
            p=PurePosixPath(i.filename); mode=i.external_attr>>16
            require(p.parts and p.parts[0]==PREFIX[:-1] and not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename,'Unsafe ZIP path')
            require(not i.is_dir() and not stat.S_ISLNK(mode) and not i.flag_bits&1,'Nonregular/encrypted ZIP member')
            out=dest/str(p);out.parent.mkdir(parents=True,exist_ok=True)
            with out.open('xb') as f:f.write(z.read(i))
            out.chmod(0o755 if str(p).endswith('.sh') else 0o644)
    return dest/PREFIX[:-1]

def child_limits(pin_cpu):
    resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    if pin_cpu and hasattr(os,'sched_getaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})

def process_record(pid):
    try:
        fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
        return {'pid':pid,'parent_pid':int(fields[1]),'birth_ticks':int(fields[19]),'state':fields[0]}
    except (OSError,ValueError,IndexError):return None

def owned_descendants(pid):
    # This wrapper launches one command at a time. Capture only children joined
    # through /proc parent identities before stopping that exact process group.
    records=[];todo=[pid]
    while todo and len(records)<128:
        parent=todo.pop()
        try:children=(Path('/proc')/str(parent)/'task'/str(parent)/'children').read_text().split()
        except OSError:continue
        for child in children:
            rec=process_record(int(child))
            if rec and rec['parent_pid']==parent:
                records.append(rec);todo.append(rec['pid'])
    return records, bool(todo)

def same_live(rec):
    now=process_record(rec['pid'])
    return bool(now and now['birth_ticks']==rec['birth_ticks'] and now['state'] not in ('Z','X'))

def run(argv,cwd,output,label,*,pin_cpu=False,timeout_seconds=65):
    started=time.monotonic()
    env={'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','SOURCE_DATE_EPOCH':'0','HOME':str(output/'home')}
    (output/'home').mkdir(exist_ok=True)
    metadata={'scope':'offline retained analysis and local harness controls; no scientific execution','timed_out':False,'cpu_limit_scope':'per process; not a measured whole-group CPU counter'}
    with (output/(label+'.stdout.txt')).open('xb') as stdout,(output/(label+'.stderr.txt')).open('xb') as stderr:
        process=subprocess.Popen(argv,cwd=cwd,env=env,stdout=stdout,stderr=stderr,start_new_session=True,preexec_fn=functools.partial(child_limits,pin_cpu))
        try:
            process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            metadata['timed_out']=True
            descendants=[]
            try:descendants,truncated=owned_descendants(process.pid);metadata['descendant_snapshot_truncated']=truncated
            except Exception as error:metadata['descendant_snapshot_error_class']=type(error).__name__
            finally:
                try:os.killpg(process.pid,signal.SIGKILL);metadata['process_group_kill_requested']=True
                except ProcessLookupError:metadata['process_group_already_absent']=True
            # The retained harness starts fixture workers in their own sessions.
            # Kill only captured descendants with unchanged Linux birth identity.
            for rec in reversed(descendants):
                if same_live(rec):
                    try:os.kill(rec['pid'],signal.SIGKILL)
                    except ProcessLookupError:pass
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:metadata['direct_child_cleanup_uncertain']=True
            until=time.monotonic()+2
            while any(same_live(rec)for rec in descendants) and time.monotonic()<until:time.sleep(.02)
            metadata['known_descendants']=descendants
            metadata['known_descendants_terminated']=not any(same_live(rec)for rec in descendants)
            metadata['all_possible_descendants_termination_proven']=False
            # A timed-out analysis is always a failed retained attempt; the
            # bounded snapshot cannot certify an unobserved process-creation race.
    metadata.update(exit_code=process.returncode,wall_seconds=time.monotonic()-started)
    (output/(label+'.execution.json')).write_text(json.dumps(metadata,indent=2,sort_keys=True)+'\n')
    require(not metadata['timed_out'] and process.returncode==0,label+' failed; retained logs identify the failure')
    return metadata

def verify_and_run(root, output):
    manifest=check_tree(root)
    # The exact initially rejected LA-023 ZIP is kept intact, including its verifier.
    legacy=root/'historical_compact/anonymous_supplement.zip'
    with tempfile.TemporaryDirectory(prefix='law-compact-') as temp:
        with zipfile.ZipFile(legacy) as z:
            names=z.namelist()
            require(len(names)==len(set(names)) and len(names)<100 and sum(i.file_size for i in z.infolist())<10_000_000,'Unexpected legacy inventory')
            for name in names:
                p=PurePosixPath(name)
                require(not p.is_absolute() and '..' not in p.parts and p.parts[0]=='law_to_action_anonymous_supplement','Unsafe legacy member')
            z.extractall(temp)
        compact=Path(temp)/'law_to_action_anonymous_supplement'
        old=run(['/bin/sh',str(compact/'reproduce.sh')],compact,output,'compact_analysis')
    portable=run([sys.executable,'-I','-B',str(root/'recovery_source_v1/reproduce.py'),'--output',str(output/'recovery_analysis')],root,output,'recovery_analysis',pin_cpu=True)
    proof=json.loads((output/'recovery_analysis/verification.json').read_bytes())
    require(proof['success'] and proof['scientific_rows']==900 and proof['host_attempts']==902 and proof['actual_group_cpu_seconds']==1608.817478,'Portable reduction differs')
    report={'schema':'law-final-offline-reproduction/v1','success':True,'scope':manifest['scope'],'compact_analysis':old,'recovery_analysis':portable,'all_package_files_verified':True,'all_9933_original_reducer_inputs_verified':proof['all_9933_original_reducer_inputs_included'],'all_45_paired_family_bootstrap_contrasts_recomputed':proof['all_45_paired_family_bootstrap_contrasts_recomputed'],'new_scientific_executions':0}
    (output/'verification.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,sort_keys=True))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--zip',type=Path);args=p.parse_args()
    output=args.output.resolve();require(not output.exists(),'Choose a fresh output directory');output.mkdir(parents=True,mode=0o700)
    here=Path(__file__).resolve().parent
    archive=args.zip
    if archive is None and (here/'anonymous_supplement.zip').is_file():archive=here/'anonymous_supplement.zip'
    if archive:
        with tempfile.TemporaryDirectory(prefix='law-final-') as temp:verify_and_run(extract_checked(archive.resolve(),Path(temp)),output)
    else:verify_and_run(here,output)
if __name__=='__main__':main()
