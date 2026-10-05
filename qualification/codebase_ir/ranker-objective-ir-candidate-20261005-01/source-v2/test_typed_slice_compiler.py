"""UNEXECUTED pure AST/IR controls for the objective scalar candidate.

No original ranker imports or objective/gradient evaluations occur. Native,
process and libm evaluation calls are blocked within every future test case.
All assertions concern source syntax, exact literal extraction or inert output.
"""
import ast
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

import pytest
import objective_scalar_compiler as compiler


SOURCE = Path(os.environ.get('RANKER_AST_SOURCE', '/home/barberb/lift_coding/artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-intent-corpus-head-20261004-01/source/benchmarks/agent_supervisor/container_coding/terminal_codebase_intent_ranker_training.py'))
LOSS_SHA = 'b71027e5d37d1a5b5b574a4b880a0857f0885dbc19c81dff3e652f8f7c76287e'
FACTOR_SHA = 'a5f60c17cb8efc0869ec1ac4001c04c1b43f67d7d38bc025cbb87061247d70aa'


@pytest.fixture(autouse=True)
def prohibit_process_and_libm_evaluation(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('pure source controls may not execute native/process/libm work')
    for name in ['Popen', 'run', 'call', 'check_call', 'check_output']:
        monkeypatch.setattr(subprocess, name, blocked)
    monkeypatch.setattr(os, 'system', blocked)
    monkeypatch.setattr(math, 'exp', blocked)
    monkeypatch.setattr(math, 'log1p', blocked)


@pytest.fixture
def source_bytes():
    raw = SOURCE.read_bytes()
    assert len(raw) == 16391 and hashlib.sha256(raw).hexdigest() == compiler.SOURCE_SHA256
    return raw


def lower(expression, bindings=None):
    return compiler.compile_scalar_ast(ast.parse(expression, mode='eval').body,
                                       {'z': 0} if bindings is None else bindings)


def canonical(raw):
    return compiler.compile_objective_scalar_slices(raw,
        expected_stable_loss_ast_sha256=LOSS_SHA, expected_stable_factor_ast_sha256=FACTOR_SHA)


def changed(raw, old, new):
    assert raw.count(old) == 1
    mutated = raw.replace(old, new, 1)
    module = ast.parse(mutated)
    function = next(n for n in module.body if type(n) is ast.FunctionDef and n.name == '_objective')
    return mutated, hashlib.sha256(mutated).hexdigest(), compiler._ast_sha(function)


SUPPORTED = [
    ('z', 'var'), ('0', 'num'), ('0.0', 'num'), ('0.01', 'num'), ('-z', 'neg'),
    ('abs(z)', 'abs'), ('z + 1', 'add'), ('z - 1', 'sub'), ('z * 1', 'mul'),
    ('z / 1', 'div'), ('max(0.0, -z)', 'max'), ('math.exp(z)', 'exp'),
    ('math.log1p(z)', 'log1p'), ('1 if z >= 0 else 2', 'ifNonneg'),
    ('math.exp(-z)/(1+math.exp(-z)) if z>=0 else 1/(1+math.exp(z))', 'ifNonneg'),
]


@pytest.mark.parametrize('expression,kind', SUPPORTED)
def test_supported_generic_operation_structure(expression, kind):
    result = lower(expression)
    assert result['source_scalar']['kind'] == result['ir']['body']['kind'] == kind
    assert result['ir']['slots'] == 1
    assert compiler.validate_scalar_ir(result['ir']) >= 1


REFUSED = [
    ('unknown', 'unknownName'), ('True', 'unsupportedLiteral'), ('"0"', 'unsupportedLiteral'),
    ('None', 'unsupportedLiteral'), ('1j', 'unsupportedLiteral'), ('1e309', 'unsupportedLiteral'),
    ('z ** 2', 'unsupportedNode'), ('z // 2', 'unsupportedNode'), ('z % 2', 'unsupportedNode'),
    ('+z', 'unsupportedNode'), ('not z', 'unsupportedNode'), ('z and z', 'unsupportedNode'),
    ('z[0]', 'unsupportedNode'), ('z.attr', 'unsupportedNode'), ('[z]', 'unsupportedNode'),
    ('(z, z)', 'unsupportedNode'), ('lambda: z', 'unsupportedNode'),
    ('math.log(z)', 'unsupportedCallTarget'), ('exp(z)', 'unsupportedCallTarget'),
    ('other.exp(z)', 'unsupportedCallTarget'), ('math.exp()', 'wrongArity'),
    ('abs(z, z)', 'wrongArity'), ('max(z)', 'wrongArity'), ('math.exp(x=z)', 'keywordArguments'),
    ('z if z > 0 else -z', 'unsupportedComparison'),
    ('z if z >= 1 else -z', 'unsupportedComparison'),
    ('z if 0 <= z else -z', 'unsupportedComparison'),
    ('z if z >= False else -z', 'unsupportedComparison'),
    ('z if z >= 0 >= z else -z', 'unsupportedComparison'),
    ('z >= 0', 'unsupportedNode'),
]


@pytest.mark.parametrize('expression,reason', REFUSED)
def test_unsupported_expression_is_explicit_refusal(expression, reason):
    with pytest.raises(compiler.CompileRefusal) as error:
        lower(expression)
    assert error.value.reason_code == reason


@pytest.mark.parametrize('expression', ['z if 0 >= 0 else z[0]', 'z[0] if 0 >= 0 else z'])
def test_malformed_dead_branch_is_still_refused(expression):
    with pytest.raises(compiler.CompileRefusal):
        lower(expression)


@pytest.mark.parametrize('expression,bindings', [
    ('abs(z)', {'z': 0, 'abs': 1}), ('max(z,z)', {'z': 0, 'max': 1}),
    ('math.exp(z)', {'z': 0, 'math': 1}), ('math.log1p(z)', {'z': 0, 'math': 1}),
])
def test_lexically_shadowed_builtin_target_is_refused(expression, bindings):
    with pytest.raises(compiler.CompileRefusal) as error:
        lower(expression, bindings)
    assert error.value.reason_code == 'unsupportedCallTarget'


@pytest.mark.parametrize('expression', ['1 / 0', 'math.log1p(-1)', 'math.log1p(-2)'])
def test_domain_sensitive_syntax_is_not_claimed_successful(expression):
    result = lower(expression)
    assert result['ir']['body']['kind'] in {'div', 'log1p'}
    # A supported syntax is not a proof of its evaluation domain. No evaluator
    # call or desired exact-real value is used by this pure source control.
    assert 'value' not in result and 'evaluated' not in result


def test_float_literal_is_exact_binary64_ratio():
    number = lower('0.01')['ir']['body']
    assert number == {'kind': 'num', 'numerator': '5764607523034235',
                      'denominator': '576460752303423488'}
    assert (number['numerator'], number['denominator']) != ('1', '100')


def test_arithmetic_tree_and_repeated_exp_calls_are_preserved():
    result = lower('math.exp(-z)/(1+math.exp(-z))')['ir']['body']
    assert result['kind'] == 'div' and result['right']['kind'] == 'add'
    assert result['left'] == result['right']['right']
    assert result['left'] is not result['right']['right']
    assert lower('z - z * z')['ir']['body'] != lower('(z - z) * z')['ir']['body']


def test_changed_query_changes_operator_tree():
    assert lower('math.log1p(math.exp(-abs(z)))')['ir'] != lower('math.log1p(math.exp(abs(z)))')['ir']
    assert lower('1 if z >= 0 else 2')['ir'] != lower('2 if z >= 0 else 1')['ir']


def test_lexical_slot_permutation_is_preserved():
    first = lower('a - b', {'a': 0, 'b': 1})
    second = lower('a - b', {'a': 1, 'b': 0})
    assert first['source_scalar'] == second['source_scalar']
    assert first['ir'] != second['ir']


@pytest.mark.parametrize('bindings', [{}, {'z': True}, {'a': 0, 'b': 0}, {'a': 1}, {'bad name': 0}])
def test_invalid_scope_refused(bindings):
    with pytest.raises(compiler.CompileRefusal):
        lower('z', bindings)


def test_wide_ast_cannot_allocate_an_unbounded_pending_copy():
    node = ast.Call(func=ast.Name(id='max', ctx=ast.Load()),
                    args=[ast.Constant(value=0) for _ in range(1000)], keywords=[])
    with pytest.raises(compiler.CompileRefusal) as error:
        compiler.compile_scalar_ast(node, {'z': 0}, max_nodes=16)
    assert error.value.reason_code == 'budget'


def test_cyclic_ast_refused_by_depth_or_node_budget():
    node = ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=0))
    node.operand = node
    with pytest.raises(compiler.CompileRefusal) as error:
        compiler.compile_scalar_ast(node, {'z': 0}, max_nodes=16, max_depth=8)
    assert error.value.reason_code == 'budget'


