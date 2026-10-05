"""Convert the freshly merged datasets candidate using frozen original logic.

The failed stale-baseline generation is preserved. The new candidate contains
the captured published main before any unpublished history is rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import types
from pathlib import Path

BASE = Path(__file__).resolve().parent
DRIVER = BASE / 'prepare_datasets_hf_history.py'
DRIVER_SHA = '2f56b6c4c86221d1215034bae9e6cc56ad8c972e7d1b206aa60b3a0666437b03'
FAILED = BASE / 'datasets-hf-history-conversion-01'
FAILED_STATE_SHA = '6f8efb904fbcab2e36330f588b1570c3cc3e3be99d2d82c73ffa72afe79d949e'
FAILED_RECEIPT_SHA = '0fcdf22f1e87b5f82df0b7a504cda26440c884e70725c4b967408a9a7d3495a1'
REFRESH = BASE.parent / 'refresh_main_candidate.py'
REFRESH_SHA = '8c20d17e5c0936abca0423854a22fe91433aa0c58227260a47756dedef06d4e8'
PLAN = BASE / 'datasets-main-refresh-01/plan.json'
PLAN_SHA = '2c532c3ba159eb5cab229cd7c01f98e1b6157f80a39ecc90555b794bc936aa18'
PREPARED = BASE / 'datasets-main-refresh-01/prepared.json'
PREPARED_SHA = 'bf15a9181cc0403497c1c7c45f15fa5b191e509a7549e48309998a363719b0fa'
EXPECTED_TIP = '23540627b1cf6515df0fd84c9417b4cbdb91234a'


def driver():
    with DRIVER.open('rb') as stream:
        data = stream.read(65537)
    if len(data) > 65536 or hashlib.sha256(data).hexdigest() != DRIVER_SHA:
        raise ValueError('frozen original datasets driver differs')
    module = types.ModuleType('frozen_datasets_driver')
    module.__file__ = str(DRIVER)
    exec(compile(data, str(DRIVER), 'exec'), module.__dict__)
    module.PLAN, module.PLAN_SHA = PLAN, PLAN_SHA
    module.PREPARED, module.PREPARED_SHA = PREPARED, PREPARED_SHA
    module.EXPECTED_TIP = EXPECTED_TIP
    return module


def provenance(module):
    failed_state_pin, state = module.fixed_json(FAILED / 'original-state.json', FAILED_STATE_SHA)
    failed_receipt_pin, _ = module.fixed_json(FAILED / 'prepare-failure.json', FAILED_RECEIPT_SHA)
    refresh_pin = module.binding(REFRESH)
    if refresh_pin['sha256'] != REFRESH_SHA:
        raise ValueError('frozen refresh helper differs')
    prior = {key: value for key, value in state.items() if key not in ('schema', 'content_sha256')}
    return [failed_state_pin, failed_receipt_pin, module.binding(DRIVER)], refresh_pin, prior


def invoke(module, operation, directory, receipt_pin):
    prior_pins, refresh_pin, prior_state = provenance(module)
    _, plan = module.fixed_json(PLAN, PLAN_SHA)
    _, prepared = module.fixed_json(PREPARED, PREPARED_SHA)
    if prepared['refreshed_prior_plan_binding']['sha256'] != '96c24ebbd82ddde08e3fec44ccc158f956165cf5ef9bae4c1e9a18414496b353':
        raise ValueError('refreshed source candidate selects another original generation')
    owner = module.owner()
    module.preserved(prior_state, owner.source_state(module.SOURCE, plan['authoritative_source']['selected_files']))
    original_write = module.write

    def qualified_write(path, value):
        if Path(path).name == 'preflight.json':
            value = {**value, 'recovery_driver_binding': module.binding(Path(__file__).resolve()),
                     'prior_failed_attempt_bindings': prior_pins, 'refresh_helper_binding': refresh_pin,
                     'prior_original_state_verified_preserved': True,
                     'live_main_merged_before_conversion': True,
                     'scope': 'Fresh isolated capture after ordinary published-main merge and full canonical restoration; failed stale-baseline attempt is unchanged.'}
        return original_write(path, value)

    module.write = qualified_write
    if operation == 'prepare':
        result = module.prepare(directory)
    else:
        _, _, preflight = module.selected_preflight(directory)
        if preflight['recovery_driver_binding'] != module.binding(Path(__file__).resolve()):
            raise ValueError('frozen recovery implementation changed')
        if preflight['prior_failed_attempt_bindings'] != prior_pins or preflight['refresh_helper_binding'] != refresh_pin:
            raise ValueError('prior failure or refreshed-source lineage differs')
        result = (module.convert if operation == 'convert' else module.package)(directory, receipt_pin)
    module.preserved(prior_state, owner.source_state(module.SOURCE, plan['authoritative_source']['selected_files']))
    provenance(module)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'convert', 'package'))
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--hf-publication-receipt-binding', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    module = driver()
    try:
        receipt_pin = None
        if args.operation != 'prepare':
            if args.hf_publication_receipt_binding is None:
                parser.error('conversion/packaging requires an external HF receipt file binding')
            receipt_pin = json.loads(args.hf_publication_receipt_binding.read_bytes())
        result = invoke(module, args.operation, args.directory, receipt_pin)
    except Exception as error:
        if args.directory.is_dir():
            failure = args.directory / (args.operation + '-failure.json')
            if not failure.exists():
                module.write(failure, {'schema': 'isolated-hf-history-operation-failure/v1',
                    'operation': args.operation, 'error_type': type(error).__name__,
                    'error': str(error) if isinstance(error, ValueError) else None,
                    'partial_generation_preserved': True, 'origin_push_executed': False,
                    'hf_upload_executed': False, 'training_executed': False})
        raise
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
