"""Materialize actual supported scalar PyExpr source syntax in one bounded child.

Root alone executes this source job. Historical integrity is replayed from the
externally reviewed standalone checkpoint source before and after the child.
No historical private helper, original ranker, native prover, model or metadata
job executes. This is source-syntax evidence, not supervisor/proof admission.
"""
import argparse
import ast
import ctypes
import datetime
import hashlib
import json
import io
import tokenize
import struct
import os
from pathlib import Path
import re
import resource
import selectors
import signal
import stat
import subprocess
import sys
import time

W = Path('/home/barberb/lift_coding')
ROOT = W / 'maintenance/ranker-supported-python-ast-scalar-source-transport-20261007-01'
CANDIDATE = W / 'qualification/codebase_ir/ranker-supported-python-ast-source-transport-candidate-20261006-01'
REPLAY_ROOT = W / 'qualification/codebase_ir/ranker-qualification-checkpoint-replay-candidate-20261006-02'
AUTHORITY = {key: False for key in ('proof_authority', 'execution_authority', 'completion_authority', 'planner_activation')}
STAT_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
OUTPUT_ROOT = W / 'qualification/codebase_ir/ranker-supported-python-ast-scalar-source-host-result-20261007-01'
Q5 = W / 'qualification/codebase_ir/ranker-supported-python-ast-qualification-20261006-05'
CONTEXT_PATH = W / 'qualification/codebase_ir/ranker-supported-python-ast-scalar-source-transport-plan-20261007-01/context-01.json'
PLAN_KEYS = {'schema', 'producer_source_review', 'context', 'context_source_review', 'output_root'}
CONTEXT_KEYS = {'schema', 'accepted_request', 'accepted_helper', 'accepted_review', 'accepted_native_review',
                'recent_scope_policies', 'direct_inputs', 'expected_guard_count',
                'original_checkout_guards', 'protected_live_sources', *AUTHORITY}
REQUIRED_DIRECT = {'source', 'bindings', 'draft', 'grammar', 'grammar_check', 'host', 'host_interface',
                   'host_source_gate', 'host_controls', 'host_control_source_gate',
                   'fixture', 'fixture_audit', 'progress', 'next_gaps'}
FIXED_INPUTS = {
    'source': (16391, '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a'),
    'bindings': (25170, 'd6cb9f35169351848198d3919a7e794cee89429b07a2879ea680cb8511bfa8b8'),
    'draft': (13910, '4a7067a4797891740734fa7eae9ad46c02bc3410a4d4fff73ba43445a5a4ae17'),
    'grammar': (3916, '11baa458c201926c3a6e02b8ec7ca35213c336a30da199ce0390e3f1d7972faf'),
    'host': (43572, 'adb876326a54fde0481b52c838815c1cae65f62e918025e7444bc285a6854c0d'),
    'fixture': (299466, 'acfd1af4ccf740d9093d0b38468b25453c86f5683caddcc2dce12e067e91297d'),
    'fixture_audit': (3445, 'c5e93dc6f5c256feeb8337b48b03803a2f16ca299a6907f982297755fbb6daa5'),
}
NARROW_FALSE = {'source_parser_correctness_proved': False, 'actual_source_equivalence_proved': False,
                'normalization_preservation_proved': False, 'source_global_purity_proved': False,
                'Float_refinement_proved': False, 'original_loop_convergence_proved': False,
                'global_autoencoder_convergence_proved': False, 'strict_cache_admission': False,
                'metadata_hydration': False, 'candidate_compiled': False,
                'actual_new_qualified_queries': 0, 'full_task_satisfaction': 'unknown',
                'all32_governing_RPI_exits': 'OPEN', **AUTHORITY}



def need(value, message):
    if value is not True:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def parse(raw):
    def unique(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def signature(info):
    return tuple(getattr(info, key) for key in STAT_FIELDS)


def read_body(path, expected=None, capture=False):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path and not path.is_symlink(),
         'canonical nonsymlink input path required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and (not capture or before.st_size <= 32 * 1024**2),
             'regular bounded body required')
        digest, total, blocks = hashlib.sha256(), 0, []
        while block := os.read(fd, 1024**2):
            total += len(block)
            need(total <= before.st_size, 'body grew while reading')
            digest.update(block)
            if capture:
                blocks.append(block)
        need(signature(before) == signature(os.fstat(fd)) == signature(path.lstat())
             and path.resolve(strict=True) == path and not path.is_symlink() and total == before.st_size,
             'input body/stat changed while reading')
    finally:
        os.close(fd)
    found = {'path': str(path), 'bytes': total, 'sha256': digest.hexdigest()}
    if expected is not None:
        need(type(expected) is dict and set(expected) == {'path', 'bytes', 'sha256'} and found == expected,
             'exact input descriptor/body differs')
    return found, b''.join(blocks)


def exact(row, capture=False):
    need(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}
         and type(row['path']) is str and type(row['bytes']) is int and row['bytes'] >= 0
         and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}', row['sha256']) is not None,
         'exact canonical descriptor required')
    return read_body(row['path'], row, capture)[1]


