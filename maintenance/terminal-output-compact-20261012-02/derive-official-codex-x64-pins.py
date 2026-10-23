#!/usr/bin/env python3
"""Derive native SHA256 pins from fresh integrity-verified official npm bytes."""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
VERSION = '0.160.0'
MAX_PACKAGE_BYTES = 256 * 1024 * 1024
MAX_NATIVE_BYTES = 384 * 1024 * 1024
MAX_UNPACKED_BYTES = 512 * 1024 * 1024
MAX_METADATA_BYTES = 1024 * 1024
MAX_MEMBERS = 128
TARGETS = {'codex', 'codex-code-mode-host'}


def canonical(value):
    return json.dumps(value, sort_keys=True, indent=2) + '\n'


def checked_url(url):
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'registry.npmjs.org'
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError('official HTTPS npm registry URL required')
    return url


def metadata(url):
    with urlopen(Request(checked_url(url), headers={'Accept': 'application/json'}), timeout=20) as response:
        checked_url(response.geturl())
        raw = response.read(MAX_METADATA_BYTES + 1)
    if len(raw) > MAX_METADATA_BYTES:
        raise ValueError('registry metadata exceeds bound')
    return json.loads(raw), {'url': url, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


class LimitedDecompressedReader:
    def __init__(self, source, deadline):
        self.source = source
        self.deadline = deadline
        self.read_bytes = 0

    def read(self, size=-1):
        if time.monotonic() >= self.deadline:
            raise ValueError('archive parsing deadline exceeded')
        if size < 0 or size > 1024 * 1024:
            raise ValueError('unbounded archive parser read refused')
        raw = self.source.read(min(size, MAX_UNPACKED_BYTES - self.read_bytes + 1))
        self.read_bytes += len(raw)
        if self.read_bytes > MAX_UNPACKED_BYTES:
            raise ValueError('archive decompression exceeds bound')
        return raw


def main():
    started = time.monotonic()
    wrapper, wrapper_binding = metadata('https://registry.npmjs.org/@openai/codex/' + VERSION)
    alias = wrapper.get('optionalDependencies', {}).get('@openai/codex-linux-x64')
    expected_alias = 'npm:@openai/codex@' + VERSION + '-linux-x64'
    if wrapper.get('name') != '@openai/codex' or wrapper.get('version') != VERSION or alias != expected_alias:
        raise ValueError('official wrapper metadata does not select expected x64 platform alias')
    package_version = alias.split('@')[-1]
    package, package_binding = metadata('https://registry.npmjs.org/@openai/codex/' + package_version)
    if (package.get('name') != '@openai/codex' or package.get('version') != package_version
            or package.get('os') != ['linux'] or package.get('cpu') != ['x64']):
        raise ValueError('official platform metadata identity differs')
    dist = package['dist']
    if (type(dist.get('fileCount')) is not int or not 1 <= dist['fileCount'] <= MAX_MEMBERS
            or type(dist.get('unpackedSize')) is not int
            or not 1 <= dist['unpackedSize'] <= MAX_UNPACKED_BYTES):
        raise ValueError('official package population exceeds explicit scan bounds')
    integrity = dist['integrity']
    if type(integrity) is not str or not integrity.startswith('sha512-') or ' ' in integrity:
        raise ValueError('single official SHA512 integrity value required')
    expected_integrity = base64.b64decode(integrity[len('sha512-'):], validate=True)
    if len(expected_integrity) != 64:
        raise ValueError('invalid SHA512 integrity digest')
    tarball = checked_url(dist['tarball'])
    deadline = time.monotonic() + 180
    digests = {name: hashlib.new(name) for name in ('sha256', 'sha512', 'sha1')}
    downloaded = 0
    selected, member_count, regular_bytes = {}, 0, 0
    vendor_candidates = []
    with tempfile.NamedTemporaryFile(prefix='.official-codex-x64-', suffix='.tgz', dir=ROOT) as temporary:
        with urlopen(Request(tarball, headers={'Accept': 'application/octet-stream'}), timeout=20) as response:
            checked_url(response.geturl())
            length = response.headers.get('Content-Length')
            if length is not None and int(length) > MAX_PACKAGE_BYTES:
                raise ValueError('compressed official package exceeds 256MiB bound')
            while True:
                if time.monotonic() >= deadline:
                    raise ValueError('download deadline exceeded')
                chunk = response.read(65536)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > MAX_PACKAGE_BYTES:
                    raise ValueError('compressed official package exceeds 256MiB bound')
                temporary.write(chunk)
                for digest in digests.values():
                    digest.update(chunk)
            if length is not None and int(length) != downloaded:
                raise ValueError('Content-Length does not match downloaded package bytes')
        temporary.flush()
        if digests['sha512'].digest() != expected_integrity or digests['sha1'].hexdigest() != dist['shasum']:
            raise ValueError('official registry package integrity mismatch')
        temporary.seek(0)
        with gzip.GzipFile(fileobj=temporary, mode='rb') as decompressed:
            limited = LimitedDecompressedReader(decompressed, deadline)
            with tarfile.open(fileobj=limited, mode='r|') as archive:
                for member in archive:
                    member_count += 1
                    if member_count > MAX_MEMBERS:
                        raise ValueError('archive member count exceeds bound')
                    name = PurePosixPath(member.name)
                    if (name.is_absolute() or '..' in name.parts or member.issym() or member.islnk()
                            or not (member.isfile() or member.isdir())):
                        raise ValueError('unsupported package archive member')
                    if member.isfile():
                        regular_bytes += member.size
                        if member.size < 0 or regular_bytes > MAX_UNPACKED_BYTES:
                            raise ValueError('package member population exceeds size bounds')
                    parts = name.parts
                    if (len(parts) == 5 and parts[:2] == ('package', 'vendor')
                            and parts[3] == 'bin' and parts[4] in TARGETS):
                        vendor_candidates.append({'archive_member': member.name,
                            'bytes': member.size, 'architecture': parts[2], 'name': parts[4]})
                        if (not member.isfile() or parts[2] not in
                                {'x86_64-unknown-linux-musl', 'x86_64-unknown-linux-gnu'}
                                or not member.mode & 0o111 or parts[4] in selected):
                            raise ValueError('ambiguous or unsupported native binary member')
                        if member.size > MAX_NATIVE_BYTES:
                            raise ValueError('selected native exceeds 384MiB bound: ' + member.name + ': ' + str(member.size))
                        native = hashlib.sha256()
                        native_bytes = 0
                        stream = archive.extractfile(member)
                        while True:
                            if time.monotonic() >= deadline:
                                raise ValueError('native hashing deadline exceeded')
                            chunk = stream.read(65536)
                            if not chunk:
                                break
                            native_bytes += len(chunk)
                            if native_bytes > MAX_NATIVE_BYTES:
                                raise ValueError('native member exceeds 384MiB bound')
                            native.update(chunk)
                        if native_bytes != member.size:
                            raise ValueError('native member byte length differs')
                        selected[parts[4]] = {'archive_member': member.name,
                            'bytes': native_bytes, 'mode': member.mode, 'sha256': native.hexdigest(),
                            'architecture': parts[2]}
            decompressed_bytes = limited.read_bytes
    if (set(selected) != TARGETS or regular_bytes != dist['unpackedSize']
            or member_count != dist['fileCount']
            or len({row['architecture'] for row in selected.values()}) != 1):
        raise ValueError('exact official native population or archive census differs')
    report = {
        'schema': 'official-codex-linux-x64-native-pin-derivation@1',
        'codex_version': VERSION, 'platform_package_name': package['name'],
        'platform_package_version': package_version, 'npm_os': package['os'], 'npm_cpu': package['cpu'],
        'wrapper_optional_dependency_name': '@openai/codex-linux-x64', 'wrapper_optional_dependency_alias': alias,
        'registry_metadata': {'wrapper': wrapper_binding, 'platform': package_binding},
        'tarball_url': tarball, 'registry_integrity': integrity, 'registry_shasum': dist['shasum'],
        'tarball_sha256': digests['sha256'].hexdigest(), 'tarball_bytes': downloaded,
        'registry_integrity_verified': True, 'registry_shasum_verified': True,
        'registry_signature_or_attestation_verified': False,
        'file_count': member_count, 'regular_file_bytes': regular_bytes,
        'decompressed_archive_bytes_observed': decompressed_bytes,
        'native_members': selected, 'native_sha256': {name: row['sha256'] for name, row in selected.items()},
        'matched_vendor_binary_members': vendor_candidates,
        'matched_vendor_codex_paths': [row['archive_member'] for row in vendor_candidates if row['name'] == 'codex'],
        'bounds': {'compressed_package_bytes': MAX_PACKAGE_BYTES, 'selected_native_bytes': MAX_NATIVE_BYTES,
                   'total_decompressed_bytes': MAX_UNPACKED_BYTES, 'archive_members': MAX_MEMBERS,
                   'metadata_bytes': MAX_METADATA_BYTES, 'download_and_parse_deadline_seconds': 180},
        'fresh_download': True, 'archive_extracted_to_filesystem': False,
        'temporary_tarball_removed': True, 'native_binaries_executed': False,
        'provider_calls': 0, 'credentials_read': False, 'source_modified': False,
        'elapsed_seconds': time.monotonic() - started,
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'limitations': ['Pins are independently derived from official HTTPS npm registry metadata and matching package integrity; registry signatures and SLSA attestations were not independently verified.',
            'No native x86_64 execution was attempted on the ARM64 host.',
            'The compressed package is bounded to256MiB and each selected native member to384MiB; the total unpacked population is scanned under a512MiB total decompression ceiling.'],
    }
    path = ROOT / 'official-codex-linux-x64-0.160.0-pins.json'
    with path.open('x') as stream:
        stream.write(canonical(report))
    print(json.dumps({'report': str(path), 'native_sha256': report['native_sha256'],
        'tarball_bytes': downloaded, 'elapsed_seconds': report['elapsed_seconds']}))


if __name__ == '__main__':
    main()
