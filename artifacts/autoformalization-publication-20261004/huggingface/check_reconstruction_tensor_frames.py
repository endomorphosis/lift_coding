"""Small offline framing/corruption checks; creates no tensors, models or weights."""

import hashlib
import json
import os
import struct
from pathlib import Path

WORK = Path(__file__).resolve().parent
CHECKER_SHA = '21816a6540b8e02f7dadcdf7efdf04c071f62b9e90e29199e8e878bcb9cc59e2'


def main():
    source = WORK / 'verify_reconstruction_release.py'
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == CHECKER_SHA
    namespace = {'__name__': '_selected_frame_checker', '__file__': str(source)}
    exec(compile(data, str(source), 'exec'), namespace)
    raw, parse = namespace['raw'], namespace['tensor_values']
    checked = []

    def frame(header, body):
        encoded = raw(header)
        return struct.pack('<Q', len(encoded)) + encoded + body

    body = struct.pack('<fff', 1.25, -0.5, 200.)
    valid = {'matrix': {'dtype': 'F32', 'shape': [1, 2], 'data_offsets': [0, 8]},
             'step': {'dtype': 'F32', 'shape': [], 'data_offsets': [8, 12]}}
    values = parse(frame(valid, body))
    assert values['matrix']['nested'] == [[1.25, -0.5]] and values['step']['nested'] == 200.
    checked.append('valid_F32_matrix_and_scalar_serialization')

    def reject(name, payload):
        try:
            parse(payload)
        except ValueError:
            checked.append(name)
        else:
            raise AssertionError(name + ' was accepted')

    def changed(field, value):
        header = json.loads(raw(valid))
        header['matrix'][field] = value
        return frame(header, body)

    reject('overlapping_tensor_extents', changed('data_offsets', [4, 12]))
    reject('tensor_byte_length_shape_mismatch', changed('data_offsets', [0, 4]))
    reject('non_F32_dtype', changed('dtype', 'F64'))
    reject('boolean_tensor_dimension', changed('shape', [True, 2]))
    reject('unbound_body_suffix', frame(valid, body + b'0000'))
    reject('nonfinite_F32_payload', frame(valid, struct.pack('<fff', 1.25, float('nan'), 200.)))
    reject('truncated_header', struct.pack('<Q', 999) + b'{}')
    encoded = b'{"x":{"dtype":"F32","dtype":"F32","shape":[1],"data_offsets":[0,4]}}'
    reject('duplicate_header_key', struct.pack('<Q', len(encoded)) + encoded + struct.pack('<f', 1.))
    header = {'matrix': {'dtype': 'F32', 'shape': [1, 2], 'data_offsets': [4, 12]}}
    reject('unbound_prefix_gap', frame(header, body))
    result = {'schema': 'reconstruction-serialization-offline-fixture/v1', 'checks_passed': checked,
              'check_count': len(checked), 'checker_source_sha256': CHECKER_SHA,
              'model_loads': 0, 'model_calls': 0, 'optimizer_updates': 0, 'ML_library_imports': 0,
              'numerical_runtime_restore_executed': False, 'qualified': False, 'source_fidelity_established': False}
    result['content_sha256'] = hashlib.sha256(raw(result)).hexdigest()
    encoded = raw(result) + b'\n'
    target = WORK / 'reconstruction_tensor_frame_fixture.json'
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'checks': len(checked), 'receipt': {'path': str(target), 'bytes': len(encoded),
                                                        'sha256': hashlib.sha256(encoded).hexdigest()}}))


if __name__ == '__main__':
    main()
