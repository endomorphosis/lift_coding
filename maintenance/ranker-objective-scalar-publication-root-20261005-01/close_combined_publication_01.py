"""Join independently pinned publication evidence after fresh remote reads."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent
WORKSPACE = Path('/home/barberb/lift_coding')


def main():
    # The helper source is read with a bounded buffer, pinned through the CLI
    # plan, and executed only for its standard-library stable-read functions.
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    if not __debug__ or re.fullmatch('[0-9a-f]{64}', args.plan_sha256) is None:
        raise ValueError('unoptimized externally pinned closure plan required')
    with args.plan.open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != args.plan_sha256:
        raise ValueError('bounded external closure plan pin differs')
    plan = json.loads(raw)
    if set(plan) != {'schema', 'helper_source', 'git_commit', 'hf_commit', 'git_files', 'git_bytes', 'selected_files', 'selected_bytes', 'receipts'} or plan['schema'] != 'ranker-objective-scalar-combined-publication-plan@1':
        raise ValueError('closed combined plan required')
    source = ROOT / 'close_release_publication_01.py'
    with source.open('rb') as stream:
        helper = stream.read(262145)
    expected = {'path': str(source), 'bytes': len(helper), 'sha256': hashlib.sha256(helper).hexdigest()}
    if len(helper) > 262144 or expected != plan['helper_source']:
        raise ValueError('externally pinned helper differs')
    namespace = {'__file__': str(source), '__name__': 'held_objective_scalar_file_only_helpers'}
    exec(compile(helper, str(source), 'exec'), namespace)
    need, read_pin, document, save = [namespace[name] for name in ('need', 'read_pin', 'document', 'save')]
    need(read_pin(source)[1] == expected, 'helper file changed')
    plan_pin = read_pin(args.plan)[1]
    need(plan_pin['sha256'] == args.plan_sha256, 'stable closure plan differs')
    git_commit, hf_commit = plan['git_commit'], plan['hf_commit']
    need(all(type(value) is str and re.fullmatch('[0-9a-f]{40}', value) is not None for value in (git_commit, hf_commit)), 'actual commit ids required')
    for key in ('git_files', 'git_bytes', 'selected_files', 'selected_bytes'):
        need(type(plan[key]) is int and 0 < plan[key] <= (10000 if key.endswith('files') else 256 * 1024**2), 'bounded exact population counts required')
    pins = plan['receipts']
    need(set(pins) == {'git_publication', 'git_independent_input_review', 'hf_publication', 'hf_public_readback', 'hf_ledger_before_git_commit', 'full_frozen_selection', 'qualification'}, 'complete actual closure receipt set')
    docs = {name: document(row) for name, row in pins.items()}
    git, hf, public, ledger, q = [docs[key] for key in ('git_publication', 'hf_publication', 'hf_public_readback', 'hf_ledger_before_git_commit', 'qualification')]
    need(git['status'] == 'PUBLISHED_AND_VERIFIED' and git['commit'] == git_commit and git['hf_commit'] == hf_commit and git['full_new_population_remote_Git_blobs_verified'] is True and git['all_nine_fresh_parent_gitlinks_preserved'] is True and git['original_root_or_child_HEAD_index_mutations'] == 0 and git['new_file_count'] == plan['git_files'] and git['new_file_bytes'] == plan['git_bytes'] and git['remote_main'] == git_commit and git['tree'] == git['remote_tree'], 'complete Git closure differs')
    need(git['commit_calls'] == git['push_calls'] == 1 and git['force_push_calls'] == git['concurrency_rebases'] == 0 and git['parent_gitlinks'] == git['commit_gitlinks'] and len(git['commit_gitlinks']) == 9, 'normal publication and fresh gitlink joins differ')
    peer = docs['git_independent_input_review']
    need(peer['schema'] == 'ranker-objective-scalar-independent-final-Git-input-review@1' and peer['status'] == 'passed_file_only_actual_HF_gate_and_exact_compact_selection' and peer['findings'] == [] and git['final_stage'] in peer['reviewed_input_pins'] and all(pins[key] in peer['reviewed_input_pins'] for key in ('hf_publication', 'hf_public_readback', 'hf_ledger_before_git_commit')), 'Git final input review/stage/HF joins failed')
    need(hf['status'] == 'PUBLISHED_AND_VERIFIED' and hf['commit'] == hf_commit and hf['remote_readback_verified'] is True and public['commit'] == hf_commit and public['status'] == 'passed' and ledger['status'] == 'HF_PUBLISHED_AND_VERIFIED_GITHUB_PUBLICATION_PENDING' and ledger['huggingface']['commit'] == hf_commit and ledger['input_receipts']['hf_closed'] == pins['hf_publication'] and ledger['input_receipts']['public_readback'] == pins['hf_public_readback'], 'HF/ledger/readback joins differ')
    need(q['status'] == 'passed' and q['qualified_theorem_queries'] == 14 and q['metadata_payloads'] == 4458 and ledger['input_receipts']['qualification'] == pins['qualification'], 'qualified scope join differs')
    frozen = document(ledger['input_receipts']['frozen_inputs'])
    need(frozen['schema'] == 'ranker-objective-scalar-publication-closed-inputs@1' and frozen['final_selection'] == pins['full_frozen_selection'], 'ledger binds this complete frozen selection')
    need(hf['parent'] == public['parent'] == ledger['huggingface']['parent'] == 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e' and hf['files'] == public['selected_files'] == ledger['huggingface']['selected_files'] and hf['selected_bytes'] == public['selected_bytes'] == ledger['huggingface']['selected_bytes'] and hf['prior_immutable_remote_files_preserved'] == public['prior_immutable_files_preserved'] == 329, 'actual HF parent/population/preservation joins differ')
    need(peer['actual_HF_commit'] == hf_commit and peer['combined_selected_files'] == plan['git_files'] and peer['combined_selected_bytes'] == plan['git_bytes'], 'Git peer reviewed actual population differs')
    population = docs['full_frozen_selection']['files']
    need(len(population) == plan['selected_files'] and sum(row['bytes'] for row in population) == plan['selected_bytes'] and len({row['path'] for row in population}) == len(population), 'full selected census differs')
    for row in population:
        need(read_pin(row['path'])[1] == {key: row[key] for key in ('path', 'bytes', 'sha256')}, 'selected source changed')
    observed = subprocess.check_output(['git', '-C', str(WORKSPACE), 'ls-remote', 'origin', 'refs/heads/main'], text=True, timeout=30).strip().split()
    need(observed == [git_commit, 'refs/heads/main'], 'fresh GitHub main differs')
    with urllib.request.urlopen('https://huggingface.co/api/datasets/Publicus/codebase-ir-proof-index/revision/main', timeout=30) as response:
        remote = response.read(4 * 1024**2 + 1)
    need(len(remote) <= 4 * 1024**2, 'public HF response exceeds bound')
    remote = json.loads(remote)
    need(remote['id'] == 'Publicus/codebase-ir-proof-index' and remote['sha'] == hf_commit, 'fresh HF main differs')
    guards = {}
    for role, cwd in (('root', WORKSPACE), ('child', WORKSPACE / 'external/ipfs_accelerate')):
        wanted = q['original_checkout_guards'][role]
        head = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-C', str(cwd), 'rev-parse', 'HEAD'], text=True, timeout=30).strip()
        index = read_pin(wanted['index']['path'])[1]
        need(head == wanted['head'] and index == wanted['index'], 'original checkout changed')
        guards[role] = {'head': head, 'index': index}
    need(all(read_pin(row['path'])[1] == row for row in list(namespace['HELD'].values())), 'held inputs changed after remote checks')
    result = {'schema': 'ranker-objective-scalar-combined-publication-closure@1', 'status': 'PUBLISHED_AND_VERIFIED', 'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'producer': read_pin(Path(__file__).resolve())[1], 'plan': plan_pin, 'receipts': pins,
        'github': {'commit': git_commit, 'url': 'https://github.com/endomorphosis/lift_coding/commit/' + git_commit, 'fresh_main_matches': True, 'files': plan['git_files'], 'bytes': plan['git_bytes'], 'all_new_remote_blobs_verified': True},
        'huggingface': {'commit': hf_commit, 'url': 'https://huggingface.co/datasets/Publicus/codebase-ir-proof-index/commit/' + hf_commit, 'fresh_main_matches': True, 'files': hf['files'], 'bytes': hf['selected_bytes'], 'prior_immutable_files_preserved': 329},
        'full_frozen_population': {'files': plan['selected_files'], 'bytes': plan['selected_bytes'], 'all_pins_unchanged_after_both_publications': True}, 'original_checkout_guards': guards, 'all_nine_fresh_gitlinks_preserved': True, 'pre_commit_hf_ledger_preserved_as_historical_receipt': True,
        'native_model_prover_test_or_codec_jobs': 0, 'remote_mutations': 0, 'raw_SDK_logs_read': False, 'all32_governing_RPI_exits': 'OPEN', 'full_task_satisfaction': 'unknown', 'official_benchmark_score': None, **namespace['AUTHORITY']}
    print(json.dumps({'status': result['status'], 'receipt': save(ROOT / 'release-publication-closed-01.json', result)}))


if __name__ == '__main__':
    main()
