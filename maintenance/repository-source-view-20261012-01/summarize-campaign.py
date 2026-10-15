"""Bind final offline evidence to the tested, committed implementation."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


ROOT = Path(__file__).parent
SOURCE = Path('/home/barberb/lift_coding_worktrees/repository-source-view-20261012')
BASE = '4c49239351126303035b0521e9ba71d3bf20e576'


def git(*args):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args], text=True).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    qualification = json.loads((ROOT / 'public-final-02/qualification.json').read_text())
    independent = json.loads((ROOT / 'independent-review.json').read_text())
    stress = json.loads((ROOT / 'stress-final/qualification.json').read_text())
    suites = list(ET.parse(ROOT / 'tests-final.xml').getroot().iter('testsuite'))
    counts = {name: sum(int(suite.get(name, '0')) for suite in suites)
              for name in ('tests', 'failures', 'errors', 'skipped')}
    if (not qualification['qualified'] or not stress['qualified']
            or not independent['independent_recalculation_passed']
            or independent['source_commit'] != git('rev-parse', 'HEAD')
            or independent['qualification_sha256'] != sha(ROOT / 'public-final-02/qualification.json')
            or counts['failures'] or counts['errors'] or counts['skipped']
            or git('status', '--porcelain')):
        raise RuntimeError('final checks must pass against clean source')
    files = git('diff', '--name-only', BASE, 'HEAD').splitlines()
    source_hashes = {name: sha(SOURCE / name) for name in files}
    for name, digest in source_hashes.items():
        committed = subprocess.check_output(['git', '-C', str(SOURCE), 'show', 'HEAD:' + name])
        if hashlib.sha256(committed).hexdigest() != digest:
            raise RuntimeError('source does not match commit')
    rows = []
    for task in qualification['tasks']:
        original = task['protocol']['original']['read_edit_refresh_protocol']
        compact = task['protocol']['compact']['read_edit_refresh_protocol']
        a, b = original['local_tokenizer_proxy_tokens'], compact['local_tokenizer_proxy_tokens']
        rows.append({'task': task['task_name'], 'qualified': task['qualified'],
            'file_count': task['file_count'], 'actual_compact_reads': task['compact_reads'],
            'original_file_bytes': task['original_file_bytes'],
            'compact_file_bytes': task['compact_file_bytes'],
            'host_package_bytes': task['host_storage']['package_bytes'],
            'read_edit_refresh_original_proxy_tokens': a,
            'read_edit_refresh_compact_proxy_tokens': b,
            'proxy_tokens_saved': a - b if a is not None and b is not None else None,
            'proxy_reduction_percent': (a - b) * 100 / a if a else None,
            'original_workflow_json_bytes': original['rendered_json_bytes'],
            'compact_workflow_json_bytes': compact['rendered_json_bytes'],
            'exact_original_restore_after_source_removal': task['checks']['original_tree_byte_mode_exact']
                and task['checks']['original_source_removed_before_restoration'],
            'paired_final_canonical_trees_identical': task['checks']['paired_final_canonical_trees_identical']})
    evidence = ['tests-final.xml', 'tests-final.log', 'public-final-02/qualification.json',
                'stress-final/qualification.json', 'stress-roundtrip.py', 'independent-review.json']
    report = {'schema': 'repository-source-view-campaign-summary@1',
        'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'implemented': ['bounded whole-tree original/compact package',
            'independent exact restoration after source removal',
            'hash-checked immutable revision batches', 'create/verify/list/read/restore/revise CLI'],
        'source': {'path': str(SOURCE), 'base_commit': BASE, 'commit': git('rev-parse', 'HEAD'),
                   'branch': git('branch', '--show-current'), 'clean': True,
                   'changed_file_sha256': source_hashes, 'publication': 'local commit only'},
        'tests': {**counts, 'passed': counts['tests'],
            'seconds': sum(float(suite.get('time', '0')) for suite in suites),
            'scope': 'new engine/revision/CLI/public-harness tests plus existing source-view regressions; final run counted once'},
        'public_tasks': rows, 'original_dataset_unchanged': qualification['original_dataset_unchanged'],
        'authored_behavior_qualified': qualification['authored_behavior']['qualified'],
        'independent_review_passed': True,
        'stress': {'qualified': stress['qualified'], 'files': stress['capture']['file_count'],
            'entries': stress['capture']['entry_count'], 'compacted_files': stress['capture']['compacted_files'],
            'original_tree_exact': stress['original_tree_exact'],
            'compact_files_match_manifest': stress['compact_files_match_manifest'],
            'entry_limit_refused_without_publication': stress['entry_limit_error'] == 'entry_limit'
                and stress['limit_rejection_published_no_package'],
            'capture_seconds': stress['capture_seconds'], 'restore_seconds': stress['restore_seconds'],
            'process_peak_rss_kib': stress['process_peak_rss_kib']},
        'local_tokenizer': qualification['local_tokenizer'],
        'provider_calls': 0, 'containers_started': 0, 'official_reward': None,
        'live_token_savings_established': False, 'automatic_native_tool_routing': False,
        'existing_runtime_defaults_changed': False, 'github_push_performed': False,
        'evidence_sha256': {name: sha(ROOT / name) for name in evidence},
        'limitations': qualification['limitations'] + [
            'V1 snapshot hard caps: 4096 included entries, 64 MiB total and 1 MiB per file.',
            'Git metadata excluded; ownership, timestamps, ACLs and xattrs are outside restoration scope.',
            'Changed compact trees are not automatically reverse-compiled; edits require explicit supported operations.',
            'Source location and revision identities contribute to serialized proxy counts; these are retained measured transcripts.',
            'Storage/read/revision validation is not formal source-equivalence or task acceptance authority.'],
        'next_phase': ['wire task-scoped reads/edits through supervisor-owned tools and measure actual worker adoption',
            'join existing source/symbol/capsule/proof indexes by exact original hashes; refresh after admitted edits',
            'measure source/data selection and repeated conversation context separately from code rendering',
            'qualify repeated live paired trials with complete usage, task success, resource limits and provider backoff']}
    (ROOT / 'summary.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'summary': str(ROOT / 'summary.json'), 'tests_passed': counts['tests'],
                      'public_tasks': rows, 'stress': report['stress'], 'source_commit': report['source']['commit']}))


if __name__ == '__main__':
    main()
