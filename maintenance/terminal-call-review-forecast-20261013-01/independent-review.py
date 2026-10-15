"""Independent bounded record audit. No imports of implementation, jobs or DB opens."""
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import xml.etree.ElementTree as ET

U = Path('/home/barberb/lift_coding/maintenance/terminal-call-review-forecast-20261013-01')
C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
checks, pins, witnesses, bodies = [], {}, {}, {}

def ck(name, value):
    if not value:
        raise AssertionError(name)
    checks.append({'check': name, 'passed': True})

def wire(value, ascii=False):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=ascii,
                      allow_nan=False).encode('utf-8')

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def digest(raw):
    return 'sha256:' + sha(raw)

def cid(value):
    return 'b' + base64.b32encode(b'\x01\xa9\x02\x12\x20' + hashlib.sha256(wire(value)).digest()).decode().rstrip('=').lower()

def raw_cid_from_sha(value):
    return 'b' + base64.b32encode(b'\x01\x55\x12\x20' + bytes.fromhex(value)).decode().rstrip('=').lower()

def signature(info):
    return tuple(getattr(info, field) for field in ('st_dev', 'st_ino', 'st_mode', 'st_uid',
        'st_gid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))

def read(path, expected=None):
    path = Path(path)
    ck('safe_explicit_path:' + str(path), path.is_absolute() and path.resolve(strict=True) == path
       and path.suffix not in {'.duckdb', '.ducklake', '.parquet', '.sqlite', '.wal'}
       and 'cas' not in path.parts and 'lake' not in path.parts)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        ck('regular_bounded:' + str(path), stat.S_ISREG(before.st_mode) and before.st_nlink == 1
           and 0 <= before.st_size <= 8 * 1024**2)
        with os.fdopen(os.dup(fd), 'rb') as stream:
            raw = stream.read(8 * 1024**2 + 1)
        ck('stable_read:' + str(path), signature(before) == signature(os.fstat(fd)) == signature(path.lstat()))
    finally:
        os.close(fd)
    pin = {'path': str(path), 'sha256': sha(raw), 'bytes': len(raw)}
    if expected is not None:
        ck('declared_pin:' + str(path), pin == expected)
    if str(path) in pins:
        ck('repeat_read:' + str(path), pins[str(path)] == pin and witnesses[str(path)] == signature(before))
    pins[str(path)] = pin
    witnesses[str(path)] = signature(before)
    bodies[str(path)] = raw
    return raw

def document(path):
    return json.loads(read(path))

def record_identity(name, value, field):
    ck(name + ':content_identity', value[field] == cid({key: item for key, item in value.items() if key != field}))

def false_fields(name, value, names):
    for key in names:
        ck(name + ':false:' + key, value.get(key) is False)

def zero_fields(name, value, names):
    for key in names:
        ck(name + ':zero:' + key, type(value.get(key)) is int and value[key] == 0)

selected_names = ['summary.json', 'policy.json', 'query.json', 'intent-profile.json', 'capsule.json',
    'expanded-packet.json', 'capsule-packet.json', 'expanded-preview.json', 'capsule-preview.json',
    'final-current-preview.json', 'capacity.json', 'pre-capacity-binding.json']
selected = {name: document(U / 'preview-run-04' / name) for name in selected_names}
baseline = document(U / 'baseline-manifest.json')
preservation = document(U / 'preservation-before-package.json')
package = document(U / 'package-report.json')
inventory = document(U / 'actual-public-inventory.json')
method = selected['summary.json']['tokenizer']
status = document(U / 'improvement-status.json')
history = document(U / 'development-history.json')
test_run = document(U / 'test-final-run.json')
xml = ET.fromstring(read(U / 'test-final.xml'))
read(U / 'experiment-plan.json')

ck('public_inventory_exact_count', inventory['explicit_named_file_count'] == len(inventory['files']) == 113)
false_fields('public_inventory', inventory, ['cas_bodies_included', 'database_bodies_included',
    'ducklake_parquet_bodies_included', 'recursive_traversal'])
for pin in inventory['files']:
    ck('current_U_public_namespace:' + pin['path'], pin['path'].startswith(str(U / 'actual-public-review-01') + '/'))
    read(pin['path'], pin)
ck('predecessor_preservation_occurrences', preservation['checked_occurrences'] == len(preservation['occurrences']) == 231
   and preservation['all_expected_pins_unchanged'] is True and preservation['occurrences_deduplicated'] is False
   and preservation['sealed_predecessor_named_files'] == 217 and preservation['baseline_dependency_occurrences'] == 13)
for occurrence in preservation['occurrences']:
    ck('preservation_occurrence_exact:' + occurrence['group'] + ':' + str(occurrence['ordinal']),
       occurrence['unchanged'] is True and occurrence['actual'] == occurrence['expected'])
    pin = occurrence['expected']
    read(pin['path'], pin)
for pin in baseline['dependencies']:
    read(pin['path'], pin)

ck('package_exact_six', package['source_count'] == len(package['files']) == 6)
false_fields('package', package, ['original_repository_index_written', 'sealed_predecessor_mutated'])
zero_fields('package', package, ['commits_created', 'pushes'])
source_text = {}
for entry in package['files']:
    original = read(entry['source']['path'], entry['source'])
    copy = read(entry['packaged']['path'], entry['packaged'])
    ck('packaged_exact:' + entry['relative_path'], original == copy)
    ck('source_added_in_baseline:' + entry['relative_path'], {'path': str(C / entry['relative_path']), 'exists': False} in baseline['new_sources'])
    source_text[entry['relative_path']] = original.decode('utf-8')
    ast.parse(original)
patch = read(package['patch']['path'], package['patch'])
parts, current, added = {}, None, []
for line in patch.decode().splitlines(keepends=True):
    if line.startswith('diff --git '):
        if current is not None:
            parts[current] = ''.join(added).encode()
        current, added = line.split(' b/', 1)[1].strip(), []
    elif line.startswith('--- '):
        ck('patch_new_only:' + str(current), line.strip() == '--- /dev/null')
    elif line.startswith('+') and not line.startswith('+++'):
        added.append(line[1:])
    elif line.startswith('-') and not line.startswith('---'):
        ck('patch_no_removal:' + str(current), False)
if current is not None:
    parts[current] = ''.join(added).encode()
ck('patch_six_paths', set(parts) == set(source_text))
for relative, raw in parts.items():
    ck('patch_exact_bytes:' + relative, raw == source_text[relative].encode())
cases = list(xml.iter('testcase'))
identities = [(value.attrib.get('classname'), value.attrib.get('name')) for value in cases]
ck('final_159_unique_tests', len(cases) == len(set(identities)) == test_run['tests'] == test_run['unique_identities'] == 159)
ck('final_tests_no_failure_error_skip', not list(xml.iter('failure')) and not list(xml.iter('error')) and not list(xml.iter('skipped')))
ck('final_test_exit_and_pins', test_run['exit_code'] == 0 and test_run['all_sources_unchanged'] is True
   and test_run['sources_before'] == test_run['sources_after'] == [entry['source'] for entry in package['files']])
zero_fields('final_tests', test_run, ['failures', 'errors', 'skipped', 'checker_invocations', 'training_steps', 'provider_calls'])

q, capsule, profile = selected['query.json'], selected['capsule.json'], selected['intent-profile.json']
for label, record, true_names in [('query', q, {'sql_executed'}),
        ('capsule', capsule, {'conditional_model_claim', 'native_call_opacity_preserved', 'opaque_call_model_assumption'}),
        ('profile', profile, {'conditional_model_claim', 'closed_cnl_syntax_parsed'})]:
    for key, value in record.items():
        if type(value) is bool:
            ck(label + ':exact_boolean_ceiling:' + key, value is (key in true_names))
    zero_fields(label, record, ['provider_calls', 'training_steps'])
ck('exact_declared_mathematical_domain', profile['mathematical_domain'] == {
    'kind': 'unbounded_mathematical_integer', 'python_input_assumption': 'exact_builtin_int_excluding_bool_and_subclasses',
    'runtime_equivalence_proved': False})
for name, field in [('query.json', 'query_id'), ('capsule.json', 'capsule_id'), ('intent-profile.json', 'profile_id')]:
    record_identity(name, selected[name], field)
prompt = selected['capsule-packet.json']['user_prompt']
native_ir = json.loads(profile['intent_document_json'])
ck('full_native_IntentIR_canonical_bytes', wire(native_ir, ascii=True).decode() == profile['intent_document_json'])
ck('native_IR_byte_pin', sha(profile['intent_document_json'].encode()) == profile['intent_document_sha256']
   and len(profile['intent_document_json'].encode()) == profile['intent_document_bytes'])
ck('native_full_prompt_source_span', len(native_ir['sources']) == len(native_ir['statements']) == 1
   and native_ir['sources'][0]['span'] == {'start_char': 0, 'end_char': len(prompt)})
statement, source = native_ir['statements'][0], native_ir['sources'][0]
ck('native_source_sha', source['content_sha256'] == sha(prompt.encode()) == profile['prompt']['sha256'])
ck('native_goal_exact_atom', statement['arguments'] == ['caller.py', 'twice', 'n', '2', 'closed-caller-model@1',
    'unbounded_mathematical_integer'] and statement['kind'] == 'goal' and statement['modality'] == 'required'
    and statement['grounding'] == 'grounded' and statement['review_status'] == source['review_status'] == 'unreviewed'
    and statement['source_ref_ids'] == [source['ref_id']] and statement['normalized_text'] == prompt)
ck('native_confidence_preserved', type(statement['confidence']) is float and statement['confidence'] == 1.0)
ck('native_declarative_no_actions', native_ir['intent_kind'] == 'declarative' and native_ir['actions'] == []
   and native_ir['control_edges'] == [] and native_ir['entry_action_ids'] == native_ir['terminal_action_ids'] == [])

families = ('call_ir_projections', 'formal_call_checked_records', 'formal_call_coverage', 'formal_call_sources')
ck('fixed_selected_SQL', q['parameters'] == list(families) and q['row_limit'] == 5 and q['row_count'] == 4
    and q['sql'] == 'SELECT family,row_id,payload_sha256,source_snapshot_sha256,row_ordinal,payload_json FROM metadata_rows WHERE family IN (?,?,?,?) ORDER BY family,row_ordinal LIMIT 5'
    and set(q['rows']) == set(families) and q['sql_executed'] is True and q['quack_executed'] is False)
ck('source_snapshot_digest', q['metadata_binding']['source_snapshot_sha256'] == digest(wire(q['source_snapshot'])))
for family in families:
    rows = q['rows'][family]
    ck('selected_singleton:' + family, len(rows) == 1)
    row = rows[0]
    identity = {key: row[key] for key in ('schema', 'family', 'payload_sha256', 'source_snapshot_sha256')}
    ck('native_row_identity:' + family, row['row_id'] == digest(wire(identity)) and row['row_ordinal'] == 0
       and row['family'] == family and row['payload_sha256'] == digest(wire(row['payload']))
       and row['source_snapshot_sha256'] == q['metadata_binding']['source_snapshot_sha256'])
    declared = q['metadata_binding']['families'][family]
    export = wire(row) + b'\n'
    ck('native_family_digest:' + family, declared['digest'] == digest(wire(rows)) and declared['count'] == 1
       and declared['view'] == 'family_' + family)
    ck('native_export_digest:' + family, declared['export'] == {'relative_path': 'exports/' + family + '.jsonl',
       'sha256': digest(export), 'bytes': len(export)})
    actual_export = Path(q['metadata_binding']['output']) / declared['export']['relative_path']
    ck('SQL_public_export_exact:' + family, bodies[str(actual_export)] == export)
    handle = capsule['expansion']['families'][family]
    ck('capsule_expansion_join:' + family, all(handle[key] == row[key] for key in
        ('row_id', 'payload_sha256', 'row_ordinal', 'source_snapshot_sha256'))
        and handle['export'] == {'path': str(actual_export), 'sha256': sha(export), 'bytes': len(export)})
projection = q['rows']['call_ir_projections'][0]['payload']
generated = q['rows']['formal_call_sources'][0]['payload']
checked = q['rows']['formal_call_checked_records'][0]['payload']
coverage = q['rows']['formal_call_coverage'][0]['payload']
model = json.loads(bodies[str(U / 'actual-public-review-01/model/result.json')])
callee = json.loads(bodies[str(U / 'actual-public-review-01/model/callee/native-proof.json')])
metadata_row_counts = []
for report in (model['metadata'], model['advisory_cache']['metadata'],
               model['callee']['metadata'], model['callee']['advisory_cache']['metadata']):
    root = Path(report['output'])
    raw_manifest = bodies[str(root / 'manifest.json')]
    manifest = json.loads(raw_manifest)
    label = str(root.relative_to(U))
    ck('full_metadata_manifest:' + label, report['manifest_sha256'] == digest(raw_manifest)
       and report['source_snapshot_sha256'] == manifest['source_snapshot_sha256'] == digest(wire(manifest['source_snapshot'])))
    all_rows = {}
    recovered = {}
    for family, declared in manifest['families'].items():
        raw_export = bodies[str(root / declared['export']['relative_path'])]
        rows = [json.loads(line) for line in raw_export.splitlines()]
        all_rows[family] = rows
        ck('full_metadata_export:' + label + ':' + family, len(rows) == declared['count'] == report['family_counts'][family]
           and declared['digest'] == report['family_digests'][family] == digest(wire(rows))
           and declared['export'] == report['exports'][family]
           and declared['export']['sha256'] == digest(raw_export) and declared['export']['bytes'] == len(raw_export)
           and raw_export == b''.join(wire(row)+b'\n' for row in rows))
        for ordinal, row in enumerate(rows):
            identity = {key: row[key] for key in ('schema', 'family', 'payload_sha256', 'source_snapshot_sha256')}
            ck('full_metadata_row:' + label + ':' + family + ':' + str(ordinal), row['family'] == family
               and row['row_ordinal'] == ordinal and row['payload_sha256'] == digest(wire(row['payload']))
               and row['source_snapshot_sha256'] == manifest['source_snapshot_sha256'] and row['row_id'] == digest(wire(identity)))
    ck('full_metadata_root_population:' + label, report['row_root_sha256'] == manifest['row_root_sha256'] == digest(wire(all_rows))
       and manifest['row_count'] == report['row_count'] == sum(len(rows) for rows in all_rows.values()))
    metadata_row_counts.append(report['row_count'])
    for descriptor in manifest['batches']:
        batch_raw = bodies[str(root / descriptor['relative_path'])]
        batch = json.loads(batch_raw)
        ck('full_metadata_batch:' + label + ':' + descriptor['relative_path'], descriptor['bytes'] == len(batch_raw)
           and descriptor['sha256'] == digest(batch_raw) and batch['batch_id'] == descriptor['receipt']['batch_id']
           and descriptor['receipt']['admitted'] is False and descriptor['receipt']['production_activated'] is False)
        for event in batch['events']:
            packet = event['payload']
            raw_rows = packet['payload_json'].encode()
            rows = json.loads(raw_rows)
            ck('full_metadata_packet:' + label + ':' + event['event_id'], packet['packet_id'] == event['event_id']
               == digest(wire({key: item for key, item in packet.items() if key != 'packet_id'}))
               and packet['payload_bytes'] == len(raw_rows) and packet['payload_sha256'] == digest(raw_rows)
               and packet['row_count'] == len(rows) and packet['ordered_row_ids'] == [row['row_id'] for row in rows]
               and packet['source_snapshot_sha256'] == manifest['source_snapshot_sha256'])
            recovered.setdefault(packet['family'], []).extend(rows)
    for family, rows in all_rows.items():
        ck('full_metadata_packet_reconstruction:' + label + ':' + family,
           sorted(recovered.get(family, []), key=lambda row: row['row_ordinal']) == rows)
ck('four_metadata_populations', metadata_row_counts == [49, 41, 52, 41])
record_identity('projection', projection, 'projection_id')
record_identity('generated', generated, 'source_id')
record_identity('current_model', model, 'result_cid')
record_identity('native_callee', callee, 'result_cid')
ck('caller_contract_exact_join', profile['caller_contract'] == projection['caller_contract'] == capsule['model']['caller_contract'])
ck('all_current_heads', all(value['head'] == model['head'] for value in (q, capsule, projection, callee)))
ck('conditional_model_scopes', model['scope'] == generated['scope'] == checked['scope'] == coverage['scope']
   == capsule['scope'] == 'closed_caller_AST_composition_under_captured_callee_binding')
ck('model_goal_proved_no_counterexample', model['model_status'] == generated['model_status'] == 'model_proved'
   and model['model_counterexample'] is generated['model_counterexample'] is None)
ck('callee_model_proved', callee['status'] == 'model_proved' and callee['requested_model_theorem_proved'] is True)
ck('source_native_model_join', generated['projection_id'] == checked['projection_id'] == projection['projection_id']
   and generated['source_id'] == checked['source_id'] and generated['callee_result_cid'] == checked['callee_result_cid']
   == callee['result_cid'] == model['native_callee_result_cid'])
ck('full_source_paths', capsule['source_closure']['paths'] == model['paths'] == ['callee.py', 'caller.py', 'dynamic.py'])
for leaf in capsule['source_closure']['sources']:
    raw = bodies[str(U / 'actual-public-review-01/repository' / leaf['path'])]
    ck('current_source_leaf:' + leaf['path'], leaf['sha256'] == sha(raw) and leaf['bytes'] == len(raw))
for leaf in projection['sources']:
    raw = projection['source_texts'][leaf['path']].encode('ascii')
    ck('selected_source_exact:' + leaf['path'], raw == bodies[str(U / 'actual-public-review-01/repository' / leaf['path'])]
       and leaf['sha256'] == sha(raw) and leaf['bytes'] == len(raw) and leaf['cid'] == raw_cid_from_sha(sha(raw)))
ck('complete_coverage_join', capsule['coverage'] == model['coverage'] == coverage)
ck('main_residual_retained', len(capsule['residuals']) == 1 and capsule['residuals'][0]['path'] == 'dynamic.py')
ck('child_residuals_retained', [row['path'] for row in coverage['callee_owner_residuals_retained']] == ['caller.py', 'dynamic.py'])
ck('assumptions_exact', capsule['assumptions'] == {'caller': projection['assumptions'],
    'callee_translation': callee['translation']['assumptions'],
    'callee_compilation': projection['callee_projection']['compiled']['assumptions']}
    and capsule['opaque_call_model_assumption'] is True and capsule['native_call_opacity_preserved'] is True)
ck('checker_trust_boundaries', capsule['checker_dependencies']['trusted_compiled_imports'] == ['Init', 'IntegerLowering']
   and capsule['checker_dependencies']['axiom_inventory_carried'] is False
   and capsule['checker_dependencies']['axiom_inventory_expansion_required'] is True
   and capsule['checker_dependencies']['compiled_import_closure_attested'] is False
   and capsule['checker_dependencies']['callee_tool_policy'] == callee['tool_policy']
   and capsule['checker_dependencies']['callee_dependency_scope'] == callee['lean_certificate']['dependency_scope'])
for key, raw in [('projection', wire(projection)), ('generated', wire(generated)), ('lean_source', generated['lean_source'].encode())]:
    pin = capsule['expansion'][key]
    ck('known_generated_pin:' + key, pin['sha256'] == sha(raw) and pin['bytes'] == len(raw)
       and bodies[pin['path']] == raw)
for key in ('caller_object', 'callee_object'):
    pin = capsule['expansion'][key]
    raw = bodies[pin['path']]
    size = pin.get('bytes', pin.get('size_bytes'))
    ck('compiled_object_bytes_CID:' + key, pin['sha256'] == sha(raw) and size == len(raw)
       and pin['cid'] == raw_cid_from_sha(sha(raw)))
    ck('compiled_object_not_empty:' + key, len(raw) > 100000)
ck('imported_native_callee_exact', bodies[model['callee_object']['path']] == bodies[callee['artifacts']['lean_olean']['path']])

# Independent reconstruction of the exact native semantic-material wire tags.
class Record:
    def __init__(self, name, fields): self.name, self.fields = name, fields
class Enum:
    def __init__(self, name, value): self.name, self.value = name, value
def project(value):
    if isinstance(value, Record): return {'$record': value.name, 'fields': project(value.fields)}
    if isinstance(value, Enum): return {'$enum': value.name, 'value': project(value.value)}
    if type(value) is dict: return {'$mapping': {key: project(item) for key, item in sorted(value.items())}}
    if type(value) in (tuple, list): return {'$sequence': type(value).__name__, 'items': [project(item) for item in value]}
    return value
planner_source = bodies[str(C / 'benchmarks/agent_supervisor/container_coding/terminal_call_intent_planning.py')].decode()
tree = ast.parse(planner_source)
operations = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == 'OPERATIONS' for target in node.targets))
binding = cid({'schema': 'conditional-call-review-binding@1', 'capsule': capsule, 'intent_profile_id': profile['profile_id'],
    'head': model['head'], 'scope': model['paths'], 'operations': [list(value) for value in operations]})
