"""Bounded generated Python syntax with sealed calls and explicit value labels.

This interpreter is a development implementation. It grants no native authority.
"""
from dataclasses import dataclass, replace
import ast
import hashlib
import json
import math
import operator
import time


class ProgramError(ValueError):
    pass


@dataclass(frozen=True)
class Limits:
    source_bytes: int = 32768
    ast_nodes: int = 2048
    steps: int = 30000
    iterations: int = 2048
    calls: int = 256
    depth: int = 24
    nodes: int = 8192
    collection: int = 512
    string_bytes: int = 65536
    total_bytes: int = 131072
    integer_bits: int = 128


@dataclass(frozen=True)
class Value:
    data: object
    labels: frozenset = frozenset()


def wrap(data, labels=frozenset(), source_labels=None, path=()):
    labels = frozenset(labels) | frozenset((source_labels or {}).get('/'.join(map(str, path)), []))
    if type(data) is dict:
        return Value({key: wrap(value, source_labels=source_labels, path=path + (key,)) for key, value in data.items()}, labels)
    if type(data) is list:
        return Value([wrap(value, source_labels=source_labels, path=path + (index,)) for index, value in enumerate(data)], labels)
    return Value(data, labels)


def unbox(value):
    if type(value.data) is dict:
        return {key: unbox(child) for key, child in value.data.items()}
    if type(value.data) is list:
        return [unbox(child) for child in value.data]
    return value.data


def labels(value):
    children = value.data.values() if type(value.data) is dict else value.data if type(value.data) is list else ()
    return value.labels | frozenset(label for child in children for label in labels(child))


def label_paths(value, path=''):
    result = {path: sorted(value.labels)} if value.labels else {}
    children = value.data.items() if type(value.data) is dict else enumerate(value.data) if type(value.data) is list else ()
    for key, child in children:
        result.update(label_paths(child, path + '/' + str(key)))
    return result


def check_value(value, limits):
    count = 0
    provenance_bytes = 0
    active = set()
    def visit(item, depth):
        nonlocal count, provenance_bytes
        count += 1
        if count > limits.nodes or depth > limits.depth:
            raise ProgramError('Value nesting/node bound exceeded')
        if not isinstance(item, Value) or type(item.labels) is not frozenset or any(type(s) is not str for s in item.labels):
            raise ProgramError('Invalid value/provenance representation')
        provenance_bytes += sum(len(label.encode()) for label in item.labels)
        if len(item.labels) > 16 or any(len(label.encode()) > 128 for label in item.labels) or provenance_bytes > limits.total_bytes:
            raise ProgramError('Provenance metadata bound exceeded')
        data = item.data
        if type(data) in (list, dict):
            if id(data) in active or len(data) > limits.collection:
                raise ProgramError('Cyclic or oversized collection')
            active.add(id(data))
            if type(data) is dict and any(type(key) is not str for key in data):
                raise ProgramError('Dictionary keys must be strings')
            for child in data.values() if type(data) is dict else data:
                visit(child, depth + 1)
            active.remove(id(data))
        elif type(data) is str:
            if len(data.encode('utf-8')) > limits.string_bytes:
                raise ProgramError('String byte bound exceeded')
        elif type(data) is int:
            if data.bit_length() > limits.integer_bits:
                raise ProgramError('Integer bound exceeded')
        elif type(data) is float:
            if not math.isfinite(data):
                raise ProgramError('Nonfinite float')
        elif data is not None and type(data) is not bool:
            raise ProgramError('Only JSON-shaped values are supported')
    visit(value, 0)
    if len(json.dumps(unbox(value), ensure_ascii=False, allow_nan=False).encode()) > limits.total_bytes:
        raise ProgramError('Total value byte bound exceeded')
    return value


ALLOWED_NODES = {ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Load, ast.Store,
                 ast.Assign, ast.Expr, ast.If, ast.For, ast.Return, ast.Pass,
                 ast.Name, ast.Constant, ast.List, ast.Dict, ast.Subscript,
                 ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Call,
                 ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
                 ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
                 ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
                 ast.In, ast.NotIn, ast.Is, ast.IsNot}


