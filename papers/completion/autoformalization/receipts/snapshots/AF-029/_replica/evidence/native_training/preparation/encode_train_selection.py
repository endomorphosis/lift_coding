"""Frozen development-only MiniLM preprocessing; runs inside an offline container."""
from pathlib import Path
import hashlib,json,os,resource,time,sys
from datetime import datetime,timezone
import importlib.metadata as metadata
BASE=Path('/job');OUT=Path('/output')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def save(name,value):
 p=OUT/name
 with p.open('xb')as f:f.write(canon(value));f.flush();os.fsync(f.fileno())
start=time.monotonic();cpu0=resource.getrusage(resource.RUSAGE_SELF);manifest=json.loads((BASE/'preprocessing_manifest.json').read_text())
report={'schema':'af-native-training-encoder-execution/v1','started_at':datetime.now(timezone.utc).isoformat(),'manifest_sha256':sha(BASE/'preprocessing_manifest.json'),'source_sha256':sha(BASE/'encode_train_selection.py'),'status':'incomplete','new_model_api_calls':0,'grouping_vectors_loaded':False,'final_inputs_opened':False,'runtime':{},'counts':{}}
try:
 assert report['source_sha256']==manifest['producer_source_sha256']
 assert manifest['splits']=={'train':69,'selection':15}
 for name,expected in manifest['model_files'].items():assert sha(Path('/encoder')/name)==expected['sha256']
 inputs={}
 for split in ['train','selection']:
  p=BASE/'inputs'/(split+'.sources.jsonl');expected=manifest['inputs'][split];assert sha(p)==expected['sha256']
  rows=[json.loads(line)for line in p.read_text().splitlines()if line.strip()];assert len(rows)==manifest['splits'][split];inputs[split]=rows
 assert len({r['record_id']for rows in inputs.values()for r in rows})==84
 import torch,numpy
 from transformers import AutoModel,AutoTokenizer
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
 assert torch.cuda.is_available()is False
 report['runtime']={'python':sys.version,'executable':sys.executable,'packages':{n:metadata.version(n)for n in ['torch','numpy','transformers','tokenizers','safetensors','huggingface-hub']},'origins':{'torch':torch.__file__,'numpy':numpy.__file__},'torch_threads':torch.get_num_threads(),'torch_interop_threads':torch.get_num_interop_threads(),'cuda_available':torch.cuda.is_available()}
 tokenizer=AutoTokenizer.from_pretrained('/encoder',local_files_only=True,trust_remote_code=False)
 model=AutoModel.from_pretrained('/encoder',local_files_only=True,trust_remote_code=False).to('cpu').eval()
 assert str(next(model.parameters()).dtype)=='torch.float32'
 assert tokenizer.num_special_tokens_to_add(pair=False)==2
 output=[];window_rows=[]
 with torch.inference_mode():
  for split,rows in inputs.items():
   total_tokens=0;total_windows=0
   for row in rows:
    text=row['text'];tokens=tokenizer(text,add_special_tokens=False,truncation=False)['input_ids'];assert tokens
    sums=torch.zeros(384,dtype=torch.float32);weight_sum=0;windows=[]
    for offset in range(0,len(tokens),254):
     chunk=tokens[offset:offset+254];prepared=tokenizer.prepare_for_model(chunk,add_special_tokens=True,truncation=False,return_attention_mask=True,return_token_type_ids=True);assert len(prepared['input_ids'])<=256
     batch={k:torch.tensor([v],dtype=torch.long)for k,v in prepared.items()if k in ['input_ids','attention_mask','token_type_ids']}
     hidden=model(**batch).last_hidden_state;mask=batch['attention_mask'].unsqueeze(-1).to(hidden.dtype)
     vector=torch.nn.functional.normalize((hidden*mask).sum(1)/mask.sum(1).clamp(min=1e-9),p=2,dim=1)[0]
     assert vector.shape==(384,)and torch.isfinite(vector).all()
     sums+=len(chunk)*vector;weight_sum+=len(chunk)
     windows.append({'offset':offset,'content_tokens':len(chunk),'input_tokens_with_specials':len(prepared['input_ids']),'token_ids_sha256':hashlib.sha256(canon(chunk)).hexdigest()})
    embedding=torch.nn.functional.normalize((sums/weight_sum).reshape(1,-1),p=2,dim=1)[0]
    assert torch.isfinite(embedding).all()and abs(float(torch.linalg.vector_norm(embedding))-1)<1e-5
    vector=embedding.tolist();source_hash=hashlib.sha256(text.encode()).hexdigest()
    output.append({'record_id':row['record_id'],'split':split,'document_sha256':row['document_sha256'],'text_sha256':source_hash,'text_characters':len(text),'embedding_model':manifest['model_id'],'embedding_revision':manifest['model_revision'],'embedding_dimension':384,'embedding_vector':vector,'embedding_vector_sha256':hashlib.sha256(canon(vector)).hexdigest(),'content_tokens':len(tokens),'windows':len(windows),'preprocessing_manifest_sha256':report['manifest_sha256'],'source_gold':False,'independent_gold':False})
    window_rows.append({'record_id':row['record_id'],'split':split,'text_sha256':source_hash,'windows':windows})
    total_tokens+=len(tokens);total_windows+=len(windows)
    print(json.dumps({'split':split,'completed_rows_in_split':sum(r['split']==split for r in output),'content_tokens':total_tokens,'windows':total_windows}),flush=True)
   report['counts'][split]={'rows':len(rows),'content_tokens':total_tokens,'windows':total_windows}
 assert len(output)==84
 save('native_training_inputs.json',{'schema':'af-frozen-real-semantic-encoder-inputs/v1','scope':'train_and_selection_only','manifest_sha256':report['manifest_sha256'],'model_id':manifest['model_id'],'model_revision':manifest['model_revision'],'no_fitting_on_selection':True,'final_test_access':False,'teacher_type':'fixed_pretrained_semantic_embedding_not_source_gold','rows':output})
 save('window_inventory.json',{'schema':'af-encoder-window-inventory/v1','manifest_sha256':report['manifest_sha256'],'rows':window_rows})
 report.update(status='completed',outputs={n:{'sha256':sha(OUT/n),'bytes':(OUT/n).stat().st_size}for n in ['native_training_inputs.json','window_inventory.json']},real_embedding_rows=84,teacher_fitting_updates=0)
except BaseException as exc:
 report.update(error={'type':type(exc).__name__,'message':str(exc)});raise
finally:
 usage=resource.getrusage(resource.RUSAGE_SELF);report.update(completed_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,cpu_seconds=(usage.ru_utime-cpu0.ru_utime)+(usage.ru_stime-cpu0.ru_stime),peak_rss_bytes=usage.ru_maxrss*1024)
 for target in ['/sys/fs/cgroup/memory.peak','/sys/fs/cgroup/cpu.stat']:
  p=Path(target)
  if p.exists():report.setdefault('cgroup_observations',{})[target]=p.read_text().strip()
 save('execution_receipt.json',report)