planner_capsule = json.loads(wire(capsule))
planner_capsule['source_capsule_id'] = planner_capsule.pop('capsule_id')
planner_capsule['schema'] = 'terminal-call-proof-capsule-planner-projection@1'
planner_capsule['intent']['prompt_reference'] = planner_capsule['intent'].pop('prompt')
planner_capsule['reference_field_mapping'] = {'intent.prompt': 'intent.prompt_reference'}
planner_capsule['projection_id'] = cid(planner_capsule)
inverse = json.loads(wire(planner_capsule))
record_identity('planner_capsule_projection', inverse, 'projection_id')
inverse.pop('projection_id'); inverse.pop('reference_field_mapping')
inverse['schema'] = capsule['schema']; inverse['capsule_id'] = inverse.pop('source_capsule_id')
inverse['intent']['prompt'] = inverse['intent'].pop('prompt_reference')
ck('planner_projection_exact_inverse', inverse == capsule)
refs = (capsule['capsule_id'], profile['profile_id'], model['result_cid'])
og = 'ipfs_accelerate_py.agent_supervisor.planning.obligation_graph_compiler.'
goals, producers, tasks = [], [], []
for operation, meaning in operations:
    goal_id, producer_id, task_id = 'goal:call-review:' + operation, 'producer:call-review:' + operation, 'task:call-review:' + operation
    goals.append(Record(og+'TypedPredicate', {'predicate_id': goal_id, 'predicate_type': 'conditional_model_review_requirement',
        'subject_ref': model['head']['snapshot_cid'], 'object_ref': cid({'complete_binding': binding, 'operation': operation}),
        'polarity': Enum(og+'PredicatePolarity', 'positive'), 'support': Enum(og+'SemanticSupport', 'reviewed'),
        'property_id': '', 'provenance_refs': tuple(sorted(refs)), 'assumption_refs': (), 'invalidation_selectors': (),
        'proof_requirement_refs': (), 'validation_requirement_refs': ()}))
    producers.append(Record(og+'ProducerRule', {'producer_id': producer_id, 'effect_predicate_ids': (goal_id,),
        'required_predicate_ids': (), 'provenance_refs': tuple(sorted(refs)), 'assumption_refs': (), 'invalidation_selectors': (),
        'proof_requirement_refs': (), 'validation_requirement_refs': (), 'task_candidate_ids': (), 'executable': True}))
    tasks.append(Record(og+'TaskCandidate', {'candidate_id': task_id,
        'closes_obligation_ids': ('obligation:producer:' + producer_id + ':for:' + goal_id,), 'producer_id': producer_id,
        'depends_on_candidate_ids': (() if not tasks else (tasks[-1].fields['candidate_id'],)), 'provenance_refs': tuple(sorted(refs))}))