def pin(path):
    return read_body(path)[0]


def document(row):
    return parse(exact(row, True))


def write(path, raw):
    need(type(raw) is bytes, 'output bytes required')
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return pin(path)


def gate_document(row):
    gate = document(row)
    need(gate['status'] == 'passed_source_only' and gate['findings'] == []
         and all(gate[key] is False for key in AUTHORITY), 'independent source-only gate required')
    return gate


def child_limits():
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024**2, 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def group_members(group):
    members = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            value = (entry / 'stat').read_text()
        except FileNotFoundError:
            continue
        tail = value[value.rfind(')') + 2:].split()
        need(len(tail) > 3, 'proc group observation malformed')
        if int(tail[2]) == group:
            members.append(int(entry.name))
    return sorted(members)


def close_group(process):
    """Kill/reap the complete subprocess group under the unchanged five seconds."""
    started = time.monotonic()
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=max(0.01, 5 - (time.monotonic() - started)))
    reaped = []
    while True:
        try:
            while True:
                pid, status = os.waitpid(-process.pid, os.WNOHANG)
                if pid == 0:
                    break
                reaped.append({'pid': pid, 'wait_status': status})
        except ChildProcessError:
            pass
        members = group_members(process.pid)
        if not members:
            break
        need(time.monotonic() - started < 5, 'subprocess group did not drain within cleanup bound')
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        time.sleep(0.02)
    if process.stdout is not None:
        process.stdout.close()
    return {'process_group': process.pid, 'reaped_adopted_children': reaped,
            'remaining_members': [], 'elapsed_seconds': time.monotonic() - started}


def add_rows(rows, additions):
    for row in additions:
        exact(row)
        need(row['path'] not in rows or rows[row['path']] == row, 'overlapping guarded descriptor changed')
        rows[row['path']] = row


def frozen_literal(helper):
    tree = ast.parse(exact(helper, True))
    values = [node.value for node in tree.body if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == 'FROZEN' for target in node.targets)]
    need(len(values) == 1, 'one literal FROZEN assignment required')
    frozen = ast.literal_eval(values[0])
    need(type(frozen) is dict and set(frozen) == {'REPLAY_SOURCE', 'CHECKPOINT', 'REPLAY_GATE',
        'MODULE_MAP', 'CANDIDATE_PINS', 'SOURCE_GATE', 'EXTRA_CONTEXT', 'CONTEXT_SEALS', 'STRICT_GUARD_COUNT'}
        and frozen['STRICT_GUARD_COUNT'] == 4230, 'exact accepted helper literal required; no helper execution')
    return frozen


def recent_census(policy):
    need(set(policy) == {'seal', 'scope_root', 'schema', 'regular_file_count', 'regular_file_bytes'},
         'closed recent scope policy required')
    seal = document(policy['seal'])
    scope, leaves = Path(policy['scope_root']), seal['files']
    need(scope.resolve(strict=True) == scope and not scope.is_symlink()
         and Path(policy['seal']['path']).parent == scope and seal['scope_root'] == str(scope)
         and seal['schema'] == policy['schema']
         and len(leaves) == len({row['path'] for row in leaves}) == seal['regular_file_count'] == policy['regular_file_count']
         and sum(row['bytes'] for row in leaves) == seal['regular_file_bytes'] == policy['regular_file_bytes']
         and hashlib.sha256(wire(leaves)).hexdigest() == seal['file_inventory_sha256']
         and seal['seal_self_excluded_from_files'] is True and seal['fixture_symlinks'] == seal['excluded_dependency_subtrees'] == []
         and all(Path(row['path']).is_relative_to(scope) for row in leaves)
         and all(seal[key] is False for key in AUTHORITY), 'exact immutable recent inventory metadata required')
    files, pending = set(), [scope]
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(Path(entry.path))
                elif stat.S_ISREG(info.st_mode):
                    files.add(str(Path(entry.path)))
                else:
                    raise ValueError('link or special file in recent sealed scope')
    need(files == {row['path'] for row in leaves} | {policy['seal']['path']}, 'complete recent physical census differs')
    return [policy['seal'], *leaves, seal['review']]


