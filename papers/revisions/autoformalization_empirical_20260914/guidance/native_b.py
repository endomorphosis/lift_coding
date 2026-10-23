#!/usr/bin/env python3
"""Bounded actual typed-deontic compiler and source-withheld round-trip arm B.

The added vocabulary producer uses only contiguous lexical spans from the same
source prefix. It is a declared lexical projection, not semantic gold or a
learned stage. Native compiler, decompiler, policy, and CID gates are unchanged.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,resource,signal,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
for k,v in {'IPFS_DATASETS_PY_MINIMAL_IMPORTS':'1','IPFS_DATASETS_AUTO_INSTALL':'false','IPFS_KIT_AUTO_INSTALL_DEPS':'0','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1','CUDA_VISIBLE_DEVICES':'','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}.items():os.environ[k]=v
sys.path.insert(0,str(ROOT/'external/ipfs_datasets'))
from ipfs_datasets_py.logic.legal_ir import canonical_compiler,canonical_contracts,canonical_decompiler,canonical_roundtrip
from ipfs_datasets_py.logic.deontic import converter

CONFIG={
 'schema':'autoformalization-native-B-source-lexicon/v1','source_prefix_characters':4096,'record_timeout_seconds':5.0,
 'vocabulary':{'tokens':'lowercase [a-z0-9]+','boundary':'each punctuation/newline-delimited source segment; no cross-segment ngrams','actors_ngram_lengths':[1,2,3,4,5],'actions_ngram_lengths':[1],'objects_ngram_lengths':[1,2,3,4,5],'qualifiers_ngram_lengths':[1,2,3,4,5],'maximum_atoms_per_category':1000,'selection':'shortest ngram first, source occurrence order, unique; then lexicographic serialization','scope':'lexical source-derived projection, not semantic gold'},
 'allow_explicit_partial':False,'fallback':False,'model_calls':0,'decompiler_source_withheld':True,
 'metric_scope':'native execution and L1/L2 structural equality, not natural-language source fidelity or theorem truth',
}


def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(8<<20),b''):h.update(block)
 return h.hexdigest()


def objsha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def implementation():
 modules={m.__name__:sha(m.__file__) for m in (canonical_compiler,canonical_contracts,canonical_decompiler,canonical_roundtrip,converter)}
 return {'runner_sha256':sha(__file__),'native_modules':modules,'configuration':CONFIG,'native_compiler_configuration':canonical_compiler.compiler_configuration(),'native_roundtrip_configuration':canonical_roundtrip.roundtrip_configuration()}


def source_vocabulary(text):
 segments=[re.findall(r'[a-z0-9]+',segment.lower()) for segment in re.split(r'[.;!?\n]+',text)]
 def atoms(lengths):
  values={}
  for size in lengths:
   for words in segments:
    for offset in range(max(0,len(words)-size+1)):
     value='_'.join(words[offset:offset+size])
     if value not in values and len(values)<1000:values[value]=None
  return tuple(sorted(values))
 return canonical_contracts.CanonicalAtomVocabulary(actors=atoms(range(1,6)),actions=atoms((1,)),objects=atoms(range(1,6)),qualifiers=atoms(range(1,6)))


class RecordTimeout(BaseException):pass


def _expired(_signum,_frame):raise RecordTimeout('Native B exceeded frozen five-second record budget')


def run_record(row):
 record_id=row['record_id'];source=row['text'];prefix=source[:4096]
 started=time.monotonic();old_handler=signal.signal(signal.SIGALRM,_expired);signal.setitimer(signal.ITIMER_REAL,5.0)
 result={'schema':'autoformalization-native-B-execution/v1','arm':'B_native_source_lexicon_v1','record_id':record_id,'family':row.get('family'),'text_sha256':hashlib.sha256(source.encode()).hexdigest(),'prefix_sha256':hashlib.sha256(prefix.encode()).hexdigest(),'source_characters':len(source),'prefix_characters':len(prefix),'source_truncated':len(source)>4096,'model_calls':0,'replica_used':False,'reference_targets_used':False,'human_semantics_measured':False,'status':'started'}
 try:
  vocabulary=source_vocabulary(prefix)
  result['vocabulary_sha256']=objsha(vocabulary.to_dict());result['vocabulary_counts']={k:len(v) for k,v in vocabulary.to_dict().items()}
  request=canonical_contracts.CompilerRequest(source_text=prefix,request_id=record_id,atom_vocabulary=vocabulary,allow_explicit_partial=False)
  pipeline=canonical_roundtrip.CanonicalSemanticRoundTrip()
  native=pipeline.run(request)
  payload=native.to_dict()
  # Native decoder rechecks every nested CID and the outer evidence chain.
  decoded=canonical_roundtrip.CanonicalSemanticRoundTripResult.from_dict(payload)
  if decoded.to_dict()!=payload:raise ValueError('Native wire receipt did not round-trip exactly')
  l1=native.l1_result;l2=native.l2_result
  l1_ir=l1.canonical_ir.to_dict() if l1 and l1.canonical_ir else None
  l2_ir=l2.canonical_ir.to_dict() if l2 and l2.canonical_ir else None
  result.update(status='measured',native_status=native.status.value,terminal_stage=native.terminal_stage,
   compile_success=bool(l1 and l1.status is canonical_contracts.OperationStatus.SUCCESS),
   canonical_ir=l1_ir,canonical_rule_count=len(l1_ir['rules']) if l1_ir else 0,
   roundtrip_completed=native.status is canonical_contracts.OperationStatus.SUCCESS,
   roundtrip_exact=(l1_ir==l2_ir) if l1_ir is not None and l2_ir is not None else None,
   native_receipt=payload,native_receipt_sha256=objsha(payload),native_cid_revalidated=True,
   decompiler_original_source_visible=False)
 except RecordTimeout as exc:
  result.update(status='timeout',error=str(exc),compile_success=False,canonical_ir=None,canonical_rule_count=0,roundtrip_completed=False,roundtrip_exact=None)
 except Exception as exc:
  result.update(status='error',error_type=type(exc).__name__,error=str(exc),compile_success=False,canonical_ir=None,canonical_rule_count=0,roundtrip_completed=False,roundtrip_exact=None)
 finally:
  signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_handler)
  result['wall_seconds']=time.monotonic()-started
 return result


def main():
 p=argparse.ArgumentParser();p.add_argument('--sources',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--split',choices=('constructed','selection','final'),required=True);p.add_argument('--freeze',type=Path);a=p.parse_args()
 hard=resource.getrlimit(resource.RLIMIT_AS)[1];cap=min(4<<30,hard) if hard!=resource.RLIM_INFINITY else 4<<30;resource.setrlimit(resource.RLIMIT_AS,(cap,cap));os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[-2:]))
 identity=implementation()
 if a.split=='final':
  if not a.freeze:raise ValueError('Final access requires frozen profile')
  frozen=json.loads(a.freeze.read_text())
  if frozen.get('native_b_implementation')!=identity or frozen.get('final_sources_sha256')!=sha(a.sources):raise ValueError('Final sources or native B implementation differs from frozen profile')
 started=time.monotonic();counts={};seen=set();total=0
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x') as out,a.sources.open() as sources:
  for line in sources:
   row=json.loads(line)
   if row['record_id'] in seen:raise ValueError('Duplicate source ID')
   seen.add(row['record_id']);result=run_record(row)
   out.write(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n');out.flush();total+=1
   status=result.get('native_status',result['status']);counts[status]=counts.get(status,0)+1
   print(json.dumps({'count':total,'last_status':status,'wall_seconds':time.monotonic()-started}),flush=True)
 if a.split=='final' and total!=1913:raise ValueError('Final denominator differs from 1,913')
 receipt={'schema':'autoformalization-native-B-run-receipt/v1','implementation':identity,'split':a.split,'count':total,'status_counts':counts,'sources_sha256':sha(a.sources),'results_sha256':sha(a.output),'wall_seconds':time.monotonic()-started,'cpu_seconds':time.process_time(),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'reference_targets_read':False,'model_calls':0,'final_records_read':a.split=='final'}
 Path(str(a.output)+'.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
