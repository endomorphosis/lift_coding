#!/usr/bin/env python3
"""Actual native spaCy-to-ModalIR compiler, fixed source-withheld cycle.

This deliberately omits the full codec's KG/embedding decoration. It is a
structural experiment, not a source-semantic or theorem correctness oracle.
"""
from pathlib import Path
import argparse, collections, dataclasses, hashlib, importlib.abc, importlib.util
import json, os, signal, sys, time

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
os.environ.update(IPFS_DATASETS_AUTO_INSTALL='false', IPFS_KIT_AUTO_INSTALL_DEPS='0',
 IPFS_DATASETS_PY_MINIMAL_IMPORTS='1', IPFS_DATASETS_PY_ENABLE_LLM_IMPORTS='0',
 HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', CUDA_VISIBLE_DEVICES='',
 OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
sys.path.insert(0,str(ROOT/'external/ipfs_datasets'))
sys.path.insert(0,str(HERE.parent/'guidance'))

def sha(b): return hashlib.sha256(b).hexdigest()

class Overlay(importlib.abc.MetaPathFinder):
 def find_spec(self, fullname, path, target=None):
  if fullname in {'ipfs_datasets_py.logic.modal.codec',
                  'ipfs_datasets_py.optimizers.logic_theorem_optimizer.spacy_modal_codec'}:
   p=HERE/'patch_overlay/external/ipfs_datasets'/Path(*fullname.split('.')).with_suffix('.py')
   return importlib.util.spec_from_file_location(fullname,p)

def setup(patched=False):
 if patched: sys.meta_path.insert(0,Overlay())
 from ipfs_datasets_py.optimizers.logic_theorem_optimizer.spacy_modal_codec import SpaCyLegalEncoder,SpaCyModalIRCompiler
 from ipfs_datasets_py.logic.modal import codec
 from ipfs_datasets_py.logic.modal.decompiler import decode_modal_ir_document
 from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_ir import ModalIRDocument,ModalIRProvenance
 from structural_checks import CHECKS,checker_contract
 encoder=SpaCyLegalEncoder(); compiler=SpaCyModalIRCompiler()
 def compile_text(text,record_id,citation=None):
  result=compiler.compile(encoder.encode(text,document_id=record_id,citation=citation,source='frozen_legal_corpus'))
  result=codec._enrich_modal_ir_formula_clauses(result)
  return codec._apply_executable_exception_scoping(result) if patched else result
 def withheld(doc):
  formulas=[dataclasses.replace(f,formula_id=f'ir:f{i:04d}',
   provenance=ModalIRProvenance(source_id='ir',start_char=0,end_char=0),metadata={})
   for i,f in enumerate(doc.formulas)]
  return ModalIRDocument(document_id='ir',source='withheld',normalized_text='',formulas=formulas)
 return compile_text,withheld,decode_modal_ir_document,CHECKS,checker_contract,encoder.used_fallback_model

def signature(doc):
 return collections.Counter(json.dumps({k:f.to_dict()[k] for k in
  ['operator','predicate','conditions','exceptions']},sort_keys=True) for f in doc.formulas)

def evaluate(row,api,seconds=10):
 compile_text,withheld,decode,checks,contract,fallback=api
 text=str(row['text'])[:4096]; rid=row['record_id']; start=time.monotonic()
 result={'record_id':rid,'text_sha256':sha(text.encode()),'full_text_sha256':sha(str(row['text']).encode()),
  'source_chars':len(row['text']),'evaluated_chars':len(text),'source_truncated':len(row['text'])>4096,
  'spacy_blank_fallback':fallback}
 def deadline(signum,frame):raise TimeoutError('per-record compiler/cycle budget')
 signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,seconds)
 try:
  doc=compile_text(text,rid,row.get('citation'));ir=doc.to_dict()
  packet={'record_id':rid,'text_sha256':sha(text.encode()),'canonical_ir':ir,'checker_contract':contract(),'source_text':text}
  results={name:check(packet) for name,check in checks.items()}
  result.update(status='measured',compile_status='measured',canonical_ir=ir,checks=results,formula_count=len(doc.formulas),
   family_counts=dict(collections.Counter(f.operator.family for f in doc.formulas)),
   compile_seconds=time.monotonic()-start)
  projected=withheld(doc); decoded=decode(projected).text
  cycled=compile_text(decoded[:4096],'ir')
  first,second=signature(projected),signature(cycled); common=sum((first&second).values())
  result['cycle']={'status':'measured','eligible':bool(doc.formulas),'source_withheld':True,'withheld_ir_sha256':sha(projected.to_json().encode()),
   'decoded_text':decoded,'decoded_truncated':len(decoded)>4096,'formula_count_after':len(cycled.formulas),
   'exact_semantic_field_multiset':first==second,'formula_multiset_precision':common/sum(second.values()) if second else 0.,
   'formula_multiset_recall':common/sum(first.values()) if first else 0.,
   'not_independent_semantic_fidelity':True}
 except Exception as exc:
  result.update(status='timeout' if isinstance(exc,TimeoutError) else 'error',error=type(exc).__name__+': '+str(exc))
  if result.get('compile_status')=='measured':result['cycle']={'status':result['status'],'eligible':bool(result.get('formula_count'))}
  else:result['compile_status']=result['status']
 finally:signal.setitimer(signal.ITIMER_REAL,0)
 result['wall_seconds']=time.monotonic()-start
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--patched',action='store_true');a=p.parse_args()
 api=setup(a.patched);a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x') as f:
  for i,line in enumerate(a.input.read_text().splitlines()):
   result=evaluate(json.loads(line),api);f.write(json.dumps(result,ensure_ascii=False)+'\n');f.flush()
   if i%50==0:print(json.dumps({'rows':i+1,'status':result['status']}),flush=True)
 return 0
if __name__=='__main__':raise SystemExit(main())
