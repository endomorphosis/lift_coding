"""Publish measured local status and successor priorities, then seal public artifacts."""
import json
import os
from pathlib import Path
from evidence_io import ROOT,FALSE,read,write,sha,pin,predecessor_inputs

def main():
    result=json.loads(read(ROOT/'experiment-02/result.json'))
    tests=json.loads(read(ROOT/'regression-03-process-report.json'))
    process=json.loads(read(ROOT/'experiment-02-process-report.json'))
    cold=json.loads(read(ROOT/'experiment-02-cold-02-cold-report.json'))
    cold_process=json.loads(read(ROOT/'experiment-02-cold-02-process-report.json'))
    faults=json.loads(read(ROOT/'native-faults-01.json'))
    if not all(r['qualified'] is True for r in [tests,process,cold,cold_process,faults]):
        raise ValueError('qualified selected tests, run, cold replay and genuine faults required')
    if tests['tests']!={'tests':83,'failures':0,'errors':0,'skipped':0}:
        raise ValueError('complete selected regression required')
    for entry in process['after']:
        if pin(Path(entry['path']))!=entry:
            raise ValueError('selected genuine-run producer changed after qualification')
    nomination=json.loads(read(ROOT/'experiment-02/nomination-report.json'))
    evaluation=result['primary_evaluation'];learned=evaluation['learned'];untrained=evaluation['same_seed_untrained']
    svd=evaluation['train_svd'];mean=evaluation['train_mean']
    ranks={k:v['positive_ranks'] for k,v in nomination['methods'].items()}
    panels=[json.loads(read(ROOT/'experiment-02'/(name+'-evaluation.json'))) for name in
        ['primary-1729','replay-1729','seed-2718','seed-31415','short-1729']]
    checkpoints=[json.loads(read(ROOT/'experiment-02'/(name+'-checkpoint.json'))) for name in
        ['primary-1729','replay-1729','seed-2718','seed-31415','short-1729']]
    nonlinear_curves=[{'run_id':r['run_id'],'objective_increase_epochs':[s['epoch'] for s in r['steps']
        if s['train_objective_after']>s['train_objective_before']], 'selected_epoch':r['selected_epoch'],
        'actual_steps':r['completed_optimizer_steps']} for r in checkpoints]
    status={'schema':'terminal-richer-ir-improvement-status@1','completed_milestone':True,
        'selected_run':'experiment-02','sources':5,'functions':28,'split_counts':result['split_counts'],
        'training_only_feature_columns':266,'trained_numeric_modalities':['ast','calls','interfaces','literals',
            'references','scopes','symbols','types'],
        'untrained_modalities_retained_as_source_bound_residuals':['effects','imports','diagnostics'],
        'latent_width':16,'parameter_count':checkpoints[0]['parameter_count'],'actual_optimizer_updates':272,
        'failed_pretraining_attempt_updates':0,'same_seed_full_optimizer_and_numerical_replay':True,
        'native_shared_admission':True,'native_current_head':result['native_head'],
        'coverage':result['coverage'],'heldout_reconstruction':evaluation,
        'empirical_mse_improvement_over_same_seed_untrained':1-learned['mse']/untrained['mse'],
        'learned_mse_better_than_train_mean':learned['mse']<mean['mse'],
        'learned_mse_better_than_train_svd':learned['mse']<svd['mse'],
        'learned_macro_modality_mse_better_than_train_svd':learned['macro_modality_mse']<svd['macro_modality_mse'],
        'svd_basis_count':panels[0]['svd_basis_count'],'svd_training_numerical_rank':panels[0]['svd_training_numerical_rank'],
        'seed_eval_mse':{p['run_id']:p['panels']['evaluation']['learned']['mse'] for p in panels},
        'learning_curves':nonlinear_curves,'authored_alignment_query_ranks':ranks,
        'authored_query_oov_atoms':nomination['query']['oov_atoms'],'query_count':1,
        'learned_latent_advantage_over_structural_ranking_demonstrated':False,
        'neural_candidate_promoted':False,'ready_for_supervisor_default':False,
        'promotion_decision':'retain advisory artifact; SVD wins reconstruction and raw/graph ranking already ranks the single positive first',
        'metadata_original_record_counts':result['metadata']['family_counts'],
        'metadata_losslessly_hydrated_and_cold_reopened':True,'unique_selected_tests':83,
        'genuine_negative_controls':faults['controls'],'all_original_fault_bodies_restored':True,
        'cold_after_faults_qualified':True,'new_lean_compilations':0,
        'previous_sealed_math_proof_preserved':'one source-bound g64 alignment fragment; seven mathematical theorems, two false controls',
        'proof_applies_to_learned_decoder':False,'source_body_execution':False,
        'official_terminal_bench_harness_executed':False,'native_full_supervisor_invoked':False,**FALSE}
    write(ROOT/'improvement-status-01.json',status)
    plan={'schema':'terminal-codebase-intent-ir-improvement-plan@4',
        'evidence_status':'genuine multi-modality lossy feature training; empirical baseline comparison; all learned evidence candidate-only',
        'next_work':[
            {'priority':1,'id':'reversible-current-source-capsules-and-token-evaluation',
             'reason':'learned reconstruction loses to training-only SVD and adds no recall on one authored alignment query',
             'implementation':['Build deterministic capsules from current native DuckDB/DuckLake indexes and exact typed sidecars.',
                'Keep source spans, interface/effect assumptions, proof-scope receipts and unknown requirement residuals recoverable.',
                'Use raw structural ranking and conditional exact proof lookup as selection gates; never omit an unresolved requirement because a learned score is low.',
                'Implement reversible identifier aliases and syntax-safe minification with expansion maps; retain original bytes as the validation owner.',
                'Run paired supervisor/Terminal Bench paths on the same frozen tasks and model configuration.'],
             'acceptance':['Count setup, full input/history, retrieval, capsule expansion, retries, tool outputs and generated tokens.',
                'Use provider actual usage for savings claims; separately report local token estimates.',
                'Require paired task outcomes, action validity, stale-source refusals and complete residual retention before enabling compression.']},
            {'priority':2,'id':'discrete-typed-codebase-ir-decoder-and-binding-semantics',
             'implementation':['Define constrained native AST/ProgramIR productions preserving variable binding, field order, exact literals, types, effects and control flow.',
                'Retain every unsupported construction and out-of-vocabulary atom with source provenance.',
                'Train typed discrete heads on a larger declared public corpus with immutable task-exclusive splits; keep evaluation unused for vocabulary, gradients and selection.',
                'Compare raw structural extraction, same-seed untrained, training-only mean/SVD and existing 44-feature baseline under matching metrics.'],
             'acceptance':['Exact typed reconstruction requires byte/identity/reference-valid replay, not continuous MSE.',
                'Demonstrate contract and intent retrieval on multiple predeclared queries with interface/effect-sensitive distractors and seed variation.',
                'Online adaptation must preserve task role ancestry, source head bindings, optimizer receipts and all spent work.']},
            {'priority':3,'id':'logic-family-lowering-and-source-model-claims',
             'implementation':['Project only supported decoded candidates into the actual native logic-family modules.',
                'Extend closed semantics profiles separately for positive division, bitwise operations, control flow and effects.',
                'Compile each supported profile through its actual checker and Lean with rejected false formulas and retained diagnostics.',
                'Bind proof cache records to exact source/head, target, compiler, checker, assumptions and artifacts; invalidate reverse dependencies when any component changes.'],
             'acceptance':['Learned vectors and successful parsers remain candidate evidence.',
                'Distinguish kernel-checked modeled fragment properties from parser correctness, CPython/runtime equivalence and whole-program behavior.']},
            {'priority':4,'id':'complete-intent-ir-and-supervisor-task-coverage',
             'implementation':['Decode full instructions into source-span-accounted goals, guards, prohibitions, effects, action/control requirements and numeric bounds.',
                'Match these requirements against current interfaces/effects/graph/contracts and preserve unresolved spans.',
                'Feed only source-bound candidate nominations to the actual ipfs_accelerate_py planner; require fresh native admission and actual coverage checks.'],
             'acceptance':['Partial manually authored queries cannot qualify benchmark intent understanding or full task satisfaction.',
                'Qualify complete behavior through actual task execution and official harness results.']},
            {'priority':5,'id':'durable-budgets-and-honest-convergence-evidence',
             'implementation':['Integrate persistent per-task work counters with original native leases across workers, failures and reboot.',
                'Preserve receipts immediately after every optimizer update, including work on rejected or interrupted candidates.',
                'Report finite empirical learning curves and seed/heldout behavior independently of mathematical convergence theorems.'],
             'acceptance':['Loss improvement over finite steps is not a proof of optimizer convergence.',
                'Any optimizer theorem must state the actual algorithm and objective assumptions; it cannot establish task completion or semantic equivalence.']}
        ],'measured_decision':status['promotion_decision'],**FALSE}
    write(ROOT/'follow-up-plan-01.json',plan)
    predecessor_inputs()
    # Discover only this new owned stage; never traverse Git metadata or follow symlinks.
    files=[]
    for base,dirs,names in os.walk(ROOT,followlinks=False):
        dirs[:]=[name for name in dirs if name not in {'.git','__pycache__','.pytest_cache'}]
        for name in names:
            path=Path(base)/name
            if path.is_symlink():raise ValueError('unexpected successor symlink')
            files.append(path.relative_to(ROOT).as_posix())
    config={'schema':'terminal-codebase-ir-evidence-selection@1','root':str(ROOT),
        'files':sorted(files+['seal-config-01.json']),'selection_scope':'owned_public_richer_training_artifacts',
        'excluded_git_metadata':True,'symlink_targets_opened':False,'proof_authority':False}
    write(ROOT/'seal-config-01.json',config)
    from seal_training_evidence import seal
    sealed=seal(config,ROOT/'evidence-manifest.json');seal(config,ROOT/'evidence-manifest.json',verify=True)
    print(json.dumps({'sealed':True,'file_count':sealed['file_count'],'bytes':sealed['total_bytes'],
        'file_set_sha256':sealed['file_set_sha256'],'optimizer_updates':272,'tests':83,
        'neural_candidate_promoted':False}))

if __name__=='__main__':main()
