"""Exact-byte AST refinement of the native observation for this closed profile.

The generic mapper's unresolved results are retained. This adapter does not
represent them as resolved by the generic mapper or infer whole-Python safety.
"""
import ast
from collections import defaultdict
import hashlib
from effects import digest, write_fresh
from program import validate, ProgramError


def shape(node):
    if node is None:
        return 'none'
    if type(node) is ast.Constant:
        return 'constant:' + type(node.value).__name__
    return {ast.Name: 'name', ast.Call: 'call', ast.List: 'collection', ast.Dict: 'mapping',
            ast.Subscript: 'subscript', ast.BinOp: 'binary_expression', ast.BoolOp: 'boolean_expression',
            ast.Compare: 'comparison'}.get(type(node), type(node).__name__.lower())


def ast_events(source, primitive_names):
    tree, profile = validate(source, primitive_names)
    text = source.decode('utf-8')
    events = []
    for node in ast.walk(tree):
        if type(node) is ast.Call:
            name = node.func.id
            expected = [('action', 'invoke'), ('target', name), ('effect', 'call')]
            expected += [('data_flow', shape(arg) + '->argument:' + name) for arg in node.args]
            dimensions = ('invoke', name, 'profile-values->sealed-call', 'call')
            kind = 'sealed_call'
        elif type(node) is ast.Assign:
            target = node.targets[0]
            name = target.id if type(target) is ast.Name else shape(target)
            expected = [('action', 'write'), ('target', name), ('effect', 'state_update'),
                        ('data_flow', shape(node.value) + '->' + shape(target))]
            dimensions = ('write', 'profile:local', 'profile-values->local', 'state_update')
            kind = 'confined_local_assignment'
        elif type(node) is ast.Return:
            expected = [('action', 'return'), ('target', 'caller'), ('effect', 'function_return'),
                        ('data_flow', shape(node.value) + '->caller')]
            dimensions = ('return', 'profile:caller', 'profile-values->return', 'function_return')
            kind = 'confined_function_return'
        else:
            continue
        segment = ast.get_source_segment(text, node)
        if segment is None:
            raise ProgramError('Source span could not be recovered')
        record = {'kind': kind, 'line': node.lineno, 'end_line': node.end_lineno,
                  'column': node.col_offset, 'end_column': node.end_col_offset,
                  'source_segment': segment, 'source_segment_sha256': hashlib.sha256(segment.encode()).hexdigest(),
                  'ast_sha256': hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest(),
                  'expected_native_facts': sorted(set(expected)),
                  'normalized_request': dict(zip(('action', 'target', 'data_flow', 'expected_effect'), dimensions))}
        if type(node) is ast.Call:
            record['arguments'] = [{'index': index, 'shape': shape(arg),
                                    'source_segment': ast.get_source_segment(text, arg),
                                    'ast_sha256': hashlib.sha256(ast.dump(arg, include_attributes=False).encode()).hexdigest()}
                                   for index, arg in enumerate(node.args)]
        record['event_id'] = 'profile-ast-event:' + digest({'source_sha256': profile['source_sha256'], 'record': record})
        events.append(record)
    events.sort(key=lambda row: (row['line'], row['column'], row['end_line'], row['end_column'], row['kind']))
    if len({event['event_id'] for event in events}) != len(events):
        raise ProgramError('Duplicate AST event identity')
    return profile, events


