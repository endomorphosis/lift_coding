#!/usr/bin/env python3
"""Losslessly materialize decoder rows as float64 arrays, bounded one state at a time."""
import argparse,hashlib,json,mmap,os,re,resource,time
from pathlib import Path
import numpy as np
from extract_heads import digest_file

def main():
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True,type=Path);p.add_argument('--sha256',required=True);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 resource.setrlimit(resource.RLIMIT_AS,(64<<30,64<<30));os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[-2:]);start=time.monotonic()
 if a.output.exists():raise ValueError('Output exists')
 if digest_file(a.checkpoint)!=a.sha256:raise ValueError('Checkpoint hash changed')
 a.output.mkdir(parents=True);components={}
 with a.checkpoint.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
  fields=list(re.finditer(rb'^    "([^"\n]+)": ',data,re.M))
  for i,m in enumerate(fields):
   k=m[1].decode()
   if not k.endswith('_embedding_weights'):continue
   end=fields[i+1].start() if i+1<len(fields) else data.rfind(b'\n  }')
   # Boundaries are C regex scans over read-only mmap: no gigantic JSON tree.
   rows=list(re.finditer(rb'^      ("(?:[^"\\]|\\.)+"): \[',data[m.end():end],re.M))
   if not rows:continue
   keys=[json.loads(r[1]) for r in rows];array_path=a.output/(k+'.npy');arr=np.lib.format.open_memmap(array_path,mode='w+',dtype=np.float64,shape=(len(rows),384))
   exact_checks=[]
   for n,r in enumerate(rows):
    left=m.end()+r.end();right=m.end()+rows[n+1].start() if n+1<len(rows) else end
    raw=data[left:right];raw=raw[:raw.index(b']')]
    values=np.fromstring(raw.replace(b',',b' '),sep=' ',dtype=np.float64)
    if values.shape!=(384,) or not np.isfinite(values).all():raise ValueError((k,n,values.shape))
    arr[n]=values
    if n in {0,len(rows)//2,len(rows)-1}:
     direct=json.loads(b'['+raw+b']')
     if direct!=values.tolist():raise ValueError('Float64 conversion differs from native JSON')
     exact_checks.append(n)
   arr.flush();del arr
   keys_path=a.output/(k+'.keys.json');keys_path.write_text(json.dumps(keys,separators=(',',':')))
   components[k]={'rows':len(rows),'dimensions':384,'dtype':'float64','array_file':array_path.name,'array_sha256':digest_file(array_path),'keys_file':keys_path.name,'keys_sha256':digest_file(keys_path),'json_float_equivalence_checked_rows':exact_checks}
   print(json.dumps({'component':k,'rows':len(rows),'wall_seconds':time.monotonic()-start}),flush=True)
 receipt={'schema':'autoformalization-exact-vector-checkpoint/v1','source_checkpoint_sha256':a.sha256,'components':components,'source_encoding':'native JSON floats','representation':'IEEE754float64, exact Python json float parity on first/middle/last rows of each component','source_memory_included':False,'wall_seconds':time.monotonic()-start,'cpu_seconds':time.process_time(),'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
 (a.output/'manifest.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='components'}),flush=True)
if __name__=='__main__':main()
