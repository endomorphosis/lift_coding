"""Actual dynamic operation/resource authorization through native A3/A4 APIs."""
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
from pathlib import Path
import sys
import time
from effects import canonical, digest, write_fresh


def load_baseline(source_root):
    path = Path(source_root) / 'papers/completion/law_to_action/benchmark/baselines.py'
    spec = importlib.util.spec_from_file_location('la_generated_profile_native_baseline', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def permission(policy, actor, action, resource):
    from ipfs_kit_py.mcp_server.mcplusplus.ucan import resource_covers
    matches = lambda rule: rule['action'] == action and resource_covers(rule['resource'], resource)
    return actor == policy['actor'] and any(matches(rule) for rule in policy['permissions']) and not any(matches(rule) for rule in policy.get('prohibitions', []))


class DeclaredPolicy:
    provider_id = 'la-generated-profile-declared-policy-v1'
    available = True
    def evaluate(self, *, actor, action, resource=None, policy=None, policy_text=None, **context):
        from ipfs_kit_py.mcp.profile_d_policy import policy_root
        return {'decision': 'allow' if permission(policy, actor, action, resource) else 'deny',
                'policy_root': policy_root(policy, policy_text), 'canonical': False,
                'provider': self.provider_id}


class CountVerifier:
    def __init__(self, real):
        self.real = real
        self.calls = 0
    def verify(self, *args, **kwargs):
        self.calls += 1
        return self.real.verify(*args, **kwargs)


def checked_obligations(baseline, policy, invocation, profile_binding_valid):
    from ipfs_kit_py.mcp_server.mcplusplus.ucan import resource_covers
    checks = [{'kind': 'complete_exact_byte_profile_binding', 'passed': profile_binding_valid}]
    for rule in policy.get('flow_rules', []):
        if rule['action'] == invocation['name'] and resource_covers(rule['resource'], invocation['resource']):
            checks.append({'kind': 'declared_output_flow', 'rule': rule,
                           'observed_labels': invocation['flow_labels'],
                           'passed': not bool(set(rule['forbidden_labels']) & set(invocation['flow_labels']))})
    for rule in policy.get('argument_rules', []):
        if rule['action'] == invocation['name'] and resource_covers(rule['resource'], invocation['resource']):
            if rule['kind'] != 'equals':
                raise ValueError('Argument predicate is not implemented')
            index = rule['index']
            passed = type(index) is int and 0 <= index < len(invocation['arguments']) and invocation['arguments'][index] == rule['value']
            checks.append({'kind': 'typed_argument_equality', 'rule': rule, 'passed': passed})
    if not 1 <= len(checks) <= 16 or any(type(row['passed']) is not bool for row in checks):
        raise ValueError('Unsupported obligation count/type')
    # Assert each independently evaluated predicate and ask whether at least one
    # obligation can fail under those facts. Preserve the concrete valuation.
    clauses = [[index if row['passed'] else -index] for index, row in enumerate(checks, 1)]
    clauses.append([-index for index in range(1, len(checks) + 1)])
    provider = baseline.sat_provider(len(checks), clauses)
    checker = baseline.sat_checker(len(checks), clauses, provider)
    return {'checks': checks, 'clauses': clauses, 'provider': provider, 'checker': checker,
            'allowed': provider['status'] == 'unsat' and checker['agrees_with_provider'] is True,
            'authority_kind': 'satisfiability_of_declared_profile_predicates',
            'whole_program_theorem_or_legal_validity_claimed': False}


class NativeGate:
    def __init__(self, source_root, shared, task, arm, source_sha256, profile_report, environment_digest, attempt_id):
        if arm not in ('A0', 'A1', 'A2', 'A3', 'A4'):
            raise ValueError('Unknown arm')
        self.baseline = load_baseline(source_root)
        self.shared = Path(shared)
        self.shared.mkdir(exist_ok=True)
        self.task, self.arm, self.source_sha256 = task, arm, source_sha256
        if type(attempt_id) is not str or not attempt_id:
            raise ValueError('Concrete attempt identity is required')
        self.attempt_id = attempt_id
        self.policy = task['policy']
        if set(self.policy) - {'actor', 'permissions', 'prohibitions', 'flow_rules', 'argument_rules'}:
            raise ValueError('Unknown task policy fields')
        if self.policy['actor'] != self.baseline.ACTOR:
            raise ValueError('Declared actor differs')
        for key in ('permissions', 'prohibitions'):
            for rule in self.policy.get(key, []):
                if set(rule) != {'action', 'resource'} or any(type(value) is not str or not value for value in rule.values()):
                    raise ValueError('Malformed permission rule')
        self.profile_report = profile_report
        self.environment_digest = environment_digest
        self.profile_valid = (profile_report['source_profile']['source_sha256'] == source_sha256
                              and profile_report['all_semantic_native_facts_reconciled'] is True
                              and profile_report['all_ast_call_sites_reconciled'] is True and not profile_report['findings'])
        if not self.profile_valid:
            raise ValueError('Complete source profile/request binding required before dispatch')
        self.call_sites = {(event['line'], event['column'], event['normalized_request']['target'])
                           for event in profile_report['ast_events'] if event['kind'] == 'sealed_call'}

    def ucan(self, invocation, directory):
        from ipfs_kit_py.mcp.profile_d_policy import policy_root
        from ipfs_kit_py.mcp_server import mcplusplus
        from ipfs_kit_py.mcp_server.authorization import AuthorizationDenied, AuthorizationGate
        from ipfs_kit_py.mcp_server.mcplusplus.event_dag import EventDAGStore
        from ipfs_kit_py.mcp_server.mcplusplus.ucan import issue_ucan, ucan_token_id
        directory.mkdir()
        ledger, verifier, key = self.baseline.ucan_bundle(directory)
        counted = CountVerifier(verifier)
        grants = [{'resource': rule['resource'], 'ability': rule['action']} for rule in self.policy['permissions']]
        if not grants:
            grants = [{'resource': 'no-grants/' + digest(self.policy), 'ability': 'no-granted-operation'}]
        now = time.time()
        token = issue_ucan(issuer=self.baseline.ISSUER, audience=self.policy['actor'], capabilities=grants,
                          private_key=key, kid='root-v1', expires_at=now + 60,
                          nonce=digest({'attempt': self.attempt_id, 'task': self.task['id'], 'invocation': invocation})[:32], issued_at=now - 1)
        envelope = {'tool': invocation['name'], 'resource': invocation['resource'], 'ability': invocation['name'],
                    'actor': self.policy['actor'], 'ucan': token, 'policy_root': policy_root(self.policy, None),
                    'request_id': 'req-' + digest(invocation), 'transaction_id': 'req-' + digest(invocation),
                    'policy': self.policy}
        gate = AuthorizationGate(policy_provider=DeclaredPolicy(), ucan_verifier=counted, ledger=ledger,
                                 audit_store=EventDAGStore(storage_dir=str(directory / 'dag')),
                                 envelope_validator=mcplusplus.validate_packet, validator_available=True)
        try:
            result = gate.authorize(tool=invocation['name'], arguments={'resource': invocation['resource'], 'policy': self.policy}, envelope=envelope)
            report = {'decision': 'allow', 'authorization_event_cid': result.authorization_event_cid}
        except AuthorizationDenied as exc:
            report = {'decision': 'deny', 'reason': exc.code}
        report.update(actual_tool=invocation['name'], actual_resource=invocation['resource'],
                      declared_grants=grants, native_verifier_calls=counted.calls,
                      token_id=ucan_token_id(token), native_ucan='real-ed25519-verifier',
                      policy_provider=DeclaredPolicy.provider_id)
        write_fresh(directory / 'result.json', report)
        return report

    def __call__(self, invocation, delegate, directory):
        site = invocation['source_call']
        if (site['line'], site['column'], site['name']) not in self.call_sites or invocation['name'] != site['name']:
            raise ValueError('Actual invocation differs from exact source call site')
        if self.arm in ('A0', 'A1', 'A2'):
            return {'arm': self.arm, 'mechanism': 'unguarded_inside_common_fixture_containment',
                    'model_prompt_intervention_qualified': False}, delegate()
        ucan = self.ucan(invocation, directory / 'ucan')
        if self.arm == 'A3':
            return {'arm': self.arm, 'ucan': ucan}, delegate() if ucan['decision'] == 'allow' else None
        from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import SupervisorInvocationContext, SupervisorPreInvocationEnforcement
        from ipfs_datasets_py.logic.admissibility.receipt import BoundRoots, BoundContext, build_decision_receipt, derive_capability
        from ipfs_datasets_py.logic.admissibility.compose import InternalDecisionStatus
        from multiformats import CID, multihash
        obligation = checked_obligations(self.baseline, self.policy, invocation, self.profile_valid)
        decision = ucan['decision'] == 'allow' and obligation['allowed']
        policy_sha = digest(self.policy)
        policy_cid = str(CID('base32', 1, 'raw', multihash.digest(canonical(self.policy), 'sha2-256')))
        roots = BoundRoots(policy_root=policy_cid, corpus_roots=('source:' + self.source_sha256,),
                           revocation_root='revocation:' + digest(ucan))
        identity = digest({'attempt': self.attempt_id, 'task': digest(self.task), 'candidate': self.source_sha256, 'invocation': invocation})
        effects = ('effect:' + invocation['name'] + ':' + invocation['resource'],)
        bound = BoundContext(request_digest=identity, arguments_digest=digest(invocation['arguments']),
            actor_id=self.policy['actor'], audience_id='audience:la-generated-profile',
            tool_id='tool:' + invocation['name'], tool_version='1', effect_ids=effects,
            environment_digest=self.environment_digest, environment_id='env:la-generated-profile',
            resource_ids=('resource:' + invocation['resource'],), nonce='nonce:' + identity,
            capability_ids=('capability:' + identity,))
        now = datetime.now(timezone.utc)
        stamp = lambda value: value.isoformat().replace('+00:00', 'Z')
        receipt = build_decision_receipt(receipt_id='receipt:' + identity, context=bound, roots=roots,
            outcome=InternalDecisionStatus.ALLOW if decision else InternalDecisionStatus.DENY,
            reasons=('Native dynamic invocation, exact source profile and checked declared policy predicates',),
            selected_evidence_cids=(policy_cid,), obligation_ids=('obligation:closed-profile-dynamic-effect',),
            attempt_digests=(digest(invocation),), result_digests=(digest(obligation), digest(ucan)),
            decision_digest=digest({'allow': decision, 'obligation': obligation, 'ucan': ucan}),
            policy_digest=policy_sha, profile_id='profile:bounded-python-syntax-development-v1',
            issued_at=stamp(now - timedelta(seconds=1)), deadline=stamp(now + timedelta(seconds=30)),
            expiry=stamp(now + timedelta(seconds=40)), producer_id='producer:trusted-closed-profile-adapter',
            metadata={'scientific_benchmark': False, 'native_generic_mapper_claimed_complete': False,
                      'source_profile_mapping_sha256': digest(self.profile_report), 'invocation': invocation})
        capability = derive_capability(receipt, capability_id='capability:' + identity,
                                       allowed_effects=effects, require_strict_subset=False) if decision else None
        write_fresh(directory / 'admission.json', {'receipt': receipt.to_dict(),
                    'capability': capability.to_dict() if capability else None, 'obligations': obligation,
                    'cryptographic_proof_receipt_claimed': False})
        context = SupervisorInvocationContext(**{key: getattr(bound, key) for key in
            ['actor_id', 'audience_id', 'tool_id', 'request_digest', 'arguments_digest',
             'environment_digest', 'effect_ids', 'tool_version', 'environment_id', 'delegation_ids',
             'delegation_digest', 'nonce', 'resource_ids', 'capability_ids']},
             task_id='task:' + self.task['id'], plan_id='plan:' + identity)
        durable = self.baseline.load_durable()
        store = durable.DuckDBCapabilityConsumptionStore(self.shared / 'consumption.duckdb', owner_id='owner:la-generated-profile')
        result = None
        def actual_delegate():
            nonlocal result
            result = delegate()
            return result
        try:
            store.attach()
            enforcer = SupervisorPreInvocationEnforcement(mode='enforce', store=store,
                expected_roots=roots, clock=lambda: stamp(datetime.now(timezone.utc)))
            outcome = enforcer.authorize_and_delegate(context, actual_delegate, receipt=receipt, capability=capability)
            report = {'arm': self.arm, 'ucan': ucan, 'obligations': obligation,
                      'enforcement': {'disposition': outcome.disposition.value,
                                      'delegate_called': outcome.delegate_called,
                                      'denial_reason': outcome.observation.denial_reason,
                                      'store_kind': store.store_kind, 'in_memory': getattr(store, 'in_memory', None)}}
        finally:
            store.close()
        write_fresh(directory / 'enforcement.json', report)
        return report, result