@pytest.mark.parametrize('mutation', ['slot', 'extra', 'unreduced', 'denominator', 'boolean_slots', 'opcode'])
def test_closed_ir_schema_refuses_tampering(mutation):
    ir = copy.deepcopy(lower('z')['ir'])
    if mutation == 'slot': ir['body']['slot'] = 1
    elif mutation == 'extra': ir['body']['extra'] = None
    elif mutation == 'unreduced': ir['body'] = {'kind': 'num', 'numerator': '2', 'denominator': '2'}
    elif mutation == 'denominator': ir['body'] = {'kind': 'num', 'numerator': '1', 'denominator': '0'}
    elif mutation == 'boolean_slots': ir['slots'] = True
    else: ir['body'] = {'kind': 'objective'}
    with pytest.raises(compiler.CompileRefusal):
        compiler.validate_scalar_ir(ir)


def test_renderer_refuses_names_that_disagree_with_named_source():
    with pytest.raises(compiler.CompileRefusal):
        compiler.render_source_scalar(lower('z'), ('other',))
    with pytest.raises(compiler.CompileRefusal):
        compiler.render_source_scalar(lower('z'), ('z\naxiom bad : False',))


def test_renderer_refuses_nonstring_unhashable_name():
    with pytest.raises(compiler.CompileRefusal):
        compiler.render_source_scalar(lower('z'), ({},))


