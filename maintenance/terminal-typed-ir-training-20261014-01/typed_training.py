"""Experimental multi-head structural AE; learned numbers have no proof authority.

Four float64 parameter tensors and AdamW are owned here. The preserved neutral
native loss kernel computes FP32 MSE/cosine/guarded-norm losses, with no legal
or logic-family target. Fixed validation selects weights; evaluation never fits.
"""
from types import SimpleNamespace
import math
import re
import time
from evidence_io import FALSE, sha, wire

SCHEMA = 'terminal-typed-structural-autoencoder@1'
CONFIG = {'epochs': 64, 'latent_width': 16, 'learning_rate': .01, 'weight_decay': .0001,
    'betas': [.9,.999], 'eps': 1e-8, 'gradient_clip': 1., 'cosine_weight': .1,
    'parameter_dtype': 'float64', 'native_loss_dtype': 'float32',
    'objective': 'macro_modality_native_mse_cosine_guarded_norm',
    'selection': 'minimum_fixed_validation_objective_including_untrained',
    'vocabulary': 'training_functions_only', 'max_seconds_per_run': 60.}
RUNS = [('primary-1729',1729,64), ('replay-1729',1729,64),
        ('seed-2718',2718,64), ('seed-31415',31415,64), ('short-1729',1729,16)]

def require(ok, message):
    if not ok:
        raise ValueError(message)

def matrix(values, width):
    import torch
    require(type(values) is list and 1 <= len(values) <= 128 and 1 <= width <= 4096,
            'bounded nonempty feature matrix required')
    require(all(type(row) is list and len(row) == width and all(type(v) in (int,float)
        and math.isfinite(v) for v in row) for row in values), 'finite exact feature shape required')
    return torch.tensor(values, dtype=torch.float64)

def parameters(values, width, latent):
    import torch
    require(type(latent) is int and 1 <= latent <= 64, 'bounded latent width required')
    require(type(values) is list and len(values) == 4, 'four parameter tensors required')
    result = [torch.tensor(row, dtype=torch.float64) for row in values]
    require([tuple(p.shape) for p in result] == [(width,latent),(latent,),(latent,width),(width,)]
        and all(bool(torch.isfinite(p).all()) for p in result), 'finite checkpoint tensors required')
    return result

def forward(inputs, params):
    import torch
    latent = torch.tanh(inputs @ params[0] + params[1])
    return latent, latent @ params[2] + params[3]

def seeded_parameters(width, latent, seed):
    import torch
    require(type(seed) is int and 0<=seed<2**31, 'bounded exact seed required')
    generator=torch.Generator(device='cpu').manual_seed(seed)
    return [torch.randn(shape,generator=generator,dtype=torch.float64)*.1 if len(shape)==2
        else torch.zeros(shape,dtype=torch.float64)
        for shape in [(width,latent),(latent,),(latent,width),(width,)]]

def modalities(feature_names):
    require(type(feature_names) is list and 1 <= len(feature_names) <= 4096
        and feature_names == sorted(set(feature_names))
        and all(type(v) is str and '|' in v for v in feature_names), 'canonical fitted columns required')
    spans = {}
    for index, name in enumerate(feature_names):
        key = name.split('|',1)[0]
        if key not in spans:
            spans[key] = [index,index+1]
        else:
            spans[key][1] = index+1
    return spans

def native_objective(data, prediction, params, spans):
    import torch
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import modal_autoencoder_cuda as kernel
    empty = torch.zeros((len(data),0), dtype=torch.float64)
    session = SimpleNamespace(blocks={},parameters=params,parameter_count=sum(p.numel() for p in params))
    total = 0.
    for start, end in spans.values():
        state = SimpleNamespace(torch=torch,device=torch.device('cpu'),embeddings=data[:,start:end])
        value, _, _ = kernel._loss_chunk(state,session,(prediction[:,start:end],empty,empty),
            {'decoded_embedding'},0,len(data),len(data),CONFIG['cosine_weight'],0.,False)
        total = total + value/len(spans)
    return total