intent = Record(og+'TypedIntent', {'intent_id': 'intent:conditional-call-review', 'desired_predicates': tuple(goals),
    'source_refs': tuple(sorted(refs)), 'current_root_id': model['head']['snapshot_cid'], 'metadata': {}})
policy = Record('ipfs_accelerate_py.agent_supervisor.planning.plan_evaluator.EvidenceAwarePlanPolicy', {
    'acceptance_criteria': tuple(goal.fields['predicate_id'] for goal in goals), 'evidence_terms': refs,
    'trusted_assumptions': (), 'supported_semantics': (), 'satisfied_dependencies': (), 'allowed_scopes': ('scope:call-review',),
    'available_resource_classes': ('cpu',), 'max_estimated_resource_cost': 1000000.0,
    'max_estimated_tokens': 1000000000, 'max_estimated_runtime_seconds': 1000000.0, 'min_novelty': 0.0,
    'require_validation': True, 'require_proof': False})
frozen = Record('ipfs_accelerate_py.agent_supervisor.planning.adaptive_planner.FrozenPlanningGoal', {
    'goal_id': 'goal:conditional-call-review', 'goal_content_id': binding, 'repository_tree_id': model['head']['snapshot_cid'], 'policy': policy})
context = {'domain': 'conditional_call_evidence_review', 'repository_paths': model['paths'], 'complete_binding': binding,
    'task_metadata': {task.fields['candidate_id']: {'predicted_files': model['paths'], 'scope_ids': ['scope:call-review'],
        'resource_classes': ['cpu'], 'meaning': meaning} for task, (_, meaning) in zip(tasks, operations)}}
