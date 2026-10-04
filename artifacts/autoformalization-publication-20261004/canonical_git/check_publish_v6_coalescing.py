"""Read-only V6 source extraction and exact pointer coalescing checks."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import runpy
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
PUBLISHER = BASE / 'publish_integrated_v6.py'
PUBLISHER_SHA = '638ea6cdb81595740c74623dca554f3e71efd2f55f082361d7660a6ea922b3b2'
REPORT = BASE / 'git/root-hf-history-conversion-02/conversion.json'
REPORT_SHA = 'e82ccd6a3275114a50712b8cd7f9733c6f9f75a22fe7cae6dce7a150d9f52dac'


def pin(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def check(output):
    if pin(PUBLISHER)['sha256'] != PUBLISHER_SHA or pin(REPORT)['sha256'] != REPORT_SHA:
        raise ValueError('selected publisher or actual root conversion changed')
    module = runpy.run_path(str(PUBLISHER), run_name='read_only_coalescing_library')
    report = json.loads(REPORT.read_bytes())
    if len(report['references']) != 27 or len(report['coalesced_tree_occurrences']) != 27:
        raise ValueError('exact actual 27-root-reference conversion required')
    verified_owner = module['LIB']['owner_bytes'].decode()
    for name in ('audit_history', 'transform'):
        matches = [node for node in ast.parse(verified_owner).body
                   if isinstance(node, ast.FunctionDef) and node.name == name]
        if len(matches) != 1 or module['frozen_function'](name) != ast.get_source_segment(verified_owner, matches[0]) + '\n':
            raise ValueError('AST extraction differs from selected immutable owner bytes')
    transform = module['V4']['transform']
    positive, rejected_mode, rejected_oid = 0, 0, 0
    for row in report['coalesced_tree_occurrences']:
        name, adjacent, mode = row['path'], row['reference_path'], row['mode']
        source = {'mode': mode, 'kind': 'blob', 'oid': row['source_git_blob_oid']}
        reference = {'mode': mode, 'kind': 'blob', 'oid': row['reference_git_blob_oid']}
        unrelated = {'mode': '100644', 'kind': 'blob', 'oid': '1' * 40}
        original = {name: source, adjacent: reference, 'unrelated-source.py': unrelated}
        expected, substitutions = transform(original, report)
        if expected != {adjacent: reference, 'unrelated-source.py': unrelated} or len(substitutions) != 1:
            raise ValueError('exact existing pointer coalescing changed unrelated source')
        if original[name] != source or original[adjacent] != reference:
            raise ValueError('transform mutated input metadata')
        positive += 1
        for kind, changed in (
            ('mode', {**reference, 'mode': '100755' if mode == '100644' else '100644'}),
            ('oid', {**reference, 'oid': '0' * 40}),
        ):
            try:
                transform({**original, adjacent: changed}, report)
            except ValueError as error:
                if str(error) != 'existing HF reference identity differs':
                    raise
            else:
                raise ValueError('different existing pointer accepted')
            if kind == 'mode':
                rejected_mode += 1
            else:
                rejected_oid += 1

    class MetadataOnlyOperations(module['CTX']['GitOperations']):
        def run(self, repository, args, **kwargs):
            if args[0] != 'rev-list' and args != ['cat-file', '--batch']:
                raise ValueError('read-only metadata audit attempted another operation')
            return super().run(repository, args, **kwargs)

    with tempfile.TemporaryDirectory(prefix='publisher-v6-metadata-audit-') as temporary:
        ops = MetadataOnlyOperations(Path(temporary))
        try:
            audit = module['V4']['audit_history'](ops, Path(report['isolated_repository']), report)
            operation_count = ops.count
            if ops.push_attempted:
                raise ValueError('unexpected push attempted')
        finally:
            ops.close()
    if pin(PUBLISHER)['sha256'] != PUBLISHER_SHA or pin(REPORT)['sha256'] != REPORT_SHA:
        raise ValueError('selected source or conversion bytes changed during checks')
    result = {'schema': 'publisher-v6-exact-coalescing-engineering-check/v1',
        'checker_binding': pin(Path(__file__).resolve()), 'publisher_binding': pin(PUBLISHER),
        'actual_conversion_binding': pin(REPORT), 'AST_function_extractions_from_verified_owner_bytes': 2,
        'positive_actual_exact_pointer_cases': positive, 'wrong_existing_pointer_mode_rejections': rejected_mode,
        'wrong_existing_pointer_GitOID_rejections': rejected_oid, 'actual_readonly_history_audit': audit,
        'readonly_Git_operation_count': operation_count,
        'Git_operations_allowed': ['rev-list', 'cat-file --batch'],
        'original_weight_payloads_read': False, 'source_files_or_candidate_edited': False,
        'fetch_executed': False, 'push_executed': False, 'training_executed': False}
    result['content_sha256'] = hashlib.sha256(module['V4']['raw'](result)).hexdigest()
    with output.open('xb') as stream:
        os.chmod(output, 0o600)
        stream.write(module['V4']['raw'](result) + b'\n')
    print(json.dumps({'validation_binding': pin(output), 'checks': result}), flush=True)


if __name__ == '__main__':
    check(BASE / 'canonical_git/publisher-v6-coalescing-validation-01.json')
