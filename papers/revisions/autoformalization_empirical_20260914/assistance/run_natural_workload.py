#!/usr/bin/env python3
"""Finite client workload for one fresh warm server; never loads model itself.

Use as the single client of run_leanstral_ephemeral.py --wall-seconds10000.
All software batches reuse that same runner-owned endpoint until100are attempted.
"""
from pathlib import Path
import json,os,subprocess,sys,time
HERE=Path(__file__).resolve().parent

def count():
 p=HERE/'natural_model/results.jsonl';return len(p.read_text().splitlines()) if p.exists() else 0

def main():
 if 'LEANSTRAL_BASE_URL' not in os.environ:raise RuntimeError('Use as client of the bounded temporary runner')
 started=time.monotonic()
 for batch in range(8):
  before=count()
  if before==100:return 0
  if before>100:raise RuntimeError('More than100records violates frozen manifest')
  if time.monotonic()-started>9600:return 124
  print(json.dumps({'event':'same_server_client_batch','batch':batch,'already_attempted':before}),flush=True)
  result=subprocess.run([sys.executable,'-B',str(HERE/'run_natural_a.py'),'run','--client-soft-stop','1320'])
  if result.returncode:return result.returncode
  if count()<=before:raise RuntimeError('No progress; preserving server failure and receipts')
 return 0 if count()==100 else 1
if __name__=='__main__':raise SystemExit(main())
