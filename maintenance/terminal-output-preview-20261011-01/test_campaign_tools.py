"""Authored controls and receipt projections; no provider calls or task files."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
SOURCE = Path('/home/barberb/lift_coding_worktrees/indexed-worker-context-20261011')
sys.path.insert(0, str(SOURCE))


def load(name, filename):
    spec=importlib.util.spec_from_file_location(name, ROOT/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


prepare=load('authored_prepare','prepare-campaign.py')
collector=load('authored_collector','collect-benchmark.py')
from benchmarks.agent_supervisor.container_coding.terminal_tool_output_policy import tool_output_dispatch_observation
from ipfs_accelerate_py.agent_supervisor.runtime.codex_interaction_telemetry import build_interaction_telemetry
from ipfs_accelerate_py.agent_supervisor.runtime.tool_output_policy import create_binding


def report(mode='artifact-preview@1', adopted=True):
    calls=[]
    for phase in ('planning','coding'):
        values=dict(input_tokens=100, cached_input_tokens=40, output_tokens=10, total_tokens=110)
        records=[dict(type='event_msg',payload=dict(type='token_count',info=dict(total_token_usage=values)))]
        native=dict(schema='native-codex-cumulative-usage@1',usage_available=True,
            task_complete_observed=True,cache_included_in_input=True,thread_id=phase+'-session',usage=values,
            interaction_telemetry=build_interaction_telemetry(records,completed=True,malformed=0))
        call=dict(phase=phase,purpose=phase,provider='codex_cli',model='gpt-6.1-sol',invocation_id=phase+'-invocation',
            workspace='/authored/candidate',model_prompt_sha256='a'*64,native_prompt_sha256='a'*64,model_prompt_bytes=2300,native_rollout_usage=native)
        if phase=='coding' and mode!='legacy':
            binding=create_binding(workspace=Path('/authored/candidate'))
            usage={key:0 for key in collector.HELPER_COUNTS}
            usage.update(schema='tool-output-artifact-usage@1',capture_count=int(adopted),complete_capture_count=int(adopted),
                raw_content_exported=False,worker_owned_observation=True,proof_authority=False,completion_authority=False,
                helper_operations_observed=adopted,store_cleanup_complete=True,artifacts_retained_after_invocation=False)
            binding['usage']=usage;call['tool_output_policy']=binding
        calls.append(call)
    result=dict(task_completed=True,worker_cleanup_returncode=0,remaining_processes=0,provider_invocations=calls,
        planning=dict(model_request_sha256='a'*64),
        context_input_audit=dict(status='verified_all_observed_model_inputs',all_observed_coding_inputs_verified=True,
            read_errors=[],coding_receipts_seen=1,usable_coding_receipts=1,
            invocations=[dict(invocation_id='coding-invocation',status='verified_exact_model_input',model_input_verified=True)],
            matches=[dict(invocation_id='coding-invocation',model_input_verified=True,model_prompt_sha256='a'*64,model_prompt_bytes=2300,
                model_input_checks=dict(model_prompt_sha256=True,model_prompt_bytes=True,workspace_advisory_sha256=True,
                    workspace_advisory_bytes=True,tool_output_helper_source=True))]))
    if mode!='legacy':result['tool_output_policy']=mode
    return result


def project(value, mode='artifact-preview@1'):
    return collector.project_report(value,mode,tool_output_dispatch_observation)


def test_default_plan_is_closed_abba_and_executes_nothing():
    assert [(r['name'],r['tool_output_policy']) for r in prepare.planned_trials()]==[
        ('mjcf-legacy-01','legacy'),('mjcf-preview-01','artifact-preview@1'),
        ('mjcf-preview-02','artifact-preview@1'),('mjcf-legacy-02','legacy')]
    assert prepare.skeleton()['max_concurrent_trials']==1
    assert prepare.skeleton()['live_token_savings_claimed_before_execution'] is False


def test_config_normalization_removes_only_declared_axes():
    config=dict(job_name='A',jobs_dir='/a',agents=[dict(kwargs=dict(tool_output_policy='legacy',semantic_context_profile='indexed-default@1',runtime_archive='/fixed'))],
        retry=dict(exclude_exceptions=['b','a']),environment=dict(cpu=5))
    selected=copy.deepcopy(config);selected['agents'][0]['kwargs']['tool_output_policy']='artifact-preview@1';selected.update(job_name='B',jobs_dir='/b')
    assert prepare.normalize_config(config)==prepare.normalize_config(selected)
    assert config['retry']['exclude_exceptions']==['b','a']
    selected['environment']['cpu']=6
    assert prepare.normalize_config(config)!=prepare.normalize_config(selected)
    selected=copy.deepcopy(config);selected['agents'][0]['kwargs']['semantic_context_profile']='foreign'
    assert prepare.normalize_config(config)!=prepare.normalize_config(selected)


def test_no_protocol_is_pending(tmp_path):
    result=collector.collect(tmp_path,lambda *_: (_ for _ in ()).throw(AssertionError('no dispatch expected')))
    assert result['status']=='pending' and result['trials']==[] and result['provider_calls_by_collector']==0


@pytest.mark.parametrize('adopted',[True,False])
def test_selected_advisory_qualifies_and_nonadoption_is_explicit(adopted):
    result=project(report(adopted=adopted))
    assert result['problems']==[]
    assert result['native_usage_complete'] is True
    assert result['complete_tokens']['total_tokens']==220
    assert result['uncached_input_tokens']==120
    assert result['invocations'][1]['helper_capture_observed'] is adopted


def test_legacy_control_has_no_helper_observation():
    result=project(report('legacy'),'legacy')
    assert result['problems']==[]
    assert result['invocations'][1]['helper_usage'] is None


@pytest.mark.parametrize('mutation',['incomplete_native','duplicate_id','duplicate_session','cache_overflow','missing_audit',
    'changed_advisory','cleanup_failed','missing_helper_usage','planning_policy','unreceipted','tool_secret'])
def test_incomplete_or_unbound_evidence_stays_separate(mutation):
    value=report();row=value['provider_invocations'][1]
    if mutation=='incomplete_native':row['native_rollout_usage']['task_complete_observed']=False
    elif mutation=='duplicate_id':row['invocation_id']=value['provider_invocations'][0]['invocation_id']
    elif mutation=='duplicate_session':row['native_rollout_usage']['thread_id']='planning-session'
    elif mutation=='cache_overflow':row['native_rollout_usage']['usage']['cached_input_tokens']=101
    elif mutation=='missing_audit':value.pop('context_input_audit')
    elif mutation=='changed_advisory':row['tool_output_policy']['instruction_sha256']='0'*64
    elif mutation=='cleanup_failed':row['tool_output_policy']['usage']['store_cleanup_complete']=False
    elif mutation=='missing_helper_usage':row['tool_output_policy'].pop('usage')
    elif mutation=='planning_policy':value['provider_invocations'][0]['tool_output_policy']={}
    elif mutation=='unreceipted':value['unreceipted_provider_attempt']=True
    elif mutation=='tool_secret':row['tool_output_policy']['usage']['secret']='DO_NOT_EXPORT_AUTHORED_CONTENT'
    result=project(value)
    assert 'DO_NOT_EXPORT_AUTHORED_CONTENT' not in json.dumps(result)
    if mutation in {'incomplete_native','duplicate_id','duplicate_session','cache_overflow','unreceipted'}:
        assert result['native_usage_complete'] is False and result['complete_tokens']['total_tokens'] is None
    elif mutation!='tool_secret':assert result['problems']


def test_failed_outcome_keeps_observed_native_cost():
    value=report();value['task_completed']=False
    result=project(value)
    assert result['task_completed'] is False and result['complete_tokens']['total_tokens']==220


def test_means_retain_failed_and_nonadopted_trials():
    rows=[]
    for item, tokens in zip(prepare.planned_trials(),[100,80,120,100]):
        rows.append(dict(name=item['name'],requested_policy=item['tool_output_policy'],repeat=item['repeat'],state='finished',
            comparison_eligible=True,native_usage_complete=True,complete_tokens={key:tokens for key in collector.TOKENS},
            official_success=False,invocations=[]))
    result=collector.summarize(rows)
    assert result['mean_total_token_change_percent']==0
    assert [pair['total_token_change_percent'] for pair in result['pairs']]==[-20,20]
    assert result['arms']['artifact-preview@1']['successes']==0
    assert result['token_savings_established'] is False


def test_unknown_usage_blocks_mean_without_invented_zero():
    rows=[]
    for item in prepare.planned_trials():
        rows.append(dict(name=item['name'],requested_policy=item['tool_output_policy'],repeat=item['repeat'],state='pending',
            comparison_eligible=False,native_usage_complete=False,complete_tokens=dict.fromkeys(collector.TOKENS)))
    result=collector.summarize(rows)
    assert result['mean_total_token_change_percent'] is None
    assert result['arms']['artifact-preview@1']['means']['total_tokens'] is None


@pytest.mark.parametrize('text',['{"a":1,"a":2}','{"a":NaN}','{"a":1e309}'])
def test_malformed_json_is_rejected(tmp_path,text):
    path=tmp_path/'bad.json';path.write_text(text)
    with pytest.raises(ValueError):collector.read_json(path)


def authored_campaign(root):
    protocol=prepare.skeleton();protocol.update(source_commit='1'*40,archive_sha256='2'*64)
    for index, selected in enumerate(protocol['trials']):
        folder=root/'trials'/selected['name'];folder.mkdir(parents=True)
        kwargs=dict(runtime_archive='/authored/archive',semantic_context_profile='indexed-default@1')
        if selected['tool_output_policy']!='legacy':kwargs['tool_output_policy']=selected['tool_output_policy']
        config=dict(job_name=selected['name'],jobs_dir=str(folder/'jobs'),agents=[dict(kwargs=kwargs)])
        raw=json.dumps(config).encode();(folder/'config.json').write_bytes(raw)
        selected['config_sha256']=collector.telemetry.sha(raw)
        prepared=dict(task='tune-mjcf',archive_sha256='2'*64,task_input_sha256={'instruction.md':'3'*64},
            host_source_sha256={'authored.py':'4'*64},model='gpt-6.1-sol',reasoning_effort='high',cli_version='0.160.0',
            config_sha256=selected['config_sha256'],semantic_context_profile='indexed-default@1',
            resource_profile='source384-5cpu-16gib-extended@1')
        if selected['tool_output_policy']!='legacy':prepared['tool_output_policy']=selected['tool_output_policy']
        (folder/'preparation.json').write_text(json.dumps(prepared))
        frozen={key:prepared[key] for key in ('archive_sha256','task_input_sha256','host_source_sha256')}
        frozen['normalized_configuration']=prepare.normalize_config(config)
        protocol['preparations'].setdefault('tune-mjcf',frozen)
        authored=report(selected['tool_output_policy'],adopted=index==1)
        for call in authored['provider_invocations']:
            call['invocation_id']=selected['name']+'-'+call['invocation_id']
            call['native_rollout_usage']['thread_id']=selected['name']+'-'+call['native_rollout_usage']['thread_id']
        for kind in ('invocations','matches'):
            authored['context_input_audit'][kind][0]['invocation_id']=selected['name']+'-coding-invocation'
        if index==2:authored['task_completed']=False
        receipt=dict(task='tune-mjcf',original_task_inputs_unchanged=True,native_job_result_present=True,trials=[dict(
            task='terminal-bench/tune-mjcf',exact_trial_task_matches=True,reward={'reward':0.0 if index==2 else 1.0},
            supervisor=authored,durations_seconds={'agent_execution':12.5})])
        (folder/'receipt.json').write_text(json.dumps(receipt))
    (root/'comparison-protocol.json').write_text(json.dumps(protocol))
    return protocol


def test_complete_authored_campaign_retains_failure_and_nonadoption(tmp_path):
    authored_campaign(tmp_path)
    result=collector.collect(tmp_path,tool_output_dispatch_observation)
    assert result['status']=='complete'
    assert result['all_trials_comparison_eligible'] is True
    assert result['mean_total_token_change_percent']==0.0
    assert result['arms']['artifact-preview@1']['successes']==1
    assert result['arms']['artifact-preview@1']['helper_capture_trials']==1
    assert result['arms']['artifact-preview@1']['mean_durations_seconds']['agent_execution']==12.5
    assert result['trials'][2]['official_reward']==0.0
    assert result['trials'][2]['complete_tokens']['total_tokens']==220
    assert result['trials'][2]['helper_capture_count']==0


@pytest.mark.parametrize('mutation',['envelope_task','preparation_task','native_task','foreign_namespace','missing_namespace','exact_flag'])
def test_task_identity_checks_both_receipt_scopes(tmp_path,mutation):
    authored_campaign(tmp_path)
    path=tmp_path/'trials/mjcf-legacy-01'/('preparation.json' if mutation=='preparation_task' else 'receipt.json')
    value=json.loads(path.read_text())
    if mutation in ('envelope_task','preparation_task'):value['task']='foreign-task'
    elif mutation=='native_task':value['trials'][0]['task']='terminal-bench/foreign-task'
    elif mutation=='foreign_namespace':value['trials'][0]['task']='foreign/tune-mjcf'
    elif mutation=='missing_namespace':value['trials'][0]['task']='tune-mjcf'
    else:value['trials'][0]['exact_trial_task_matches']=False
    path.write_text(json.dumps(value))
    result=collector.collect(tmp_path,tool_output_dispatch_observation)
    assert result['all_trials_comparison_eligible'] is False
    assert 'trial_task_mismatch' in result['trials'][0]['problems']
    assert result['trials'][0]['complete_tokens']['total_tokens']==220
    assert result['trials'][1]['comparison_eligible'] is True


def test_cross_trial_native_session_reuse_disqualifies_comparison(tmp_path):
    authored_campaign(tmp_path)
    folders=[tmp_path/'trials'/row['name'] for row in prepare.planned_trials()]
    earlier=json.loads((folders[0]/'receipt.json').read_text())
    later=json.loads((folders[1]/'receipt.json').read_text())
    later['trials'][0]['supervisor']['provider_invocations'][0]['native_rollout_usage']['thread_id']=earlier['trials'][0]['supervisor']['provider_invocations'][0]['native_rollout_usage']['thread_id']
    (folders[1]/'receipt.json').write_text(json.dumps(later))
    result=collector.collect(tmp_path,tool_output_dispatch_observation)
    assert result['cross_trial_identities_unique'] is False
    assert result['all_trials_comparison_eligible'] is False
    assert result['mean_total_token_change_percent'] is None


def test_config_drift_preserves_cost_but_prevents_comparison(tmp_path):
    authored_campaign(tmp_path)
    path=tmp_path/'trials/mjcf-preview-01/config.json'
    config=json.loads(path.read_text());config['unexpected_provider_option']=True
    path.write_text(json.dumps(config))
    result=collector.collect(tmp_path,tool_output_dispatch_observation)
    assert result['all_trials_comparison_eligible'] is False
    assert result['trials'][1]['native_usage_complete'] is True
    assert result['trials'][1]['complete_tokens']['total_tokens']==220
    assert 'normalized_configuration' in result['trials'][1]['problems']


def test_missing_telemetry_never_becomes_zero_byte_measurement():
    value=report();value['provider_invocations'][1]['native_rollout_usage'].pop('interaction_telemetry')
    result=project(value)
    assert result['native_usage_complete'] is True
    assert result['all_tool_censuses_complete'] is False
    assert result['observed_tool_output_bytes'] is None
    assert result['invocations'][1]['tool_observations']['retained_tool_output_byte_lower_bound'] is None


def test_planning_binding_drift_does_not_erase_usage():
    value=report();value['planning']['model_request_sha256']='0'*64
    result=project(value)
    assert result['complete_tokens']['total_tokens']==220
    assert 'planning_input_binding_unverified' in result['problems']


@pytest.mark.parametrize('target',['receipt.json','config.json','preparation.json'])
def test_malformed_trial_artifact_does_not_drop_other_trials(tmp_path,target):
    authored_campaign(tmp_path)
    (tmp_path/'trials/mjcf-preview-01'/target).write_text('{partial')
    result=collector.collect(tmp_path,tool_output_dispatch_observation)
    assert len(result['trials'])==4
    assert result['trials'][1]['state']=='unverified'
    assert result['trials'][1]['complete_tokens']['total_tokens'] is None
    assert result['trials'][0]['complete_tokens']['total_tokens']==220
    assert result['trials'][2]['complete_tokens']['total_tokens']==220
    assert result['mean_total_token_change_percent'] is None


@pytest.mark.parametrize('field,value',[('capture_count',33),('artifact_count',33),('store_bytes',32*1024**2+1),
    ('read_count',100001),('read_bytes',1024**3+1),('observed_bytes',8*1024**2+65537),
    ('preview_bytes',8193),('retained_bytes',8*1024**2+1),('omitted_bytes',1)])
def test_impossible_helper_counts_remain_unknown(field,value):
    authored=report();authored['provider_invocations'][1]['tool_output_policy']['usage'][field]=value
    result=project(authored)
    assert result['helper_usage_and_cleanup_verified'] is False
    assert result['invocations'][1]['helper_usage_valid'] is False
    assert result['helper_capture_count'] is None
    assert result['invocations'][1]['helper_counts_worker_owned'] is True
