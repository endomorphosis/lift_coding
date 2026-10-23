#!/usr/bin/env python3
"""Post-prediction source-vector scoring; never called from the predictor."""
import argparse,hashlib,json,math,statistics
from pathlib import Path
import numpy as np

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mean(xs):return sum(xs)/len(xs) if xs else None

def score(predictions,embeddings):
 # Bind the entire prediction file before reading reconstruction inputs.
 prediction_sha=sha(predictions)
 pred=[json.loads(l) for l in open(predictions)]
 ref={r['record_id']:r for r in map(json.loads,open(embeddings))}
 if len(pred)!=len({r['record_id'] for r in pred}):raise ValueError('Duplicate predictions')
 rows=[]
 for p in pred:
  r=ref[p['record_id']]
  if p['text_sha256']!=r['text_sha256']:raise ValueError('Source binding mismatch')
  a=np.asarray(p['decoded_source_embedding'],dtype=np.float64);b=np.asarray(r['embedding_vector'],dtype=np.float64)
  if a.shape!=(384,) or b.shape!=(384,) or not np.isfinite(a).all():raise ValueError('Invalid vector')
  cosine=float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))) if np.linalg.norm(a)*np.linalg.norm(b) else 0.0
  rows.append({'record_id':p['record_id'],'family':p['family'],'arm_id':p['arm_id'],'seed':p['seed'],'cosine':cosine,'mse':float(np.mean((a-b)**2)),'squared_l2':float(np.sum((a-b)**2)),'prediction_wall_seconds':p['wall_seconds']})
 summary={'count':len(rows),'mean_cosine':mean([r['cosine'] for r in rows]),'mean_mse':mean([r['mse'] for r in rows]),'cosine_min':min(r['cosine'] for r in rows),'cosine_max':max(r['cosine'] for r in rows),'family':{family:{'count':sum(r['family']==family for r in rows),'mean_cosine':mean([r['cosine'] for r in rows if r['family']==family]),'mean_mse':mean([r['mse'] for r in rows if r['family']==family])} for family in sorted({r['family'] for r in rows})},'predictions_sha256':prediction_sha,'source_embeddings_sha256':sha(embeddings),'scope':'Reconstruction of source-derived MiniLM vector, not independent legal/semantic fidelity; no protected source truth established.'}
 return rows,summary

def main():
 p=argparse.ArgumentParser();p.add_argument('--predictions',required=True,type=Path);p.add_argument('--embeddings',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 rows,summary=score(a.predictions,a.embeddings);a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps({'schema':'autoformalization-source-embedding-scores/v1','summary':summary,'rows':rows},indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