def validate(source, primitive_names, limits=Limits()):
    if type(source) is not bytes or not 0 < len(source) <= limits.source_bytes:
        raise ProgramError('Exact bounded UTF-8 source bytes required')
    try:
        text = source.decode('utf-8')
        tree = ast.parse(text, filename='candidate.py')
    except (UnicodeDecodeError, SyntaxError, RecursionError) as exc:
        raise ProgramError('Invalid source: ' + str(exc)) from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > limits.ast_nodes or any(type(node) not in ALLOWED_NODES for node in nodes):
        raise ProgramError('Unsupported AST syntax or size')
    if len(tree.body) != 1 or type(tree.body[0]) is not ast.FunctionDef:
        raise ProgramError('Exactly one run function is required')
    fn = tree.body[0]
    if fn.name != 'run' or fn.decorator_list or fn.returns or fn.type_comment or getattr(fn, 'type_params', []):
        raise ProgramError('Unsupported function contract')
    a = fn.args
    if len(a.args) != 1 or a.args[0].arg != 'payload' or a.args[0].annotation or a.posonlyargs or a.kwonlyargs or a.defaults or a.kw_defaults or a.vararg or a.kwarg:
        raise ProgramError('Signature must be run(payload)')
    if sum(type(node) is ast.FunctionDef for node in nodes) != 1:
        raise ProgramError('Nested functions are forbidden')
    calls = []
    for node in nodes:
        if type(node) is ast.Name and node.id.startswith('__'):
            raise ProgramError('Dunder identifiers are unsupported')
        if type(node) is ast.Name and type(node.ctx) is ast.Store and node.id in set(primitive_names) | {'run'}:
            raise ProgramError('Primitive/function name cannot be assigned')
        if type(node) is ast.Assign:
            if len(node.targets) != 1 or type(node.targets[0]) not in (ast.Name, ast.Subscript) or node.type_comment:
                raise ProgramError('Only one simple assignment target is supported')
        if type(node) is ast.For and (type(node.target) is not ast.Name or node.orelse or node.type_comment):
            raise ProgramError('Only simple bounded for loops are supported')
        if type(node) is ast.Call:
            if type(node.func) is not ast.Name or node.func.id not in primitive_names or node.keywords:
                raise ProgramError('Call must name a sealed primitive with positional arguments')
            calls.append({'name': node.func.id, 'line': node.lineno, 'end_line': node.end_lineno,
                          'column': node.col_offset, 'argument_count': len(node.args)})
        if type(node) is ast.Constant:
            check_value(wrap(node.value), limits)
        if type(node) is ast.Dict and any(key is None for key in node.keys):
            raise ProgramError('Dictionary unpacking is unsupported')
    calls.sort(key=lambda row: (row['line'], row['column']))
    return tree, {'source_sha256': hashlib.sha256(source).hexdigest(), 'ast_nodes': len(nodes), 'calls': calls,
                  'profile': 'bounded-python-syntax-development-v1', 'grants_execution_authority': False}


class Returned(Exception):
    def __init__(self, value):
        self.value = value