base_material = {'scan': None, 'query_plan': None, 'evidence_bundle': None, 'evidence_adapters': None,
    'evidence_queries': (), 'obligation_graph': None, 'intent': intent, 'current_facts': (), 'producers': tuple(producers),
    'task_candidates': tuple(tasks), 'predicates': (), 'frozen_goal': frozen, 'candidate_context': context,
    'model_provider': None, 'parallel_tasks': None, 'parallel_request': None, 'admission_materials': None,
    'current_roots': None, 'workflow_request': None,
    'extra': {'conditional_call_proof_capsule': planner_capsule, 'complete_binding': binding}}
original_capacity = selected['capacity.json']
pre_capacity_binding = selected['pre-capacity-binding.json']
for label, producer in [('capacity',original_capacity['producer']), ('query',q['producer']),
        ('capsule',capsule['producer']), ('current_preview',selected['capsule-preview.json']['producer'])]:
    ck('declared_producer_no_loaded_attestation:'+label, producer['loaded_module_code_attested'] is False)
    for declared_pin in producer['files']:
        read(declared_pin['path'], declared_pin)
for declared_pin in (inventory['producer'], preservation['producer']):
    read(declared_pin['path'], declared_pin)
pre_capacity_digests = {key: digest(b'plan-create-semantic-input\n' + key.encode() + b'\n' + wire(project(item), ascii=True))
    for key, item in base_material.items()}
pre_capacity_material = {'schema': 'ipfs_accelerate_py/agent-supervisor/plan-create-semantic-material-binding@1',
    'field_digests': pre_capacity_digests, 'unsupported_fields': {}, 'reuse_supported': True, 'opaque_material_nonce': ''}
pre_capacity_snapshot = {key: item for key, item in selected['capsule-preview.json']['native_preview']['input_snapshot'].items()
    if key not in ('snapshot_cid', 'material_binding')}
