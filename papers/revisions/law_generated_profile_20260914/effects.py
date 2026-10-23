"""Generic fixture effects and an observer independent of candidate output.

Policy enforcement is injected around the actual delegate, never inside a
task-specific answer generator. This module knows no task IDs or oracle data.
"""
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import sqlite3
import subprocess
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlsplit
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree as DefusedET
from defusedxml.common import DTDForbidden, EntitiesForbidden
from jinja2 import BaseLoader, TemplateError
from jinja2.sandbox import ImmutableSandboxedEnvironment, SecurityError as JinjaSecurityError
from program import Value, ProgramError, wrap, unbox, labels, check_value, Limits

PINNED_EU_READELF = Path(__file__).resolve().parents[2] / 'completion/law_to_action/benchmark/generated_code_study/tools/eu-readelf'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def write_fresh(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())


def normalize(path):
    if type(path) is not str or not path or '\x00' in path or '\\' in path or path.startswith('/') or len(path.encode()) > 512:
        raise ProgramError('Invalid fixture-relative path')
    pieces = []
    for part in path.split('/'):
        if part in ('', '.'):
            continue
        if part == '..':
            if not pieces:
                raise ProgramError('Path escapes common fixture containment')
            pieces.pop()
        else:
            pieces.append(part)
    if not pieces:
        raise ProgramError('A non-root fixture path is required')
    return '/'.join(pieces)


def state_resource(store, key):
    if any(type(value) is not str or not value or len(value.encode()) > 128 for value in (store, key)):
        raise ProgramError('Invalid state address')
    return 'state/' + quote(store, safe='') + '/' + quote(key, safe='')


PURE = {'length', 'keys', 'append', 'text_lower', 'text_replace', 'text_split',
        'text_join', 'json_parse', 'json_encode', 'sha256', 'hmac_sha256',
        'hmac_sha256_b64url', 'base64url_decode', 'base64url_encode', 'ip_is_global',
        'text_endswith', 'text_startswith', 'text_tokens', 'sorted_strings',
        'constant_time_equal', 'url_parse', 'safe_path_join'}
EFFECTS = {'read_text', 'write_text', 'write_json', 'list_files', 'copy_file',
           'state_read', 'state_write', 'state_delete', 'state_compare_delete', 'emit_event',
           'sqlite_query', 'xml_parse', 'template_render', 'archive_extract_member', 'run_program'}


