"""Select the normally refreshed root candidate for exact weight coalescing.

The earlier original remote-tracking cache advanced externally. Only the two
explicit old-to-new origin main cache joins below are excepted when checking
that earlier cutoff; active refs, HEAD, index and source bytes stay exact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import types
from pathlib import Path

BASE = Path(__file__).resolve().parent
WRAPPER = BASE / 'prepare_root_hf_history_recovery.py'
WRAPPER_SHA = 'd0e355cc65c5acc91a0fb3ee74e02b946115ee58dbf48aef26c7532aa4ef53fc'
PLAN = BASE / 'root-main-refresh-01/plan.json'
PLAN_SHA = 'bbbe6a6a257c2d52f25c9e7be200a0b2cb0401f1ecff5c8cf2b81791b84f3b27'
PREPARED = BASE / 'root-main-refresh-01/prepared.json'
PREPARED_SHA = '13ed6e930d5ac16345fbebde570f73ecf73d323e1609594621bcc970649bcf14'
EXPECTED_TIP = '9d1944b9a9fd95abbb6297b4c7d34a1312809f14'
OLD_MAIN = 'cc5d5bf9fa40bd9a8834d8fb61a03a4724033297'
CURRENT_MAIN = 'e8994ea6003fdd1f1fe061550bb190c70ba011dc'
TRACKING_CHANGES = [{'ref': ref, 'before': OLD_MAIN, 'after': CURRENT_MAIN}
                    for ref in ('refs/remotes/origin/HEAD', 'refs/remotes/origin/main')]


def wrapper():
    with WRAPPER.open('rb') as stream:
        data = stream.read(65537)
    if len(data) > 65536 or hashlib.sha256(data).hexdigest() != WRAPPER_SHA:
        raise ValueError('frozen first coalescing wrapper differs')
    module = types.ModuleType('frozen_root_coalescing_wrapper')
    module.__file__ = str(WRAPPER)
    exec(compile(data, str(WRAPPER), 'exec'), module.__dict__)
    return module


def adjusted_loader(selected):
    original_loader = selected.load_verified

    def load(path, digest, name):
        module = original_loader(path, digest, name)
        if path == selected.DRIVER:
            module.PLAN, module.PLAN_SHA = PLAN, PLAN_SHA
            module.PREPARED, module.PREPARED_SHA = PREPARED, PREPARED_SHA
            module.EXPECTED_TIP = EXPECTED_TIP
            initial_preserved, initial_write = module.preserved, module.write

            def preserve_cutoff(before, after):
                old = dict(row.split(' ', 1) for row in before['refs'])
                new = dict(row.split(' ', 1) for row in after['refs'])
                adjusted = dict(old)
                for change in TRACKING_CHANGES:
                    ref = change['ref']
                    if old.get(ref) == change['before'] and new.get(ref) == change['after']:
                        adjusted[ref] = change['after']
                return initial_preserved({**before, 'refs': sorted(ref + ' ' + oid for ref, oid in adjusted.items())}, after)

            def scope_write(path, value):
                if Path(path).name == 'preflight.json':
                    value = {**value, 'latest_recovery_driver_binding': module.binding(Path(__file__).resolve()),
                             'refreshed_prior_plan_binding': module.binding(PLAN),
                             'refreshed_prior_prepared_binding': module.binding(PREPARED),
                             'external_original_tracking_cache_changes': TRACKING_CHANGES,
                             'captured_original_active_ref_HEAD_index_source_preserved': True,
                             'prior_remote_tracking_cache_unchanged_claimed': False}
                return initial_write(path, value)

            module.preserved, module.write = preserve_cutoff, scope_write
        return module

    selected.load_verified = load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'convert', 'package'))
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--hf-publication-receipt-binding', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    selected = wrapper()
    adjusted_loader(selected)
    module = selected.load_verified(selected.DRIVER, selected.DRIVER_SHA, 'frozen_refreshed_root_driver')
    receipt_pin = None
    if args.operation != 'prepare':
        if args.hf_publication_receipt_binding is None:
            parser.error('conversion/packaging requires an external HF receipt binding')
        receipt_pin = json.loads(args.hf_publication_receipt_binding.read_bytes())
        _, _, preflight = module.selected_preflight(args.directory)
        if preflight['latest_recovery_driver_binding'] != module.binding(Path(__file__).resolve()):
            raise ValueError('latest frozen recovery driver differs')
    try:
        result = selected.invoke(module, args.operation, args.directory, receipt_pin)
    except Exception as error:
        if args.directory.is_dir():
            path = args.directory / (args.operation + '-failure.json')
            if not path.exists():
                module.write(path, {'schema': 'isolated-hf-history-operation-failure/v1',
                    'operation': args.operation, 'error_type': type(error).__name__,
                    'error': str(error) if isinstance(error, ValueError) else None,
                    'partial_generation_preserved': True, 'origin_push_executed': False,
                    'hf_upload_executed': False, 'training_executed': False})
        raise
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
