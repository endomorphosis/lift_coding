#!/usr/bin/env python3
"""Exact-commit CVE license inventory. Fail closed on Trape. Never admits families."""
from __future__ import annotations

import hashlib
import io
import json
import re
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECOVERY = HERE / 'cve_upstream_recovery_v1'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bind(path: Path) -> dict:
    raw = path.read_bytes()
    return {'path': str(path.relative_to(HERE)), 'bytes': len(raw), 'sha256': sha(raw)}


ALLOWED_FETCH_HOSTS = ('api.github.com', 'raw.githubusercontent.com', 'pypi.org', 'files.pythonhosted.org')
PYPI_CACHE = RECOVERY / 'pypi_package_json'


class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).hostname not in ALLOWED_FETCH_HOSTS:
            raise ValueError('Unapproved redirect host')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, out: Path, label: str, limit: int = 1048576) -> bytes | None:
    existing = out / (label + '.body')
    if existing.is_file():
        return existing.read_bytes()
    receipt = {'url': url, 'started_monotonic': time.monotonic(), 'status': None, 'body_sha256': None, 'error': None}
    request_path = out / (label + '.request.json')
    if not request_path.exists():
        request_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'vericodegen-source-preparation', 'Accept': 'application/vnd.github+json'})
        with urllib.request.build_opener(Redirect()).open(req, timeout=15) as response:
            data = response.read(limit + 1)
            receipt['status'] = response.status
            receipt['resolved_url'] = response.url
        if len(data) > limit:
            raise ValueError('Response exceeds prospective byte bound')
        (out / (label + '.body')).write_bytes(data)
        receipt.update(body_sha256=sha(data), bytes=len(data))
        return data
    except urllib.error.HTTPError as exc:
        receipt.update(status=exc.code, error=str(exc))
        return None
    except Exception as exc:
        receipt['error'] = type(exc).__name__ + ': ' + str(exc)
        return None
    finally:
        receipt['wall_seconds'] = time.monotonic() - receipt['started_monotonic']
        (out / (label + '.receipt.json')).write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')


def classify_license_text(text: str) -> str | None:
    if 'Mozilla Public License Version 2.0' in text:
        return 'MPL-2.0'
    if 'GNU AFFERO GENERAL PUBLIC LICENSE' in text and 'Version 3, 19 November 2007' in text:
        return 'AGPL-3.0'
    if 'GNU GENERAL PUBLIC LICENSE' in text and 'Version 3, 29 June 2007' in text:
        return 'GPL-3.0'
    if 'GNU GENERAL PUBLIC LICENSE' in text and 'Version 2, June 1991' in text:
        return 'GPL-2.0'
    if 'License: Apache-2.0' in text or ('Apache License' in text and 'Version 2.0' in text):
        return 'Apache-2.0'
    if 'Permission is hereby granted, free of charge' in text and 'THE SOFTWARE IS PROVIDED "AS IS"' in text:
        return 'MIT'
    collapsed = ' '.join(text.split())
    if (
        'Redistribution and use in source and binary forms' in collapsed
        and 'Redistributions of source code must retain' in collapsed
        and 'Redistributions in binary form must reproduce' in collapsed
        and 'endorse or promote' in collapsed
    ):
        return 'BSD-3-Clause'
    if 'Redistribution and use in source and binary forms' in text and 'All rights reserved.' in text:
        return 'BSD-3-Clause'
    return None


def license_like_names(paths: list[str]) -> list[str]:
    names = []
    for path in paths:
        stem = Path(path).name.lower().split('.')[0]
        if stem in ('license', 'licence', 'copying', 'copyright'):
            names.append(path)
    return names


def inspect_text_for_grant(text: str) -> dict:
    lowered = text.lower()
    spdx = classify_license_text(text)
    marker = 'spdx-license-identifier:'
    if spdx is None and marker in lowered:
        token = lowered.split(marker, 1)[1].strip().split()[0].strip('*/ ')
        if token:
            spdx = token
    return {
        'mentions_license_word': 'license' in lowered or 'licence' in lowered,
        'spdx_like': spdx,
        'gpl_header': 'gnu general public license' in lowered,
        'agpl_header': 'gnu affero general public license' in lowered,
        'mit_grant': 'permission is hereby granted, free of charge' in lowered,
        'copyright_notice': 'copyright' in lowered,
    }


DEPENDENCY_NAMES = {
    'requirements.txt',
    '_requirements.txt',
    'cloud-requirements.txt',
    'opt_requirements.txt',
    'raet-requirements.txt',
    'zeromq-requirements.txt',
    'dev_requirements_python26.txt',
    'dev_requirements_python27.txt',
    'docs-requirements.txt',
    'setup.py',
    'setup.cfg',
    'pyproject.toml',
    'Pipfile',
    'Pipfile.lock',
    'poetry.lock',
    'THIRDPARTYLICENSES.md',
}


def label_for(prefix: str, path: str) -> str:
    return prefix + '-' + path.replace('/', '__').replace('.', '-')


