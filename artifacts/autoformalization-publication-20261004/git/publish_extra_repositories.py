"""Publish nine externally selected, reviewed extra-repository integrations."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import SimpleNamespace

OUT = Path(__file__).resolve().parent
PUBLISHER = OUT.parent / 'huggingface/publish_integrated_v2.py'
PUBLISHER_SHA = 'b770d67839d76c1970d6bc36cf9a3c7a0cca93308af37bc6fe9295fcdbe837c8'
SELECTION = OUT / 'extra_publication_selections_v2.json'
SELECTION_SHA = 'e68d1f74d5d01767963bd4fb749f0230cd04524794490f9db604a70c6cbcb366'
RUN = OUT / 'published-01'


def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode() + b'\n'
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def main():
    source = PUBLISHER.read_bytes()
    selected_bytes = SELECTION.read_bytes()
    if hashlib.sha256(source).hexdigest() != PUBLISHER_SHA:
        raise ValueError('reviewed publisher bytes differ')
    if hashlib.sha256(selected_bytes).hexdigest() != SELECTION_SHA:
        raise ValueError('root-approved nine publication selections differ')
    selection = json.loads(selected_bytes)
    if selection['repository_count'] != 9 or len(selection['repositories']) != 9:
        raise ValueError('nine selected repositories required')
    for row in selection['repositories']:
        for key in ['plan_binding', 'prepared_binding', 'full_current_tree_binding']:
            if binding(Path(row[key]['path'])) != row[key]:
                raise ValueError('selected publication input differs')
        if Path(row['output_directory']).exists():
            raise ValueError('fresh per-repository output required')
    for key in ['GIT_INDEX_FILE', 'GIT_DIR', 'GIT_WORK_TREE']:
        os.environ.pop(key, None)
    spec = importlib.util.spec_from_file_location('verified_extra_publisher_v2', PUBLISHER)
    owner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = owner
    exec(compile(source, str(PUBLISHER), 'exec'), owner.__dict__)
    RUN.mkdir(mode=0o700)
    save(RUN / 'execution_plan.json', {
        'schema': 'nine-extra-publication-execution/v1',
        'driver_binding': binding(Path(__file__)), 'publisher_binding': binding(PUBLISHER),
        'selection_binding': binding(SELECTION), 'parallel_repository_limit': 3,
        'reviewed_publisher_exact_bytes_compiled_before_execution': True,
        'push_scope': 'nine selected owned origins; ordinary selectedtip:refs/heads/main',
        'canonical_seven_repositories_not_published_by_this_driver': True,
        'force_push_authorized': False,
    })

    def publish(row):
        if binding(PUBLISHER)['sha256'] != PUBLISHER_SHA:
            raise ValueError('reviewed publisher changed before publication')
        args = SimpleNamespace(
            plan=Path(row['plan_binding']['path']), plan_sha=row['plan_binding']['sha256'],
            prepared=Path(row['prepared_binding']['path']), prepared_sha=row['prepared_binding']['sha256'],
            output=Path(row['output_directory']), published_gitlink=[],
        )
        code = owner.publish(args)
        report_path = args.output / 'publication.json'
        report = json.loads(report_path.read_bytes())
        if binding(PUBLISHER)['sha256'] != PUBLISHER_SHA:
            raise ValueError('reviewed publisher changed after publication')
        return {
            'normalized_origin': row['normalized_origin'], 'exit_code': code,
            'publication_binding': binding(report_path), 'status': report['status'],
            'integrated_tip': report.get('integrated_tip'), 'remote_main_before': report.get('remote_main_before'),
            'remote_main_after': report.get('remote_main_after'),
            'remote_publication_verified': report['remote_publication_verified'],
            'push_attempted': report['push_attempted'], 'url': report.get('url'),
            'remote_main_changed': report.get('remote_main_before') != report.get('remote_main_after'),
        }

    rows = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = {pool.submit(publish, row): row for row in selection['repositories']}
        for future in as_completed(pending):
            selected = pending[future]
            try:
                row = future.result()
            except Exception as error:
                row = {'normalized_origin': selected['normalized_origin'],
                       'status': 'driver_failed_preserve_per_repository_evidence',
                       'error_type': type(error).__name__}
            rows.append(row)
            print(json.dumps(row, sort_keys=True), flush=True)
    if binding(SELECTION)['sha256'] != SELECTION_SHA:
        raise ValueError('root-approved selection changed after publication')
    final = save(RUN / 'results.json', {
        'schema': 'nine-extra-publication-results/v1',
        'publisher_binding': binding(PUBLISHER), 'driver_binding': binding(Path(__file__)),
        'selection_binding': binding(SELECTION), 'repositories': sorted(rows, key=lambda row: row['normalized_origin']),
        'verified_publication_count': sum(row.get('remote_publication_verified') is True for row in rows),
        'remote_main_updated_count': sum(row.get('remote_publication_verified') is True
                                        and row.get('remote_main_changed') is True for row in rows),
        'force_push_used': False, 'canonical_seven_repositories_touched_by_driver': False,
    })
    print(json.dumps({'results_binding': final}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