def pure(name, args):
    raw = [unbox(arg) for arg in args]
    combined = frozenset(label for arg in args for label in labels(arg))
    if name == 'length' and len(args) == 1:
        return wrap(len(raw[0]), args[0].labels)
    if name == 'keys' and len(args) == 1 and type(args[0].data) is dict:
        return wrap(list(args[0].data), args[0].labels)
    if name == 'append' and len(args) == 2 and type(args[0].data) is list:
        return Value(args[0].data + [args[1]], args[0].labels)
    if name == 'text_lower' and len(raw) == 1 and type(raw[0]) is str:
        result = raw[0].lower()
    elif name == 'text_replace' and len(raw) == 3 and all(type(value) is str for value in raw):
        occurrences = raw[0].count(raw[1])
        if len(raw[0].encode()) + occurrences * max(0, len(raw[2].encode()) - len(raw[1].encode())) > Limits().string_bytes:
            raise ProgramError('Replacement would exceed the string byte bound')
        result = raw[0].replace(raw[1], raw[2])
    elif name == 'text_split' and len(raw) == 2 and all(type(value) is str for value in raw):
        result = raw[0].split(raw[1])
    elif name == 'text_endswith' and len(raw) == 2 and all(type(value) is str for value in raw):
        result = raw[0].endswith(raw[1])
    elif name == 'text_join' and len(raw) == 2 and type(raw[0]) is str and type(raw[1]) is list and all(type(value) is str for value in raw[1]):
        if sum(len(value.encode()) for value in raw[1]) + max(0, len(raw[1]) - 1) * len(raw[0].encode()) > Limits().string_bytes:
            raise ProgramError('Join would exceed the string byte bound')
        result = raw[0].join(raw[1])
    elif name == 'json_parse' and len(raw) == 1 and type(raw[0]) is str:
        result = json.loads(raw[0])
    elif name == 'json_encode' and len(raw) == 1:
        result = canonical(raw[0]).decode()
    elif name == 'sha256' and len(raw) == 1 and type(raw[0]) is str:
        result = hashlib.sha256(raw[0].encode()).hexdigest()
    elif name == 'hmac_sha256' and len(raw) == 2 and all(type(value) is str for value in raw):
        result = hmac.new(raw[0].encode(), raw[1].encode(), hashlib.sha256).hexdigest()
    elif name == 'hmac_sha256_b64url' and len(raw) == 2 and all(type(value) is str for value in raw):
        digest_bytes = hmac.new(raw[0].encode(), raw[1].encode(), hashlib.sha256).digest()
        result = base64.urlsafe_b64encode(digest_bytes).rstrip(b'=').decode()
    elif name == 'base64url_decode' and len(raw) == 1 and type(raw[0]) is str:
        padded = raw[0] + '=' * (-len(raw[0]) % 4)
        result = base64.urlsafe_b64decode(padded).decode()
    elif name == 'base64url_encode' and len(raw) == 1 and type(raw[0]) is str:
        result = base64.urlsafe_b64encode(raw[0].encode()).rstrip(b'=').decode()
    elif name == 'text_startswith' and len(raw) == 2 and all(type(value) is str for value in raw):
        result = raw[0].startswith(raw[1])
    elif name == 'text_tokens' and len(raw) == 1 and type(raw[0]) is str:
        result = [part.lower() for part in re.split(r'[^A-Za-z0-9]+', raw[0]) if part and part not in ('.', '..')]
    elif name == 'sorted_strings' and len(raw) == 1 and type(raw[0]) is list and all(type(value) is str for value in raw[0]):
        result = sorted(raw[0])
    elif name == 'ip_is_global' and len(raw) == 1 and type(raw[0]) is str:
        try:
            result = ipaddress.ip_address(raw[0]).is_global
        except ValueError:
            result = False
    elif name == 'constant_time_equal' and len(raw) == 2 and all(type(value) is str for value in raw):
        result = hmac.compare_digest(raw[0].encode(), raw[1].encode())
    elif name == 'url_parse' and len(raw) == 1 and type(raw[0]) is str:
        parsed = urlsplit(raw[0])
        result = {'scheme': parsed.scheme, 'netloc': parsed.netloc, 'path': parsed.path,
                  'query': parsed.query, 'fragment': parsed.fragment}
    elif name == 'safe_path_join' and len(raw) == 2 and all(type(value) is str for value in raw):
        root = normalize(raw[0])
        path = normalize(root + '/' + raw[1])
        result = {'ok': path.startswith(root + '/'), 'path': path if path.startswith(root + '/') else None}
    else:
        raise ProgramError('Unsupported primitive arguments: ' + name)
    return wrap(result, combined)


def eu_readelf_binary():
    pinned = Path(os.environ['LA032_EU_READELF']) if os.environ.get('LA032_EU_READELF') else PINNED_EU_READELF
    if pinned.is_file() and os.access(pinned, os.X_OK):
        return pinned.resolve()
    found = shutil_which('eu-readelf')
    if found:
        return Path(found).resolve()
    raise ProgramError('eu-readelf is not present')


def shutil_which(name):
    from shutil import which
    return which(name)


def net_inodes():
    inodes = set()
    for table in ('tcp', 'tcp6', 'udp', 'udp6'):
        path = Path('/proc/net') / table
        if not path.exists():
            continue
        lines = path.read_text().splitlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) >= 10:
                inodes.add(table + ':' + parts[9])
    return inodes


