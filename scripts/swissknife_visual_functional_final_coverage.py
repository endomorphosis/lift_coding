"""Current independent viewport evidence and final-review joins.

New app verification runs use this module. Historical V1 receipts
remain historical. No function here calls a model, browser, SDK or backend.
"""
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import uuid

PARENT_SCHEMA = 'swissknife.visual-functional-workflow.v2'
CHILD_SCHEMA = 'swissknife.visual-functional-viewport.v1'
COVERAGE_SCHEMA = 'swissknife.current-final-app-coverage.v1'
JOIN_SCHEMA = 'swissknife.current-final-app-review-join.v1'
FAILURE_SCHEMA = 'swissknife.unchanged-final-app-review.v1'
VIEWPORTS = ({'name': 'desktop', 'width': 1440, 'height': 900},
             {'name': 'mobile', 'width': 390, 'height': 844})
STATIC_INPUTS = (
    'swissknife/scripts/run-visual-functional-workflow.mjs',
    'swissknife/scripts/capture-visual-functional-baseline.mjs',
    'swissknife/scripts/lib/pick-free-port.mjs',
    'scripts/swissknife_visual_functional_worker.py',
    'scripts/swissknife_visual_functional_llm.py',
    'scripts/swissknife_visual_functional_phase_budget.py',
    'scripts/swissknife_visual_functional_review_recheck.py',
    'scripts/swissknife_visual_functional_final_coverage.py',
    'scripts/swissknife_visual_functional_blocked.py',
    'scripts/swissknife_visual_functional_native_context.py',
    'scripts/swissknife_visual_functional_recovery.py',
    'config/swissknife_visual_functional_supervisor.json',
    'config/swissknife_visual_functional_payload_fixtures.json',
    'swissknife/build-tools/configs/vite.web.config.ts',
    'external/ipfs_accelerate/ipfs_accelerate_py/llm_router.py',
    'external/ipfs_accelerate/ipfs_accelerate_py/cli_runtime/grok_stream_capture.py',
    'swissknife/scripts/mcpplusplus-profile-a.cjs',
    'swissknife/scripts/mcpplusplus-artifact-store.cjs',
    'swissknife/scripts/vdg-connector-artifacts.cjs',
    'swissknife/config/mcpplusplus-helia-bootstrap-peers.json',
    'swissknife/scripts/live-click-fixture.cjs',
    'swissknife/web/js/apps/network-native-tools.js',
    'swissknife/web/index.html', 'swissknife/web/js/main-simple.js',
    'swissknife/web/js/live-tool-gateway.js',
    'swissknife/web/js/core/mcp-plus-plus-desktop-client.js',
    'swissknife/web/js/all-app-backend-status.js',
    'swissknife/src/services/apps/virtual-desktop-app-manifest.ts',
    'swissknife/src/services/apps/all-app-executable-backend-contract.ts',
    'swissknife/src/services/apps/all-app-live-tool-bindings.ts',
    'swissknife/src/services/mcp/all-app-tool-mediator.ts',
    'swissknife/src/services/mcp/all-app-tool-gateway.ts',
    'swissknife/src/services/mcp/mcp-plus-plus-connector.ts',
    'swissknife/src/services/mcp/mcp-plus-plus-profile-c.ts',
)
OPTIONAL_INPUTS = ('swissknife/ipfs_accelerate_js/src/p2p/collaborative-file-system.js',)
SOURCE_LIMITS = {'files': 512, 'bytes': 16777216}
SOURCE_READER = r"""
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import net from 'node:net';
import http from 'node:http';
import https from 'node:https';
import dgram from 'node:dgram';
import child from 'node:child_process';
import threads from 'node:worker_threads';
import {syncBuiltinESMExports} from 'node:module';
import {pathToFileURL} from 'node:url';
const refuse=()=>{throw new Error('readonly viewport source collector refused an effect');};
for(const name of ['writeFile','appendFile','copyFile','cp','mkdir','mkdtemp','rename','unlink','rm','rmdir','truncate','chmod','chown','lchown','utimes','lutimes','link','symlink']){
  if(typeof fs[name]==='function')fs[name]=refuse;
  if(typeof fs[name+'Sync']==='function')fs[name+'Sync']=refuse;
  if(typeof fsp[name]==='function')fsp[name]=refuse;
}
const readonly=flags=>{if(typeof flags==='number'?(flags&(fs.constants.O_WRONLY|fs.constants.O_RDWR|fs.constants.O_CREAT|fs.constants.O_TRUNC|fs.constants.O_APPEND)):/[wa+]/.test(flags||'r'))refuse();};
const openSync=fs.openSync.bind(fs);fs.openSync=(file,flags,...rest)=>{readonly(flags);return openSync(file,flags,...rest);};
const open=fs.open.bind(fs);fs.open=(file,flags,...rest)=>{readonly(flags);return open(file,flags,...rest);};
const openPromise=fsp.open.bind(fsp);fsp.open=(file,flags,...rest)=>{readonly(flags);return openPromise(file,flags,...rest);};
for(const name of ['connect','createConnection'])net[name]=refuse;
net.Socket.prototype.connect=refuse;net.Server.prototype.listen=refuse;
for(const api of [http,https]){api.request=refuse;api.get=refuse;}
dgram.createSocket=refuse;globalThis.fetch=refuse;
for(const name of ['spawn','spawnSync','exec','execSync','execFile','execFileSync','fork'])child[name]=refuse;
threads.Worker=class{constructor(){refuse();}};syncBuiltinESMExports();
const runner=process.argv[2],root=process.argv[3],app=JSON.parse(process.argv[4]),contract=process.argv[5],scenario=process.argv[6];
const module=await import(pathToFileURL(runner).href);
const snapshot=Array.isArray(app)?Object.fromEntries(app.map(item=>[item.app_id,module.independentWorkflowSourceSnapshot(item,{projectRoot:root+'/swissknife',contractsPath:root+'/'+contract,scenarioPath:root+'/swissknife/test/e2e/functional-workflows/'+item.app_id+'.json'})]))
 :module.independentWorkflowSourceSnapshot(app,{projectRoot:root+'/swissknife',contractsPath:root+'/'+contract,scenarioPath:root+'/'+scenario});
console.log(JSON.stringify({fixed:module.INDEPENDENT_STATIC_INPUTS,optional:module.INDEPENDENT_OPTIONAL_INPUTS,limits:module.INDEPENDENT_SOURCE_LIMITS,
 snapshot}));
"""
_ACTIVE_SNAPSHOTS = ContextVar('svf_current_final_source_snapshots', default=None)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def path(root, name):
    root = Path(root)
    need(root.is_absolute() and root.resolve() == root, 'final coverage root must be physical')
    need(type(name) is str and name and not Path(name).is_absolute()
         and all(part not in ('', '.', '..') for part in name.split('/')),
         'final coverage path must be exact repository relative')
    result = root / name
    need(result.resolve() == result and not result.is_symlink(), 'final coverage path escaped its physical checkout')
    return result


def read(root, name, limit=16 * 1024 * 1024, *, private=False):
    target = path(root, name)
    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit
             and (not private or before.st_uid == os.getuid() and before.st_mode & 0o077 == 0),
             'final coverage needs bounded regular immutable bytes')
        raw = stream.read(limit + 1); after = os.fstat(stream.fileno())
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    need(len(raw) == before.st_size and identity(before) == identity(after) == identity(target.lstat()),
         'final coverage bytes changed while being read')
    return raw


def parse(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            need(key not in result, 'duplicate final coverage JSON field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite final coverage JSON')))


