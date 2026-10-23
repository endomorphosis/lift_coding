"""Train and evaluate richer CodebaseIR features on the frozen public corpus."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback
from evidence_io import ROOT, FALSE, predecessor_inputs, read, write, sha, wire, pin

POLICY={'schema':'terminal-typed-ir-training-policy@1','source_files':5,
    'source_bytes_per_file':8192,'ast_nodes_per_file':2048,'feature_width_max':4096,
    'fixed_task_splits':True,'new_optimizer_steps_budget':272,'training_seeds':[1729,2718,31415],
    'cpu_seconds_hard_limit':180,'address_space_bytes_hard_limit':8*1024**3,
    'file_bytes_hard_limit':32*1024**2,'outer_wall_seconds':240,
    'training_root_memory_mb':1024,'native_shared_scheduler':True,
    'source_execution':False,'official_terminal_bench_harness_executed':False,
    'native_full_supervisor_invoked':False,'automatic_model_promotion':False,**FALSE}

def coverage(targets):
    names=set(targets['feature_names']);result={}
    for role in ['train','validation','evaluation']:
        rows=[r for r in targets['rows'] if r['split']==role];blocks={}
        for name in ['ast','calls','diagnostics','effects','imports','interfaces','literals','references','scopes','symbols','types']:
            masses=[(sum(v for k,v in r['atom_counts'].items() if k.startswith(name+'|') and k in names),
                sum(v for k,v in r['atom_counts'].items() if k.startswith(name+'|') and k not in names)) for r in rows]
            blocks[name]={'known_atom_mass':sum(a for a,b in masses),'unknown_atom_mass':sum(b for a,b in masses),
                'target_nonzero_rows':sum(a+b>0 for a,b in masses),'fully_unrepresented_rows':sum(a==0 and b>0 for a,b in masses),
                'modality_in_fitted_vocabulary':any(k.startswith(name+'|') for k in names)}
        result[role]={'function_count':len(rows),'known_atom_mass':sum(r['known_atom_mass'] for r in rows),
            'unknown_atom_mass':sum(r['unknown_atom_mass'] for r in rows),'modalities':blocks}
    return result

def check_lease(lease):
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import LeaseCancelledError
    if lease.cancelled:raise LeaseCancelledError('native experiment lease cancelled')

def validate_summary(result,targets,runs,panels,structural,metadata):
    fields={'schema','completed','policy','feature_width','latent_width','split_counts','coverage','optimizer_steps',
        'same_seed_full_replay','primary_evaluation','metadata','native_head','native_structural_current_at_final_observation',
        'artifact_pins','nomination_report_sha256','source_execution','native_full_supervisor_invoked',
        'official_terminal_bench_harness_executed','peak_rss_kib','seconds',*FALSE}
    if type(result) is not dict or set(result)!=fields or result['schema']!='terminal-richer-typed-ir-training-experiment@1':
        raise ValueError('closed result summary required')
    if result['completed'] is not True or result['policy']!=POLICY or any(result[k] is not False for k in FALSE):
        raise ValueError('result policy or authority differs')
    integers={'feature_width':len(targets['feature_names']),'latent_width':16,
              'optimizer_steps':sum(r['completed_optimizer_steps'] for r in runs)}
    if any(type(result[k]) is not int or result[k]!=v for k,v in integers.items()) or result['optimizer_steps']!=272:
        raise ValueError('result dimensions or optimizer accounting differs')
    if result['split_counts']!=targets['split_counts'] or result['coverage']!=coverage(targets):
        raise ValueError('result population or residual coverage differs')
    if result['primary_evaluation']!=panels[0]['panels']['evaluation'] or result['metadata']!=metadata:
        raise ValueError('result evaluation or metadata differs')
    if result['native_head']!=structural['head'] or result['native_structural_current_at_final_observation'] is not True:
        raise ValueError('result native current head differs')
    if result['same_seed_full_replay'] is not True or any(result[k] is not False for k in
        ['source_execution','native_full_supervisor_invoked','official_terminal_bench_harness_executed']):
        raise ValueError('result runtime or replay claim differs')

def source_repository(output,bodies):
    repository=output/'source-repository';repository.mkdir()
    for name,body in sorted(bodies.items()):
        path=repository/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(body)
    for args in [['init','-q'],['add','--',*sorted(bodies)],
        ['-c','user.name=CodebaseIR experiment','-c','user.email=local-experiment@localhost',
         'commit','-q','-m','Fixed public Terminal Bench source-only corpus']]:
        process=subprocess.run(['git','-C',str(repository),*args],stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
        if process.returncode or process.stderr:raise ValueError('source-only Git preparation failed')
    return repository

def metadata_records(structural,targets,runs,panels,nomination,provenance):
    def row(kind,payload):
        return {'row_id':sha(wire({'kind':kind,'record':payload})), 'record':payload, **FALSE}
    records={'sources':[row('source',{k:v for k,v in s.items() if k!='ast'}) for s in structural['sources']],
        'ast':[row('ast',{'path':s['path'],'ast':s['ast']}) for s in structural['sources']],
        'typed_targets':[row('target',r) for r in targets['rows']],
        'feature_space':[row('feature_space',{k:v for k,v in targets.items() if k!='rows'})],
        'residuals':[row('residual',{'unit_id':r['unit_id'],'unknown_atoms':r['unknown_atoms']}) for r in targets['rows']],
        'training':[row('training',r) for r in runs],
        'evaluations':[row('evaluation',p) for p in panels],
        'nomination':[row('nomination',nomination)],'provenance':[row('provenance',provenance)],
        'vectors':[row('vector',{'unit_id':r['unit_id'],'latent':panels[0]['learned_latents'][i],
            'features':r['features'],'source_sha256':r['source_sha256'],'advisory_only':True})
            for i,r in enumerate(targets['rows'])],
        'kg':[], 'interfaces':[], 'effects':[], 'contracts':[]}
    for s in structural['sources']:
        ast=s['ast']
        for kind in ['symbols','scopes','imports','references','calls']:
            records['kg'].extend(row(kind,{'path':s['path'],'kind':kind,'value':v}) for v in ast.get(kind,[]))
        records['effects'].extend(row('effect',{'path':s['path'],'value':v}) for v in ast.get('effects',[]))
        records['interfaces'].extend(row('interface',{'path':s['path'],'symbol_id':v['symbol_id'],
            'signature':v['signature'],'span':v['span']}) for v in ast['symbols'] if v['signature'] is not None)
    records['contracts']=[row('contract',{'profile':'alignment_structural_nomination_only',
        'nomination':nomination,'source_semantics_proved_by_training':False})]
    return records

def run(output):
    resource.setrlimit(resource.RLIMIT_CPU,(180,180))
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    if output.resolve()!=output or output.exists() or output.parent!=ROOT:
        raise ValueError('exclusive canonical owned experiment required')
    output.mkdir(mode=0o700);write(output/'policy.json',POLICY)
    started=time.monotonic()
    corpus,original,bodies,lineage=predecessor_inputs()
    write(output/'corpus-manifest.json',corpus);write(output/'lineage.json',lineage)
    repository=source_repository(output,bodies)
    from native_structural_ir import prepare_structural_ir, verify_structural_ir, _scheduler
    structural=prepare_structural_ir(repository=repository,output=output/'structural',
        repository_id='terminal-typed-ir-training-20261014-01:'+output.name,
        expected_sources={name:sha(body) for name,body in bodies.items()})
    write(output/'structural-report.json',structural)
    source_records=[{**s,'source_bytes':bodies[s['path']]} for s in structural['sources']]
    from typed_targets import build_targets, validate_targets
    targets=build_targets(corpus,source_records)
    validate_targets(corpus,source_records,expected=targets)
    write(output/'typed-targets.json',targets)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLane
    scheduler=_scheduler();runs=[];panels=[]
    with scheduler.acquire(ResourceLane.TRAINER,cpu_slots=1,memory_mb=1024,child_process_slots=1,
                           timeout=30,request_id='terminal-typed-ir:bounded-training') as lease:
        check_lease(lease)
        import torch
        torch.set_num_threads(1);torch.set_num_interop_threads(1)
        from typed_training import RUNS, fit, evaluate, forward, matrix, validate_checkpoint
        from nomination_review import evaluate_nominations, authored_query_vector
        write(output/'runtime.json',{'python':sys.version,'executable':sys.executable,
            'torch_version':str(torch.__version__),'torch_module':torch.__file__,
            'actual_native_shared_admission':True,'cpu_slots':1,'memory_mb':1024,'torch_threads':1,
            'loaded_policy':'sealed-source-pinned-current-native-overlay',
            'complete_transitive_loaded_code_closure':False})
        for run_id,seed,epochs in RUNS:
            check_lease(lease)
            print(json.dumps({'stage':'typed_training_start','run_id':run_id,'feature_width':len(targets['feature_names'])}),flush=True)
            with (output/(run_id+'-optimizer-receipts.jsonl')).open('xb') as receipts:
                def observer(value):
                    receipts.write(wire(value)+b'\n');receipts.flush();os.fsync(receipts.fileno())
                saved=fit(targets,run_id=run_id,seed=seed,epochs=epochs,
                    checkpoint=lambda:check_lease(lease),step_observer=observer)
            write(output/(run_id+'-checkpoint.json'),saved)
            panel=evaluate(saved,targets);write(output/(run_id+'-evaluation.json'),panel)
            runs.append(saved);panels.append(panel)
            print(json.dumps({'stage':'typed_training_complete','run_id':run_id,'steps':saved['completed_optimizer_steps'],
                'selected_epoch':saved['selected_epoch'],'eval_mse':panel['panels']['evaluation']['learned']['mse']}),flush=True)
        primary={k:v for k,v in runs[0].items() if k!='run_id'}
        replay={k:v for k,v in runs[1].items() if k!='run_id'}
        if primary!=replay:raise ValueError('same-seed full optimizer replay differs')
        if {k:v for k,v in panels[0].items() if k!='run_id'}!={k:v for k,v in panels[1].items() if k!='run_id'}:
            raise ValueError('same-seed full inference replay differs')
        query=authored_query_vector(targets['feature_names'])
        params=validate_checkpoint(runs[0],targets)
        with torch.no_grad():query_latent=forward(matrix([query['vector']],len(targets['feature_names'])),params)[0][0].tolist()
        nomination=evaluate_nominations(corpus_manifest=corpus,targets=targets,source_records=source_records,
            learned_reconstructions=panels[0]['learned_reconstructions'],
            untrained_reconstructions=panels[0]['untrained_reconstructions'],
            alignment_projection=original['alignment_projection'],
            learned_latents=panels[0]['learned_latents'],query_latent=query_latent)
        write(output/'nomination-report.json',nomination)
        records=metadata_records(structural,targets,runs,panels,nomination,
            {'lineage':lineage,'policy':POLICY,'native_head':structural['head'],
             'same_seed_optimizer_replay':True,'historical_alignment_proof_authority':False})
        from metadata_projections import hydrate_and_verify_records
        with lease.acquire_child(lane=ResourceLane.PERSISTENCE,cpu_slots=1,memory_mb=256,
            child_process_slots=1,timeout=20,request_id='terminal-typed-ir:metadata-readback') as child:
            check_lease(child)
            metadata=hydrate_and_verify_records(records=records,output=output/'metadata',
                source_snapshot={'schema':'terminal-richer-ir-snapshot@1','native_head':structural['head'],
                    'target_sha256':sha(wire(targets)),'selected_checkpoint_sha256':sha(wire(runs[0]))})
        write(output/'metadata-report.json',metadata)
    verify_structural_ir(repository=repository,output=output/'structural',expected=structural)
    if predecessor_inputs()[3]!=lineage:raise ValueError('selected sealed lineage changed')
    validate_targets(corpus,source_records,expected=targets)
    files=['policy.json','corpus-manifest.json','lineage.json','structural-report.json','typed-targets.json',
        'runtime.json','nomination-report.json','metadata-report.json']
    files += [run_id+suffix for run_id,_,_ in RUNS for suffix in ['-checkpoint.json','-evaluation.json','-optimizer-receipts.jsonl']]
    artifacts=[{'relative_path':name,**{k:v for k,v in pin(output/name).items() if k!='path'}} for name in sorted(files)]
    result={'schema':'terminal-richer-typed-ir-training-experiment@1','completed':True,'policy':POLICY,
        'feature_width':len(targets['feature_names']),'latent_width':16,'split_counts':targets['split_counts'],'coverage':coverage(targets),
        'optimizer_steps':sum(r['completed_optimizer_steps'] for r in runs),'same_seed_full_replay':True,
        'primary_evaluation':panels[0]['panels']['evaluation'],'metadata':metadata,
        'native_head':structural['head'],'native_structural_current_at_final_observation':True,'artifact_pins':artifacts,
        'nomination_report_sha256':sha(wire(nomination)),'source_execution':False,
        'native_full_supervisor_invoked':False,'official_terminal_bench_harness_executed':False,
        'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'seconds':time.monotonic()-started,**FALSE}
    validate_summary(result,targets,runs,panels,structural,metadata)
    write(output/'result.json',result)
    print(json.dumps({'stage':'complete','optimizer_steps':result['optimizer_steps'],'seconds':result['seconds']}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    try:run(Path(args.output))
    except BaseException as error:
        destination=Path(args.output)
        if destination.is_dir() and not (destination/'failure.json').exists():
            write(destination/'failure.json',{'class':type(error).__name__,'message':str(error),**FALSE})
        traceback.print_exc();raise
