#!/usr/bin/env python3
"""Frozen source-only native AE consumer. Predictions precede separate scoring.

This module never imports compiler/reference targets or learns an output vocabulary
from the current example. Native target caches remain empty. Reconstruction uses
the direct learned projection and bypasses target-based safe-projection selection.
"""
from __future__ import annotations
import argparse,hashlib,json,math,os,resource,sys,time
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
for k,v in {'IPFS_DATASETS_PY_MINIMAL_IMPORTS':'1','IPFS_DATASETS_AUTO_INSTALL':'false','IPFS_KIT_AUTO_INSTALL_DEPS':'0','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','MKL_NUM_THREADS':'2'}.items():os.environ[k]=v
sys.path.insert(0,str(REPO/'external/ipfs_datasets'))
from ipfs_datasets_py.optimizers.logic_theorem_optimizer import modal_autoencoder as native
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.legal_samples import build_us_code_sample
# Fixed BEFORE final access from all retained TRAINING checkpoint view-embedding
# keys. This two-label alphabet never varies with a scored example's targets.
VIEW_VOCAB=('deontic.ir','knowledge_graphs.neo4j_compat')
MODAL_VOCAB=tuple(native._all_modal_families())
CONFIG={'schema':'autoformalization-source-only-ae-consumer/v1','parser_text_chars':4096,'view_vocabulary':VIEW_VOCAB,'modal_vocabulary':MODAL_VOCAB,'sample_memory':'False for T0/T2/T3; True only for explicit T1 memorization baseline','reference_cache':False,'source_embedding_input_allowed':True,'embedding_safe_projection':False,'proof_abstention_threshold':0.55,'t0':'native cold state','metric_scope':'source embedding reconstruction and machine target agreement, never independent semantic fidelity'}

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def objsha(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def softmax(x):
 m=max(x.values());p={k:math.exp(v-m) for k,v in x.items()};z=sum(p.values());return {k:v/z for k,v in p.items()}

class SourceOnlyModel(native.AdaptiveModalAutoencoder):
 def _cache_legal_ir_targets(self,*args,**kwargs):raise RuntimeError('Reference cache forbidden')
 def _legal_ir_view_target_distribution_for_sample(self,sample,*,include_autoencoder_prior=True):
  # No compiler targets or target-derived keys. Pure source heuristic prior is
  # retained where the native decoder uses source-modal information for gating.
  assert not self._legal_ir_view_target_cache and not self._legal_ir_loss_target_cache
  return self._autoencoder_view_target_distribution_for_sample(sample) if include_autoencoder_prior else {}
 def _legal_ir_view_distribution_for_embedding(self,sample,*,use_sample_memory):
  assert use_sample_memory is False
  return softmax(self._legal_ir_view_logits_for(sample,VIEW_VOCAB,use_sample_memory=False))
 def _reconstruction_safe_projection(self,target,base,candidate):
  # No comparison, tuning, blending, or choice based on reconstruction target.
  return list(candidate)
 def encode(self,*args,**kwargs):raise RuntimeError('Use explicit source-only prediction API')
 def decode(self,*args,**kwargs):raise RuntimeError('Use explicit source-only projection API')

def source_sample(row,embedding=None):
 allowed={k:row.get(k) for k in ('record_id','text','title','section_id','citation','family')}
 if not isinstance(allowed['text'],str) or not allowed['text']:raise ValueError('Source text required')
 return build_us_code_sample(title=str(allowed['title'] or 'CFR'),section=str(allowed['section_id'] or allowed['record_id']),text=allowed['text'][:4096],citation=str(allowed['citation'] or allowed['record_id']),embedding_model='sentence-transformers/all-MiniLM-L6-v2' if embedding is not None else 'not_used:classification_only',embedding_vector=embedding if embedding is not None else [0.0])

class ArrayRows(dict):
 """Lazy native list rows backed by a read-only exact-float64 NPY array."""
 def __init__(self,keys,array):super().__init__((k,i) for i,k in enumerate(keys));self.array=array
 def __getitem__(self,k):return self.array[super().__getitem__(k)].tolist()
 def get(self,k,default=None):return self[k] if k in self else default
 def items(self):return ((k,self[k]) for k in self)
 def values(self):return (self[k] for k in self)

def load_model(compact=None,vectors=None):
 if compact is None:return SourceOnlyModel(compute_device='cpu'),{'arm_id':'T0','seed':None,'checkpoint_sha256':None}
 x=json.load(open(compact));state=SimpleNamespace(**x['state'])
 if x['source_metadata']['arm_id'] in {'T2','T3'} and set(state.legal_ir_view_embedding_weights)!=set(VIEW_VOCAB):raise ValueError('Frozen output alphabet differs from training checkpoint')
 if vectors:
  import numpy as np
  manifest=json.load(open(Path(vectors)/'manifest.json'))
  for k,v in manifest['components'].items():
   if sha(Path(vectors)/v['keys_file'])!=v['keys_sha256'] or sha(Path(vectors)/v['array_file'])!=v['array_sha256']:raise ValueError('Vector artifact identity mismatch')
   keys=json.load(open(Path(vectors)/v['keys_file']))
   array=np.load(Path(vectors)/v['array_file'],mmap_mode='r')
   if array.dtype!=np.float64 or array.shape!=(len(keys),384) or len(keys)!=v['rows']:raise ValueError('Vector shape/dtype mismatch')
   state.__dict__[k]=ArrayRows(keys,array)
 kwargs={k:0.0 for k in x.get('disabled_embedding_scales',[])}
 model=SourceOnlyModel(state=state,compute_device='cpu',**kwargs)
 return model,{'arm_id':x['source_metadata']['arm_id'],'seed':x['source_metadata']['seed'],'checkpoint_sha256':x['source_sha256'],'compact_sha256':sha(compact),'vectors_manifest_sha256':sha(Path(vectors)/'manifest.json') if vectors else None}

def predict_row(model,row,provenance=None,embedding=None):
 start=time.monotonic();sample=source_sample(row,embedding)
 memory_control=(provenance or {}).get('arm_id')=='T1'
 views=softmax(model._legal_ir_view_logits_for(sample,VIEW_VOCAB,use_sample_memory=False))
 modal=softmax(model._logits_for_families(sample,MODAL_VOCAB,use_sample_memory=memory_control))
 features=model._legal_ir_view_feature_keys_for(sample)
 learned=[k for k in features if k in model.state.feature_legal_ir_view_logits or k in model.state.feature_family_logits or k in model.state.feature_embedding_weights]
 predicted_view=max(views,key=lambda k:(views[k],k))
 # Export all FIXED family heads: downstream source-only routing can choose a
 # context from its own source proposal without receiving reference labels.
 proof={family:model.predict_proof_auxiliary_heads(family) for family in native.LEGAL_IR_VIEW_FAMILIES}
 result={'schema':'autoformalization-source-only-prediction/v1','record_id':row['record_id'],'text_sha256':hashlib.sha256(row['text'].encode()).hexdigest(),'parser_text_sha256':hashlib.sha256(sample.text.encode()).hexdigest(),'family':row.get('family'),'parser_window_chars':len(sample.text),'view_distribution':views,'modal_distribution':modal,'predicted_view':predicted_view,'proof_heads_by_family':proof,'active_learned_features':learned,'sample_memory_used':memory_control,'sample_memory_hit':memory_control and sample.sample_id in model.state.decoded_embeddings,'reference_targets_used':False,**(provenance or {})}
 if embedding is not None:
  result['decoded_source_embedding']=model._decoded_for(sample,use_sample_memory=memory_control)
  result['input_embedding_sha256']=objsha(embedding)
 result['wall_seconds']=time.monotonic()-start
 model._sample_feature_cache.clear()
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--sources',required=True,type=Path);p.add_argument('--compact',type=Path);p.add_argument('--vectors',type=Path);p.add_argument('--embeddings',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--freeze',type=Path);p.add_argument('--split',choices=('train','selection','final'),required=True);a=p.parse_args()
 inherited_hard=resource.getrlimit(resource.RLIMIT_AS)[1]
 memory_ceiling=min(64<<30,inherited_hard) if inherited_hard!=resource.RLIM_INFINITY else 64<<30
 resource.setrlimit(resource.RLIMIT_AS,(memory_ceiling,memory_ceiling));cpus=sorted(os.sched_getaffinity(0))[-2:];os.sched_setaffinity(0,cpus)
 if a.split=='final':
  if not a.freeze:raise ValueError('Final access requires frozen manifest')
  freeze=json.load(open(a.freeze))
  if freeze.get('source_only_eval_sha256')!=sha(__file__):raise ValueError('Consumer differs from freeze')
  if freeze.get('final_sources_sha256')!=sha(a.sources):raise ValueError('Final sources differ from freeze')
  if freeze.get('native_implementation_sha256')!=sha(native.__file__):raise ValueError('Native implementation differs from freeze')
  if freeze.get('configuration_sha256')!=objsha(CONFIG):raise ValueError('Configuration differs from freeze')
  if not a.embeddings or freeze.get('source_embeddings_sha256')!=sha(a.embeddings):raise ValueError('Source embeddings differ from derived input binding')
  if a.compact:
   record=json.load(open(a.compact))
   binding={'compact_sha256':sha(a.compact),'checkpoint_sha256':record['source_sha256'],'arm_id':record['source_metadata']['arm_id'],'seed':record['source_metadata']['seed'],'vectors_manifest_sha256':sha(a.vectors/'manifest.json') if a.vectors else None}
   if binding not in freeze.get('model_bindings',[]):raise ValueError('Checkpoint/vector model binding not frozen')
  elif freeze.get('t0_allowed') is not True:raise ValueError('T0 not frozen')
 start=time.monotonic();model,provenance=load_model(a.compact,a.vectors)
 embedding_records={r['record_id']:r for r in map(json.loads,open(a.embeddings))} if a.embeddings else None
 embeddings={k:r['embedding_vector'] for k,r in embedding_records.items()} if embedding_records else None
 if a.vectors is not None and a.embeddings is None:raise ValueError('Vector consumer requires source embeddings')
 a.output.parent.mkdir(parents=True,exist_ok=True);count=0
 with a.output.open('x') as out,a.sources.open() as sources:
  for line in sources:
   row=json.loads(line)
   if embeddings:
    er=embedding_records[row['record_id']]
    if er['text_sha256']!=hashlib.sha256(row['text'].encode()).hexdigest() or er['embedding_vector_sha256']!=objsha(er['embedding_vector']):raise ValueError('Source embedding row binding mismatch')
   prediction=predict_row(model,row,provenance,embeddings[row['record_id']] if embeddings else None)
   out.write(json.dumps(prediction,sort_keys=True,separators=(',',':'))+'\n');out.flush();count+=1
 receipt={'schema':'autoformalization-source-only-inference-receipt/v1','configuration':CONFIG,'configuration_sha256':objsha(CONFIG),'consumer_sha256':sha(__file__),'native_implementation_sha256':sha(native.__file__),'sources_sha256':sha(a.sources),'predictions_sha256':sha(a.output),'count':count,'split':a.split,'provenance':provenance,'sample_memory_enabled':provenance['arm_id']=='T1','wall_seconds':time.monotonic()-start,'cpu_seconds':time.process_time(),'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'targets_read':False}
 Path(str(a.output)+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