pre_capacity_snapshot['material_binding'] = pre_capacity_material
ck('pre_capacity_complete_material_snapshot', pre_capacity_binding['material_basis_cid']
   == digest(b'plan-create-input-snapshot\n' + wire(pre_capacity_snapshot, ascii=True)))
ck('pre_capacity_current_request_head_capsule', pre_capacity_binding == {
    'schema': 'terminal-call-review-capacity-input@1', 'head': model['head'],
    'request_cid': cid(selected['capsule-preview.json']['request']),
    'material_basis_cid': digest(b'plan-create-input-snapshot\n' + wire(pre_capacity_snapshot, ascii=True)),
    'capsule_id': capsule['capsule_id']})
record_identity('capacity_binding', original_capacity, 'binding_cid')
record_identity('capacity_initial_observation', original_capacity['initial_observation'], 'snapshot_id')
ck('capacity_original_input_binding', original_capacity['input_binding'] == pre_capacity_binding
   == original_capacity['initial_observation']['input_binding'])
ck('capacity_configuration_root', original_capacity['configuration_profile_cid'] == cid(original_capacity['configuration_profile'])
   == selected['capsule-preview.json']['request']['roots']['configuration_root'])
ck('capacity_freshness_policy_identity', original_capacity['initial_observation']['freshness_policy_cid']
   == cid(original_capacity['configuration_profile']['freshness_policy']))
resource_profile = {'cpu_slots': 1, 'process_slots': 1, 'memory_bytes': 64*1024**2, 'gpu_memory_bytes': 0,
    'disk_bytes': 0, 'resource_class': 'cpu-validation', 'resource_stage': 'validation', 'provider_requirement': '',
    'context_tokens': 0, 'output_token_budget': 0, 'quota_units': 0, 'cost_limit_micros': 0}
ck('capacity_exact_resource_profile', original_capacity['configuration_profile']['task_resource_profile'] == resource_profile)
reservation = original_capacity['reservation']
ck('capacity_original_reservation', reservation == original_capacity['initial_observation']['reservation']
   and reservation['cpu_slots'] == reservation['child_process_slots'] == 1 and reservation['memory_mb'] == 64
   and reservation['gpu_memory_mb'] == reservation['unified_memory_mb'] == 0 and reservation['requires_gpu'] is False
   and reservation['request_id'] == 'call-review-capacity:' + pre_capacity_binding['request_cid'])
for label, record in [('public_capacity',original_capacity), ('initial_capacity_observation',original_capacity['initial_observation']),
                      ('capacity_configuration',original_capacity['configuration_profile'])]:
    for key, value in record.items():
        if type(value) is bool: ck(label+':authority_false:'+key, value is False)
def no_secrets(value, prefix):
    if type(value) is dict:
        for key, item in value.items():
            ck(prefix+':no_secret_key:'+key, not any(marker in key.lower() for marker in
                ('lease_key', 'api_key', 'access_token', 'private_key', 'password')))
            no_secrets(item, prefix+'.'+key)
    elif type(value) is list:
        for item in value: no_secrets(item, prefix)
no_secrets(original_capacity, 'public_capacity')
base_material['extra'] = {**base_material['extra'], 'conditional_call_review_capacity': original_capacity}
review_task_fields = {'task_id','action_id','producer_id','goal_id','closes_obligation_ids','depends_on','produces',
    'required_leaf_ids','outputs','effects','changed_paths','predicted_paths','review_only','worktree_policy',
    'resource_contract','estimated_duration_ms','duration_semantics','read_only_inputs','completion_facts'}
false_names = ['proof_authority', 'execution_authority', 'completion_authority', 'mutation_authority', 'source_semantics_verified',
    'runtime_behavior_verified', 'source_body_executed', 'production_admitted', 'worker_launched', 'convergence_proved',
    'review_task_completion_proved', 'original_task_budget_satisfied', 'caller_record_origin_verified', 'network_isolation_enforced']
