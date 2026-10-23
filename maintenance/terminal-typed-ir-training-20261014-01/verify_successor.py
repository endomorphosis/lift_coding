"""Fresh-process source, checkpoint arithmetic, rankings, and lake readback."""
import argparse
import json
from pathlib import Path
import resource
from evidence_io import ROOT,FALSE,read,write,sha,wire,predecessor_inputs
from run_successor import POLICY, coverage, validate_summary, check_lease

def run(directory):
    resource.setrlimit(resource.RLIMIT_CPU,(180,180))
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    if directory.resolve()!=directory or directory.parent!=ROOT:raise ValueError('owned run required')
    result=json.loads(read(directory/'result.json'))
    if result.get('schema')!='terminal-richer-typed-ir-training-experiment@1' or result.get('completed') is not True:
        raise ValueError('complete closed experiment required')
    if result['policy']!=POLICY or any(result.get(k) is not False for k in FALSE):
        raise ValueError('experiment policy or authority claims changed')
    for key in ['source_execution','native_full_supervisor_invoked','official_terminal_bench_harness_executed']:
        if result.get(key) is not False:raise ValueError('unobserved runtime authority claim')
    from typed_training import RUNS,CONFIG,validate_checkpoint,metrics,modalities,parameters
    names=['policy.json','corpus-manifest.json','lineage.json','structural-report.json','typed-targets.json',
        'runtime.json','nomination-report.json','metadata-report.json']
    names += [run_id+suffix for run_id,_,_ in RUNS for suffix in ['-checkpoint.json','-evaluation.json','-optimizer-receipts.jsonl']]
    expected=sorted(names)
    if [row['relative_path'] for row in result['artifact_pins']]!=expected:
        raise ValueError('complete selected artifact scope required')
    for row in result['artifact_pins']:
        if set(row)!= {'relative_path','bytes','sha256'}:raise ValueError('closed artifact binding required')
        raw=read(directory/row['relative_path'],32*1024**2)
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('selected artifact changed')
    corpus,original,bodies,lineage=predecessor_inputs()
    if wire(lineage)!=read(directory/'lineage.json') or wire(corpus)!=read(directory/'corpus-manifest.json'):
        raise ValueError('sealed selected source lineage changed')
    structural=json.loads(read(directory/'structural-report.json'))
    from native_structural_ir import verify_structural_ir,_scheduler
    repository=directory/'source-repository'
    verify_structural_ir(repository=repository,output=directory/'structural',expected=structural)
    records=[]
    for row in structural['sources']:
        raw=read(repository/row['path'],8192)
        if raw!=bodies[row['path']]:raise ValueError('live original source differs')
        records.append({**row,'source_bytes':raw})
    targets=json.loads(read(directory/'typed-targets.json'))
    from typed_targets import validate_targets
    validate_targets(corpus,records,expected=targets)
    if result['coverage']!=coverage(targets):raise ValueError('known or residual target coverage differs')
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    with _scheduler().acquire(ResourceLane.VALIDATION,cpu_slots=1,memory_mb=1024,child_process_slots=1,
        timeout=30,request_id='terminal-typed-ir:cold-forward') as lease:
        import torch
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
        # Separate complete batch arithmetic. No trainer forward or optimizer call.
        data=torch.tensor([r['features'] for r in targets['rows']],dtype=torch.float64)
        runs=[];panels=[]
        for run_id,seed,epochs in RUNS:
            saved=json.loads(read(directory/(run_id+'-checkpoint.json')))
            params=validate_checkpoint(saved,targets)
            receipts=[json.loads(line) for line in read(directory/(run_id+'-optimizer-receipts.jsonl')).splitlines()]
            expected_receipts=[{k:step[k] for k in ['epoch','weights_before_sha256','weights_after_sha256',
                'actual_optimizer_tensor_steps']}|{'parameters_finite':True} for step in saved['steps']]
            if receipts!=expected_receipts:raise ValueError('immediate optimizer receipts differ from completed ledger')
            if (saved['run_id'],saved['seed'],saved['completed_optimizer_steps'])!=(run_id,seed,epochs):
                raise ValueError('fixed run configuration differs')
            with torch.no_grad():
                latent=torch.tanh(torch.matmul(data,params[0])+params[1])
                prediction=torch.matmul(latent,params[2])+params[3]
                initial=parameters(saved['initial_parameters'],len(targets['feature_names']),CONFIG['latent_width'])
                untrained_latent=torch.tanh(torch.matmul(data,initial[0])+initial[1])
                untrained=torch.matmul(untrained_latent,initial[2])+initial[3]
                training=data[[i for i,r in enumerate(targets['rows']) if r['split']=='train']]
                mean=training.mean(dim=0,keepdim=True)
                _,singular,v=torch.linalg.svd(training-mean,full_matrices=False)
                tolerance=max(training.shape)*torch.finfo(training.dtype).eps*float(singular[0])
                numerical_rank=int((singular>tolerance).sum());effective=min(CONFIG['latent_width'],numerical_rank)
                basis=v[:effective];svd=(data-mean)@basis.T@basis+mean
                predictions={'learned':prediction,'same_seed_untrained':untrained,
                    'train_mean':mean.expand_as(data),'train_svd':svd,'zero':torch.zeros_like(data),
                    'deterministic_features':data}
            panel=json.loads(read(directory/(run_id+'-evaluation.json')))
            if latent.tolist()!=panel['learned_latents'] or prediction.tolist()!=panel['learned_reconstructions']:
                raise ValueError('separate cold checkpoint arithmetic differs')
            if untrained_latent.tolist()!=panel['untrained_latents'] or untrained.tolist()!=panel['untrained_reconstructions']:
                raise ValueError('separate cold untrained arithmetic differs')
            measured={}
            for split in ['train','validation','evaluation']:
                indices=[i for i,r in enumerate(targets['rows']) if r['split']==split]
                measured[split]={key:metrics(data[indices],value[indices],modalities(targets['feature_names']))
                    for key,value in predictions.items()}
            if measured!=panel['panels'] or panel['svd_basis_count']!=effective or panel['svd_training_numerical_rank']!=numerical_rank or panel['svd_rank_tolerance']!=tolerance:
                raise ValueError('cold reconstruction or baseline controls differ')
            runs.append(saved);panels.append(panel);check_lease(lease)
        if {k:v for k,v in runs[0].items() if k!='run_id'}!={k:v for k,v in runs[1].items() if k!='run_id'}:
            raise ValueError('full same-seed replay differs')
        if result['primary_evaluation']!=panels[0]['panels']['evaluation'] or result['optimizer_steps']!=sum(r['completed_optimizer_steps'] for r in runs):
            raise ValueError('experiment metrics or optimizer accounting differs')
        from nomination_review import authored_query_vector,evaluate_nominations
        query=authored_query_vector(targets['feature_names'])
        with torch.no_grad():
            params=validate_checkpoint(runs[0],targets)
            query_latent=torch.tanh(torch.tensor([query['vector']],dtype=torch.float64)@params[0]+params[1])[0].tolist()
        nomination=evaluate_nominations(corpus_manifest=corpus,targets=targets,source_records=records,
            learned_reconstructions=panels[0]['learned_reconstructions'],
            untrained_reconstructions=panels[0]['untrained_reconstructions'],alignment_projection=original['alignment_projection'],
            learned_latents=panels[0]['learned_latents'],query_latent=query_latent)
        if wire(nomination)!=read(directory/'nomination-report.json') or sha(wire(nomination))!=result['nomination_report_sha256']:
            raise ValueError('cold contract nomination differs')
        from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as native_metadata
        from benchmarks.agent_supervisor.container_coding.terminal_codebase_supervisor_fixture import reconstruct_terminal_codebase_metadata_records
        metadata=json.loads(read(directory/'metadata-report.json'))
        validate_summary(result,targets,runs,panels,structural,metadata)
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=256,
            child_process_slots=1,timeout=20,request_id='terminal-typed-ir:cold-lake') as child:
            check_lease(child)
            reopened=native_metadata.validate_codebase_ir_metadata(output=directory/'metadata',
                expected=metadata['native_metadata'],fresh_process=True)
        restored={}
        for family,descriptor in reopened['exports'].items():
            restored[family]=[json.loads(line)['payload'] for line in read(directory/'metadata'/descriptor['relative_path']).splitlines()]
        recovered=reconstruct_terminal_codebase_metadata_records(restored)
        if sha(wire(recovered))!=metadata['records_sha256']:raise ValueError('cold complete lake records differ')
    verify_structural_ir(repository=repository,output=directory/'structural',expected=structural)
    if predecessor_inputs()[3]!=lineage:raise ValueError('lineage changed during replay')
    return {'schema':'terminal-richer-typed-ir-cold-replay@1','qualified':True,
        'current_native_source_head_verified_before_and_after':True,'selected_artifact_bindings_verified':True,
        'separate_checkpoint_forward_exact':True,'recorded_genuine_same_seed_optimizer_runs_match':True,
        'optimizer_steps_executed_in_cold_replay':0,
        'all_five_checkpoints_verified':True,'complete_duckdb_ducklake_readback':True,
        'contract_nomination_exact_replay':True,'native_shared_resource_admission':True,
        'numerical_independence':'separate forward code, shared Torch numerical backend',**FALSE}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);parser.add_argument('--report',required=True)
    args=parser.parse_args()
    for name in [args.run,args.report]:
        if not name or Path(name).name!=name or name in {'.','..'}:raise ValueError('local names required')
    report=run(ROOT/args.run);write(ROOT/args.report,report);print(json.dumps(report))