def metrics(expected, predicted, spans):
    import torch
    require(expected.shape == predicted.shape and bool(torch.isfinite(predicted).all()), 'finite matching inference required')
    blocks = {}
    for name,(start,end) in spans.items():
        x,y=expected[:,start:end],predicted[:,start:end]
        mask = torch.linalg.vector_norm(x,dim=1)>1e-8
        cosine = torch.nn.functional.cosine_similarity(x,y,dim=1,eps=1e-8)
        blocks[name]={'mse':float((x-y).square().mean()),'target_nonzero_rows':int(mask.sum()),
            'cosine_on_nonzero_targets':float(cosine[mask].mean()) if bool(mask.any()) else None}
    present, nominated = expected>0, predicted>.1
    tp=int((present&nominated).sum());fp=int((~present&nominated).sum());fn=int((present&~nominated).sum())
    precision=tp/(tp+fp) if tp+fp else 0.;recall=tp/(tp+fn) if tp+fn else 0.
    return {'mse':float((expected-predicted).square().mean()),
        'macro_modality_mse':sum(v['mse'] for v in blocks.values())/len(blocks),'modalities':blocks,
        'known_atom_presence_threshold':.1,'presence_precision':precision,'presence_recall':recall,
        'presence_f1':2*precision*recall/(precision+recall) if precision+recall else 0.,
        'unseen_atoms_not_in_reconstruction_loss':True,'exact_source_reconstruction':False}

def bindings(targets):
    names=targets['feature_names'];modalities(names)
    rows=targets['rows']
    require(len(rows)==28 and {r['split'] for r in rows}=={'train','validation','evaluation'},
            'fixed complete public split required')
    require(len({r['unit_id'] for r in rows})==len(rows), 'duplicate function identity')
    tasks={}
    for row in rows:
        role=row['split']; task=row['task_id']
        require(task not in tasks or tasks[task]==role, 'task split leakage')
        tasks[task]=role
    return {'targets_sha256':sha(wire(targets)),'feature_names_sha256':sha(wire(names)),
        'training_units':[r['unit_id'] for r in rows if r['split']=='train'],
        'validation_units':[r['unit_id'] for r in rows if r['split']=='validation'],
        'evaluation_units':[r['unit_id'] for r in rows if r['split']=='evaluation']}

def fit(targets, *, run_id, seed, epochs, checkpoint=None, step_observer=None):
    import torch
    require(type(seed) is int and 0<=seed<2**31 and type(epochs) is int and 1<=epochs<=64,
            'bounded training configuration required')
    started=time.monotonic(); bound=bindings(targets)
    names=targets['feature_names'];width=len(names);spans=modalities(names)
    train=matrix([r['features'] for r in targets['rows'] if r['split']=='train'],width)
    validation=matrix([r['features'] for r in targets['rows'] if r['split']=='validation'],width)
    require(len(train)==8 and len(validation)==1, 'frozen training/validation population differs')
    latent=CONFIG['latent_width']
    params=[p.requires_grad_() for p in seeded_parameters(width,latent,seed)]
    initial=[p.detach().tolist() for p in params]
    optimizer=torch.optim.AdamW(params,lr=CONFIG['learning_rate'],weight_decay=CONFIG['weight_decay'],
        betas=tuple(CONFIG['betas']),eps=CONFIG['eps'])
    def snapshot():
        moments=[]
        for p in params:
            state=optimizer.state.get(p,{})
            moments.append({'step':int(state.get('step',0)),
                'exp_avg':state.get('exp_avg',torch.zeros_like(p)).tolist(),
                'exp_avg_sq':state.get('exp_avg_sq',torch.zeros_like(p)).tolist()})
        return {'parameters':[p.detach().tolist() for p in params],'optimizer_moments':moments}
    with torch.no_grad():
        initial_validation=float(native_objective(validation,forward(validation,params)[1],params,spans))
    best=snapshot();best_loss=initial_validation;selected_epoch=0;steps=[]
    for epoch in range(1,epochs+1):
        if checkpoint is not None:checkpoint()
        require(time.monotonic()-started<CONFIG['max_seconds_per_run'], 'training wall budget exhausted')
        before=sha(wire([p.detach().tolist() for p in params]));optimizer.zero_grad(set_to_none=True)
        value=native_objective(train,forward(train,params)[1],params,spans)
        require(bool(torch.isfinite(value)), 'nonfinite objective')
        value.backward()
        gradient=float(torch.nn.utils.clip_grad_norm_(params,CONFIG['gradient_clip']))
        require(math.isfinite(gradient), 'nonfinite gradient')
        optimizer.step()
        finite=all(bool(torch.isfinite(p).all()) for p in params)
        after=sha(wire([p.detach().tolist() for p in params])) if finite else None
        tensor_steps=[int(optimizer.state[p]['step']) for p in params]
        if step_observer is not None:step_observer({'epoch':epoch,'weights_before_sha256':before,
            'weights_after_sha256':after,'parameters_finite':finite,'actual_optimizer_tensor_steps':tensor_steps})
        require(tensor_steps==[epoch]*4 and finite, 'actual finite AdamW steps required')
        with torch.no_grad():
            tuning=float(native_objective(validation,forward(validation,params)[1],params,spans))
            train_after=float(native_objective(train,forward(train,params)[1],params,spans))
        require(math.isfinite(tuning) and math.isfinite(train_after), 'nonfinite post-fit metrics')
        selected=tuning<best_loss
        if selected:
            best=snapshot();best_loss=tuning;selected_epoch=epoch
        steps.append({'epoch':epoch,'weights_before_sha256':before,'weights_after_sha256':after,
            'train_objective_before':float(value.detach()),'train_objective_after':train_after,
            'validation_objective_after':tuning,'unclipped_gradient_norm':gradient,
            'selected':selected,'actual_optimizer_tensor_steps':tensor_steps})
    return {'schema':SCHEMA,'run_id':run_id,'seed':seed,'configuration':{**CONFIG,'epochs':epochs},
        'bindings':bound,'initial_parameters':initial,'initial_parameters_sha256':sha(wire(initial)),
        **best,'selected_parameters_sha256':sha(wire(best['parameters'])),
        'selected_epoch':selected_epoch,'initial_validation_objective':initial_validation,
        'selected_validation_objective':best_loss,'completed_optimizer_steps':len(steps),
        'final_parameters_sha256':sha(wire([p.detach().tolist() for p in params])),
        'parameter_count':sum(p.numel() for p in params),'steps':steps,**FALSE}

