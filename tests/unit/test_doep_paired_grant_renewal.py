"""Combined native broker renews each exact role once through multiple TTLs."""
from dataclasses import replace
import os
from types import SimpleNamespace

import pytest

from test_doep_default_grant_renewal import admitted


@pytest.fixture
def paired(admitted, tmp_path, monkeypatch):
    x=admitted
    from ipfs_accelerate_py.agent_supervisor.runtime import owner_merge_bootstrap_broker as native
    from ipfs_accelerate_py.agent_supervisor.task_sources import owner_merge_bootstrap as bundle
    from test.api.test_agent_supervisor_lgcvf_quack_successor import _lgcvf_test_execution_route_policy
    policy=_lgcvf_test_execution_route_policy(SimpleNamespace(LGCVF_TASK_ALIASES=('DOEP-001',)))
    x.broker.policy=policy
    x.owner.update(process_birth=x.birth.to_dict(),store_id='doep:test',database_uuid='uuid:task',
                   listen_uri='quack:127.0.0.1:41327')
    x.gateway.identity=dict(x.owner)
    queue_identity={**x.owner,'store_id':'queue:separate','database_uuid':'uuid:queue',
                    'server_id':'server:queue','listen_uri':'quack:127.0.0.1:41328'}
    gateway=x.typed.TypedStateOwnerGateway(connection=None,socket_path=tmp_path/'queue.sock',
        store_id=queue_identity['store_id'],identity=queue_identity)
    renewals=[]
    def renew(*args,**kwargs):
        value=gateway.renew_grant(*args,**kwargs);renewals.append(value);return value
    queue=SimpleNamespace(identity=SimpleNamespace(to_dict=lambda:dict(queue_identity)),_command_gateway=gateway,
        issue_typed_client_grant_record=gateway.issue_grant,renew_typed_client_grant=renew,
        revoke_typed_client_grant=gateway.revoke_grant,typed_command_socket_path=lambda:gateway.socket_path)
    scope=dict(board_namespace='board:doep',config_cid='config:current',plan_cid=policy.plan_root_cid,
               lane_id='0',attempt_root=str(tmp_path/'attempts'))
    peer_checks=[]
    def validate(**kwargs):peer_checks.append(kwargs);return '0'
    monkeypatch.setattr(native,'time',SimpleNamespace(monotonic=lambda:x.clock.mono))
    x.broker.board.payload={'merge_target_branch':'main'}
    x.broker._validate_merge_peer=validate
    # Exercise the actual native-parent constructor wiring, retaining the
    # fixture's kernel-peer admission override and real grant gateways.
    x.broker.__init__(listener=x.broker.listener,server=x.broker.server,board=x.broker.board,
        paths=x.broker.paths,policy=policy,launch_id=x.broker.launch_id,
        queue_server=queue,queue_scope_bindings=[scope])
    client=f'database-implementation-daemon:{x.m.OWNER_SESSION}:shard:0-of-4'
    request=dict(schema=bundle.REQUEST_SCHEMA,request_id='a'*32,pid=x.birth.pid,
        process_birth=x.birth.to_dict(),process_birth_id=x.owner['process_birth_id'],
        client_id=client,store_id=x.owner['store_id'],config_cid=scope['config_cid'],plan_cid=scope['plan_cid'])
    response=x.broker._admit(request,peer_pid=x.birth.pid,peer_uid=os.geteuid())
    return SimpleNamespace(x=x,native=native,queue=queue,queue_identity=queue_identity,
        queue_gateway=gateway,queue_renewals=renewals,peer_checks=peer_checks,
        request=request,response=response,client=client)


def test_each_role_renews_once_beyond_two_original_ttls(paired):
    p=paired;x=p.x
    reader,reader_response,reader_original=x.admit('supervisor')
    original=dict(x.gateway._grants)|dict(p.queue_gateway._grants)
    parent_task=x.broker._grant_bindings[p.client][0]
    peer=(x.birth.pid,os.geteuid(),x.birth.start_time_ticks)
    for cycle in range(3):
        x.clock.wall+=x.m.GRANT_TTL_SECONDS-60
        x.clock.mono+=x.m.GRANT_TTL_SECONDS-60
        x.broker._maintain_grants()
        assert len(x.renewals)==2*(cycle+1)
        assert len(p.queue_renewals)==2*(cycle+1)
        assert sum(g.grant_id==parent_task.grant_id for g in x.renewals)==cycle+1
        entry=x.broker._paired._issued[p.client]
        assert x.broker._grant_bindings[p.client][0]==entry['grant_records'][parent_task.grant_id]
        for gateway in (x.gateway,p.queue_gateway):
            for token,current in gateway._grants.items():
                first=original[token]
                assert replace(current,issued_at=first.issued_at,expires_at=first.expires_at)==first
                assert gateway._require_active_grant(first,peer_identity=peer)==current
        before=(len(x.renewals),len(p.queue_renewals))
        x.broker._maintain_grants()
        assert (len(x.renewals),len(p.queue_renewals))==before
        assert x.broker._admit(p.request,peer_pid=x.birth.pid,peer_uid=os.geteuid())==p.response
    assert x.clock.wall*1000 > parent_task.expires_at+x.m.GRANT_TTL_SECONDS*1000
    assert set(x.gateway._grants)|set(p.queue_gateway._grants)==set(original)