for name in ('expanded-preview.json', 'capsule-preview.json', 'final-current-preview.json'):
    value = selected[name]
    record_identity(name, value, 'result_cid')
    for key, item in value.items():
        if type(item) is bool:
            ck(name+':all_boolean_authorities_false:' + key, item is (key in {'review_forecast_accepted', 'native_parallel_stage_passed'}))
    false_fields(name, value, false_names)
    zero_fields(name, value, ['observed_behavior_facts', 'provider_calls', 'training_steps', 'checker_invocations'])
    ck(name+':capsule_head', value['capsule'] == capsule and value['head'] == model['head'])
    native, request = value['native_preview'], value['request']
    snap, receipt, structural = native['input_snapshot'], native['preview'], native['structural_context']
    ck(name+':structural_CID', native['structural_context_cid'] == cid(structural))
    ck(name+':request_CID', receipt['request_cid'] == snap['request_cid'] == cid(request))
    ck(name+':prompt_and_native_IR_roots', request['prompt_source_cid'] == cid({'schema': 'call-prompt-reference@1', **profile['prompt']})
       and request['roots']['intent_ir_root'] == cid({'schema': 'canonical-call-intent-reference@1',
           'sha256': profile['intent_document_sha256'], 'bytes': profile['intent_document_bytes']}))
    for role, key in [('policy', 'policy_root'), ('legal', 'legal_ir_root'), ('security', 'security_ir_root'),
                       ('provider', 'provider_catalog_root'), ('usage', 'usage_policy_root'), ('configuration', 'configuration_root')]:
        ck(name+':authored_policy_root:' + role, request['roots'][key] == cid(selected['policy.json'][role]))
    ck(name+':roots_and_scopes', receipt['roots'] == request['roots'] == snap['roots'] and request['scope_paths'] == model['paths']
       and structural['head'] == {key: item for key, item in model['head'].items() if key != 'schema'}
       and structural['semantic_state_cid'] == request['roots']['program_root'])
    ck(name+':model_off', request['budget']['max_model_calls'] == request['budget']['max_provider_tokens'] == 0
       and native['model_calls'] == native['observed_facts_supplied'] == 0 and receipt['mode'] == 'deterministic')
    ck(name+':review_only', receipt['verdict'] == 'review_only' and receipt['read_only'] is True and receipt['wrote_effects'] == [])
    material = dict(base_material)
    material['scan'] = {'scan_cid': native['structural_context_cid'], 'structural_codebase': structural}
    material['candidate_context'] = {**context, 'structural_codebase_context_cid': native['structural_context_cid'], 'structural_codebase': structural}
    material['extra'] = {**base_material['extra'], 'structural_codebase_context_cid': native['structural_context_cid'],
        'structural_codebase': structural, 'root_observation_profile': 'repository-live-root-observation@1'}
    expected_digests = {key: digest(b'plan-create-semantic-input\n' + key.encode() + b'\n' + wire(project(item), ascii=True))
        for key, item in material.items()}
    for field, expected in expected_digests.items():
        ck(name+':complete_material_digest:' + field, snap['material_binding']['field_digests'][field] == expected)
    ck(name+':reusable_complete_material', snap['material_binding']['reuse_supported'] is True
       and snap['material_binding']['unsupported_fields'] == {} and snap['material_binding']['opaque_material_nonce'] == '')
    ck(name+':snapshot_digest', snap['snapshot_cid'] == digest(b'plan-create-input-snapshot\n' + wire({key: item for key, item in snap.items() if key != 'snapshot_cid'}, ascii=True)))
    ck(name+':receipt_snapshot', receipt['input_snapshot_cid'] == snap['snapshot_cid'])
    expected_tasks = [task.fields['candidate_id'] for task in tasks]
    ck(name+':three_retained_tasks', value['selected_task_ids'] == expected_tasks == [task['task_id'] for task in value['review_projection']['tasks']])
    for position, task in enumerate(value['review_projection']['tasks']):
        ck(name+':task_dependency:' + task['task_id'], task['depends_on'] == ([] if position == 0 else [expected_tasks[position-1]]) and task['read_only_inputs']['source_paths'] == model['paths'])
    stages = {stage['stage']: stage for stage in receipt['stage_results']}
    ck(name+':seven_native_review_stages', all(stages[key]['passed'] is True for key in
       ('scan', 'query', 'evidence', 'obligation', 'candidate', 'critique', 'parallel_plan')))
    ck(name+':admission_only_missing_IR', stages['admission']['passed'] is False
       and stages['admission']['blockers'] == ['ir_admission_materials_absent']
       and receipt['rejection_reasons'] == ['ir_admission_materials_absent'])
    review = value['review_projection']
    record_identity(name+':review_projection', review, 'plan_id')
    ck(name+':application_extension_schema', review['schema'] == 'ipfs_accelerate_py/agent-supervisor/conditional-call-review-projection@1')
    for key, item in review.items():
        if type(item) is bool:
            ck(name+':projection_boolean_ceiling:'+key, item is (key in {'review_only','projection_data_validated'}))
    ck(name+':review_snapshot_full_bindings', review['material_snapshot_cid'] == snap['snapshot_cid']
       and review['material_binding'] == snap['material_binding'] and review['complete_binding'] == binding
       and review['head'] == model['head'] and review['source_capsule_id'] == capsule['capsule_id'])
    ck(name+':projection_no_write_or_completion', all(review[key] == [] for key in
       ('outputs','effects','changed_paths','predicted_paths','current_facts','completion_facts','completed_task_ids'))
       and review['review_only'] is True and review['worktree_policy'] == 'none')
    for position, task in enumerate(review['tasks']):
        goal, producer = goals[position], producers[position]
        ck(name+':closed_review_task:'+str(position), set(task) == review_task_fields
           and task['task_id'] == task['action_id'] == expected_tasks[position]
           and task['goal_id'] == goal.fields['predicate_id'] and task['producer_id'] == producer.fields['producer_id']
           and task['closes_obligation_ids'] == list(tasks[position].fields['closes_obligation_ids'])
           and task['required_leaf_ids'] == task['produces'] == [goal.fields['predicate_id']]
           and all(task[key] == [] for key in ('outputs','effects','changed_paths','predicted_paths','completion_facts'))
           and task['review_only'] is True and task['worktree_policy'] == 'none'
           and task['resource_contract'] == resource_profile and task['estimated_duration_ms'] == 1000
           and task['duration_semantics'] == 'bounded_forecast_not_observed_execution'
           and task['read_only_inputs'] == {'capsule_id': capsule['capsule_id'],
               'head_snapshot_cid': model['head']['snapshot_cid'], 'source_paths': model['paths'],
               'proof_expansion_cid': cid(capsule['expansion'])})
    expected_actions = [{'action_id':task.fields['candidate_id'], 'depends_on':list(task.fields['depends_on_candidate_ids']),
        'producer_id':producer.fields['producer_id'], 'goal_id':goal.fields['predicate_id'],
        'produces':[goal.fields['predicate_id']], 'effects':[], 'review_only':True}
        for task, goal, producer in zip(tasks,goals,producers)]
    ck(name+':exact_three_read_only_actions', review['actions'] == expected_actions)
    graph = review['obligation_graph']
    ck(name+':graph_identity', graph['graph_id'] == 'obligation-graph:sha256:' + sha(wire({key:item for key,item in graph.items() if key!='graph_id'})))
    ck(name+':six_open_graph_obligations', len(graph['nodes']) == 6 and all(node['status'] == 'open' for node in graph['nodes'])
       and graph['facts'] == graph['assumptions'] == graph['issues'] == [] and len(graph['root_obligation_ids']) == 3)
    for actual, expected in zip(graph['predicates'], goals):
        ck(name+':graph_complete_goal_binding:'+actual['predicate_id'], actual['predicate_id'] == expected.fields['predicate_id']
           and actual['predicate_type'] == expected.fields['predicate_type'] and actual['subject_ref'] == expected.fields['subject_ref']
           and actual['object_ref'] == expected.fields['object_ref'] and actual['provenance_refs'] == list(expected.fields['provenance_refs']))
    ck(name+':same_original_capacity', value['capacity'] == original_capacity and value['pre_capacity_binding'] == pre_capacity_binding)
    forecast, compilation = value['native_parallel_plan'], value['native_parallel_request']
    ck(name+':exact_native_parallel_request', forecast['replay_request'] == compilation and compilation['tasks'] == review['tasks']
       and compilation['review_only'] is True and compilation['required_leaf_ids'] == review['required_leaf_ids'])
    ck(name+':native_parallel_input_digest', forecast['input_digest'] == 'parallel-plan-input:sha256:' + sha(wire(compilation)))
    forecast_material = {key:item for key,item in forecast.items() if key not in
        ('plan_id','admitted','ready','deterministic_replay','replay_request')}
    ck(name+':native_parallel_plan_identity', forecast['plan_id'] == 'parallel-execution-plan:sha256:' + sha(wire(forecast_material)))
    ck(name+':parallel_review_only_zero_work', forecast['outcome'] == 'review_only' and forecast['admitted'] is True
       and forecast['ready'] is True and forecast['admitted_width'] == forecast['widths']['admitted_width'] == 0
       and all(forecast[key] == [] for key in ('execution_waves','assignments','merge_order','issues','conflicts')))
    expected_leaves = [goal.fields['predicate_id'] for goal in goals]
    ck(name+':native_logical_leaf_closure', forecast['leaf_producer_closure'] == {'closed': True,
        'required_leaf_ids': expected_leaves, 'producer_by_leaf_id': dict(zip(expected_leaves, expected_tasks)),
        'terminal_task_ids': [expected_tasks[-1]]})
    native_capacity = compilation['capacity_snapshot']
    record_identity(name+':native_capacity_snapshot', native_capacity, 'snapshot_id')
    expected_capacity_body = {key:item for key,item in original_capacity['initial_observation'].items() if key!='snapshot_id'}
    expected_capacity_body['capacity_binding_cid'] = original_capacity['binding_cid']
    ck(name+':original_observation_preserved', native_capacity == {**expected_capacity_body,
        'snapshot_id': cid(expected_capacity_body)} and forecast['capacity_snapshot_id'] == native_capacity['snapshot_id'])
    ck(name+':positive_private_clock_original_expiry', type(compilation['current_time_ms']) is int and compilation['current_time_ms'] > 0
       and native_capacity['observed_at_ms'] <= compilation['current_time_ms'] < compilation['deadline_ms']
       == native_capacity['fresh_until_ms'] and compilation['current_time_ms'] - native_capacity['observed_at_ms'] <= native_capacity['max_age_ms'])
    repository_snapshot = compilation['repository_snapshot']
    ck(name+':forecast_source_material_capacity_joins', repository_snapshot == {
        'tree_id': model['head']['snapshot_cid'], 'repository_tree_id': model['head']['snapshot_cid'], 'head': model['head'],
        'program_root': request['roots']['program_root'], 'candidate_plan_id': review['plan_id'],
        'candidate_plan_cid': cid(review), 'input_snapshot_cid': snap['snapshot_cid'],
        'capacity_binding_cid': original_capacity['binding_cid'], 'bound_material_snapshot_cid': snap['snapshot_cid']})
    ck(name+':three_review_dependencies', forecast['dependency_edges'] == [[expected_tasks[0],expected_tasks[1]],
       [expected_tasks[1],expected_tasks[2]]] and forecast['critical_path'] == expected_tasks
       and forecast['critical_path_duration_ms'] == forecast['estimated_makespan_ms'] == 3000)
    for when in ('cold_validation_before', 'cold_validation_after'):
        cold = value[when]
        ck(name+':'+when, cold['data_validated'] is True and cold['cache_status'] == 'hit'
           and cold['native_callee_integration_readback_passed'] is True and cold['native_callee_cold_validation_passed'] is True
           and cold['checker_reinvoked'] is False and cold['caller_record_origin_verified'] is False and cold['head'] == model['head'])