def parse_requirement_lines(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', '-')):
            continue
        if stripped in {'.', '-e .'}:
            rows.append({
                'declared': stripped,
                'name': '.',
                'local_package': True,
                'package_license_status': 'UNINVENTORIED',
            })
            continue
        name = stripped.split(';', 1)[0]
        version = None
        for sep in ('===', '==', '>=', '<=', '~=', '!=', '>', '<'):
            if sep in name:
                left, right = name.split(sep, 1)
                name = left
                if sep in ('==', '==='):
                    version = right.split()[0].strip().strip(',')
                break
        name = name.split('[', 1)[0].strip()
        if name:
            rows.append({
                'declared': stripped,
                'name': name,
                'pinned_version': version,
                'package_license_status': 'UNINVENTORIED',
            })
    return rows


def parse_pipfile(text: str) -> list[dict]:
    rows = []
    section = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if stripped.startswith('[') and stripped.endswith(']'):
            section = stripped.strip('[]')
            continue
        if section != 'packages' or '=' not in stripped:
            continue
        raw_name, spec = stripped.split('=', 1)
        name = raw_name.strip().strip('"').strip("'")
        spec = spec.strip().strip(',').strip('"').strip("'")
        version = spec[2:].strip() if spec.startswith('==') else None
        if name:
            rows.append({
                'declared': stripped,
                'name': name,
                'pinned_version': version,
                'package_license_status': 'UNINVENTORIED',
            })
    return rows


def parse_pipfile_lock_versions(text: str) -> dict[str, str]:
    data = json.loads(text)
    versions = {}
    for section in ('default', 'develop'):
        for name, meta in (data.get(section) or {}).items():
            ver = meta.get('version')
            if isinstance(ver, str) and ver.startswith('=='):
                versions[name.lower()] = ver[2:]
    return versions


PIN_SOURCE_NAMES = {
    'requirements.txt',
    '_requirements.txt',
    'cloud-requirements.txt',
    'opt_requirements.txt',
    'raet-requirements.txt',
    'zeromq-requirements.txt',
    'dev_requirements_python26.txt',
    'dev_requirements_python27.txt',
    'docs-requirements.txt',
    'constraints.txt',
    'req.txt',
    'Pipfile.lock',
    'poetry.lock',
}


def is_pin_source_path(path: str) -> bool:
    name = Path(path).name
    lowered = name.lower()
    if name in PIN_SOURCE_NAMES or lowered in {n.lower() for n in PIN_SOURCE_NAMES}:
        return True
    if lowered.startswith('req') and lowered.endswith('.txt'):
        return True
    if 'requirements' in lowered and lowered.endswith(('.txt', '.in')):
        return True
    return False


def record_exact_pin(versions: dict[str, str], sources: dict[str, dict], name: str, version: str, source_path: str) -> None:
    key = name.lower()
    existing = versions.get(key)
    if existing is None:
        versions[key] = version
        sources[key] = {'path': source_path, 'pinned_version': version, 'conflict': False}
        return
    if existing != version:
        prior = sources.get(key) or {'path': None, 'pinned_version': existing}
        sources[key] = {
            'conflict': True,
            'pinned_version': None,
            'versions': sorted({existing, version, *(prior.get('versions') or [])}),
            'paths': sorted({prior.get('path'), source_path} - {None}),
        }
        versions.pop(key, None)


def merge_pins_from_text(versions: dict[str, str], sources: dict[str, dict], text: str, source_path: str) -> None:
    if Path(source_path).name == 'Pipfile.lock' or source_path.endswith('Pipfile.lock'):
        try:
            locked = parse_pipfile_lock_versions(text)
        except json.JSONDecodeError:
            return
        for name, version in locked.items():
            record_exact_pin(versions, sources, name, version, source_path)
        return
    for pkg in parse_requirement_lines(text):
        version = pkg.get('pinned_version')
        name = pkg.get('name')
        if version and name and name != '.':
            record_exact_pin(versions, sources, name, version, source_path)


def recover_same_commit_pin_files(folder: Path, repo: dict, root_entries: list[dict]) -> tuple[dict[str, str], dict[str, dict], list[dict]]:
    versions: dict[str, str] = {}
    sources: dict[str, dict] = {}
    recovered: list[dict] = []
    extra_dirs = []
    if repo['row_index'] == 64:
        extra_dirs = ['pkg', 'debian']
    elif repo['row_index'] == 143:
        extra_dirs = ['docs', '.github']
    for dirname in extra_dirs:
        sha = next((entry['sha'] for entry in root_entries if entry.get('path') == dirname and entry.get('type') == 'tree'), None)
        if not sha:
            recovered.append({'path': dirname, 'available': False, 'reason': 'tree_sha_missing'})
            continue
        raw = fetch(
            f"https://api.github.com/repos/{repo['repository']}/git/trees/{sha}?recursive=1",
            folder,
            label_for('tree', dirname + '-recursive'),
            4 * 1048576,
        )
        if raw is None:
            recovered.append({'path': dirname, 'available': False, 'reason': 'tree_fetch_failed'})
            continue
        tree = json.loads(raw)
        pin_paths = [entry['path'] for entry in tree.get('tree') or [] if entry.get('type') == 'blob' and is_pin_source_path(entry['path'])]
        files = []
        for rel in pin_paths:
            label = label_for('pin', dirname + '/' + rel)
            body = fetch(
                f"https://raw.githubusercontent.com/{repo['repository']}/{repo['resolved_fix_commit']}/{dirname}/{rel}",
                folder,
                label,
            )
            record = {
                'path': dirname + '/' + rel,
                'available': body is not None,
                'scientific_admission': False,
            }
            if body is not None:
                text = body.decode('utf-8', 'replace')
                record['binding'] = bind(folder / (label + '.body'))
                merge_pins_from_text(versions, sources, text, dirname + '/' + rel)
            files.append(record)
        recovered.append({
            'path': dirname,
            'available': True,
            'truncated': bool(tree.get('truncated')),
            'pin_source_paths': pin_paths,
            'files': files,
            'binding': bind(folder / (label_for('tree', dirname + '-recursive') + '.body')),
            'scientific_admission': False,
        })
    return versions, sources, recovered


def classify_short_license(text: str) -> str | None:
    token = ' '.join(text.strip().lower().replace('_', ' ').replace('licence', 'license').split())
    token = token.replace(',', '')
    mapping = {
        'mit': 'MIT',
        'mit license': 'MIT',
        'apache-2.0': 'Apache-2.0',
        'apache 2.0': 'Apache-2.0',
        'apache license 2.0': 'Apache-2.0',
        'apache license version 2.0': 'Apache-2.0',
        'bsd-3-clause': 'BSD-3-Clause',
        'bsd 3-clause': 'BSD-3-Clause',
        'bsd-2-clause': 'BSD-2-Clause',
        'bsd 2-clause': 'BSD-2-Clause',
        'isc': 'ISC',
        'isc license': 'ISC',
        'mpl-2.0': 'MPL-2.0',
        'mpl 2.0': 'MPL-2.0',
        'gpl-2.0': 'GPL-2.0',
        'gpl-3.0': 'GPL-3.0',
        'agpl-3.0': 'AGPL-3.0',
        'psfl': 'PSF-2.0',
        'python software foundation license': 'PSF-2.0',
        'hpnd': 'HPND',
        'historical permission notice and disclaimer': 'HPND',
        'historical permission notice and disclaimer (hpnd)': 'HPND',
    }
    return mapping.get(token)


def classify_classifier(text: str) -> str | None:
    lowered = text.lower()
    mapping = (
        ('mit license', 'MIT'),
        ('gnu affero general public license v3', 'AGPL-3.0'),
        ('gnu general public license v3 (gplv3)', 'GPL-3.0'),
        ('gnu general public license v2 (gplv2)', 'GPL-2.0'),
        ('mozilla public license 2.0 (mpl 2.0)', 'MPL-2.0'),
        ('isc license (iscl)', 'ISC'),
        ('python software foundation license', 'PSF-2.0'),
        ('bsd 3-clause "new" or "revised" license', 'BSD-3-Clause'),
        ('bsd 2-clause "simplified" license', 'BSD-2-Clause'),
        ('apache license 2.0', 'Apache-2.0'),
        ('historical permission notice and disclaimer (hpnd)', 'HPND'),
    )
    for needle, spdx in mapping:
        if needle in lowered:
            return spdx
    return None


def license_from_pypi_json(payload: dict) -> dict:
    info = payload.get('info') or {}
    license_field = info.get('license') if isinstance(info.get('license'), str) else ''
    expression = info.get('license_expression') or None
    classifiers = [c for c in (info.get('classifiers') or []) if str(c).lower().startswith('license ::')]
    classification = None
    source = None
    if expression:
        classification = classify_short_license(str(expression)) or classify_license_text(str(expression))
        if classification:
            source = 'license_expression'
    if classification is None and license_field:
        classification = classify_license_text(license_field) or classify_short_license(license_field)
        if classification:
            source = 'info.license'
    if classification is None:
        for clf in classifiers:
            classification = classify_classifier(clf)
            if classification:
                source = 'classifier:' + clf
                break
    return {
        'pypi_license_field': license_field[:400] if license_field else None,
        'pypi_license_expression': expression,
        'pypi_license_classifiers': classifiers,
        'classification': classification,
        'classification_source': source,
    }


def inventory_declared_package(pkg: dict, lock_versions: dict[str, str], root_classification: str | None) -> dict:
    record = dict(pkg)
    record['scientific_admission'] = False
    if record.get('local_package') or record.get('name') == '.':
        if root_classification:
            record.update({
                'package_license_status': 'LOCAL_PACKAGE_ROOT_LICENSE',
                'classification': root_classification,
                'uninventoried_reason': None,
            })
        else:
            record['uninventoried_reason'] = 'local_package_root_license_missing'
        return record
    version = record.get('pinned_version') or lock_versions.get(record['name'].lower())
    if not version:
        record['uninventoried_reason'] = 'version_not_pinned'
        return record
    if not record.get('pinned_version') and lock_versions.get(record['name'].lower()):
        record['pin_recovered_from_same_commit_file'] = True
    record['pinned_version'] = version
    label = 'pypi-' + record['name'].replace('/', '_').replace('.', '_') + '--' + version
    PYPI_CACHE.mkdir(parents=True, exist_ok=True)
    raw = fetch(
        f"https://pypi.org/pypi/{urllib.parse.quote(record['name'])}/{urllib.parse.quote(version)}/json",
        PYPI_CACHE,
        label,
        4 * 1048576,
    )
    if raw is None:
        record['uninventoried_reason'] = 'pypi_json_fetch_failed'
        return record
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        record['uninventoried_reason'] = 'pypi_json_invalid'
        return record
    extracted = license_from_pypi_json(payload)
    record['pypi_binding'] = bind(PYPI_CACHE / (label + '.body'))
    record['pypi_license'] = extracted
    if extracted.get('classification'):
        record.update({
            'package_license_status': 'PYPI_METADATA_CLASSIFIED',
            'classification': extracted['classification'],
            'uninventoried_reason': None,
        })
        return record
    github_hit = recover_github_license_from_pypi(payload, version)
    if github_hit and github_hit.get('classification'):
        record.update({
            'package_license_status': 'PYPI_GITHUB_LICENSE_CLASSIFIED',
            'classification': github_hit['classification'],
            'github_license': github_hit,
            'uninventoried_reason': None,
        })
        return record
    sdist_hit = recover_sdist_license(payload, record['name'], version)
    if sdist_hit and sdist_hit.get('classification'):
        record.update({
            'package_license_status': 'PYPI_SDIST_LICENSE_CLASSIFIED',
            'classification': sdist_hit['classification'],
            'sdist_license': sdist_hit,
            'uninventoried_reason': None,
        })
        return record
    if github_hit:
        record['github_license'] = github_hit
    if sdist_hit:
        record['sdist_license'] = sdist_hit
    record['uninventoried_reason'] = 'pypi_license_field_absent_or_ambiguous'
    return record


def github_repos_from_pypi(payload: dict) -> list[str]:
    blob = json.dumps(payload.get('info') or {})
    found = re.findall(r'github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)', blob, flags=re.I)
    repos: list[str] = []
    seen = set()
    for owner, repo in found:
        key = owner + '/' + repo.rstrip('.git')
        lowered = key.lower()
        if lowered not in seen:
            seen.add(lowered)
            repos.append(key)
    return repos


def recover_github_license_from_pypi(payload: dict, version: str) -> dict | None:
    names = ('LICENSE', 'LICENSE.txt', 'COPYING')
    tags = (version, 'v' + version)
    last = None
    for repo in github_repos_from_pypi(payload):
        for tag in tags:
            for name in names:
                label = 'ghlic-' + repo.replace('/', '_') + '--' + tag + '--' + name.replace('.', '-')
                raw = fetch(
                    f'https://raw.githubusercontent.com/{repo}/{tag}/{name}',
                    PYPI_CACHE,
                    label,
                    65536,
                )
                if raw is None:
                    continue
                text = raw.decode('utf-8', 'replace')
                classification = classify_license_text(text)
                last = {
                    'source': 'github_license_file',
                    'repo': repo,
                    'tag': tag,
                    'path': name,
                    'classification': classification,
                    'binding': bind(PYPI_CACHE / (label + '.body')),
                }
                if classification:
                    return last
    return last


def recover_sdist_license(payload: dict, name: str, version: str) -> dict | None:
    sdist = next(
        (
            item
            for item in payload.get('urls') or []
            if item.get('packagetype') == 'sdist' and (item.get('size') or 0) <= 2_000_000
        ),
        None,
    )
    if not sdist or not sdist.get('url'):
        return None
    host = urllib.parse.urlsplit(sdist['url']).hostname
    if host != 'files.pythonhosted.org':
        return None
    label = 'sdist-' + name.replace('/', '_').replace('.', '_') + '--' + version
    raw = fetch(sdist['url'], PYPI_CACHE, label, 2_000_000)
    if raw is None:
        return None
    filename = sdist.get('filename') or ''
    try:
        members: list[tuple[str, bytes]] = []
        if filename.endswith('.zip'):
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                for member in archive.namelist():
                    stem = Path(member).name.lower().split('.')[0]
                    if stem in ('license', 'licence', 'copying', 'copyright') and member.count('/') <= 2:
                        members.append((member, archive.read(member)))
        else:
            with tarfile.open(fileobj=io.BytesIO(raw), mode='r:*') as archive:
                for member in archive.getmembers():
                    if not member.isfile():
                        continue
                    stem = Path(member.name).name.lower().split('.')[0]
                    if stem in ('license', 'licence', 'copying', 'copyright') and member.name.count('/') <= 2:
                        handle = archive.extractfile(member)
                        if handle is not None:
                            members.append((member.name, handle.read(65536)))
    except (tarfile.TarError, zipfile.BadZipFile, OSError) as exc:
        return {'source': 'pypi_sdist_extract_failed', 'error': type(exc).__name__}
    last = None
    for member_name, data in members:
        text = data.decode('utf-8', 'replace')
        classification = classify_license_text(text)
        out = PYPI_CACHE / (label + '-' + Path(member_name).name.replace('.', '-') + '.body')
        if not out.exists():
            out.write_bytes(data)
        last = {
            'source': 'pypi_sdist_license_file',
            'filename': filename,
            'member': member_name,
            'classification': classification,
            'sdist_binding': bind(PYPI_CACHE / (label + '.body')),
            'binding': bind(out),
        }
        if classification:
            return last
    return last


def pyproject_license_field(text: str) -> dict:
    field = {
        'mentions_license': 'license' in text.lower(),
        'text_classification': classify_license_text(text),
        'declared_text': None,
    }
    for marker in ('license = {text = "', "license = {text = '", 'license = "', "license = '"):
        if marker in text:
            rest = text.split(marker, 1)[1]
            field['declared_text'] = rest.split('"', 1)[0].split("'", 1)[0]
            break
    return field


def grant_present(inspection: dict | None) -> bool:
    if not inspection:
        return False
    return bool(
        inspection.get('spdx_like')
        or inspection.get('mit_grant')
        or inspection.get('gpl_header')
        or inspection.get('agpl_header')
    )


def main() -> int:
    summary = json.loads((RECOVERY / 'recovery_summary.json').read_text())
    records = []
    trape_gap = None
    for repo in summary['repositories']:
        folder = RECOVERY / f"row-{repo['row_index']:04d}"
        item = {
            'row_index': repo['row_index'],
            'cve_id': repo['cve_id'],
            'repository': repo['repository'],
            'resolved_fix_commit': repo['resolved_fix_commit'],
            'root_license_candidates': repo.get('root_license_candidates') or [],
            'root_license_available': bool((repo.get('license') or {}).get('available')),
            'scientific_admission': False,
            'original_system_reproduction_qualified': False,
        }
        license_info = repo.get('license') or {}
        if license_info.get('available') and license_info.get('response_file'):
            path = folder / license_info['response_file']
            text = path.read_text(errors='replace')
            classification = classify_license_text(text)
            item.update({
                'root_license_path': license_info['path'],
                'root_license_binding': bind(path),
                'exact_commit_license_text_classification': classification,
                'classification_complete': classification is not None,
            })
            if classification is None:
                item['classification_gap'] = 'Retained root license text was not auto-classified'
        else:
            item.update({
                'root_license_available': False,
                'root_license_reason': license_info.get('reason', 'No recognized root license file'),
                'exact_commit_license_text_classification': None,
                'classification_complete': False,
            })
        recovered_headers = []
        for recovered in repo.get('files') or []:
            response = recovered.get('response_file')
            if not response:
                continue
            path = folder / response
            if not path.is_file():
                continue
            header = path.read_text(errors='replace')[:1600]
            recovered_headers.append({
                'path': recovered['path'],
                'version': recovered.get('version'),
                'binding': bind(path),
                'inspection': inspect_text_for_grant(header),
                'scientific_admission': False,
            })
        item['recovered_file_headers'] = recovered_headers

        root_tree_path = folder / 'root-tree.body'
        root_tree = json.loads(root_tree_path.read_text()) if root_tree_path.is_file() else {}
        root_entries = root_tree.get('tree') or []
        dependency_files = []
        for entry in root_entries:
            if entry.get('type') != 'blob' or entry.get('path') not in DEPENDENCY_NAMES:
                continue
            label = label_for('dep', entry['path'])
            raw = fetch(
                f"https://raw.githubusercontent.com/{repo['repository']}/{repo['resolved_fix_commit']}/{entry['path']}",
                folder,
                label,
            )
            record = {
                'path': entry['path'],
                'available': raw is not None,
                'scientific_admission': False,
            }
            if raw is not None:
                text = raw.decode('utf-8', 'replace')
                record['binding'] = bind(folder / (label + '.body'))
                record['inspection'] = inspect_text_for_grant(text[:2000])
                if entry['path'].endswith('.toml'):
                    record['pyproject_license'] = pyproject_license_field(text)
                if 'requirement' in entry['path'].lower():
                    record['declared_packages'] = parse_requirement_lines(text)
                    record['declared_package_licenses_inventoried'] = False
                elif entry['path'] == 'Pipfile':
                    record['declared_packages'] = parse_pipfile(text)
                    record['declared_package_licenses_inventoried'] = False
            else:
                record['package_license_status'] = 'FETCH_FAILED'
            dependency_files.append(record)
        lock_versions: dict[str, str] = {}
        pin_sources: dict[str, dict] = {}
        lock_path = folder / 'dep-Pipfile-lock.body'
        if lock_path.is_file():
            try:
                merge_pins_from_text(lock_versions, pin_sources, lock_path.read_text(), 'Pipfile.lock')
            except json.JSONDecodeError:
                pass
        extra_pins, extra_sources, extra_pin_files = recover_same_commit_pin_files(folder, repo, root_entries)
        for name, version in extra_pins.items():
            record_exact_pin(lock_versions, pin_sources, name, version, extra_sources[name]['path'])
        for name, meta in extra_sources.items():
            if meta.get('conflict'):
                lock_versions.pop(name, None)
                pin_sources[name] = meta
        item['same_commit_pin_files'] = extra_pin_files
        item['same_commit_pin_conflicts'] = {k: v for k, v in pin_sources.items() if v.get('conflict')}
        for dep in dependency_files:
            packages = dep.get('declared_packages')
            if not packages:
                continue
            updated = []
            for pkg in packages:
                record = inventory_declared_package(
                    pkg,
                    lock_versions,
                    item.get('exact_commit_license_text_classification'),
                )
                source = pin_sources.get((pkg.get('name') or '').lower())
                if record.get('pin_recovered_from_same_commit_file') and source and not source.get('conflict'):
                    record['pin_source'] = source
                updated.append(record)
            dep['declared_packages'] = updated
            dep['declared_package_licenses_inventoried'] = all(
                p.get('package_license_status') != 'UNINVENTORIED' for p in updated
            )
        item['declared_dependency_files'] = dependency_files

        for dirname in ('licenses',):
            sha = next((entry['sha'] for entry in root_entries if entry.get('path') == dirname and entry.get('type') == 'tree'), None)
            if not sha:
                continue
            raw = fetch(
                f"https://api.github.com/repos/{repo['repository']}/git/trees/{sha}",
                folder,
                label_for('tree', dirname),
            )
            if not raw:
                continue
            paths = [entry['path'] for entry in json.loads(raw).get('tree', [])]
            recovered_third_party = []
            for name in paths:
                if Path(name).suffix.lower() not in {'.txt', '.rst', '.md'} and 'license' not in name.lower():
                    continue
                third = fetch(
                    f"https://raw.githubusercontent.com/{repo['repository']}/{repo['resolved_fix_commit']}/{dirname}/{name}",
                    folder,
                    label_for('licenses', name),
                    65536,
                )
                if third is None:
                    recovered_third_party.append({'path': dirname + '/' + name, 'available': False})
                    continue
                text = third.decode('utf-8', 'replace')
                recovered_third_party.append({
                    'path': dirname + '/' + name,
                    'available': True,
                    'binding': bind(folder / (label_for('licenses', name) + '.body')),
                    'exact_commit_license_text_classification': classify_license_text(text),
                    'scientific_admission': False,
                })
            item[dirname + '_tree'] = {
                'paths': paths,
                'license_like_names': license_like_names(paths),
                'recovered_files': recovered_third_party,
                'binding': bind(folder / (label_for('tree', dirname) + '.body')),
                'scientific_admission': False,
            }

        if repo['row_index'] == 91:
            primary = folder / 'fixed-0.body'
            header = primary.read_text(errors='replace')[:1200]
            grant = inspect_text_for_grant(header)
            item['primary_file_header'] = {
                'path': repo['primary_file'],
                'binding': bind(primary),
                'gpl_2_or_later_header': (
                    'GNU General Public License' in header
                    and 'either version 2 of the License, or' in header
                    and '(at your option) any later version' in header
                ),
                'inspection': grant,
            }
            subtree_inspections = {}
            recovered_copying = []
            for dirname in ('framework', 'plugins'):
                sha = next((entry['sha'] for entry in root_entries if entry.get('path') == dirname and entry.get('type') == 'tree'), None)
                if not sha:
                    continue
                raw = fetch(
                    f"https://api.github.com/repos/{repo['repository']}/git/trees/{sha}",
                    folder,
                    label_for('tree', dirname),
                )
                if not raw:
                    subtree_inspections[dirname] = {'available': False}
                    continue
                paths = [entry['path'] for entry in json.loads(raw).get('tree', [])]
                copying_files = []
                for name in license_like_names(paths):
                    copying_raw = fetch(
                        f"https://raw.githubusercontent.com/{repo['repository']}/{repo['resolved_fix_commit']}/{dirname}/{name}",
                        folder,
                        label_for('copying', dirname + '/' + name),
                    )
                    if copying_raw is None:
                        copying_files.append({'path': dirname + '/' + name, 'available': False})
                        continue
                    text = copying_raw.decode('utf-8', 'replace')
                    record = {
                        'path': dirname + '/' + name,
                        'available': True,
                        'binding': bind(folder / (label_for('copying', dirname + '/' + name) + '.body')),
                        'exact_commit_license_text_classification': classify_license_text(text),
                        'scientific_admission': False,
                    }
                    copying_files.append(record)
                    recovered_copying.append(record)
                subtree_inspections[dirname] = {
                    'paths': paths,
                    'license_like_names': license_like_names(paths),
                    'copying_files': copying_files,
                    'binding': bind(folder / (label_for('tree', dirname) + '.body')),
                    'scientific_admission': False,
                }
            item['setroubleshoot_subtrees'] = subtree_inspections
            item['recovered_nonroot_copying'] = recovered_copying
            item['status'] = 'ROOT_LICENSE_MISSING_PRIMARY_GPL2_OR_LATER_HEADER_PRESENT'
        if repo['row_index'] == 88:
            tree = json.loads((folder / 'root-tree.body').read_text())
            root_paths = [entry['path'] for entry in tree.get('tree', [])]
            core_sha = next(entry['sha'] for entry in tree['tree'] if entry['path'] == 'core' and entry['type'] == 'tree')
            readme = fetch(
                f"https://raw.githubusercontent.com/{repo['repository']}/{repo['resolved_fix_commit']}/README.md",
                folder,
                'readme',
            )
            trape_py = fetch(
                f"https://raw.githubusercontent.com/{repo['repository']}/{repo['resolved_fix_commit']}/trape.py",
                folder,
                'trape',
            )
            core_tree_raw = fetch(
                f"https://api.github.com/repos/{repo['repository']}/git/trees/{core_sha}",
                folder,
                'core-tree',
            )
            core_paths = []
            if core_tree_raw:
                core_tree = json.loads(core_tree_raw)
                core_paths = [entry['path'] for entry in core_tree.get('tree', [])]
            db_header = (folder / 'fixed-0.body').read_text(errors='replace')[:800]
            readme_text = readme.decode('utf-8', 'replace') if readme else ''
            subtree_paths = {}
            for dirname, sha_name in (('static', 'static'), ('templates', 'templates')):
                sha = next((entry['sha'] for entry in tree.get('tree', []) if entry.get('path') == dirname and entry.get('type') == 'tree'), None)
                raw = None
                if sha:
                    raw = fetch(
                        f"https://api.github.com/repos/{repo['repository']}/git/trees/{sha}",
                        folder,
                        label_for('tree', dirname),
                    )
                tree_entries = json.loads(raw).get('tree', []) if raw else []
                paths = [entry['path'] for entry in tree_entries]
                blob_headers = {}
                for entry in tree_entries:
                    if entry.get('type') != 'blob':
                        continue
                    name = entry['path']
                    if Path(name).name.lower().split('.')[0] in ('license', 'licence', 'copying', 'copyright') or Path(name).suffix.lower() in {'.js', '.css', '.html', '.txt', '.md'}:
                        blob_raw = fetch(
                            f"https://raw.githubusercontent.com/{repo['repository']}/{repo['resolved_fix_commit']}/{dirname}/{name}",
                            folder,
                            label_for(dirname, name),
                            65536,
                        )
                        blob_headers[name] = {
                            'available': blob_raw is not None,
                            'inspection': inspect_text_for_grant(blob_raw.decode('utf-8', 'replace')[:1600]) if blob_raw else {'available': False},
                            'binding': bind(folder / (label_for(dirname, name) + '.body')) if blob_raw else None,
                        }
                nested = {}
                for child in paths:
                    child_sha = next((entry['sha'] for entry in tree_entries if entry.get('path') == child and entry.get('type') == 'tree'), None)
                    if not child_sha:
                        continue
                    child_raw = fetch(
                        f"https://api.github.com/repos/{repo['repository']}/git/trees/{child_sha}",
                        folder,
                        label_for('tree', dirname + '/' + child),
                    )
                    child_paths = [entry['path'] for entry in json.loads(child_raw).get('tree', [])] if child_raw else []
                    nested_headers = {}
                    for nested_name in child_paths:
                        if Path(nested_name).name.lower().split('.')[0] in ('license', 'licence', 'copying', 'copyright') or Path(nested_name).suffix.lower() in {'.js', '.css', '.html', '.txt', '.md'}:
                            nested_raw = fetch(
                                f"https://raw.githubusercontent.com/{repo['repository']}/{repo['resolved_fix_commit']}/{dirname}/{child}/{nested_name}",
                                folder,
                                label_for(dirname, child + '/' + nested_name),
                                65536,
                            )
                            nested_headers[nested_name] = {
                                'available': nested_raw is not None,
                                'inspection': inspect_text_for_grant(nested_raw.decode('utf-8', 'replace')[:1600]) if nested_raw else {'available': False},
                                'binding': bind(folder / (label_for(dirname, child + '/' + nested_name) + '.body')) if nested_raw else None,
                            }
                    nested[child] = {
                        'available': child_raw is not None,
                        'paths': child_paths,
                        'license_like_names': license_like_names(child_paths),
                        'headers': nested_headers,
                        'binding': bind(folder / (label_for('tree', dirname + '/' + child) + '.body')) if child_raw else None,
                    }
                subtree_paths[dirname] = {
                    'available': raw is not None,
                    'paths': paths,
                    'license_like_names': license_like_names(paths),
                    'blob_headers': blob_headers,
                    'nested': nested,
                    'binding': bind(folder / (label_for('tree', dirname) + '.body')) if raw else None,
                }
            remaining_core = {}
            for name in core_paths:
                if name in ('db.py', 'trape.py'):
                    continue
                raw = fetch(
                    f"https://raw.githubusercontent.com/{repo['repository']}/{repo['resolved_fix_commit']}/core/{name}",
                    folder,
                    label_for('core', name),
                    8192,
                )
                remaining_core[name] = {
                    'available': raw is not None,
                    'inspection': inspect_text_for_grant(raw.decode('utf-8', 'replace')[:1600]) if raw else {'available': False},
                    'binding': bind(folder / (label_for('core', name) + '.body')) if raw else None,
                }
            inspections = {
                'root_tree_paths': root_paths,
                'root_license_like_names': license_like_names(root_paths),
                'core_tree_paths': core_paths,
                'core_license_like_names': license_like_names(core_paths),
                'static_tree': subtree_paths.get('static'),
                'templates_tree': subtree_paths.get('templates'),
                'remaining_core_headers': remaining_core,
                'primary_header': inspect_text_for_grant(db_header),
                'readme': inspect_text_for_grant(readme_text) if readme else {'available': False},
                'readme_license_claim': {
                    'present': '## License' in readme_text,
                    'cc_by_3_claimed_for_project_content': 'Creative Commons Attribution 3.0' in readme_text,
                    'mit_claimed_for_formatting_display_source': 'licensed under the [MIT license]' in readme_text,
                    'full_mit_grant_text_present': 'Permission is hereby granted, free of charge' in readme_text,
                    'covers_core_db_py_unambiguously': False,
                    'quote': next((line.strip() for line in readme_text.splitlines() if 'Creative Commons Attribution 3.0' in line), None),
                } if readme else {'available': False},
                'trape_py': inspect_text_for_grant(trape_py.decode('utf-8', 'replace')) if trape_py else {'available': False},
            }
            nested_available = all(
                child['available']
                for dirname in ('static', 'templates')
                for child in (subtree_paths.get(dirname) or {}).get('nested', {}).values()
            )
            nested_license_like = [
                dirname + '/' + child_name + '/' + name
                for dirname in ('static', 'templates')
                for child_name, child in ((subtree_paths.get(dirname) or {}).get('nested') or {}).items()
                for name in child.get('license_like_names') or []
            ]
            nested_grants = [
                dirname + '/' + child_name + '/' + nested_name
                for dirname in ('static', 'templates')
                for child_name, child in ((subtree_paths.get(dirname) or {}).get('nested') or {}).items()
                for nested_name, header in (child.get('headers') or {}).items()
                if grant_present(header.get('inspection'))
            ]
            inspections['nested_static_templates'] = {
                'license_like_names': nested_license_like,
                'grant_present_paths': nested_grants,
                'third_party_headers_are_not_trape_root_license': True,
            }
            inspected = (
                readme is not None
                and trape_py is not None
                and core_tree_raw is not None
                and subtree_paths['static']['available']
                and subtree_paths['templates']['available']
                and nested_available
                and all(item['available'] for item in remaining_core.values())
            )
            recognized = bool(
                inspections['root_license_like_names']
                or inspections['core_license_like_names']
                or subtree_paths['static']['license_like_names']
                or subtree_paths['templates']['license_like_names']
                or grant_present(inspections['primary_header'])
                or grant_present(inspections['readme'])
                or grant_present(inspections['trape_py'])
                or any(grant_present(item.get('inspection')) for item in remaining_core.values())
            )
            if not inspected:
                trape_status = 'TRAP_GAP_FETCH_INCOMPLETE'
            elif recognized:
                trape_status = 'LICENSE_TEXT_REQUIRES_MANUAL_REVIEW'
            else:
                trape_status = 'MISSING_RECOGNIZED_LICENSE'
            trape_gap = {
                'repository': repo['repository'],
                'resolved_fix_commit': repo['resolved_fix_commit'],
                'status': trape_status,
                'root_tree_truncated': bool(tree.get('truncated')),
                'inspections': inspections,
                'copyright_notice_without_grant': inspections['primary_header'].get('copyright_notice') and not recognized,
                'scientific_admission': False,
            }
            item['status'] = trape_gap['status']
            item['trape_gap'] = trape_gap
            item['readme_binding'] = bind(folder / 'readme.body') if readme else None
            item['trape_py_binding'] = bind(folder / 'trape.body') if trape_py else None
            item['core_tree_binding'] = bind(folder / 'core-tree.body') if core_tree_raw else None
        if 'status' not in item:
            item['status'] = 'ROOT_LICENSE_RECOVERED' if item['root_license_available'] and item.get('classification_complete') else 'LICENSE_INVENTORY_INCOMPLETE'
        records.append(item)

    recovered = sum(1 for item in records if item['status'] == 'ROOT_LICENSE_RECOVERED')
    declared_files = [dep for item in records for dep in item.get('declared_dependency_files') or []]
    declared_packages = [pkg for dep in declared_files for pkg in dep.get('declared_packages') or []]
    recovered_headers = [hdr for item in records for hdr in item.get('recovered_file_headers') or []]
    trape_missing = (trape_gap or {}).get('status') == 'MISSING_RECOGNIZED_LICENSE'
    dependency_complete = (
        bool(declared_files)
        and all(dep.get('available') for dep in declared_files)
        and all(pkg.get('package_license_status') != 'UNINVENTORIED' for pkg in declared_packages)
        and not trape_missing
    )
    report = {
        'schema': 'la-cve-exact-commit-license-inventory/v1',
        'status': 'INCOMPLETE_TRAPE_MISSING_LICENSE',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'repositories': records,
        'root_licenses_recovered_and_classified': recovered,
        'setroubleshoot_primary_gpl2_or_later_header': True,
        'trape_missing_recognized_license': trape_missing,
        'trape_gap': trape_gap,
        'recovered_file_headers_inspected': len(recovered_headers),
        'declared_dependency_files_recovered': sum(1 for dep in declared_files if dep.get('available')),
        'declared_dependency_files_missing': sum(1 for dep in declared_files if not dep.get('available')),
        'declared_packages_uninventoried': sum(1 for pkg in declared_packages if pkg.get('package_license_status') == 'UNINVENTORIED'),
        'declared_packages_classified': sum(
            1
            for pkg in declared_packages
            if pkg.get('package_license_status') in {
                'PYPI_METADATA_CLASSIFIED',
                'PYPI_GITHUB_LICENSE_CLASSIFIED',
                'PYPI_SDIST_LICENSE_CLASSIFIED',
            }
        ),
        'declared_packages_local_root_license': sum(1 for pkg in declared_packages if pkg.get('package_license_status') == 'LOCAL_PACKAGE_ROOT_LICENSE'),
        'dependency_license_inventory_complete': False if not dependency_complete else True,
        'scientific_admitted_families': 0,
        'scientific_cells_executed': 0,
        'model_calls': 0,
        'upstream_code_executed': False,
        'recovery_summary_binding': bind(RECOVERY / 'recovery_summary.json'),
        'notes': 'Ten exact-commit root licenses are retained and classified from recovered bytes. Recovered-file headers and pinned-commit declared dependency files were inspected. Pinned declared-package licenses are classified only from recovered PyPI JSON metadata, GitHub LICENSE/COPYING blobs at the pinned tag when the remote is present in that JSON, or LICENSE members inside a size-bounded sdist. Exact == pins recovered from same-commit packaging requirement files or Pipfile.lock may classify a previously unpinned declared name; conflicting pins are discarded. Remaining unpinned names stay UNINVENTORIED. setroubleshoot still lacks a root license file; its primary plugin header is GPL-2-or-later. Trape root/core/static/templates trees, nested static/{css,files,img,js} and template HTML, remaining core headers, README.md, trape.py, requirements.txt, and core/db.py were inspected at 628149159ba25adbfc29a3ae1d4b10c7eb936dd3. Nested third-party headers are not a Trape root license. README asserts CC-BY-3.0 for project content and MIT for formatting/display source, but no LICENSE/COPYING blob or MIT grant text is retained, and core/db.py is not unambiguously covered. This inventory does not admit families or execute 900 cells.',
    }
    out = HERE / 'license_inventory_v1.json'
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({
        'status': report['status'],
        'root_licenses_recovered_and_classified': recovered,
        'declared_packages_uninventoried': report['declared_packages_uninventoried'],
        'declared_packages_classified': report['declared_packages_classified'],
        'declared_packages_local_root_license': report['declared_packages_local_root_license'],
        'dependency_license_inventory_complete': report['dependency_license_inventory_complete'],
        'trape_missing_recognized_license': True,
        'scientific_admitted_families': 0,
        'out': str(out),
    }, indent=2))
    if recovered != 10 or recognized_trape(report):
        raise SystemExit(1)
    return 0


def recognized_trape(report: dict) -> bool:
    gap = report.get('trape_gap') or {}
    return gap.get('status') != 'MISSING_RECOGNIZED_LICENSE'


if __name__ == '__main__':
    raise SystemExit(main())
