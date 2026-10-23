#!/usr/bin/env python3
"""Offline MiniLM source embeddings with the AF029 full-document window contract."""
from pathlib import Path
import argparse,hashlib,json,os,resource,time
for k,v in {'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','MKL_NUM_THREADS':'2','TOKENIZERS_PARALLELISM':'false','USE_TF':'0','TORCH_DEVICE_BACKEND_AUTOLOAD':'0'}.items():os.environ[k]=v
from extract_heads import digest_file
REVISION='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
MODEL=Path('/home/barberb/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots')/REVISION
CONFIG={'model_id':'sentence-transformers/all-MiniLM-L6-v2','revision':REVISION,'content_window_tokens':254,'tokenization':'WordPiece without truncation','pooling':'attention-mask mean then per-window L2','aggregation':'content-token-weighted average then document L2','dtype':'float32','device':'cpu','threads':2,'batch_size':1,'semantic_gold':False}

def main():
 p=argparse.ArgumentParser();p.add_argument('--sources',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--split',choices=['train','selection','final'],required=True);p.add_argument('--freeze',type=Path);p.add_argument('--limit',type=int);a=p.parse_args()
 resource.setrlimit(resource.RLIMIT_AS,(8<<30,8<<30));os.sched_setaffinity(0,sorted(os.sched_getaffinity(0))[-2:]);start=time.monotonic()
 if a.split=='final':
  if not a.freeze:raise ValueError('Frozen manifest required')
  frozen=json.load(open(a.freeze))
  if frozen['encoder_source_sha256']!=digest_file(__file__) or frozen['final_sources_sha256']!=digest_file(a.sources):raise ValueError('Frozen identity mismatch')
  if a.limit:raise ValueError('Final truncation forbidden')
 import torch,numpy,transformers,tokenizers
 from transformers import AutoTokenizer,AutoModel
 torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
 tokenizer=AutoTokenizer.from_pretrained(MODEL,local_files_only=True,trust_remote_code=False)
 model=AutoModel.from_pretrained(MODEL,local_files_only=True,trust_remote_code=False).to('cpu').eval()
 assert str(next(model.parameters()).dtype)=='torch.float32'
 model_files={p.name:digest_file(p) for p in MODEL.iterdir() if p.is_file() and p.name in {'model.safetensors','pytorch_model.bin','config.json','tokenizer.json','tokenizer_config.json','vocab.txt','special_tokens_map.json'}}
 if a.split=='final' and frozen.get('encoder_model_files')!=model_files:raise ValueError('Encoder model assets differ from freeze')
 a.output.parent.mkdir(parents=True,exist_ok=True);count=0;windows_total=0;tokens_total=0
 with torch.inference_mode(),a.output.open('x') as out,a.sources.open() as sources:
  for line in sources:
   if a.limit and count>=a.limit:break
   row=json.loads(line);text=row['text'];ids=tokenizer(text,add_special_tokens=False,truncation=False)['input_ids']
   if not ids:raise ValueError('Empty tokenizer input')
   sums=torch.zeros(384,dtype=torch.float32);weight_sum=0;windows=[]
   for offset in range(0,len(ids),254):
    chunk=ids[offset:offset+254];prepared=tokenizer.prepare_for_model(chunk,add_special_tokens=True,truncation=False,return_attention_mask=True,return_token_type_ids=True)
    batch={k:torch.tensor([v],dtype=torch.long) for k,v in prepared.items() if k in ['input_ids','attention_mask','token_type_ids']}
    hidden=model(**batch).last_hidden_state;mask=batch['attention_mask'].unsqueeze(-1).to(hidden.dtype)
    vector=torch.nn.functional.normalize((hidden*mask).sum(1)/mask.sum(1).clamp(min=1e-9),p=2,dim=1)[0]
    assert vector.shape==(384,) and torch.isfinite(vector).all()
    sums+=len(chunk)*vector;weight_sum+=len(chunk);windows.append({'offset':offset,'content_tokens':len(chunk),'token_ids_sha256':hashlib.sha256(json.dumps(chunk,separators=(',',':')).encode()).hexdigest()})
   vector=torch.nn.functional.normalize((sums/weight_sum).reshape(1,-1),p=2,dim=1)[0].tolist()
   result={'record_id':row['record_id'],'split':a.split,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'embedding_model':CONFIG['model_id'],'embedding_revision':REVISION,'embedding_vector':vector,'embedding_vector_sha256':hashlib.sha256(json.dumps(vector,separators=(',',':')).encode()).hexdigest(),'content_tokens':len(ids),'window_inventory':windows,'source_gold':False,'independent_gold':False}
   out.write(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n');out.flush();count+=1;windows_total+=len(windows);tokens_total+=len(ids)
   print(json.dumps({'rows':count,'windows':windows_total,'tokens':tokens_total,'wall_seconds':time.monotonic()-start}),flush=True)
 receipt={'schema':'autoformalization-frozen-source-encoder/v1','configuration':CONFIG,'consumer_sha256':digest_file(__file__),'sources_sha256':digest_file(a.sources),'embeddings_sha256':digest_file(a.output),'model_files':model_files,'split':a.split,'count':count,'windows':windows_total,'tokens':tokens_total,'wall_seconds':time.monotonic()-start,'cpu_seconds':time.process_time(),'max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'package_versions':{'torch':torch.__version__,'numpy':numpy.__version__,'transformers':transformers.__version__,'tokenizers':tokenizers.__version__},'targets_read':False,'network_used':False,'services_started':False}
 Path(str(a.output)+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
