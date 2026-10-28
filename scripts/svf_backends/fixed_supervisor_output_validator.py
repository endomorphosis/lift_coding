#!/usr/bin/env python3
"""Protected independent recomputation; imports no producer or implementation."""
from __future__ import annotations
import argparse,hashlib,json,os,re,stat,time,uuid
from pathlib import Path

def check(runtime_root,run_id,stage,challenge):
    if str(uuid.UUID(run_id))!=run_id or stage not in {'a','b'} or re.fullmatch('[0-9a-f]{32}',challenge) is None:raise ValueError('invalid fixed validation identity')
    root=Path(runtime_root)
    if not root.is_absolute() or root.resolve()!=root:raise ValueError('canonical runtime required')
    run=root/run_id
    if run.is_symlink() or run.resolve()!=run:raise ValueError('symlink run refused')
    def read(which):
        path=run/(which+'.json');info=path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or not 0<info.st_size<=4096:raise ValueError('unsafe actual output')
        return path.read_bytes()
    a={'schema':'swissknife.fixed-supervisor-output.v1','run_id':run_id,'stage':'a','challenge':challenge,'predecessor_sha256':None,'result':hashlib.sha256(('a:'+challenge).encode()).hexdigest()}
    if stage=='a':expected=a
    else:
        previous=read('a')
        if json.loads(previous)!=a:raise ValueError('invalid actual predecessor output')
        expected={'schema':a['schema'],'run_id':run_id,'stage':'b','challenge':challenge,'predecessor_sha256':hashlib.sha256(previous).hexdigest(),'result':hashlib.sha256(('b:'+a['result']+':'+challenge).encode()).hexdigest()}
    data=read(stage)
    canonical=(json.dumps(expected,sort_keys=True,separators=(',',':'))+'\n').encode()
    if data!=canonical:raise ValueError('actual output differs from independent expected bytes')
    return {'stage':stage,'output_sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'validated':True,'validator_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'work_complete':False,'completion_authority':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime-root',required=True);p.add_argument('--run-id',required=True);p.add_argument('--stage',choices=['a','b'],required=True);p.add_argument('--challenge',required=True);a=p.parse_args();time.sleep(.10);print(json.dumps(check(a.runtime_root,a.run_id,a.stage,a.challenge),sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