@pytest.mark.parametrize('length', [81, 10000])
def test_oversized_decimal_is_refused_before_regex_scan(length, monkeypatch):
    class ForbiddenRegex:
        def fullmatch(self, value):
            raise AssertionError('oversized numeric strings must not reach regex')
    monkeypatch.setattr(compiler, '_INT', ForbiddenRegex())
    ir = {'schema': 'ranker-objective-scalar-ir@1', 'slots': 1,
          'body': {'kind': 'num', 'numerator': '9' * length, 'denominator': '1'}}
    with pytest.raises(compiler.CompileRefusal):
        compiler.validate_scalar_ir(ir)


def test_oversized_hash_is_refused_before_regex_scan(source_bytes, monkeypatch):
    class ForbiddenRegex:
        def fullmatch(self, value):
            raise AssertionError('oversized digest must not reach regex')
    monkeypatch.setattr(compiler, '_SHA', ForbiddenRegex())
    with pytest.raises(compiler.CompileRefusal):
        compiler.compile_objective_scalar_slices(source_bytes, 'a' * 10000)


@pytest.mark.parametrize('shape', ['large_string', 'deep', 'cyclic'])
def test_emitter_refuses_unbounded_caller_receipt_before_serialization(source_bytes, shape):
    result = canonical(source_bytes)
    if shape == 'large_string':
        result['untrusted'] = 'x' * (compiler.MAX_RECEIPT_BYTES + 1)
    elif shape == 'deep':
        value = {}
        for _ in range(60): value = {'child': value}
        result['untrusted'] = value
    else:
        value = {}; value['child'] = value; result['untrusted'] = value
    with pytest.raises(compiler.CompileRefusal) as error:
        compiler.render_generated_lean(result, source_bytes)
    assert error.value.reason_code == 'budget'


