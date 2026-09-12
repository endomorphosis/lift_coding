"""Witness the actual guarded outer trainer with a synthetic CPU fixture only."""
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path
from unittest.mock import patch
p=argparse.ArgumentParser();p.add_argument('--native-source',type=Path,required=True);a=p.parse_args()
sys.path[:0]=[str(a.native_source),'/home/barberb/.local/lib/python3.12/site-packages']
import torch
torch.set_num_threads(2);torch.set_num_interop_threads(2)
from ipfs_datasets_py.optimizers.logic_theorem_optimizer import modal_autoencoder_cuda as native
s=importlib.util.spec_from_file_location('actual_native_fixture',a.native_source/'tests/unit/optimizers/logic_theorem_optimizer/test_modal_autoencoder_cuda_training.py')
f=importlib.util.module_from_spec(s);s.loader.exec_module(f)
v=f._autoencoder('python');samples=f._samples();before=v.state.to_dict();calls=[]
executor=native.apply_cpu_reference_projection_update;scatter=native._scatter_blocks

def observed(*args, **kwargs):
    old=v.state.to_dict();blocks=[]
    step=min(1.,max(0.,float(kwargs['learning_rate'])))
    def same_step(model,session):
        for b in session.blocks.values():
            g=b.parameter.grad
            blocks.append({'component':b.component,'gradient_squared_norm':float(g.square().sum()),
                           'gradient_finite':bool(torch.isfinite(g).all()),
                           'changed_parameters':int((b.parameter!=b.initial).sum()),
                           'sgd_max_absolute_error':float((b.parameter-(b.initial-step*g)).abs().max())})
        return scatter(model,session)
    with patch.object(native,'_scatter_blocks',side_effect=same_step):
        r=executor(*args,**kwargs)
    calls.append({'report':r.to_dict(),'blocks':blocks,'canonical_state_changed_during_candidate':v.state.to_dict()!=old})
    return r

def forbidden(*args,**kwargs): raise AssertionError('historical nudge must not execute')
with patch.object(native,'apply_cpu_reference_projection_update',side_effect=observed), \
     patch.object(v,'_nudge_family_logits',side_effect=forbidden), \
     patch.object(v,'_nudge_decoded_embedding',side_effect=forbidden), \
     patch.object(v,'_nudge_legal_ir_view_logits',side_effect=forbidden):
    r=v.train_generalizable_projection(samples,validation_samples=samples,epochs=1,learning_rate=.025,
        projection_update_backend='packed_cpu',max_line_search_attempts=1,legal_ir_evaluate_provers=False)
after=v.state.to_dict();digest=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
assert r['accepted_epochs']==1 and before!=after
assert any(c['report']['gradient_norm']>0 and c['canonical_state_changed_during_candidate'] for c in calls)
assert all(b['gradient_finite'] and b['sgd_max_absolute_error']<=1e-7 for c in calls for b in c['blocks'])
assert after['family_logits']==before['family_logits'] and after['decoded_embeddings']==before['decoded_embeddings']
print(json.dumps({'schema':'actual-outer-packed-cpu-witness/v1','accepted_epochs':r['accepted_epochs'],
    'selected_update':r['epoch_reports'][0]['selected_update'],'candidate_update_order':r['candidate_update_order'],
    'backend':r['projection_update_backend'],'backend_report':r['projection_packed_cpu'],'same_step_calls':calls,
    'before_sha256':digest(before),'after_sha256':digest(after),'changed_components':[k for k in before if before[k]!=after[k]],
    'sample_memory_changed':False,'synthetic_training_and_validation_same_two_fixtures':True,
    'scientific_fidelity_evaluation':False,'research_benchmark':False,'existing_guardrails_unchanged':True},indent=2))