def reference(root, file):
    relative = str(Path(file).relative_to(root))
    raw = read(root, relative, 128 * 1024 * 1024)
    return {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def check_reference(root, record, *, prefix=None):
    need(type(record) is dict and set(record) == {'path', 'sha256', 'bytes'}
         and type(record['bytes']) is int and record['bytes'] > 0
         and type(record['sha256']) is str and re.fullmatch('[0-9a-f]{64}', record['sha256']),
         'invalid final coverage artifact reference')
    target = path(root, record['path'])
    need(prefix is None or target.is_relative_to(prefix), 'final coverage artifact escaped its owner')
    need(reference(root, target) == record, 'final coverage artifact hash or size differs')
    return target


def check_references(root, records, *, prefix):
    need(type(records) is list and records and len(records) <= 512,
         'final coverage artifacts are missing or unbounded')
    indexed = {}
    for record in records:
        target = check_reference(root, record, prefix=prefix)
        need(record['path'] not in indexed, 'duplicate final coverage artifact path')
        indexed[record['path']] = record
    return indexed


def app_contract(root, profile, task):
    config = parse(read(root, profile['appContractPath']))
    apps = [app for app in config['apps'] if app['app_id'] == task['app_id']]
    need(len(apps) == 1, 'final coverage needs one canonical app')
    return apps[0]


def _snapshot_runner_path(root):
    return path(root, 'swissknife/scripts/run-visual-functional-workflow.mjs')


def _node_collect(root, profile, apps):
    environment = {key: value for key, value in os.environ.items()
                   if key not in {'NODE_OPTIONS', 'NODE_PATH', 'NODE_COMPILE_CACHE', 'NODE_V8_COVERAGE'}}
    def descriptor(app):
        need(type(app) is dict and type(app.get('app_id')) is str and type(app.get('source_paths')) is list
             and all(type(name) is str for name in app['source_paths']), 'final source collector app descriptor is invalid')
        return {'app_id': app['app_id'], 'source_paths': app['source_paths']}
    descriptors = descriptor(apps) if type(apps) is dict else [descriptor(app) for app in apps]
    argument = encoded(descriptors)
    need(len(argument) <= 65536, 'final source collector descriptor argv exceeds its64KiB bound')
    scenario = ('swissknife/test/e2e/functional-workflows/' + apps['app_id'] + '.json') if type(apps) is dict else ''
    completed = subprocess.run(['node', '--input-type=module', '-e', SOURCE_READER, 'svf-readonly-source-snapshot',
        str(_snapshot_runner_path(root)), str(root), argument.decode(), profile['appContractPath'], scenario],
        cwd=root, env=environment, stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
    need(completed.returncode == 0, 'readonly final source collector failed: ' + completed.stderr[-3000:].decode(errors='replace'))
    need(0 < len(completed.stdout) <= 4 * 1024 * 1024, 'final source collector output exceeds its bound')
    value = parse(completed.stdout)
    need(type(value) is dict and set(value) == {'fixed', 'optional', 'limits', 'snapshot'}
         and value['fixed'] == list(STATIC_INPUTS) and value['optional'] == list(OPTIONAL_INPUTS)
         and value['limits'] == SOURCE_LIMITS, 'Node/Python final source closure policies differ')
    return value['snapshot']


def _node_source_snapshot(root, profile, task, app):
    return _node_collect(root, profile, app)


def _node_source_snapshots(root, profile, apps):
    value = _node_collect(root, profile, apps)
    need(type(value) is dict and set(value) == {app['app_id'] for app in apps}, 'final batched source closure omitted a canonical app')
    return value


def source_snapshot(root, profile, task):
    app = app_contract(root, profile, task)
    scenario = 'swissknife/test/e2e/functional-workflows/' + task['app_id'] + '.json'
    names = [*STATIC_INPUTS, profile['appContractPath'], scenario]
    names += ['swissknife/' + name for name in app['source_paths']]
    index = read(root, 'swissknife/web/index.html', 1048576).decode()
    styles = 0
    for tag in re.findall(r'<link\b[^>]*>', index, re.I):
        attributes = {}
        for match in re.finditer(r'\b(rel|href)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', tag, re.I):
            name = match[1].lower()
            need(name not in attributes, 'duplicate final coverage stylesheet attribute')
            attributes[name] = next(value for value in match.groups()[1:] if value is not None)
        if 'stylesheet' not in attributes.get('rel', '').lower().split():
            continue
        href = attributes.get('href', '')
        need(re.fullmatch(r'/css/[a-zA-Z0-9_.-]+\.css', href), 'final coverage stylesheet is not a local exact CSS file')
        names.append('swissknife/web' + href); styles += 1
    need(styles > 0, 'final coverage shared stylesheet closure is absent')
    active = _ACTIVE_SNAPSHOTS.get()
    snapshot = (active['snapshots'][task['app_id']] if active is not None and active['root'] == root
                and active['contract'] == profile['appContractPath'] and task['app_id'] in active['snapshots']
                else _node_source_snapshot(root, profile, task, app))
    need(type(snapshot) is dict and set(snapshot) == {'contract_sha256', 'scenario_sha256', 'source_sha256'}
         and type(snapshot['source_sha256']) is dict and set(names) <= set(snapshot['source_sha256'])
         and len(snapshot['source_sha256']) <= SOURCE_LIMITS['files'], 'final transitive source closure is incomplete or unbounded')
    sources = {}; total = 0
    for name, expected in snapshot['source_sha256'].items():
        target = path(root, name)
        if expected is None:
            need(name in OPTIONAL_INPUTS and not target.exists() and not target.is_symlink(),
                 'final optional absence marker is unapproved or materialized')
            sources[name] = None
            continue
        raw = read(root, name); total += len(raw)
        need(total <= SOURCE_LIMITS['bytes'] and type(expected) is str
             and hashlib.sha256(raw).hexdigest() == expected, 'final source changed between Node collection and independent Python hashing')
        sources[name] = expected
    need(snapshot['contract_sha256'] == sources[profile['appContractPath']]
         and snapshot['scenario_sha256'] == sources[scenario], 'final transitive closure contract/scenario identity differs')
    return snapshot


@contextmanager
def source_snapshot_transaction(root, profile, tasks):
    """One bounded before/after graph collection; never a cross-turn cache.

    Every consumer read still independently hashes the physical source files.
    A second complete graph discovery catches import-resolution/absence changes
    before the coverage result can be published, including new shadow files.
    """
    names = {task['app_id'] for task in tasks}; active = _ACTIVE_SNAPSHOTS.get()
    if (active is not None and active['root'] == root and active['contract'] == profile['appContractPath']
            and names <= set(active['snapshots'])):
        yield
        return
    apps = [app_contract(root, profile, task) for task in tasks]
    before = _node_source_snapshots(root, profile, apps)
    token = _ACTIVE_SNAPSHOTS.set({'root': root, 'contract': profile['appContractPath'], 'snapshots': before})
    try:
        for task in tasks: source_snapshot(root, profile, task)
        yield
        after = _node_source_snapshots(root, profile, apps)
        need(after == before, 'final source/import/optional-resolution graph changed during coverage validation')
        for task in tasks: source_snapshot(root, profile, task)
    finally:
        _ACTIVE_SNAPSHOTS.reset(token)


def _observation(value, validate, actual, expected):
    validate(value)
    need(value.get('operator') == 'equals' and encoded(value.get('actual')) == encoded(actual)
         and encoded(value.get('expected')) == encoded(expected), 'final viewport check is detached from actual required semantics')


PHASE_EVIDENCE_SCHEMA = 'swissknife.visual-functional-phase-evidence.v1'
_PHASES = ('primary_result', 'persist_reopen', 'failure_recovery')
_MEDIA_KEYS = {'present', 'tag', 'visible', 'decoded_cid', 'src_sha256', 'current_time', 'duration',
               'ready_state', 'paused', 'ended', 'seeking', 'video_width', 'video_height'}
_CONTROL_KEYS = {'present', 'tag', 'type', 'visible', 'enabled', 'value', 'value_as_number', 'min', 'max', 'step'}


def _phase_number(value, *, nullable=False, low=None):
    if nullable and value is None:
        return
    need(type(value) in {int, float} and math.isfinite(value) and (low is None or value >= low),
         'phase evidence needs finite typed measured scalars')


def _phase_snapshot(value, *, media):
    if value is None:
        return
    keys = _MEDIA_KEYS if media else _CONTROL_KEYS
    need(type(value) is dict and set(value) == keys and type(value['present']) is bool,
         'phase snapshot shape is invalid')
    flags = {'visible'} if media else {'visible', 'enabled'}
    need(all(type(value[key]) is bool for key in flags), 'phase snapshot visibility/control flags are invalid')
    if not value['present']:
        need(all(value[key] is False for key in flags) and all(value[key] is None for key in keys - flags - {'present'}),
             'missing sampled element cannot contain invented media/control values')
        return
    if media:
        need(value['tag'] in {'VIDEO', 'AUDIO'} and all(type(value[key]) is bool for key in ('paused', 'ended', 'seeking')),
             'phase media element/flags differ from an actual media snapshot')
        need(value['decoded_cid'] is None or type(value['decoded_cid']) is str and 0 < len(value['decoded_cid']) <= 256,
             'phase decoded CID must be bounded raw observed text')
        need(value['src_sha256'] is None or type(value['src_sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['src_sha256']),
             'phase media source digest is invalid')
        for key in ('current_time', 'video_width', 'video_height'):
            _phase_number(value[key], low=0)
        _phase_number(value['duration'], nullable=True, low=0)
        need(type(value['ready_state']) is int and 0 <= value['ready_state'] <= 4, 'phase readyState is invalid')
    else:
        need(type(value['tag']) is str and re.fullmatch('[A-Z][A-Z0-9-]{0,63}', value['tag'])
             and (value['type'] is None or type(value['type']) is str and len(value['type']) <= 64),
             'phase control tag/type is invalid')
        need(value['value'] is None or type(value['value']) is str and len(value['value'].encode()) <= 8192,
             'phase declared control value exceeds its bounded observation')
        if value['type'] in {'password', 'file', 'hidden'}:
            need(value['value'] is None and value['value_as_number'] is None,
                 'phase private control must not retain input contents')
        for key in ('value_as_number', 'min', 'max', 'step'):
            _phase_number(value[key], nullable=True)


def _phase_selectors(scenario):
    media = set(); controls = set()
    for phase in _PHASES:
        for step in scenario['phases'][phase]:
            if step.get('probe', {}).get('kind') == 'media_state':
                media.add(step['probe']['selector'])
            if step['op'] in {'click', 'fill', 'press', 'select', 'check', 'uncheck'}:
                controls.add(step['selector'])
    need(len(media) <= 4 and len(controls) <= 32, 'phase evidence selector boundary exceeds declared limits')
    return media, controls




def _supplemental_encoded(value):
    """Public JS canonicalJSON bytes for this fixed-key scalar DOM wire."""
    if value is None:
        return b'null'
    if type(value) in {str, bool}:
        return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8', 'backslashreplace')
    if type(value) in {int, float}:
        try:
            number = float(value)
        except (OverflowError, ValueError):
            raise ValueError('supplemental JSON number is not finite') from None
        need(math.isfinite(number), 'supplemental JSON number is not finite')
        if number == 0:
            return b'0'
        negative = number < 0
        mantissa, _, exponent = repr(abs(number)).lower().partition('e')
        point = mantissa.find('.') if '.' in mantissa else len(mantissa)
        digits = mantissa.replace('.', '')
        position = point + (int(exponent) if exponent else 0)
        while digits.startswith('0'):
            digits = digits[1:]; position -= 1
        digits = digits.rstrip('0')
        if 0 < position <= 21:
            text = (digits + '0' * (position - len(digits)) if position >= len(digits)
                    else digits[:position] + '.' + digits[position:])
        elif -6 < position <= 0:
            text = '0.' + '0' * -position + digits
        else:
            power = position - 1
            text = digits[0] + ('.' + digits[1:] if len(digits) > 1 else '') + 'e' + ('+' if power >= 0 else '') + str(power)
        return (('-' if negative else '') + text).encode()
    if type(value) is list:
        return b'[' + b','.join(_supplemental_encoded(item) for item in value) + b']'
    need(type(value) is dict and all(type(key) is str for key in value),
         'supplemental observation is not finite JSON data')
    return b'{' + b','.join(_supplemental_encoded(key) + b':' + _supplemental_encoded(value[key])
                            for key in sorted(value)) + b'}'


def _supplemental_scalar(value):
    need(value is None or type(value) in {bool, str, int, float},
         'supplemental observation must be a JSON scalar')
    need(len(_supplemental_encoded(value)) <= 512, 'supplemental scalar exceeds its 512-byte bound')


def _supplemental_equal(actual, expected):
    # JSON has one numeric type; bool remains distinct from numbers.
    if type(actual) in {int, float} and type(expected) in {int, float}:
        return _supplemental_encoded(actual) == _supplemental_encoded(expected)
    return type(actual) is type(expected) and actual == expected


def supplemental_descriptors(scenario):
    """Return only bounded anonymous DOM checks, without semantic authority."""
    rows = []
    for phase in _PHASES:
        steps = scenario.get('phases', {}).get(phase)
        need(type(steps) is list and 0 < len(steps) <= 64,
             'supplemental source phase is absent or unbounded')
        for index, step in enumerate(steps):
            need(type(step) is dict, 'supplemental source step is not an object')
            if step.get('op') != 'assert':
                continue
            if 'requirement_id' in step or 'checkpoint_id' in step:
                present = [key for key in ('requirement_id', 'checkpoint_id') if key in step]
                need(len(present) == 1 and type(step[present[0]]) is str and step[present[0]],
                     'assertion identity must be present and nonempty or both keys absent')
                continue
            need(set(step) == {'op', 'probe', 'operator', 'expected'},
                 'supplemental assertion cannot name identities, retention or other fields')
            probe = step['probe']
            need(type(probe) is dict and type(probe.get('kind')) is str and probe['kind'] in {'text', 'value', 'json_attribute'},
                 'supplemental probe must be a readonly DOM text/value/attribute observation')
            required = {'kind', 'selector'} | ({'attribute'} if probe['kind'] == 'json_attribute' else set())
            allowed = required | ({'pointer'} if probe['kind'] == 'json_attribute' else set())
            need(required <= set(probe) <= allowed,
                 'supplemental probe cannot add temporal, media, owner or unknown fields')
            selector = probe['selector']
            need(type(selector) is str and selector.strip() and len(selector.encode('utf-16-le', 'surrogatepass')) // 2 <= 512
                 and not re.search(r'[\r\n\x00]', selector)
                 and not re.search(r'data-svd-(?:vda-marker|workflow)|data-(?:fake-)?proof|data-acceptance-passed', selector),
                 'supplemental selector is invalid or names synthetic proof')
            if probe['kind'] == 'json_attribute':
                attribute = probe['attribute']
                need(type(attribute) is str and re.fullmatch(r'data-[a-z0-9-]+', attribute)
                     and not re.search(r'secret|password|token|credential', attribute),
                     'supplemental attribute must be declared nonsensitive DOM data')
                if 'pointer' in probe:
                    pointer = probe['pointer']
                    need(type(pointer) is str and pointer.startswith('/') and len(pointer) <= 2048
                         and re.search(r'~(?![01])', pointer) is None,
                         'supplemental attribute pointer is invalid')
            need(type(step['operator']) is str and step['operator'] in {'equals', 'not_equals', 'contains', 'at_least'},
                 'supplemental assertion operator is unsupported')
            _supplemental_scalar(step['expected'])
            rows.append({'phase': phase, 'step_index': index, 'probe': probe,
                         'operator': step['operator'], 'expected': step['expected']})
    need(len(rows) <= 8 and len(_supplemental_encoded(rows)) <= 2048,
         'supplemental source exceeds its eight-check/2048-byte bound')
    return rows


def validate_supplemental_observations(child, scenario, observation_validator=None):
    """Re-evaluate exact per-child supplemental facts, never required roles."""
    declared = supplemental_descriptors(scenario)
    if 'supplemental_observations' not in child:
        need(not declared, 'final viewport omitted declared supplemental observations')
        return []
    rows = child['supplemental_observations']
    need(type(rows) is list and len(rows) == len(declared) and len(_supplemental_encoded(rows)) <= 4096,
         'supplemental observation count/order or byte bound differs from source')
    for row, source in zip(rows, declared):
        need(type(row) is dict and set(row) == {'phase', 'step_index', 'probe', 'observed'}
             and row['phase'] == source['phase'] and type(row['step_index']) is int
             and row['step_index'] == source['step_index'] and encoded(row['probe']) == encoded(source['probe']),
             'supplemental observation is detached from its exact original source step')
        value = row['observed']
        need(type(value) is dict and set(value) == {'operator', 'actual', 'expected'}
             and value['operator'] == source['operator'], 'supplemental observation shape/operator differs')
        _supplemental_scalar(value['actual']); _supplemental_scalar(value['expected'])
        need(_supplemental_equal(value['expected'], source['expected']),
             'supplemental expected value differs from its exact typed source value')
        operator, actual, expected = value['operator'], value['actual'], value['expected']
        passed = (_supplemental_equal(actual, expected) if operator == 'equals' else
                  not _supplemental_equal(actual, expected) if operator == 'not_equals' else
                  type(actual) is str and type(expected) is str and bool(expected) and expected in actual
                  if operator == 'contains' else
                  type(actual) in {int, float} and type(expected) in {int, float}
                  and expected > 0 and actual >= expected)
        need(passed, 'supplemental actual observation contradicts its expected value')
        if observation_validator is not None:
            observation_validator(value)
    return rows


def validate_phase_evidence(child, scenario):
    """Validate optional actual-step observations, preserving historical V2 absence."""
    if 'phase_evidence' not in child:
        return None
    evidence = child['phase_evidence']
    need(type(evidence) is dict and set(evidence) == {'schema', 'phases'}
         and evidence['schema'] == PHASE_EVIDENCE_SCHEMA and len(encoded(evidence)) <= 131072,
         'phase evidence version/shape/byte bound is invalid')
    phases = evidence['phases']
    need(type(phases) is list and len(phases) == 3, 'phase evidence must retain all three original phases')
    media_selectors, control_selectors = _phase_selectors(scenario)
    supplements = validate_supplemental_observations(child, scenario)
    observations = {(a['phase'], a['step_index']): a['observed']
                    for a in [*child['semantic_assertions'], *child['error_observations'], *supplements]}
    temporal = []; generation = None; finished = 0
    for phase, name in zip(phases, _PHASES):
        need(type(phase) is dict and set(phase) == {'phase', 'generation_before', 'generation_after', 'steps'}
             and phase['phase'] == name and type(phase['generation_before']) is int and phase['generation_before'] >= 0,
             'phase evidence phase/order/generation is invalid')
        if generation is None:
            generation = phase['generation_before']
        need(phase['generation_before'] == generation, 'phase evidence generation continuity changed')
        steps = scenario['phases'][name]; records = phase['steps']
        need(type(records) is list and 0 < len(records) == len(steps) <= 64, 'phase evidence omitted/duplicated an actual original step')
        for index, (record, step) in enumerate(zip(records, steps)):
            need(type(record) is dict and set(record) == {'step_index', 'step', 'generation_before', 'generation_after',
                 'started_ms', 'finished_ms', 'observed', 'temporal_samples', 'media', 'controls', 'reopen'}
                 and type(record['step_index']) is int and record['step_index'] == index
                 and (_supplemental_encoded(record['step']) == _supplemental_encoded(step)
                      if step['op'] == 'assert' and 'requirement_id' not in step and 'checkpoint_id' not in step
                      else encoded(record['step']) == encoded(step)),
                 'phase action differs from its exact original scenario step/order')
            after_generation = generation + (1 if step['op'] == 'reopen_app' else 0)
            need(type(record['generation_before']) is int and type(record['generation_after']) is int
                 and record['generation_before'] == generation and record['generation_after'] == after_generation,
                 'phase action generation is not bound to its actual reopen')
            _phase_number(record['started_ms'], low=finished)
            _phase_number(record['finished_ms'], low=record['started_ms'])
            need(record['finished_ms'] <= 3600000, 'phase action exceeded bounded session observation time')
            finished = record['finished_ms']; generation = after_generation
            expected = observations.get((name, index)) if step['op'] == 'assert' else None
            need(encoded(record['observed']) == encoded(expected), 'phase observed value detached from actual semantic/error probe')
            samples = record['temporal_samples']; need(type(samples) is list, 'phase temporal samples must be explicit')
            if step['op'] == 'assert' and 'temporal_ms' in step['probe']:
                need(len(samples) == 1 and samples[0] in child['temporal_observations'], 'phase temporal sample is not retained by actual probe')
                sample = samples[0]
                need(type(sample) is dict and set(sample) == {'before', 'after', 'sample_ms'}
                     and type(sample['sample_ms']) is int and sample['sample_ms'] == step['probe']['temporal_ms'],
                     'phase temporal sample duration differs from original probe')
                _phase_number(sample['before']); _phase_number(sample['after'])
                need(encoded(sample['after'] - sample['before']) == encoded(expected['actual']), 'phase temporal delta differs from actual assertion')
            else:
                need(samples == [], 'phase action invented an undeclared temporal sample')
            temporal.extend(samples)
            media = record['media']; controls = record['controls']
            need(type(media) is list and len(media) <= 4 and len({m.get('selector') for m in media if type(m) is dict}) == len(media),
                 'phase media selectors are duplicated or unbounded')
            need(type(controls) is list and len(controls) <= 32 and len({m.get('selector') for m in controls if type(m) is dict}) == len(controls),
                 'phase control selectors are duplicated or unbounded')
            for item in controls:
                need(type(item) is dict and set(item) == {'selector', 'before', 'after'} and item['selector'] in control_selectors,
                     'phase control is not a declared original action selector')
                _phase_snapshot(item['before'], media=False); _phase_snapshot(item['after'], media=False)
            for item in media:
                need(type(item) is dict and set(item) == {'selector', 'before', 'after', 'same_element', 'seeked_events'}
                     and item['selector'] in media_selectors, 'phase media is not from a declared media_state probe')
                _phase_snapshot(item['before'], media=True); _phase_snapshot(item['after'], media=True)
                both = all(type(item[key]) is dict and item[key]['present'] for key in ('before', 'after'))
                need(type(item['same_element']) is bool if both else item['same_element'] is None,
                     'phase media ElementHandle identity is not bound to sampled elements')
                events = item['seeked_events']
                need(type(events) is list and len(events) <= 8, 'phase native seek event count exceeds bound')
                for event in events:
                    need(type(event) is dict and set(event) == {'current_time', 'is_trusted'} and type(event['is_trusted']) is bool,
                         'phase native seek event shape is invalid')
                    _phase_number(event['current_time'], low=0)
                if events:
                    target = next((c for c in controls if c['selector'] == step.get('selector')), None)
                    need(step['op'] in {'press', 'fill', 'select'} and target is not None
                         and any(type(target[key]) is dict and target[key]['present'] and target[key]['tag'] == 'INPUT'
                                 and target[key]['type'] == 'range' for key in ('before', 'after')),
                         'phase seek events detached from an actual declared range action')
            if step['op'] == 'reopen_app':
                need(type(record['reopen']) is dict and set(record['reopen']) == {'old_window_disconnected'}
                     and record['reopen']['old_window_disconnected'] is True
                     and {m['selector'] for m in media} == media_selectors
                     and all(m['before'] is not None and m['after'] is not None for m in media),
                     'phase reopen lacks actual disconnected window/media generation observations')
            else:
                need(record['reopen'] is None, 'phase non-reopen action invented a window transition')
            if step.get('checkpoint_id') == 'error_observed':
                need({c['selector'] for c in controls} == control_selectors and all(c['after'] is not None for c in controls),
                     'phase error checkpoint omitted actual declared-control availability')
        need(type(phase['generation_after']) is int and phase['generation_after'] == generation,
             'phase closing generation differs from actual action sequence')
    need(sorted(encoded(s) for s in temporal) == sorted(encoded(s) for s in child['temporal_observations']),
         'phase temporal samples differ from complete actual probe samples')
    return evidence


def _phase_media_summary(value):
    if value is None or not value['present']:
        return value
    return {key: value[key] for key in ('decoded_cid', 'src_sha256', 'current_time', 'duration', 'ready_state', 'paused',
                                       'ended', 'seeking', 'visible', 'video_width', 'video_height')}


def _phase_raw_cid(value):
    if type(value) is not str or not re.fullmatch('b[a-z2-7]{58}', value):
        return False
    try:
        body = value[1:]
        raw = base64.b32decode(body.upper() + '=' * ((8-len(body) % 8) % 8))
        return len(raw) == 36 and raw[:4] == b'\x01\x55\x12\x20' and 'b' + base64.b32encode(raw).decode().rstrip('=').lower() == value
    except ValueError:
        return False


def _phase_owner_cids(child):
    return sorted({value for row in child.get('backend_observations', []) for value in
                   (row.get('result_assertion', {}).get('actual'),)
                   if _phase_raw_cid(value)})


def _phase_identity_pair(before, after, owner_cids, *, same_source=False):
    if not (before and after and before['present'] and after['present']
            and before['ready_state'] >= 2 and after['ready_state'] >= 2
            and before['src_sha256'] and after['src_sha256']):
        return False
    if same_source and before['src_sha256'] != after['src_sha256']:
        return False
    left, right = before['decoded_cid'], after['decoded_cid']
    if left is None and right is None:
        return not owner_cids and before['src_sha256'] == after['src_sha256']
    return _phase_raw_cid(left) and left == right and (not owner_cids or left in owner_cids)


def phase_projection(child, scenario):
    evidence = validate_phase_evidence(child, scenario)
    if evidence is None:
        return None
    owner_cids = _phase_owner_cids(child)
    selected = {'schema': PHASE_EVIDENCE_SCHEMA, 'original_sha256': digest(evidence), 'owner_result_cids': owner_cids,
                'step_count': sum(len(p['steps']) for p in evidence['phases']),
                'seek': None, 'reopen': None, 'failure_controls': None, 'retry_source_values': [], 'probe_temporal_samples': []}
    for phase in evidence['phases']:
        name = phase['phase']
        for row in phase['steps']:
            step = row['step']; index = row['step_index']
            for sample in row['temporal_samples']:
                selected['probe_temporal_samples'].append({'phase': name, 'step_index': index,
                    'probe': step['probe'], **sample})
            if selected['seek'] is None and step['op'] in {'press', 'fill', 'select'}:
                for item in row['media']:
                    before, after = item['before'], item['after']
                    if not (_phase_identity_pair(before, after, owner_cids, same_source=True)
                            and before['visible'] and after['visible'] and before['current_time'] != after['current_time']
                            and any(event['is_trusted'] for event in item['seeked_events'])):
                        continue
                    selected['seek'] = {'phase': name, 'step_index': index, 'action': step,
                        'media_selector': item['selector'], 'before': _phase_media_summary(before), 'after': _phase_media_summary(after),
                        'same_element': item['same_element'],
                        'seeked_events': [next(event for event in item['seeked_events'] if event['is_trusted'])],
                        'native_event_count': len(item['seeked_events']),
                        'untrusted_event_count': sum(not event['is_trusted'] for event in item['seeked_events'])}
                    break
            if step['op'] == 'reopen_app' and selected['reopen'] is None:
                selected['reopen'] = {'phase': name, 'step_index': index, 'generation_before': row['generation_before'],
                    'generation_after': row['generation_after'], 'old_window_disconnected': row['reopen']['old_window_disconnected'],
                    'media': [{'selector': m['selector'], 'before': _phase_media_summary(m['before']),
                               'after': _phase_media_summary(m['after']), 'same_element': m['same_element']} for m in row['media']],
                    'identity_pairs': [{'selector': m['selector'], 'decoded_cid': m['before']['decoded_cid'],
                        'before_src_sha256': m['before']['src_sha256'], 'after_src_sha256': m['after']['src_sha256']}
                        for m in row['media'] if _phase_identity_pair(m['before'], m['after'], owner_cids)]}
            if step.get('checkpoint_id') == 'error_observed':
                selected['failure_controls'] = {'phase': name, 'step_index': index, 'actual_error': row['observed'],
                    'controls': [{'selector': c['selector'], 'after': c['after']} for c in row['controls']]}
            if name == 'failure_recovery' and step['op'] in {'fill', 'select'} and any(
                    old['step'].get('checkpoint_id') == 'error_observed' for old in phase['steps'][:index]):
                target = next((c for c in row['controls'] if c['selector'] == step['selector']), None)
                selected['retry_source_values'].append({'step_index': index, 'selector': step['selector'],
                    'declared_value': step['value'], 'observed_after': target['after'] if target else None})
    return selected


BACKEND_REQUEST_PHASE_SCHEMA = 'swissknife.visual-functional-backend-request-phases.v1'
BACKEND_PHASES = ('primary_result', 'persist_reopen', 'failure_recovery', 'backend_proof', 'unknown')


def _raw_call_sha256(raw):
    # Hash the exact canonical Node call bytes embedded in the raw artifact.
    # Re-encoding with Python would change valid JS number spellings (1e-7).
    text = raw.decode('utf-8'); decoder = json.JSONDecoder(); position = 0
    def whitespace(index):
        while index < len(text) and text[index].isspace():
            index += 1
        return index
    position = whitespace(position)
    need(text[position:position+1] == '{', 'owner artifact is not an object')
    position += 1
    while True:
        position = whitespace(position)
        need(text[position:position+1] != '}', 'owner artifact has no native call')
        key, position = decoder.raw_decode(text, position)
        position = whitespace(position)
        need(text[position:position+1] == ':', 'invalid owner artifact field')
        start = whitespace(position+1); _, end = decoder.raw_decode(text, start)
        if key == 'call':
            return hashlib.sha256(text[start:end].encode('utf-8')).hexdigest()
        position = whitespace(end)
        need(text[position:position+1] == ',', 'owner artifact has no native call')
        position += 1


def validate_backend_request_phases(root, child, scenario):
    """Join native request-time phase witnesses to exact retained owner calls.

    Historical reports without witnesses remain explicitly unphased. No phase
    is guessed from an assertion, receipt timestamp or the final collection step.
    """
    witness = child.get('backend_request_phases')
    observations = child.get('backend_observations', [])
    if witness is None:
        need(all('request_phase_index' not in item for item in observations),
             'phased backend proof has no original request witness')
        return None
    need(type(witness) is dict and set(witness) == {'schema', 'requests'}
         and witness['schema'] == BACKEND_REQUEST_PHASE_SCHEMA and type(witness['requests']) is list
         and len(witness['requests']) == child['backend_call_count'] <= 64,
         'backend request-phase witness schema/count differs')
    requests = witness['requests']; seen = set()
    for index, row in enumerate(requests):
        need(type(row) is dict and set(row) == {'request_index', 'phase', 'step_index', 'generation',
             'binding_id', 'correlation_id', 'call_sha256'} and type(row['request_index']) is int
             and row['request_index'] == index and type(row['phase']) is str and row['phase'] in BACKEND_PHASES
             and type(row['generation']) is int and row['generation'] >= 0
             and type(row['binding_id']) is str and row['binding_id'] in {item['binding_id'] for item in scenario['backend_bindings']}
             and type(row['correlation_id']) is str and row['correlation_id'] and row['correlation_id'] not in seen
             and type(row['call_sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', row['call_sha256']),
             'backend request-phase identity or ordinal differs')
        seen.add(row['correlation_id'])
        if row['phase'] in BACKEND_PHASES[:3]:
            need(type(row['step_index']) is int and 0 <= row['step_index'] < len(scenario['phases'][row['phase']]),
                 'backend request phase has no declared scenario step')
            phase = next((item for item in child.get('phase_evidence', {}).get('phases', []) if item['phase'] == row['phase']), None)
            if phase is not None:
                need(phase['generation_before'] <= row['generation'] <= phase['generation_after'],
                     'backend request generation escaped its actual phase')
        else:
            need(row['step_index'] is None, 'unphased backend request has an invented scenario step')
    need(all(sum(row['phase'] == phase for row in requests) == child['backend_call_phases'][phase]
             for phase in BACKEND_PHASES), 'backend request witnesses disagree with dispatch-phase counts')
    for item in observations:
        index = item.get('request_phase_index')
        need(type(index) is int and 0 <= index < len(requests), 'backend observation lacks its exact request ordinal')
        row = requests[index]
        need(row['binding_id'] == item['binding_id'] and row['correlation_id'] == item['correlation_id'],
             'backend phase belongs to another native result')
        for key in ('receipt_artifact', 'event_artifact'):
            raw = read(root, item[key]); parse(raw)
            need(_raw_call_sha256(raw) == row['call_sha256'], 'backend request phase is detached from retained receipt call bytes')
    return requests


def _scenario_error_checkpoints(scenario):
    """Bind one error and optional before/after-retry saved-PNG observations."""
    allowed = {'error_observed', 'error_image_retained', 'recovery_image_retained'}
    checkpoints = [(phase, index, step) for phase in BACKEND_PHASES[:3]
                   for index, step in enumerate(scenario['phases'][phase]) if 'checkpoint_id' in step]
    need(1 <= len(checkpoints) <= 3
         and all(type(step['checkpoint_id']) is str for _, _, step in checkpoints)
         and len({step['checkpoint_id'] for _, _, step in checkpoints}) == len(checkpoints)
         and all(phase == 'failure_recovery' and step.get('op') == 'assert'
                 and step['checkpoint_id'] in allowed and 'requirement_id' not in step
                 for phase, _, step in checkpoints)
         and all('retained_from' not in step or step.get('checkpoint_id') in allowed - {'error_observed'}
                 for steps in scenario['phases'].values() for step in steps),
         'scenario needs one error and at most one of each typed saved-image checkpoint')
    phase, error_index, original_error = checkpoints[0]
    need(original_error['checkpoint_id'] == 'error_observed', 'scenario lacks its original error checkpoint')
    steps = scenario['phases'][phase]
    def passive(items):
        return all(item.get('op') in {'assert', 'capture', 'wait_ms', 'wait_for'}
                   and not (item.get('op') == 'assert' and (item.get('requirement_id')
                            or item.get('probe', {}).get('kind') == 'backend_result')) for item in items)
    for _, index, image in checkpoints[1:]:
        refs = image.get('retained_from'); probe = image.get('probe')
        need(type(probe) is dict and probe.get('kind') == 'image_state' and 'temporal_ms' not in probe
             and type(refs) is dict and set(refs) == {'primary_result', 'persist_reopen'},
             'saved-image checkpoint must bind both original native image assertions')
        if image['checkpoint_id'] == 'error_image_retained':
            need(index > error_index and passive(steps[error_index + 1:index]),
                 'saved-image error checkpoint must precede recovery UI or owner actions')
        else:
            semantics = [i for i, step in enumerate(steps) if step.get('requirement_id') == 'failure_recovery'
                         and step.get('op') == 'assert']
            need(len(semantics) == 1 and error_index < semantics[0] < index
                 and any(step.get('op') in {'click', 'check', 'uncheck', 'fill', 'select', 'press', 'reopen_app'}
                         for step in steps[error_index + 1:semantics[0]])
                 and all(item.get('op') in {'capture', 'wait_ms', 'wait_for'}
                         for item in [*steps[semantics[0] + 1:index], *steps[index + 1:]]),
                 'saved-image recovery checkpoint must follow the original recovery assertion/action with no later UI or owner action')
        for source_phase, source_index in refs.items():
            source_steps = scenario['phases'][source_phase]
            need(type(source_index) is int and 0 <= source_index < min(64, len(source_steps))
                 and source_steps[source_index].get('op') == 'assert'
                 and source_steps[source_index].get('probe', {}).get('kind') == 'image_state'
                 and 'temporal_ms' not in source_steps[source_index]['probe']
                 and (bool(re.fullmatch(r'result_[1-9][0-9]*', str(source_steps[source_index].get('requirement_id', ''))))
                      if source_phase == 'primary_result' else source_steps[source_index].get('requirement_id') == source_phase),
                 'saved-image baseline is not its exact declared native image assertion')
    return checkpoints


def validate_decoded_images(root, child, scenario, child_path):
    rows = child.get('image_observations', [])
    need(type(rows) is list and len(rows) <= 64, 'native image observation count is unbounded')
    artifacts = {item['path']: item for item in child['artifacts']}
    for row in rows:
        need(type(row) is dict and set(row) == {'phase', 'step_index', 'selector', 'decoded', 'natural_width',
             'natural_height', 'visible_area', 'source_sha256', 'content_sha256', 'image_artifact'}
             and row['phase'] in BACKEND_PHASES[:3] and type(row['step_index']) is int
             and 0 <= row['step_index'] < len(scenario['phases'][row['phase']]), 'image observation has no original step')
        step = scenario['phases'][row['phase']][row['step_index']]
        need(step.get('op') == 'assert' and step.get('probe', {}).get('kind') == 'image_state'
             and step['probe']['selector'] == row['selector'] and row['decoded'] is True
             and all(type(row[k]) is int and row[k] > 0 for k in ('natural_width', 'natural_height'))
             and type(row['visible_area']) in (int, float) and math.isfinite(row['visible_area']) and row['visible_area'] >= 64
             and type(row['source_sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', row['source_sha256']),
             'native decoded image differs from its scenario/decoder facts')
        assertion = next((item for item in child['semantic_assertions'] + child['error_observations']
                          if item['phase'] == row['phase'] and item['step_index'] == row['step_index']), None)
        actual = {key: row[key] for key in ('decoded', 'natural_width', 'natural_height', 'visible_area')}
        if step['probe'].get('pointer') is not None:
            for part in step['probe']['pointer'].split('/')[1:]:
                need(type(actual) is dict and part.replace('~1', '/').replace('~0', '~') in actual, 'native image probe pointer is absent')
                actual = actual[part.replace('~1', '/').replace('~0', '~')]
        need(assertion is not None and 'temporal_ms' not in step['probe']
             and encoded(actual) == encoded(assertion['observed']['actual']),
             'image semantic assertion is detached from native decoder snapshot')
        if row['content_sha256'] is None:
            need(row['image_artifact'] is None, 'image artifact has no encoded source')
            continue
        ref = row['image_artifact']
        need(type(ref) is dict and artifacts.get(ref.get('path')) == ref
             and type(row['content_sha256']) is str and re.fullmatch(r'[0-9a-f]{64}', row['content_sha256']),
             'decoded image escaped its child closure')
        target = check_reference(root, ref, prefix=child_path.parent); raw = read(root, ref['path'])
        need(len(raw) >= 24 and raw[:8] == b'\x89PNG\r\n\x1a\n' and raw[12:16] == b'IHDR'
             and struct.unpack('>II', raw[16:24]) == (row['natural_width'], row['natural_height'])
             and hashlib.sha256(raw).hexdigest() == row['content_sha256']
             and hashlib.sha256(b'data:image/png;base64,' + __import__('base64').b64encode(raw)).hexdigest() == row['source_sha256'],
             'native PNG bytes/dimensions/source identity do not match')
    has_retention = any(step.get('checkpoint_id') in {'error_image_retained', 'recovery_image_retained'}
                        for steps in scenario['phases'].values() for step in steps)
    checkpoints = _scenario_error_checkpoints(scenario) if has_retention else []
    for phase, index, step in checkpoints[1:]:
        if step['checkpoint_id'] == 'recovery_image_retained':
            semantic_index = next(i for i, item in enumerate(scenario['phases'][phase])
                                  if item.get('requirement_id') == 'failure_recovery')
            success = [item for item in child['semantic_assertions']
                       if item.get('phase') == phase and item.get('step_index') == semantic_index
                       and item.get('requirement_id') == 'failure_recovery']
            need(len(success) == 1 and success[0].get('passed') is True,
                 'saved-image recovery checkpoint lacks the original passed recovery assertion')
        references = {phase: index, **step['retained_from']}
        bound = []
        for source_phase, source_index in references.items():
            selector = scenario['phases'][source_phase][source_index]['probe']['selector']
            matches = [row for row in rows if row['phase'] == source_phase
                       and row['step_index'] == source_index and row['selector'] == selector]
            need(len(matches) == 1 and matches[0]['content_sha256'] is not None
                 and matches[0]['image_artifact'] is not None,
                 'saved-image checkpoint lacks its own exact artifact-verified native PNG snapshot')
            bound.append(matches[0])
        identity = lambda row: tuple(row[key] for key in
                                    ('content_sha256', 'source_sha256', 'natural_width', 'natural_height'))
        need(all(identity(row) == identity(bound[0]) for row in bound[1:]),
             'saved PNG source/content/dimensions changed between primary, reopen and retention checkpoint')
    return rows


def validate_dual_workflow(root, profile, task, report, *, observation_validator, backend_validator):
    report = Path(report); owner = path(root, profile['runtimeRoot']) / 'tasks' / task['task_id']
    need(report.is_relative_to(owner), 'final workflow escaped its task namespace')
    data = parse(read(root, str(report.relative_to(root))))
    need(data.get('schema') == PARENT_SCHEMA and data.get('app_id') == task['app_id']
         and data.get('coverage') == 'independent_canonical_sessions' and data.get('passed') is True
         and data.get('actual_desktop') is True and data.get('source_template') is False
         and data.get('work_complete') is False and data.get('completion_authority') is False,
         'final coverage needs current independent viewport workflow V2')
    current = source_snapshot(root, profile, task)
    need(all(data.get(key) == value for key, value in current.items()), 'final workflow source/scenario/controller closure is stale')
    entries = data.get('viewport_reports')
    need(type(entries) is list and len(entries) == 2, 'final workflow omitted an independent canonical viewport')
    retained = check_references(root, data.get('artifacts'), prefix=report.parent)
    app = app_contract(root, profile, task); primary = app['primary_workflow']
    requirements = {f'result_{i+1}': text for i, text in enumerate(primary['expected_results'])}
    requirements.update(persist_reopen=primary['persist_reopen'], failure_recovery=primary['error'] + ' Recovery: ' + primary['recovery'])
    scenario = parse(read(root, 'swissknife/test/e2e/functional-workflows/' + task['app_id'] + '.json'))
    need(scenario.get('schema') == 'swissknife.visual-functional-scenario.v1' and scenario.get('app_id') == task['app_id'],
         'final workflow scenario identity is invalid')
    supplemental_descriptors(scenario)
    scenario_assertions = {}; scenario_errors = []
    for phase in ('primary_result', 'persist_reopen', 'failure_recovery'):
        steps = scenario.get('phases', {}).get(phase)
        need(type(steps) is list, 'final workflow scenario phase is absent')
        for index, step in enumerate(steps):
            if step.get('requirement_id'):
                role = step['requirement_id']
                need(role not in scenario_assertions and step.get('op') == 'assert', 'duplicate or non-assert final requirement')
                scenario_assertions[role] = (phase, index, step)
            if 'checkpoint_id' in step:
                scenario_errors.append((phase, index, step))
    need(set(scenario_assertions) == set(requirements) and scenario_errors == _scenario_error_checkpoints(scenario),
         'final workflow scenario omitted exact requirements or error checkpoint')
    children = []; sessions = set(); expected_artifacts = {}; images = []
    owner_identities = {name: set() for name in ('correlation_id', 'receipt_id', 'event_dag_cid')}
    for entry, viewport in zip(entries, VIEWPORTS):
        name = viewport['name']
        need(type(entry) is dict and set(entry) == {'name', 'viewport', 'report'} and entry['name'] == name
             and entry['viewport'] == {key: viewport[key] for key in ('width', 'height')},
             'final viewport names/order/geometry differ from the canonical contract')
        child_path = check_reference(root, entry['report'], prefix=report.parent / name)
        need(child_path == report.parent / name / 'workflow.json' and retained.get(entry['report']['path']) == entry['report'],
             'final child report was swapped or omitted from parent artifacts')
        child = parse(read(root, entry['report']['path']))
        need(child.get('schema') == CHILD_SCHEMA and child.get('app_id') == task['app_id']
             and child.get('viewport') == viewport and child.get('initial_viewport') == viewport
             and child.get('passed') is True and child.get('actual_desktop') is True and child.get('source_template') is False
             and child.get('work_complete') is False and child.get('completion_authority') is False,
             'final child does not attest its own actual semantic viewport session')
        session = child.get('session_id')
        need(type(session) is str and str(uuid.UUID(session)) == session and uuid.UUID(session).version == 4
             and uuid.UUID(session).variant == uuid.RFC_4122 and session not in sessions,
             'final viewport sessions are missing, copied or duplicated')
        sessions.add(session)
        need(all(child.get(key) == value for key, value in current.items()), 'final child source/scenario/controller closure is stale')
        artifacts = check_references(root, child.get('artifacts'), prefix=child_path.parent)
        assertions = child.get('semantic_assertions')
        need(type(assertions) is list and len(assertions) == len(requirements)
             and {item.get('requirement_id') for item in assertions} == set(requirements),
             'final viewport omitted original result/persistence/recovery semantics')
        for assertion in assertions:
            role = assertion['requirement_id']; phase = 'primary_result' if role.startswith('result_') else role
            declared_phase, declared_index, declared = scenario_assertions[role]
            need(assertion.get('passed') is True and assertion.get('requirement_text') == requirements[role]
                 and assertion.get('phase') == phase == declared_phase and type(assertion.get('step_index')) is int
                 and assertion['step_index'] == declared_index
                 and assertion.get('probe') == declared['probe']
                 and assertion.get('observed', {}).get('operator') == declared['operator']
                 and encoded(assertion.get('observed', {}).get('expected')) == encoded(declared['expected']),
                 'final viewport assertion is detached from the original scenario/requirement')
            observation_validator(assertion.get('observed'))
        checks = child.get('checks'); required_checks = {'primary_result', 'keyboard', name + '_layout', 'error_recovery'}
        need(type(checks) is list and len(checks) == 4 and {item.get('kind') for item in checks} == required_checks
             and all(item.get('passed') is True for item in checks), 'final viewport missing its own semantic/keyboard/layout checks')
        values = {'primary_result': sorted(role for role in requirements if role.startswith('result_')),
                  'keyboard': True, name + '_layout': [], 'error_recovery': ['failure_recovery']}
        for check in checks:
            _observation(check.get('observation'), observation_validator, values[check['kind']], values[check['kind']])
        keyboard = child.get('keyboard_observations')
        need(type(keyboard) is list and keyboard and all(type(item) is dict and item.get('focused') is True
             and item.get('inside_app') is True and item.get('semantic_requirement_id') in requirements for item in keyboard),
             'final viewport lacks actual keyboard-to-semantic observations')
        for item in keyboard:
            phase, index, declared = scenario_assertions[item['semantic_requirement_id']]
            press_index = item.get('step_index')
            steps = scenario['phases'][phase]
            need(item.get('phase') == phase and type(press_index) is int and 0 <= press_index < index
                 and steps[press_index].get('op') == 'press' and item.get('key') == steps[press_index].get('key')
                 and all(step.get('op') in {'assert', 'capture', 'wait_ms', 'wait_for'} for step in steps[press_index+1:index]),
                 'final viewport keyboard result was not observed after its actual scenario keypress')
        errors = child.get('error_observations')
        need(type(errors) is list and len(errors) == len(scenario_errors),
             'final viewport lacks its exact original error checkpoints')
        for error, (error_phase, error_index, error_step) in zip(errors, scenario_errors):
            need(type(error) is dict and error.get('checkpoint_id') == error_step['checkpoint_id']
                 and error.get('phase') == error_phase and type(error.get('step_index')) is int
                 and error['step_index'] == error_index and error.get('probe') == error_step['probe']
                 and error.get('observed', {}).get('operator') == error_step['operator']
                 and encoded(error.get('observed', {}).get('expected')) == encoded(error_step['expected']),
                 'final viewport error observation differs from its exact scenario checkpoint')
            observation_validator(error.get('observed'))
        supplements = validate_supplemental_observations(child, scenario, observation_validator)
        need(not supplements or 'phase_evidence' in child,
             'supplemental observations require their actual source-bound phase evidence')
        temporal = child.get('temporal_observations')
        timed_assertions = [a for a in [*assertions, *errors] if 'temporal_ms' in a['probe']]
        need(type(temporal) is list and len(temporal) == len(timed_assertions), 'final viewport temporal observations missing')
        # Each retained sample must establish the delta in its own assertion.
        unmatched = list(temporal)
        for assertion in timed_assertions:
            matches = [row for row in unmatched if type(row) is dict and set(row) == {'before', 'after', 'sample_ms'}
                       and row['sample_ms'] == assertion['probe']['temporal_ms']
                       and all(type(row[key]) in {int, float} and math.isfinite(row[key]) for key in ('before', 'after'))
                       and encoded(row['after'] - row['before']) == encoded(assertion['observed']['actual'])]
            need(matches, 'final viewport temporal sample is detached from its actual semantic result')
            unmatched.remove(matches[0])
        validate_phase_evidence(child, scenario)
        views = child.get('viewports')
        need(type(views) is list and len(views) == 1 and views[0].get('name') == name
             and views[0].get('viewport') == entry['viewport'] and views[0].get('violations') == [],
             'final child layout is not from its declared canonical viewport')
        bounds = views[0].get('window'); content = views[0].get('primary')
        need(type(bounds) is dict and type(content) is dict
             and all(type(bounds.get(key)) in {int, float} and math.isfinite(bounds[key]) for key in ('left', 'top', 'right', 'bottom'))
             and all(type(content.get(key)) in {int, float} and math.isfinite(content[key]) for key in ('left', 'top', 'width', 'height'))
             and -1 <= bounds['left'] < bounds['right'] <= viewport['width']+1
             and -1 <= bounds['top'] < bounds['bottom'] <= viewport['height']+1
             and content['width'] > 0 and content['height'] > 0
             and bounds['left']-1 <= content['left'] <= content['left']+content['width'] <= bounds['right']+1
             and bounds['top']-1 <= content['top'] < bounds['bottom'],
             'final viewport primary/window geometry is absent or out of bounds')
        layout_name = str((child_path.parent / (name + '-layout.json')).relative_to(root))
        need(layout_name in artifacts and parse(read(root, layout_name)) == {key: value for key, value in views[0].items() if key != 'name'},
             'final viewport layout report is detached from its exact retained observation')
        count = child.get('backend_call_count'); observations = child.get('backend_observations')
        need(type(count) is int and 0 <= count <= 64 and type(observations) is list
             and child.get('unexpected_backend_calls') == 0 and type(child.get('unexpected_backend_calls')) is int,
             'final viewport backend boundary observation is missing')
        phases = child.get('backend_call_phases')
        need(type(phases) is dict and set(phases) == {'primary_result', 'persist_reopen', 'failure_recovery', 'backend_proof', 'unknown'}
             and all(type(value) is int and value >= 0 for value in phases.values()) and sum(phases.values()) == count,
             'final viewport actual backend dispatch phase counts are missing or inconsistent')
        request_phases = validate_backend_request_phases(root, child, scenario)
        validate_decoded_images(root, child, scenario, child_path)
        if app['disposition'] == 'tool_backed':
            need(count > 0 and observations, 'final viewport lacks its own actual owner proof')
            need({item['binding_id'] for item in scenario['backend_bindings']}
                 <= {item.get('binding_id') for item in observations}, 'final viewport omitted a declared owner binding')
            for item in observations:
                need(item.get('app_id') == task['app_id'] and item.get('actual_desktop') is True
                     and item.get('binding_id') in {declared['binding_id'] for declared in scenario['backend_bindings']},
                     'final viewport owner proof is not from this actual app/scenario binding')
                roles = [(role, declared) for role in app.get('backend_roles', []) for declared in role.get('bindings', [])
                         if declared.get('binding_id') == item['binding_id']]
                need(len(roles) == 1 and item['owner'] == roles[0][0]['owner']
                     and item['tool_id'] in roles[0][1]['exact_tool_candidates']
                     and item['transport'] in roles[0][1]['transports'], 'final owner proof exceeded its canonical binding/owner/tool/transport')
                declared_binding = roles[0][1]
                backend_validator(item, app_id=task['app_id'], artifact_paths={path(root, name) for name in artifacts})
                for key in ('receipt_artifact', 'event_artifact'):
                    payload = parse(read(root, item[key]))
                    call = payload.get('call', {}); policy = call.get('input', {}).get('policy', {})
                    need(call.get('binding_id') == item['binding_id'],
                         'final owner raw receipt/event belongs to a different binding')
                    need(call.get('protocol') == 'swissknife.all-app-tool-gateway.v1' and call.get('receipt_required') is True
                         and type(call.get('intent_id')) is str and call['intent_id']
                         and policy.get('dry_run') is False
                         and policy.get('outcome') == ('require_confirmation' if declared_binding['mutates_remote_state'] else 'allow')
                         and policy.get('consent') == ('granted' if declared_binding['mutates_remote_state'] else 'not_required')
                         and (not declared_binding['mutates_remote_state']
                              or call.get('input', {}).get('payload', {}).get('fixture_scope') == scenario.get('fixture_scope')),
                         'final raw owner proof was a preview, unconfirmed or outside its isolated scenario')
                declared_results = [step for phase in scenario['phases'].values() for step in phase
                    if step.get('op') == 'assert' and step.get('probe', {}).get('kind') == 'backend_result'
                    and step['probe'].get('binding_id') == item['binding_id']]
                possible = [{'pointer': step['probe']['pointer'], 'operator': step['operator'], 'expected': step['expected']}
                            for step in declared_results]
                intent = next(value for value in scenario['backend_bindings'] if value['binding_id'] == item['binding_id'])
                if type(intent.get('result_assertion')) is dict:
                    possible.append(intent['result_assertion'])
                observed_result = item['result_assertion']
                need(any(all(encoded(observed_result.get(key)) == encoded(declared.get(key))
                             for key in ('pointer', 'operator', 'expected')) for declared in possible),
                     'final owner proof result differs from its declared backend probe/fallback intent')
            for assertion in [*assertions, *errors]:
                probe = assertion['probe']
                if probe.get('kind') != 'backend_result':
                    continue
                need(any(item.get('binding_id') == probe.get('binding_id')
                         and item['result_assertion'].get('pointer') == probe.get('pointer')
                         and all(encoded(item['result_assertion'].get(key)) == encoded(assertion['observed'][key])
                                 for key in ('operator', 'actual', 'expected'))
                         and (request_phases is None or request_phases[item['request_phase_index']]['phase'] == assertion['phase']
                              and request_phases[item['request_phase_index']]['step_index'] <= assertion['step_index'])
                         for item in observations),
                     'final semantic backend result is detached from its actual raw owner proof')
            for key, previous in owner_identities.items():
                observed = {item.get(key) for item in observations}
                need(all(type(value) is str and value for value in observed) and not previous & observed,
                     'final mobile viewport reused desktop owner correlation/receipt/event evidence')
                previous.update(observed)
        else:
            need(count == 0 and observations == [], 'final viewport violated its local/external backend boundary')
        image = child.get('result_screenshot'); image_path = check_reference(root, image, prefix=child_path.parent)
        need(image_path == child_path.parent / (name + '.png') and artifacts.get(image['path']) == image,
             'final result image was swapped or omitted from child artifacts')
        png = read(root, image['path'])
        need(len(png) > 128 and png[:8] == b'\x89PNG\r\n\x1a\n' and png[12:16] == b'IHDR'
             and struct.unpack('>II', png[16:24]) == (viewport['width'], viewport['height']),
             'final result image does not match its actual canonical viewport dimensions')
        need(any(Path(record['path']).name == 'trace.zip' for record in artifacts.values()), 'final viewport trace is missing')
        expected_artifacts[entry['report']['path']] = entry['report']; expected_artifacts.update(artifacts)
        children.append({'entry': entry, 'data': child}); images.append(image)
    need(retained == expected_artifacts, 'final parent artifacts differ from both exact child closures')
    return {'data': data, 'report': reference(root, report), 'children': children, 'images': images,
            'source_identity_sha256': digest(current['source_sha256'])}


def task_identity(task):
    return digest({key: value for key, value in task.items() if key != 'status'})


def binding(task, validated):
    return {'schema': 'swissknife.final-viewport-model-evidence.v1', 'task_id': task['task_id'],
            'app_id': task['app_id'], 'task_semantics_sha256': task_identity(task),
            'report': validated['report'],
            'children': [child['entry']['report'] for child in validated['children']],
            'images': validated['images'], 'source_identity_sha256': validated['source_identity_sha256']}


def review_join(root, profile, task, expected, review_path, *, require_pass=True):
    need(task.get('kind') in {'verify', 'final-app-verify'}, 'independent review needs an app verification contract')
    """Verify exact producer/body/image binding in the immutable model context."""
    from swissknife_visual_functional_llm import validate_model_receipt
    need(type(expected) is dict and set(expected) == {'schema', 'task_id', 'app_id', 'task_semantics_sha256',
         'report', 'children', 'images', 'source_identity_sha256'}
         and expected['schema'] == 'swissknife.final-viewport-model-evidence.v1'
         and expected['task_id'] == task['task_id'] and expected['app_id'] == task['app_id']
         and expected['task_semantics_sha256'] == task_identity(task), 'final model evidence contract differs')
    parent = check_reference(root, expected['report'])
    need(parent.is_relative_to(path(root, profile['runtimeRoot']) / 'tasks' / task['task_id'])
         and Path(review_path) == parent.parent / 'visual-review.json', 'final review escaped its exact producer attempt')
    need(type(expected['children']) is list and len(expected['children']) == 2
         and type(expected['images']) is list and len(expected['images']) == 2,
         'final review lacks exact two children/images')
    for record, viewport in zip(expected['children'], VIEWPORTS):
        need(check_reference(root, record) == parent.parent / viewport['name'] / 'workflow.json',
             'final review child identity differs')
    for record, viewport in zip(expected['images'], VIEWPORTS):
        need(check_reference(root, record) == parent.parent / viewport['name'] / (viewport['name'] + '.png'),
             'final review image identity/order differs')
    review_path = Path(review_path)
    receipt = parse(read(root, str(review_path.relative_to(root)), 8 * 1024 * 1024))
    validate_model_receipt(root, receipt, task_id=task['task_id'], mode='review', require_visual=True)
    native = receipt.get('native_observation', {}); stream = native.get('native_grok_progress', {})
    need(native.get('native_grok_usage_observed') is True and native.get('native_grok_envelope_observed') is True
         and all(stream.get(key) is True for key in ('stdout_eof', 'stderr_eof', 'process_exit_observed', 'stream_complete', 'response_usable'))
         and stream.get('stream_tainted') is False and stream.get('text_truncated') is False
         and stream.get('timed_out') is False and stream.get('returncode') == 0
         and type(stream.get('returncode')) is int and stream.get('final_event_type') == 'end'
         and stream.get('final_reason_code') == 'end_turn', 'final review lacks completed clean native Grok evidence')
    session = receipt.get('invocation_id')
    need(type(session) is str and str(uuid.UUID(session)) == session and uuid.UUID(session).version == 4
         and uuid.UUID(session).variant == uuid.RFC_4122,
         'final review lacks its unique native invocation identity')
    immutable = path(root, receipt.get('attempt_receipt_path', ''))
    need(immutable == parent.parent / 'model-invocations' / ('visual-review-' + session + '.json')
         and read(root, str(immutable.relative_to(root)), 8 * 1024 * 1024) == read(root, str(review_path.relative_to(root)), 8 * 1024 * 1024),
         'final review differs from its immutable native invocation receipt')
    parent_data = parse(read(root, expected['report']['path']))
    need(receipt.get('router_source_sha256') == parent_data.get('source_sha256', {}).get('external/ipfs_accelerate/ipfs_accelerate_py/llm_router.py'),
         'final review used a router outside its source-bound workflow contract')
    decision = receipt['response']['decision']
    need(decision == 'pass' if require_pass else decision in {'needs_changes', 'blocked'},
         'final visual review is missing its required positive/negative decision')
    need(receipt['screenshots'] == [{'path': item['path'], 'sha256': item['sha256'], 'size_bytes': item['bytes'],
                                    'width': viewport['width'], 'height': viewport['height']}
                                     for item, viewport in zip(expected['images'], VIEWPORTS)],
         'final review used stale, swapped or unrelated images/viewport dimensions')
    contexts = []
    for item in receipt.get('input_files', []):
        if Path(str(item.get('path', ''))).name != 'context.json':
            continue
        record = {'path': item['path'], 'sha256': item['sha256'], 'bytes': item['size_bytes']}
        context_path = check_reference(root, record, prefix=parent.parent / 'model-inputs')
        context = parse(read(root, record['path']))
        if 'final_workflow_evidence' in context:
            need(context['final_workflow_evidence'] == expected and context.get('task', {}).get('task_id') == task['task_id']
                 and context['task'].get('app_id') == task['app_id'] and context['task'].get('kind') == task['kind'],
                 'final model context was rebound to different workflow/source/semantics')
            contexts.append(record)
    need(len(contexts) == 1, 'final review lacks one exact immutable workflow/source context')
    return {'schema': JOIN_SCHEMA, 'task_id': task['task_id'], 'app_id': task['app_id'],
            'task_semantics_sha256': task_identity(task), 'workflow': expected['report'],
            'children': expected['children'], 'images': expected['images'],
            'source_identity_sha256': expected['source_identity_sha256'],
            'review': reference(root, review_path), 'review_context': contexts[0]}



_PHASE_FACT_FIELDS = {
    'seek': {'phase', 'step_index', 'action', 'media_selector', 'before', 'after', 'same_element',
             'seeked_events', 'native_event_count', 'untrusted_event_count'},
    'reopen': {'phase', 'step_index', 'generation_before', 'generation_after', 'old_window_disconnected',
               'media', 'identity_pairs'},
    'failure_controls': {'phase', 'step_index', 'actual_error', 'controls'},
}
_MEDIA_PROJECTION_FIELDS = {'decoded_cid', 'src_sha256', 'current_time', 'duration', 'ready_state', 'paused',
                            'ended', 'seeking', 'visible', 'video_width', 'video_height'}
_CONTROL_PROJECTION_FIELDS = {'present', 'tag', 'type', 'visible', 'enabled', 'value', 'value_as_number', 'min', 'max', 'step'}
_LEGACY_SHARED_SEMANTICS = ('projection_value_ref selects exact typed JSON from shared_projection_values. '
    'overrides replaces named fields only; no deletion. Expand in the same slot. '
    'Shared values imply no shared session/element/event/phase. Original reports stay distinct.')

_PREVIOUS_SHARED_SEMANTICS = ('projection_value_ref: exact same-slot typed shared_projection_values; overrides replace fields, never delete. Equality implies no shared session/element/event/phase.')
_SHARED_SEMANTICS = 'Same-slot typed refs; overrides replace; equality is not identity.'


def _projection_snapshot_slots(result):
    slots = []
    for view in result['viewports']:
        phase = view.get('phase_evidence', {})
        seek = phase.get('seek')
        if type(seek) is dict and 'projection_value_ref' not in seek:
            slots.extend((seek, key, _MEDIA_PROJECTION_FIELDS) for key in ('before', 'after'))
        reopen = phase.get('reopen')
        if type(reopen) is dict and 'projection_value_ref' not in reopen:
            for media in reopen['media']:
                slots.extend((media, key, _MEDIA_PROJECTION_FIELDS) for key in ('before', 'after'))
        failure = phase.get('failure_controls')
        if type(failure) is dict and 'projection_value_ref' not in failure:
            slots.extend((control, 'after', _CONTROL_PROJECTION_FIELDS) for control in failure['controls'])
        slots.extend((retry, 'observed_after', _CONTROL_PROJECTION_FIELDS)
                     for retry in phase.get('retry_source_values', []))
    return slots


_LEGACY_REVIEW_LITERAL_SEMANTICS = ('The shared_review_literals_reference_key names same-slot references to exact typed JSON in shared_review_literals. '
    'Table entries are literal, not links. Expand before phase shared values. No facts are omitted; identical values imply no shared session, element, call or event.')

_PREVIOUS_REVIEW_LITERAL_SEMANTICS = ('shared_review_literals_reference_key selects same-slot literal JSON in shared_review_literals; expand before phase values. No facts lost or shared session/element/call/event implied.')
_REVIEW_LITERAL_SEMANTICS = 'Key selects literal table first; equality is not identity.'


def _review_dictionary_keys(value):
    keys = set()
    def visit(item):
        if type(item) is dict:
            keys.update(item)
            for child in item.values(): visit(child)
        elif type(item) is list:
            for child in item: visit(child)
    visit(value)
    return keys


def _expand_review_literals(value):
    result = parse(encoded(value))
    table = result.pop('shared_review_literals', None)
    caption = result.pop('shared_review_literals_semantics', None)
    marker = result.pop('shared_review_literals_reference_key', None)
    if table is None:
        need(caption is None and marker is None, 'review literal metadata is incomplete')
        return result
    need(type(table) is dict and 0 < len(table) <= 64
         and all(type(key) is str and re.fullmatch(r'r[0-9]+', key) for key in table)
         and caption in {_REVIEW_LITERAL_SEMANTICS, _PREVIOUS_REVIEW_LITERAL_SEMANTICS, _LEGACY_REVIEW_LITERAL_SEMANTICS} and type(marker) is str
         and re.fullmatch(r'review_ref(?:_[0-9]+)?', marker)
         and marker not in _review_dictionary_keys(table), 'review literal table/key/semantics are malformed or cyclic')
    used = set()
    def visit(item):
        if type(item) is dict:
            if marker in item:
                need(set(item) == {marker} and type(item[marker]) is str and item[marker] in table,
                     'review literal reference is unknown or collides with fields')
                key = item[marker]; used.add(key)
                return parse(encoded(table[key]))
            return {key: visit(child) for key, child in item.items()}
        if type(item) is list: return [visit(child) for child in item]
        return item
    result = visit(result)
    need(used == set(table), 'review literal table has unreachable or unused values')
    return result


def _factor_review_literals(value):
    """Deduplicate exact JSON literals with a marker absent from every input key."""
    original = encoded(value)
    need(not {'shared_review_literals','shared_review_literals_semantics','shared_review_literals_reference_key'} & set(value),
         'projection already has review literal metadata')
    keys = _review_dictionary_keys(value); marker = 'review_ref'; index = 0
    while marker in keys:
        index += 1; marker = 'review_ref_' + str(index)
    groups = {}
    owner_fields = {'backend_observations', 'additional_backend_phase_proofs'}
    def contains_owner(item):
        if type(item) is dict: return bool(owner_fields & set(item)) or any(contains_owner(child) for child in item.values())
        return type(item) is list and any(contains_owner(child) for child in item)
    def collect(item, path=()):
        if path and path[-1] in owner_fields: return  # Owner JSON and raw reference records stay literal.
        raw = encoded(item)
        if path and len(raw) >= 48 and type(item) in {dict, list, str} and not contains_owner(item): groups.setdefault(raw, []).append(path)
        if type(item) is dict:
            for key, child in item.items(): collect(child, (*path, key))
        elif type(item) is list:
            for index, child in enumerate(item): collect(child, (*path, index))
    collect(value)
    candidates = []
    for raw, paths in groups.items():
        gain = (len(raw) - len(encoded({marker: 'r63'}))) * len(paths) - len(raw) - 7
        if len(paths) > 1 and gain > 0: candidates.append((gain, raw, paths))
    result = parse(original); table = {}
    # Never store a subtree after a descendant changed: all entries stay literal.
    for _, raw, paths in sorted(candidates, key=lambda row: (-row[0], row[1])):
        if len(table) == 64: break
        slots = []
        for path in paths:
            owner = result
            try:
                for part in path[:-1]: owner = owner[part]
                if encoded(owner[path[-1]]) == raw: slots.append((owner, path[-1]))
            except (KeyError, IndexError, TypeError): continue
        key = 'r' + str(len(table)); ref = {marker: key}
        if len(slots) < 2 or (len(raw) - len(encoded(ref))) * len(slots) <= len(raw) + len(key) + 5: continue
        table[key] = parse(raw)
        for owner, field in slots: owner[field] = ref.copy()
    if table:
        result['shared_review_literals'] = table
        result['shared_review_literals_semantics'] = _REVIEW_LITERAL_SEMANTICS
        result['shared_review_literals_reference_key'] = marker
    need(encoded(_expand_review_literals(result)) == original, 'review literal factoring changed typed evidence')
    return result if len(encoded(result)) < len(original) else value


def _expand_projection(value):
    """Invert presentation factoring only at known typed slots; never raw payloads."""
    result = _expand_review_literals(value)
    table = result.pop('shared_projection_values', None)
    caption = result.pop('shared_projection_values_semantics', None)
    need(table is None or type(table) is dict and 0 < len(table) <= 16
         and all(type(key) is str and re.fullmatch(r'v[0-9]+', key) for key in table),
         'projection shared values table is malformed')
    need((table is None and caption is None) or (table is not None and caption in {_SHARED_SEMANTICS, _PREVIOUS_SHARED_SEMANTICS, _LEGACY_SHARED_SEMANTICS}),
         'projection shared values semantics are absent or changed')
    used = set()
    def expand(item, fields, *, overrides=False):
        if type(item) is not dict or 'projection_value_ref' not in item:
            return item
        need(table is not None and set(item) <= {'projection_value_ref', 'overrides'}
             and type(item['projection_value_ref']) is str and item['projection_value_ref'] in table,
             'projection reference is unknown or collides with literal fields')
        key = item['projection_value_ref']; base = table[key]
        need(type(base) is dict and set(base) == fields and 'projection_value_ref' not in base,
             'projection shared base has wrong typed shape or a cyclic reference')
        changes = item.get('overrides', {})
        need(type(changes) is dict and set(changes) <= fields and (overrides or not changes),
             'projection overrides cannot add or delete fields')
        used.add(key)
        return {**base, **changes}
    for view in result['viewports']:
        phase = view.get('phase_evidence', {})
        for key, fields in _PHASE_FACT_FIELDS.items():
            if key in phase:
                phase[key] = expand(phase[key], fields)
    for owner, key, fields in _projection_snapshot_slots(result):
        owner[key] = expand(owner[key], fields, overrides=True)
    need(table is None or used == set(table), 'projection shared table has unused or unreachable references')
    return result


def _factor_projection(value):
    """Losslessly fit repeated typed facts; all source/session/owner data stay literal."""
    need('shared_projection_values' not in value and 'shared_projection_values_semantics' not in value,
         'projection input collides with shared presentation fields')
    original = encoded(value)
    # Reject marker collisions even when the ordinary projection already fits.
    _expand_projection(value)
    if len(original) <= 18000:
        return value
    result = parse(original); table = {}
    slots = _projection_snapshot_slots(result)
    # Bounded deterministic base selection, using typed encoded equality.
    for _ in range(8):
        best = None
        for owner, key, fields in slots:
            base = owner[key]
            if type(base) is not dict or set(base) != fields:
                continue
            ident = 'v' + str(len(table)); options = []
            saving = -len(encoded(base)) - len(ident) - 5
            for other, field, expected in slots:
                actual = other[field]
                if expected != fields or type(actual) is not dict or set(actual) != fields:
                    continue
                changes = {name: item for name, item in actual.items() if encoded(item) != encoded(base[name])}
                ref = {'projection_value_ref': ident}
                if changes:
                    ref['overrides'] = changes
                gain = len(encoded(actual)) - len(encoded(ref))
                if gain > 0:
                    options.append((other, field, ref)); saving += gain
            if best is None or saving > best[0]:
                best = (saving, base, ident, options)
        if best is None or best[0] <= 0:
            break
        _, base, ident, options = best; table[ident] = base
        for owner, key, ref in options:
            owner[key] = ref
    for name in _PHASE_FACT_FIELDS:
        groups = {}
        for view in result['viewports']:
            phase = view.get('phase_evidence', {}); item = phase.get(name)
            if type(item) is dict:
                groups.setdefault(encoded(item), []).append(phase)
        for raw, owners in groups.items():
            ident = 'v' + str(len(table)); ref = {'projection_value_ref': ident}
            if len(owners) > 1 and len(raw) * len(owners) > len(raw) + len(encoded(ref)) * len(owners) + len(ident) + 5:
                table[ident] = parse(raw)
                for owner in owners:
                    owner[name] = ref
    if table:
        result['shared_projection_values'] = table
        result['shared_projection_values_semantics'] = _SHARED_SEMANTICS
    if len(encoded(result)) > 18000:
        result = _factor_review_literals(result)
    need(encoded(_expand_projection(result)) == original, 'projection factoring changed typed evidence values')
    return result


def _project_backend_observations(root, child, child_path):
    """Present retained observations without inferring a phase or stronger result."""
    artifacts = {item['path']: item for item in child['artifacts']}
    result = []; additional = []; representatives = {}
    requests = validate_backend_request_phases(root, child, parse(read(root, 'swissknife/test/e2e/functional-workflows/' + child['app_id'] + '.json'))) if child.get('backend_request_phases') is not None else None
    for index, item in enumerate(child['backend_observations']):
        projected = {key: item[key] for key in ('owner', 'tool_id', 'binding_id', 'transport',
            'outcome', 'receipt_verified', 'semantic_result_verified')}
        assertion = item['result_assertion']
        if child.get('backend_request_phases') is not None:
            request = requests[item['request_phase_index']]
            projected['request_phase'] = {key: request[key] for key in ('request_index', 'phase', 'step_index')}
        projected['result_assertion'] = {key: assertion[key] for key in ('pointer', 'operator')}
        for key in ('actual', 'expected'):
            value = assertion[key]
            projected['result_assertion'][key] = value if len(encoded(value)) <= 1024 else {
                'projection_omitted': True, 'original_bytes': len(encoded(value)),
                'original_sha256': digest(value),
                'original_child_pointer': '/backend_observations/' + str(index) + '/result_assertion/' + key}
        for kind in ('receipt', 'event'):
            name = item[kind + '_artifact']; record = artifacts.get(name)
            need(record is not None, 'projected backend artifact is absent from its child closure')
            check_reference(root, record, prefix=child_path.parent)
            projected[kind + '_artifact'] = ({**record, 'path': str(Path(record['path']).relative_to(child_path.parent.relative_to(root)))}
                if requests is not None else record)
        if requests is not None:
            request = requests[item['request_phase_index']]
            identity = encoded({'request': request, 'correlation_id': item['correlation_id'],
                'receipt_id': item['receipt_id'], 'event_dag_cid': item['event_dag_cid'],
                'receipt_artifact': projected['receipt_artifact'], 'event_artifact': projected['event_artifact'],
                'owner': projected['owner'], 'tool_id': projected['tool_id'], 'binding_id': projected['binding_id'],
                'transport': projected['transport'], 'outcome': projected['outcome'],
                'receipt_verified': projected['receipt_verified'], 'semantic_result_verified': projected['semantic_result_verified']})
            if identity in representatives:
                row = result[representatives[identity]]
                row.setdefault('additional_result_assertions', []).append({
                    'observation_index': index, 'result_assertion': projected['result_assertion']})
                continue
            projected['request_phase'] = {key: request[key] for key in ('request_index', 'phase', 'step_index', 'generation', 'correlation_id', 'call_sha256')}
        else:
            identity = None
        projected['observation_index'] = index
        if identity is not None: representatives[identity] = len(result)
        result.append(projected)
    return result, additional


def projection(root, report):
    """Bound semantic context; complete immutable observations remain retained."""
    data = parse(read(root, str(Path(report).relative_to(root))))
    need(data.get('schema') == PARENT_SCHEMA, 'final projection needs independent viewport evidence')
    result = {'schema': 'swissknife.visual-functional-review-input.v2', 'projection_only': True,
              'original': reference(root, report), 'original_schema': PARENT_SCHEMA,
              'app_id': data['app_id'], 'passed': data['passed'], 'actual_desktop': data['actual_desktop'],
              'source_template': data['source_template'], 'coverage': data['coverage'],
              'contract_sha256': data['contract_sha256'], 'scenario_sha256': data['scenario_sha256'],
              'source_identity_sha256': digest(data['source_sha256']), 'source_file_count': len(data['source_sha256']),
              'scenario_phase_order': ['primary_result', 'persist_reopen', 'failure_recovery'],
              'step_index_semantics': 'Zero-based per phase; resets to 0.',
              'backend_call_phases_semantics': 'Dispatch counts: not validity flags; backend_proof=0:no call; request_phase:exact join.',
              'viewports': []}
    scenario = parse(read(root, 'swissknife/test/e2e/functional-workflows/' + data['app_id'] + '.json'))
    for entry in data['viewport_reports']:
        child_path = check_reference(root, entry['report'], prefix=Path(report).parent)
        child = parse(read(root, entry['report']['path']))
        owner_rows, additional_owner_rows = _project_backend_observations(root, child, child_path)
        decoded_images = validate_decoded_images(root, child, scenario, child_path)
        result['viewports'].append({'name': entry['name'], 'viewport': child['viewport'],
            'session_id': child['session_id'],
            'original': entry['report'], 'result_screenshot': child['result_screenshot'],
            'checks': [{'kind': item['kind'], 'passed': item['passed']} for item in child['checks']],
            'semantic_assertions': [{'requirement_id': item['requirement_id'], 'requirement_text': item['requirement_text'],
                'phase': item['phase'], 'step_index': item['step_index'], 'probe': item['probe'],
                'passed': item['passed'], 'observed_sha256': digest(item['observed']),
                'observed': item['observed'] if len(encoded(item['observed'])) <= 1024 else {
                    'projection_omitted': True, 'original_bytes': len(encoded(item['observed'])),
                    'original_sha256': digest(item['observed'])}} for item in child['semantic_assertions']],
            'keyboard_observation_count': len(child['keyboard_observations']),
            'error_observation_count': len(child['error_observations']),
            'error_observations': [{'phase': item['phase'], 'step_index': item['step_index'], 'probe': item['probe'],
                'checkpoint_id': item['checkpoint_id'],
                **({'retained_from': scenario['phases'][item['phase']][item['step_index']]['retained_from']}
                   if item['checkpoint_id'] in {'error_image_retained', 'recovery_image_retained'} else {}),
                'observed_sha256': digest(item['observed']),
                'observed': item['observed'] if len(encoded(item['observed'])) <= 1024 else {
                    'projection_omitted': True, 'original_bytes': len(encoded(item['observed'])),
                    'original_sha256': digest(item['observed'])}} for item in child['error_observations']],
            'temporal_observation_count': len(child['temporal_observations']),
            'backend_observation_count': len(child['backend_observations']),
            **({'decoded_images': [{k: row[k] for k in ('phase', 'step_index', 'selector', 'decoded', 'natural_width', 'natural_height', 'content_sha256', 'source_sha256', 'image_artifact')} for row in decoded_images]} if decoded_images else {}),
            'backend_observations': owner_rows,
            **({'additional_backend_phase_proofs': additional_owner_rows} if additional_owner_rows else {}),
            'backend_call_count': child['backend_call_count'],
            'backend_call_phases': child['backend_call_phases'],
            'layout': child['viewports'][0]})
        supplements = validate_supplemental_observations(child, scenario)
        if supplements:
            result['viewports'][-1]['supplemental_observations'] = supplements
        phase = phase_projection(child, scenario)
        if phase is not None:
            result['viewports'][-1]['phase_evidence'] = phase
    if any('request_phase' in row for view in result['viewports'] for row in view['backend_observations']):
        result['backend_artifact_path_base'] = 'viewport_original_directory'
    result['instruction'] = ('Inspect both results. Initial/demo/layout-only mobile state cannot prove mobile execution. '
        'Owner results: without an inferred phase or broader success. Each phased row is one request; additional_result_assertions use that same request. Unphased rows imply no identity. '
        'HTMLMediaElement/CID facts only. Phased receipt/event paths are relative to viewport original directory; filenames contain raw CIDs.')
    if any(view.get('decoded_images') for view in result['viewports']):
        result['instruction'] += ' retained_from:IMG source/content/dims, not canvas/layers.'
    result = _factor_projection(result)
    need(len(encoded(result)) <= 18000, 'final review projection exceeds its bounded prompt share')
    return result


def _failure_path(root, profile, task):
    return path(root, profile['runtimeRoot']) / 'tasks' / task['task_id'] / 'failed-final-review-source-fence.json'


def _review_identity(root, profile, task):
    return {'task_semantics_sha256': task_identity(task),
            'source_snapshot': source_snapshot(root, profile, task), 'route': profile['llm']}


def assert_final_review_allowed(root, profile, task):
    target = _failure_path(root, profile, task)
    if not target.exists() and not target.is_symlink():
        return
    value = parse(read(root, str(target.relative_to(root)), private=True))
    need(type(value) is dict and set(value) == {'schema', 'task_id', 'app_id', 'task_contract', 'identity', 'evidence', 'failed_review',
         'work_complete', 'completion_authority'} and value['schema'] == FAILURE_SCHEMA
         and value['task_id'] == task['task_id'] and value['app_id'] == task['app_id']
         and value['work_complete'] is False and value['completion_authority'] is False,
         'final failed-review source fence is malformed')
    old_task = value['task_contract']
    need(type(old_task) is dict and old_task.get('task_id') == task['task_id'] and old_task.get('app_id') == task['app_id']
         and old_task.get('kind') == 'final-app-verify' and old_task.get('edit_paths') == [] and old_task.get('checks') == [],
         'final failed-review historical task policy is malformed')
    check_reference(root, value['failed_review'])
    # Historical source changes may requalify admission; immutable failure
    # receipt/context/image references must remain authentic before either path.
    review_join(root, profile, old_task, value['evidence'], path(root, value['failed_review']['path']), require_pass=False)
    need(type(value['identity']) is dict and set(value['identity']) == {'task_semantics_sha256', 'source_snapshot', 'route'}
         and value['identity']['task_semantics_sha256'] == task_identity(old_task)
         and digest(value['identity']['source_snapshot']['source_sha256']) == value['evidence']['source_identity_sha256'],
         'final failed-review source identity was rebound')
    snapshot = value['identity']['source_snapshot']; parent = parse(read(root, value['evidence']['report']['path']))
    need(type(snapshot) is dict and set(snapshot) == {'contract_sha256', 'scenario_sha256', 'source_sha256'}
         and all(parent.get(key) == data for key, data in snapshot.items())
         and type(value['identity']['route']) is dict and value['identity']['route'].get('provider') == 'grok_cli'
         and value['identity']['route'].get('model') == 'grok-4.7'
         and value['identity']['route'].get('allowLocalFallback') is False
         and value['identity']['route'].get('allowCrossProviderFallback') is False,
         'final failed-review fence source/route differs from its retained original')
    if value['identity'] == _review_identity(root, profile, task):
        raise ValueError('unchanged_final_app_visual_review: source is unchanged since the genuine failed dual-viewport review; scoped remediation is required')


def remember_failed_review(root, profile, task, validated, review_path):
    expected = binding(task, validated)
    review_join(root, profile, task, expected, review_path, require_pass=False)
    identity = _review_identity(root, profile, task)
    need(digest(identity['source_snapshot']['source_sha256']) == expected['source_identity_sha256'],
         'final sources changed before failure fence persistence')
    value = {'schema': FAILURE_SCHEMA, 'task_id': task['task_id'], 'app_id': task['app_id'],
             'task_contract': {key: value for key, value in task.items() if key != 'status'},
             'identity': identity, 'evidence': expected, 'failed_review': reference(root, review_path),
             'work_complete': False, 'completion_authority': False}
    target = _failure_path(root, profile, task)
    need(target.resolve() == target and not target.is_symlink(), 'final failed-review fence path is unsafe')
    temporary = target.parent / ('.failed-final-review-' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded(value) + b'\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, target)
        fd = os.open(target.parent, os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)


def validate_final_task_contract(root, profile, task, spec=None):
    need(task.get('kind') == 'final-app-verify' and task.get('checks') == [] and task.get('edit_paths') == [],
         'final app verification is readonly and cannot create repair admissions')
    need(not {'recovery_edit_paths', 'semantic_recovery_command'} & set(task),
         'final app verification cannot acquire hidden recovery edit/command authority')
    spec = spec or parse(read(root, profile['taskSpecPath']))
    original = next((item for item in spec['tasks'] if item['task_id'] == task.get('original_verify_task')), None)
    need(original is not None and original.get('kind') == 'verify' and original.get('app_id') == task['app_id'],
         'final app verification lacks its original same-app verification contract')
    originals = {item['task_id'] for item in spec['tasks'] if item.get('kind') == 'verify' and item.get('app_id')}
    need(len(originals) == 45 and originals | {'SVF-043', 'SVF-044'} <= set(task.get('dependencies', [])),
         'final app verification must wait for all original app repairs and accepted backend foundations')
    return original


def final_task_map(root, profile, owner_task, spec=None):
    spec = spec or parse(read(root, profile['taskSpecPath']))
    apps = parse(read(root, profile['appContractPath']))['apps']
    names = {app['app_id'] for app in apps}; mapping = owner_task.get('final_app_tasks')
    need(len(apps) == len(names) == 45 and type(mapping) is dict and set(mapping) == names
         and all(type(value) is str for value in mapping.values()) and len(set(mapping.values())) == 45,
         'final regression/aggregate needs one exact fresh verification task for each of 45 canonical apps')
    indexed = {item['task_id']: item for item in spec['tasks']}
    for app_id, task_id in mapping.items():
        task = indexed.get(task_id)
        need(task is not None and task.get('app_id') == app_id, 'final coverage task mapping has a missing/swapped app')
        validate_final_task_contract(root, profile, task, spec)
    if owner_task.get('kind') == 'regression':
        need(set(mapping.values()) <= set(owner_task.get('dependencies', [])), 'final regression omitted fresh app dependencies')
    return mapping, indexed


def coverage(root, profile, owner_task, *, validate_task, retained_report, validate_report, spec=None):
    mapping, indexed = final_task_map(root, profile, owner_task, spec)
    groups = []
    tasks = [indexed[mapping[app_id]] for app_id in sorted(mapping)]
    with source_snapshot_transaction(root, profile, tasks):
        for task in tasks:
            receipt = validate_task(profile, task)
            directory = path(root, profile['runtimeRoot']) / 'tasks' / task['task_id']
            report = retained_report(profile, task, receipt, directory / 'verification')
            validated = validate_report(profile, task, report)
            join = review_join(root, profile, task, binding(task, validated), report.parent / 'visual-review.json')
            groups.append({'app_id': task['app_id'], 'task_id': task['task_id'],
                           'task_receipt': reference(root, directory / 'receipt.json'), 'review_join': join})
    return {'schema': COVERAGE_SCHEMA, 'task_id': owner_task['task_id'], 'final_app_tasks': mapping,
            'app_count': 45, 'fresh_positive_visual_review_count': 45, 'groups': groups,
            'work_complete': False, 'completion_authority': False}


def validate_coverage(root, profile, owner_task, receipt, *, validate_task, retained_report, validate_report):
    directory = path(root, profile['runtimeRoot']) / 'tasks' / owner_task['task_id']
    records = [item for item in receipt['artifacts'] if Path(item['path']).name == 'final-app-coverage.json']
    need(len(records) == 1, 'final regression receipt lacks one explicit app/review coverage manifest')
    target = check_reference(root, records[0], prefix=directory)
    expected = coverage(root, profile, owner_task, validate_task=validate_task,
                        retained_report=retained_report, validate_report=validate_report)
    need(parse(read(root, str(target.relative_to(root)))) == expected,
         'final regression coverage is stale or lost a current per-app visual review join')
    return expected


def retained_final_report(root, profile, task, receipt, directory, *, validate_report):
    directory = Path(directory)
    owner = path(root, profile['runtimeRoot']) / 'tasks' / task['task_id']
    need(directory == owner / 'verification', 'final workflow receipt escaped its verification owner')
    candidates = []
    all_reports = []
    for record in receipt.get('artifacts', []):
        if Path(str(record.get('path', ''))).name != 'workflow.json':
            continue
        target = path(root, record['path']); all_reports.append(record)
        if target.parent.parent == directory and re.fullmatch(r'attempt-[A-Za-z0-9_-]{6,80}', target.parent.name):
            candidates.append(record)
    need(len(candidates) == 1, 'final task must retain one immutable independent workflow producer attempt')
    record = candidates[0]; report = check_reference(root, record, prefix=directory)
    expected = ['node', 'swissknife/scripts/run-visual-functional-workflow.mjs', '--app', task['app_id'],
                '--contracts', profile['appContractPath'], '--output-dir', str(report.parent), '--independent-viewports']
    producers = [check for check in receipt.get('checks', []) if check.get('argv') == expected
                 and type(check.get('exit_code')) is int and check['exit_code'] == 0]
    need(len(producers) == 1, 'final workflow lacks its exact successful independent-viewports producer invocation')
    validated = validate_report(profile, task, report)
    expected_reports = {record['path']: record,
                        **{child['entry']['report']['path']: child['entry']['report'] for child in validated['children']}}
    need({record['path']: record for record in all_reports} == expected_reports and len(all_reports) == 3,
         'final task retained a missing, duplicate or foreign child workflow')
    retained = {item['path']: item for item in receipt['artifacts']}
    need(all(retained.get(item['path']) == item for item in validated['data']['artifacts']),
         'final task receipt omitted exact child evidence artifacts')
    return report
