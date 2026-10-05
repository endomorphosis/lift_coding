"""Real Git checks for source-preserving child publication links."""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

OWNER = Path(__file__).with_name('update_published_child_gitlinks.py')
SPEC = importlib.util.spec_from_file_location('published_child_owner', OWNER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def command(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL)


def setup(tmp_path):
    repo = tmp_path / 'original'
    repo.mkdir()
    command(repo, 'init', '-q')
    command(repo, 'config', 'user.name', 'Fixture')
    command(repo, 'config', 'user.email', 'fixture@example.invalid')
    command(repo, 'remote', 'add', 'origin', 'https://github.com/endomorphosis/fixture-parent.git')
    (repo / 'source.py').write_text('value = 1\n')
    (repo / 'checkpoint.json.hf.json').write_text('{"fixture_reference": true}\n')
    (repo / '.gitmodules').write_text('[submodule "child"]\n\tpath = child\n\turl = https://github.com/endomorphosis/fixture-child.git\n')
    command(repo, 'add', '.')
    command(repo, 'commit', '-qm', 'initial')
    child_oid = command(repo, 'rev-parse', 'HEAD').decode().strip()
    command(repo, 'update-index', '--add', '--cacheinfo', '160000', child_oid, 'child')
    command(repo, 'commit', '-qm', 'canonical child')
    snapshot = command(repo, 'rev-parse', 'HEAD').decode().strip()
    work = tmp_path / 'private'
    command(repo, 'worktree', 'add', '-qb', 'publication/fixture', str(work), snapshot)
    rows = [{'state': 'deleted', 'path': 'checkpoint.json'}]
    for name, entry in MODULE.tree(repo, snapshot).items():
        if entry['kind'] == 'blob':
            rows.append({'state': 'present', 'path': name, 'mode': entry['mode'], 'git_oid': entry['oid']})
    original_manifest = MODULE.save(tmp_path / 'original-manifest.json', {
        'schema': 'complete-canonical-snapshot-blob-pins/v1',
        'snapshot_commit': snapshot, 'authoritative_source': {'selected_files': rows}})
    converted_manifest = MODULE.save(tmp_path / 'converted-manifest.json', {
        'schema': 'converted-canonical-snapshot-blob-pins/v1', 'mapped_snapshot_commit': snapshot,
        'original_manifest_binding': original_manifest})
    plan = {'canonical_repository': str(repo), 'fresh_worktree': str(work),
            'normalized_origin': 'github.com/endomorphosis/fixture-parent',
            'integration_branch': 'publication/fixture', 'heads': [{'oid': snapshot, 'original_oid': snapshot}],
            'authoritative_full_tree_snapshot': {'snapshot_commit': snapshot, 'manifest_binding': converted_manifest},
            'published_gitlinks': []}
    plan_pin = MODULE.save(tmp_path / 'plan.json', plan)
    prepared = {'schema': 'worktree-main-integration-hf-reference-prepublication/v3',
                'plan_binding': plan_pin, 'fresh_worktree': str(work), 'integrated_tip': snapshot,
                'mapped_prior_integrated_tip': snapshot, 'all_mapped_selected_heads_ancestors': True,
                'original_rewritten_commit_oids_remote_ancestry_claimed': False,
                'published_gitlinks': [], 'python_syntax_errors': []}
    prepared_pin = MODULE.save(tmp_path / 'prepared.json', prepared)
    receipt = {'schema': 'git-integrated-main-publication/v1', 'status': 'published_and_verified',
               'remote_publication_verified': True, 'integrated_tip': snapshot, 'remote_main_after': snapshot,
               'normalized_origin': 'github.com/endomorphosis/fixture-child'}
    receipt_pin = MODULE.save(tmp_path / 'receipt.json', receipt)
    args = SimpleNamespace(plan=Path(plan_pin['path']), plan_sha=plan_pin['sha256'],
                           prepared=Path(prepared_pin['path']), prepared_sha=prepared_pin['sha256'],
                           output=tmp_path / 'updated',
                           published_gitlink=[['child', receipt_pin['path'], receipt_pin['sha256']]])
    return args, repo, work, snapshot, receipt


def test_preserves_blobs_mapped_profile_original_index_and_active_hooks(tmp_path):
    args, repo, work, snapshot, _ = setup(tmp_path)
    index_before = (repo / '.git/index').read_bytes()
    blobs_before = {p: e for p, e in MODULE.tree(work, 'HEAD').items() if e['kind'] == 'blob'}
    marker = tmp_path / 'precommit-ran'
    hook = repo / '.git/hooks/pre-commit'
    hook.write_text('#!/bin/sh\ntouch ' + str(marker) + '\n')
    hook.chmod(0o755)
    MODULE.update(args)
    final = MODULE.tree(work, 'HEAD')
    assert final['child'] == {'mode': '160000', 'kind': 'commit', 'oid': snapshot}
    assert {p: e for p, e in final.items() if e['kind'] == 'blob'} == blobs_before
    assert 'checkpoint.json' not in final
    assert marker.exists()
    assert command(repo, 'rev-parse', 'HEAD').decode().strip() == snapshot
    assert (repo / '.git/index').read_bytes() == index_before
    prepared = json.loads((args.output / 'prepared.json').read_bytes())
    assert prepared['schema'] == 'worktree-main-integration-hf-reference-prepublication/v3'
    assert prepared['all_mapped_selected_heads_ancestors'] is True
    assert prepared['original_rewritten_commit_oids_remote_ancestry_claimed'] is False
    assert 'all_selected_heads_ancestors' not in prepared


def test_rejects_bad_receipt_sha_before_commit(tmp_path):
    args, _, work, snapshot, _ = setup(tmp_path)
    args.published_gitlink[0][2] = '0' * 64
    with pytest.raises(ValueError, match='selected metadata bytes differ'):
        MODULE.update(args)
    assert command(work, 'rev-parse', 'HEAD').decode().strip() == snapshot
    assert not args.output.exists()


def test_rejects_validly_sealed_receipt_for_different_child_origin(tmp_path):
    args, _, work, snapshot, receipt = setup(tmp_path)
    receipt['normalized_origin'] = 'github.com/endomorphosis/different-child'
    pin = MODULE.save(tmp_path / 'wrong-origin.json', receipt)
    args.published_gitlink[0][1:] = [pin['path'], pin['sha256']]
    with pytest.raises(ValueError, match='child origin or canonical Gitlink differs'):
        MODULE.update(args)
    assert command(work, 'rev-parse', 'HEAD').decode().strip() == snapshot


def test_rejects_hook_that_stages_ordinary_source(tmp_path):
    args, repo, _, _, _ = setup(tmp_path)
    hook = repo / '.git/hooks/pre-commit'
    hook.write_text('#!/bin/sh\nprintf "value = 999\\n" > source.py\ngit add source.py\n')
    hook.chmod(0o755)
    with pytest.raises(ValueError, match='hook changed unrelated committed source'):
        MODULE.update(args)
    assert not (args.output / 'prepared.json').exists()
