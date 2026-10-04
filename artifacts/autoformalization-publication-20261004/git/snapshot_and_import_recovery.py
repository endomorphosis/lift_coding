"""Recover exact history refs, then snapshot source with submodule recursion off."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent
HELPER = OUT / 'snapshot_and_import.py'
HELPER_SHA = '8d41b21e88c562a8705a2ff6bdf05b4ccf0bd43f2c3913d35db32699b0fcf698'
PRIOR = OUT / 'snapshot-import-01'
RUN = OUT / 'snapshot-import-recovery-01'


class UnsupportedPlaceholder(ValueError):
    """All-zero worktree HEAD identifies no commit to import."""


def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def load_verified_helper():
    data = HELPER.read_bytes()
    if hashlib.sha256(data).hexdigest() != HELPER_SHA:
        raise ValueError('frozen first helper differs before execution')
    spec = importlib.util.spec_from_file_location('verified_snapshot_import_helper', HELPER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    exec(compile(data, str(HELPER), 'exec'), module.__dict__)
    return module


def main():
    module = load_verified_helper()
    prior_bindings = [binding(path) for path in sorted(PRIOR.rglob('*')) if path.is_file()]
    provenance = {
        'schema': 'source-snapshot-import-recovery-provenance/v1', 'created_utc': datetime.now(UTC).isoformat(),
        'first_helper_binding': binding(HELPER), 'recovery_helper_binding': binding(Path(__file__)),
        'interrupted_attempt_bindings': prior_bindings, 'interrupted_helper_exit_code': 130,
        'interruption_reason': 'configured_implicit_submodule_recursion_disabled_for_recovery',
        'first_attempt_success_import_receipt_count': len(list((PRIOR / 'imports').glob('*.json'))),
        'first_attempt_failure_receipt_count': len(list((PRIOR / 'failures').glob('*.json'))),
        'first_attempt_source_snapshot_count': len(list((PRIOR / 'snapshots').glob('*.json'))),
        'first_attempt_source_commit_count': len(list((PRIOR / 'created-source-commits').glob('*.json'))),
        'implicit_submodule_fetch_attempted_in_first_attempt': True,
        'recursive_fetch_effects_on_cached_remote_refs_not_fully_attributed': True,
        'first_attempt_main_merge_or_origin_push': False,
        'recovery_submodule_recursion': False, 'recovery_automatic_gc': False,
        'existing_matching_publication_refs_verified_without_overwrite': True,
        'zero_head_status': 'unsupported_unborn_registration_not_a_commit_lineage',
    }
    module.save(OUT / 'snapshot_import_recovery_provenance.json', provenance)
    original_git = module.git

    def no_gc_git(path, *args, **kwargs):
        return original_git(path, '-c', 'gc.auto=0', *args, **kwargs)

    module.git = no_gc_git

    def exact_nonrecursive_fetch(target, source_common, commit, ref):
        if commit and set(commit) == {'0'}:
            raise UnsupportedPlaceholder('all-zero detached registration names no commit')
        existing = module.text_git(target, 'rev-parse', '--verify', ref, allowed=(0, 128))
        if existing and existing != commit:
            raise ValueError('existing publication ref selects another commit')
        if not existing:
            module.git(target, 'fetch', '--recurse-submodules=no', '--no-tags', '--no-write-fetch-head',
                       '--no-auto-maintenance', str(source_common), commit + ':' + ref)
        if module.text_git(target, 'rev-parse', '--verify', ref) != commit:
            raise ValueError('exact imported ref differs')
        module.text_git(target, 'cat-file', '-e', commit + '^{commit}')
        return {'target_worktree': str(target), 'source_common_dir': str(source_common), 'commit': commit,
                'ref': ref, 'commit_verified': True, 'force_used': False, 'origin_push_performed': False,
                'submodule_recursion': False, 'automatic_gc': False,
                'operation': 'verified_existing_exact_publication_ref' if existing else 'nonrecursive_local_history_import'}

    module.fetch_ref = exact_nonrecursive_fetch
    module.RUN = RUN
    module.main()
    for selected in prior_bindings:
        if binding(Path(selected['path'])) != selected:
            raise ValueError('interrupted attempt evidence changed')
    results = json.loads((RUN / 'results.json').read_bytes())
    failures = [json.loads(Path(item['path']).read_bytes()) for item in results['failure_receipt_bindings']]
    summary = {
        'schema': 'source-snapshot-import-recovery-summary/v1', 'results_binding': binding(RUN / 'results.json'),
        'interrupted_attempt_bindings_preserved': True,
        'verified_or_imported_history_heads': len(results['history_import_receipt_bindings']),
        'unsupported_zero_head_count': sum(item['error_type'] == 'UnsupportedPlaceholder' for item in failures),
        'genuine_failure_count': sum(item['error_type'] != 'UnsupportedPlaceholder' for item in failures),
        'snapshot_receipt_count': len(results['snapshot_receipt_bindings']),
        'main_merge_performed': False, 'origin_push_performed': False,
    }
    selected = module.save(RUN / 'recovery_summary.json', summary)
    print(json.dumps({'recovery_summary_binding': selected, **summary}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