@pytest.mark.parametrize('target', ['abs', 'math'])
def test_nonload_call_target_is_refused(target):
    if target == 'abs':
        function = ast.Name(id='abs', ctx=ast.Store())
    else:
        function = ast.Attribute(value=ast.Name(id='math', ctx=ast.Store()), attr='exp', ctx=ast.Load())
    node = ast.Call(func=function, args=[ast.Name(id='z', ctx=ast.Load())], keywords=[])
    with pytest.raises(compiler.CompileRefusal) as error:
        compiler.compile_scalar_ast(node, {'z': 0})
    assert error.value.reason_code == 'unsupportedCallTarget'


def test_pinned_source_extraction_has_nine_honest_snippets(source_bytes):
    result = canonical(source_bytes)
    assert result['schema'] == 'ranker-objective-scalar-source-slices@1'
    assert result['status'] == 'compiled_source_only_kernel_pending'
    assert result['host_AST_parse_calls'] == 1 and result['source_function_execution_calls'] == 0
    assert len(result['source_snippets']) == 9 and len(result['statements']) == 7
    assert result['source_snippets']['stable_loss_scalar']['ast_sha256'] == LOSS_SHA
    assert result['source_snippets']['stable_factor_scalar']['ast_sha256'] == FACTOR_SHA
    assert result['source_snippets']['factor_condition']['role'] == 'comparison_context_only_not_scalar'
    assert result['source_snippets']['gradient_coordinate']['role'].startswith('unsupported_context_only')
    assert result['source_L2']['prior_exact_mu_rat_matches'] is True
    assert result['source_L2']['literal_lexeme'] == '0.01'


def test_all_snippets_are_exact_segments_and_hashes(source_bytes):
    result = canonical(source_bytes)
    for snippet in result['source_snippets'].values():
        raw = snippet['source_segment'].encode('utf-8')
        assert raw in source_bytes
        assert len(raw) == snippet['source_segment_utf8_bytes']
        assert hashlib.sha256(raw).hexdigest() == snippet['source_segment_utf8_sha256']


def test_source_and_context_pin_mismatches_refused(source_bytes):
    with pytest.raises(compiler.CompileRefusal):
        compiler.compile_objective_scalar_slices(source_bytes + b'\n')
    with pytest.raises(compiler.CompileRefusal):
        compiler.compile_objective_scalar_slices(source_bytes, expected_objective_ast_sha256='0' * 64)
    with pytest.raises(compiler.CompileRefusal):
        compiler.compile_objective_scalar_slices(source_bytes, expected_stable_loss_ast_sha256='0' * 64)


@pytest.mark.parametrize('old,new,reason', [
    (b'for z in margins) / len(margins)', b'for z in margins if z > 0) / len(margins)', 'comprehensionFilter'),
    (b'for z in margins) / len(margins)', b'for z in margins for z2 in margins) / len(margins)', 'multipleGenerators'),
    (b'if z >= 0 else', b'if z > 0 else', 'unsupportedComparison'),
    (b'gradient = [L2 *', b'gradient = 1 # [L2 *', 'malformedSource'),
])
def test_changed_unsupported_context_refused(source_bytes, old, new, reason):
    mutated = source_bytes.replace(old, new, 1)
    assert mutated != source_bytes
    if reason == 'malformedSource':
        with pytest.raises(compiler.CompileRefusal):
            compiler.compile_objective_scalar_slices(mutated, hashlib.sha256(mutated).hexdigest())
        return
    _, digest, context = changed(source_bytes, old, new)
    with pytest.raises(compiler.CompileRefusal) as error:
        compiler.compile_objective_scalar_slices(mutated, digest, context)
    assert error.value.reason_code == reason


def test_safe_changed_query_can_lower_but_cannot_emit_original_bridge(source_bytes):
    raw, digest, context = changed(source_bytes, b'math.exp(-abs(z))', b'math.exp(abs(z))')
    altered = compiler.compile_objective_scalar_slices(raw, digest, context)
    assert altered['stable_loss']['ir'] != canonical(source_bytes)['stable_loss']['ir']
    assert altered['source']['original_source_pin_matches'] is False
    with pytest.raises(compiler.CompileRefusal):
        compiler.render_generated_lean(altered, raw)


