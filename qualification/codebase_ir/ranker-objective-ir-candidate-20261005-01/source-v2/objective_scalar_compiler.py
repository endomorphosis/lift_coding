"""Inert source AST extraction and Lean emission for two objective scalar leaves.

No source execution, file reads, project imports, model work or process calls are
present. The caller supplies one pinned source byte buffer. The exact-real
backend is a declared projection; Python Float/libm and whole-function execution
remain open. This candidate has not been imported, tested or native-qualified.
"""
import ast
import hashlib
import json
import re
from fractions import Fraction

SOURCE_SHA256 = '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a'
OBJECTIVE_AST_SHA256 = '129da31ae6856167478c7f030a059d0f477b8362bb8fa478221eac7bac6031c2'
SOURCE_L2_NUMERATOR = '5764607523034235'
SOURCE_L2_DENOMINATOR = '576460752303423488'
MAX_SOURCE_BYTES = 262144
MAX_MODULE_NODES = 4096
MAX_SCALAR_NODES = 128
MAX_DEPTH = 32
MAX_INTEGER_BITS = 256
MAX_RECEIPT_BYTES = 65536
_NAME = re.compile(r'[A-Za-z_][A-Za-z_0-9]{0,63}\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_INT = re.compile(r'-?(0|[1-9][0-9]*)\Z')
_BINARY = {'add', 'sub', 'mul', 'div', 'max'}
_UNARY = {'neg', 'abs', 'exp', 'log1p'}


class CompileRefusal(ValueError):
    """Explicit source/schema refusal; never a fallback to source evaluation."""

    def __init__(self, reason_code, message, node=None):
        self.reason_code = reason_code
        self.node_kind = type(node).__name__ if node is not None else None
        self.span = ([node.lineno, node.col_offset, node.end_lineno, node.end_col_offset]
                     if node is not None and all(hasattr(node, field) for field in
                                                ['lineno', 'col_offset', 'end_lineno', 'end_col_offset']) else None)
        super().__init__(message)


def _need(condition, reason, message, node=None):
    if condition is not True:
        raise CompileRefusal(reason, message, node)


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _bounded_wire(value):
    """Check caller/result JSON size and nesting before serialization."""
    pending, count, text_bytes = [(value, 1)], 0, 0
    while pending:
        current, depth = pending.pop()
        count += 1
        _need(count <= 8192 and depth <= 48, 'budget', 'receipt JSON node/depth cap exceeded')
        if type(current) is str:
            _need(len(current) <= MAX_RECEIPT_BYTES, 'budget', 'receipt string cap exceeded')
            try:
                text_bytes += len(current.encode('utf-8'))
            except UnicodeEncodeError:
                raise CompileRefusal('irSchema', 'receipt requires valid UTF-8 strings') from None
            _need(text_bytes <= MAX_RECEIPT_BYTES, 'budget', 'receipt aggregate text cap exceeded')
        elif type(current) is int:
            _need(abs(current).bit_length() <= MAX_INTEGER_BITS, 'budget', 'receipt integer cap exceeded')
        elif current is None or type(current) is bool:
            pass
        elif type(current) is dict:
            for key, child in current.items():
                _need(type(key) is str and count + len(pending) + 2 <= 8192,
                      'budget', 'receipt key/pending cap exceeded')
                pending.append((key, depth + 1)); pending.append((child, depth + 1))
        elif type(current) is list:
            for child in current:
                _need(count + len(pending) < 8192, 'budget', 'receipt pending cap exceeded')
                pending.append((child, depth + 1))
        else:
            raise CompileRefusal('irSchema', 'receipt must contain bounded JSON primitives')
    raw = _wire(value)
    _need(len(raw) <= MAX_RECEIPT_BYTES, 'budget', 'receipt byte cap exceeded')
    return raw


def _ast_sha(node):
    return hashlib.sha256(ast.dump(node, annotate_fields=True, include_attributes=False).encode('utf-8')).hexdigest()


def _bounds(node, max_nodes=MAX_SCALAR_NODES, max_depth=MAX_DEPTH):
    _need(type(max_nodes) is int and 1 <= max_nodes <= MAX_MODULE_NODES,
          'budget', 'invalid node cap')
    _need(type(max_depth) is int and 1 <= max_depth <= MAX_DEPTH,
          'budget', 'invalid depth cap')
    pending, count = [(node, 1)], 0
    while pending:
        current, depth = pending.pop()
        count += 1
        _need(count <= max_nodes and depth <= max_depth,
              'budget', 'AST node/depth budget exceeded', current)
        for child in ast.iter_child_nodes(current):
            _need(count + len(pending) < max_nodes,
                  'budget', 'AST pending-node budget exceeded', current)
            pending.append((child, depth + 1))
    return count


def _scope(bindings):
    _need(type(bindings) is dict and 1 <= len(bindings) <= 8,
          'binderShape', 'closed finite lexical scope required')
    _need(all(type(name) is str and len(name) <= 64 and _NAME.fullmatch(name) is not None
              and type(slot) is int and 0 <= slot < len(bindings)
              for name, slot in bindings.items()), 'binderShape', 'invalid lexical name/slot')
    _need(set(bindings.values()) == set(range(len(bindings))), 'binderShape', 'duplicate/missing slots')
    return dict(bindings)


def _number(value, node=None):
    _need(type(value) in (int, float), 'unsupportedLiteral', 'only integer/Float constants accepted', node)
    try:
        numerator, denominator = value.as_integer_ratio() if type(value) is float else (value, 1)
    except (OverflowError, ValueError):
        raise CompileRefusal('unsupportedLiteral', 'nonfinite Float literal refused', node) from None
    _need(abs(numerator).bit_length() <= MAX_INTEGER_BITS and denominator.bit_length() <= MAX_INTEGER_BITS,
          'budget', 'numeric literal bit budget exceeded', node)
    rational = Fraction(numerator, denominator)
    return {'kind': 'num', 'numerator': str(rational.numerator), 'denominator': str(rational.denominator)}


def _zero_constant(node):
    return type(node) is ast.Constant and type(node.value) in (int, float) and node.value == 0


def compile_scalar_ast(node, bindings, *, max_nodes=MAX_SCALAR_NODES, max_depth=MAX_DEPTH):
    """Generic operation-tree lowering. Validate BOTH IfExp branches eagerly.

    A Compare is not a scalar. Only an IfExp with exactly `test >= 0` becomes
    ifNonneg. Runtime lazy evaluation and domain errors belong to the separate
    Lean semantics; this host function never evaluates exp/log/division trees.
    """
    scope = _scope(bindings)
    _need(type(max_nodes) is int and 1 <= max_nodes <= MAX_SCALAR_NODES,
          'budget', 'invalid scalar node cap')
    _bounds(node, max_nodes, max_depth)

    def lower(current):
        if type(current) is ast.Name:
            _need(type(current.ctx) is ast.Load and type(current.id) is str
                  and len(current.id) <= 64 and current.id in scope,
                  'unknownName', 'unresolved/non-load scalar name', current)
            return {'kind': 'var', 'name': current.id}, {'kind': 'var', 'slot': scope[current.id]}
        if type(current) is ast.Constant:
            value = _number(current.value, current)
            return dict(value), dict(value)
        if type(current) is ast.UnaryOp:
            _need(type(current.op) is ast.USub, 'unsupportedNode', 'unsupported unary operator', current)
            source, typed = lower(current.operand)
            return {'kind': 'neg', 'value': source}, {'kind': 'neg', 'value': typed}
        if type(current) is ast.BinOp:
            kind = {ast.Add: 'add', ast.Sub: 'sub', ast.Mult: 'mul', ast.Div: 'div'}.get(type(current.op))
            _need(kind is not None, 'unsupportedNode', 'unsupported binary operator', current)
            left_source, left_typed = lower(current.left)
            right_source, right_typed = lower(current.right)
            return ({'kind': kind, 'left': left_source, 'right': right_source},
                    {'kind': kind, 'left': left_typed, 'right': right_typed})
        if type(current) is ast.Call:
            _need(current.keywords == [], 'keywordArguments', 'keyword/star calls refused', current)
            function = current.func
            if (type(function) is ast.Name and type(function.id) is str
                    and len(function.id) <= 64 and function.id in {'abs', 'max'}):
                _need(type(function.ctx) is ast.Load, 'unsupportedCallTarget', 'non-load call name refused', function)
                _need(function.id not in scope, 'unsupportedCallTarget', 'lexically shadowed builtin call refused', function)
                kind, arity = function.id, 1 if function.id == 'abs' else 2
            elif (type(function) is ast.Attribute and type(function.value) is ast.Name
                  and function.value.id == 'math' and type(function.attr) is str
                  and len(function.attr) <= 16 and function.attr in {'exp', 'log1p'}):
                _need(type(function.ctx) is ast.Load and type(function.value.ctx) is ast.Load,
                      'unsupportedCallTarget', 'non-load math receiver refused', function)
                _need('math' not in scope, 'unsupportedCallTarget', 'lexically shadowed math call refused', function)
                kind, arity = function.attr, 1
            else:
                raise CompileRefusal('unsupportedCallTarget', 'scalar call target refused', current)
            _need(len(current.args) == arity, 'wrongArity', 'scalar call arity differs', current)
            parts = [lower(argument) for argument in current.args]
            if arity == 1:
                return {'kind': kind, 'value': parts[0][0]}, {'kind': kind, 'value': parts[0][1]}
            return ({'kind': kind, 'left': parts[0][0], 'right': parts[1][0]},
                    {'kind': kind, 'left': parts[0][1], 'right': parts[1][1]})
        if type(current) is ast.IfExp:
            test = current.test
            _need(type(test) is ast.Compare and len(test.ops) == len(test.comparators) == 1
                  and type(test.ops[0]) is ast.GtE and _zero_constant(test.comparators[0]),
                  'unsupportedComparison', 'only scalar >= numeric zero condition accepted', test)
            condition_source, condition_typed = lower(test.left)
            yes_source, yes_typed = lower(current.body)
            no_source, no_typed = lower(current.orelse)
            return ({'kind': 'ifNonneg', 'condition': condition_source, 'then': yes_source, 'else': no_source},
                    {'kind': 'ifNonneg', 'condition': condition_typed, 'then': yes_typed, 'else': no_typed})
        raise CompileRefusal('unsupportedNode', 'unsupported scalar AST: ' + type(current).__name__, current)

    source, typed = lower(node)
    result = {'schema': 'ranker-objective-scalar-lowering@1', 'source_scalar': source,
              'ir': {'schema': 'ranker-objective-scalar-ir@1', 'slots': len(scope), 'body': typed}}
    validate_scalar_ir(result['ir'])
    return result


def validate_scalar_ir(ir):
    _need(type(ir) is dict and len(ir) == 3 and set(ir) == {'schema', 'slots', 'body'}
          and ir['schema'] == 'ranker-objective-scalar-ir@1', 'irSchema', 'closed scalar IR schema required')
    slots = ir['slots']
    _need(type(slots) is int and 1 <= slots <= 8, 'irSchema', 'invalid slot count')
    count = 0

    def visit(node, depth):
        nonlocal count
        count += 1
        _need(count <= MAX_SCALAR_NODES and depth <= MAX_DEPTH, 'budget', 'IR budget exceeded')
        _need(type(node) is dict and len(node) <= 4 and type(node.get('kind')) is str
              and len(node['kind']) <= 16, 'irSchema', 'bounded closed IR node required')
        kind = node['kind']
        if kind == 'num':
            _need(set(node) == {'kind', 'numerator', 'denominator'}
                  and all(type(node[k]) is str and len(node[k]) <= 80
                          and _INT.fullmatch(node[k]) is not None for k in ['numerator', 'denominator']),
                  'irSchema', 'canonical rational strings required')
            n, d = int(node['numerator']), int(node['denominator'])
            _need(d > 0 and abs(n).bit_length() <= MAX_INTEGER_BITS and d.bit_length() <= MAX_INTEGER_BITS,
                  'irSchema', 'invalid rational domain/cap')
            q = Fraction(n, d)
            _need((str(q.numerator), str(q.denominator)) == (node['numerator'], node['denominator']),
                  'irSchema', 'unreduced/noncanonical rational')
        elif kind == 'var':
            _need(set(node) == {'kind', 'slot'} and type(node['slot']) is int and 0 <= node['slot'] < slots,
                  'irSchema', 'invalid typed slot')
        elif kind in _UNARY:
            _need(set(node) == {'kind', 'value'}, 'irSchema', 'unary IR keys')
            visit(node['value'], depth + 1)
        elif kind in _BINARY:
            _need(set(node) == {'kind', 'left', 'right'}, 'irSchema', 'binary IR keys')
            visit(node['left'], depth + 1); visit(node['right'], depth + 1)
        elif kind == 'ifNonneg':
            _need(set(node) == {'kind', 'condition', 'then', 'else'}, 'irSchema', 'conditional IR keys')
            visit(node['condition'], depth + 1); visit(node['then'], depth + 1); visit(node['else'], depth + 1)
        else:
            raise CompileRefusal('irSchema', 'unsupported IR node: ' + kind)

    visit(ir['body'], 1)
    return count


def render_source_scalar(lowering, names):
    _need(type(lowering) is dict and len(lowering) == 3 and set(lowering) == {'schema', 'source_scalar', 'ir'}
          and lowering['schema'] == 'ranker-objective-scalar-lowering@1',
          'irSchema', 'closed lowering schema required')
    ir = lowering['ir']
    validate_scalar_ir(ir)
    _need(type(names) is tuple and len(names) == ir['slots']
          and all(type(name) is str and len(name) <= 64 and _NAME.fullmatch(name) is not None for name in names)
          and len(set(names)) == len(names),
          'binderShape', 'safe ordered renderer names required')

    def named(node):
        kind = node['kind']
        if kind == 'var':
            return {'kind': 'var', 'name': names[node['slot']]}
        if kind == 'num':
            return dict(node)
        if kind in _UNARY:
            return {'kind': kind, 'value': named(node['value'])}
        if kind in _BINARY:
            return {'kind': kind, 'left': named(node['left']), 'right': named(node['right'])}
        return {'kind': kind, 'condition': named(node['condition']),
                'then': named(node['then']), 'else': named(node['else'])}

    _need(_bounded_wire(lowering['source_scalar']) == _bounded_wire(named(ir['body'])),
          'binderShape', 'named source tree does not match ordered lexical slots')

    def render(node):
        kind = node['kind']
        if kind == 'num':
            if node['denominator'] == '1':
                return '(.num (' + node['numerator'] + ' : Rat))'
            return '(.num ((' + node['numerator'] + ' : Rat) / ' + node['denominator'] + '))'
        if kind == 'var':
            return '(.var ' + json.dumps(names[node['slot']]) + ')'
        if kind in _UNARY:
            return '(.' + kind + ' ' + render(node['value']) + ')'
        if kind in _BINARY:
            return '(.' + kind + ' ' + render(node['left']) + ' ' + render(node['right']) + ')'
        return '(.ifNonneg ' + render(node['condition']) + ' ' + render(node['then']) + ' ' + render(node['else']) + ')'

    return render(ir['body'])


def _record(node, ast_path, text, role):
    segment = ast.get_source_segment(text, node)
    _need(type(segment) is str, 'malformedSource', 'source location missing', node)
    return {'ast_path': ast_path, 'role': role, 'node_kind': type(node).__name__,
            'span': [node.lineno, node.col_offset, node.end_lineno, node.end_col_offset],
            'ast_sha256': _ast_sha(node), 'source_segment': segment,
            'source_segment_utf8_bytes': len(segment.encode('utf-8')),
            'source_segment_utf8_sha256': hashlib.sha256(segment.encode('utf-8')).hexdigest()}


def _comprehension(node, expected_class, iterable, binder):
    _need(type(node) is expected_class and len(node.generators) == 1,
          'multipleGenerators', 'one expected comprehension generator required', node)
    generator = node.generators[0]
    _need(generator.is_async == 0, 'asyncComprehension', 'async generator refused', generator)
    _need(generator.ifs == [], 'comprehensionFilter', 'filtered comprehension refused', generator)
    _need(type(generator.target) is ast.Name and generator.target.id == binder
          and type(generator.iter) is ast.Name and generator.iter.id == iterable,
          'binderShape', 'comprehension lexical target/input differs', generator)
    return node.elt


def compile_objective_scalar_slices(source_bytes, expected_source_sha256=SOURCE_SHA256,
                                   expected_objective_ast_sha256=OBJECTIVE_AST_SHA256,
                                   expected_stable_loss_ast_sha256=None,
                                   expected_stable_factor_ast_sha256=None):
    """Read one supplied buffer, bind exact context, lower two scalar leaves.

    An explicit alternate source hash permits pure changed-query controls. The
    generated mathematical bridge is refused unless original bytes/context/L2
    match. The gradient coordinate and bare comparison are context-only records.
    """
    _need(type(source_bytes) is bytes and 1 <= len(source_bytes) <= MAX_SOURCE_BYTES,
          'budget', 'bounded raw source bytes required')
    _need(type(expected_source_sha256) is str and len(expected_source_sha256) == 64
          and _SHA.fullmatch(expected_source_sha256) is not None,
          'sourcePinMismatch', 'explicit exact source digest required')
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    _need(source_sha == expected_source_sha256, 'sourcePinMismatch', 'supplied source bytes differ')
    try:
        text = source_bytes.decode('utf-8')
        module = ast.parse(text, mode='exec')
    except (UnicodeDecodeError, SyntaxError, RecursionError):
        raise CompileRefusal('malformedSource', 'source UTF-8/Python syntax refused') from None
    module_nodes = _bounds(module, MAX_MODULE_NODES)
    functions = [(i, n) for i, n in enumerate(module.body) if type(n) is ast.FunctionDef and n.name == '_objective']
    _need(len(functions) == 1, 'ambiguousBinding', 'unique objective FunctionDef required')
    index, objective = functions[0]
    _need(type(expected_objective_ast_sha256) is str and len(expected_objective_ast_sha256) == 64
          and _SHA.fullmatch(expected_objective_ast_sha256) is not None
          and _ast_sha(objective) == expected_objective_ast_sha256,
          'contextHashMismatch', 'bound objective function AST differs', objective)
    args = objective.args
    _need(objective.decorator_list == [] and objective.returns is None
          and args.posonlyargs == args.kwonlyargs == args.defaults == args.kw_defaults == []
          and args.vararg is None and args.kwarg is None
          and [x.arg for x in args.args] == ['weights', 'differences']
          and all(x.annotation is None for x in args.args), 'binderShape', 'objective argument/decorator scope differs', objective)
    _need(len(objective.body) == 7, 'contextHashMismatch', 'exact seven-statement context required', objective)
    for statement, name in zip(objective.body[:5], ['margins', 'data', 'regularizer', 'factors', 'gradient']):
        _need(type(statement) is ast.Assign and len(statement.targets) == 1
              and type(statement.targets[0]) is ast.Name and statement.targets[0].id == name,
              'contextHashMismatch', 'objective assignment order/name differs', statement)
    data = objective.body[1].value
    _need(type(data) is ast.BinOp and type(data.op) is ast.Div and type(data.left) is ast.Call
          and type(data.left.func) is ast.Attribute and type(data.left.func.value) is ast.Name
          and data.left.func.value.id == 'math' and data.left.func.attr == 'fsum'
          and data.left.keywords == [] and len(data.left.args) == 1,
          'contextHashMismatch', 'data fsum/division context differs', data)
    _need(type(data.right) is ast.Call and type(data.right.func) is ast.Name and data.right.func.id == 'len'
          and data.right.keywords == [] and len(data.right.args) == 1
          and type(data.right.args[0]) is ast.Name and data.right.args[0].id == 'margins',
          'contextHashMismatch', 'data mean denominator context differs', data)
    loss = _comprehension(data.left.args[0], ast.GeneratorExp, 'margins', 'z')
    factor = _comprehension(objective.body[3].value, ast.ListComp, 'margins', 'z')
    for node, expected_hash in [(loss, expected_stable_loss_ast_sha256),
                                (factor, expected_stable_factor_ast_sha256)]:
        if expected_hash is not None:
            _need(type(expected_hash) is str and len(expected_hash) == 64 and _SHA.fullmatch(expected_hash) is not None
                  and _ast_sha(node) == expected_hash,
                  'contextHashMismatch', 'bound scalar expression AST differs', node)
    _need(type(factor) is ast.IfExp, 'contextHashMismatch', 'factor must retain IfExp', factor)
    lowered_loss = compile_scalar_ast(loss, {'z': 0})
    lowered_factor = compile_scalar_ast(factor, {'z': 0})
    # Ancillary snippet extraction is exact-context inventory, not extra support.
    _need(type(loss) is ast.BinOp and type(loss.op) is ast.Add
          and type(loss.right) is ast.Call and len(loss.right.args) == 1,
          'contextHashMismatch', 'stable loss outer context differs', loss)
    _need(type(objective.body[4].value) is ast.ListComp,
          'contextHashMismatch', 'gradient list-comprehension context required', objective.body[4])
    assignments = [(i, n) for i, n in enumerate(module.body) if type(n) is ast.Assign
                   and any(type(t) is ast.Name and t.id == 'L2' for t in n.targets)]
    _need(len(assignments) == 1 and len(assignments[0][1].targets) == 1,
          'ambiguousBinding', 'unique simple source L2 binding required')
    l2_index, l2_assignment = assignments[0]
    l2 = l2_assignment.value
    _need(type(l2) is ast.Constant, 'unsupportedLiteral', 'source L2 literal required', l2)
    l2_lowering = compile_scalar_ast(l2, {'z': 0})
    original_l2 = l2_lowering['ir']['body'] == {'kind': 'num', 'numerator': SOURCE_L2_NUMERATOR,
                                               'denominator': SOURCE_L2_DENOMINATOR}
    prefix = 'module.body[' + str(index) + ']'
    snippet_nodes = [
        ('stable_loss_scalar', loss, prefix + '.body[1].value.left.args[0].elt', 'accepted_scalar_leaf'),
        ('stable_factor_scalar', factor, prefix + '.body[3].value.elt', 'accepted_scalar_leaf'),
        ('factor_condition', factor.test, prefix + '.body[3].value.elt.test', 'comparison_context_only_not_scalar'),
        ('factor_then_branch', factor.body, prefix + '.body[3].value.elt.body', 'accepted_scalar_subexpression'),
        ('factor_else_branch', factor.orelse, prefix + '.body[3].value.elt.orelse', 'accepted_scalar_subexpression'),
        ('loss_max_subexpression', loss.left, prefix + '.body[1].value.left.args[0].elt.left', 'accepted_scalar_subexpression'),
        ('log1p_argument', loss.right.args[0], prefix + '.body[1].value.left.args[0].elt.right.args[0]', 'accepted_scalar_subexpression'),
        ('source_L2_literal', l2, 'module.body[' + str(l2_index) + '].value', 'exact_source_literal_binding_only'),
        ('gradient_coordinate', objective.body[4].value.elt, prefix + '.body[4].value.elt', 'unsupported_context_only_indexing_and_containers_open'),
    ]
    result = {
        'schema': 'ranker-objective-scalar-source-slices@1', 'status': 'compiled_source_only_kernel_pending',
        'source': {'bytes': len(source_bytes), 'sha256': source_sha, 'module_ast_sha256': _ast_sha(module),
                   'module_ast_nodes': module_nodes, 'original_source_pin_matches': source_sha == SOURCE_SHA256},
        'expected_AST_bindings': {'objective': expected_objective_ast_sha256,
                                  'stable_loss': expected_stable_loss_ast_sha256,
                                  'stable_factor': expected_stable_factor_ast_sha256},
        'objective_context': _record(objective, prefix, text, 'whole_function_context_only'),
        'statements': [_record(node, prefix + '.body[' + str(i) + ']', text, 'context_only')
                       for i, node in enumerate(objective.body)],
        'source_snippets': {name: _record(node, path, text, role) for name, node, path, role in snippet_nodes},
        'stable_loss': {**lowered_loss, 'lean_source_scalar': render_source_scalar(lowered_loss, ('z',))},
        'stable_factor': {**lowered_factor, 'lean_source_scalar': render_source_scalar(lowered_factor, ('z',))},
        'source_L2': {**l2_lowering, 'literal_lexeme': ast.get_source_segment(text, l2),
                      'literal_class': type(l2.value).__name__, 'prior_exact_mu_rat_matches': original_l2,
                      'lean_source_scalar': render_source_scalar(l2_lowering, ('z',))},
        'literal_backend': 'stdlib AST Float constant exact as_integer_ratio; Rat-to-Real projection',
        'conditional_policy': {'syntax_validation': 'both branches eager', 'exact_real_evaluation': 'selected branch only lazy'},
        'partial_domain_policy': {'div': 'denominator nonzero else divisionByZero',
                                  'log1p': '1+argument strictly positive else logDomain'},
        'host_AST_parse_calls': 1, 'source_function_execution_calls': 0,
        'native_qualification_jobs': 0, 'project_imports': 0,
        'compiled': False, 'theorem_qualified': False, 'proof_authority': False,
        'host_parser_correctness_theorem_proved': False, 'python_ranker_source_equivalence_proved': False,
        'Python_Float_semantics_proved': False, 'Python_libm_semantics_proved': False,
        'CPython_math_fsum_semantics_proved': False, 'objective_to_IR_translation_proved': False,
        'gradient_to_IR_translation_proved': False, 'feature_preparation_to_IR_translation_proved': False,
        'full_training_loop_to_IR_translation_proved': False, 'optimizer_source_convergence_proved': False,
        'whole_codebase_IR_semantic_preservation_proved': False, 'global_autoencoder_convergence_proved': False,
        'execution_authority': False, 'completion_authority': False, 'planner_activation': False,
        'full_task_satisfaction': 'unknown', 'all32_governing_RPI_exits': 'OPEN',
        'frontiers': ['host AST/hash/literal-rendering binding', 'Python name/global resolution',
                      'binary64 literal/runtime arithmetic and libm', 'containers/indexing/nonempty means/fsum',
                      '_need finite validation and exceptions', 'dictionary/tuple/sqrt return behavior',
                      '_prepare/corpus/features/hashes', 'full optimizer source loop/AE/general IR/full task'],
    }
    _bounded_wire(result)
    return result


def render_generated_lean_with_receipt(compilation, source_bytes):
    """Emit nine UNQUALIFIED query statements from the same byte buffer.

    Re-extraction prevents caller-edited IR/provenance from entering the emitter.
    Changed-query controls can lower but cannot acquire the original bridge.
    """
    _need(type(compilation) is dict and type(compilation.get('expected_AST_bindings')) is dict,
          'contextHashMismatch', 'complete bound extraction required')
    compilation_wire = _bounded_wire(compilation)
    expected = compilation['expected_AST_bindings']
    _need(len(expected) == 3 and set(expected) == {'objective', 'stable_loss', 'stable_factor'},
          'contextHashMismatch', 'closed expected AST bindings required')
    actual = compile_objective_scalar_slices(source_bytes,
        expected_objective_ast_sha256=expected['objective'],
        expected_stable_loss_ast_sha256=expected['stable_loss'],
        expected_stable_factor_ast_sha256=expected['stable_factor'])
    _need(compilation_wire == _bounded_wire(actual),
          'contextHashMismatch', 'renderer requires exact same-buffer extraction')
    _need(actual['objective_context']['ast_sha256'] == OBJECTIVE_AST_SHA256
          and actual['source_L2']['prior_exact_mu_rat_matches'] is True,
          'literalPolicyMismatch', 'original objective context/exact L2 required')
    loss = actual['stable_loss']['lean_source_scalar']
    factor = actual['stable_factor']['lean_source_scalar']
    l2 = actual['source_L2']['lean_source_scalar']
    header = '-- UNQUALIFIED SOURCE-ONLY CANDIDATE; no native run has occurred.\n'
    header += '-- Source SHA256 ' + SOURCE_SHA256 + '\n'
    header += '-- _objective AST SHA256 ' + OBJECTIVE_AST_SHA256 + '\n'
    header += '-- Stable loss AST SHA256 ' + actual['source_snippets']['stable_loss_scalar']['ast_sha256'] + '\n'
    header += '-- Stable factor AST SHA256 ' + actual['source_snippets']['stable_factor_scalar']['ast_sha256'] + '\n'
    header += '-- Exact-real scalar projection only; Python/Float/full objective/gradient/training remain open.\n'
    text = header + '''import ObjectiveScalarIR

namespace RankerObjectiveIRGenerated
noncomputable section
open RankerObjectiveIR

def emittedStableLossSource : SourceScalar := ''' + loss + '''
def emittedStableFactorSource : SourceScalar := ''' + factor + '''
def emittedSourceL2 : SourceScalar := ''' + l2 + '''
def emittedScalarScope (name : String) : Option (Fin 1) :=
  if name = "z" then some 0 else none

theorem emitted_compile_scalar_sound {slots : Nat}
    (scope : String → Option (Fin slots)) (environment : Fin slots → Real)
    (source : SourceScalar) (program : ScalarIR slots)
    (accepted : compileScalar scope source = .ok program) :
    evalSourceExact (namesFromScope scope environment) source = evalExact program environment := by
  exact RankerObjectiveIR.compile_scalar_sound
    (scope := scope) (environment := environment) (source := source)
    (program := program) (accepted := accepted)

theorem emitted_compile_refuses_unsupported {slots : Nat}
    (scope : String → Option (Fin slots)) (tag : String) :
    compileScalar scope (.unsupported tag) = .error (.unsupportedNode tag) := by
  rfl

theorem emitted_compile_refuses_unknown_name {slots : Nat}
    (scope : String → Option (Fin slots)) (name : String) (missing : scope name = none) :
    compileScalar scope (.var name) = .error (.unknownName name) := by
  simp only [compileScalar, missing]

theorem emitted_stableLoss_compiles :
    compileScalar emittedScalarScope emittedStableLossSource = .ok stableLossBody := by
  rfl

theorem emitted_stableFactor_compiles :
    compileScalar emittedScalarScope emittedStableFactorSource = .ok stableFactorBody := by
  rfl

theorem emitted_stableLoss_eval_success (z : Real) :
    evalSourceExact (namesFromScope emittedScalarScope (scalarEnvironment z))
      emittedStableLossSource = .ok (RankerRealCurvature.realStablePairLoss z) := by
  rw [emitted_compile_scalar_sound emittedScalarScope (scalarEnvironment z)
    emittedStableLossSource stableLossBody emitted_stableLoss_compiles]
  exact RankerObjectiveIR.stableLoss_eval_success z

theorem emitted_stableFactor_eval_success (z : Real) :
    evalSourceExact (namesFromScope emittedScalarScope (scalarEnvironment z))
      emittedStableFactorSource = .ok (RankerRealCurvature.realStableLogisticP z) := by
  rw [emitted_compile_scalar_sound emittedScalarScope (scalarEnvironment z)
    emittedStableFactorSource stableFactorBody emitted_stableFactor_compiles]
  exact RankerObjectiveIR.stableFactor_eval_success z

theorem emitted_stableLoss_eq_pairLoss (z : Real) :
    evalSourceExact (namesFromScope emittedScalarScope (scalarEnvironment z))
      emittedStableLossSource = .ok (RankerRealCurvature.realPairLoss z) := by
  rw [emitted_stableLoss_eval_success, RankerRealCurvature.realStablePairLoss_eq]

theorem emitted_stableFactor_eq_logisticP (z : Real) :
    evalSourceExact (namesFromScope emittedScalarScope (scalarEnvironment z))
      emittedStableFactorSource = .ok (RankerRealCurvature.realLogisticP z) := by
  rw [emitted_stableFactor_eval_success, RankerRealCurvature.realStableLogisticP_eq]

#print axioms emitted_compile_scalar_sound
#print axioms emitted_compile_refuses_unsupported
#print axioms emitted_compile_refuses_unknown_name
#print axioms emitted_stableLoss_compiles
#print axioms emitted_stableFactor_compiles
#print axioms emitted_stableLoss_eval_success
#print axioms emitted_stableFactor_eval_success
#print axioms emitted_stableLoss_eq_pairLoss
#print axioms emitted_stableFactor_eq_logisticP

end
end RankerObjectiveIRGenerated
'''
    _need(len(text.encode('utf-8')) <= 65536, 'budget', 'generated Lean source budget exceeded')
    return {'text': text, 'validation_AST_parse_calls': actual['host_AST_parse_calls'],
            'source_sha256': actual['source']['sha256'], 'source_execution_calls': 0,
            'native_qualification_jobs': 0, 'theorem_qualified': False}


def render_generated_lean(compilation, source_bytes):
    """Text-only convenience wrapper; one validation AST parse, zero execution."""
    return render_generated_lean_with_receipt(compilation, source_bytes)['text']
