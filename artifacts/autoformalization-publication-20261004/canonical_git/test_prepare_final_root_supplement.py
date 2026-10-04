"""Disposable Git check for explicit final overlays and advanced-main recovery."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

PATH = Path(__file__).with_name('prepare_final_root_supplement.py')
SPEC = importlib.util.spec_from_file_location('final_supplement', PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL)


def test_advanced_main_exact_overlays_unselected_source_and_eight_links(tmp_path):
    lib = MODULE.checked_owner(MODULE.LIBRARY, MODULE.LIBRARY_SHA, 'fixture_lib')
    root = tmp_path / 'original'
    root.mkdir()
    git(root, 'init', '-qb', 'main')
    git(root, 'config', 'user.name', 'Fixture')
    git(root, 'config', 'user.email', 'fixture@example.invalid')
    git(root, 'remote', 'add', 'origin', 'https://github.com/endomorphosis/lift_coding.git')
    (root / '.gitignore').write_text('# fixture\n')
    (root / 'unselected.py').write_text('value = 1\n')
    selected_path = 'implementation_plan/docs/result.md'
    (root / selected_path).parent.mkdir(parents=True)
    (root / selected_path).write_text('old result\n')
    (root / 'checkpoint.json.hf.json').write_text('{"fixture_reference":true}\n')
    git(root, 'add', '.')
    git(root, 'commit', '-qm', 'initial')
    child_oid = git(root, 'rev-parse', 'HEAD').decode().strip()
    children = ['Mcp-Plus-Plus', 'external/ipfs_accelerate', 'external/ipfs_datasets',
                'external/ipfs_kit', 'hallucinate_app', 'swissknife', 'foreign1', 'foreign2']
    (root / '.gitmodules').write_text(''.join('[submodule "' + p + '"]\n\tpath = ' + p
        + '\n\turl = https://github.com/endomorphosis/fixture-child.git\n' for p in children))
    git(root, 'add', '.gitmodules')
    for child in children:
        git(root, 'update-index', '--add', '--cacheinfo', '160000', child_oid, child)
    git(root, 'commit', '-qm', 'published canonical links')
    base = git(root, 'rev-parse', 'HEAD').decode().strip()
    remote = tmp_path / 'remote.git'
    subprocess.check_call(['git', 'clone', '--bare', '-q', str(root), str(remote)])
    git(root, 'config', 'url.' + str(remote) + '.insteadOf', 'https://github.com/endomorphosis/lift_coding.git')
    actor = tmp_path / 'actor'
    subprocess.check_call(['git', 'clone', '-q', str(remote), str(actor)])
    git(actor, 'config', 'user.name', 'Fixture')
    git(actor, 'config', 'user.email', 'fixture@example.invalid')
    (actor / 'unselected.py').write_text('value = 999\n')
    (actor / 'advanced-main.md').write_text('unique advanced baseline addition\n')
    git(actor, 'add', '.')
    git(actor, 'commit', '-qm', 'main advanced')
    advanced = git(actor, 'rev-parse', 'HEAD').decode().strip()
    git(actor, 'push', '-q', 'origin', 'main')  # Disposable local bare remote only.
    canonical = lib['tree'](root, base)
    source_rows = []
    for name, row in canonical.items():
        if row['kind'] == 'blob':
            data = git(root, 'cat-file', 'blob', row['oid'])
            source_rows.append({'state': 'present', 'path': name, 'mode': row['mode'], 'git_oid': row['oid'],
                               'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    source_rows.append({'state': 'deleted', 'path': 'checkpoint.json'})
    full = lib['save'](tmp_path / 'old-full.json', {'schema': 'complete-canonical-snapshot-blob-pins/v1',
        'snapshot_commit': base, 'authoritative_source': {'snapshot_commit': base, 'selected_files': source_rows}})
    links = [{'path': child, 'oid': child_oid} for child in children[:6]]
    plan = {'canonical_repository': str(root), 'normalized_origin': 'github.com/endomorphosis/lift_coding',
            'fresh_worktree': str(root), 'integration_branch': 'main', 'origin_main_sha256_or_git_oid': base,
            'authoritative_source': {'snapshot_commit': base, 'selected_files': []},
            'authoritative_full_tree_snapshot': {'snapshot_commit': base, 'manifest_binding': full},
            'published_gitlinks': links, 'heads': [{'oid': base, 'kind': 'canonical_current_source'}]}
    plan_pin = lib['save'](tmp_path / 'old-plan.json', plan)
    prepared_pin = lib['save'](tmp_path / 'old-prepared.json', {'integrated_tip': base, 'fresh_worktree': str(root)})
    pub = lib['save'](tmp_path / 'publication.json', {'schema': 'git-integrated-main-publication/v1',
        'status': 'published_and_verified', 'remote_publication_verified': True,
        'normalized_origin': plan['normalized_origin'], 'integrated_tip': base, 'remote_main_after': base,
        'canonical_repository': str(root), 'plan_binding': plan_pin, 'prepared_binding': prepared_pin})
    (root / selected_path).write_text('exact new result\n')
    data = (root / selected_path).read_bytes()
    selector = lib['save'](tmp_path / 'selection.json', {'schema': 'final-root-source-supplement-selection/v1',
        'canonical_repository': str(root), 'source_publication_binding': pub,
        'selected_files': [{'path': selected_path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'mode': '100644'}],
        'commit_message': 'Selected final metadata'})
    index_before = (root / '.git/index').read_bytes()
    marker = tmp_path / 'hooks-ran'
    hook = root / '.git/hooks/pre-commit'
    hook.write_text('#!/bin/sh\ntouch ' + str(marker) + '\n')
    hook.chmod(0o755)
    output = tmp_path / 'prepared'
    MODULE.prepare(SimpleNamespace(selection=Path(selector['path']), selection_sha=selector['sha256'],
                                   output=output, branch='publication/fixture-final'))
    result = json.loads((output / 'plan.json').read_bytes())
    work = Path(result['fresh_worktree'])
    tip = git(work, 'rev-parse', 'HEAD').decode().strip()
    assert result['origin_main_sha256_or_git_oid'] == advanced
    assert (work / selected_path).read_bytes() == data
    assert (work / 'unselected.py').read_text() == 'value = 1\n'
    assert (work / 'advanced-main.md').read_text() == 'unique advanced baseline addition\n'
    assert all(lib['tree'](work, tip)[name] == canonical[name] for name in children)
    assert 'checkpoint.json' not in lib['tree'](work, tip)
    assert marker.exists()
    assert git(root, 'rev-parse', 'HEAD').decode().strip() == base
    assert (root / '.git/index').read_bytes() == index_before
    assert (root / selected_path).read_bytes() == data
    assert result['published_gitlinks'] == links
    git(work, 'merge-base', '--is-ancestor', base, tip)
    git(work, 'merge-base', '--is-ancestor', advanced, tip)


@pytest.mark.parametrize('name,data', [
    ('artifacts/autoformalization-publication-20261004/training/run-01/arm/training-report.json', b'{}'),
    ('artifacts/autoformalization-publication-20261004/huggingface/source-reconstruction-aes-v1/card.md', b'card'),
    ('artifacts/autoformalization-publication-20261004/training/run-01/arm/model.safetensors', b'weights'),
    ('artifacts/autoformalization-publication-20261004/numeric.json', b'{"weights":[1.2]}'),
])
def test_rejects_training_weight_staging_and_vector_payloads(name, data):
    with pytest.raises(ValueError):
        MODULE.eligible(name, data)


def test_rejects_nested_vectors_and_model_state_but_allows_scalar_counts_and_config_statistics():
    name = 'artifacts/autoformalization-publication-20261004/compact.json'
    for value in ({'schema': 'alignment-lane-bundle/v1', 'rows': [{'vector': [1.0, 2.0]}]},
                  {'rows': [{'vector': [1.0, 2.0]}]},
                  {'arms': [{'latent_vectors': [[1.0, 2.0]]}]},
                  {'arms': [{'model_state': {'layer.weight': [1.0, 2.0]}}]}):
        with pytest.raises(ValueError):
            MODULE.eligible(name, json.dumps(value).encode())
    MODULE.eligible(name, json.dumps({'training_rows': 16, 'normalization': {'coordinate_mean': [0.1, 0.2],
                        'global_rms': 0.7}, 'profile': {'source_vector_dimension': 768}}).encode())