def check_context(context_pin, replay):
    """Fresh historical replay + literal recomputation; no body cache or helpers."""
    context = document(context_pin)
    need(set(context) == CONTEXT_KEYS and context['schema'] == 'ranker-supported-python-ast-scalar-source-transport-context@1'
         and context['expected_guard_count'] == 4230 and len(context['protected_live_sources']) == 4
         and all(context[key] is False for key in AUTHORITY), 'closed exact current context required')
    direct = context['direct_inputs']
    need(REQUIRED_DIRECT <= set(direct), 'required transport/source/context roles missing')
    for role, pair in FIXED_INPUTS.items():
        need((direct[role]['bytes'], direct[role]['sha256']) == pair, 'fixed source/fixture/API differs: ' + role)
    frozen = frozen_literal(context['accepted_helper'])
    need(direct['replay_source'] == frozen['REPLAY_SOURCE'] and direct['replay_manifest'] == frozen['CHECKPOINT']
         and direct['replay_source_review'] == frozen['REPLAY_GATE'], 'exact accepted standalone replay context required')
    old = replay(frozen['CHECKPOINT'])
    need(old['status'] == 'passed_file_only' and old['physical_scope_count'] == 47 and old['scope_count'] == 48
         and old['historical_helpers_executed'] == 0 and old['digest_cache_used'] is False,
         'complete fresh historical closure and 47 physical censuses required')
    checkpoint = document(frozen['CHECKPOINT'])
    request = document(context['accepted_request'])
    need(request['strict_guard_count'] == len(request['strict_old_inputs']) == 4230
         and request['protected_live_sources'] == context['protected_live_sources']
         and request['original_checkout_guards'] == context['original_checkout_guards'] == old['original_checkout_guards'],
         'current accepted request/checkout/protected rows differ')
    policies = context['recent_scope_policies']
    need(len(policies) == 15 and policies[:13] == frozen['CONTEXT_SEALS']
         and policies[13]['scope_root'] == str(Q5)
         and policies[14]['scope_root'] == str(W / 'qualification/codebase_ir/ranker-supported-python-ast-candidate-20261006-05'),
         'exact thirteen inherited plus current Q5/C5 physical policies required')
    rows = {row['path']: row for row in checkpoint['closure']}
    scope_rows = []
    for ordinal, policy in enumerate(policies):
        captured = recent_census(policy)
        scope_rows.extend(captured)
        if ordinal < 13:
            add_rows(rows, captured)
    add_rows(rows, [frozen['REPLAY_SOURCE'], frozen['CHECKPOINT'], frozen['REPLAY_GATE'], frozen['MODULE_MAP'],
                   *frozen['CANDIDATE_PINS'].values(), frozen['SOURCE_GATE'], *frozen['EXTRA_CONTEXT']])
    basis = [rows[path] for path in sorted(rows)]
    need(len(basis) == 4230 and basis == request['strict_old_inputs'], 'entire literal-rederived accepted 4230 basis differs')
    review = document(context['accepted_review'])
    witness = document(context['accepted_native_review'])
    need(review['status'] == 'qualified_supported_scalar_AST_ideal_real_observation_scope'
         and review['qualified_theorem_queries'] == 3 and review['actual_standard_axiom_reports'] == 6
         and review['root_resources_drained'] is True and review['native_caps_unchanged'] is True
         and witness['status'] == 'passed_file_only_completed_native_scope' and witness['findings'] == []
         and witness['actual_existing_qualified_queries_reviewed'] == 3
         and all(review[key] is witness[key] is False for key in AUTHORITY), 'genuine accepted scalar support review required')
    host_gate = gate_document(direct['host_source_gate'])
    need(direct['host'] in host_gate['candidate_pins'].values(), 'tested transport source gate differs')
    controls = document(direct['host_controls'])
    need(controls['status'] == 'passed' and controls['test_groups_passed'] == 20
         and controls['candidate_source_review'] == direct['host_source_gate']
         and controls['runner_source_review'] == direct['host_control_source_gate']
         and controls['supervisor_lease_claimed'] is False, 'actual twenty bounded tested transport controls required')
    audit = document(direct['fixture_audit'])
    need(audit['status'] == 'passed_file_only_source_fixture_scope' and audit['findings'] == []
         and audit['fixture'] == direct['fixture'] and audit['source'] == direct['source']
         and audit['counts']['scalar_occurrences'] == 29, 'independent exact source fixture audit required')
    grammar = document(direct['grammar_check'])
    need(grammar['status'] == 'passed' and grammar['native_lean_returncode'] == 0
         and (grammar['source']['bytes'], grammar['source']['sha256']) == FIXED_INPUTS['grammar'],
         'actual qualified grammar source body required')
    add_rows(rows, [*scope_rows, context['accepted_request'], context['accepted_helper'], context['accepted_review'],
                   context['accepted_native_review'], context_pin, *direct.values(), *context['protected_live_sources']])
    need(len(rows) == 4293 and sum(row['bytes'] for row in rows.values()) == 1286403819,
         'exact independently audited expanded current input denominator differs')
    return context, {'schema': 'ranker-supported-python-ast-scalar-source-context-readback@1',
        'status': 'passed_file_only', 'context': context_pin, 'accepted_basis_count': 4230,
        'complete_guard_count': len(rows), 'complete_guard_bytes': sum(row['bytes'] for row in rows.values()),
        'complete_guard_inventory_sha256': hashlib.sha256(wire([rows[p] for p in sorted(rows)])).hexdigest(),
        'historical_replay': old, 'recent_physical_scope_count': 15, 'historical_private_helper_execution_calls': 0,
        'accepted_helper_use': 'AST parse plus ast.literal_eval of FROZEN only', **AUTHORITY}