def validate_checkpoint(saved, targets):
    fields={'schema','run_id','seed','configuration','bindings','initial_parameters','initial_parameters_sha256',
        'parameters','optimizer_moments','selected_parameters_sha256','selected_epoch','initial_validation_objective',
        'selected_validation_objective','completed_optimizer_steps','final_parameters_sha256','parameter_count','steps',*FALSE}
    require(type(saved) is dict and set(saved)==fields and saved.get('schema')==SCHEMA and all(saved.get(k) is False for k in FALSE),
            'unpromoted structural checkpoint required')
    require(type(saved['completed_optimizer_steps']) is int and 1<=saved['completed_optimizer_steps']<=64
        and type(saved['selected_epoch']) is int and 0<=saved['selected_epoch']<=saved['completed_optimizer_steps']
        and type(saved['seed']) is int and 0<=saved['seed']<2**31, 'exact bounded optimizer integers required')
    require(all(type(saved[k]) in (int,float) and math.isfinite(saved[k]) and saved[k]>=0 for k in
        ['initial_validation_objective','selected_validation_objective']), 'finite nonnegative validation objective required')
    require(all(type(saved[k]) is str and re.fullmatch('[0-9a-f]{64}',saved[k]) for k in
        ['initial_parameters_sha256','selected_parameters_sha256','final_parameters_sha256']), 'canonical numerical SHA256 required')
    require(saved['bindings']==bindings(targets), 'checkpoint target/vocabulary/split binding differs')
    params=parameters(saved['parameters'],len(targets['feature_names']),saved['configuration']['latent_width'])
    require(sha(wire(saved['parameters']))==saved['selected_parameters_sha256']
        and sha(wire(saved['initial_parameters']))==saved['initial_parameters_sha256'], 'numerical binding differs')
    parameters(saved['initial_parameters'],len(targets['feature_names']),saved['configuration']['latent_width'])
    require([p.tolist() for p in seeded_parameters(len(targets['feature_names']),saved['configuration']['latent_width'],saved['seed'])]
        ==saved['initial_parameters'], 'seeded initial parameter control differs')
    require(type(saved['parameter_count']) is int and saved['parameter_count']==sum(p.numel() for p in params),
            'parameter count differs')
    require(saved['configuration']=={**CONFIG,'epochs':saved['completed_optimizer_steps']}, 'optimizer configuration differs')
    steps=saved['steps'];require(len(steps)==saved['completed_optimizer_steps'] and 1<=len(steps)<=64,
            'complete bounded optimizer ledger required')
    previous=saved['initial_parameters_sha256'];best=saved['initial_validation_objective'];selected=0
    for index, row in enumerate(steps,1):
        require(type(row['epoch']) is int and row['epoch']==index and row['weights_before_sha256']==previous
            and type(row['actual_optimizer_tensor_steps']) is list and all(type(v) is int for v in row['actual_optimizer_tensor_steps'])
            and row['actual_optimizer_tensor_steps']==[index]*4
            and all(type(row[k]) in (int,float) and math.isfinite(row[k]) and row[k]>=0 for k in ['train_objective_before','train_objective_after',
                'validation_objective_after','unclipped_gradient_norm'])
            and type(row['weights_after_sha256']) is str and re.fullmatch('[0-9a-f]{64}',row['weights_after_sha256']), 'optimizer ledger differs')
        improved=row['validation_objective_after']<best
        require(row['selected'] is improved,'validation selection replay differs')
        if improved:best=row['validation_objective_after'];selected=index
        previous=row['weights_after_sha256']
    require(selected==saved['selected_epoch'] and best==saved['selected_validation_objective']
        and previous==saved['final_parameters_sha256'], 'selection or final ledger differs')
    expected_hash=saved['initial_parameters_sha256'] if not selected else steps[selected-1]['weights_after_sha256']
    require(expected_hash==saved['selected_parameters_sha256'], 'selected weights differ from actual step ledger')
    require(type(saved['optimizer_moments']) is list and len(saved['optimizer_moments'])==4,
            'four optimizer moment records required')
    for p,item in zip(params,saved['optimizer_moments']):
        for key in ['exp_avg','exp_avg_sq']:
            import torch
            x=torch.tensor(item[key],dtype=torch.float64)
            require(x.shape==p.shape and bool(torch.isfinite(x).all()), 'invalid optimizer moment')
            if key=='exp_avg_sq':require(bool((x>=0).all()),'negative squared moment')
        require(type(item['step']) is int and item['step']==selected, 'optimizer moment epoch differs')
    return params