def test_valid_changed_gradient_context_refused_without_computation(source_bytes):
    module = ast.parse(source_bytes)
    objective = next(n for n in module.body if type(n) is ast.FunctionDef and n.name == '_objective')
    original_value = ast.get_source_segment(source_bytes.decode('utf-8'), objective.body[4].value).encode('utf-8')
    raw, digest, context = changed(source_bytes, original_value, b'0')
    with pytest.raises(compiler.CompileRefusal) as error:
        compiler.compile_objective_scalar_slices(raw, digest, context)
    assert error.value.reason_code == 'contextHashMismatch'


def test_source_L2_changed_to_decimal_fraction_cannot_gain_bridge(source_bytes):
    raw, digest, context = changed(source_bytes, b'L2 = 0.01', b'L2 = 1')
    altered = compiler.compile_objective_scalar_slices(raw, digest, context)
    assert altered['source_L2']['prior_exact_mu_rat_matches'] is False
    with pytest.raises(compiler.CompileRefusal):
        compiler.render_generated_lean(altered, raw)


@pytest.mark.parametrize('field', ['stable_loss', 'stable_factor', 'source', 'status'])
def test_emitter_refuses_caller_modified_result(source_bytes, field):
    original = canonical(source_bytes)
    altered = copy.deepcopy(original)
    altered[field] = {} if field != 'status' else 'passed'
    with pytest.raises(compiler.CompileRefusal):
        compiler.render_generated_lean(altered, source_bytes)


def test_renderer_query_population_and_partial_preservation(source_bytes):
    result = canonical(source_bytes)
    rendered = compiler.render_generated_lean_with_receipt(result, source_bytes)
    text = rendered['text']
    assert rendered['validation_AST_parse_calls'] == 1 and rendered['source_execution_calls'] == 0
    assert text.count('#print axioms ') == 9 and 'import ObjectiveScalarIR' in text
    assert 'accepted : compileScalar scope source = .ok program' in text
    assert 'evalSourceExact' in text and 'theorem emitted_stableLoss_eq_pairLoss' in text
    assert 'theorem emitted_stableFactor_eq_logisticP' in text
    assert '5764607523034235' in text and '576460752303423488' in text
    assert 'sorry' not in text and '\naxiom ' not in text
    assert 'realCoordinateGradient' not in text and 'realObjective' not in text


def test_actual_parse_counter_is_compile_one_renderer_one(source_bytes, monkeypatch):
    original_parse, calls = ast.parse, []
    def counted(*args, **kwargs):
        calls.append(1)
        return original_parse(*args, **kwargs)
    monkeypatch.setattr(ast, 'parse', counted)
    result = canonical(source_bytes)
    assert len(calls) == result['host_AST_parse_calls'] == 1
    emitted = compiler.render_generated_lean_with_receipt(result, source_bytes)
    assert len(calls) == result['host_AST_parse_calls'] + emitted['validation_AST_parse_calls'] == 2


def test_projection_frontiers_are_never_promoted(source_bytes):
    result = canonical(source_bytes)
    for field in ['compiled', 'theorem_qualified', 'proof_authority', 'execution_authority',
                  'completion_authority', 'planner_activation', 'host_parser_correctness_theorem_proved',
                  'python_ranker_source_equivalence_proved', 'Python_Float_semantics_proved',
                  'Python_libm_semantics_proved', 'objective_to_IR_translation_proved',
                  'gradient_to_IR_translation_proved', 'full_training_loop_to_IR_translation_proved',
                  'optimizer_source_convergence_proved', 'whole_codebase_IR_semantic_preservation_proved',
                  'global_autoencoder_convergence_proved']:
        assert result[field] is False
    assert result['full_task_satisfaction'] == 'unknown' and result['all32_governing_RPI_exits'] == 'OPEN'