def fixture_body_joins(prefix, fixture, source):
    """Compare actual raw constructor occurrences with independently audited data."""
    text = source.decode('utf-8')
    byte_lines, text_lines, offsets = source.splitlines(keepends=True), text.splitlines(keepends=True), [0]
    for line in byte_lines:
        offsets.append(offsets[-1] + len(line))
    def token_offset(pair):
        return offsets[pair[0] - 1] + len(text_lines[pair[0] - 1][:pair[1]].encode('utf-8'))
    tokens = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if not token.string:
            continue
        first, last = token_offset(token.start), token_offset(token.end)
        need(source[first:last].decode('utf-8') == token.string, 'same source token byte slice differs')
        tokens.append({'absolute_utf8_byte_start': first, 'absolute_utf8_byte_end_exclusive': last,
            'start_line_column_codepoints': list(token.start), 'end_line_column_codepoints': list(token.end),
            'kind': tokenize.tok_name[token.type], 'token': token.string,
            'source_bytes': {'bytes': last - first, 'sha256': hashlib.sha256(source[first:last]).hexdigest()}})
    occurrence_map = prefix['raw_occurrences']
    records = []
    def joined(row):
        actual = occurrence_map[row['ast_path']]
        span = row['span_utf8_columns']
        first, last = offsets[span[0] - 1] + span[1], offsets[span[2] - 1] + span[3]
        need(actual['span'] == span and actual['node_kind'] == row['node_kind'] and actual['ast_dump'] == row['ast_dump']
             and actual['ast_sha256'] == row['ast_dump_utf8']['sha256']
             and len(actual['ast_dump'].encode()) == row['ast_dump_utf8']['bytes']
             and actual['source_segment'] == row['source_segment'] == source[first:last].decode('utf-8')
             and actual['source_segment_utf8_bytes'] == row['source_segment_utf8']['bytes'] == last - first
             and actual['source_segment_utf8_sha256'] == row['source_segment_utf8']['sha256']
             and row['absolute_utf8_byte_start'] == first and row['absolute_utf8_byte_end_exclusive'] == last,
             'actual source AST/span/byte/segment fixture join differs')
        if 'tokens' in row:
            need(row['tokens'] == [token for token in tokens if first <= token['absolute_utf8_byte_start']
                 and token['absolute_utf8_byte_end_exclusive'] <= last], 'actual source body token fixture join differs')
        return {'ast_path': row['ast_path'], 'ast_sha256': actual['ast_sha256'],
                'source_segment_sha256': actual['source_segment_utf8_sha256'], 'span': span}
    for occurrence in fixture['all_scalar_expression_occurrences']:
        records.append({'fixture': occurrence['fixture'], **joined(occurrence['source'])})
    need(len(records) == 29 and len({r['ast_path'] for r in records}) == 29
         and sum(r['fixture'] == 'loss' for r in records) == 10
         and sum(r['fixture'] == 'factor' for r in records) == 19, 'exact loss10/factor19 source occurrences required')
    selections = []
    descriptions = [
        ('loss', prefix['raw_program'][1]['rhs']['left']['arguments'][0], '$.raw_program[1].rhs.left.arguments[0]'),
        ('factor', prefix['raw_program'][3]['rhs'], '$.raw_program[3].rhs'),
    ]
    for f, (name, container, output_path) in zip(fixture['fixtures'], descriptions):
        need(f['name'] == name and container['tag'] == ('generatorExp' if name == 'loss' else 'listComp')
             and len(container['generators']) == 1, 'actual raw comprehension selection differs')
        comp = container['generators'][0]
        need(comp['tag'] == 'forIn' and comp['filters'] == [] and comp['asynchronous'] is False
             and comp['target']['tag'] == 'name', 'actual admitted raw comprehension fields differ')
        binder = comp['target']['identifier']
        need(binder['tag'] == 'PyName' and binder['spelling'] == 'z'
             and type(binder['scope']) is int and binder['scope'] > 0, 'actual scoped z identity required')
        context = f['comprehension_context']
        raw_scope = context['raw_scope_evidence_identity']
        scope_output = output_path + '.generators[0].target.identifier'
        scope_join = [j for j in prefix['raw_occurrence_joins'] if j['output_path'] == scope_output]
        need(len(scope_join) == 1 and scope_join[0]['source']['raw_path'] == raw_scope + '.target',
             'actual scoped target identity source join differs')
        for row in [f['body'], f['containing_assignment'], context['target'], context['iterable'], context['containing_expression']]:
            joined(row)
        selections.append({'name': name, 'body': container['body'], 'binder': binder,
            'body_output_path': output_path + '.body', 'raw_scope_evidence_identity': raw_scope,
            'body_source': f['body'], 'containing_assignment_source': f['containing_assignment'],
            'actual_target_output_path': scope_output, 'actual_target_source_join': scope_join[0]})
    need(selections[0]['binder']['scope'] != selections[1]['binder']['scope'], 'distinct actual raw generator scopes required')
    return selections, records


