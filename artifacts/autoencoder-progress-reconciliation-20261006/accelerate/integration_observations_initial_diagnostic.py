#!/usr/bin/env python3
"""Bounded supplemental live/effective-tree comparisons, without owner imports."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

BASE = Path('/home/barberb/lift_coding')
OUT = BASE/'artifacts/autoencoder-progress-reconciliation-20261006/accelerate'
REPO = BASE/'.worktrees/contextual-legal-runtime-accelerate-20261006'
PRIMARY = OUT/'survey.json'
AUDITOR = BASE/'scripts/review_autoencoder_progress.py'


def pin(path):
    path = Path(path); before = path.stat(); raw = path.read_bytes(); after = path.stat()
    shape = lambda s: (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    if shape(before) != shape(after):raise ValueError('changed observed bytes')
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def git(*arguments, cwd=REPO):
    p=subprocess.run(['git','--literal-pathspecs','-C',str(cwd),*arguments],capture_output=True)
    if p.returncode:raise ValueError('read-only Git observation failed')
    return p.stdout


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise ValueError('fresh artifact output required')
    primary_pin=pin(PRIMARY); survey=json.loads(PRIMARY.read_bytes()); target=survey['target_origin_main_commit']
    spec=importlib.util.spec_from_file_location('_effective_tree_observation',AUDITOR)
    audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
    canonical=next(row for row in survey['worktrees'] if row['worktree'].endswith('/.git/modules/external/ipfs_accelerate'))
    live=Path(canonical['worktree']); comparisons=[]
    for entry in canonical.get('dirty_entries',[]):
        name=entry['path']
        if not name.endswith(('.py','.md')) or '/evidence/' in name or not name.startswith(('ipfs_accelerate_py/','benchmarks/','test/','tests/','docs/agent_supervisor/','docs/architecture/')):continue
        path=live/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size>512*1024:continue
        actual=pin(path); current=audit.path_entry(REPO,target,name)
        comparisons.append({'path':name,'working_status':entry['status'],'live_file_pin':actual,'target':current,
            'effective_status':'missing_from_main' if current is None else 'byte_identical_to_main' if
            (actual['bytes'],actual['sha256'])==(current['bytes'],current['sha256']) else 'different_from_main_unreviewed'})
    coding=Path('/home/barberb/lift_coding_worktrees/terminal-planning-schema-20261006')
    active=[]
    if coding.is_dir():
        for name in ('README.md','results.md','roadmap.md','compare_receipts.py','review_completed_pair.py'):
            path=coding/'docs/agent_supervisor/evidence/terminal-context-pair-20261006'/name
            if path.is_file():active.append(pin(path))
    patch_duplicates={}
    for name in ('codex/grok-terminal-diagnostics-20261006','codex/grok-terminal-reporting-20261006'):
        value=git('cherry','-v',target,name).decode().splitlines()
        patch_duplicates[name]={'rows':value,'all_unique_branch_commits_patch_equivalent_to_main':all(row.startswith('- ') for row in value)}
    contract_sources=(
      'benchmarks/agent_supervisor/container_coding/terminal_deployment.py',
      'ipfs_accelerate_py/agent_supervisor/runtime/source384_config.py',
      'ipfs_accelerate_py/agent_supervisor/runtime/task_ir_selection.py',
      'ipfs_accelerate_py/agent_supervisor/runtime/task_ir_checkpoint.py',
      'ipfs_accelerate_py/model_catalog/sources/ir_persistent.py',
      'ipfs_accelerate_py/agent_supervisor/runtime/codebase_autoencoder.py',
      'ipfs_accelerate_py/agent_supervisor/runtime/codebase_autoencoder_index.py',
      'ipfs_accelerate_py/agent_supervisor/proof/ir_registry.py',
      'docs/agent_supervisor/contextual_ir_checkpoint_recovery.md',
    )
    sources={name:audit.path_entry(REPO,target,name) for name in contract_sources}
    search=git('grep','-n','-E','contextual_legal_ir_(runtime|numeric)|prepare_contextual_legal_ir_runtime|open_contextual_legal_ir_autoencoder',target,'--','ipfs_accelerate_py','benchmarks') if False else None
    proc=subprocess.run(['git','-C',str(REPO),'grep','-n','-E',
        'contextual_legal_ir_(runtime|numeric)|prepare_contextual_legal_ir_runtime|open_contextual_legal_ir_autoencoder',
        target,'--','ipfs_accelerate_py','benchmarks'],capture_output=True)
    if proc.returncode not in (0,1):raise ValueError('source callsite observation failed')
    result={'schema':'accelerate-autoencoder-integration-observations/v1','observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'primary_survey_pin':primary_pin,'target_origin_main_commit':target,'current_origin_main_commit':git('rev-parse','origin/main^{commit}').decode().strip(),
        'canonical_live_head':git('rev-parse','HEAD',cwd=live).decode().strip(),'canonical_live_source_comparisons':comparisons,
        'live_comparison_counts':{status:sum(row['effective_status']==status for row in comparisons) for status in
            ('byte_identical_to_main','different_from_main_unreviewed','missing_from_main')},
        'current_separate_terminal_context_pair_files':active,'patch_equivalent_unmerged_branches':patch_duplicates,
        'integration_contract_git_sources':sources,'contextual_runtime_accelerate_callsite_search':{'exit_code':proc.returncode,'matches':proc.stdout.decode().splitlines()},
        'findings':[
          {'status':'published_effective_source','finding':'IRPersistentCatalogSource and exact ten-selector resolve_task_ir_selections preserve family, input/latent role, schema/version, decoder task, profile/format and record identity. Nullable unknowns are retained; no runtime is selected by a bare dimension.'},
          {'status':'published_effective_source','finding':'authenticate_task_ir_checkpoints authenticates original bytes only; optional reviewed task-context@2 cannot convert catalog metadata into numerical ABI, semantic or proof qualification. A store append changes the catalog generation and requires fresh context preparation.'},
          {'status':'published_documentation_not_executable_bridge','finding':'bcd466 contextual LegalIR contribution changes only two documentation files. No accelerate executable callsite currently invokes the new datasets contextual cached decoder. Registration and old native fragment routes remain independent.'},
          {'status':'intentional_historical_pin','finding':'Nested datasets gitlink5cc320f4 was explicitly restored by a370dd5 canonical-submodule-link commit. Preserve historical archives, retained descriptors and sealed contexts; this pointer alone does not choose a deployed decoder.'},
          {'status':'explicit_new_run_selection_available','finding':'build_runtime_archive requires explicit source/datasets/kit checkouts and the CLI requires --datasets. The archive inventories actual selected package bytes and installs source/datasets/kit PYTHONPATH. New studies can select a clean current datasets checkout and regenerate qualified archive/context generations without overwriting historical pins.'},
          {'status':'family_namespace_legacy_bridge','finding':'The public accelerate codebase_autoencoder alias imports datasets formalization.autoencoder.security.codebase_autoencoder. The index namespace is separate and candidate/proof flags stay false; a borrowed Security384 path must not be presented as a native complete Codebase384 decoder.'},
          {'status':'formal_artifact_contract_gap','finding':'IRRegistry requires exact declared artifact family/schema/version envelopes. Contextual private-state schema is a serialization identity, while native decoder schema/profile/format remain null; generated candidates need an explicit independently reviewed artifact contract before proof-index integration.'},
          {'status':'historical_no_go_preserved','finding':'Archived PGIR authority branch remains non-ancestor history. Current final_report documents no-go, zero admitted training repositories and denied descendant execution; do not reactivate old task completion flags as a new admitted campaign.'},
          {'status':'active_unqualified_documentation','finding':'The separate terminal-context-pair worktree has five untracked evidence/roadmap files: baseline reward1, compact reward0 with response-envelope rejection, greater total tokens and no qualified saving claim. These are active retained findings, not autoencoder training evidence or merge approval.'},
        ],
        'operations':{'model_loaded':False,'training_executed':False,'database_opened':False,'huggingface_updated':False,'repository_source_or_index_modified':False},
        'script_pin':pin(Path(__file__).resolve())}
    if pin(PRIMARY)!=primary_pin:raise ValueError('primary survey changed')
    with args.output.open('x') as handle:json.dump(result,handle,indent=2,sort_keys=True);handle.write('\n')
    print(json.dumps({'output':pin(args.output),'live_counts':result['live_comparison_counts'],'contextual_callsites':len(proc.stdout.decode().splitlines())}))


if __name__=='__main__':main()
