"""Seal an explicit public evidence inventory; no recursive discovery or authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path(__file__).absolute().parent
MAX_FILES = 4096
MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def signature(info):
    return tuple(getattr(info, key) for key in ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def named(path):
    if type(path) is not str:
        raise ValueError('literal named path required')
    p = Path(path)
    if not p.is_absolute() or str(p) != path or p.resolve(strict=True) != p or not p.is_relative_to(ROOT):
        raise ValueError('one canonical named successor public path required')
    parts = p.relative_to(ROOT).parts
    if '.git' in parts or '__pycache__' in parts or parts[:2] == ('checkout', 'data') or p.suffix in {'.duckdb', '.db', '.parquet', '.key', '.pyc'}:
        raise ValueError('private database/key/Git/cache bodies are excluded')
    return p


def capture(path, *, body=False):
    p = named(path)
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 <= before.st_size <= MAX_FILE_BYTES:
            raise ValueError('bounded single-link public regular file required')
        digest = hashlib.sha256(); count = 0; chunks = []
        if body and before.st_size > 8 * 1024 * 1024:
            raise ValueError('public JSON body exceeds bound')
        while True:
            block = os.read(fd, 65536)
            if not block:
                break
            count += len(block)
            if count > MAX_FILE_BYTES:
                raise ValueError('file bound exceeded')
            digest.update(block)
            if body:
                chunks.append(block)
        if count != before.st_size or signature(before) != signature(os.fstat(fd)) or signature(before) != signature(p.lstat()):
            raise ValueError('original public file changed during capture')
        fresh = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            if signature(os.fstat(fresh)) != signature(before):
                raise ValueError('fresh public file identity differs')
            second = hashlib.sha256(); second_count = 0
            while True:
                block = os.read(fresh, 65536)
                if not block:
                    break
                second_count += len(block); second.update(block)
                if second_count > count:
                    raise ValueError('fresh public file exceeds original byte bound')
            if second_count != count or second.digest() != digest.digest() or signature(os.fstat(fresh)) != signature(before) or signature(p.lstat()) != signature(before):
                raise ValueError('fresh public file bytes differ')
        finally:
            os.close(fresh)
        return {'path': path, 'bytes': count, 'sha256': digest.hexdigest()}, b''.join(chunks) if body else None
    finally:
        os.close(fd)


def decode(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate JSON field')
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('finite JSON required')))


def manifest_for(config_path):
    config_pin, raw = capture(config_path, body=True)
    cfg = decode(raw)
    if type(cfg) is not dict or set(cfg) != {'schema', 'files', 'qualified_reports'} or cfg['schema'] != 'terminal-dispatch-evidence-seal-config@1':
        raise ValueError('closed explicit seal configuration required')
    paths = cfg['files']
    if type(paths) is not list or not paths or len(paths) > MAX_FILES or any(type(p) is not str for p in paths) or paths != sorted(set(paths)):
        raise ValueError('unique sorted explicit inventory required')
    selected = sorted(set([*paths, config_path, str(Path(__file__).absolute())]))
    if len(selected) > MAX_FILES:
        raise ValueError('file census bound exceeded')
    pins = []; total = 0
    for path in selected:
        pin, _ = capture(path); pins.append(pin); total += pin['bytes']
        if total > MAX_TOTAL_BYTES:
            raise ValueError('total explicit file byte bound exceeded')
    reports = cfg['qualified_reports']
    by_path = {pin['path']: pin for pin in pins}
    if type(reports) is not list or not reports or len(reports) > 64 or len(set(reports)) != len(reports):
        raise ValueError('bounded unique qualification reports required')
    for path in reports:
        if path not in selected:
            raise ValueError('qualification report absent from sealed inventory')
        report_pin, raw = capture(path, body=True)
        if report_pin != by_path[path]:
            raise ValueError('qualification report changed after inventory capture')
        value = decode(raw)
        if type(value) is not dict or value.get('qualified') is not True:
            raise ValueError('selected report has not qualified')
    if capture(config_path)[0] != config_pin:
        raise ValueError('configuration changed during seal')
    return {'schema': 'terminal-dispatch-evidence-integrity-seal@1', 'qualified': True,
        'files': pins, 'file_count': len(pins), 'file_bytes': total,
        'file_set_sha256': hashlib.sha256(wire(pins)).hexdigest(),
        'config': config_pin, 'qualified_reports': reports,
        'recursive_discovery': False, 'fresh_reopen_required': True,
        'cryptographic_authority_conferred': False, 'native_authority_reconstructed': False,
        'loaded_code_or_dependency_closure_attested': False,
        'worker_observation_emitter_origin_proved': False,
        'source_to_model_equivalence_proved': False, 'convergence_proved': False,
        'training_steps': 0, 'full_task_satisfaction': False}


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--config', required=True); args.add_argument('--manifest', required=True)
    args.add_argument('--verify', action='store_true'); a = args.parse_args()
    value = manifest_for(a.config)
    raw = wire(value) + b'\n'
    target = Path(a.manifest)
    if not target.is_absolute() or str(target) != a.manifest or target.parent != ROOT:
        raise ValueError('one literal successor-root manifest required')
    if a.verify:
        pin, actual = capture(a.manifest, body=True)
        if actual != raw:
            raise ValueError('sealed inventory changed')
    else:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        pin = capture(a.manifest)[0]
    print(json.dumps({'qualified': True, 'verified': a.verify, 'files': value['file_count'], 'bytes': value['file_bytes'], 'manifest': pin, 'file_set_sha256': value['file_set_sha256']}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'qualified': False, 'error_type': type(error).__name__, 'error': str(error)}))
        raise SystemExit(1)
