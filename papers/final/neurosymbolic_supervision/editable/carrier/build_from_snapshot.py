"""Verify immutable text-carried manuscript sources; optionally compile in /tmp.

This helper never edits a repository output, receipt, original source or release.
It executes only the chosen TeX/BibTeX tools, with shell escape disabled.
"""
import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ref(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': sha(data)}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def safe_relative(value):
    if (not isinstance(value, str) or not value or '\\' in value or '\0' in value
            or PurePosixPath(value).is_absolute() or str(PurePosixPath(value)) != value
            or any(p in {'', '.', '..', '.git'} for p in value.split('/'))):
        raise ValueError('noncanonical source path')
    return Path(value)


def verified_sources(expected_manifest):
    manifest_path = HERE / 'source_manifest.json'
    raw = manifest_path.read_bytes()
    if sha(raw) != expected_manifest:
        raise ValueError('source manifest digest mismatch')
    manifest = json.loads(raw)
    if manifest.get('schema') != 'ns024-text-carried-editable-sources/v1' or len(manifest.get('files', [])) != 24:
        raise ValueError('source manifest schema/count mismatch')
    found, sources = set(), []
    for entry in manifest['files']:
        path, stored = safe_relative(entry['path']), safe_relative(entry['stored_path'])
        if path.as_posix() in found:
            raise ValueError('duplicate materialized source path')
        found.add(path.as_posix())
        source_file = HERE / stored
        if source_file.is_symlink() or not source_file.resolve().is_relative_to(HERE):
            raise ValueError('redirected source input')
        body = source_file.read_bytes()
        if len(body) != entry['stored_bytes'] or sha(body) != entry['stored_sha256']:
            raise ValueError('stored source differs from commitment')
        if entry['encoding'] == 'utf8':
            body.decode('utf-8', errors='strict')
            decoded = body
        elif entry['encoding'] == 'base64-ascii':
            encoded = body.decode('ascii', errors='strict')
            if not encoded.endswith('\n') or '\n' in encoded[:-1]:
                raise ValueError('noncanonical base64 source')
            decoded = base64.b64decode(encoded[:-1], validate=True)
            if base64.b64encode(decoded).decode('ascii') + '\n' != encoded:
                raise ValueError('noncanonical base64 encoding')
        else:
            raise ValueError('unsupported source encoding')
        if len(decoded) != entry['bytes'] or sha(decoded) != entry['sha256']:
            raise ValueError('decoded source differs from original selected source')
        sources.append((path, decoded))
    return manifest, sources


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest-sha256', required=True)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument('--verify-only', action='store_true')
    action.add_argument('--output', type=Path)
    p.add_argument('--pdflatex')
    p.add_argument('--bibtex')
    args = p.parse_args()
    manifest, sources = verified_sources(args.manifest_sha256)
    if args.verify_only:
        print(json.dumps({'verified': True, 'source_files': len(sources),
                          'manifest_sha256': args.manifest_sha256,
                          'decoded_original_source_bytes': sum(len(b) for _, b in sources),
                          'files_written': 0, 'compiler_calls': 0}))
        return 0
    parent = args.output.parent.resolve(strict=True)
    temporary_root = Path(tempfile.gettempdir()).resolve()
    if (not args.output.is_absolute() or args.output.name in {'', '.', '..'}
            or not parent.is_relative_to(temporary_root)
            or any((ancestor / '.git').exists() for ancestor in (parent, *parent.parents))
            or args.output.exists() or args.output.is_symlink()):
        raise ValueError('build output must be a fresh directory beneath the system temporary root')
    out = parent / args.output.name
    pdflatex = args.pdflatex or shutil.which('pdflatex')
    bibtex = args.bibtex or shutil.which('bibtex')
    if not pdflatex or not bibtex:
        raise ValueError('explicit available pdflatex/bibtex tools are required')
    # Keep the pdflatex invocation name: resolving its pdftex symlink would
    # select a different TeX format even though the executable bytes match.
    pdflatex = str(Path(pdflatex).absolute())
    bibtex = str(Path(bibtex).absolute())
    if not Path(pdflatex).is_file() or not Path(bibtex).is_file():
        raise ValueError('compiler path must identify an existing tool')
    out.mkdir(mode=0o700)
    m, e = out / 'source', out / 'execution'
    m.mkdir(); e.mkdir()
    for relative, body in sources:
        target = m / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    (m / 'build').mkdir()
    latex = [pdflatex, '-no-shell-escape', '-interaction=nonstopmode',
             '-halt-on-error', '-file-line-error', '-output-directory=build', 'main.tex']
    commands = [latex, [bibtex, 'build/main'], latex.copy(), latex.copy()]
    record = {'schema': 'ns024-ephemeral-editable-source-build/v1', 'started_at': utc(),
              'source_helper': ref(Path(__file__)), 'manifest': ref(HERE / 'source_manifest.json'),
              'source_bindings': {str(relative): ref(m / relative) for relative, _ in sources},
              'toolchain': [ref(Path(pdflatex)), ref(Path(bibtex))],
              'planned_argv': commands, 'cwd': str(m), 'commands': [],
              'shell_escape_disabled': True, 'native_or_repository_mutation': False,
              'scientific_provider_scorer_reproduction_calls': 0,
              'release_binary_adopted': False}
    (e / 'plan.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    for i, argv in enumerate(commands, 1):
        stdout, stderr = e / f'{i:02}_stdout.log', e / f'{i:02}_stderr.log'
        start, tick, expired = utc(), time.monotonic(), False
        with stdout.open('xb') as so, stderr.open('xb') as se:
            try:
                code = subprocess.run(argv, cwd=m, stdout=so, stderr=se, timeout=120, check=False).returncode
            except subprocess.TimeoutExpired:
                code, expired = None, True
            so.flush(); se.flush(); os.fsync(so.fileno()); os.fsync(se.fileno())
        record['commands'].append({'argv': argv, 'cwd': str(m), 'started_at': start,
                                   'finished_at': utc(), 'elapsed_host_wall_seconds': time.monotonic() - tick,
                                   'exit_code': code, 'timed_out': expired,
                                   'stdout': ref(stdout), 'stderr': ref(stderr)})
        if code != 0:
            break
    record.update(finished_at=utc(), success=len(record['commands']) == 4 and all(c['exit_code'] == 0 for c in record['commands']),
                  source_bytes_unchanged=all((m / relative).read_bytes() == body for relative, body in sources),
                  outputs={str(q.relative_to(m / 'build')): ref(q) for q in (m / 'build').iterdir() if q.is_file()})
    (e / 'result.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'success': record['success'], 'record': ref(e / 'result.json'),
                      'pdf': ref(m / 'build/main.pdf') if (m / 'build/main.pdf').is_file() else None}))
    return 0 if record['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
