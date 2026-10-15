import copy
import math
import pytest
from typed_training import fit, evaluate, validate_checkpoint, matrix, modalities, CONFIG

def targets():
    rows=[]
    for index in range(28):
        split='train' if index<8 else 'validation' if index==8 else 'evaluation'
        rows.append({'unit_id':str(index),'split':split,'task_id':split,
            'features':[1., (index%3)/3., .5, .25]})
    return {'feature_names':['ast|a','ast|b','effects|a','effects|b'],'rows':rows}

@pytest.fixture(scope='module')
def fitted():
    t=targets();return t,fit(t,run_id='authored',seed=123,epochs=3)

def test_actual_optimizer_and_replay(fitted):
    t,s=fitted;r=fit(t,run_id='authored',seed=123,epochs=3)
    assert r==s
    assert len(s['steps'])==3
    assert all(x['weights_before_sha256']!=x['weights_after_sha256'] for x in s['steps'])
    assert [x['actual_optimizer_tensor_steps'] for x in s['steps']]==[[1]*4,[2]*4,[3]*4]

def test_immediate_receipts_retained_before_interrupt():
    receipts=[]
    def interrupt():
        if receipts:raise RuntimeError('authored cancellation')
    with pytest.raises(RuntimeError,match='cancellation'):
        fit(targets(),run_id='interrupted',seed=123,epochs=3,checkpoint=interrupt,step_observer=receipts.append)
    assert len(receipts)==1 and receipts[0]['actual_optimizer_tensor_steps']==[1]*4
    assert receipts[0]['parameters_finite'] is True

def test_heldout_changes_do_not_change_fit(fitted):
    t,s=fitted;t=copy.deepcopy(t)
    for row in t['rows']:
        if row['split']=='evaluation':row['features']=[0.,100.,0.,500.]
    r=fit(t,run_id='authored',seed=123,epochs=3)
    assert r['bindings']!=s['bindings']
    for key in ['parameters','optimizer_moments','steps','selected_epoch','initial_parameters']:
        assert r[key]==s[key]

@pytest.mark.parametrize('field', ['proof_authority','execution_authority','full_task_satisfaction',
                                   'asymptotic_optimizer_convergence_proved'])
def test_promoted_checkpoint_rejected(fitted,field):
    t,s=fitted;s=copy.deepcopy(s);s[field]=True
    with pytest.raises(ValueError,match='unpromoted'):validate_checkpoint(s,t)

def test_weight_tamper_rejected(fitted):
    t,s=fitted;s=copy.deepcopy(s);s['parameters'][0][0][0]+=.1
    with pytest.raises(ValueError,match='numerical binding'):validate_checkpoint(s,t)

def test_vocabulary_tamper_rejected(fitted):
    t,s=fitted;t=copy.deepcopy(t);t['feature_names'][0]='ast|aa'
    with pytest.raises(ValueError,match='binding'):validate_checkpoint(s,t)

def test_split_leakage_rejected(fitted):
    t,s=fitted;t=copy.deepcopy(t);t['rows'][0]['task_id']='evaluation'
    with pytest.raises(ValueError,match='split leakage'):validate_checkpoint(s,t)

def test_missing_optimizer_moment_rejected(fitted):
    t,s=fitted;s=copy.deepcopy(s);s['optimizer_moments'].pop()
    with pytest.raises(ValueError,match='four optimizer'):validate_checkpoint(s,t)

@pytest.mark.parametrize('field', ['selected_epoch','completed_optimizer_steps','seed'])
def test_boolean_optimizer_integer_rejected(fitted,field):
    t,s=fitted;s=copy.deepcopy(s);s[field]=True
    with pytest.raises(ValueError,match='exact bounded'):validate_checkpoint(s,t)

def test_nan_initial_validation_rejected(fitted):
    t,s=fitted;s=copy.deepcopy(s);s['initial_validation_objective']=float('nan')
    with pytest.raises(ValueError,match='finite nonnegative'):validate_checkpoint(s,t)

def test_changed_initial_seed_rejected(fitted):
    t,s=fitted;s=copy.deepcopy(s);s['seed']+=1
    with pytest.raises(ValueError,match='seeded initial'):validate_checkpoint(s,t)

def test_new_checkpoint_claim_rejected(fitted):
    t,s=fitted;s=copy.deepcopy(s);s['whole_python_equivalence']=True
    with pytest.raises(ValueError,match='unpromoted'):validate_checkpoint(s,t)

def test_negative_squared_moment_rejected(fitted):
    t,s=fitted;s=copy.deepcopy(s);s['optimizer_moments'][0]['exp_avg_sq'][0][0]=-1.
    with pytest.raises(ValueError,match='negative squared'):validate_checkpoint(s,t)

def test_incomplete_step_ledger_rejected(fitted):
    t,s=fitted;s=copy.deepcopy(s);s['steps'].pop()
    with pytest.raises(ValueError,match='complete bounded'):validate_checkpoint(s,t)

def test_evaluation_controls(fitted):
    t,s=fitted;p=evaluate(s,t)
    assert p['panels']['evaluation']['deterministic_features']['mse']==0.
    assert p['svd_fitted_training_only'] is True
    assert p['evaluation_used_for_fit_or_selection'] is False
    assert p['panels']['evaluation']['learned']['exact_source_reconstruction'] is False

@pytest.mark.parametrize('value', [float('inf'),float('nan'),True,'1'])
def test_matrix_nonfinite_and_wrong_types_rejected(value):
    with pytest.raises(ValueError,match='finite exact'):matrix([[value]],1)

def test_noncanonical_columns_rejected():
    with pytest.raises(ValueError,match='canonical'):modalities(['effects|b','ast|a'])
