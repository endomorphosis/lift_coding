#!/usr/bin/env python3
"""Development-only prediction-boundary and exact-state consumer checks."""
import hashlib,json,math,sys,time
from pathlib import Path
from source_only_eval import SourceOnlyModel,source_sample,predict_row,load_model,objsha,sha,VIEW_VOCAB,native,HERE

def stable(row):return {k:v for k,v in row.items() if k!='wall_seconds'}
def main():
 results=[]
 model,prov=load_model(HERE/'compact/T3-104729.json')
 row={'record_id':'constructed-boundary-001','family':'constructed','title':'CFR','section_id':'1','citation':'constructed','text':'The agency shall file a notice unless an emergency prevents filing.'}
 a=stable(predict_row(model,row,prov));b=stable(predict_row(model,{**row,'reference':{'view_distribution':{'WRONG_FINAL_LABEL':1}},'target_embedding':[1e6]*384,'gold_label':'WRONG_FINAL_LABEL'},prov))
 assert a==b;results.append('injected reference/gold fields cannot affect the predictor')
 model._legal_ir_view_target_cache['poison']={'WRONG_FINAL_LABEL':1}
 try:predict_row(model,row,prov)
 except AssertionError:results.append('nonempty reference cache causes a hard rejection')
 else:raise AssertionError('Reference cache did not reject')
 model._legal_ir_view_target_cache.clear()
 assert model._reconstruction_safe_projection([999],[0],[2])==[2]
 assert model._reconstruction_safe_projection([-999],[0],[2])==[2]
 results.append('direct decoder returns candidate independently of target vector')
 assert set(a['view_distribution'])==set(VIEW_VOCAB)
 assert not model.state.decoded_embeddings and not model.state.family_logits
 results.append('fixed two-view vocabulary and T3 memory exclusion enforced')
 for seed in (104729,130363,155921):
  t2=json.load(open(HERE/f'compact/T2-{seed}.json'));t3=json.load(open(HERE/f'compact/T3-{seed}.json'))
  assert t2['source_metadata']['protected_fingerprint']==t3['source_metadata']['protected_fingerprint']
  excluded={'applied_proof_feedback_ids','proof_auxiliary_head_logits','proof_auxiliary_head_schema_version','proof_feedback_version_fingerprint'}
  assert {k:v for k,v in t2['state'].items() if k not in excluded}=={k:v for k,v in t3['state'].items() if k not in excluded}
  manifest=json.load(open(HERE/f'vectors/T2-{seed}/manifest.json'))
  assert manifest['source_checkpoint_sha256']==t2['source_sha256']
  assert set(t2['state']['legal_ir_view_embedding_weights'])==set(VIEW_VOCAB)
 results.append('all three exact-protected T2/T3 pairs match; fixed alphabet comes only from retained checkpoint keys')
 report={'schema':'autoformalization-source-only-boundary-qualification/v1','passed':True,'consumer_sha256':sha(HERE/'source_only_eval.py'),'native_implementation_sha256':sha(native.__file__),'checks':results,'constructed_records':1,'final_records_opened':0,'policy':'No compiler/reference labels supplied to inference; source-input reconstruction is not semantic gold'}
 (HERE/'boundary_qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
