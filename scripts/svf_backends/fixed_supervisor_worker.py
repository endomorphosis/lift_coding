#!/usr/bin/env python3
"""Protected offline fixture producer: fixed data transform, no user code."""
from __future__ import annotations
import argparse,hashlib,json,os,re,stat,time,uuid
from pathlib import Path
SCHEMA='swissknife.fixed-supervisor-output.v1'

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
def regular(path):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_size>4096:raise ValueError('unsafe fixture file')
    return path.read_bytes()
def directory(root,run_id):
    if str(uuid.UUID(run_id))!=run_id:raise ValueError('canonical UUID required')
    root=Path(root)
    if not root.is_absolute() or root.resolve()!=root:raise ValueError('canonical absolute runtime required')
    info=root.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o022:raise ValueError('private owner runtime required')
    path=root/run_id
    if path.is_symlink():raise ValueError('symlink run refused')
    path.mkdir(mode=0o700,exist_ok=True)
    if path.stat().st_uid!=os.getuid() or path.stat().st_mode&0o077:raise ValueError('private run required')
    return path

def produce(runtime_root,run_id,stage,challenge,mode='normal'):
    if stage not in {'a','b'} or mode not in {'normal','timeout','cancel'} or re.fullmatch('[0-9a-f]{32}',challenge) is None:raise ValueError('unsupported fixed fixture inputs')
    run=directory(runtime_root,run_id);target=run/(stage+'.json')
    if target.exists() or target.is_symlink():raise ValueError('immutable output collision')
    # Independent read-only kernel observers can witness the actual fixed child.
    time.sleep(.20 if mode=='normal' else 2)
    predecessor=None
    if stage=='b':
        previous=regular(run/'a.json');item=json.loads(previous)
        wanted={'schema':SCHEMA,'run_id':run_id,'stage':'a','challenge':challenge,'predecessor_sha256':None,'result':hashlib.sha256(('a:'+challenge).encode()).hexdigest()}
        if item!=wanted:raise ValueError('predecessor output is not the fixed original result')
        predecessor=hashlib.sha256(previous).hexdigest();material='b:'+item['result']+':'+challenge
    else:material='a:'+challenge
    value={'schema':SCHEMA,'run_id':run_id,'stage':stage,'challenge':challenge,'predecessor_sha256':predecessor,'result':hashlib.sha256(material.encode()).hexdigest()};data=canonical(value)
    fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as out:out.write(data);out.flush();os.fsync(out.fileno())
    folder=os.open(run,os.O_DIRECTORY);os.fsync(folder);os.close(folder)
    return {'output_path':str(target),'output_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'pid':os.getpid(),'parent_pid':os.getppid(),'start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],'producer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'work_complete':False,'completion_authority':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',required=True);p.add_argument('--run-id',required=True);p.add_argument('--stage',choices=['a','b'],required=True);p.add_argument('--challenge',required=True);p.add_argument('--mode',choices=['normal','timeout','cancel'],default='normal');a=p.parse_args()
    print(json.dumps(produce(a.runtime_root,a.run_id,a.stage,a.challenge,a.mode),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
