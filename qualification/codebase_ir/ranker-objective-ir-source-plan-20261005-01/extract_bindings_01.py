#!/usr/bin/env python3
"""Source-only AST inventory. Never import or execute the pinned ranker module."""
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path('/home/barberb/lift_coding')
OUT = ROOT / 'qualification/codebase_ir/ranker-objective-ir-source-plan-20261005-01'
SOURCE = ROOT / 'artifacts/codebase_ir_terminal_bench/terminal-codebase-ir-intent-corpus-head-20261004-01/source/benchmarks/agent_supervisor/container_coding/terminal_codebase_intent_ranker_training.py'
EXPECTED = '3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def node_record(node, path, text):
    structural = ast.dump(node, annotate_fields=True, include_attributes=False)
    segment = ast.get_source_segment(text, node)
    return {
        'ast_path': path,
        'node_kind': type(node).__name__,
        'span': [node.lineno, node.col_offset, node.end_lineno, node.end_col_offset],
        'ast_dump': structural,
        'ast_dump_utf8_sha256': digest(structural.encode('utf-8')),
        'source_segment': segment,
        'source_segment_utf8_bytes': len(segment.encode('utf-8')),
        'source_segment_utf8_sha256': digest(segment.encode('utf-8')),
    }


def main():
    source = SOURCE.read_bytes()
    if len(source) != 16391 or digest(source) != EXPECTED:
        raise SystemExit('refused: pinned source bytes differ')
    text = source.decode('utf-8')
    tree = ast.parse(text, filename=str(SOURCE), mode='exec')
    indexed = list(enumerate(tree.body))
    objective_i, objective = next((i, n) for i, n in indexed
                                  if isinstance(n, ast.FunctionDef) and n.name == '_objective')
    dot_i, dot = next((i, n) for i, n in indexed
                     if isinstance(n, ast.FunctionDef) and n.name == '_dot')
    l2_i, l2 = next((i, n) for i, n in indexed
                   if isinstance(n, ast.Assign) and len(n.targets) == 1
                   and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'L2')
    math_i, math_import = next((i, n) for i, n in indexed
                              if isinstance(n, ast.Import)
                              and any(a.name == 'math' and a.asname is None for a in n.names))
    prefix = f'module.body[{objective_i}]'
    statements = [node_record(n, f'{prefix}.body[{i}]', text)
                  for i, n in enumerate(objective.body)]
    leaves = {
        'stable_loss_scalar': node_record(objective.body[1].value.left.args[0].elt,
            f'{prefix}.body[1].value.left.args[0].elt', text),
        'stable_factor_scalar': node_record(objective.body[3].value.elt,
            f'{prefix}.body[3].value.elt', text),
        'gradient_coordinate_scalar': node_record(objective.body[4].value.elt,
            f'{prefix}.body[4].value.elt', text),
        'gradient_zip_product_scalar': node_record(objective.body[4].value.elt.right.left.args[0].elt,
            f'{prefix}.body[4].value.elt.right.left.args[0].elt', text),
        'selected_return_objective_scalar': node_record(objective.body[6].value.elts[0].values[0],
            f'{prefix}.body[6].value.elts[0].values[0]', text),
    }
    external_names = sorted({n.id for n in ast.walk(objective) if isinstance(n, ast.Name)}
                            - {'weights', 'differences', 'margins', 'data', 'regularizer',
                               'factors', 'gradient', 'row', 'z', 'f', 'i', 'x'})
    result = {
        'schema': 'ranker-objective-source-ast-bindings@1',
        'status': 'source_only_ast_inventory_not_qualification',
        'source': {'path': str(SOURCE), 'bytes': len(source), 'sha256': digest(source)},
        'parser': {'implementation': 'stdlib ast.parse', 'python_version': sys.version.split()[0],
                   'mode': 'exec', 'source_execution_count': 0, 'project_import_count': 0,
                   'ast_parses': 1,
                   'ast_hash_encoding': 'ast.dump(annotate_fields=True, include_attributes=False), UTF-8',
                   'host_parser_source_binding_proved_in_kernel': False},
        'module_ast_sha256': digest(ast.dump(tree, annotate_fields=True,
                                             include_attributes=False).encode('utf-8')),
        'objective': node_record(objective, prefix, text),
        'statements': statements,
        'selected_scalar_leaves': leaves,
        'external_syntax_bindings': {
            'math_import': node_record(math_import, f'module.body[{math_i}]', text),
            'L2_assignment': node_record(l2, f'module.body[{l2_i}]', text),
            '_dot_function': node_record(dot, f'module.body[{dot_i}]', text),
            'names': external_names,
            'calls_in_function': sorted({ast.unparse(n.func) for n in ast.walk(objective)
                                         if isinstance(n, ast.Call)}),
            'actual_python_runtime_binding_or_monkeypatch_absence_proved': False,
        },
        'frontier': {
            'objective_source_equivalence_proved': False,
            'gradient_source_equivalence_proved': False,
            'python_float_semantics_proved': False,
            'whole_function_execution_proved': False,
            'training_loop_proved': False,
            'proof_authority': False,
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'source-bindings.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': result['status'], 'objective_ast_sha256': result['objective']['ast_dump_utf8_sha256'],
                      'source': result['source'], 'written': str(OUT / 'source-bindings.json')}))


if __name__ == '__main__':
    main()
