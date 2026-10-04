"""Publish four root-approved canonical leaves with the exact reviewed publisher."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

OUT = Path(__file__).resolve().parent
PUBLISHER = OUT.parent / 'huggingface/publish_integrated_v3.py'
PUBLISHER_SHA = '0228657ee7390fbfd5d2dc3b97e00eed3e7e3d311eaf54264fe01f7b6ce41d5f'
SELECTION = OUT / 'canonical_leaf_publication_selections_v3.json'
SELECTION_SHA = '4a6a03c77d9b635f2e4fc94b923bfeb57063d883459e4b1476fbe991595df5d3'
RUN = OUT / 'published-01'


def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode() + b'\n'
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def original_state(repo):
    def git(*args, accepted=(0,)):
        result = subprocess.run(['git', '-c', 'gc.auto=0', '-c', 'core.fsmonitor=false',
                                 '-C', str(repo), *args], capture_output=True, timeout=60,
                                env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0'})
        if result.returncode not in accepted:
            raise ValueError('original checkout read-only observation failed')
        return result.stdout.decode().strip()

    index = Path(git('rev-parse', '--git-path', 'index'))
    if not index.is_absolute():
        index = repo / index
    status = git('status', '--porcelain', '--untracked-files=normal')
    return {'head': git('rev-parse', 'HEAD'),
            'branch': git('symbolic-ref', '-q', 'HEAD', accepted=(0, 1)),
            'index_binding': binding(index),
            'status_sha256': hashlib.sha256(status.encode()).hexdigest(),
            'status_lines': len(status.splitlines())}


def main():
    source = PUBLISHER.read_bytes()
    selection_bytes = SELECTION.read_bytes()
    if hashlib.sha256(source).hexdigest() != PUBLISHER_SHA:
        raise ValueError('reviewed publisher differs')
    if hashlib.sha256(selection_bytes).hexdigest() != SELECTION_SHA:
        raise ValueError('root-selected four publication inputs differ')
    selection = json.loads(selection_bytes)
    if {row['name'] for row in selection['repositories']} != {'kit', 'mcp_cpp', 'swissknife', 'hallucinate'}:
        raise ValueError('four explicitly approved leaves required')
    for key in ['GIT_INDEX_FILE', 'GIT_DIR', 'GIT_WORK_TREE']:
        os.environ.pop(key, None)
    for row in selection['repositories']:
        for key in ['plan_binding', 'prepared_binding', 'full_current_tree_binding']:
            if binding(Path(row[key]['path'])) != row[key]:
                raise ValueError('selected publication file differs')
        if Path(row['output_directory']).exists():
            raise ValueError('fresh leaf output required')
    spec = importlib.util.spec_from_file_location('verified_canonical_publisher_v3', PUBLISHER)
    owner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = owner
    exec(compile(source, str(PUBLISHER), 'exec'), owner.__dict__)
    save(RUN / 'canonical_leaf_execution_plan.json', {
        'schema': 'four-canonical-leaf-publication-execution/v1',
        'driver_binding': binding(Path(__file__)), 'publisher_binding': binding(PUBLISHER),
        'selection_binding': binding(SELECTION), 'parallel_repository_limit': 3,
        'verified_publisher_exact_bytes_compiled_before_execution': True,
        'excluded_pending_repositories': ['accelerate', 'datasets', 'root'],
        'normal_main_pushes_authorized': True, 'force_push_authorized': False,
    })

    def publish(row):
        plan = json.loads(Path(row['plan_binding']['path']).read_bytes())
        repo = Path(plan['canonical_repository'])
        before = original_state(repo)
        if binding(PUBLISHER)['sha256'] != PUBLISHER_SHA:
            raise ValueError('publisher changed before publication')
        args = SimpleNamespace(plan=Path(row['plan_binding']['path']), plan_sha=row['plan_binding']['sha256'],
                               prepared=Path(row['prepared_binding']['path']), prepared_sha=row['prepared_binding']['sha256'],
                               output=Path(row['output_directory']), published_gitlink=[])
        code = owner.publish(args)
        path = args.output / 'publication.json'
        report = json.loads(path.read_bytes())
        after = original_state(repo)
        preservation = save(args.output / 'original_checkout_preservation.json', {
            'schema': 'canonical-leaf-publication-preservation/v1',
            'canonical_repository': str(repo), 'original_before': before, 'original_after': after,
            'original_head_index_branch_and_status_preserved': before == after,
            'publisher_binding_unchanged': binding(PUBLISHER)['sha256'] == PUBLISHER_SHA,
            'selected_input_bindings_unchanged': all(binding(Path(row[key]['path'])) == row[key]
                                                    for key in ['plan_binding', 'prepared_binding', 'full_current_tree_binding']),
            'publication_binding': binding(path),
        })
        return {'name': row['name'], 'normalized_origin': row['normalized_origin'],
                'exit_code': code, 'publication_binding': binding(path), 'preservation_binding': preservation,
                'status': report['status'], 'integrated_tip': report.get('integrated_tip'),
                'remote_main_before': report.get('remote_main_before'), 'remote_main_after': report.get('remote_main_after'),
                'remote_publication_verified': report['remote_publication_verified'],
                'original_checkout_preserved': before == after, 'url': report.get('url')}

    rows = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = {pool.submit(publish, row): row for row in selection['repositories']}
        for future in as_completed(pending):
            selected = pending[future]
            try:
                row = future.result()
            except Exception as error:
                row = {'name': selected['name'], 'normalized_origin': selected['normalized_origin'],
                       'status': 'driver_failed_preserve_publication_evidence', 'error_type': type(error).__name__}
            rows.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
    final = save(RUN / 'canonical_leaf_results.json', {
        'schema': 'four-canonical-leaf-publication-results/v1',
        'driver_binding': binding(Path(__file__)), 'publisher_binding': binding(PUBLISHER),
        'selection_binding': binding(SELECTION), 'repositories': sorted(rows, key=lambda row: row['name']),
        'verified_publication_count': sum(row.get('remote_publication_verified') is True for row in rows),
        'all_original_checkout_observations_preserved': all(row.get('original_checkout_preserved') is True for row in rows),
        'force_push_used': False, 'excluded_pending_repositories': ['accelerate', 'datasets', 'root'],
    })
    print(json.dumps({'results_binding': final}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
