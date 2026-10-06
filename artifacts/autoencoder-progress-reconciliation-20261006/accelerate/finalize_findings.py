#!/usr/bin/env python3
"""Close read-only findings from retained snapshots and current publication bytes."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

OUT=Path('/home/barberb/lift_coding/artifacts/autoencoder-progress-reconciliation-20261006/accelerate')
REPO=Path('/home/barberb/lift_coding/.worktrees/contextual-legal-runtime-accelerate-20261006')


def pin(path):
    path=Path(path);raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def git(*args):
    return subprocess.check_output(['git','-C',str(REPO),*args],stderr=subprocess.PIPE)


def main():
    primary=json.loads((OUT/'survey.json').read_bytes())
    supplement=json.loads((OUT/'integration-observations-v2.json').read_bytes())
    target=git('rev-parse','origin/main^{commit}').decode().strip()
    pair=[]
    for old in supplement['current_separate_terminal_context_pair_files']:
        relative='docs/agent_supervisor/evidence/terminal-context-pair-20261006/'+Path(old['path']).name
        raw=git('show',target+':'+relative)
        pair.append({'path':relative,'main_bytes':len(raw),'main_sha256':hashlib.sha256(raw).hexdigest(),
                     'matches_observed_worktree_bytes':(len(raw),hashlib.sha256(raw).hexdigest())==(old['bytes'],old['sha256'])})
    result={'schema':'accelerate-autoencoder-reconciliation-findings/v1','observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'primary_snapshot_pin':pin(OUT/'survey.json'),'supplement_pin':pin(OUT/'integration-observations-v2.json'),
        'target_origin_main_commit':target,'primary_origin_main_commit':primary['target_origin_main_commit'],
        'published_terminal_context_pair_paths':pair,'terminal_context_pair_is_published':all(row['matches_observed_worktree_bytes'] for row in pair),
        'source_snapshot_scope':'Primary refs/worktrees captured at e3a; later d5c59e96 is a documentation-only publication. Preserve both generations.',
        'effective_tree_scope':'Fourteen bounded selected branch reviews found zero missing sampled files; broad older branches capped at128. This is not an exhaustive recovery qualification.',
        'canonical_live_dirty_source_counts':supplement['live_comparison_counts'],
        'safe_unmerged_autoencoder_candidate_identified':False,
        'candidate_scope':'The39 absent live Python/Markdown files and94 different files are uncommitted or later divergent candidates needing source/evidence review. The482 equal files are already published bytes. Grok non-ancestor commits are patch-equivalent; historical PGIR remains no-go.',
        'missing_live_candidate_examples':['ipfs_accelerate_py/agent_supervisor/runtime/codebase_preview_successor_admission.py',
            'ipfs_accelerate_py/agent_supervisor/runtime/codebase_preview_successor_contract.py',
            'ipfs_accelerate_py/agent_supervisor/runtime/codebase_preview_successor_worker_admission.py',
            'ipfs_accelerate_py/agent_supervisor/runtime/codebase_preview_successor_worker_context.py',
            'docs/agent_supervisor/codebase_larger_head_native_owner_integration_note.md',
            'docs/agent_supervisor/codebase_verified_checkpoint_read_proposal.md'],
        'cross_repository_contracts':[
            'Exact ModelManager selectors separate family,width,input/latent role,schema/version,task,profile/format,record andcheckpoint. Null decoder identities remain unknown.',
            'Store append changes catalog generation; regenerate reviewed contexts instead of editing sealed generation fields. Byte authentication@2 does not admit numericalruntime.',
            'No executable accelerate contextualLegal cached-decoder callsite exists. Publishedbcd466 update is documentation-only; native fragment and contextual private-state contracts differ.',
            'Archive creation requires an explicit datasets checkout and inventories package bytes. Historical5cc datasets gitlink is an intentional canonical pointer, not a mandate to rewrite historicalarchives. New current-package runs require fresh source/asset/context/archive qualification.',
            'Native structural CodebaseIR uses53 compilerfeatures and an8-wide latent on the reported fixture, not a trained768D semantictextdecoder. Larger-head source widths and structural latents retain separate contracts.',
            'Latest uncommitted native notes report full300 membercoverage but110 encoded/184 deferred per mode, zeroformalized/checkedproperties, and one4096D liveCPUowner diagnostic. They do not admit larger CodebaseIR lineages or proofcache outputs.',
            'Typed formal artifact family/schema/version and independentchecker admission are required before generatedIR can become checkedproofindex evidence; embeddings and decoderloss have no proofauthority.',
            'PublishedCodex826 structuredplanning remains intact. Publishedd5 contextpair reports baseline reward1 versus compact0,response-envelope rejection andhigher compacttokens, so it grants no token-savingpromotion.',
        ],
        'retained_diagnostics':[{'path':'integration-observations.json','reason':'Initial supplement used registered Git metadata directory as file root and covered zero files; superseded byactual --show-toplevel comparisonv2.'},
            {'path':'integration-observations-v2.json','reason':'Its initial active-context-pair classification is superseded here byexact publicationbyte comparisons. All615 live-file comparisons remain valid.'}],
        'operations':{'repository_source_changed':False,'model_loaded':False,'training_executed':False,'database_opened':False,'huggingface_updated':False},
        'script_pin':pin(Path(__file__).resolve())}
    output=OUT/'findings.json'
    with output.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(pin(output)))


if __name__=='__main__':main()