class Interpreter:
    def __init__(self, source, primitive_names, dispatch, *, limits=Limits(), deadline=None):
        self.tree, self.profile = validate(source, primitive_names, limits)
        self.dispatch = dispatch
        self.limits = limits
        self.deadline = deadline if deadline is not None else time.monotonic() + 5
        self.steps = 0
        self.iterations = 0
        self.call_events = []
        self.pc = frozenset()
        self.env = {}

    def tick(self):
        self.steps += 1
        if self.steps > self.limits.steps or time.monotonic() >= self.deadline:
            raise ProgramError('Instruction or cooperative deadline exhausted')

    def checked(self, value):
        return check_value(replace(value, labels=value.labels | self.pc), self.limits)

    def expression(self, node):
        self.tick()
        if type(node) is ast.Constant:
            return self.checked(wrap(node.value))
        if type(node) is ast.Name:
            if node.id not in self.env:
                raise ProgramError('Unbound local: ' + node.id)
            return self.checked(self.env[node.id])
        if type(node) is ast.List:
            return self.checked(Value([self.expression(item) for item in node.elts]))
        if type(node) is ast.Dict:
            pairs = [(self.expression(key), self.expression(value)) for key, value in zip(node.keys, node.values)]
            if any(type(key.data) is not str for key, _ in pairs):
                raise ProgramError('Dictionary keys must be strings')
            return self.checked(Value({key.data: value for key, value in pairs}, frozenset(label for key, _ in pairs for label in labels(key))))
        if type(node) is ast.Subscript:
            obj, key = self.expression(node.value), self.expression(node.slice)
            if type(obj.data) is dict and type(key.data) is str:
                item = obj.data[key.data]
            elif type(obj.data) in (list, str) and type(key.data) is int:
                item = obj.data[key.data]
                if type(obj.data) is str:
                    item = wrap(item)
            else:
                raise ProgramError('Unsupported indexing operation')
            return self.checked(replace(item, labels=item.labels | obj.labels | labels(key)))
        if type(node) is ast.Call:
            if len(self.call_events) >= self.limits.calls:
                raise ProgramError('Primitive call bound exceeded')
            args = [self.expression(arg) for arg in node.args]
            call = {'index': len(self.call_events), 'name': node.func.id, 'line': node.lineno,
                    'column': node.col_offset, 'arguments': [unbox(arg) for arg in args],
                    'argument_label_paths': [label_paths(arg) for arg in args], 'control_labels': sorted(self.pc)}
            self.call_events.append({key: value for key, value in call.items() if key != 'arguments'})
            self.call_events[-1]['arguments_sha256'] = hashlib.sha256(json.dumps(call['arguments'], sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
            result = self.dispatch(call, args)
            if not isinstance(result, Value):
                raise ProgramError('Primitive returned an untyped/unlabelled value')
            return self.checked(result)
        if type(node) is ast.BoolOp:
            taint = frozenset()
            for part in node.values:
                value = self.expression(part)
                taint |= labels(value)
                if (type(node.op) is ast.And and not unbox(value)) or (type(node.op) is ast.Or and unbox(value)):
                    break
            return self.checked(replace(value, labels=value.labels | taint))
        if type(node) is ast.UnaryOp:
            value = self.expression(node.operand)
            operation = {ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_}[type(node.op)]
            return self.checked(wrap(operation(unbox(value)), labels(value)))
        if type(node) is ast.BinOp:
            left, right = self.expression(node.left), self.expression(node.right)
            a, b = unbox(left), unbox(right)
            if type(node.op) is ast.Mult:
                seq, count = (a, b) if type(a) in (str, list) else (b, a)
                if type(seq) in (str, list) and type(count) is int and max(0, count) * len(seq) > min(self.limits.string_bytes, self.limits.collection if type(seq) is list else self.limits.string_bytes):
                    raise ProgramError('Sequence multiplication would exceed bounds')
            operation = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                         ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}[type(node.op)]
            if type(node.op) is ast.Mod and type(a) is str:
                raise ProgramError('String formatting is not supported')
            if type(node.op) is ast.Add and type(left.data) is list and type(right.data) is list:
                return self.checked(Value(left.data + right.data, left.labels | right.labels))
            if type(node.op) is ast.Mult and type(left.data) is list and type(right.data) is int:
                return self.checked(Value(left.data * right.data, left.labels | labels(right)))
            if type(node.op) is ast.Mult and type(right.data) is list and type(left.data) is int:
                return self.checked(Value(right.data * left.data, right.labels | labels(left)))
            return self.checked(wrap(operation(a, b), labels(left) | labels(right)))
        if type(node) is ast.Compare:
            left = self.expression(node.left)
            taint = labels(left)
            result = True
            for op, expr in zip(node.ops, node.comparators):
                right = self.expression(expr)
                a, b = unbox(left), unbox(right)
                taint |= labels(right)
                if type(op) in (ast.Is, ast.IsNot) and not (a is None or b is None or type(a) is bool and type(b) is bool):
                    raise ProgramError('Identity comparison supports only None and booleans')
                operation = {ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
                             ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
                             ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
                             ast.Is: operator.is_, ast.IsNot: operator.is_not}[type(op)]
                if not operation(a, b):
                    result = False
                    break
                left = right
            return self.checked(wrap(result, taint))
        raise ProgramError('Unsupported expression')

    def statements(self, statements):
        for node in statements:
            self.tick()
            if type(node) is ast.Assign:
                value = self.expression(node.value)
                target = node.targets[0]
                if type(target) is ast.Name:
                    self.env[target.id] = value
                else:
                    obj, key = self.expression(target.value), self.expression(target.slice)
                    self.pc |= labels(key)
                    if type(obj.data) is dict and type(key.data) is str or type(obj.data) is list and type(key.data) is int:
                        obj.data[key.data] = replace(value, labels=labels(key) | self.pc | value.labels)
                        check_value(obj, self.limits)
                    else:
                        raise ProgramError('Unsupported indexed assignment')
            elif type(node) is ast.Expr:
                self.expression(node.value)
            elif type(node) is ast.If:
                condition = self.expression(node.test)
                # Monotone program-counter labels conservatively preserve both
                # taken and untaken branch dependencies through later outputs.
                self.pc |= labels(condition)
                self.statements(node.body if unbox(condition) else node.orelse)
            elif type(node) is ast.For:
                values = self.expression(node.iter)
                if type(values.data) not in (list, str):
                    raise ProgramError('For loops require a list or string')
                self.pc |= values.labels
                for value in values.data:
                    self.iterations += 1
                    if self.iterations > self.limits.iterations:
                        raise ProgramError('Loop iteration bound exceeded')
                    self.env[node.target.id] = self.checked(value if isinstance(value, Value) else wrap(value))
                    self.statements(node.body)
            elif type(node) is ast.Return:
                raise Returned(self.expression(node.value) if node.value else self.checked(wrap(None)))
            elif type(node) is ast.Pass:
                pass
            else:
                raise ProgramError('Unsupported statement')

    def run(self, payload, source_labels=None):
        self.env = {'payload': check_value(wrap(payload, source_labels=source_labels), self.limits)}
        try:
            self.statements(self.tree.body[0].body)
        except Returned as returned:
            return returned.value
        except (TypeError, KeyError, IndexError, ZeroDivisionError, OverflowError, RecursionError) as exc:
            raise ProgramError(type(exc).__name__ + ': ' + str(exc)) from exc
        return self.checked(wrap(None))
