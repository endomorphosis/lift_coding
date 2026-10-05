"""Verify selected reconstruction tensors with stdlib only; no numerical model restore."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

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


def read(path):
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'nonsymlink input required')
    require(path.is_file() and 0 < path.stat().st_size <= 32 * 1024 ** 2, 'bounded ordinary input required')
    return path.read_bytes()


def checked_seal(value):
    require(type(value) is dict and hashlib.sha256(raw({k: v for k, v in value.items() if k != 'content_sha256'})).hexdigest()
            == value.get('content_sha256'), 'JSON seal differs')


def nested(values, shape):
    if not shape:
        require(len(values) == 1, 'scalar tensor shape differs')
        return values[0]
    if len(shape) == 1:
        return list(values)
    stride = math.prod(shape[1:])
    return [nested(values[i * stride:(i + 1) * stride], shape[1:]) for i in range(shape[0])]


def tensor_values(data):
    require(len(data) >= 8, 'safetensors framing truncated')
    size = struct.unpack('<Q', data[:8])[0]
    require(2 <= size <= 64 * 1024 and 8 + size <= len(data), 'bounded safetensors header required')
    header = decode(data[8:8 + size])
    require(type(header) is dict and 1 <= len(header) <= 32 and '__metadata__' not in header,
            'closed bounded tensor header required')
    body = memoryview(data)[8 + size:]
    intervals = []
    result = {}
    for name, spec in header.items():
        require(type(name) is str and type(spec) is dict and set(spec) == {'dtype', 'shape', 'data_offsets'}
                and spec['dtype'] == 'F32', 'selected CPU float32 serialization required')
        shape = spec['shape']
        require(type(shape) is list and len(shape) <= 2 and all(type(v) is int and 0 <= v <= 2048 for v in shape),
                'bounded tensor shape required')
        count = math.prod(shape)
        offsets = spec['data_offsets']
        require(type(offsets) is list and len(offsets) == 2 and all(type(v) is int for v in offsets),
                'closed tensor offsets required')
        start, stop = offsets
        require(0 <= start <= stop <= len(body) and stop - start == count * 4 and count <= 2_000_000,
                'tensor byte extent differs')
        values = [v[0] for v in struct.iter_unpack('<f', body[start:stop])]
        require(all(math.isfinite(v) for v in values), 'nonfinite serialized tensor rejected')
        result[name] = {'shape': shape, 'values': values, 'nested': nested(values, shape)}
        intervals.append((start, stop))
    cursor = 0
    for start, stop in sorted(intervals):
        require(start == cursor, 'tensor overlap/gap rejected')
        cursor = stop
    require(cursor == len(body), 'unbound tensor suffix rejected')
    return result


def model_shapes(architecture):
    d, h, z = architecture
    return {'encoder.0.weight': [h, d], 'encoder.0.bias': [h], 'encoder.2.weight': [z, h], 'encoder.2.bias': [z],
            'decoder.0.weight': [h, z], 'decoder.0.bias': [h], 'decoder.2.weight': [d, h], 'decoder.2.bias': [d]}


def checkpoint_values(directory, checkpoint, expected_config):
    checked_seal(checkpoint)
    require(checkpoint['schema'] == 'source-vector-reconstruction-checkpoint/v1'
            and checkpoint['config'] == expected_config and type(checkpoint['optimizer_steps']) is int
            and checkpoint['optimizer_steps'] == 200, 'fixed selected200 checkpoint required')
    config = checkpoint['config']
    require(config['lane_id'] in LANES and config['architecture'] == LANES[config['lane_id']]
            and type(config['seed']) is int and config['seed'] in (1729, 1730, 1731)
            and config['dtype'] == 'float32' and config['device'] == 'cpu', 'selected AE profile differs')
    require(checkpoint['masks'] == dict.fromkeys(MASKS, 0)
            and all(type(v) is int for v in checkpoint['masks'].values()), 'semantic masks forbidden')
    require(all(checkpoint[k] is False for k in ('semantic_fit_authorized', 'contrastive_fit_authorized',
                'source_fidelity_established', 'proof_authority', 'qualified')), 'checkpoint authority forbidden')
    require(checkpoint['reconstruction_fit_scope'] == 'selected_TRAIN_vectors_only', 'fit scope differs')
    norm = checkpoint['normalization']
    require(set(norm) == {'recipe', 'mean', 'rms'} and norm['recipe'] == 'train_coordinate_mean_and_global_rms/v1'
            and type(norm['mean']) is list and len(norm['mean']) == config['architecture'][0]
            and all(type(v) in (int, float) and math.isfinite(v) for v in norm['mean'])
            and type(norm['rms']) in (int, float) and math.isfinite(norm['rms']) and norm['rms'] > 1e-8
            and hashlib.sha256(raw(norm)).hexdigest() == config['normalization_sha256'], 'normalization identity differs')
    tables = {}
    for field, filename in (('model_file', 'model.safetensors'), ('optimizer_file', 'optimizer.safetensors')):
        selected = checkpoint[field]
        require(set(selected) == {'path', 'sha256', 'bytes'} and selected['path'] == filename, 'fixed tensor path required')
        data = read(directory / filename)
        require(len(data) == selected['bytes'] and hashlib.sha256(data).hexdigest() == selected['sha256'], 'tensor file pin differs')
        tables[field] = tensor_values(data)
    shapes = model_shapes(config['architecture'])
    model = tables['model_file']
    require(set(model) == set(shapes) and all(model[k]['shape'] == shape for k, shape in shapes.items()), 'model shape inventory differs')
    require(hashlib.sha256(raw({k: v['nested'] for k, v in model.items()})).hexdigest() == checkpoint['model_state_sha256'],
            'serialized model value digest differs')
    optimizer = tables['optimizer_file']
    require(set(optimizer) == {name + '/' + field for name in shapes for field in ('step', 'exp_avg', 'exp_avg_sq')},
            'Adam tensor inventory differs')
    for name, shape in shapes.items():
        step = optimizer[name + '/step']
        require(step['shape'] == [] and step['values'] == [200.0], 'Adam step differs')
        require(optimizer[name + '/exp_avg']['shape'] == shape and optimizer[name + '/exp_avg_sq']['shape'] == shape
                and all(v >= 0 for v in optimizer[name + '/exp_avg_sq']['values']), 'Adam moment shape/domain differs')
    require(hashlib.sha256(raw({k: v['nested'] for k, v in optimizer.items()})).hexdigest()
            == checkpoint['optimizer_state_sha256'], 'serialized Adam value digest differs')
    return sum(len(v['values']) for table in tables.values() for v in table.values())


def verify(directory, expected_manifest_sha256):
    directory = directory.absolute()
    data = read(directory / 'release_manifest.json')
    require(hashlib.sha256(data).hexdigest() == expected_manifest_sha256, 'external manifest pin differs')
    manifest = decode(data)
    checked_seal(manifest)
    require(manifest['schema'] == 'source-vector-reconstruction-public-release/v1', 'release schema differs')
    seen = set()
    for item in manifest['files']:
        path = Path(item['path'])
        require(not path.is_absolute() and '..' not in path.parts and str(path) == item['path'] and item['path'] not in seen,
                'unique safe release path required')
        seen.add(item['path'])
        payload = read(directory / path)
        require(len(payload) == item['bytes'] and hashlib.sha256(payload).hexdigest() == item['sha256'], 'release file pin differs')
    values = 0
    order = [(lane, seed) for lane in LANES for seed in (1729, 1730, 1731)]
    require([(r['lane_id'], r['seed']) for r in manifest['arms']] == order, 'complete ordered9 arms required')
    for arm in manifest['arms']:
        path = directory / arm['checkpoint_path']
        checkpoint = decode(read(path))
        require(checkpoint['config']['helper_binding']['sha256'] == hashlib.sha256(read(directory / 'train_reconstruction.py')).hexdigest(),
                'loader source pin differs')
        values += checkpoint_values(path.parent, checkpoint, arm['config'])
    return {'schema': 'source-reconstruction-public-integrity-check/v1', 'files_verified': len(seen), 'selected_checkpoints_verified': 9,
            'finite_F32_serialized_values_checked': values, 'model_loads': 0, 'model_calls': 0, 'optimizer_updates': 0,
            'serialized_tensor_value_digests_recomputed': True, 'numerical_runtime_restore_executed': False,
            'semantic_or_proof_authority_established': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--expected-manifest-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.expected_manifest_sha256), sort_keys=True))
