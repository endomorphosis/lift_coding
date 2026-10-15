#!/usr/bin/env python3
"""Add absent scorer metadata; preserve every frozen constant prediction value."""
import argparse,hashlib,json,time
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--raw',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();start=time.monotonic();raw_receipt=json.load(open(Path(str(a.raw)+'.receipt.json')))
 if raw_receipt['predictions_sha256']!=sha(a.raw) or raw_receipt['count']!=1913:raise ValueError('Raw prediction custody mismatch')
 count=0
 with a.output.open('x') as out:
  for line in a.raw.open():
   row=json.loads(line)
   if row['arm_id']!='training_mean_supplement' or 'seed' in row or 'wall_seconds' in row:raise ValueError('Unexpected metadata contract')
   original=dict(row);row.update({'seed':None,'wall_seconds':None})
   if {k:v for k,v in row.items() if k not in {'seed','wall_seconds'}}!=original:raise ValueError('Prediction content changed')
   out.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n');count+=1
 if count!=1913:raise ValueError('Incomplete predictions')
 receipt=dict(raw_receipt);receipt.update({'predictions_sha256':sha(a.output),'raw_predictions_sha256':raw_receipt['predictions_sha256'],'raw_producer_sha256':raw_receipt['consumer_sha256'],'consumer_sha256':sha(__file__),'adapter_wall_seconds':time.monotonic()-start,'adapter_scope':'Add only seed=None and wall_seconds=None required by frozen scorer; all original fields and384dimensional vectors unchanged','new_inference_calls':0,'per_row_original_fields_equal':True});Path(str(a.output)+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
