"""Authenticate retained banks, then probe real selected-state CE without fitting."""
import argparse
from contextlib import ExitStack
import hashlib
import importlib
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path('/home/barberb/lift_coding')
DATASETS = ROOT / '.worktrees/dual-bank-wording-adapter-datasets-20261007'
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(DATASETS))


def pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    assert 0 < len(raw) <= 32 * 1024 * 1024
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    return pin(path)


def load_verified(path, expected, name):
    assert pin(path)['sha256'] == expected
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert pin(path)['sha256'] == expected
    return module


class ForbiddenImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'transformers','sentence_transformers','huggingface_hub','duckdb','ducklake','ipfs_accelerate_py'}:
            raise AssertionError('No encoder/Hub/database/manager imports: '+fullname)


def audit(event, args):
    if event in {'socket.connect','socket.getaddrinfo'}:
        raise AssertionError('No network in retained-bank probe')


def fail(*args, **kwargs):
    raise AssertionError('No fitting or optimizer action in this probe')


def main(mode):
    sys.meta_path.insert(0, ForbiddenImports()); sys.addaudithook(audit)
    from scripts.ops.autoencoder.dual_bank_wording_replay import dual_bank_training_adapter as subject
    from ipfs_datasets_py.logic.formalization.autoencoder import normative_wording_modality_auxiliary as normative
    from ipfs_datasets_py.logic.formalization.autoencoder import paraphrase_modality_auxiliary_training as auxiliary
    from ipfs_datasets_py.logic.formalization.autoencoder import contextual_training_mixture as mixture
    from ipfs_datasets_py.logic.formalization.autoencoder import normative_wording_training_sources as authored_control
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_formula_codec as syntax
    assert 'torch' not in sys.modules
    campaign = ROOT / 'external/ipfs_datasets/workspace/test-logs/decoder-balanced-wording-20261007'
    manifest_path = campaign / 'training-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    extension = campaign / 'experiment-source'
    old = load_verified(extension/'balanced_wording_runtime_adapter.py',manifest['extensions']['balanced_wording_runtime_adapter.py'],'_retained_pairing_adapter')
    authored_balanced = load_verified(extension/'balanced_wording_candidates.py',manifest['extensions']['balanced_wording_candidates.py'],'_retained_balanced_renderer')
    asset = ROOT / 'artifacts/autoencoder-balanced-wording-20261007/runtime/assembled-inputs-r1'
    paths = [asset/(role+'-source-inventory.json') for role in subject.ROLES]
    pair_path = campaign/'training-384-r2/results/paired-source-schedule.json'
    rules_path = Path(manifest['original90_rules'])
    original = ROOT/'external/ipfs_datasets/workspace/test-logs/decoder-four-width-20261004/training-r1/results/384'
    rows_path, contexts_path = original/'training-rows.json', original/'source-contexts.json'
    codec_path = ROOT/'artifacts/autoencoder-wording-fit-20261006/development/codec.json'
    input_paths = paths+[pair_path,rules_path,rows_path,contexts_path,codec_path,manifest_path,
        extension/'balanced_wording_runtime_adapter.py',extension/'balanced_wording_candidates.py']
    original_pins = [pin(p) for p in input_paths]
    inventories = {role:json.loads(path.read_text()) for role,path in zip(subject.ROLES,paths)}
    assert pin(paths[0])['sha256']=='a9d3a6962986ec674d7673a609a23af614aef6b797b99903979c2c645c2fd57b'
    assert pin(paths[1])['sha256']=='48ca58d67e6da85ece58e70b6c6d91210d9d983530f8eae8980ada8799a26c60'
    pairing, rules = json.loads(pair_path.read_text()), json.loads(rules_path.read_text())
    rows, contexts, codec = json.loads(rows_path.read_text()), json.loads(contexts_path.read_text()), json.loads(codec_path.read_text())
    helpers = {}
    for role, authored in [('control',authored_control),('balanced',authored_balanced)]:
        helper,_ = old.configure_profile(normative, auxiliary_owner=auxiliary,mixture_owner=mixture,
            authored_owner=authored,pairing=pairing,role=role,
            prior_dataset_names=tuple(inventories[role]['prior_sources_by_dataset']))
        helpers[role]=helper
    helper = subject.configure(helpers_by_role=helpers,pairing=pairing,original_rules=rules)
    envelope = subject.build_source_inventory(inventories,pairing)
    def references(items):
        result=[]
        for row in items:
            target=json.loads(''.join(codec['target_vocabulary'][token] for token in row['target_ids'][1:-1]))
            result.append(dict(id=row['id'],source_text=row['source_text'],source_sha256=hashlib.sha256(row['source_text'].encode()).hexdigest(),
                target=target,clause_count=len(target['rules'])))
        return result
    def validate_rule(value):
        syntax._rule(value)
        return {'valid':True,'scope':'narrow canonical syntax only','source_semantics_verified':False,'proof_authority':False}
    banks = helper.prepare_bank(rows['train'],rows['validation'],training_references=references(rows['train']),
        validation_references=references(rows['validation']),source_contexts=contexts,codec=codec,
        validate_rule=validate_rule,source_inventory=envelope,deadline=time.monotonic()+120)
    assert 'torch' not in sys.modules and 'transformers' not in sys.modules
    assert banks.receipt['bank_count']==2 and banks.schedule['schedule_sha256']=='cd07c1d52399de41b737c41b791a0a86fa336bd9f642889feb4f11d44d90300f'
    result = dict(schema='retained-dual-bank-preparation-probe/v1',completed=True,
        bank_receipt=banks.receipt,schedule=banks.schedule,input_pins=original_pins,
        numerical_library_imported_during_prepare=False,encoder_executed=False,optimizer_executed=False,
        training_executed=False,network_or_database_executed=False,proof_authority=False,
        syntax_validator_scope='current narrow canonical syntax; no full compiler/native/proof validation',
        inherited_train_validation_references_accessed=True,unseen_reference_blinding_claimed=False)
    save(HERE/'retained-bank-preparation.json',result)
    if mode=='forward':
        from ipfs_datasets_py.logic.formalization.autoencoder import normative_legal_ir_runtime as runtime
        from ipfs_datasets_py.logic.formalization.autoencoder import contextual_legal_ir_numeric as numeric
        old_options_path = ROOT/'artifacts/normative-decoder-runtime-20261007/preflight-final/384-normative-wording-ce-options.json'
        options=json.loads(old_options_path.read_text())
        options['source_owner_pins']={name:pin(Path(runtime.__file__).with_name(name+'.py')) for name in runtime.SOURCE_OWNER_NAMES}
        options['max_reference_bytes']=runtime.MAX_REFERENCE_BYTES
        captured=runtime._capture(**options)
        _,prepared,_=runtime._prepare(captured)
        import torch
        torch.set_num_threads(1)
        with ExitStack() as stack:
            stack.enter_context(patch.object(torch.optim.Optimizer,'__init__',fail))
            rng_before=torch.get_rng_state().clone()
            restored=numeric.restore_contextual_legal_model(prepared)
            assert restored.tensor_sha256=='0b3c7c3b1a5581cd393d9bb8db1d24b87fe2cb9dff0be268aa2b5ed1f88b6594'
            state_before={name:value.clone() for name,value in restored.model.state_dict().items()}
            cache=helper.prepare_tensor_cache(torch,restored.model,banks,codec=codec,input_transform=restored.input_transform,
                seed=1729,deadline=time.monotonic()+180,max_optimizer_steps=170)
            observations=[]
            for index in range(170):
                packet=helper.modality_loss(torch,restored.model,cache,committed_step=index,
                    requires_grad=False,deadline=time.monotonic()+30)
                assert packet['loss'].requires_grad is False
                observations.append(packet['receipt'])
            assert all(torch.equal(value,state_before[name]) for name,value in restored.model.state_dict().items())
            assert torch.equal(rng_before,torch.get_rng_state())
            save(HERE/'retained-bank-forward-observations.json',dict(schema='retained-dual-bank-source-ce-probe/v1',
                completed=True,model_tensor_sha256=restored.tensor_sha256,cache_receipt=cache.receipt,
                observations=observations,forward_calls=170,source_clause_observations=1020,
                optimizer_commits=0,training_executed=False,weights_and_rng_unchanged=True,
                encoder_executed=False,network_or_database_executed=False,source_semantics_verified=False,
                fresh_holdout=False,proof_authority=False))
    assert all(pin(p['path'])==p for p in original_pins)
    print(json.dumps(dict(completed=True,mode=mode,source_banks=2,source_schedule_sha256=banks.schedule['schedule_sha256'],optimizer_commits=0)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['prepare','forward'])
    main(parser.parse_args().mode)