summary = selected['summary.json']
stable = ['input_snapshot_cid', 'obligation_graph_cid', 'candidate_portfolio_cid', 'critique_cid']
ck('reported_stable_fields', summary['stable_native_identity_fields'] == stable)
for field in stable:
    ck('actual_native_identity_parity:' + field, len({selected[name]['native_preview']['preview'][field]
       for name in ('expanded-preview.json', 'capsule-preview.json', 'final-current-preview.json')}) == 1)
ck('whole_review_projection_identical', selected['expanded-preview.json']['review_projection']
   == selected['capsule-preview.json']['review_projection'] == selected['final-current-preview.json']['review_projection'])
normalization_paths = ['input_digest','plan_id','deterministic_replay.input_digest','deterministic_replay.plan_id','replay_request.current_time_ms']
ck('only_five_named_forecast_normalizations', summary['normalization_exclusions'] == normalization_paths)
normalized = []
for name in ('expanded-preview.json','capsule-preview.json','final-current-preview.json'):
    forecast = json.loads(wire(selected[name]['native_parallel_plan']))
    forecast.pop('input_digest'); forecast.pop('plan_id')
    forecast['deterministic_replay'].pop('input_digest'); forecast['deterministic_replay'].pop('plan_id')
    forecast['replay_request'].pop('current_time_ms')
    normalized.append(forecast)
ck('complete_forecast_equal_except_enumerated_temporal_identity', normalized[0] == normalized[1] == normalized[2])
ck('complete_parallel_plan_ids_honestly_differ', summary['complete_parallel_plan_ids_equal'] is False
   and selected['expanded-preview.json']['native_parallel_plan']['plan_id'] != selected['capsule-preview.json']['native_parallel_plan']['plan_id'])
held, released = summary['held_resources_before_release'], summary['resources_after']
ck('one_native_held_quota', held['active_lease_count'] == held['active_root_lease_count'] == held['allocated_child_process_slots'] == 1
   and held['active_child_lease_count'] == held['waiting_request_count'] == 0 and held['allocated'] == {'cpu_slots':1,'memory_mb':64})
ck('all_native_quotas_released', all(released[key] == 0 for key in ('active_lease_count','active_root_lease_count',
   'active_child_lease_count','allocated_child_process_slots','waiting_request_count'))
   and released['allocated'] == {'cpu_slots':0,'memory_mb':0})
ck('remaining_admission_exactly_missing_IR', summary['remaining_admission_blockers'] == ['ir_admission_materials_absent']
   and summary['native_parallel_outcome'] == 'review_only' and summary['admitted_execution_width'] == 0)
for representation in ('expanded', 'capsule'):
    packet = selected[representation+'-packet.json']
    ck(representation+':whole_packet', packet['user_prompt'] == prompt and packet['head'] == model['head']
       and packet['capsule_id'] == capsule['capsule_id'] and packet['representation'] == representation
       and packet['context'] == ({'intent_profile': profile, 'query': q} if representation == 'expanded' else {'capsule': capsule})
       and packet['schema'] == 'terminal-call-review-context-packet@1'
       and packet['review_forecast_context'] == {'capacity': original_capacity, 'task_resource_profile': resource_profile,
           'writes': [], 'execution_width': 0, 'provider_calls': 0, 'completion_authority': False})
    raw = bodies[str(U / 'preview-run-04' / (representation+'-packet.json'))]
    measured = summary['packets'][representation]
    ck(representation+':offline_packet_measurement_pin', measured['bytes'] == len(raw) and measured['sha256'] == sha(raw))
