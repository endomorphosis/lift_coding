import copy
import pytest
from evidence_io import FALSE
from run_successor import POLICY,coverage,validate_summary
from run_successor import check_lease

@pytest.fixture
def evidence():
    row={'split':'train','atom_counts':{'ast|x':1},'known_atom_mass':1,'unknown_atom_mass':0}
    targets={'feature_names':['ast|x'],'rows':[row],'split_counts':{'train':1,'validation':0,'evaluation':0}}
    runs=[{'completed_optimizer_steps':64}]*4+[{'completed_optimizer_steps':16}]
    panels=[{'panels':{'evaluation':{'learned':{'mse':.1}}}}]
    structural={'head':{'generation':1}};metadata={'complete_record_reconstruction':True}
    result={'schema':'terminal-richer-typed-ir-training-experiment@1','completed':True,'policy':POLICY,
        'feature_width':1,'latent_width':16,'split_counts':targets['split_counts'],'coverage':coverage(targets),
        'optimizer_steps':272,'same_seed_full_replay':True,'primary_evaluation':panels[0]['panels']['evaluation'],
        'metadata':metadata,'native_head':structural['head'],'native_structural_current_at_final_observation':True,
        'artifact_pins':[],'nomination_report_sha256':'0'*64,'source_execution':False,
        'native_full_supervisor_invoked':False,'official_terminal_bench_harness_executed':False,
        'peak_rss_kib':1,'seconds':1.,**FALSE}
    return result,targets,runs,panels,structural,metadata

def test_complete_authored_result(evidence):validate_summary(*evidence)

@pytest.mark.parametrize('field,value', [('optimizer_steps',271),('feature_width',44),('latent_width',8),
    ('optimizer_steps',True),('native_head',{'generation':2}),('primary_evaluation',{}),('metadata',{}),
    ('split_counts',{}),('coverage',{}),('source_model_equivalence_proved',True),
    ('asymptotic_optimizer_convergence_proved',True),('full_task_satisfaction',True),
    ('provider_token_savings_measured',True),('native_full_supervisor_invoked',True)])
def test_result_headline_drift_rejected(evidence,field,value):
    evidence=copy.deepcopy(evidence);evidence[0][field]=value
    with pytest.raises(ValueError):validate_summary(*evidence)

def test_extra_result_authority_rejected(evidence):
    evidence[0]['new_proof_authority']=True
    with pytest.raises(ValueError,match='closed result'):validate_summary(*evidence)

def test_native_cancellation_property_and_refusal():
    from types import SimpleNamespace
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.resource_scheduler import ResourceLease,LeaseCancelledError
    assert isinstance(ResourceLease.cancelled,property)
    check_lease(SimpleNamespace(cancelled=False))
    with pytest.raises(LeaseCancelledError):check_lease(SimpleNamespace(cancelled=True))