def compare_scalar_route(body, proposal, binder, output_path, source_joins, matched):
    p = proposal['source_ast_path']
    join = [j for j in source_joins if j['output_path'] == output_path]
    need(len(join) == 1 and join[0]['source']['raw_path'] == p, 'actual raw scalar constructor/source occurrence differs')
    tag, constructor = body['tag'], proposal['constructor']
    need(constructor == {'name': 'PyExpr.name', 'integer': 'PyExpr.integer', 'floatLiteral': 'PyExpr.floatLiteral',
        'unary': 'PyExpr.unary', 'binary': 'PyExpr.binary', 'call': 'PyExpr.call', 'compare': 'PyExpr.compare',
        'ifExp': 'PyExpr.ifExp'}[tag], 'actual independent scalar constructor differs')
    children = []
    if tag == 'name':
        need(body['name'] == binder and proposal['identifier']['spelling'] == binder['spelling'], 'actual scalar variable binder differs')
    elif tag == 'integer':
        need(body['value'] == proposal['value_decimal'] and body['token'] == proposal['token'], 'integer spelling/kind differs')
    elif tag == 'floatLiteral':
        literal = proposal['parsed_literal']
        need(body['token'] == proposal['token'] and body['numerator'] == literal['exact_ratio']['numerator']
             and body['denominator'] == literal['exact_ratio']['denominator']
             and body['binary64_hex'] == struct.pack('>d', float.fromhex(literal['hex'])).hex(), 'original finite float literal projection differs')
    elif tag == 'unary':
        need(body['operator'] == 'neg' and proposal['operator'] == 'PyUnary.usub', 'unary grouping differs')
        children = [(body['operand'], proposal['operand'], '.operand')]
    elif tag == 'binary':
        need(body['operator'] == proposal['operator'], 'binary operator/grouping differs')
        children = [(body[k], proposal[k], '.' + k) for k in ('left', 'right')]
    elif tag == 'call':
        actual, candidate = body['callee'], proposal['callee']
        if actual['tag'] == 'name':
            need(actual['identifier']['scope'] == 0 and actual['identifier']['spelling'] == candidate['raw_spelling'], 'fixed model name callee differs')
        else:
            need(actual['base']['scope'] == 0 and actual['base']['spelling'] == candidate['base_spelling'] == 'math'
                 and actual['member'] == candidate['member'], 'fixed model attribute callee differs')
        need(len(body['arguments']) == len(proposal['ordered_arguments']), 'ordered call arity differs')
        children = [(b, c, f'.arguments[{i}]') for i, (b, c) in enumerate(zip(body['arguments'], proposal['ordered_arguments']))]
    elif tag == 'compare':
        need(body['operator'] == 'ge' and proposal['operator'] == 'PyCompare.ge'
             and body['right']['tag'] == 'integer' and body['right']['value'] == '0', 'actual integer-zero comparison differs')
        children = [(body[k], proposal[k], '.' + k) for k in ('left', 'right')]
    elif tag == 'ifExp':
        children = [(body['test'], proposal['test'], '.test'), (body['then'], proposal['then'], '.then'),
                    (body['otherwise'], proposal['otherwise'], '.otherwise')]
    matched.append({'output_path': output_path, 'raw_source_path': p, 'constructor': constructor,
                    'actual_output_subtree_sha256': join[0]['output_subtree_sha256']})
    for b, c, suffix in children:
        compare_scalar_route(b, c, binder, output_path + suffix, source_joins, matched)