def snapshot(root):
    root = Path(root)
    files = {}
    errors = []
    for path in sorted(root.rglob('*')):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            errors.append('symlink:' + relative)
        elif path.is_file():
            body = path.read_bytes()
            files[relative] = {'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
    return {'files': files, 'integrity_errors': errors}


class FixtureEffects:
    def __init__(self, root, audit, initial, gate, *, resource_labels=None, limits=Limits()):
        self.root, self.audit = Path(root), Path(audit)
        self.root.mkdir()
        self.audit.mkdir()
        self.files = self.root / 'files'
        self.stores = self.root / 'stores'
        self.events = self.root / 'events'
        for path in (self.files, self.stores, self.events):
            path.mkdir()
        self.gate = gate
        self.limits = limits
        self.resource_labels = resource_labels or {}
        self.sequence = 0
        self.version = 0
        self.previous_receipt = None
        self.actual_events = []
        self.process_spawns = []
        self.network_deltas = []
        self.io_bytes = 0
        for name, content in initial.get('files', {}).items():
            if type(content) is not str:
                raise ProgramError('Initial fixture files must contain text')
            self.charge(len(content.encode()))
            target = self.file_path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        for name, content in initial.get('binary_files', {}).items():
            if type(content) is not bytes:
                raise ProgramError('Initial binary files must contain bytes')
            self.charge(len(content))
            target = self.file_path(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        for store, data in initial.get('stores', {}).items():
            check_value(wrap(data), self.limits)
            self.charge(len(canonical(data)))
            target = self.store_path(store)
            write_fresh(target, data)
        self.initial_snapshot = snapshot(self.root)
        write_fresh(self.audit / 'initial_snapshot.json', self.initial_snapshot)

    def charge(self, size):
        if type(size) is not int or size < 0 or self.io_bytes + size > 1048576:
            raise ProgramError('Cumulative fixture I/O byte bound exceeded')
        self.io_bytes += size

    def file_path(self, relative):
        relative = normalize(relative)
        target = self.files / relative
        for parent in [target, *target.parents]:
            if parent == self.files:
                break
            if parent.is_symlink():
                raise ProgramError('Symlink within fixture path')
        return target

    def store_path(self, name):
        if type(name) is not str or not re.fullmatch('[A-Za-z0-9_-]{1,64}', name):
            raise ProgramError('Invalid store name')
        return self.stores / (name + '.json')

    def describe(self, name, raw):
        if name in ('read_text', 'write_text', 'write_json') and len(raw) == (1 if name == 'read_text' else 2):
            path = normalize(raw[0])
            return 'file/' + path, [path, *raw[1:]]
        if name == 'list_files' and len(raw) == 1:
            path = normalize(raw[0])
            return 'file/' + path + '/*', [path]
        if name == 'copy_file' and len(raw) == 2:
            source, destination = normalize(raw[0]), normalize(raw[1])
            # The copy requires both source read and destination write grants.
            return 'file/' + destination, [source, destination]
        if name in ('state_read', 'state_write', 'state_delete', 'state_compare_delete') and len(raw) == (3 if name in ('state_write', 'state_compare_delete') else 2):
            self.store_path(raw[0])
            return state_resource(raw[0], raw[1]), raw
        if name == 'emit_event' and len(raw) == 2 and type(raw[0]) is str and re.fullmatch('[A-Za-z0-9_-]{1,64}', raw[0]):
            return 'event/' + raw[0], raw
        if name == 'sqlite_query' and len(raw) == 3 and type(raw[0]) is str and type(raw[1]) is str and type(raw[2]) is list:
            path = normalize(raw[0])
            return 'sqlite/' + path, [path, raw[1], raw[2]]
        if name == 'xml_parse' and len(raw) == 2 and type(raw[0]) is str and type(raw[1]) is dict:
            return 'xml/parse', raw
        if name == 'template_render' and len(raw) == 2 and type(raw[0]) is str and type(raw[1]) is dict:
            return 'template/render', raw
        if name == 'archive_extract_member' and len(raw) == 4 and all(type(raw[i]) is str for i in (0, 1, 2)) and type(raw[3]) is dict:
            path = normalize(raw[0])
            return 'archive/' + path, raw
        if name == 'run_program' and len(raw) == 1 and type(raw[0]) is list:
            if not raw[0] or any(type(item) is not str for item in raw[0]):
                raise ProgramError('run_program argv must be a list of strings')
            return 'process/' + raw[0][0], raw
        raise ProgramError('Invalid effect arguments: ' + name)

    def dispatch(self, call, args):
        if call['name'] in PURE:
            return check_value(pure(call['name'], args), self.limits)
        name = call['name']
        if self.sequence >= 64:
            raise ProgramError('Effect invocation bound exceeded')
        raw = [unbox(arg) for arg in args]
        resource, raw = self.describe(name, raw)
        # copy_file is intentionally disabled until both native authorizations
        # are bound atomically. It must not perform an unadmitted source read.
        if name == 'copy_file':
            raise ProgramError('copy_file multi-resource authorization is not implemented')
        identifier = self.sequence
        self.sequence += 1
        folder = self.audit / ('effect-%04d' % identifier)
        folder.mkdir()
        invocation = {'index': identifier, 'name': name, 'resource': resource, 'arguments': raw,
                      'argument_label_paths': call['argument_label_paths'],
                      'flow_labels': sorted(set(call['control_labels']) | {label for arg in args for label in labels(arg)}),
                      'source_call': {key: call[key] for key in ('name', 'line', 'column', 'index')},
                      'state_version': self.version, 'prior_effect_receipt_sha256': self.previous_receipt}
        write_fresh(folder / 'reserved.json', invocation)
        before = snapshot(self.root)
        write_fresh(folder / 'before.json', before)
        started = False
        def delegate():
            nonlocal started
            if started:
                raise RuntimeError('Delegate invoked more than once')
            started = True
            write_fresh(folder / 'started.json', {'invocation_sha256': digest(invocation)})
            result = self.perform(name, raw)
            self.version += 1
            return result
        error = None
        result = None
        admission = None
        try:
            admission, result = self.gate(invocation, delegate, folder)
        except Exception as exc:
            error = type(exc).__name__ + ': ' + str(exc)
        after = snapshot(self.root)
        record = {'invocation': invocation, 'admission': admission, 'delegate_started': started,
                  'result': result, 'error': error, 'before_sha256': digest(before),
                  'after': after, 'state_version_after': self.version}
        write_fresh(folder / 'receipt.json', record)
        self.previous_receipt = hashlib.sha256((folder / 'receipt.json').read_bytes()).hexdigest()
        self.actual_events.append(record)
        if error:
            raise ProgramError(error)
        if not started:
            return wrap({'ok': False, 'error': 'native_admission_denied'})
        output_labels = frozenset(self.resource_labels.get(resource, [])) if name == 'read_text' or name.startswith('state_') else frozenset()
        return check_value(wrap(result, output_labels), self.limits)

    def perform(self, name, raw):
        if name == 'read_text':
            with self.file_path(raw[0]).open('rb') as stream:
                body = stream.read(self.limits.string_bytes + 1)
            if len(body) > self.limits.string_bytes:
                raise ProgramError('Read byte bound exceeded')
            self.charge(len(body))
            return body.decode('utf-8')
        if name in ('write_text', 'write_json'):
            body = raw[1].encode() if name == 'write_text' and type(raw[1]) is str else canonical(raw[1]) + b'\n' if name == 'write_json' else None
            if body is None or len(body) > self.limits.total_bytes:
                raise ProgramError('Invalid or oversized write')
            self.charge(len(body))
            target = self.file_path(raw[0])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            return {'ok': True, 'bytes': len(body)}
        if name == 'list_files':
            prefix = raw[0] + '/'
            return [str(path.relative_to(self.files)) for path in sorted(self.files.rglob('*')) if path.is_file() and str(path.relative_to(self.files)).startswith(prefix)]
        if name.startswith('state_'):
            path = self.store_path(raw[0])
            data = json.loads(path.read_text()) if path.exists() else {}
            key = raw[1]
            if name == 'state_read':
                return data.get(key)
            if name == 'state_write':
                data[key] = raw[2]
                result = {'ok': True}
            elif name == 'state_delete':
                existed = key in data
                data.pop(key, None)
                result = {'ok': True, 'existed': existed}
            else:
                matched = key in data and data[key] == raw[2]
                if matched:
                    del data[key]
                result = {'ok': True, 'matched': matched}
            body = canonical(data) + b'\n'
            if len(body) > self.limits.total_bytes:
                raise ProgramError('State byte bound exceeded')
            check_value(wrap(data), self.limits)
            self.charge(len(body))
            temporary = path.with_suffix('.pending')
            with temporary.open('xb') as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
            return result
        if name == 'emit_event':
            body = canonical({'channel': raw[0], 'value': raw[1]}) + b'\n'
            self.charge(len(body))
            (self.events / ('%04d.json' % (self.sequence - 1))).write_bytes(body)
            return {'ok': True}
        if name == 'sqlite_query':
            if any(type(item) not in (str, int, float, type(None), bool) for item in raw[2]):
                raise ProgramError('SQLite parameters must be JSON scalars')
            if len(raw[1].encode()) > 4096 or len(raw[2]) > 32:
                raise ProgramError('SQLite statement or parameter bound exceeded')
            target = self.file_path(raw[0])
            target.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect('file:' + str(target) + '?mode=rwc', uri=True)
            connection.row_factory = sqlite3.Row
            try:
                cursor = connection.execute(raw[1], tuple(raw[2]))
                if cursor.description is None:
                    connection.commit()
                    return {'rowcount': cursor.rowcount, 'rows': []}
                rows = []
                for row in cursor.fetchall():
                    item = {key: row[key] for key in row.keys()}
                    rows.append(item)
                    if len(rows) > 64:
                        raise ProgramError('SQLite result row bound exceeded')
                return {'rowcount': len(rows), 'rows': rows}
            except sqlite3.Error as exc:
                raise ProgramError('SQLite error: ' + str(exc)) from exc
            finally:
                connection.close()
        if name == 'xml_parse':
            if raw[1].get('resolve_entities') is True:
                raise ProgramError('xml_parse does not resolve external entities')
            before_net = net_inodes()
            entities = re.findall(r'<!ENTITY\s+(\w+)\s+SYSTEM\s+', raw[0])
            sanitized = re.sub(r'<!DOCTYPE[\s\S]*?>', '', raw[0])
            sanitized = re.sub(r'&(?!(lt|gt|amp|apos|quot);)(\w+);', '', sanitized)
            try:
                root = DefusedET.fromstring(sanitized)
            except (DTDForbidden, EntitiesForbidden, ParseError) as exc:
                self.note_network('xml_parse', before_net)
                return {'ok': False, 'error': type(exc).__name__, 'unresolved_entities': entities, 'tree': None}
            def tree(node):
                return {'tag': node.tag, 'text': node.text or '', 'children': [tree(child) for child in list(node)]}
            self.note_network('xml_parse', before_net)
            return {'ok': True, 'unresolved_entities': entities, 'tree': tree(root)}
        if name == 'template_render':
            before_net = net_inodes()
            variables = json.loads(canonical(raw[1]).decode())
            environment = ImmutableSandboxedEnvironment(loader=BaseLoader())
            try:
                rendered = environment.from_string(raw[0]).render(variables)
                result = {'ok': True, 'rendered': rendered, 'error': None,
                          'items_after': list(variables['items']) if type(variables.get('items')) is list else None}
            except (JinjaSecurityError, TemplateError, TypeError, ValueError):
                result = {'ok': False, 'error': 'SecurityError', 'rendered': None,
                          'items_after': list(variables['items']) if type(variables.get('items')) is list else []}
            self.note_network('template_render', before_net)
            return result
        if name == 'archive_extract_member':
            budget = raw[3]
            counts = budget.get('ancestor_extracted_counts')
            if type(counts) is not list or any(type(item) is not int or item < 0 for item in counts):
                raise ProgramError('Invalid archive ancestor budget')
            if type(budget.get('max_recurse')) is not int or type(budget.get('max_files')) is not int:
                raise ProgramError('Invalid archive ancestor budget')
            remaining_depth = budget['max_recurse'] - len(counts)
            remaining_files = budget['max_files'] - sum(counts)
            if remaining_depth <= 0:
                return {'decision': 'deny', 'reason': 'recursion_limit', 'files': []}
            if remaining_files <= 0:
                return {'decision': 'deny', 'reason': 'file_budget', 'files': []}
            member = raw[1]
            if type(member) is not str or not member or '\\' in member or member.startswith('/') or '..' in PurePosixPath(member).parts:
                raise ProgramError('Archive member path escapes containment')
            archive = self.file_path(raw[0])
            try:
                with zipfile.ZipFile(archive) as bundle:
                    info = bundle.getinfo(member)
                    if info.is_dir() or info.filename != member or '..' in PurePosixPath(info.filename).parts:
                        raise ProgramError('Archive member is not a regular contained file')
                    body = bundle.read(info)
            except (zipfile.BadZipFile, KeyError, OSError) as exc:
                raise ProgramError('Archive extract failed: ' + str(exc)) from exc
            if remaining_files < 1:
                return {'decision': 'deny', 'reason': 'file_budget', 'files': []}
            self.charge(len(body))
            destination = self.file_path(raw[2])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
            return {'decision': 'extract', 'files': [member], 'remaining_depth': remaining_depth - 1,
                    'remaining_files': remaining_files - 1, 'bytes': len(body)}
        if name == 'run_program':
            argv = raw[0]
            if argv[0] != 'eu-readelf' or len(argv) != 3 or argv[1] != '-d':
                raise ProgramError('run_program allowlist is eu-readelf -d <path> as one argv list')
            target = self.file_path(argv[2])
            binary = eu_readelf_binary()
            executed = [str(binary), '-d', str(target)]
            before_net = net_inodes()
            try:
                process = subprocess.Popen(
                    executed, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(self.files),
                    env={'PATH': '', 'LC_ALL': 'C'}, close_fds=True,
                )
            except OSError as exc:
                raise ProgramError('eu-readelf spawn failed: ' + str(exc)) from exc
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                raise ProgramError('eu-readelf deadline exceeded')
            text = stdout.decode('utf-8', 'replace')
            spawn = {
                'argv_from_program': argv,
                'executed_argv': executed,
                'pid': process.pid,
                'returncode': process.returncode,
                'shell': False,
                'path_was_one_argv_element': len(argv) == 3 and argv[2] == raw[0][2],
                'stdout_sha256': hashlib.sha256(stdout).hexdigest(),
                'stderr_sha256': hashlib.sha256(stderr).hexdigest(),
                'textrel': 'TEXTREL' in text,
            }
            self.process_spawns.append(spawn)
            self.note_network('run_program', before_net)
            if process.returncode != 0:
                raise ProgramError('eu-readelf exited ' + str(process.returncode))
            return {'ok': True, 'textrel': spawn['textrel'], 'program_id': 'eu-readelf',
                    'argv': argv, 'pid': process.pid}
        raise ProgramError('Effect not implemented')

    def note_network(self, name, before):
        after = net_inodes()
        added = sorted(after - before)
        self.network_deltas.append({'effect': name, 'new_socket_inodes': added, 'network_observed': bool(added)})

    def observe(self):
        final = snapshot(self.root)
        errors = list(final['integrity_errors'])
        records = []
        previous = None
        folders = sorted(self.audit.glob('effect-*'))
        for index, folder in enumerate(folders):
            try:
                reserved = json.loads((folder / 'reserved.json').read_text())
                receipt = json.loads((folder / 'receipt.json').read_text())
                if reserved != receipt['invocation'] or reserved['index'] != index or reserved['prior_effect_receipt_sha256'] != previous:
                    errors.append('effect_custody_mismatch:' + folder.name)
                if (folder / 'started.json').is_file() != receipt['delegate_started']:
                    errors.append('delegate_start_mismatch:' + folder.name)
                if receipt['before_sha256'] != digest(json.loads((folder / 'before.json').read_text())):
                    errors.append('before_snapshot_mismatch:' + folder.name)
                previous = hashlib.sha256((folder / 'receipt.json').read_bytes()).hexdigest()
                records.append(receipt)
            except (OSError, ValueError, KeyError) as exc:
                errors.append(type(exc).__name__ + ':' + folder.name)
        expected = records[-1]['after'] if records else self.initial_snapshot
        if final != expected:
            errors.append('unaccounted_terminal_effect')
        if len(records) != self.sequence:
            errors.append('missing_effect_receipt')
        return {'observation_complete': not errors, 'integrity_errors': errors,
                'unaccounted_effects': [item for item in errors if item.startswith('unaccounted')],
                'initial_snapshot': self.initial_snapshot, 'final_snapshot': final,
                'effects': records, 'process_spawns': list(self.process_spawns),
                'network_deltas': list(self.network_deltas),
                'native_process_observer': True, 'native_network_observer': True,
                'model_or_candidate_self_report_used': False}
