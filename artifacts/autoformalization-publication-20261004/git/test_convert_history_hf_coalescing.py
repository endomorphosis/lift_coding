"""Disposable Git fixtures; no real payloads, credentials or semantic labels."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('hf_coalescing', Path(__file__).with_name('convert_history_hf_coalescing.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = MODULE.owner()


def fixture(tmp_path):
    repository = tmp_path / 'repository'
    repository.mkdir()
    BASE.git(repository, 'init', '-b', 'main')
    BASE.git(repository, 'config', 'user.name', 'Disposable fixture')
    BASE.git(repository, 'config', 'user.email', 'fixture@example.invalid')
    (repository / 'source.py').write_text('value = 1\n')
    BASE.git(repository, 'add', 'source.py')
    BASE.git(repository, 'commit', '-m', 'published fixture')
    return repository, BASE.git(repository, 'rev-parse', 'HEAD').decode().strip()


def commit_file(repository, path, data, message):
    destination = repository / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    BASE.git(repository, 'add', '--', path)
    BASE.git(repository, 'commit', '-m', message)
    return BASE.git(repository, 'rev-parse', 'HEAD').decode().strip()


def reference(repository, path='nested/checkpoint.json', payload=b'selected'):
    oid = BASE.git(repository, 'hash-object', '--stdin', data=payload).decode().strip()
    return {path: {'schema': 'disposable-hf-reference/v1', 'source_git_blob_oid': oid,
                   'sha256': 'f' * 64, 'bytes': len(payload)}}


def state(repository):
    index = repository / '.git/index'
    return (BASE.git(repository, 'for-each-ref'), BASE.git(repository, 'rev-parse', 'HEAD'),
            index.read_bytes(), {str(p.relative_to(repository)): p.read_bytes()
                                 for p in repository.rglob('*') if p.is_file() and '.git' not in p.parts})


def test_small_versions_original_state_and_raw_commit_metadata_preserved(tmp_path):
    repository, published = fixture(tmp_path)
    path = 'nested/checkpoint.json'
    small = commit_file(repository, path, b'small', 'small predecessor')
    selected = commit_file(repository, path, b'selected', 'selected fixture')
    tip = commit_file(repository, 'source.py', b'value = 2\n', 'later source')
    before = state(repository)
    result = MODULE.rewrite_unpublished(repository, tip, [published], reference(repository))
    assert result['commit_map'][small] == small
    assert path not in BASE.tree(repository, result['commit_map'][selected])
    assert path + '.hf.json' in BASE.tree(repository, result['commit_map'][selected])
    old = BASE.git(repository, 'cat-file', 'commit', selected)
    new = BASE.git(repository, 'cat-file', 'commit', result['commit_map'][selected])
    assert old.partition(b'\n\n')[2] == new.partition(b'\n\n')[2]
    assert [line for line in old.splitlines() if line.startswith((b'author ', b'committer '))] == [
        line for line in new.splitlines() if line.startswith((b'author ', b'committer '))]
    assert state(repository) == before
    assert result['coalesced_tree_occurrences'] == []


def test_merge_parents_final_reference_tree_and_published_history_preserved(tmp_path):
    repository, published = fixture(tmp_path)
    left = commit_file(repository, 'nested/checkpoint.json', b'selected', 'left')
    BASE.git(repository, 'checkout', '-b', 'right', published)
    right = commit_file(repository, 'right.py', b'side = True\n', 'right')
    BASE.git(repository, 'checkout', 'main')
    BASE.git(repository, 'merge', '--no-ff', 'right', '-m', 'merge fixture')
    merged = BASE.git(repository, 'rev-parse', 'HEAD').decode().strip()
    refs = reference(repository)
    pointer = BASE.canonical(refs['nested/checkpoint.json']) + b'\n'
    commit_file(repository, 'nested/checkpoint.json.hf.json', pointer, 'exact adjacent reference')
    BASE.git(repository, 'rm', '--', 'nested/checkpoint.json')
    BASE.git(repository, 'commit', '-m', 'remove duplicate raw payload')
    tip = BASE.git(repository, 'rev-parse', 'HEAD').decode().strip()
    before = state(repository)
    result = MODULE.rewrite_unpublished(repository, tip, [published], refs)
    assert BASE.tree(repository, result['tip']) == BASE.tree(repository, tip)
    assert result['commit_map'][right] == right
    mapped_merge = BASE.git(repository, 'cat-file', 'commit', result['commit_map'][merged])
    assert [line[7:].decode() for line in mapped_merge.splitlines() if line.startswith(b'parent ')] == [result['commit_map'][left], right]
    BASE.git(repository, 'merge-base', '--is-ancestor', published, result['tip'])
    assert state(repository) == before


def test_published_raw_coexistence_is_excluded_from_rewrite(tmp_path):
    repository, _ = fixture(tmp_path)
    refs = reference(repository)
    commit_file(repository, 'nested/checkpoint.json', b'selected', 'raw')
    published = commit_file(repository, 'nested/checkpoint.json.hf.json', BASE.canonical(refs['nested/checkpoint.json']) + b'\n', 'published coexistence')
    tip = commit_file(repository, 'source.py', b'value = 2\n', 'later')
    result = MODULE.rewrite_unpublished(repository, tip, [published], refs)
    assert published not in result['commit_map']
    assert len(result['coalesced_tree_occurrences']) == 1
    assert 'nested/checkpoint.json' in BASE.tree(repository, published)
    assert 'nested/checkpoint.json' not in BASE.tree(repository, result['tip'])
    BASE.git(repository, 'merge-base', '--is-ancestor', published, result['tip'])


def test_existing_exact_pointer_coalesces_without_replacing_its_bytes_or_mode(tmp_path):
    repository, published = fixture(tmp_path)
    refs = reference(repository)
    commit_file(repository, 'nested/checkpoint.json', b'selected', 'raw')
    tip = commit_file(repository, 'nested/checkpoint.json.hf.json', BASE.canonical(refs['nested/checkpoint.json']) + b'\n', 'identical coexistence')
    before = state(repository)
    original = BASE.tree(repository, tip)
    result = MODULE.rewrite_unpublished(repository, tip, [published], refs)
    rewritten = BASE.tree(repository, result['tip'])
    assert 'nested/checkpoint.json' not in rewritten
    assert rewritten['nested/checkpoint.json.hf.json'] == original['nested/checkpoint.json.hf.json']
    assert len(result['coalesced_tree_occurrences']) == 1
    row = result['coalesced_tree_occurrences'][0]
    assert row['reference_git_blob_oid'] == original['nested/checkpoint.json.hf.json']['git_oid']
    assert row['mode'] == original['nested/checkpoint.json.hf.json']['mode']
    assert state(repository) == before


@pytest.mark.parametrize('attack', ['different_bytes', 'different_mode'])
def test_existing_wrong_pointer_hash_or_mode_rejects_without_state_changes(tmp_path, attack):
    repository, published = fixture(tmp_path)
    refs = reference(repository)
    commit_file(repository, 'nested/checkpoint.json', b'selected', 'raw')
    path = 'nested/checkpoint.json.hf.json'
    content = b'wrong reference\n' if attack == 'different_bytes' else BASE.canonical(refs['nested/checkpoint.json']) + b'\n'
    tip = commit_file(repository, path, content, 'colliding adjacent')
    if attack == 'different_mode':
        os.chmod(repository / path, 0o755)
        BASE.git(repository, 'add', '--', path)
        BASE.git(repository, 'commit', '-m', 'wrong adjacent mode')
        tip = BASE.git(repository, 'rev-parse', 'HEAD').decode().strip()
    before = state(repository)
    with pytest.raises(ValueError, match='mode or selected Git blob identity'):
        MODULE.rewrite_unpublished(repository, tip, [published], refs)
    assert state(repository) == before
