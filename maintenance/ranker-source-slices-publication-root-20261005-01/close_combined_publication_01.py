"""Write a final cross-publication join after fresh read-only remote checks."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
GIT_COMMIT = 'a6712457a8616c2d22100b3b0cd950986b891e64'
HF_COMMIT = 'fae2e38dc882929edb2bcd2226560f0da3dfcd9e'
EXPECTED = {
    'git_publication': ('maintenance/ranker-source-slices-git-publication-20261005-01/closed.json', '204b5930e3f52bbf27f6a2337a7c6b6e8cb7be10f978bde7fcf29fe7aa4d01b9'),
    'git_independent_input_review': ('maintenance/ranker-source-slices-git-final-input-review-20261005-01/review-receipt.json', '49b746f058bd1c2c1f870120e054479339b86de72f644f7626800088aa6e0635'),
    'hf_publication': ('maintenance/ranker-source-slices-publication-root-20261005-01/hf-publication-01/closed.json', '25893c408afc28cb6f14ee67a335488271c347b7d7c0a5e2153ca1f6a71edef0'),
    'hf_public_readback': ('maintenance/ranker-source-slices-publication-root-20261005-01/hf-public-readback-01.json', '59093213bb8558b7087d9a17a020ddda46b7036e4dee98d1a2dee5581badec66'),
    'hf_ledger_before_git_commit': ('maintenance/ranker-source-slices-publication-root-20261005-01/release-publication-ledger-01.json', '6dabae4b018ff8c803099b47609813c1a4c89e4bc9f7d5147984c4e2ca9711c4'),
    'full_frozen_selection': ('maintenance/ranker-source-slices-publication-20261005-01/final-selection.json', '8f3798da8008ca665e188fe51b45836d8692fca0030f146b90f2c9e9bc2f7264'),
    'qualification': ('qualification/codebase_ir/ranker-source-semantics-20261005-01/qualified-review-01.json', '39c403afd19b5972a28281813c23fdd13eddea1c32fa63747b4dd3258b07e550'),
}


def need(value, message):
    if value is not True:
        raise ValueError(message)


def main():
    producer = ROOT / 'close_release_publication_01.py'
    raw = producer.read_bytes()
    # Reuse only the pinned standard-library stable-read helper, without main.
    need(hashlib.sha256(raw).hexdigest() == 'f9076a9976e1e5703c6c2886217dc95c516c1978773e40abf175680886ce6d00', 'safe stable-read source changed')
    namespace = {'__file__': str(producer), '__name__': 'held_file_only_ledger_helpers'}
    exec(compile(raw, str(producer), 'exec'), namespace)
    read_pin = namespace['read_pin']
    docs, pins = {}, {}
    for name, (relative, expected) in EXPECTED.items():
        held, descriptor = read_pin(WORKSPACE / relative)
        need(descriptor['sha256'] == expected, 'closure input differs: ' + name)
        docs[name], pins[name] = json.loads(held), descriptor
    git_closed, hf_closed = docs['git_publication'], docs['hf_publication']
    need(git_closed['status'] == 'PUBLISHED_AND_VERIFIED' and git_closed['commit'] == GIT_COMMIT and
         git_closed['hf_commit'] == HF_COMMIT and git_closed['full_new_population_remote_Git_blobs_verified'] is True and
         git_closed['all_nine_fresh_parent_gitlinks_preserved'] is True and git_closed['original_root_or_child_HEAD_index_mutations'] == 0 and
         git_closed['new_file_count'] == 210 and git_closed['new_file_bytes'] == 11917434, 'complete actual Git closure differs')
    need(hf_closed['status'] == 'PUBLISHED_AND_VERIFIED' and hf_closed['commit'] == HF_COMMIT and
         hf_closed['remote_readback_verified'] is True and docs['hf_public_readback']['commit'] == HF_COMMIT and
         docs['hf_public_readback']['status'] == 'passed', 'actual HF publication/readback differs')
    population = docs['full_frozen_selection']['files']
    need(len(population) == 336 and sum(row['bytes'] for row in population) == 87119741, 'complete frozen population differs')
    for descriptor in population:
        need(read_pin(Path(descriptor['path']))[1] == {key: descriptor[key] for key in ('path', 'bytes', 'sha256')}, 'frozen source changed')
    observed_git = subprocess.check_output(['git', '-C', str(WORKSPACE), 'ls-remote', 'origin', 'refs/heads/main'], text=True).strip().split()
    need(observed_git == [GIT_COMMIT, 'refs/heads/main'], 'fresh GitHub main advanced')
    url = 'https://huggingface.co/api/datasets/Publicus/codebase-ir-proof-index/revision/main'
    with urllib.request.urlopen(url, timeout=20) as response:
        held = response.read(4 * 1024**2 + 1)
    need(len(held) <= 4 * 1024**2, 'public HF reply exceeded read cap')
    remote_hf = json.loads(held)
    need(remote_hf['id'] == 'Publicus/codebase-ir-proof-index' and remote_hf['sha'] == HF_COMMIT, 'fresh HF main advanced')
    guards = {}
    for role, cwd in (('root', WORKSPACE), ('child', WORKSPACE / 'external/ipfs_accelerate')):
        expected = docs['qualification']['original_checkout_guards'][role]
        head = subprocess.check_output(['git', '-c', 'core.fsmonitor=false', '-C', str(cwd), 'rev-parse', 'HEAD'], text=True).strip()
        index = read_pin(Path(expected['index']['path']))[1]
        need(head == expected['head'] and index == expected['index'], 'original HEAD/index changed')
        guards[role] = {'head': head, 'index': index}
    for name, descriptor in pins.items():
        need(read_pin(Path(descriptor['path']))[1] == descriptor, 'parsed receipt changed: ' + name)
    result = {
        'schema': 'ranker-source-slices-combined-publication-closure@1', 'status': 'PUBLISHED_AND_VERIFIED',
        'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'producer': read_pin(Path(__file__).resolve())[1], 'receipts': pins,
        'github': {'commit': GIT_COMMIT, 'url': 'https://github.com/endomorphosis/lift_coding/commit/' + GIT_COMMIT,
                   'fresh_main_matches': True, 'files': 210, 'bytes': 11917434, 'all_new_remote_blobs_verified': True},
        'huggingface': {'commit': HF_COMMIT, 'url': 'https://huggingface.co/datasets/Publicus/codebase-ir-proof-index/commit/' + HF_COMMIT,
                       'fresh_main_matches': True, 'files': 57, 'bytes': 15799007, 'prior_immutable_files_preserved': 274},
        'full_frozen_population': {'files': 336, 'bytes': 87119741, 'all_pins_unchanged_after_both_publications': True},
        'original_checkout_guards': guards, 'all_nine_fresh_gitlinks_preserved': True,
        'pre_commit_hf_ledger_preserved_as_historical_receipt': True,
        'native_model_prover_test_or_codec_jobs': 0, 'remote_mutations': 0, 'raw_SDK_logs_read': False,
        'proof_authority': False, 'execution_authority': False, 'completion_authority': False, 'planner_activation': False,
        'all32_governing_RPI_exits': 'OPEN', 'full_task_satisfaction': 'unknown', 'official_benchmark_score': None,
    }
    target = ROOT / 'release-publication-closed-01.json'
    with target.open('xb') as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n').encode())
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': result['status'], 'receipt': read_pin(target)[1]}))


if __name__ == '__main__':
    main()