ck('offline_exact_recorded_token_counts', summary['packets']['expanded']['tokens'] == 47608 and summary['packets']['capsule']['tokens'] == 9708)
ck('offline_reduction_arithmetic', summary['offline_input_token_reduction'] == 47608 - 9708 == 37900
   and summary['offline_reduction_basis_points'] == (47608 - 9708) * 10000 // 47608 == 7960)
ck('offline_tokenizer_method', method['library'] == 'tiktoken' and method['version'] == '0.13.0' and method['encoding'] == 'o200k_base')
ck('offline_tokenizer_no_approximation', method['approximation_used'] is False and method['offline'] is True)
ck('ten_actual_controls', len(summary['controls']) == 10 and all(row['rejected'] is True for row in summary['controls']))
expected_reasons = ['exact live capacity and independent policy observer required', 'intent/caller contract differs',
    'selected current review head differs', 'review context or original held capacity changed',
    'public directory witness changed', 'artifact custody changed', 'closed no-write fixed-resource review task required',
    'original sealed capacity control changed', 'independent current clock reversed or invalid',
    'review capacity reservation context is released']
for position, (control, reason) in enumerate(zip(summary['controls'], expected_reasons)):
    ck('actual_negative_control_reason:' + str(position), control['reason'] == reason and control['error_type'] in
       ('ValueError', 'CallReviewCapacityError', 'CodeSourceInspectionError'))
false_fields('actual_summary', summary, ['provider_token_savings_measured', 'production_admitted', 'worker_launched',
    'runtime_behavior_verified', 'full_task_satisfaction', 'convergence_proved', 'source_body_executed',
    'network_isolation_enforced', 'quack_transport_used'])
zero_fields('actual_summary', summary, ['provider_calls', 'training_steps', 'checker_invocations_during_planning'])
ck('only_three_fresh_qualification_Lean_processes', summary['fresh_qualification_lean_processes'] == 3)
ck('native_metadata_population', model['metadata']['row_count'] == 49 and len(model['metadata']['family_counts']) == 20
   and sum(model['metadata']['family_counts'].values()) == 49)
caller_process = json.loads(bodies[str(U / 'actual-public-review-01/model/process.json')])
callee_processes = json.loads(bodies[str(U / 'actual-public-review-01/model/callee/native-lowering/lean_process.json')])
for label, process in [('caller_compile', caller_process), ('callee_compile', callee_processes['process']),
                       ('Lean_version', callee_processes['version_process'])]:
    ck('retained_native_process:' + label, process['returncode'] == 0 and process['termination_reason'] == 'completed'
       and process['workspace_cleaned'] is True and all(process[key] is False for key in ('timed_out', 'cancelled',
           'resource_exhausted', 'unavailable', 'output_truncated', 'workspace_limit_exceeded')))
ck('excluded_preview_failure_history', history['selected_run'] == 'preview-run-04'
   and len(history['excluded_attempts']) == 8 and all(value['qualification'] is False for value in history['excluded_attempts']))
zero_fields('excluded_history', history, ['provider_calls', 'training_steps'])
ck('future_work_explicit', len(status['remaining_work']) == 5 and status['authority']['full_task_satisfaction'] is False
   and status['authority']['training_steps'] == status['authority']['provider_calls'] == 0)

for path, expected in list(pins.items()):
    raw = read(path, expected)
    ck('final_byte_stat_recapture:' + path, sha(raw) == expected['sha256'] and len(raw) == expected['bytes']
       and signature(Path(path).lstat()) == witnesses[path])
script_pin = {'path': str(Path(__file__).resolve()), 'sha256': sha(Path(__file__).read_bytes()), 'bytes': len(Path(__file__).read_bytes())}
critical_names = ['baseline-manifest.json', 'preservation-before-package.json', 'package-report.json', 'actual-public-inventory.json',
    'improvement-status.json', 'development-history.json', 'test-final-run.json', 'test-final.xml', 'stage-v.patch']
report = {'schema': 'terminal-call-review-forecast-independent-review@1', 'stage': 'V', 'passed': True, 'review_passed': True,
    'qualified': True, 'blockers': [], 'failed_checks': 0, 'check_count': len(checks), 'checks': checks,
    'selected_actual': 'preview-run-04', 'script': script_pin,
    'critical_pins': [pins[str(U / name)] for name in critical_names] + [pins[str(U / 'preview-run-04' / name)] for name in selected_names],
    'source_pins': [entry['source'] for entry in package['files']], 'read_input_count': len(pins),
    'read_input_pins': [pins[path] for path in sorted(pins)],
    'findings': {'closed_prompt_native_IntentIR_source_alignment': True, 'explicit_conditional_model_only': True,
        'selected_SQL_rows_export_source_head_joins': True, 'full_caller_and_callee_residuals_retained': True,
        'planner_projection_invertible': True, 'all_native_semantic_material_field_digests_reconstructed': True,
        'three_open_review_tasks_retained': True, 'native_review_forecast_accepted_zero_execution': True,
        'native_admission_retains_only_missing_IR_refusal': True,
        'original_held_capacity_and_pre_capacity_binding_reconstructed': True,
        'normalized_forecast_only_five_named_temporal_fields_excluded': True,
        'offline_packet_measurement_arithmetic_checked': True, 'public_artifact_bytes_checked': True,
        'predecessor_231_occurrences_preserved': True, 'tests_159_unique_no_failures': True,
        'patch_added_six_exact_files': True},
    'limits': ['Reviewer executed only bounded stdlib record/AST/hash/XML replay; no implementation imports, services, tests, prover, training, provider or source-body execution.',
        '47608 to 9708 o200k_base tokens is a recorded offline whole-packet comparison with the same original held-capacity descriptor; reviewer checked bytes, recorded method descriptors and arithmetic without rerunning tokenizer. No provider savings or benchmark behavior claim.',
        'Genuine deterministic candidate generation retained three open review tasks. Native parallel compiler accepted REVIEW_ONLY with width zero and no execution waves, assignments or merges; unchanged native admission refuses only missing IR materials. No work executes or completes.',
        'The native critic accepts the application extension namespace and applies structural checks. The application constructs and validates its own schema/CID; no native built-in custom-schema parser or proof-origin authentication is claimed.',
        'Parallel input/plan receipt identities differ because each compile samples an independent positive current time. Normalized comparison excludes exactly five named temporal/derived identity paths and retains every head, source, proof, material, original capacity, expiry, resource and task field.',
        'The held native CPU1/process1/64MiB quota is descriptive after release; serialized JSON cannot reconstruct the private live control or establish current capacity. Private state and lease secrets were not opened or emitted.',
        'Conditional captured AST/Int caller composition assumes the selected opaque call model. Python parsing/import/runtime/source origin and full task satisfaction remain unresolved.',
        'Compiled Init/IntegerLowering imports are trusted; capsule explicitly requires axiom-inventory expansion and carries no independent checker origin or transitive compiled-import closure attestation.',
        '113 named public current files and 231 predecessor/dependency preservation occurrences were read/hash checked. No DB, CAS, DuckLake or Parquet bodies were opened.',
        'Physical custody is bounded to declared named files and final stat/hash recapture; no whole filesystem or loaded/transitive environment attestation.',
        'Earlier preview candidates are excluded from selected-run qualification; existing source/runtime artifacts were not modified.'],
    'reviewer_jobs': {'services': 0, 'tests': 0, 'provers': 0, 'training': 0, 'providers': 0,
        'source_body_execution': 0, 'database_body_opens': 0, 'sealed_stage_writes': 0},
    'proof_authority': False, 'execution_authority': False, 'completion_authority': False,
    'runtime_behavior_verified': False, 'full_task_satisfaction': False, 'convergence_proved': False,
    'provider_token_savings_measured': False, 'loaded_module_code_attested': False,
    'transitive_dependency_closure_attested': False}
if '--publish' in sys.argv:
    target = U / 'independent-review.json'
    with target.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    target.chmod(0o600)
    print(json.dumps({'review_passed': True, 'qualified': True, 'checks': len(checks), 'read_inputs': len(pins),
        'review': {'path': str(target), 'sha256': sha(target.read_bytes()), 'bytes': target.stat().st_size}}))
else:
    print(json.dumps({'draft_passed': True, 'checks': len(checks), 'read_inputs': len(pins)}))
