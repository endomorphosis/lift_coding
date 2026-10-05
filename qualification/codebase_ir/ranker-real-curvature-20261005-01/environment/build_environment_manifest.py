"""Freeze a conservative source-import closure after isolated cache hydration.

Uses filesystem/JSON reads only: no Lean/Lake/import probe, build, or download.
The source parser overapproximates imports; it does not claim a runtime-open
trace. Missing source or required compiled modules refuse the manifest.
Dependency inputs are external read-only setup artifacts, outside the16MiB
private proof workspace; native proof limits are not modified here.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_FILES = 200000
MAX_EXTERNAL_BYTES = 16 * 1024**3
MAX_MANIFEST_BYTES = 64 * 1024**2
MAX_SOURCE_BYTES = 4 * 1024**2


def need(value, message):
    if value is not True:
        raise ValueError(message)


def signature(value):
    return tuple(getattr(value, 'st_' + key) for key in
                 ('dev', 'ino', 'mode', 'size', 'mtime_ns', 'ctime_ns'))


def read_pin(path, retain=False):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path, 'canonical regular source required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode), 'regular dependency file required')
        if retain:
            need(before.st_size <= MAX_SOURCE_BYTES, 'source/metadata file bound')
        digest, size, blocks = hashlib.sha256(), 0, []
        while block := os.read(fd, 1024**2):
            digest.update(block)
            size += len(block)
            if retain:
                blocks.append(block)
        need(size == before.st_size and signature(before) == signature(os.fstat(fd)) ==
             signature(path.lstat()), 'file changed during closure capture')
        return {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}, b''.join(blocks)
    finally:
        os.close(fd)


def code_without_comments(text):
    result, index, depth, quoted = [], 0, 0, False
    while index < len(text):
        pair, char = text[index:index + 2], text[index]
        if depth:
            if pair == '/-':
                depth += 1
                index += 2
            elif pair == '-/':
                depth -= 1
                index += 2
            else:
                result.append('\n' if char == '\n' else ' ')
                index += 1
        elif quoted:
            if char == '\\':
                index += 2
            elif char == '"':
                quoted = False
                index += 1
            else:
                result.append('\n' if char == '\n' else ' ')
                index += 1
        elif pair == '/-':
            result.append(' ')
            depth = 1
            index += 2
        elif pair == '--':
            end = text.find('\n', index)
            index = len(text) if end < 0 else end
        elif char == "'" and index + 2 < len(text) and text[index + 2] == "'":
            result.append(' ')
            index += 3
        elif char == "'" and text[index + 1:index + 2] == '\\':
            end = index + 1
            while end < len(text):
                if text[end] == '\\':
                    end += 2
                elif text[end] == "'":
                    break
                else:
                    end += 1
            need(end < len(text), 'unterminated character literal')
            result.append(' ')
            index = end + 1
        elif char == '"':
            result.append(' ')
            quoted = True
            index += 1
        else:
            result.append(char)
            index += 1
    need(depth == 0 and not quoted, 'unterminated source comment/string')
    return ''.join(result)


def imports(raw):
    code = code_without_comments(raw.decode('utf-8'))
    result = []
    for line in code.splitlines():
        match = re.match(r'^\s*(?:(?:public|private|meta)\s+)*import\s+(.+?)\s*$', line)
        if match:
            names = match.group(1).split()
            if names and names[0] == 'all':
                names = names[1:]
            need(len(names) > 0, 'empty import declaration')
            for name in names:
                need(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_\'.]*', name) is not None,
                     'unsupported import syntax: ' + name)
                result.append(name)
    return result


def detached_revision(root):
    git = root / '.git'
    if git.is_file():
        directive = git.read_text().strip()
        need(directive.startswith('gitdir: '), 'unsupported Git metadata')
        git = (root / directive[8:]).resolve()
    head = (git / 'HEAD').read_text().strip()
    if head.startswith('ref: '):
        ref = head[5:]
        candidate = git / ref
        if candidate.is_file():
            head = candidate.read_text().strip()
        else:
            candidates = [line.split()[0] for line in (git / 'packed-refs').read_text().splitlines()
                          if line and not line.startswith(('#', '^')) and line.split()[1] == ref]
            need(len(candidates) == 1, 'Git revision metadata missing')
            head = candidates[0]
    need(re.fullmatch('[0-9a-f]{40}', head) is not None, 'exact source revision required')
    return head


def build(*, mathlib, toolchain, expected_mathlib_revision, target_imports, source_paths,
          output, full_core_fallback=False):
    output = Path(output)
    need(output.is_absolute() and output.parent.resolve(strict=True) == output.parent,
         'canonical absolute output parent required')
    mathlib, toolchain = map(lambda p: Path(p).resolve(strict=True), (mathlib, toolchain))
    need(not output.exists() and output.name.endswith('.json'), 'new manifest output required')
    need(detached_revision(mathlib) == expected_mathlib_revision, 'Mathlib revision mismatch')
    files, byte_count = {}, 0

    def add(path, retain=False):
        nonlocal byte_count
        descriptor, raw = read_pin(path, retain)
        if descriptor['path'] not in files:
            files[descriptor['path']] = descriptor
            byte_count += descriptor['bytes']
            need(len(files) <= MAX_FILES and byte_count <= MAX_EXTERNAL_BYTES, 'external closure read profile exceeded')
        else:
            need(files[descriptor['path']] == descriptor, 'dependency changed during capture')
        return descriptor, raw

    toolchain_pin, declared = add(mathlib / 'lean-toolchain', True)
    declaration = declared.decode().strip()
    header_pin, header = add(toolchain / 'include/lean/version.h', True)
    version = re.search(r'#define LEAN_VERSION_STRING "([^"]+)"', header.decode())
    need(version is not None and declaration == 'leanprover/lean4:v' + version[1], 'source/toolchain version mismatch')
    lean, _ = add(toolchain / 'bin/lean')
    add(toolchain / 'bin/lake')
    add(toolchain / 'bin/leantar')
    for name in ('libInit_shared.so', 'libleanshared.so', 'libleanshared_1.so', 'libleanshared_2.so'):
        add(toolchain / 'lib/lean' / name)
    root_manifest, raw = add(mathlib / 'lake-manifest.json', True)
    packages = json.loads(raw)
    need(packages['name'] == 'mathlib', 'Mathlib dependency manifest required')
    add(mathlib / 'lakefile.lean')
    roots = [(mathlib, mathlib / '.lake/build/lib/lean', 'mathlib'),
             (toolchain / 'src/lean', toolchain / 'lib/lean', 'native_core')]
    dependency_rows = []
    for package in packages['packages']:
        need(package['type'] == 'git' and package.get('subDir') is None, 'unsupported dependency layout')
        root = mathlib / packages['packagesDir'] / package['name']
        need(root.is_dir() and detached_revision(root) == package['rev'], 'dependency source/revision unavailable')
        build_root = root / '.lake/build/lib/lean'
        roots.append((root, build_root, package['name']))
        metadata = []
        for name in ('lean-toolchain', package['configFile'], package['manifestFile']):
            path = root / name
            if path.is_file():
                metadata.append(add(path)[0])
        dependency_rows.append({'name': package['name'], 'revision': package['rev'],
                                'source_root': str(root), 'compiled_root': str(build_root), 'metadata': metadata})
    queue, selected_sources = list(target_imports) + ['Init'], []
    for path in source_paths:
        descriptor, raw = add(Path(path).resolve(strict=True), True)
        selected_sources.append(descriptor)
        queue.extend(imports(raw))
    modules, missing = {}, []
    while queue:
        name = queue.pop()
        if name in modules:
            continue
        relative = Path(*name.split('.'))
        found = [(root, compiled, label) for root, compiled, label in roots
                 if (root / relative.with_suffix('.lean')).is_file()]
        need(len(found) == 1, 'missing/ambiguous source module: ' + name)
        root, compiled, label = found[0]
        source_descriptor, raw = add(root / relative.with_suffix('.lean'), True)
        stem = compiled / relative
        required = Path(str(stem) + '.olean')
        if not required.is_file():
            missing.append(name)
            continue
        companions = []
        for suffix in ('.olean', '.olean.private', '.olean.server', '.ir'):
            path = Path(str(stem) + suffix)
            if path.is_file():
                companions.append(add(path)[0])
        modules[name] = {'module': name, 'package': label, 'source': source_descriptor, 'compiled': companions}
        queue.extend(imports(raw))
    need(not missing, 'required compiled dependency unavailable: ' + ', '.join(missing[:12]))
    if full_core_fallback:
        for path in sorted((toolchain / 'lib/lean').rglob('*')):
            if path.is_file() and (path.name.endswith(('.olean', '.olean.private', '.olean.server', '.ir'))):
                add(path)
    lean_path = [str(root) for _, root, _ in roots if root.is_dir()]
    need(len(lean_path) == len(set(lean_path)), 'duplicate library roots')
    result = {'schema': 'ranker-real-curvature-lean-environment@1', 'lean_executable': lean,
        'lean_path': lean_path, 'files': [files[path] for path in sorted(files)],
        'mathlib_revision': expected_mathlib_revision, 'declared_toolchain': declaration,
        'toolchain_header': header_pin, 'mathlib_toolchain': toolchain_pin,
        'mathlib_lake_manifest': root_manifest, 'packages': dependency_rows,
        'requested_imports': list(target_imports), 'selected_proof_sources': selected_sources,
        'source_import_modules': [modules[name] for name in sorted(modules)],
        'external_file_count': len(files), 'external_file_bytes': byte_count,
        'external_read_profile': {'max_files': MAX_FILES, 'max_bytes': MAX_EXTERNAL_BYTES,
                                  'max_manifest_bytes': MAX_MANIFEST_BYTES},
        'full_core_companion_fallback_selected': full_core_fallback,
        'closure_scope': 'source-declared transitive imports plus implicit Init and compiled companions; toolchain shared runtime',
        'actual_runtime_file_opens_traced': False, 'atomic_source_snapshot_claimed': False,
        'all_dependencies_readonly_required_by_root_before_proof_execution': True,
        'private_native_workspace_and_retention_limits_changed': False,
        'native_prover_calls': 0, 'Lean_or_Lake_import_probes': 0, 'network_calls': 0,
        'proof_authority': False, 'whole_source_equivalence_proved': False,
        'optimizer_convergence_proved': False, 'planner_activation': False,
        'official_benchmark_score': None, 'full_task_satisfaction': 'unknown'}
    for row in files.values():
        need(read_pin(row['path'])[0] == row, 'environment source changed after capture')
    payload = (json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    need(len(payload) <= MAX_MANIFEST_BYTES, 'environment profile manifest byte bound')
    with output.open('xb') as stream:
        stream.write(payload)
    return read_pin(output)[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mathlib', type=Path, required=True)
    parser.add_argument('--toolchain', type=Path, required=True)
    parser.add_argument('--expected-mathlib-revision', required=True)
    parser.add_argument('--import', dest='target_imports', action='append', default=[])
    parser.add_argument('--source', dest='source_paths', type=Path, action='append', default=[])
    parser.add_argument('--full-core-fallback', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(mathlib=args.mathlib, toolchain=args.toolchain,
        expected_mathlib_revision=args.expected_mathlib_revision, target_imports=args.target_imports,
        source_paths=args.source_paths, output=args.output, full_core_fallback=args.full_core_fallback)
    print(json.dumps(result, sort_keys=True))
