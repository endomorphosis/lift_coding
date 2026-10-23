#!/usr/bin/env python3
"""Provider-free, source-bound static dependency nomination preview.

This evidence program never imports the target module. Its graph closes only
recorded syntactic nominations; it does not establish Python name binding,
whole-program dependence, requirement satisfaction, or proof authority.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat
import sys
import time

CHECKOUT = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
EVIDENCE = Path('/home/barberb/lift_coding/maintenance/terminal-context-budget-20261011-01')
TOKEN_CACHE = Path('/home/barberb/lift_coding/maintenance/terminal-compact-context-20261011-01/tokenizer-cache')
TOKEN_ASSET = 'fb374d419588a4632f3f557e76b4b70aebbca790'
TOKEN_SHA = '446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d'
SOURCE_SHA = '761756ce31753e526c48d28ccbca13a5d2493b16fe37aff3e1e4d2efaf3a2bba'
SEEDS = ('HeaderDict', '_hkey', '_hval', 'BaseResponse.headers',
         'BaseResponse.__setitem__', 'BaseResponse.set_header',
         'BaseResponse.add_header', 'BaseResponse.get_header', 'BaseResponse.headerlist')
CLAIMS = {key: False for key in ('semantic_graph_completeness', 'python_name_binding_verified',
    'source_semantics_verified', 'task_coverage_verified', 'task_completion', 'proof_authority',
    'execution_authority', 'completion_authority', 'model_convergence_proved')}
BOUNDS = {'source_bytes': 262144, 'symbols': 1024, 'closure_nodes': 256,
          'closure_edges': 1024, 'closure_depth': 16, 'capsule_bytes': 32768,
          'inline_frontier_rows': 16, 'inline_symbol_rows': 32}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or path.is_symlink():
        raise ValueError('regular non-symlink input required')
    raw = path.read_bytes()
    after = path.lstat()
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(before, name) != getattr(after, name) for name in fields):
        raise ValueError('source input changed during read')
    return raw, {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw),
                 'witness': {name: getattr(after, name) for name in fields}}


def require_source(path, expected):
    raw, current = pin(path)
    if current['sha256'] != expected:
        raise ValueError('source changed; stale nominations refused')
    return raw


def definitions(tree, *, strict=False):
    values = {}
    ambiguous = set()
    class Collect(ast.NodeVisitor):
        scope = []
        def visit_definition(self, node):
            name = '.'.join([*self.scope, node.name])
            if name in values:
                ambiguous.add(name)
                if strict:
                    raise ValueError('ambiguous duplicate source definition: ' + name)
            values[name] = node
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()
        visit_ClassDef = visit_definition
        visit_FunctionDef = visit_definition
        visit_AsyncFunctionDef = visit_definition
    Collect().visit(tree)
    return values, ambiguous


def expression(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = expression(node.value)
        return base + '.' + node.attr if base else ''
    return ''


def resolve(callee, symbols):
    # "Resolved" is a unique lexical nomination, not runtime receiver binding.
    if callee in symbols:
        return 'unique_local_syntactic_target', callee
    if callee == '<dynamic>':
        return 'dynamic_call_requires_expansion', None
    if callee.startswith(('self.', 'cls.', 'super.')):
        return 'receiver_binding_unresolved', None
    if callee in vars(builtins):
        return 'builtin_environment_binding_unverified', None
    return ('external_or_attribute_binding_unresolved' if '.' in callee
            else 'local_parameter_global_or_external_binding_unresolved'), None


def spans(raw, nodes, selected):
    lines = raw.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    selected_ranges = []
    descriptors = []
    for name in sorted(selected):
        node = nodes[name]
        first = min([node.lineno, *[d.lineno for d in node.decorator_list]])
        last = node.end_lineno
        start, end = offsets[first - 1], offsets[last]
        fragment = raw[start:end]
        descriptors.append({'symbol': name, 'line_start': first, 'line_end': last,
                            'byte_start': start, 'byte_end': end, 'sha256': sha(fragment)})
        selected_ranges.append((start, end, first, last))
    merged = []
    for start, end, first, last in sorted(selected_ranges):
        if merged and start <= merged[-1][1]:
            old = merged[-1]
            merged[-1] = (old[0], max(old[1], end), old[2], max(old[3], last))
        else:
            merged.append((start, end, first, last))
    view = b''.join((f'\n# Exact source view bottle.py lines {first}-{last}; UTF-8 bytes {start}:{end}\n'.encode()
                     + raw[start:end]) for start, end, first, last in merged)
    return view, descriptors, merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', type=Path, default=EVIDENCE / 'public-source')
    parser.add_argument('--source', default='bottle.py')
    parser.add_argument('--instruction', type=Path, default=CHECKOUT /
        'benchmarks/agent_supervisor/container_coding/fixtures/public-bottle-instruction.md')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.repository.resolve(strict=True)
    source = root / args.source
    if source.resolve(strict=True) != source or source.parent != root:
        raise ValueError('one canonical public repository-contained source required')
    output_path = args.output.absolute()
    if (output_path.exists() or not output_path.is_relative_to(EVIDENCE)
            or output_path == EVIDENCE or '..' in output_path.parts
            or output_path.resolve(strict=False) != output_path
            or not output_path.parent.is_dir()
            or output_path.parent.resolve(strict=True) != output_path.parent):
        raise ValueError('new evidence-contained output required')
    started = time.monotonic()
    raw, source_pin = pin(source)
    instruction, instruction_pin = pin(args.instruction.resolve(strict=True))
    if len(raw) > BOUNDS['source_bytes'] or source_pin['sha256'] != SOURCE_SHA:
        raise ValueError('exact permitted public Bottle source required')
    if len(instruction) > 8192:
        raise ValueError('bounded public instruction required')
    sys.path.insert(0, str(CHECKOUT))
    from ipfs_accelerate_py.agent_supervisor.core.conflict_graph import build_python_ast_blob_record
    from ipfs_accelerate_py.agent_supervisor.analysis.semantic_dependency_graph import (
        ClosureBounds, SemanticAuthority, SemanticDependencyGraph, SemanticEdge,
        SemanticEdgeKind, SemanticNode, SemanticNodeKind, SemanticProvenance, SemanticTrust)
    import duckdb
    producer_paths = [CHECKOUT / 'ipfs_accelerate_py/agent_supervisor' / name for name in
        ('core/conflict_graph.py', 'analysis/semantic_dependency_graph.py', 'task_sources/task_identity.py')]
    producer_pins = [pin(path)[1] for path in producer_paths]
    native = build_python_ast_blob_record(raw.decode('utf-8'))
    if native.parse_error or len(native.qualified_symbols) > BOUNDS['symbols']:
        raise ValueError('bounded native AST parse required')
    tree = ast.parse(raw.decode('utf-8'))
    nodes, ambiguous = definitions(tree)
    if set(nodes) != set(native.qualified_symbols):
        raise ValueError('native AST and exact definition census disagree')
    if not set(SEEDS) <= set(nodes):
        raise ValueError('authored seed does not bind current exact native symbol')
    parse_seconds = time.monotonic() - started
    output_path.mkdir()
    output = output_path.resolve(strict=True)
    if output != output_path:
        raise ValueError('output directory changed during creation')
    calls = []
    for fact in native.calls:
        owner, callee = fact.split('->', 1)
        status, target = resolve(callee, nodes)
        calls.append({'owner': owner, 'callee': callee, 'status': status, 'target': target})
    # Classes nominate all exact members and uniquely named local bases. No
    # receiver, import, callback, inheritance dispatch or data-flow inference.
    relationships = [(row['owner'], row['target'], 'static_call_nomination')
                     for row in calls if row['target'] and row['owner'] in nodes]
    extras = []
    for name, node in nodes.items():
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    relationships.append((name, name + '.' + child.name, 'exact_class_member'))
            for base in node.bases:
                callee = expression(base) or '<dynamic>'
                status, target = resolve(callee, nodes)
                if target:
                    relationships.append((name, target, 'local_base_nomination'))
                else:
                    extras.append({'owner': name, 'callee': callee, 'status': status,
                                   'target': None, 'kind': 'class_base'})
    selected = set(SEEDS)
    for _ in range(BOUNDS['closure_depth']):
        added = {target for owner, target, _ in relationships if owner in selected} - selected
        if not added:
            break
        selected.update(added)
        if len(selected) + 1 > BOUNDS['closure_nodes']:
            raise ValueError('mandatory nominated closure exceeds node bound')
    else:
        raise ValueError('mandatory nominated closure exceeds depth bound')
    if selected & ambiguous:
        raise ValueError('selected target has ambiguous source definitions: ' + ','.join(sorted(selected & ambiguous)))
    retained = sorted(set((a, b, kind) for a, b, kind in relationships if a in selected))
    if len(retained) + len(SEEDS) > BOUNDS['closure_edges']:
        raise ValueError('mandatory nominated closure exceeds edge bound')
    frontier = sorted([row for row in [*calls, *extras] if row['owner'] in selected and not row['target']],
                      key=lambda row: (row['owner'], row['callee'], row['status']))
    frontier.extend([
        {'owner': '<scope>', 'callee': '<module-initialization-and-global-bindings>',
         'status': 'not_analyzed_requires_exact_module_expansion', 'target': None,
         'kind': 'missing_analysis_boundary'},
        {'owner': '<scope>', 'callee': '<control-flow-data-flow-alias-and-reflection>',
         'status': 'not_analyzed_requires_qualified_dependency_analysis', 'target': None,
         'kind': 'missing_analysis_boundary'},
    ])
    # These records are descriptive syntactic inputs in a preview namespace.
    # Graph "authoritative" means eligible for this structural traversal only.
    decision = 'preview:decision:' + sha(encoded({'source_sha256': source_pin['sha256'],
                                                'instruction_sha256': instruction_pin['sha256'], 'seeds': SEEDS}))
    graph_root = 'preview:root:' + sha(encoded({'decision': decision, 'native': native.to_dict()}))
    common = {'root_id': graph_root, 'source_root_id': 'sha256:' + source_pin['sha256'],
              'trust': SemanticTrust.REVIEWED, 'authority': SemanticAuthority.DESCRIPTIVE_INPUT,
              'version': 'task-static-nomination-preview@1'}
    graph_nodes = [SemanticNode(node_id=decision, kind=SemanticNodeKind.DECISION,
        provenance=SemanticProvenance.DECISION, provenance_id=decision,
        record={'seed_scope': 'authored_header_focus_not_inferred_intent', **CLAIMS}, **common)]
    for name in sorted(selected):
        graph_nodes.append(SemanticNode(node_id='symbol:' + name, kind=SemanticNodeKind.SYMBOL,
            provenance=SemanticProvenance.AST, provenance_id=native.symbol_hashes[name],
            record={'symbol': name, 'source_sha256': source_pin['sha256'],
                    'native_symbol_hash': native.symbol_hashes[name]}, **common))
    graph_edges = []
    for owner, target, kind in [(decision, name, 'authored_seed') for name in SEEDS] + retained:
        graph_edges.append(SemanticEdge(source=owner if owner == decision else 'symbol:' + owner,
            target='symbol:' + target, kind=SemanticEdgeKind.DEPENDS_ON,
            provenance=SemanticProvenance.AST, provenance_id='preview:edge:' + sha(encoded([owner, target, kind])),
            mandatory=True, **common))
    graph = SemanticDependencyGraph(root_id=graph_root, nodes=tuple(graph_nodes), edges=tuple(graph_edges))
    closure = graph.mandatory_closure(decision, bounds=ClosureBounds(max_nodes=BOUNDS['closure_nodes'],
        max_edges=BOUNDS['closure_edges'], max_depth=BOUNDS['closure_depth'], max_annotations=1))
    assert set(closure.node_ids) == {decision, *['symbol:' + name for name in selected]}
    view, symbol_spans, ranges = spans(raw, nodes, selected)
    range_descriptors = {'schema': 'task-selected-exact-source-ranges@1', 'source_path': args.source,
        'source_sha256': source_pin['sha256'], 'source_bytes': len(raw),
        'ranges': [{'byte_start': start, 'byte_end': end, 'line_start': first, 'line_end': last,
                    'sha256': sha(raw[start:end]), 'bytes': end-start} for start,end,first,last in ranges],
        'code_view_is_executable_module': False, 'source_semantics_verified': False}
    database = output / 'preview.duckdb'
    with duckdb.connect(str(database), config={'threads': 1}) as db:
        db.execute('CREATE TABLE sources(path VARCHAR, sha256 VARCHAR, bytes BIGINT)')
        db.execute('INSERT INTO sources VALUES (?, ?, ?)', [args.source, source_pin['sha256'], len(raw)])
        db.execute('CREATE TABLE symbols(symbol VARCHAR PRIMARY KEY, source_sha256 VARCHAR, symbol_hash VARCHAR, line_start INTEGER, line_end INTEGER)')
        db.executemany('INSERT INTO symbols VALUES (?, ?, ?, ?, ?)',
            [(name, source_pin['sha256'], native.symbol_hashes[name], *native.symbol_lines[name]) for name in sorted(nodes)])
        db.execute('CREATE TABLE static_calls(owner VARCHAR, callee VARCHAR, status VARCHAR, target VARCHAR)')
        db.executemany('INSERT INTO static_calls VALUES (?, ?, ?, ?)',
                       [(r['owner'], r['callee'], r['status'], r['target']) for r in calls])
        db.execute('CREATE TABLE kg_edges(subject VARCHAR, dependency VARCHAR, kind VARCHAR)')
        db.executemany('INSERT INTO kg_edges VALUES (?, ?, ?)', retained)
        db.execute('CREATE TABLE closure_symbols(symbol VARCHAR PRIMARY KEY)')
        db.executemany('INSERT INTO closure_symbols VALUES (?)', [(name,) for name in sorted(selected)])
    database_pin = pin(database)[1]
    with duckdb.connect(str(database), read_only=True, config={'threads': 1}) as db:
        hydrated = tuple(row[0] for row in db.execute('SELECT symbol FROM closure_symbols ORDER BY symbol').fetchall())
        assert hydrated == tuple(sorted(selected))
        assert db.execute('SELECT COUNT(*) FROM symbols').fetchone()[0] == len(nodes)
        assert db.execute('SELECT COUNT(*) FROM static_calls').fetchone()[0] == len(calls)
    assert pin(database)[1] == database_pin
    files = {'native-ast.json': encoded(native.to_dict()), 'graph.json': encoded(graph.to_dict()),
             'closure.json': encoded(closure.to_dict()), 'frontier.json': encoded(frontier),
             'symbol-spans.json': encoded(symbol_spans), 'selected-ranges.json': encoded(range_descriptors),
             'selected-code.txt': view}
    file_pins = {name: {'path': name, 'sha256': sha(value), 'bytes': len(value)} for name, value in files.items()}
    capsule = {'schema': 'task-static-dependency-preview-capsule@1', 'source':
        {key: source_pin[key] for key in ('sha256', 'bytes')}, 'source_path': args.source,
        'intent_source_sha256': instruction_pin['sha256'], 'seeds': list(SEEDS),
        'seed_authority': 'authorial_nomination_only', 'closure_scope': 'complete_relative_to_admitted_preview_graph_only',
        'graph_id': graph.graph_id, 'closure_id': closure.closure_id,
        'selected_symbol_count': len(selected), 'included_symbols': symbol_spans[:BOUNDS['inline_symbol_rows']],
        'complete_native_symbol_count': len(nodes), 'omitted_source_symbol_count': len(nodes) - len(selected),
        'omitted_symbol_metadata_count': max(0, len(symbol_spans) - BOUNDS['inline_symbol_rows']),
        'frontier_count': len(frontier), 'included_frontier': frontier[:BOUNDS['inline_frontier_rows']],
        'omitted_frontier_count': max(0, len(frontier) - BOUNDS['inline_frontier_rows']),
        'expansion_handles': [file_pins[name] for name in ('symbol-spans.json', 'selected-ranges.json',
                                                       'frontier.json', 'selected-code.txt')],
        'bounds': BOUNDS, 'claims': CLAIMS,
        'failure_contract': 'Do not infer task satisfaction or execution semantics. Resolve frontier and read exact source before editing.'}
    capsule_raw = encoded(capsule)
    if len(capsule_raw) > BOUNDS['capsule_bytes']:
        raise ValueError('complete capsule exceeds byte bound')
    files['metadata-capsule.json'] = capsule_raw
    # A common complete wrapper is included in every paired count. The exact
    # code view is disjoint slices, not an executable/equivalent Python module.
    def render(payload):
        return (b'Public task instruction (verbatim):\n' + instruction +
                b'\n\nCode evidence (descriptive; not proof or task satisfaction):\n' + payload)
    renders = {'whole_module': render(raw), 'selected_exact_code': render(view),
               'metadata_and_bounded_handles': render(capsule_raw),
               'selected_exact_code_and_metadata': render(view + b'\n\nDependency metadata capsule:\n' + capsule_raw)}
    asset_raw, asset_pin = pin(TOKEN_CACHE / TOKEN_ASSET)
    if sha(asset_raw) != TOKEN_SHA:
        raise ValueError('pinned offline tokenizer asset differs')
    os.environ['TIKTOKEN_CACHE_DIR'] = str(TOKEN_CACHE)
    import tiktoken
    tokenizer = tiktoken.get_encoding('o200k_base')
    counts = {name: {'utf8_bytes': len(value), 'local_tokens': len(tokenizer.encode(value.decode('utf-8'))),
                     'sha256': sha(value)} for name, value in renders.items()}
    for name, payload in renders.items():
        files['render-' + name + '.txt'] = payload
    # Meaningful refusal controls use fresh in-memory data only, never alter
    # the public source or a production namespace.
    control_dir = output / 'fresh-negative-controls'
    control_dir.mkdir()
    changed_source = control_dir / 'changed-source.py'
    changed_source.write_bytes(raw + b'\n# fresh source-change refusal control\n')
    stale_control = False
    try:
        require_source(changed_source, source_pin['sha256'])
    except ValueError:
        stale_control = True
    ambiguous_control = False
    try:
        definitions(ast.parse('def same(): pass\ndef same(): pass\n'), strict=True)
    except ValueError:
        ambiguous_control = True
    assert stale_control and ambiguous_control
    assert require_source(source, source_pin['sha256']) == raw
    assert pin(args.instruction.resolve(strict=True))[1] == instruction_pin
    assert [pin(path)[1] for path in producer_paths] == producer_pins
    summary = {'schema': 'task-static-dependency-preview-measurement@1', 'provider_calls': 0,
        'target_module_imports': 0, 'training_steps': 0, 'prover_invocations': 0,
        'source': source_pin, 'instruction': instruction_pin, 'producer_pins': producer_pins,
        'native_symbol_count': len(nodes), 'native_static_call_fact_count': len(calls),
        'ambiguous_definition_count': len(ambiguous), 'ambiguous_definitions': sorted(ambiguous),
        'selected_symbol_count': len(selected), 'selected_symbols': sorted(selected),
        'selected_merged_range_count': len(ranges), 'selected_exact_raw_bytes': sum(end-start for start,end,_,_ in ranges),
        'frontier_count': len(frontier), 'frontier_status_counts': {key: sum(row['status'] == key for row in frontier)
            for key in sorted({row['status'] for row in frontier})},
        'materialized_metadata': {'native_ast_symbols': len(nodes), 'native_static_call_facts': len(calls),
            'selected_static_kg_edges': len(retained), 'vectors': 0, 'behavioral_contracts': 0,
            'proofs': 0, 'quack_task_state': False, 'ducklake_projection': False},
        'graph_id': graph.graph_id, 'closure_id': closure.closure_id,
        'graph_relative_closure_complete': closure.complete, 'claims': CLAIMS,
        'fresh_database': database_pin, 'read_only_reopen_bytes_identity_unchanged': True,
        'source_and_producers_unchanged': True, 'controls': {'changed_source_refused': stale_control,
            'ambiguous_definition_refused': ambiguous_control}, 'bounds': BOUNDS, 'whole_render_counts': counts,
        'tokenizer': {'scope': 'LOCAL representation counts; not provider-native cumulative usage or configured-model tokenizer',
            'encoding': 'o200k_base', 'tiktoken_version': importlib.metadata.version('tiktoken'),
            'vocabulary_size': tokenizer.n_vocab, 'asset': asset_pin, 'network_calls': 0},
        'seconds': {'native_parse': parse_seconds, 'total': time.monotonic() - started},
        'limitations': ['Authored header seed focus is not an interpretation proof of the full public task.',
            'Unique syntactic names do not verify runtime names, receivers, monkey patches, callbacks, imports or builtins.',
            'Native calls are source facts, not a complete call/data/control-flow analysis.',
            'Class code views include native class definitions; disjoint method views are not an executable module.',
            'Metadata packet omits code bodies and cannot replace later expansion; initial-size savings are not total-token savings.',
            'No model planning or validation call is removed by this offline preview; current symbolic planning already uses zero provider calls.',
            'Fresh preview DuckDB is not production DuckLake/Quack hydration or proof-cache authority.']}
    for name, payload in files.items():
        (output / name).write_bytes(payload)
    (output / 'summary.json').write_bytes(encoded(summary))
    print(json.dumps({'output': str(output), 'summary_sha256': sha(encoded(summary)),
        'selected_symbol_count': len(selected), 'frontier_count': len(frontier), 'whole_render_counts': counts}, sort_keys=True))


if __name__ == '__main__':
    main()
