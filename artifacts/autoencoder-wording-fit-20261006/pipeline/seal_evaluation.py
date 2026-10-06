#!/usr/bin/env python3
"""Seal development evaluation only after both released paired fits exist.

This script hashes local inputs and prepares a reviewable plan/manifest. It never
loads Torch, models, encoders, source-head modules or development reference JSON.
The latter remains a separately authenticated artifact for the observer's durable
prediction barrier. No weights are moved, downloaded, promoted or admitted.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]
EXPERIMENT = WORKSPACE/'external/ipfs_datasets/workspace/test-logs/decoder-normative-wording-r2-20261006'
DEVELOPMENT = WORKSPACE/'artifacts/autoencoder-wording-fit-20261006/development/seal-manifest.json'
OBSERVER = 'scripts/ops/autoencoder/evaluate_normative_wording_development.py'
OBSERVER_SHA256 = '6be7e03656087fa9b5607b7e82b4a0a1244ca920cad8a81d64510f140962cfc6'
ARMS = {'normative-wording-zero','normative-wording-ce'}
ROLES = {'selected','last-attempt'}


def require(value,message):
    if not value:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda:stream.read(1048576),b''):
            h.update(data)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def exclusive_save(path,value):
    path = Path(path)
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def seal(args):
    root = args.experiment_root.resolve()
    output = args.output_directory.resolve()
    require(root.is_dir() and output.is_dir(), 'existing experiment/output directories required')
    paths = {name:output/name for name in ('evaluation-plan.json','evaluation-manifest.json',
        'evaluation-seal-receipt.json')}
    require(not any(path.exists() for path in paths.values()), 'fresh evaluation seal files required')
    training_manifest_path = root/'training-manifest.json'
    training_plan_path = root/'training-plan.json'
    training = read(training_manifest_path)
    inputs = dict(training['inputs'])
    def retain(path,wanted=None):
        path = Path(path).resolve()
        require(path.is_file() and not path.is_symlink(), 'regular retained input required: '+str(path))
        observed = sha(path)
        require(wanted is None or observed == wanted, 'retained input hash changed: '+str(path))
        require(str(path) not in inputs or inputs[str(path)] == observed,
            'duplicate input binding differs: '+str(path))
        inputs[str(path)] = observed
        return path
    def bind_refs(value):
        if type(value) is dict:
            if {'path','sha256'} <= set(value):
                retain(value['path'],value['sha256'])
            for child in value.values():
                bind_refs(child)
        elif type(value) is list:
            for child in value:
                bind_refs(child)
    for path,wanted in list(inputs.items()):
        retain(path,wanted)
    retain(training_manifest_path)
    retain(training_plan_path,training['plan_sha256'])
    require(read(training_plan_path)['input_sha256'] == training['inputs'], 'training input plan differs')
    summaries,terminals,aliases = {},{},{}
    for dimension,attempt in ((384,args.training_384),(768,args.training_768)):
        folder = root/attempt
        exit_path = retain(folder/'child-exit.json')
        resources_path = retain(folder/'resources-final.json')
        guardian_path = retain(root/(attempt+'-guardian-exit.json'))
        require(read(exit_path)['returncode'] == 0 and read(guardian_path)['returncode'] == 0
            and read(resources_path)['status'] == 'released', 'complete released width required: '+str(dimension))
        summary_path = retain(folder/'results/summary.json')
        summary = read(summary_path)
        require(summary.get('schema') == 'normative-wording-training-comparison/v1' and
            summary.get('complete') is True and summary.get('phase') == 'training' and
            summary.get('dimension') == dimension and len(summary.get('runs',[])) == 2 and
            {run['arm'] for run in summary['runs']} == ARMS,
            'both complete fixed training arms required: '+str(dimension))
        bind_refs(summary)
        aliases[str(dimension)] = {}
        for descriptor in summary['runs']:
            run_path = retain(descriptor['summary_path'],descriptor['summary_sha256'])
            run = read(run_path)
            require(run['dimension'] == dimension and run['arm'] == descriptor['arm']
                and run['budget_completed'] is True and run['seed'] == 1729
                and all(run.get(flag) is False for flag in ('qualified','admitted','checkpoint_promoted'))
                and ROLES <= set(run['states']), 'unqualified complete saved endpoint required')
            if run['arm'] == 'normative-wording-zero':
                require(run['zero_arm_archived_replay_verified'] is True, 'exact zero replay must already be verified')
            bind_refs(run)
            report = read(run['training_ref']['path'])
            require(report['optimizer_steps'] == 170 and len(report['committed_updates']) == 170,
                'complete matched170-update fit required')
            aliases[str(dimension)][run['arm']] = dict(
                selected_last_identical_tensor_alias=run['states']['selected']['tensor_sha256'] ==
                    run['states']['last-attempt']['tensor_sha256'],
                selected_tensor_sha256=run['states']['selected']['tensor_sha256'],
                last_tensor_sha256=run['states']['last-attempt']['tensor_sha256'])
        summaries[str(dimension)] = str(summary_path)
        terminals[str(dimension)] = dict(child_exit=str(exit_path),resources_final=str(resources_path))
    prep = root/'preparation-r1/results'
    prep_summary_path = retain(prep/'summary.json')
    prep_summary = read(prep_summary_path)
    require(prep_summary['complete'] is True and prep_summary['development_reference_json_parsed'] is False,
        'successful source-only native preparation required')
    bind_refs(prep_summary)
    source_inputs = {}
    for dimension in (384,768):
        path = retain(prep/f'development-inputs-{dimension}.json')
        data = read(path)
        require(data['schema'] == 'prospective-wording-source-inputs/v1' and data['complete'] is True
            and data['dimension'] == dimension and data['role'] == 'prospective_development'
            and len(data['rows']) == len(data['clause_cache']) == 60
            and all(set(row) == {'id','source_text','input'} for row in data['rows']),
            'complete source-only60-row native cache required')
        source_inputs[str(dimension)] = str(path)
    dev_seal_path = retain(args.development_seal)
    development = read(dev_seal_path)
    require(development['complete'] is True and development['encoder_executed'] is False
        and all(development.get(flag) is False for flag in ('admitted','checkpoint_promoted',
            'fresh_holdout_claimed','independent_human_review_authenticated')),
        'pre-model authored development seal required')
    # Authenticate the original builder closure too. Hashing reference bytes is
    # permitted; this script never parses their labels or passes them to a model.
    bind_refs(development)
    artifact = development['artifact_files']
    reference_path = retain(artifact['references']['path'],artifact['references']['sha256'])
    receipt_path = retain(artifact['receipt']['path'],artifact['receipt']['sha256'])
    development_receipt = read(receipt_path)
    require(development_receipt['schema'] == 'prospective-normative-development/v1'
        and development_receipt['complete'] is True and development_receipt['source_rows'] == 60
        and development_receipt['sealed_recipe_sha256'] == development['sealed_recipe_sha256']
        and development_receipt['actor_action_disjointness_checked'] is True
        and development_receipt['actor_action_group_overlap'] == 0,
        'complete sixty-source authored development receipt required')
    frozen_root = root/'experiment-source'
    observer_path = retain(frozen_root/OBSERVER,OBSERVER_SHA256)
    require(training['extensions'][OBSERVER] == OBSERVER_SHA256, 'training freeze observer pin differs')
    for relative,wanted in training['extensions'].items():
        retain(frozen_root/relative,wanted)
    # Import only the standalone script for its closed recipe. No package owner
    # or numerical runtime is initialized by this operation.
    spec = importlib.util.spec_from_file_location('_sealed_wording_development_recipe',observer_path)
    observer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(observer)
    retain(Path(__file__).resolve())
    for name in ('run_reserved.py','run_guardian.py','adopt_shared_scheduler.py',
        'lazy_scheduler_adoption.py','owned_lease_watchdog.py'):
        retain(root/name)
    plan = dict(observer.FIXED,input_sha256=inputs)
    manifest = dict(schema='normative-wording-development-manifest/v1',inputs=inputs,
        extensions=training['extensions'],producer_pins=training['producer_pins'],
        training_manifest=str(training_manifest_path),training_plan=str(training_plan_path),
        training_extension_root=str(frozen_root),training_summaries=summaries,training_terminals=terminals,
        source_inputs=source_inputs,references=str(reference_path),development_receipt=str(receipt_path),
        development_recipe_seal=development['sealed_recipe_sha256'],development_seal=str(dev_seal_path),
        reference_json_parsed_by_sealer=False,endpoint_tensor_aliases=aliases)
    for path,wanted in inputs.items():
        require(sha(path) == wanted, 'input changed during evaluation sealing: '+path)
    exclusive_save(paths['evaluation-plan.json'],plan)
    manifest['plan_sha256'] = sha(paths['evaluation-plan.json'])
    exclusive_save(paths['evaluation-manifest.json'],manifest)
    result = dict(schema='normative-wording-development-seal-receipt/v1',complete=True,
        inputs=len(inputs),extensions=len(manifest['extensions']),
        manifest_path=str(paths['evaluation-manifest.json']),manifest_sha256=sha(paths['evaluation-manifest.json']),
        plan_path=str(paths['evaluation-plan.json']),plan_sha256=manifest['plan_sha256'],
        all_four_fits_completed=True,endpoint_tensor_aliases=aliases,
        source_rows_per_panel=60,panels=8,reference_json_parsed=False,
        model_executed=False,encoder_executed=False,training_executed=False,
        qualified=False,admitted=False,lake_executed=False,checkpoint_promoted=False)
    exclusive_save(paths['evaluation-seal-receipt.json'],result)
    print(json.dumps(result,sort_keys=True))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--experiment-root',type=Path,default=EXPERIMENT)
    parser.add_argument('--training-384',default='training-384-r1')
    parser.add_argument('--training-768',default='training-768-r1')
    parser.add_argument('--development-seal',type=Path,default=DEVELOPMENT)
    parser.add_argument('--output-directory',type=Path,default=EXPERIMENT)
    seal(parser.parse_args())


if __name__ == '__main__':
    main()
