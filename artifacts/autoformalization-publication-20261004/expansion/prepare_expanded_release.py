"""Prepare nine completed reconstruction checkpoints from externally selected reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = Path('/home/barberb/lift_coding/external/ipfs_datasets')
PREFIX = 'releases/20261005-authored32-source-reconstruction-aes-v1'
PLAN_SCHEMA = 'source-vector-expanded-reconstruction-run-plan/v1'
HELPER_SHA = '9d5dca6c6a07d60956eb9da3c874b9df65e8cd8ad965ed16090bbc70738c1182'
CHECKER_SHA = '21816a6540b8e02f7dadcdf7efdf04c071f62b9e90e29199e8e878bcb9cc59e2'
LANES = {'legacy8': [8, 16, 4], 'native384': [384, 128, 32], 'native768': [768, 128, 64]}
MASKS = ('weak_decoder_fit', 'strong_semantic_fit', 'contrastive_supervision', 'proof_supervision', 'fidelity_evaluation')


def require(value, reason):
    if not value:
        raise ValueError(reason)


def raw(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key rejected')
            result[key] = value
        return result
    return json.loads(data.decode('utf-8', 'strict'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON rejected')))


def binding(path, data):
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read_selected(reference):
    require(type(reference) is dict and set(reference) == {'path', 'bytes', 'sha256'}, 'closed selected file binding required')
    path = Path(reference['path'])
    require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)), 'absolute nonsymlink selection required')
    require(type(reference['bytes']) is int and 0 < reference['bytes'] <= 32 * 1024 ** 2, 'bounded selected input required')
    before = path.stat()
    require(path.is_file() and before.st_size == reference['bytes'], 'selected file size differs')
    data = path.read_bytes()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), 'selected source changed during read')
    require(binding(path, data) == reference, 'selected file SHA differs')
    return data


def unbound_file(path):
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)), 'ordinary code source required')
    data = path.read_bytes()
    require(0 < len(data) <= 2 * 1024 ** 2, 'bounded source required')
    return data, binding(path, data)


def seal(value):
    require(type(value) is dict and hashlib.sha256(raw({k: v for k, v in value.items() if k != 'content_sha256'})).hexdigest()
            == value.get('content_sha256'), 'selected JSON seal differs')


def sealed(value):
    value = dict(value)
    value['content_sha256'] = hashlib.sha256(raw(value)).hexdigest()
    return raw(value) + b'\n'


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path, data)


def prepare(selection_reference, output_directory):
    selection = decode(read_selected(selection_reference))
    require(type(selection) is dict and set(selection) == {'schema', 'run_plan_binding', 'reports', 'content_sha256'}
            and selection['schema'] == 'source-reconstruction-publication-selection/v1', 'closed selection required')
    seal(selection)
    plan_reference = selection['run_plan_binding']
    require(type(plan_reference['sha256']) is str and len(plan_reference['sha256']) == 64, 'externally bound run plan required')
    plan_data = read_selected(plan_reference)
    plan = decode(plan_data)
    seal(plan)
    require(plan['schema'] == PLAN_SCHEMA and plan['seeds'] == [1729, 1730, 1731]
            and plan['config']['steps'] == 200 and plan['config']['private_resume_comparison_updates'] == 3,
            'fixed reconstruction run differs')
    require(plan['authorization_scope'] == 'user_authorized_source_vector_reconstruction_only_no_semantic_mask_promotion'
            and len(plan['train_selection']) == 32
            and all(r['original_masks'] == dict.fromkeys(MASKS, 0) for r in plan['train_selection']),
            'expanded source-only TRAIN32 masks/scope differ')
    cohort_data = read_selected(plan['cohort_binding'])
    cohort = decode(cohort_data)
    seal(cohort)
    require(cohort['schema'] == 'source-only-authored-expansion-cohort/v1'
            and cohort['contains_formal_targets'] is False and len(cohort['rows']) == 64
            and cohort['policy']['semantic_masks'] == dict.fromkeys(MASKS, 0)
            and cohort['policy']['source_reconstruction_fit_authorized'] is True
            and cohort['policy']['semantic_label_admission'] is False, 'expanded cohort scope differs')
    helper_reference = plan['helper_binding']
    require(helper_reference['sha256'] == HELPER_SHA, 'selected reconstruction helper differs')
    helper_data = read_selected(helper_reference)
    checker_path = WORK.parent / 'huggingface/verify_reconstruction_release.py'
    checker_data, checker_reference = unbound_file(checker_path)
    require(checker_reference['sha256'] == CHECKER_SHA, 'selected integrity checker differs')
    namespace = {'__name__': '_selected_static_reconstruction_checker', '__file__': str(checker_path)}
    exec(compile(checker_data, str(checker_path), 'exec'), namespace)
    require(type(selection['reports']) is list and len(selection['reports']) == 9, 'exact9 completed reports required')
    order = [(lane, seed) for lane in LANES for seed in (1729, 1730, 1731)]
    directory = Path(output_directory).absolute()
    require(not directory.exists() and not any(p.is_symlink() for p in directory.parents), 'fresh release directory required')
    directory.mkdir(mode=0o700)
    inputs = {reference['path']: reference for reference in (selection_reference, plan_reference, helper_reference, checker_reference, plan['cohort_binding'])}
    arms = []

    def selected(reference):
        data = read_selected(reference)
        inputs[reference['path']] = reference
        return data

    def publish(relative, data):
        return put(directory / relative, data)

    for report_reference, (lane, seed) in zip(selection['reports'], order, strict=True):
        report = decode(selected(report_reference))
        seal(report)
        require(report['schema'] == 'source-vector-reconstruction-training-report/v1'
                and report['status'] == 'completed_fixed_budget_reconstruction_only'
                and report['lane_id'] == lane and type(report['seed']) is int and report['seed'] == seed,
                'completed ordered lane/seed report differs')
        for key, wanted in (('selected_optimizer_updates', 200), ('additional_private_optimizer_updates', 3),
                            ('actual_total_optimizer_updates', 203), ('training_rows', 32), ('query_or_dev_rows_read', 0),
                            ('encoder_backbone_calls', 0), ('prover_calls', 0), ('cpu_threads', 1)):
            require(type(report[key]) is int and report[key] == wanted, 'actual report count differs')
        require(report['reconstruction_fit_authorized'] is True and report['device'] == 'cpu' and report['optimizer'] == 'Adam',
                'reconstruction-only CPU fit scope differs')
        for key in ('saved_reload_exact', 'private_resume_weights_and_adam_exact', 'master_state_preserved',
                    'global_cpu_rng_preserved', 'finite_loss_gradients_parameters_and_adam'):
            require(report[key] is True, 'saved verification did not complete')
        for key in ('semantic_fit_authorized', 'contrastive_fit_authorized', 'source_fidelity_established', 'proof_authority',
                    'qualified', 'os_sandbox', 'formal_target_bodies_read', 'old_checkpoints_modified'):
            require(report[key] is False, 'report authority or execution scope differs')
        require(report['masks'] == dict.fromkeys(MASKS, 0) and all(type(v) is int for v in report['masks'].values()),
                'report semantic masks forbidden')
        config = report['config']
        require(config['lane_id'] == lane and config['seed'] == seed and config['architecture'] == LANES[lane]
                and config['helper_binding'] == helper_reference and config['plan_sha256'] == hashlib.sha256(raw(plan)).hexdigest()
                and config['bundle_binding'] == plan['lanes'][lane]['bundle_binding'], 'actual config lineage differs')
        require(type(config['training_rows']) is int and config['training_rows'] == 32
                and config['batch_schedule'] == 'TRAIN32_seed_plus_epoch_four_batches/v1'
                and config['fit_policy'] == 'source_vector_self_reconstruction_only_no_semantic_admission/v1'
                and config['cohort_binding'] == plan['cohort_binding'], 'expanded config scope differs')
        require(report['source_only_development_metadata_rows_read'] == 32
                and report['query_or_dev_rows_scope'] == 'native_vector_rows_only; source-only64identity_metadata_read_for_split_validation'
                and report['batches_per_epoch'] == 4 and report['selected_epochs'] == 50,
                'expanded scheduling/metadata access scope differs')
        require(config['training_ids'] == [r['id'] for r in plan['train_selection']]
                and len(config['input_sha256s']) == 32, 'ordered TRAIN cohort differs')
        refs = [report[key] for key in ('initial_checkpoint', 'midpoint_checkpoint', 'selected_checkpoint')]
        checkpoints = [decode(selected(reference)) for reference in refs]
        for checkpoint, step in zip(checkpoints, (0, 100, 200), strict=True):
            seal(checkpoint)
            require(checkpoint['config'] == config and checkpoint['normalization'] == report['normalization']
                    and type(checkpoint['optimizer_steps']) is int and checkpoint['optimizer_steps'] == step,
                    'saved progress/config differs')
        require(checkpoints[0]['parent_checkpoint_sha256'] is None
                and checkpoints[1]['parent_checkpoint_sha256'] == hashlib.sha256(raw(checkpoints[0])).hexdigest()
                and checkpoints[2]['parent_checkpoint_sha256'] == hashlib.sha256(raw(checkpoints[1])).hexdigest(),
                'checkpoint parent chain differs')
        final = checkpoints[2]
        values_checked = namespace['checkpoint_values'](Path(refs[2]['path']).parent, final, config)
        relative = f'checkpoints/{lane}-seed{seed}'
        publish(relative + '/checkpoint.json', selected(refs[2]))
        for field in ('model_file', 'optimizer_file'):
            item = final[field]
            reference = {**item, 'path': str(Path(refs[2]['path']).parent / item['path'])}
            publish(relative + '/' + item['path'], selected(reference))
        # Retain every newly saved model/Adam payload on HF. These three
        # archival phases are explicitly unselected; selected200 remains above.
        scratch_reference = report['scratch_resume_checkpoint']
        scratch = decode(selected(scratch_reference))
        archived = [('initial-0', refs[0], checkpoints[0], 0),
                    ('midpoint-100', refs[1], checkpoints[1], 100),
                    ('private-resume-201', scratch_reference, scratch, 201)]
        for phase_name, state_reference, state, step in archived:
            seal(state)
            require(state['schema'] == 'source-vector-reconstruction-checkpoint/v1'
                    and state['config'] == config and state['normalization'] == report['normalization']
                    and type(state['optimizer_steps']) is int and state['optimizer_steps'] == step
                    and state['masks'] == dict.fromkeys(MASKS, 0)
                    and all(state[k] is False for k in ('semantic_fit_authorized', 'contrastive_fit_authorized',
                        'source_fidelity_established', 'proof_authority', 'qualified')), 'archival state scope differs')
            archive_path = f'archives/{lane}-seed{seed}/{phase_name}'
            publish(archive_path + '/checkpoint.json', selected(state_reference))
            tables = {}
            for field in ('model_file', 'optimizer_file'):
                item = state[field]
                expected_filename = 'model.safetensors' if field == 'model_file' else 'optimizer.safetensors'
                require(item['path'] == expected_filename, 'archival tensor filename differs')
                reference = {**item, 'path': str(Path(state_reference['path']).parent / item['path'])}
                data = selected(reference)
                tables[field] = namespace['tensor_values'](data)
                publish(archive_path + '/' + item['path'], data)
            shapes = namespace['model_shapes'](config['architecture'])
            require(set(tables['model_file']) == set(shapes)
                    and all(tables['model_file'][k]['shape'] == shape for k, shape in shapes.items()),
                    'archival model shape inventory differs')
            for field, state_digest in (('model_file', 'model_state_sha256'), ('optimizer_file', 'optimizer_state_sha256')):
                require(hashlib.sha256(raw({k: v['nested'] for k, v in tables[field].items()})).hexdigest() == state[state_digest],
                        'archival serialized-value digest differs')
            optimizer_table = tables['optimizer_file']
            if step == 0:
                require(set(optimizer_table) == {'__empty__'} and optimizer_table['__empty__']['shape'] == [0],
                        'archival zero-step Adam must be empty')
            else:
                require(set(optimizer_table) == {name + '/' + field for name in shapes for field in ('step', 'exp_avg', 'exp_avg_sq')},
                        'archival Adam inventory differs')
                for name, shape in shapes.items():
                    require(optimizer_table[name + '/step']['shape'] == []
                            and optimizer_table[name + '/step']['values'] == [float(step)]
                            and optimizer_table[name + '/exp_avg']['shape'] == shape
                            and optimizer_table[name + '/exp_avg_sq']['shape'] == shape
                            and all(v >= 0 for v in optimizer_table[name + '/exp_avg_sq']['values']),
                            'archival Adam step/moment shape/domain differs')
        for phase in ('initial_observations', 'final_observations'):
            require(report[phase]['row_count'] == 32 and report[phase]['raw_identity_reconstruction_mse'] == 0., 'control scope differs')
        summary_keys = ('schema', 'status', 'lane_id', 'seed', 'config', 'normalization', 'selected_optimizer_updates',
            'additional_private_optimizer_updates', 'actual_total_optimizer_updates', 'training_rows', 'query_or_dev_rows_read',
            'saved_reload_exact', 'private_resume_weights_and_adam_exact', 'master_state_preserved', 'global_cpu_rng_preserved',
            'finite_loss_gradients_parameters_and_adam', 'parameter_count', 'torch_version', 'wall_seconds', 'peak_rss_kib',
            'worker_cpu_seconds', 'publication_gate_scope', 'masks', 'reconstruction_fit_authorized', 'semantic_fit_authorized',
            'contrastive_fit_authorized', 'source_fidelity_established', 'proof_authority', 'qualified', 'os_sandbox', 'device',
            'cpu_threads', 'optimizer', 'encoder_backbone_calls', 'formal_target_bodies_read', 'prover_calls', 'old_checkpoints_modified',
            'source_only_development_metadata_rows_read', 'query_or_dev_rows_scope', 'batch_schedule',
            'fit_policy', 'selected_epochs', 'batches_per_epoch')
        summary = {key: report[key] for key in summary_keys}
        summary['schema'] = 'public-reconstruction-training-summary/v1'
        summary['original_training_report_file_binding'] = report_reference
        summary['scope'] = 'exact_selected_report_metadata_and_scalar_metrics_without_vector_row_tables'
        summary['initial_raw_coordinate_mse'] = report['initial_observations']['raw_coordinate_mse']
        summary['final_raw_coordinate_mse'] = report['final_observations']['raw_coordinate_mse']
        summary['raw_identity_reconstruction_mse'] = 0.
        summary['selected_checkpoint_path'] = relative + '/checkpoint.json'
        publish(f'reports/{lane}-seed{seed}.json', sealed(summary))
        arms.append({'lane_id': lane, 'seed': seed, 'config': config, 'checkpoint_path': relative + '/checkpoint.json',
                     'training_summary_path': f'reports/{lane}-seed{seed}.json', 'initial_mse': summary['initial_raw_coordinate_mse'],
                     'final_mse': summary['final_raw_coordinate_mse'], 'serialized_values_checked': values_checked})

    publish('train_reconstruction.py', helper_data)
    publish('run-plan-expanded-01.json', plan_data)
    publish('verify_reconstruction_release.py', checker_data)
    license_data, license_reference = unbound_file(ROOT / 'LICENSE')
    inputs[license_reference['path']] = license_reference
    publish('LICENSE', license_data)
    text = '''---
license: agpl-3.0
tags:
- autoencoder
- reconstruction
- experimental
---

# Source-vector reconstruction autoencoders: nine completed experimental fits

These nine new models reconstruct frozen native source vectors. They are
separate from the old spaCy categorical heads, the retained 384D residual/formula
model, and the 768D-conditioned span decoder. No text encoder backbone or
text-to-formal decoder is included.

| Lane | Native input/output | Hidden width | Complete latent width |
| --- | ---: | ---: | ---: |
| legacy8 | 8 | 16 | 4 |
| native384 | 384 | 128 | 32 |
| native768 | 768 | 128 | 64 |

Every lane has seeds 1729, 1730 and 1731. Each encoder has two linear layers
with an intermediate tanh; the decoder reverses the widths with tanh. There
is no skip connection or sample memory. Normalize native coordinates using
the saved TRAIN coordinate mean/global centered RMS, encode, decode, then
reverse normalization. The complete latents are 4D, 32D and 64D respectively.

The inputs are frozen spaCy8 linguistic features, mean-pooled/L2 GTE-small384,
and CLS-pooled/L2 GTE-multilingual768 with pinned producer revisions. A separately recorded source-only encoding stage produced64 native vectors
per lane before fitting. No text backbone fine-tuning occurred; these fits
read only the frozen32 TRAIN vectors per lane. The
original producer normalization and the AE's TRAIN transform are distinct.

Each model completed 200 selected-lineage Adam updates at .003, batch8,
CPU float32/one thread and gradient clipping5. Selected step200 was fixed
before fitting. The cohort is the exposed authored32 TRAIN sources/eight declared groups;
no DEV vector fitting/scoring, formal labels or semantic relations were used.
Source-only identity metadata for32 DEV requests was read for split validation.
Four batches form an epoch;200 selected updates correspond to50 epochs. Across
nine arms there are 1,800 selected updates and 27 separately counted scratch
Adam-resume comparison updates, 1,827 actual updates. The selected200 master
was preserved. The archives retain27 explicitly unselected initial0, midpoint100
and private-resume201 triplets alongside the nine selected200 triplets; they
are retained experimental states, not additional chosen models. Exact private reload outputs, resumed parameters/Adam moments,
finite values and CPU RNG preservation are recorded in the selected reports.

## Load and check

Keep each checkpoint triplet together. Externally select the manifest SHA256
and run `python -I -B verify_reconstruction_release.py --directory .
--expected-manifest-sha256 SELECTED_SHA256`. The stdlib checker verifies exact
files, seals, F32 tensor shapes, finite values, saved Adam steps/moments and
canonical serialized-value digests. It creates no model and performs no
numerical forward/optimizer call. Compact summaries bind the original reports;
latent/reconstruction row tables and data banks are excluded.

The exact included `train_reconstruction.py::load_checkpoint(torch,
checkpoint_file_binding, selected_config)` is the numerical load route.
Its original selected workers used Torch2.13.0+cu130 and safetensors0.7.0 while
explicitly computing on CPU. Select the checkpoint JSON file SHA independently
and the exact config from the manifest, preserving the triplet's local filenames.
The loader verifies implementation SHA, tensors, Adam and normalization; it
does not reopen the historical bank. A numerical download/restore smoke was
not executed by the publication preparer.

```python
# First verify/load the exact manifest-pinned helper source bytes.
model, adam, checkpoint = helper.load_checkpoint(torch, selected_file_binding, selected_config)
with torch.inference_mode():
    mean = torch.tensor(checkpoint['normalization']['mean'], dtype=torch.float32)
    rms = checkpoint['normalization']['rms']
    latent = model['encoder']((native_vectors - mean) / rms)
    reconstructed = model['decoder'](latent) * rms + mean
```

The 64 controlled English compositions have32 TRAIN and32 DEV rows.
All remain exposed authored diagnostics with no independent semantic reviews.
Dense bottlenecks32/64 meet or exceed the TRAIN centered rank bound31;
compare effective-rank PCA, raw vectors and the frozen TRAIN mean.

TRAIN reconstruction error is an engineering measure. Raw identity MSE is0
without compression. Error reduction against an untrained network establishes
no held-out reconstruction, retrieval quality, text meaning, source fidelity,
prover truth or logic-family coverage. Different widths/capacities prevent
using cross-lane MSE as a semantic ranking. All five semantic/decoder masks
remain0; semantic/contrastive fit authority, qualification, fidelity and proof
authority remain false. Reconstruction-only training is explicitly authorized.
No human identity/independence or relation admission is authenticated here.

Authorial source/checkpoints use AGPL-3.0. Upstream embedding backbones retain
their licenses and are neither copied nor relicensed by this release.
'''
    publish('README.md', text.encode())
    for lane in LANES:
        card = f'# {lane}: experimental source-vector reconstruction\n\n'
        card += '| Seed | Initial TRAIN MSE | Selected200 TRAIN MSE |\n| ---: | ---: | ---: |\n'
        for arm in arms:
            if arm['lane_id'] == lane:
                card += f'| {arm["seed"]} | {arm["initial_mse"]:.9g} | {arm["final_mse"]:.9g} |\n'
        card += '\nRaw identity MSE is0 without compression. These are TRAIN-only scalar errors, not held-out or semantic-quality measurements. All semantic/decoder masks stay0.\n'
        publish('cards/' + lane + '.md', card.encode())
    files = []
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            data = path.read_bytes()
            files.append({'path': str(path.relative_to(directory)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    manifest = {'schema': 'source-vector-reconstruction-public-release/v1', 'repo_id': 'Publicus/legal-ir-autoencoder',
                'prefix': PREFIX, 'source_cohort_rows': 64, 'train_rows': 32, 'train_groups': 8,
                'development_rows_available': 32, 'independent_semantic_reviews': 0,
                'scope': 'exposed_authored_composition_source_reconstruction_only',
                'prefix_identity_date': '2026-10-05', 'archival_unselected_checkpoint_triplets': 27,
                'selected_checkpoint_triplets': 9, 'all_new_saved_checkpoint_triplets': 36, 'arms': arms, 'files': files, 'selected_updates': 1800, 'scratch_comparison_updates': 27,
                'actual_historical_updates': 1827, 'historical_training_completed': True,
                'model_loads_by_preparer': 0, 'optimizer_updates_by_preparer': 0, 'model_calls_by_preparer': 0,
                'vector_row_tables_or_bank_bodies_included': False, 'numerical_download_restore_executed': False,
                'semantic_fit_authorized': False, 'contrastive_fit_authorized': False,
                'source_fidelity_established': False, 'proof_authority': False, 'qualified': False, 'semantic_gold_created': False}
    manifest_reference = publish('release_manifest.json', sealed(manifest))
    files.append({'path': 'release_manifest.json', 'bytes': manifest_reference['bytes'], 'sha256': manifest_reference['sha256']})
    _, preparation_reference = unbound_file(Path(__file__).resolve())
    inputs[preparation_reference['path']] = preparation_reference
    _, publisher_reference = unbound_file(WORK / 'publish_expanded_release.py')
    inputs[publisher_reference['path']] = publisher_reference
    for reference in inputs.values():
        read_selected(reference)
    upload_plan = {'schema': 'append-only-HF-publication-plan/v1', 'repo_id': 'Publicus/legal-ir-autoencoder', 'repo_type': 'model',
                   'prefix': PREFIX, 'directory': str(directory), 'files': files, 'original_input_bindings': list(inputs.values()),
                   'public_manifest_binding': manifest_reference, 'create_if_missing': False,
                   'tracking_metadata_policy': 'allow_only_exact_selected_path_LFS_additions',
                   'new_model_calls': 0, 'new_optimizer_updates': 0, 'qualified': False,
                   'source_fidelity_established': False, 'proof_authority': False}
    return put(WORK / 'expanded-publication-plan-01.json', sealed(upload_plan)), manifest_reference


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-selection', type=Path, required=True)
    parser.add_argument('--expected-training-selection-sha256', required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    path = args.training_selection.absolute()
    require(path.is_file(), 'externally selected training selection required')
    reference = {'path': str(path), 'bytes': path.stat().st_size, 'sha256': args.expected_training_selection_sha256}
    plan, manifest = prepare(reference, args.output_directory)
    print(json.dumps({'plan': plan, 'manifest': manifest}, sort_keys=True))