def reconcile(source, primitive_names, native_document, supplied_events=None):
    profile, events = ast_events(source, primitive_names)
    if supplied_events is not None and supplied_events != events:
        raise ProgramError('Supplied AST event/span/argument inventory differs from exact source')
    if native_document['status'] != 'extracted' or native_document.get('diagnostics'):
        raise ProgramError('Native extraction incomplete or unsupported')
    raw = defaultdict(list)
    semantic_kinds = {'action', 'target', 'data_flow', 'effect'}
    for fact in native_document['facts']:
        if fact['binding']['source_sha256'] != 'sha256:' + profile['source_sha256']:
            raise ProgramError('Native fact/source byte binding differs')
        scope = fact['source_scope']
        if scope['path'] != 'candidate.py' or scope['delta'] != 'added' or scope['symbol'] != 'run':
            raise ProgramError('Unexpected native source scope')
        if fact['kind'] in semantic_kinds:
            raw[(fact['kind'], fact['value'], scope['line_start'], scope['line_end'])].append(fact['fact_id'])
        elif fact['kind'] not in {'language', 'source_scope', 'guard', 'capability'}:
            raise ProgramError('Unreconciled native fact kind')
    expected_keys = set()
    for event in events:
        evidence = []
        for kind, value in event['expected_native_facts']:
            key = (kind, value, event['line'], event['end_line'])
            expected_keys.add(key)
            if key not in raw:
                raise ProgramError('Expected exact-span native fact is missing: ' + str(key))
            evidence.extend(raw[key])
        event['native_fact_evidence_ids'] = sorted(set(evidence))
    if set(raw) != expected_keys:
        raise ProgramError('Native semantic facts not accounted for by the closed AST profile')
    calls = [event for event in events if event['kind'] == 'sealed_call']
    if {(event['line'], event['column'], event['normalized_request']['target']) for event in calls} != {(call['line'], call['column'], call['name']) for call in profile['calls']} or len(calls) != len(profile['calls']):
        raise ProgramError('Complete call-site reconciliation failed')
    return profile, events


def build_native_mappings(source, primitive_names, context, directory):
    from ipfs_accelerate_py.agent_supervisor.proof.code_security_facts import ChangedCodeDiff, extract_code_security_facts
    from ipfs_accelerate_py.agent_supervisor.proof.cve_security_gate import (SecurityRequestMapping,
        SecurityFactStream, SecurityRequestMappingStatus, map_code_security_requests, correlate_security_requests)
    source_sha = hashlib.sha256(source).hexdigest()
    facts = extract_code_security_facts(ChangedCodeDiff(tree_id='tree:' + source_sha,
        diff_id='diff:' + digest({'before': '', 'after_sha256': source_sha}), new_path='candidate.py',
        before_source='', after_source=source.decode('utf-8')))
    raw = facts.to_dict()
    write_fresh(directory / 'native_facts.json', raw)
    generic = map_code_security_requests(facts, context)
    write_fresh(directory / 'generic_native_mapping.json', {'scope': 'Unmodified generic native mapper; ambiguity is retained',
                'mappings': [mapping.to_dict() for mapping in generic]})
    profile, events = reconcile(source, primitive_names, raw)
    code = tuple(SecurityRequestMapping(stream=SecurityFactStream.CODE, source_id=event['event_id'],
                    status=SecurityRequestMappingStatus.EXACT,
                    request=context.request(**event['normalized_request']),
                    evidence_ids=tuple(event['native_fact_evidence_ids']) + (event['event_id'],)) for event in events)
    declarations = [('invoke', name, 'profile-values->sealed-call', 'call') for name in sorted(primitive_names)]
    declarations += [('write', 'profile:local', 'profile-values->local', 'state_update'),
                     ('return', 'profile:caller', 'profile-values->return', 'function_return')]
    intent = tuple(SecurityRequestMapping(stream=SecurityFactStream.INTENT,
                    source_id='closed-profile-intent:' + digest(dimensions), status=SecurityRequestMappingStatus.EXACT,
                    request=context.request(**dict(zip(('action', 'target', 'data_flow', 'expected_effect'), dimensions))),
                    evidence_ids=('profile:bounded-python-syntax-development-v1',)) for dimensions in declarations)
    findings = correlate_security_requests(intent, code)
    report = {'schema': 'la-exact-ast-native-request-adapter/v1', 'source_profile': profile,
              'ast_events': events, 'code': [mapping.to_dict() for mapping in code],
              'intent': [mapping.to_dict() for mapping in intent], 'findings': [finding.to_dict() for finding in findings],
              'generic_native_mapper_claimed_complete': False,
              'scope': 'Exact-byte closed interpreter profile; primitive call syntax and confined local operations only. Actual dynamic effect arguments/resources require separate invocation admission.',
              'all_semantic_native_facts_reconciled': True, 'all_ast_call_sites_reconciled': True}
    write_fresh(directory / 'profile_request_mapping.json', report)
    if findings:
        raise ProgramError('Native profile-intent correlation failed')
    return report