def evaluate(saved, targets):
    import torch
    params=validate_checkpoint(saved,targets);names=targets['feature_names'];spans=modalities(names)
    data=matrix([r['features'] for r in targets['rows']],len(names))
    initial=parameters(saved['initial_parameters'],len(names),CONFIG['latent_width'])
    training=data[[i for i,r in enumerate(targets['rows']) if r['split']=='train']]
    with torch.no_grad():
        latent,predicted=forward(data,params);untrained_latent,untrained=forward(data,initial)
        mean=training.mean(dim=0,keepdim=True);mean_pred=mean.expand_as(data)
        _,singular,v=torch.linalg.svd(training-mean,full_matrices=False)
        tolerance=max(training.shape)*torch.finfo(training.dtype).eps*float(singular[0])
        numerical_rank=int((singular>tolerance).sum())
        effective=min(CONFIG['latent_width'],numerical_rank);basis=v[:effective]
        svd=(data-mean)@basis.T@basis+mean
        predictions={'learned':predicted,'same_seed_untrained':untrained,'train_mean':mean_pred,
            'train_svd':svd,'zero':torch.zeros_like(data),'deterministic_features':data}
        panels={}
        for split in ['train','validation','evaluation']:
            selected=[i for i,r in enumerate(targets['rows']) if r['split']==split]
            panels[split]={name:metrics(data[selected],value[selected],spans) for name,value in predictions.items()}
    return {'schema':'terminal-typed-structural-evaluation@1','run_id':saved['run_id'],
        'selection_used_validation':True,'evaluation_used_for_fit_or_selection':False,
        'svd_fitted_training_only':True,'svd_basis_count':effective,'svd_training_numerical_rank':numerical_rank,
        'svd_rank_tolerance':tolerance,'svd_rank_is_not_neural_latent_width':True,
        'panels':panels,'learned_reconstructions':predicted.tolist(),'untrained_reconstructions':untrained.tolist(),
        'learned_latents':latent.tolist(),'untrained_latents':untrained_latent.tolist(),**FALSE}
