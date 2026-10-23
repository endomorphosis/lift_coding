"""Check the later parent merge without rerunning qualification or changing Git."""
from __future__ import annotations

import collections
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PHASE = Path(__file__).resolve().parent
ACCEL = Path('/home/barberb/lift_coding/.worktrees/repository-proof-context-20261014')
DATASETS = Path('/home/barberb/lift_coding/.worktrees/repository-proof-context-datasets-20261014')
KIT = Path('/home/barberb/lift_coding/.worktrees/repository-proof-context-kit-20261014')
QUALIFIED = '014fc361c31edce74390f5667948f1706655791f'
BASE = '51774875d8e42deb4d378aa4d9dbf3ec8329969f'
INCOMING = 'c5ab7034b6e923f66cd7661a3f1ae322856d6fb3'
MERGED = '5c3ec38d041d7cc6837840a1275155e73957e9ea'
CHILD = 'b184d30229b3b8f23a390ca24580962d44620536'
DATASETS_PIN = 'b1fd77597867ad31f1687edc8bff090caf3d3b7d'
NOTE = 'implementation_plan/docs/126-supervisor-repository-proof-context-2026-10-14.md'
ACTOR_NOTE = 'implementation_plan/docs/126-legal-actor-refinement-2026-10-14.md'
OUTPUT = PHASE / 'parent-merge-review.json'
sys.dont_write_bytecode = True


def need(value, message):
    if not value:
        raise ValueError(message)


def git(root, *args):
    result = subprocess.run(['git', '--no-optional-locks', *args], cwd=root,
                            capture_output=True, timeout=60)
    need(result.returncode == 0, 'Git observation failed: ' + repr(args))
    return result.stdout


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def state(root):
    return dict(head=git(root, 'rev-parse', 'HEAD').decode().strip(),
                refs_sha256=sha(git(root, 'for-each-ref', '--format=%(refname) %(objectname)')),
                index_sha256=sha(git(root, 'ls-files', '--stage', '-z')))


def tree(root, revision):
    rows = {}
    for row in git(root, 'ls-tree', '-r', '-z', revision).split(b'\0'):
        if row:
            metadata, path = row.split(b'\t', 1)
            need(path not in rows, 'duplicate tree path')
            rows[path] = metadata
    return rows


