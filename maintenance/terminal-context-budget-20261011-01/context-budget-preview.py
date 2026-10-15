#!/usr/bin/env python3
"""Count complete provider-free public source/capsule display envelopes.

No target import, model call, native rollout read, source rewriting, or semantic
equivalence claim. The selected static graph has an explicit unresolved frontier.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import stat
import sys

H = Path('/home/barberb/lift_coding/maintenance/terminal-context-budget-20261011-01')
C = Path('/home/barberb/lift_coding/maintenance/terminal-token-reduction-20261007-01/checkout')
CACHE = Path('/home/barberb/lift_coding/maintenance/terminal-compact-context-20261011-01/tokenizer-cache')
ASSET = CACHE / 'fb374d419588a4632f3f557e76b4b70aebbca790'
ASSET_SHA = '446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d'
SOURCE_SHA = '761756ce31753e526c48d28ccbca13a5d2493b16fe37aff3e1e4d2efaf3a2bba'
INSTRUCTION_SHA = '89b1abdf0af19399f720233b5cdf6b2e8e0ff7b6e3fe3e2a3af0d4d298a8641a'


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_pin(path, cap=4_000_000):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > cap:
            raise ValueError('bounded regular input required')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            raw = stream.read(cap + 1)
        after = os.fstat(fd)
        witness = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if len(raw) > cap or any(getattr(before, name) != getattr(after, name) for name in witness):
            raise ValueError('input changed or exceeded read budget')
        if any(getattr(path.lstat(), name) != getattr(after, name) for name in witness):
            raise ValueError('input path changed')
        return raw, {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dependency-preview', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    preview = args.dependency_preview.resolve(strict=True)
    requested_output = args.output.absolute()
    resolved_output = args.output.resolve(strict=False)
    if (not preview.is_relative_to(H) or args.output.exists()
            or resolved_output != requested_output or resolved_output.parent != H):
        raise ValueError('existing preview and new output must be stage-contained')
    paths = [H / 'public-source/bottle.py',
             C / 'benchmarks/agent_supervisor/container_coding/fixtures/public-bottle-instruction.md',
             preview / 'summary.json', preview / 'metadata-capsule.json',
             preview / 'symbol-spans.json', preview / 'frontier.json', preview / 'selected-code.txt',
             H / 'task-dependency-preview.py',
             C / 'ipfs_accelerate_py/agent_supervisor/runtime/code_view_minification.py',
             C / 'test/api/test_code_view_minification.py',
             preview / 'selected-ranges.json', ASSET, Path(__file__)]
    values = [read_pin(path) for path in paths]
    pins = [pin for _, pin in values]
    raw, instruction, summary_raw, metadata, spans_raw, frontier_raw, selected = [row[0] for row in values[:7]]
    if sha(raw) != SOURCE_SHA or sha(instruction) != INSTRUCTION_SHA or pins[-2]['sha256'] != ASSET_SHA:
        raise ValueError('exact public source, instruction and offline tokenizer required')
    summary, spans, frontier = map(json.loads, (summary_raw, spans_raw, frontier_raw))
    if summary['source']['sha256'] != SOURCE_SHA or summary['instruction']['sha256'] != INSTRUCTION_SHA:
        raise ValueError('dependency preview source/task pins disagree')
    if any(summary['claims'].values()) or len(spans) != summary['selected_symbol_count'] or len(frontier) != summary['frontier_count']:
        raise ValueError('preview authority or census mismatch')
    source = raw.decode('utf-8')
    original_lines = list(io.StringIO(source).readlines())
    offsets = [0]
    for line in original_lines:
        offsets.append(offsets[-1] + len(line.encode('utf-8')))
    ranges = []
    for row in spans:
        first, last = row['line_start'], row['line_end']
        if type(first) is not int or type(last) is not int or not 1 <= first <= last <= len(original_lines):
            raise ValueError('invalid source span')
        start, end = offsets[first - 1], offsets[last]
        if (start, end) != (row['byte_start'], row['byte_end']) or sha(raw[start:end]) != row['sha256']:
            raise ValueError('exact source span does not replay')
        ranges.append((start, end, first, last))
    merged = []
    for start, end, first, last in sorted(ranges):
        if merged and start <= merged[-1][1]:
            old = merged[-1]
            merged[-1] = (old[0], max(old[1], end), old[2], max(old[3], last))
        else:
            merged.append((start, end, first, last))
    rebuilt = b''.join(f'\n# Exact source view bottle.py lines {first}-{last}; UTF-8 bytes {start}:{end}\n'.encode()
                       + raw[start:end] for start, end, first, last in merged)
    if rebuilt != selected:
        raise ValueError('selected exact view does not replay from pinned source')
    range_record = json.loads(values[-3][0])
    if range_record['source_sha256'] != SOURCE_SHA or range_record['source_bytes'] != len(raw):
        raise ValueError('declared merged range source differs')
    declared_ranges = range_record['ranges']
    if len(declared_ranges) != len(merged):
        raise ValueError('selected range census differs')
    for declared, (start, end, first, last) in zip(declared_ranges, merged):
        if (declared['byte_start'], declared['byte_end'], declared['line_start'], declared['line_end']) != (start, end, first, last):
            raise ValueError('selected range identities differ')
        if declared['sha256'] != sha(raw[start:end]):
            raise ValueError('selected merged range hash differs')
    os.environ['TIKTOKEN_CACHE_DIR'] = str(CACHE)
    import tiktoken
    tokenizer = tiktoken.get_encoding('o200k_base')
    count = lambda text: len(tokenizer.encode(text, disallowed_special=()))
    sys.path.insert(0, str(C))
    from ipfs_accelerate_py.agent_supervisor.runtime.code_view_minification import build_code_view_preview
    view = build_code_view_preview(source, token_counter=count)
    if not view['ast_structure_verified'] or not view['token_structure_verified'] or view['original_source_sha256'] != SOURCE_SHA:
        raise ValueError('full-file display checks failed')
    display_lines = list(io.StringIO(view['view_text']).readlines())
    if len(display_lines) != len(original_lines):
        raise ValueError('physical source line mapping changed')
    selected_display = view['guidance'].encode() + b''.join(
        f'\n# Display slice bottle.py ORIGINAL lines {first}-{last}; original span SHA256 {sha(raw[start:end])}\n'.encode()
        + ''.join(display_lines[first-1:last]).encode()
        for start, end, first, last in merged)
    selected_labeled_exact = b''.join(
        f'\n# Display slice bottle.py ORIGINAL lines {first}-{last}; original span SHA256 {sha(raw[start:end])}\n'.encode()
        + raw[start:end] for start, end, first, last in merged)
    # The dictionary is a bounded descriptive projection, not an attested
    # production expansion protocol. Its handles point to public stage files.
    handles = [{'path': name, 'bytes': len(payload), 'sha256': sha(payload)}
               for name, payload in [('symbol-spans.json', spans_raw), ('frontier.json', frontier_raw), ('selected-code.txt', selected)]]
    compact = encoded({'schema': 'context-budget-preview-projection@1',
        'source_path': 'bottle.py', 'source_sha256': SOURCE_SHA, 'instruction_sha256': INSTRUCTION_SHA,
        'selection_scope': 'authored header focus; closure only relative to preview static graph',
        'native_symbol_count': summary['native_symbol_count'], 'selected_symbol_count': len(spans),
        'graph_id': summary['graph_id'], 'closure_id': summary['closure_id'],
        'frontier_count': len(frontier), 'frontier_status_counts': summary['frontier_status_counts'],
        'omitted_inline_symbol_rows': len(spans), 'omitted_inline_frontier_rows': len(frontier),
        'expansion_handles': handles, 'expansion_protocol_implemented': False,
        'claims': summary['claims'],
        'failure_contract': 'Frontier remains unresolved. These are descriptive nominations, not full task coverage. Read exact original before edits. Stage handles require later bounded verified retrieval.'})
    def render(payload):
        return b'Public task instruction (verbatim):\n' + instruction + b'\n\nCode evidence (descriptive; not proof or task satisfaction):\n' + payload
    def combine(capsule, code):
        return b'Descriptive metadata capsule:\n' + capsule + b'\n\nRead-only source evidence:\n' + code
    renders = {'whole_module': render(raw), 'whole_module_minified': render(view['rendered_view'].encode()),
               'selected_exact_code': render(selected), 'metadata_verbose_handles': render(metadata),
               'metadata_compact_handles': render(compact),
               'selected_exact_with_verbose_metadata': render(combine(metadata, selected)),
               'selected_exact_with_compact_metadata': render(combine(compact, selected)),
               'selected_labeled_exact_with_compact_metadata': render(combine(compact, selected_labeled_exact)),
               'selected_display_with_compact_metadata': render(combine(compact, selected_display)),
               'whole_module_with_compact_metadata': render(combine(compact, raw))}
    counts = {name: {'utf8_bytes': len(payload), 'local_tokens': count(payload.decode('utf-8')), 'sha256': sha(payload)}
              for name, payload in renders.items()}
    shared = {'whole_module': 'whole_module', 'selected_exact_code': 'selected_exact_code',
              'metadata_and_bounded_handles': 'metadata_verbose_handles'}
    for dependency_name, name in shared.items():
        if summary['whole_render_counts'][dependency_name] != counts[name]:
            raise ValueError('independent tokenizer render count disagrees with dependency preview')
    full_pair = ('whole_module', 'whole_module_minified')
    selected_pair = ('selected_exact_with_compact_metadata', 'selected_display_with_compact_metadata')
    gates = {}
    for name, (original, candidate) in [('full_file', full_pair), ('selected_spans', selected_pair)]:
        accepted = counts[candidate]['local_tokens'] < counts[original]['local_tokens'] and counts[candidate]['utf8_bytes'] < counts[original]['utf8_bytes']
        gates[name] = {'scope': 'LOCAL complete-envelope comparison only; no live runtime selection',
                       'accepted': accepted, 'original': original, 'candidate': candidate,
                       'selected': candidate if accepted else original}
    comparisons = []
    for baseline, candidate in [full_pair, selected_pair,
        ('selected_labeled_exact_with_compact_metadata', 'selected_display_with_compact_metadata'),
        ('whole_module_with_compact_metadata', 'selected_exact_with_compact_metadata'),
        ('selected_exact_with_verbose_metadata', 'selected_exact_with_compact_metadata')]:
        before, after = counts[baseline]['local_tokens'], counts[candidate]['local_tokens']
        comparisons.append({'baseline': baseline, 'candidate': candidate, 'local_tokens_saved': before-after,
                            'local_reduction_percent': round((before-after)*100/before, 6),
                            'task_sufficiency_verified': False, 'provider_token_savings_verified': False})
    receipt = {'schema': 'context-budget-public-source-experiment@1', 'pins': pins,
        'provider_calls': 0, 'target_module_imports': 0, 'candidate_source_modified': False,
        'training_steps': 0, 'prover_invocations': 0, 'production_runtime_controls_changed': False,
        'local_tokenizer': {'encoding': 'o200k_base', 'tiktoken_version': importlib.metadata.version('tiktoken'),
            'vocabulary_size': tokenizer.n_vocab, 'asset_sha256': ASSET_SHA, 'network_calls': 0,
            'scope': 'LOCAL exact representation counts using a surrogate; not configured provider tokenizer, native cumulative usage, or billed totals'},
        'native_symbols': summary['native_symbol_count'], 'selected_symbols': len(spans),
        'unresolved_frontier': len(frontier), 'materialized_metadata': summary['materialized_metadata'],
        'source_spans_exactly_replayed': True, 'whole_render_counts': counts, 'comparisons': comparisons,
        'local_minification_gates': gates,
        'minification': {key: value for key, value in view.items() if key not in {'view_text', 'rendered_view', 'removed_comments'}},
        'claims': summary['claims'],
        'limitations': ['The current initial code-retrieval prompt carries metadata, not whole source bodies; source-view savings apply to later reads or an explicitly changed delivery route.',
            'Authored selected seeds and unresolved frontier do not establish sufficient context for all public task requirements.',
            'Full module structural checks do not authenticate Python semantics, dynamic binding, or partial-view execution.',
            'No codebaseIR training, formal certificate, Lean check, task trial, or provider convergence occurred.',
            'Metadata-handle-only views require later source expansion; do not compare them as equally sufficient task inputs.',
            'Minifying selected display slices adds labels and guidance; a complete-envelope gate can correctly reject it.',
            'All counts are independently tokenized complete strings; no fragment-token summation or cumulative-token attribution.']}
    for path, (_, old) in zip(paths, values):
        if read_pin(path)[1] != old:
            raise ValueError('input or producer changed during experiment')
    output = args.output
    output.mkdir()
    for name, payload in renders.items():
        (output / ('render-' + name + '.txt')).write_bytes(payload)
    (output / 'compact-metadata-capsule.json').write_bytes(compact)
    (output / 'minification-comment-sidecar.json').write_bytes(encoded(view['removed_comments']))
    (output / 'summary.json').write_bytes(encoded(receipt))
    print(json.dumps({'output': str(output), 'summary_sha256': sha(encoded(receipt)),
                      'whole_render_counts': counts, 'local_minification_gates': gates}, sort_keys=True))


if __name__ == '__main__':
    main()