def child_main(args):
    own = pin(Path(__file__).resolve())
    need(own['sha256'] == args.expected_source_sha256, 'held child source differs')
    child_pin = pin(args.child_plan)
    need(child_pin['sha256'] == args.child_plan_sha256, 'held child plan differs')
    plan = document(child_pin)
    need(set(plan) == {'schema', 'worker_source', 'inputs', 'output_root', 'context', 'producer_review'}
         and plan['schema'] == 'ranker-supported-python-ast-scalar-source-child-plan@1'
         and plan['worker_source'] == own and plan['output_root'] == str(OUTPUT_ROOT), 'exact held child plan required')
    inputs = plan['inputs']
    need(set(inputs) == {'host', 'source', 'bindings', 'draft', 'grammar', 'fixture'}, 'fixed held scalar transport roles required')
    buffers = {role: exact(row, True) for role, row in inputs.items()}
    for role, raw in buffers.items():
        need((len(raw), hashlib.sha256(raw).hexdigest()) == FIXED_INPUTS[role], 'held original fixture/host/API body differs')
    host = {'__file__': inputs['host']['path'], '__name__': 'held_tested_python_ast_transport'}
    exec(compile(buffers['host'], inputs['host']['path'], 'exec'), host)
    # Exactly ONE public transport call; no verifier/emitter API calls that
    # reparse/transport the prefix a second time. Two scalar syntax renders.
    prefix = host['transport_prefix'](buffers['source'], buffers['bindings'], buffers['draft'])
    fixture = parse(buffers['fixture'])  # Orchestration JSON; not host decode_json.
    need(prefix['source_bound_actual_prefix'] is True and prefix['source_execution_calls'] == 0
         and prefix['new_qualified_queries'] == 0 and host['LEAN_API_PIN'] == {'bytes': inputs['grammar']['bytes'], 'sha256': inputs['grammar']['sha256']},
         'actual source-bound host syntax/API receipt required')
    selections, records = fixture_body_joins(prefix, fixture, buffers['source'])
    matched = []
    for selection, f in zip(selections, fixture['fixtures']):
        compare_scalar_route(selection['body'], f['independent_supported_scalar_route'], selection['binder'],
                             selection['body_output_path'], prefix['raw_occurrence_joins'], matched)
    need(len(matched) == 29 and len({m['raw_source_path'] for m in matched}) == 29, 'all actual scalar nodes must join the29 independent occurrences')
    duplicate = fixture['factor_duplicate_exp_negative_occurrence_paths']
    need(len(duplicate) == 2 and all(sum(m['raw_source_path'] == path for m in matched) == 1 for path in duplicate),
         'both distinct original exp(-z) occurrences retained')
    loss, factor = selections
    loss_text, factor_text = host['_lean_expr'](loss['body']), host['_lean_expr'](factor['body'])
    module = ('import PyAstNumericSubset\n\nopen RankerSupportedPythonAstReal\n\n'
        '/- Actual held raw scalar syntax only. Parser/global binding/Float/model preservation remains unproved. -/\n'
        'namespace GeneratedPythonAstScalarSource\n\n'
        'def lossBinder : PyName := ' + host['_lean_name'](loss['binder']) + '\n'
        'def factorBinder : PyName := ' + host['_lean_name'](factor['binder']) + '\n'
        'def lossScope : List PyName := [lossBinder]\n'
        'def factorScope : List PyName := [factorBinder]\n\n'
        'def actualLossBody : PyExpr := ' + loss_text + '\n\n'
        'def actualFactorBody : PyExpr := ' + factor_text + '\n\n'
        'theorem loss_binder_spelling : lossBinder.spelling = "z" := by rfl\n'
        'theorem factor_binder_spelling : factorBinder.spelling = "z" := by rfl\n'
        'theorem scalar_binders_distinct : lossBinder.scope ≠ factorBinder.scope := by decide\n\n'
        '#print axioms loss_binder_spelling\n#print axioms factor_binder_spelling\n#print axioms scalar_binders_distinct\n\n'
        'end GeneratedPythonAstScalarSource\n')
    need('SourceExpr' not in module and 'SourceTerm' not in module, 'generated raw syntax must not import target model/IR constructors')
    output = Path(plan['output_root'])
    need(output.resolve(strict=True) == output and not output.is_symlink() and list(output.iterdir()) == [], 'fresh empty canonical output scope required')
    prefix_pin = write(output / 'prefix-transport-receipt-01.json', host['canonical'](prefix) + b'\n')
    joins = {'schema': 'ranker-supported-python-ast-actual-scalar-source-joins@1', 'context': plan['context'],
        'inputs': inputs, 'prefix_receipt': prefix_pin, 'selections': selections, 'source_occurrence_joins': records,
        'actual_scalar_constructor_joins': matched, 'factor_duplicate_exp_negative_occurrence_paths': duplicate,
        'selected_trees': 'raw_program only; no dot/L2/alias normalization of either selected scalar body',
        'minimal_scopes': {'loss': [loss['binder']], 'factor': [factor['binder']]},
        'fixed_model_callees': ['scope0 abs', 'scope0 max', 'scope0 math.exp', 'scope0 math.log1p'],
        'source_global_binding_or_purity_proved': False, **NARROW_FALSE}
    joins_pin = write(output / 'scalar-source-joins-01.json', wire(joins) + b'\n')
    module_pin = write(output / 'GeneratedPythonAstScalarSource.lean', module.encode('utf-8'))
    receipt = {'schema': 'ranker-supported-python-ast-actual-scalar-source-materialization@1', 'status': 'source_only_materialized_uncompiled',
        'worker': own, 'child_plan': child_pin, 'context': plan['context'], 'producer_review': plan['producer_review'],
        'inputs': inputs, 'prefix_receipt': prefix_pin, 'source_joins': joins_pin, 'generated_module': module_pin,
        'module_name': 'GeneratedPythonAstScalarSource', 'prospective_queries': ['GeneratedPythonAstScalarSource.loss_binder_spelling',
            'GeneratedPythonAstScalarSource.factor_binder_spelling', 'GeneratedPythonAstScalarSource.scalar_binders_distinct'],
        'source_transport_calls': 1, 'scalar_lean_render_calls': 2, 'source_AST_parse_calls_in_tested_host': 1,
        'original_source_function_calls': 0, 'native_jobs': 0, 'tests': 0, 'model_jobs': 0, 'metadata_jobs': 0,
        'scalar_source_occurrences_joined': 29, 'actual_host_scopes': {'loss': loss['binder'], 'factor': factor['binder']},
        'full_prefix_dot_L2_normalized_metadata': 'unproved context only; neither selected raw scalar tree uses it', **NARROW_FALSE}
    materialization = write(output / 'scalar-transport-receipt-01.json', wire(receipt) + b'\n')
    for row in inputs.values():
        exact(row)
    print(json.dumps({'status': receipt['status'], 'receipt': materialization, 'source_transport_calls': 1,
                      'native_jobs': 0, 'actual_new_qualified_queries': 0}))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--plan-sha256')
    parser.add_argument('--expected-source-sha256', required=True)
    parser.add_argument('--child-plan', type=Path)
    parser.add_argument('--child-plan-sha256')
    args = parser.parse_args()
    need(__debug__ and re.fullmatch('[0-9a-f]{64}', args.expected_source_sha256) is not None, 'external exact producer pin required')
    if args.child_plan is not None:
        need(args.plan is None and args.plan_sha256 is None and args.child_plan_sha256 is not None
             and re.fullmatch('[0-9a-f]{64}', args.child_plan_sha256) is not None, 'exclusive held child mode required')
        return child_main(args)
    need(args.plan is not None and args.child_plan_sha256 is None and args.plan_sha256 is not None
         and re.fullmatch('[0-9a-f]{64}', args.plan_sha256) is not None, 'externally pinned parent plan required')
    own = pin(Path(__file__).resolve())
    need(own['path'] == str(ROOT / 'run_transport_01.py') and own['sha256'] == args.expected_source_sha256, 'exact fixed producer source differs')
    plan_pin = pin(args.plan)
    need(plan_pin['sha256'] == args.plan_sha256, 'exact external plan differs')
    plan = document(plan_pin)
    need(set(plan) == PLAN_KEYS and plan['schema'] == 'ranker-supported-python-ast-scalar-source-transport-plan@1'
         and plan['output_root'] == str(OUTPUT_ROOT) and plan['context']['path'] == str(CONTEXT_PATH), 'closed fixed parent source plan required')
    source_gate = gate_document(plan['producer_source_review'])
    need(source_gate['reviewed_source'] == own, 'independent exact producer source gate required')
    context_gate = document(plan['context_source_review'])
    need(context_gate['status'] == 'passed_file_only_source_transport_context' and context_gate['findings'] == []
         and context_gate['context'] == plan['context'] and all(context_gate[key] is False for key in AUTHORITY),
         'independent exact source-context file-only gate required')
    context = document(plan['context'])
    need(set(context) == CONTEXT_KEYS and context['schema'] == 'ranker-supported-python-ast-scalar-source-transport-context@1',
         'closed pinned current source context required')
    direct = context['direct_inputs']
    need(REQUIRED_DIRECT <= set(direct), 'required source fixture roles missing')
    frozen = frozen_literal(context['accepted_helper'])
    replay_gate = gate_document(direct['replay_source_review'])
    need(replay_gate['reviewed_sources'] == [direct['replay_source'], direct['replay_manifest']]
         and direct['replay_source'] == frozen['REPLAY_SOURCE'] and direct['replay_manifest'] == frozen['CHECKPOINT'],
         'exact externally reviewed standalone replay source/manifest required')
    run = ROOT / 'run-01'
    run.mkdir()
    held = run / 'held-source'
    held.mkdir()
    copies, captures = [], {}
    originals = {'worker': own, 'replay': direct['replay_source'],
                 **{role: direct[role] for role in ('host', 'source', 'bindings', 'draft', 'grammar', 'fixture')}}
    for role, original in originals.items():
        out = held / (role + '-' + Path(original['path']).name)
        write(out, exact(original, True))
        out.chmod(0o444)
        captured = pin(out)
        need((captured['bytes'], captured['sha256']) == (original['bytes'], original['sha256']), 'held body differs')
        copies.append({'role': role, 'original': original, 'captured': captured})
        captures[role] = captured
    # Only this standalone stdlib source executes in the parent. The Q5 helper
    # namespace is never imported or compiled. Replay has no historical chain.
    replay_source = exact(captures['replay'], True)
    namespace = {'__file__': captures['replay']['path'], '__name__': 'held_reviewed_standalone_history_replay'}
    exec(compile(replay_source, captures['replay']['path'], 'exec'), namespace)
    history_calls = [0]
    def replay(manifest_pin):
        history_calls[0] += 1
        return namespace['replay'](manifest_pin)
    context, before = check_context(plan['context'], replay)
    parent_pins = [own, plan_pin, plan['producer_source_review'], plan['context_source_review'], plan['context']]
    for row in parent_pins:
        exact(row)
    OUTPUT_ROOT.mkdir()
    child_plan = {'schema': 'ranker-supported-python-ast-scalar-source-child-plan@1', 'worker_source': captures['worker'],
        'inputs': {role: captures[role] for role in ('host', 'source', 'bindings', 'draft', 'grammar', 'fixture')},
        'output_root': str(OUTPUT_ROOT), 'context': plan['context'], 'producer_review': plan['producer_source_review']}
    child_pin = write(run / 'child-plan-01.json', wire(child_plan) + b'\n')
    Path(child_pin['path']).chmod(0o444)
    libc = ctypes.CDLL(None, use_errno=True)
    need(libc.prctl(36, 1, 0, 0, 0) == 0, 'Linux child subreaper setup failed')
    argv = [sys.executable, '-I', '-B', captures['worker']['path'], '--child-plan', child_pin['path'],
            '--child-plan-sha256', child_pin['sha256'], '--expected-source-sha256', own['sha256']]
    env = {'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'}
    process = selector = None
    output, cleanup = bytearray(), []
    error, returncode, closure, after, materialization = None, None, None, None, None
    started = time.monotonic()
    try:
        process = subprocess.Popen(argv, cwd=run, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            start_new_session=True, preexec_fn=child_limits)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        while selector.get_map():
            need(time.monotonic() - started <= 45, 'source child wall timeout')
            for key, _ in selector.select(timeout=0.2):
                block = os.read(key.fileobj.fileno(), 8192)
                if not block:
                    selector.unregister(key.fileobj)
                else:
                    need(len(output) + len(block) <= 65536, 'source child stdout cap')
                    output.extend(block)
        returncode = process.wait(timeout=max(0.01, 45 - (time.monotonic() - started)))
        need(returncode == 0 and time.monotonic() - started <= 45, 'bounded source child did not pass')
        paths = list(OUTPUT_ROOT.iterdir())
        need(all(path.is_file() and not path.is_symlink() for path in paths)
             and {p.name for p in paths} == {'prefix-transport-receipt-01.json', 'scalar-source-joins-01.json',
                 'GeneratedPythonAstScalarSource.lean', 'scalar-transport-receipt-01.json'}, 'exact four actual source output files required')
        materialization = document(pin(OUTPUT_ROOT / 'scalar-transport-receipt-01.json'))
        need(materialization['status'] == 'source_only_materialized_uncompiled'
             and materialization['source_transport_calls'] == 1 and materialization['scalar_lean_render_calls'] == 2
             and materialization['scalar_source_occurrences_joined'] == 29 and materialization['worker'] == captures['worker']
             and materialization['child_plan'] == child_pin and materialization['context'] == plan['context']
             and all(materialization[key] == value for key, value in NARROW_FALSE.items()), 'exact source-only actual materialization receipt required')
        for key in ('prefix_receipt', 'source_joins', 'generated_module'):
            exact(materialization[key])
    except BaseException as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
    finally:
        if selector is not None:
            selector.close()
        if process is not None:
            try:
                closure = close_group(process)
                returncode = process.returncode
            except BaseException as exc:
                cleanup.append({'stage': 'strict_process_group_cleanup', 'message': str(exc)})
        try:
            for row in [*parent_pins, child_pin, *(copy['captured'] for copy in copies)]:
                exact(row)
            for copy in copies:
                need(stat.S_IMODE(Path(copy['captured']['path']).stat().st_mode) == 0o444, 'held readonly source mode changed')
            _, after = check_context(plan['context'], replay)
            comparable = set(before) - {'historical_replay'}
            need(set(before) == set(after) and all(before[k] == after[k] for k in comparable), 'whole fresh current guard inventory changed')
            old_keys = set(before['historical_replay']) - {'elapsed_seconds'}
            need(all(before['historical_replay'][k] == after['historical_replay'][k] for k in old_keys), 'whole fresh historical replay changed')
        except BaseException as exc:
            cleanup.append({'stage': 'fresh_original_and_held_source_context_readback', 'message': str(exc)})
    stdout_pin = write(run / 'source-stdout.log', bytes(output))
    passed = error is None and cleanup == [] and closure is not None and after is not None and materialization is not None
    receipt = {'schema': 'ranker-supported-python-ast-bounded-scalar-source-transport-job@1', 'status': 'passed' if passed else 'failed',
        'producer': own, 'plan': plan_pin, 'producer_source_review': plan['producer_source_review'],
        'context_source_review': plan['context_source_review'], 'context': plan['context'], 'before': before, 'after': after,
        'captured_sources_and_buffers': copies, 'child_plan': child_pin, 'source_materialization': materialization,
        'ordinary_bounded_source_job': True, 'supervisor_lease_claimed': False, 'source_transport_calls': 1 if materialization else None,
        'source_transport_call_count_observed_in_actual_receipt': materialization is not None,
        'standalone_historical_replay_calls': history_calls[0], 'historical_private_helper_execution_calls': 0,
        'accepted_helper_execution_calls': 0, 'original_source_function_calls': 0,
        'native_jobs': 0, 'tests': 0, 'model_jobs': 0, 'metadata_jobs': 0,
        'returncode': returncode, 'process_group_closure': closure, 'primary_error': error, 'cleanup_errors': cleanup,
        'stdout': stdout_pin, 'output_scope': str(OUTPUT_ROOT), 'limits': {'wall_seconds': 45, 'cpu_seconds': 20,
            'memory_bytes': 1024**3, 'per_file_bytes': 1024**2, 'stdout_bytes': 65536, 'cleanup_seconds': 5},
        'child_and_readback_elapsed_seconds': time.monotonic() - started,
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), **NARROW_FALSE}
    closed = write(run / 'closed.json', wire(receipt) + b'\n')
    print(json.dumps({'status': receipt['status'], 'receipt': closed, 'primary_error': error, 'cleanup_errors': cleanup,
                      'source_transport_calls': receipt['source_transport_calls'], 'actual_new_qualified_queries': 0}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
