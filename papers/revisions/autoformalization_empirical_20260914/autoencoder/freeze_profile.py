#!/usr/bin/env python3
"""Build fixed scientific configuration from development-only verified artifacts."""
import json
from pathlib import Path
from source_only_eval import HERE,CONFIG,sha,objsha,native

def build():
 review=json.load(open(HERE/'engineering_review_guidance.json'))
 boundary=json.load(open(HERE/'boundary_qualification.json'))
 if boundary['consumer_sha256']!=sha(HERE/'source_only_eval.py') or boundary['passed'] is not True:raise ValueError('Boundary qualification changed')
 model_bindings=[]
 for arm in ('T1','T2','T3'):
  for seed in (104729,130363,155921):
   p=HERE/f'compact/{arm}-{seed}.json';x=json.load(open(p));v=HERE/f'vectors/T2-{seed}/manifest.json' if arm in ('T2','T3') else None
   model_bindings.append({'arm_id':arm,'seed':seed,'compact_sha256':sha(p),'checkpoint_sha256':x['source_sha256'],'vectors_manifest_sha256':sha(v) if v else None})
 encoder=json.load(open(HERE/'selection/reencoded_sources.jsonl.receipt.json'))
 out={'schema':'autoformalization-ae-frozen-scientific-profile/v1','source_only_eval_sha256':sha(HERE/'source_only_eval.py'),'encoder_source_sha256':sha(HERE/'encode_sources.py'),'scorer_sha256':sha(HERE/'score_embeddings.py'),'derive_t3_sha256':sha(HERE/'derive_t3.py'),'derive_t1_sha256':sha(HERE/'derive_t1.py'),'native_implementation_sha256':sha(native.__file__),'configuration':CONFIG,'configuration_sha256':objsha(CONFIG),'encoder_model_files':encoder['model_files'],'model_bindings':model_bindings,'t0_allowed':True,'final_access_performed':False,'final_input_binding_policy':'After parent protocol frozen and final export authorized, bind derived source export and source embedding file SHA256. This adds input identities only; configuration, code, models, output alphabet, seeds, metrics and budgets remain unchanged.','primary_metrics':['mean source-input MiniLM reconstruction cosine','mean source-input MiniLM reconstruction MSE','T1 sample memory hits','isolated proof-head distributions and scored structural-contract agreement'],'uncertainty':{'primary':'Paired connected-source-component bootstrap of seed-mean T2 minus T0 unit deltas: 10000 draws, resample the 20 original AF004 operational source components with replacement and include all their member units, seed104729. Preserve and discuss the dominant 1738-record component and four-edition dependence.','secondary':'Domain-stratified paired unit bootstrap, 2000 draws, seed104729: conditional finite-cohort display only, not an independent-unit generalization claim.','membership':'Root supplies original frozen AF004 component membership through the final export binding; grouping is not chosen from outcomes.'},'scope':'No independent semantic fidelity claim, no reference-guided output alphabet, no decode candidate selection against reference, no classifier-learning gain from empty fixed-vocabulary heads','development_qualifications':{'boundary_sha256':sha(HERE/'boundary_qualification.json'),'independent_review_sha256':sha(HERE/'engineering_review_guidance.json'),'encoder_bitexact_sha256':sha(HERE/'selection/encoder_equivalence.json'),'derived_controls_sha256':sha(HERE/'derived_controls_qualification.json')},'history':'Seven-view and initial wrongly assumed two-view pilots retained. Boundary test rejected incorrect two-key alphabet; final two keys read and asserted from all three retained TRAINING states, before any final access.'}
 return out
if __name__=='__main__':
 out=build();p=HERE/'scientific_profile.json'
 if p.exists():raise ValueError('Scientific profile already exists')
 p.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print(sha(p))