def binding(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def main():
    need(not OUTPUT.exists(), 'refusing to overwrite merge evidence')
    roots = (ROOT, ACCEL, DATASETS, KIT)
    before = {str(root): state(root) for root in roots}
    need(before[str(ROOT)]['head'] == MERGED, 'actual merge changed')
    parents = git(ROOT, 'rev-parse', MERGED + '^1', MERGED + '^2').decode().splitlines()
    need(parents == [QUALIFIED, INCOMING], 'actual merge parents differ')
    incoming = tree(ROOT, INCOMING)
    merged = tree(ROOT, MERGED)
    changed_gitlink = b'external/ipfs_accelerate'
    need(all(merged.get(path) == metadata for path, metadata in incoming.items()
             if path != changed_gitlink), 'incoming tree object was not preserved')
    pins = {'external/ipfs_accelerate': CHILD, 'external/ipfs_datasets': DATASETS_PIN,
            'external/ipfs_kit': '40c98c71b95be750509ffdb21e7e5494d91b4e79'}
    for path, revision in pins.items():
        need(merged[path.encode()] == ('160000 commit ' + revision).encode(), 'merged dependency pin differs')
        need(git(ROOT, 'rev-parse', ':' + path).decode().strip() == revision, 'staged dependency pin differs')
    original = tree(ROOT, QUALIFIED)
    owned = git(ROOT, 'diff', '--name-only', BASE, QUALIFIED).decode().splitlines()
    need(len(owned) == 7 and all(original[p.encode()] == merged[p.encode()] for p in owned),
         'qualified parent objects changed during merge')
    retained = []
    for path in owned:
        if path == 'external/ipfs_accelerate':
            continue
        raw = git(ROOT, 'show', QUALIFIED + ':' + path)
        need(raw == git(ROOT, 'show', MERGED + ':' + path), 'qualified object changed')
        if path != NOTE:
            need(raw == (ROOT / path).read_bytes(), 'retained receipt changed in working state')
        retained.append(dict(path=path, bytes=len(raw), sha256=sha(raw), revision=QUALIFIED))
    qpath = 'docs/agent_supervisor/evidence/repository-proof-context-20261014/qualification-05/commands.json'
    q = json.loads(git(ACCEL, 'show', CHILD + ':' + qpath))
    need(q['status'] == 'pass' and q['before'] == q['after'], 'selected qualification differs')
    compared = []
    for row in q['before']:
        if row['repository'] == 'datasets_execution_checkout':
            raw = git(DATASETS, 'show', DATASETS_PIN + ':' + row['path'])
            need(len(raw) == row['bytes'] and sha(raw) == row['sha256'], 'listed dataset object changed')
            compared.append(dict(row, preserved_parent_pin=DATASETS_PIN, same_used_object=True))
    need(len(compared) == 51, 'dataset binding population differs')
    need(before[str(ACCEL)]['head'] == CHILD
         and before[str(DATASETS)]['head'] == q['datasets_execution_revision']
         and before[str(KIT)]['head'] == q['kit_execution_revision'], 'execution checkout changed')
    need(all(not git(root, 'status', '--porcelain') for root in roots[1:]), 'execution checkout is dirty')
    incoming_rows = git(ROOT, 'diff', '--name-status', BASE, INCOMING).decode().splitlines()
    need(len(incoming_rows) == 228, 'incoming population differs')
    actor_paths = [ACTOR_NOTE, 'artifacts/legal-actor-refinement-20261014-01/MODEL_CARD_v01.md',
                   'artifacts/legal-actor-refinement-20261014-01/public-result-summary-v01.json']
    actor_objects = []
    for path in actor_paths:
        raw = git(ROOT, 'show', INCOMING + ':' + path)
        need(raw == git(ROOT, 'show', MERGED + ':' + path), 'actor evidence changed')
        actor_objects.append(dict(path=path, bytes=len(raw), sha256=sha(raw), attributed_revision=INCOMING))
    checker_path = ACCEL / 'scripts/docs/check_current_docs_links.py'
    need(sha(checker_path.read_bytes()) == '596a0038b18d592f2e605643890afc85e457558f7b887932a474557d7586819e',
         'pinned documentation checker changed')
    spec = importlib.util.spec_from_file_location('parent_merge_link_checker', checker_path)
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    checker.ROOT = ROOT
    guards = [binding(ROOT / NOTE), binding(Path(__file__))]
    expected_changes = {NOTE, str(Path(__file__).relative_to(ROOT)), str(OUTPUT.relative_to(ROOT))}
    changed = set(git(ROOT, 'diff', '--name-only', 'HEAD').decode().splitlines())
    need(changed <= expected_changes, 'foreign working changes during merge review')
    with OUTPUT.open('x') as handle:
        for note in (NOTE, ACTOR_NOTE):
            need(not checker.check_file(ROOT / note, check_anchors=True), 'parent note links failed')
        after = {str(root): state(root) for root in roots}
        need(before == after and guards == [binding(ROOT / NOTE), binding(Path(__file__))],
             'read guards or Git state changed')
        result = dict(schema='repository-proof-context-parent-merge-review@1', status='pass',
            checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            qualified_parent_leaf=QUALIFIED, original_parent_base=BASE, incoming_parent=INCOMING,
            actual_merge=MERGED, actual_merge_parents=parents,
            incoming_changed_paths=len(incoming_rows),
            incoming_status_counts=dict(collections.Counter(row.split('\t', 1)[0] for row in incoming_rows)),
            all_incoming_tree_objects_preserved_except_owned_accelerator_pin=True,
            incoming_tree_objects_checked=len(incoming)-1, merged_dependency_pins=pins,
            qualified_parent_objects_unchanged_in_merge=owned, retained_qualification_artifacts=retained,
            original_receipts_describe_qualified_parent_leaf=True,
            updated_parent_note_and_checker_bindings=guards,
            selected_qualification='qualification-05', selected_documentation='documentation-checks-04.json',
            retained_tests=187, retained_new_cases=38, retained_suites=5, retained_source_bindings=250,
            dataset_objects_same_at_latest_parent_pin=compared,
            preserved_actor_evidence_objects=actor_objects,
            actor_findings_attributed_to_parallel_session=dict(trained_donor='N11', copied_tensors=42,
                frozen_nonactor_tensors=36, learned_conditions_retained=True, actor_updates=32,
                training_joint_exact_ir='154/168', older_evaluation_joint_exact_ir='53/72',
                newer_evaluation_joint_exact_ir='34/72', fresh_development_exact_ir='0/36',
                fresh_test_exact_ir='0/36', latent_conditioning_enabled=False,
                external_embedding_encoder_executed=False, placeholder_latent_dimension=384,
                checkpoint_sha256='f421514dc02cb3542e7587767191aa99bd32551f145e0af4d01c47595d4d73c4',
                model_manager_registration_established=False, default_decoder_promoted=False,
                hf_release_revision='1622817fd804ff5333fce7dc8d04433e4acef2e4',
                hf_release_files=198, hf_release_bytes=77331365, hf_prior_identities_preserved=5448,
                hf_attributes_correction_documented=True, network_reverified_here=False),
            documentation_notes_checked=[NOTE, ACTOR_NOTE], git_state_before=before, git_state_after=after,
            git_refs_and_index_mutated=False, tests_or_workflow_rerun=False,
            additional_provider_model_training_solver_docker_calls=0,
            learned_latent_decoding_qualified=False, model_manager_registration_qualified=False,
            production_consumer_adoption_qualified=False, proof_authority=False,
            execution_authority=False, completion_authority=False,
            total_session_token_savings_established=False, output_self_excluded=True)
        json.dump(result, handle, sort_keys=True, indent=2)
        handle.write('\n')
    print(json.dumps(dict(status='pass', incoming_paths=228, datasets_bindings=51,
                         retained_tests=187, actual_merge=MERGED)))


if __name__ == '__main__':
    main()
