#!/usr/bin/env python3
"""Execute a frozen native arm with bounded workers and durable per-unit rows."""
from pathlib import Path
import argparse, concurrent.futures, hashlib, json, multiprocessing, os, resource, sys, time
HERE=Path(__file__).resolve().parent
API=None
def initialize(arm):
 global API
 resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
 os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
 if arm in ['C','T5']:
  from native_c import setup,evaluate
  native=setup(arm=='T5');API=lambda row:evaluate(row,native)
 else:
  sys.path.insert(0,str(HERE.parent/'guidance'))
  import native_b
  API=native_b.run_record
def call(row):return API(row)
def main():
 p=argparse.ArgumentParser();p.add_argument('--arm',choices=['C','T5','B'],required=True)
 p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--workers',type=int,default=4);a=p.parse_args()
 rows=[json.loads(l) for l in a.input.read_text().splitlines()]
 start=time.monotonic();a.output.parent.mkdir(exist_ok=True,parents=True)
 with a.output.open('x') as f, concurrent.futures.ProcessPoolExecutor(max_workers=a.workers,
  mp_context=multiprocessing.get_context('spawn'),initializer=initialize,initargs=(a.arm,)) as pool:
  for i,r in enumerate(pool.map(call,rows,chunksize=1)):
   f.write(json.dumps(r,ensure_ascii=False)+'\n');f.flush()
   if i%50==0:print(json.dumps({'arm':a.arm,'done':i+1,'total':len(rows),'elapsed':time.monotonic()-start}),flush=True)
 print(json.dumps({'arm':a.arm,'done':len(rows),'elapsed':time.monotonic()-start}),flush=True)
if __name__=='__main__':main()