@pytest.mark.parametrize('role',['task','queue','recovery'])
@pytest.mark.parametrize('fault',['revoked','expired','missing','duplicate','scope','peer_uid','grant_id'])
def test_entire_bundle_is_validated_before_any_role_renews(paired,role,fault):
    p=paired;x=p.x
    gateway=x.gateway if role=='task' else p.queue_gateway
    token=p.response[role]['token']
    original=gateway._grants[token]
    if fault=='revoked':gateway.revoke_grant(original.grant_id)
    elif fault=='expired':x.clock.wall+=x.m.GRANT_TTL_SECONDS
    elif fault=='missing':gateway._grants.pop(token)
    elif fault=='duplicate':gateway._grants['foreign-token']=original
    elif fault=='scope':gateway._grants[token]=replace(original,entity_scopes=(('repository_id','other'),))
    elif fault=='peer_uid':gateway._grants[token]=replace(original,peer_uid=os.geteuid()+1)
    elif fault=='grant_id':gateway._grants[token]=replace(original,grant_id='other')
    x.broker._paired._issued[p.client]['renew_at']=0
    with pytest.raises((RuntimeError,x.typed.TypedStateOwnerError)):
        x.broker._maintain_grants()
    assert not x.renewals and not p.queue_renewals
    with pytest.raises((RuntimeError,x.typed.TypedStateOwnerError)):
        x.broker._admit(p.request,peer_pid=x.birth.pid,peer_uid=os.geteuid())


@pytest.mark.parametrize('fault',['dead','pid_reuse','boot','parent'])
def test_paired_birth_retirement_removes_both_parent_bindings_and_all_roles(paired,monkeypatch,fault):
    p=paired;x=p.x
    fields={'pid_reuse':{'start_time_ticks':x.birth.start_time_ticks+1},
            'boot':{'boot_id':'foreign'},'parent':{'parent_pid':x.birth.parent_pid+1}}
    birth=None if fault=='dead' else replace(x.birth,**fields[fault])
    # Owner and client use this fixture PID; preserve the owner observation
    # and vary only the following client birth read.
    observations=iter((x.birth,birth))
    monkeypatch.setattr(p.native,'read_process_birth',lambda _:next(observations,x.birth))
    x.broker._paired._issued[p.client]['renew_at']=0
    x.broker._maintain_grants()
    assert not x.gateway._grants and not p.queue_gateway._grants
    assert not x.broker._paired._issued
    assert p.client not in x.broker._grants and p.client not in x.broker._grant_bindings
    assert not x.renewals and not p.queue_renewals


@pytest.mark.parametrize('fault',['queue_owner','queue_gateway','task_owner','task_gateway','lane_scope'])
def test_owner_and_exact_retained_lane_scope_checked_before_any_renewal(paired,fault):
    p=paired;x=p.x
    if fault=='queue_owner':p.queue_identity['generation']+=1
    elif fault=='queue_gateway':p.queue_gateway.identity={**p.queue_identity,'generation':105}
    elif fault=='task_owner':x.owner['generation']+=1
    elif fault=='task_gateway':x.gateway.identity={**x.owner,'generation':105}
    elif fault=='lane_scope':x.broker._paired.validate_peer=lambda **_:'1'
    x.broker._paired._issued[p.client]['renew_at']=0
    with pytest.raises(RuntimeError):x.broker._maintain_grants()
    assert not x.renewals and not p.queue_renewals
    with pytest.raises(RuntimeError):x.broker._admit(p.request,peer_pid=x.birth.pid,peer_uid=os.geteuid())


def test_orphaned_paired_executor_cannot_fall_through_to_default_renewal(paired):
    p=paired;x=p.x
    x.broker._paired._issued.clear()
    with pytest.raises(x.m.HandoffError,match='no complete retained owner bundle'):
        x.broker._maintain_grants()
    assert not x.renewals and not p.queue_renewals


@pytest.mark.parametrize('fault',['missing_binding','changed_binding','changed_role'])
def test_paired_task_retains_the_parent_binding_before_any_extension(paired,fault):
    p=paired;x=p.x
    if fault=='missing_binding':x.broker._grant_bindings.pop(p.client)
    elif fault=='changed_binding':
        grant,identity=x.broker._grant_bindings[p.client]
        x.broker._grant_bindings[p.client]=(replace(grant,allowed_operations=frozenset()),identity)
    else:x.broker._grants[p.client]['client_role']='supervisor_read'
    x.broker._paired._issued[p.client]['renew_at']=0
    with pytest.raises(x.m.HandoffError,match='retained native binding'):
        x.broker._maintain_grants()
    assert not x.renewals and not p.queue_renewals


def test_stopping_prevents_paired_and_reader_renewal(paired):
    p=paired;x=p.x
    x.admit('supervisor')
    before=dict(x.gateway._grants)|dict(p.queue_gateway._grants)
    x.broker.stopping.set()
    x.broker._maintain_grants()
    assert not x.renewals and not p.queue_renewals
    assert dict(x.gateway._grants)|dict(p.queue_gateway._grants)==before
