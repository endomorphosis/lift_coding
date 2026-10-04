"""Prepare pinned historical formula sidecars; never train or publish models."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = Path('/home/barberb/lift_coding/external/ipfs_datasets')
SELECTED_COMMIT = '64bc5734dc82db72e955f2e809b770127e9b6cfc'
INVENTORY_SHA = 'b18f382453cd93704a7401e29a5b00b99dd378854bf63ea3e2a845672cf73149'
PREFIX = 'releases/20261004-formula-sidecars-v1'
PRODUCERS = {
    'scripts/ops/autoencoder/benchmark_multidimension_modality_training.py': '5cf07411916024fa8be12f5b68ad258a113c31a335d6fc6b366cabcf0ded926b',
    'scripts/ops/autoencoder/benchmark_formula_checkpoint_continuation.py': '172e57ee71aa8bba810fe09603d24fc422ca909ca2b1e15dcc4d37a74b5c1807',
}


def require(value, message):
    if not value:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def file_binding(path, data):
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read(binding):
    path = Path(binding['path']).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'nonsymlink ordinary input required')
    require(path.is_file() and 0 < path.stat().st_size <= 32 * 1024 ** 2, 'bounded input required')
    data = path.read_bytes()
    require(file_binding(path, data) == binding, 'external selected file differs')
    return data


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return file_binding(path, data)


def sealed(value):
    value = dict(value)
    value['content_sha256'] = hashlib.sha256(raw(value)).hexdigest()
    return raw(value) + b'\n'


def prepare():
    inventory_file = WORK / 'formula_sidecar_inventory.json'
    data = inventory_file.read_bytes()
    require(hashlib.sha256(data).hexdigest() == INVENTORY_SHA, 'selected inventory differs')
    inventory = json.loads(data)
    require(hashlib.sha256(raw({k: v for k, v in inventory.items() if k != 'content_sha256'})).hexdigest()
            == inventory['content_sha256'], 'inventory seal differs')
    directory = WORK / 'formula-sidecars-v1'
    require(not directory.exists(), 'fresh release directory required')
    directory.mkdir(mode=0o700)
    inputs = [file_binding(inventory_file, data)]
    git_inputs = []
    states = []
    comparisons = []
    sources = {}

    def publish_file(relative, value):
        return put(directory / relative, value)

    for group in inventory['comparisons']:
        label = 'original340' if group['comparison'] == 'decoder-four-width-20261004' else 'continuation170'
        rows = []
        for arm in group['arms']:
            row = {key: arm[key] for key in ('arm', 'dimension', 'seed', 'recipe', 'completed_optimizer_steps', 'selected_epoch', 'exact_optimizer_resume')}
            for endpoint in arm['states']:
                binding = endpoint['file_binding']
                state_data = read(binding)
                inputs.append(binding)
                relative = f'checkpoints/{label}/{arm["arm"]}/{endpoint["role"]}-state.json'
                publish_file(relative, state_data)
                states.append({'path': relative, 'comparison': label, 'arm': arm['arm'], 'dimension': arm['dimension'],
                    'role': endpoint['role'], 'selected': endpoint['selected'], 'weights_sha256': endpoint['weights_sha256'],
                    'producer_declared_runtime_tensor_sha256': endpoint['producer_declared_runtime_tensor_sha256'],
                    'runtime_tensor_digest_independently_recomputed': False,
                    'fit_completed_optimizer_steps': arm['completed_optimizer_steps'], 'selected_epoch': arm['selected_epoch'],
                    'initial_and_epoch_zero_endpoints_are_not_newly_fitted_weights': True})
            rows.append(row)
        comparisons.append({'name': label, 'fit_count': 6, 'completed_optimizer_updates': group['completed_optimizer_updates'],
                            'producer_elapsed_seconds': group['producer_elapsed_seconds'], 'arms': rows})
        for source in group['producer_source_pins']:
            key = source['producer_source_key']
            wanted = source['producer_sha256']
            if key in sources:
                require(sources[key]['sha256'] == wanted, 'historical source version collision')
                continue
            category, relative = key.split(':', 1)
            require(category in {'dependency', 'extension', 'parent_extension', 'previous_extension'}
                    and not Path(relative).is_absolute() and '..' not in Path(relative).parts, 'explicit safe capsule path required')
            if source['matching_explicit_source_files']:
                source_binding = source['matching_explicit_source_files'][0]
                source_data = read(source_binding)
                inputs.append(source_binding)
            else:
                result = subprocess.run(['git', '-C', str(ROOT), 'show', SELECTED_COMMIT + ':' + relative],
                                        capture_output=True, check=True, timeout=30)
                source_data = result.stdout
                require(len(source_data) <= 2 * 1024 ** 2 and hashlib.sha256(source_data).hexdigest() == wanted,
                        'selected historical Git source differs')
                oid = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', SELECTED_COMMIT + ':' + relative],
                                     capture_output=True, check=True, timeout=30).stdout.decode().strip()
                git_inputs.append({'repository': str(ROOT), 'commit': SELECTED_COMMIT, 'path': relative,
                                   'git_blob_oid': oid, 'bytes': len(source_data), 'sha256': wanted})
            require(hashlib.sha256(source_data).hexdigest() == wanted, 'producer source pin differs')
            target = f'source-capsule/{category}/{relative}'
            publish_file(target, source_data)
            sources[key] = {'path': target, 'bytes': len(source_data), 'sha256': wanted}
    for relative, wanted in PRODUCERS.items():
        candidates = [ROOT / relative, *[ROOT / 'workspace/test-logs' / run / 'experiment-source' / relative
                                       for run in ('decoder-four-width-20261004', 'decoder-continuation-20261004')]]
        selected = next((p for p in candidates if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == wanted), None)
        require(selected is not None, 'pinned historical producer unavailable')
        data = selected.read_bytes()
        inputs.append(file_binding(selected, data))
        publish_file('source-capsule/producers/' + relative, data)
    license_path = ROOT / 'LICENSE'
    license_data = license_path.read_bytes()
    inputs.append(file_binding(license_path, license_data))
    publish_file('LICENSE', license_data)
    checker = WORK / 'verify_formula_sidecar_release.py'
    checker_data = checker.read_bytes()
    inputs.append(file_binding(checker, checker_data))
    publish_file('verify_formula_sidecar_release.py', checker_data)
    overview = f'''---
license: agpl-3.0
tags:
- formal-logic
- experimental-decoder
---

# Experimental native-vector-conditioned formula sidecars

This append-only release retains 36 JSON states from twelve historical decoder
fits: six original 340-update fits and six distinct 170-update continuations.
The native input widths are 8, 384 and 768. These are fixed-vocabulary formula
decoders, with a frozen residual identity path; they are not learned vector
reconstruction autoencoders. No pretrained embedding backbone is included.

Each arm has separately labelled initial, selected and last-attempt states.
Epoch-zero selected endpoints retain their parent/initial weights. The fit budget
is not the optimizer age of every selected endpoint. Continuations restore model
weights with fresh optimizer and scheduler; no optimizer state is provided.

The original comparison has 2,040 completed updates and reported training wall
time 547.527 seconds. The continuations have 1,020 further updates and reported
wall time 397.537 seconds. These are saved producer measurements, not a new
benchmark. Only the original 384D auxiliary arm selected newly fitted weights
(epoch 80); other original arms selected epoch zero. Continuation selections:
8D low-rate epoch 4, 8D high-rate epoch zero, both larger widths epoch 40.

The decoder vocabulary has 32 tokens; its source interface requires explicit
transformed source vectors and padded clause context. Hidden width is 64.
Saved preprocessing statistics and producer provenance are retained in each
state. Upstream source-vector production and target vocabulary are separate
requirements; width equality alone does not establish compatibility.

## Check integrity

Download this whole release directory. Select the SHA256 of
`release_manifest.json` from the publication receipt, then run:

```sh
python -I -B verify_formula_sidecar_release.py --directory . --expected-manifest-sha256 SELECTED_SHA256
```

The checker verifies exact file identities, finite saved JSON weights and the
JSON weight digest. It imports no ML library and runs no model. Runtime tensor
digests are historical producer declarations, not newly reconstructed tensors.

## Restore scope

The capsule contains 95 exact historical dependency/extension source versions
and two producer scripts. Version categories are separate because the producers
composed multiple versions. This is a source capsule, not an installable complete
runtime. Original `benchmark_formula_checkpoint_continuation.py::restore_model`
uses `prepare_lane` and a sealed private experiment context, then checks strict
state layout and runtime tensor digests. Those private inputs are not distributed.
No downloaded standalone numerical restore smoke was executed for this release.
Production-runtime compatibility remains false.

These exposed authored development comparisons establish no fresh-holdout gain,
global logic-family coverage, semantic-label admission, source fidelity, proof
authority or production qualification. All saved authority flags remain false.
Raw reference banks and training-report bodies are excluded. This release
contains authorial AGPL-3.0 code/checkpoint assets; upstream backbones retain
their own licenses and are not copied or relicensed.

Repository destination: `Publicus/legal-ir-autoencoder/{PREFIX}`.
'''
    publish_file('README.md', overview.encode())
    for comparison in comparisons:
        text = '# ' + comparison['name'] + '\n\n'
        text += 'Experimental fixed-vocabulary decoder states. Initial and selected epoch-zero states are labelled explicitly.\n\n'
        text += '| Arm | Width | Completed fit updates | Selected epoch |\n| --- | ---: | ---: | ---: |\n'
        for arm in comparison['arms']:
            text += f'| {arm["arm"]} | {arm["dimension"]} | {arm["completed_optimizer_steps"]} | {arm["selected_epoch"]} |\n'
        text += '\nNo learned vector reconstruction, optimizer resume, fresh-holdout qualification or proof authority is claimed.\n'
        publish_file('cards/' + comparison['name'] + '.md', text.encode())
    files = []
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            value = path.read_bytes()
            files.append({'path': str(path.relative_to(directory)), 'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()})
    public = {'schema': 'experimental-formula-sidecar-release/v1', 'repo_id': 'Publicus/legal-ir-autoencoder',
              'prefix': PREFIX, 'comparisons': comparisons, 'states': states, 'source_capsule': list(sources.values()),
              'files': files, 'model_loads': 0, 'new_training_executed': False, 'qualified': False,
              'source_fidelity_established': False, 'proof_authority': False, 'semantic_gold_created': False,
              'complete_runtime_or_private_input_closure_claimed': False}
    manifest_binding = publish_file('release_manifest.json', sealed(public))
    files.append({'path': 'release_manifest.json', 'bytes': manifest_binding['bytes'], 'sha256': manifest_binding['sha256']})
    # The private upload plan binds original inputs; it is never uploaded itself.
    input_map = {item['path']: item for item in inputs}
    for binding in input_map.values():
        read(binding)
    plan = {'schema': 'experimental-HF-append-only-publication-plan/v1', 'repo_id': 'Publicus/legal-ir-autoencoder',
            'prefix': PREFIX, 'directory': str(directory), 'files': files,
            'original_input_bindings': list(input_map.values()), 'original_git_source_bindings': git_inputs,
            'public_manifest_binding': manifest_binding, 'model_loads': 0, 'new_training_executed': False,
            'qualified': False, 'source_fidelity_established': False, 'proof_authority': False,
            'training_report_bodies_or_raw_reference_banks_uploaded': False}
    return put(WORK / 'formula_sidecar_publication_plan.json', sealed(plan)), manifest_binding


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    plan, manifest = prepare()
    print(json.dumps({'plan': plan, 'public_manifest': manifest}, sort_keys=True))
