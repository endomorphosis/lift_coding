#!/usr/bin/env python3
"""Stream/hash one native checkpoint; retain exact head values, drop decoder arrays.

Native checkpoints are indented JSON. Extraction validates every component kept
with json.loads, checks source SHA256 against the retained training manifest,
and preserves embedding-key membership because feature selection reads it.
No checkpoint is ever decoded to one enormous Python object.
"""
import argparse, hashlib, json, mmap, os, re, resource, time
from pathlib import Path

def digest_file(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()

def extract(path, expected, output):
 start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(64<<30,64<<30))
 got=digest_file(path)
 if got!=expected:raise ValueError(f'Checkpoint hash mismatch {got}')
 with open(path,'rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
  matches=list(re.finditer(rb'^    "([^"\n]+)": ',data,re.M))
  if not matches:raise ValueError('Checkpoint must use retained native indented JSON format')
  prefix=data[:matches[0].start()].decode();metadata=json.loads(prefix.rsplit('"state": {',1)[0]+'"state": {}}')
  state={};stats={}
  for i,match in enumerate(matches):
   key=match[1].decode();end=matches[i+1].start() if i+1<len(matches) else data.rfind(b'\n  }')
   if end<=match.end():raise ValueError('Malformed component boundary')
   value=data[match.end():end].rstrip().removesuffix(b',')
   if key in {'decoded_embeddings','family_logits'}:
    state[key]={};stats[key]={'mode':'sample_memory_removed','raw_bytes':len(value)}
   elif key.endswith('_embedding_weights'):
    names=[json.loads(m[1]) for m in re.finditer(rb'^      ("(?:[^"\\]|\\.)+"): \[',value,re.M)]
    if value.strip()!=b'{}' and not names:raise ValueError(f'No array rows found for {key}')
    state[key]={name:[] for name in names};stats[key]={'mode':'membership_only','keys':len(names),'raw_bytes':len(value)}
   else:
    state[key]=json.loads(value);stats[key]={'mode':'exact_values','raw_bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()}
   del value
 metadata.pop('state',None)
 result={'schema':'autoformalization-source-only-head-checkpoint/v1','source_checkpoint':str(Path(path).resolve()),'source_sha256':got,'source_bytes':Path(path).stat().st_size,'source_metadata':metadata,'components':stats,'state':state,'scope':'Exact native prediction heads; embedding key membership preserved; decoder arrays and sample memory excluded. Never use this compact checkpoint for embedding reconstruction.'}
 Path(output).parent.mkdir(parents=True,exist_ok=True)
 with open(output,'x') as f:json.dump(result,f,sort_keys=True,separators=(',',':'))
 receipt={'source_sha256':got,'compact_sha256':digest_file(output),'compact_bytes':Path(output).stat().st_size,'wall_seconds':time.monotonic()-start,'cpu_seconds':time.process_time(),'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'components':stats}
 Path(str(output)+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({k:v for k,v in receipt.items() if k!='components'}),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args();extract(a.checkpoint,a.sha256,a.output)
