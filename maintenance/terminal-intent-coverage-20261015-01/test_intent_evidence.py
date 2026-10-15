"""Reject false completion, work counters and changes to original evidence."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import pytest
from intent_io import ROOT,FALSE,wire,sha,inputs
from intent_run import POLICY,FILES
from intent_verify import validate_result,artifact_check,fault_precondition

LEAN_LABELS=('headless-terminal','feal-differential-cryptanalysis','break-filter-js-from-html',
    'llm-inference-batching-scheduler','false-type-control')

def _authored_artifacts(output,result):
    """Inert custody bytes only; these do not pretend to be compiler evidence."""
    (output/'lean').mkdir()
    names=[*FILES,'lean/report.json']
    for label in LEAN_LABELS:
        names.extend(['lean/'+label+'.lean','lean/'+label+'-process.json'])
    pins=[]
    for name in names:
        raw=wire({'authored_custody_fixture':name});(output/name).write_bytes(raw)
        pins.append({'relative_path':name,'bytes':len(raw),'sha256':sha(raw)})
    result['artifact_pins']=sorted(pins,key=lambda row:row['relative_path'])

def _authored_fault(result,run,result_raw):
    cases=['changed_instruction','omitted_instruction_unit','forged_grounding',
        'projection_authority_promoted','source_changed_at_exit']
    return {'schema':'terminal-intent-coverage-faults@1','qualified':True,'selected_run':run,
        'selected_result_sha256':sha(result_raw),'native_head':result['native_head'],
        'controls':[{'case':case,'rejected':True,
            'exception_class':'StaleCodebaseError' if case==cases[-1] else 'ValueError',
            'message':'authored parser fixture, no actual fault execution claimed'} for case in cases],
        'source_restored':True,'source_body_execution':False,'external_provider_calls':0,
        'new_optimizer_updates':0,**FALSE}

@pytest.fixture
def authored_result():
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
    cid=cid_for_structured({'schema':'authored-result-test@1'})
    head=CodebaseHead(repository_id='authored-result',generation=1,manifest_cid=cid,snapshot_cid=cid,
        ast_revision_id='rev:authored-result:snapshot:'+cid,receipt_cid=cid).to_dict()
    return {'schema':'terminal-source-bound-intent-experiment@1','completed':True,'policy':deepcopy(POLICY),
        'native_head':head,'source_count':5,'task_count':4,'new_optimizer_updates':0,'external_provider_calls':0,
        'source_body_execution':False,'metadata_original_record_counts':{'ast':5},'native_capsule_inventory':{'capsules':57},
        'artifact_pins':[],'seconds':1.25,'peak_rss_kib':123,**FALSE}

def test_authored_result_validation_grants_no_proof_or_completion(authored_result):
    validate_result(authored_result)
    assert authored_result['full_task_satisfaction'] is False
    assert authored_result['source_model_equivalence_proved'] is False

@pytest.mark.parametrize('key',list(FALSE)+['source_body_execution'])
def test_unobserved_authority_promotion_rejected(authored_result,key):
    authored_result[key]=True
    with pytest.raises(ValueError):validate_result(authored_result)

@pytest.mark.parametrize('key,value',[('source_count',True),('task_count',4.0),('new_optimizer_updates',False),
    ('external_provider_calls',0.0),('seconds',float('nan')),('seconds',float('inf')),('peak_rss_kib',True)])
def test_numeric_aliases_and_nonfinite_diagnostics_rejected(authored_result,key,value):
    authored_result[key]=value
    with pytest.raises(ValueError):validate_result(authored_result)

def test_unknown_result_field_cannot_add_execution_authority(authored_result):
    authored_result['validated_original_task']=True
    with pytest.raises(ValueError):validate_result(authored_result)

def test_selected_sealed_corpus_preserves_unicode_and_all_four_originals():
    corpus,bodies,instructions,lineage=inputs()
    assert len(corpus['tasks'])==4 and len(bodies)==5 and len(instructions)==4
    scheduler=instructions['llm-inference-batching-scheduler']
    assert len(scheduler)==4365 and len(scheduler.decode('utf-8'))==4346
    assert 'exactly once' in scheduler.decode() and 'unchanged' in scheduler.decode()

@pytest.mark.parametrize('damage',['body_changed','missing_pin','unknown_file','numeric_size'])
def test_core_artifact_custody_refuses_mutation(authored_result,damage):
    with tempfile.TemporaryDirectory(prefix='.authored-intent-custody-',dir=ROOT) as directory:
        output=Path(directory);_authored_artifacts(output,authored_result)
        artifact_check(output,authored_result)
        if damage=='body_changed':(output/FILES[0]).write_bytes(b'changed')
        elif damage=='missing_pin':authored_result['artifact_pins'].pop()
        elif damage=='unknown_file':
            p=output/'unexpected-private.key';p.write_bytes(b'authored-not-a-secret')
            authored_result['artifact_pins'].append({'relative_path':p.name,'bytes':21,'sha256':sha(p.read_bytes())})
        else:authored_result['artifact_pins'][0]['bytes']=float(authored_result['artifact_pins'][0]['bytes'])
        with pytest.raises(ValueError):artifact_check(output,authored_result)

@pytest.mark.parametrize('damage',['missing_dir','symlink_dir','unknown_label','private_key_json','missing_mandatory_leaf'])
def test_closed_mandatory_lean_custody_inventory(authored_result,damage):
    with tempfile.TemporaryDirectory(prefix='.authored-intent-lean-custody-',dir=ROOT) as directory:
        output=Path(directory);_authored_artifacts(output,authored_result)
        artifact_check(output,authored_result)
        if damage in {'missing_dir','symlink_dir'}:
            for path in (output/'lean').iterdir():path.unlink()
            (output/'lean').rmdir()
            authored_result['artifact_pins']=[r for r in authored_result['artifact_pins'] if not r['relative_path'].startswith('lean/')]
            if damage=='symlink_dir':
                (output/'authored-empty').mkdir();(output/'lean').symlink_to(output/'authored-empty',target_is_directory=True)
        elif damage=='missing_mandatory_leaf':
            name='lean/false-type-control-process.json';(output/name).unlink()
            authored_result['artifact_pins']=[r for r in authored_result['artifact_pins'] if r['relative_path']!=name]
        else:
            name='lean/'+('unknown-label-process.json' if damage=='unknown_label' else 'private-key.json')
            raw=wire({'authored':'not a secret'});(output/name).write_bytes(raw)
            authored_result['artifact_pins'].append({'relative_path':name,'bytes':len(raw),'sha256':sha(raw)})
            authored_result['artifact_pins'].sort(key=lambda r:r['relative_path'])
        with pytest.raises(ValueError):artifact_check(output,authored_result)

@pytest.mark.parametrize('key,value',[
    ('source_body_execution',0),('complete_original_instruction_bytes_required',1),
    ('native_original_task_coverage_expected',False),('manual_candidates_are_semantic_evidence',0)])
def test_policy_semantic_status_numeric_aliases_cannot_replace_declared_types(authored_result,key,value):
    authored_result['policy'][key]=value
    with pytest.raises(ValueError):validate_result(authored_result)

@pytest.mark.parametrize('family,key,value',[
    ('metadata_original_record_counts','ast',5.0),('metadata_original_record_counts','ast',True),
    ('native_capsule_inventory','capsules',57.0),('native_capsule_inventory','capsules',False)])
def test_metadata_counter_aliases_are_refused(authored_result,family,key,value):
    authored_result[family][key]=value
    with pytest.raises(ValueError):validate_result(authored_result)

@pytest.mark.parametrize('damage',['head_generation','missing_case','wrong_order','rejected_numeric_alias',
    'qualified_numeric_alias','source_restored_numeric_alias','counter_numeric_alias','native_owner_exception'])
def test_fault_precondition_binds_full_native_head_and_all_exact_controls(authored_result,damage):
    with tempfile.TemporaryDirectory(prefix='.authored-intent-fault-precondition-',dir=ROOT) as directory:
        output=Path(directory);result_raw=wire(authored_result)
        report=_authored_fault(authored_result,output.name,result_raw)
        target=output/'authored-fault.json';target.write_bytes(wire(report))
        # Product API deliberately permits only a root-local owned filename.
        import intent_verify
        original_root=intent_verify.ROOT
        try:
            intent_verify.ROOT=output
            fault_precondition(target.name,output=output,result=authored_result,result_raw=result_raw)
            if damage=='head_generation':report['native_head']={**report['native_head'],'generation':2}
            elif damage=='missing_case':report['controls'].pop()
            elif damage=='wrong_order':report['controls'][0],report['controls'][1]=report['controls'][1],report['controls'][0]
            elif damage=='rejected_numeric_alias':report['controls'][0]['rejected']=1
            elif damage=='qualified_numeric_alias':report['qualified']=1
            elif damage=='source_restored_numeric_alias':report['source_restored']=1
            elif damage=='counter_numeric_alias':report['external_provider_calls']=False
            else:report['controls'][-1]['exception_class']='ValueError'
            target.write_bytes(wire(report))
            with pytest.raises(ValueError):fault_precondition(target.name,output=output,result=authored_result,result_raw=result_raw)
        finally:intent_verify.ROOT=original_root

def test_finalizer_rejects_selected_producer_drift_before_any_publication(authored_result,monkeypatch):
    import finalize_stage
    import intent_verify
    import run_process
    args=SimpleNamespace(run='authored-run',regression='authored-tests',fault='authored-fault',cold='authored-cold')
    expected=[{'path':'/authored/public-producer.py','bytes':12,'sha256':'a'*64}]
    retained={args.run+'/result.json':authored_result,
        args.run+'-process-report.json':{},args.regression+'-process-report.json':{},
        args.fault+'-fault-report.json':{},args.fault+'-process-report.json':{},
        args.cold+'-cold-report.json':{},args.cold+'-process-report.json':{'after':expected}}
    monkeypatch.setattr(finalize_stage,'read',lambda path,maximum=0:wire(retained[Path(path).relative_to(ROOT).as_posix()]))
    # This is a pure early-guard test; no authored receipt reaches artifact/claim interpretation.
    monkeypatch.setattr(intent_verify,'artifact_check',lambda *a,**k:{})
    monkeypatch.setattr(run_process,'selected',lambda:[{**expected[0],'sha256':'b'*64}])
    monkeypatch.setattr(finalize_stage,'write',lambda *a,**k:pytest.fail('producer drift must refuse before publication'))
    with pytest.raises(ValueError,match='current selected producers differ'):
        finalize_stage.finalize(args)

def test_actual_native_current_owner_refuses_source_mutation_after_candidate_build(tmp_path,monkeypatch):
    """Real owner/SQL/CAS/context; an isolated authored sampler only for this unit test."""
    import subprocess
    import native_structural_ir
    from intent_source_mutation import owned_source_mutation
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import StaleCodebaseError
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.proof_resource_safety import ProofHostResources
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import GlobalResourceScheduler,ResourceSchedulerConfig
    from ipfs_accelerate_py.agent_supervisor.planning.structural_codebase_context import run_with_structural_codebase_context
    scheduler=GlobalResourceScheduler(ResourceSchedulerConfig.for_proof_host(
        state_path=tmp_path/'authored-unit-scheduler.json',
        proof_resource_sampler=lambda:ProofHostResources(8,8192,8192),auto_renew_leases=False))
    monkeypatch.setattr(native_structural_ir,'_scheduler',lambda:scheduler)
    with tempfile.TemporaryDirectory(prefix='.authored-intent-owner-',dir=ROOT) as directory:
        output=Path(directory);repository=output/'source';repository.mkdir()
        marker=output/'source-must-not-execute';raw=("from pathlib import Path\nPath("+repr(str(marker))+").write_text('executed')\n"
            "def authored(value):\n    return value + 1\n").encode()
        source=repository/'unit.py';source.write_bytes(raw)
        def git(*argv):
            subprocess.run(['git','-C',str(repository),*argv],stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=10)
        git('init','-q');git('add','--','unit.py')
        git('-c','user.name=Authored fixture','-c','user.email=fixture@invalid','commit','-qm','Authored source')
        structural=native_structural_ir.prepare_structural_ir(repository=repository,output=output/'structural',
            repository_id='authored:intent-current-owner',expected_sources={'unit.py':sha(raw)})
        head=CodebaseHead.from_dict(structural['head']);reached=[];returned=[]
        with native_structural_ir._owner(output/'structural',existing=True) as (index,_):
            with owned_source_mutation(source,raw) as mutation:
                def build(context):
                    reached.append(context.head.to_dict());mutation.apply()
                    return {'authored_candidate':'must not escape a stale owner'}
                with pytest.raises(StaleCodebaseError):
                    returned.append(run_with_structural_codebase_context(index,repository,build,
                        repository_id=head.repository_id,expected_head=head,scheduler=scheduler,memory_mb=256))
            assert reached==[head.to_dict()] and returned==[]
            assert source.read_bytes()==raw and not marker.exists()
            index.observe_current(repository,expected_head=head,scheduler=scheduler,memory_mb=256)
