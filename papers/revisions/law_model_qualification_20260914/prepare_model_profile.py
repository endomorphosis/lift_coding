#!/usr/bin/env python3
"""Bind existing local weights/runtime before a bounded qualification launch.

This hashes existing files. It downloads nothing and starts no model or service.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AF = ROOT / 'papers/revisions/autoformalization_empirical_20260914'


def fingerprint(path):
    s = path.stat()
    return {'device': s.st_dev, 'inode': s.st_ino, 'bytes': s.st_size,
            'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns}


def binding(path):
    path = path.resolve(strict=True)
    before = fingerprint(path)
    start = time.monotonic()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if before != fingerprint(path):
        raise RuntimeError('File changed while hashing: ' + str(path))
    return {'path': str(path), 'sha256': digest, **before,
            'hash_wall_seconds': time.monotonic() - start}


def main():
    output = HERE / 'static_model_profile.json'
    if output.exists():
        raise RuntimeError('A profile already exists; preserve it and review before any new profile')
    previous = json.loads((AF / 'assistance/preflight.json').read_text())
    identity_path = AF / 'supplement_staging/natural/MODEL_IDENTITY.json'
    identity = json.loads(identity_path.read_text())
    model = binding(Path(previous['model']))
    if model['sha256'] != identity['model_file_sha256'] or model['bytes'] != identity['model_file_bytes']:
        raise RuntimeError('Actual local weights differ from the previously verified immutable model identity')
    binary = binding(Path(previous['binary']))
    template_source = AF / 'assistance/leanstral_v15.jinja'
    template = HERE / 'leanstral_v15.jinja'
    if template.exists():
        raise RuntimeError('Fresh template copy required')
    shutil.copyfile(template_source, template)
    template_binding = binding(template)
    if template_binding['sha256'] != previous['chat_template_sha256']:
        raise RuntimeError('Explicit text framing changed')
    linked = subprocess.run(['/usr/bin/ldd', binary['path']], capture_output=True, text=True, timeout=10)
    if linked.returncode != 0 or 'not found' in linked.stdout:
        raise RuntimeError('Server shared-library dependencies unresolved')
    libraries = {}
    for line in linked.stdout.splitlines():
        match = re.search(r'(?:=>\s+)?(/[^\s]+)\s+\(', line)
        if match:
            path = Path(match[1]).resolve(strict=True)
            libraries[str(path)] = binding(path)
    cache_source = Path.home() / '.cache/ipfs_accelerate_py/llama_cpp/source'
    git = subprocess.run(['git', '-C', str(cache_source), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=5)
    dirty = subprocess.run(['git', '-C', str(cache_source), 'status', '--porcelain=v1', '--untracked-files=no'],
                           capture_output=True, text=True, timeout=5)
    profile = {'schema': 'law-static-leanstral-profile/v1',
               'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'scope': 'Existing actual weights and runtime identity; no live model qualification or scientific outcome',
               'model_identity': identity, 'model_identity_source': binding(identity_path),
               'actual_weights': model, 'server_binary': binary, 'linked_libraries': libraries,
               'linker_observation': {'argv': ['/usr/bin/ldd', binary['path']], 'stdout': linked.stdout},
               'source_checkout_observation': {'path': str(cache_source), 'git_returncode': git.returncode,
                    'commit': git.stdout.strip(), 'tracked_dirty_output': dirty.stdout, 'status_returncode': dirty.returncode,
                    'compiled_binary_identity_is_its_actual_sha256': True},
               'tokenizer': {'kind': 'embedded_GGUF', 'bound_by_complete_weights_sha256': model['sha256'],
                             'metadata_observation': binding(AF / 'assistance/local_model_metadata.json')},
               'chat_template': template_binding, 'ephemeral_runner': binding(ROOT / 'scripts/run_leanstral_ephemeral.py'),
               'declared_runtime': {'wall_seconds': 10000, 'startup_seconds': 360,
                    'memory_bytes': 90 * 1024**3, 'reserve_bytes': 12 * 1024**3,
                    'cpus': 4, 'tasks': 128, 'context': 4096, 'gpu': '0', 'gpu_layers': 36,
                    'parallel_slots': 1, 'loopback_host': '127.0.0.1', 'port': 8080,
                    'model_alias': 'leanstral_local', 'keep_warm_across_active_calls': True},
               'decoding': {'temperature': 0, 'seeds': [104729, 104759, 104761],
                            'maximum_input_tokens': 2048, 'maximum_output_tokens': 1024, 'stream': False},
               'model_calls': 0, 'model_service_launched': False, 'scientific_cases_executed': 0}
    with output.open('x') as stream:
        json.dump(profile, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'profile': str(output), 'weights_sha256': model['sha256'],
                      'weights_bytes': model['bytes'], 'weights_hash_wall_seconds': model['hash_wall_seconds'],
                      'linked_library_count': len(libraries), 'model_calls': 0}))


if __name__ == '__main__':
    main()
