"""Recover root model-weight conversion with exact existing-pointer coalescing.

Preserves the failed generation and frozen original driver. Only independently
verified coalescing code replaces its collision rule; no publication occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import types
from pathlib import Path

BASE = Path(__file__).resolve().parent
DRIVER = BASE / 'prepare_root_hf_history.py'
DRIVER_SHA = 'be8be8c1432826b365a05ac04abc262c9c5fd44721b25810e0b2bdbf4d123bc1'
COALESCER = BASE / 'convert_history_hf_coalescing.py'
COALESCER_SHA = 'acb7f5c50aadc03c40ce438d890954a149e53a01c746b56fcbc31861b799d01a'
FAILED = BASE / 'root-hf-history-conversion-01'
FAILED_PREFLIGHT_SHA = '26a12d3ebbcc71aebc4751ce90b4239647e9d4bce327aae95d210f9225e72f5f'
FAILED_RECEIPT_SHA = '5b71396ab36f5a7f7748ffebcb6744d374e589a616e57ceeee0e07f5f9da7956'
FAILED_SELECTION_SHA = '253f4f4f3ca672632b4f2b310ffcf80b29c8510efd23309deb7f8da1bc0e516f'


def load_verified(path, digest, name):
    with path.open('rb') as stream:
        data = stream.read(65537)
    if len(data) > 65536 or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('selected frozen implementation differs')
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    return module


def invoke(module, operation, directory, receipt_pin):
    coalescer = load_verified(COALESCER, COALESCER_SHA, 'frozen_exact_pointer_coalescer')
    prior_pin, prior = module.fixed_json(FAILED / 'preflight.json', FAILED_PREFLIGHT_SHA)
    failure_pin, _ = module.fixed_json(FAILED / 'convert-failure.json', FAILED_RECEIPT_SHA)
    selection_pin, _ = module.fixed_json(FAILED / 'artifact-selection.json', FAILED_SELECTION_SHA)
    prior_bindings = [prior_pin, failure_pin, selection_pin, module.binding(DRIVER)]
    plan = module.read_selected(prior['selected_plan_binding'])
    base_owner = module.owner
    original_write = module.write
    last_result = {}

    def selected_owner():
        owner = base_owner()

        def rewrite(repository, tip, published_commits, references):
            result = coalescer.rewrite_unpublished(repository, tip, published_commits, references)
            last_result.update(result)
            return result

        owner.rewrite_unpublished = rewrite
        return owner

    module.owner = selected_owner

    def qualified_write(path, value):
        if Path(path).name == 'preflight.json':
            value = {**value, 'recovery_driver_binding': module.binding(Path(__file__).resolve()),
                     'coalescing_implementation_binding': module.binding(COALESCER),
                     'prior_failed_attempt_bindings': prior_bindings,
                     'adjacent_collision_policy': coalescer.COLLISION_POLICY}
        elif Path(path).name == 'conversion.json':
            value = {**value, 'coalesced_tree_occurrences': last_result['coalesced_tree_occurrences'],
                     'adjacent_collision_policy': coalescer.COLLISION_POLICY,
                     'coalescing_implementation_binding': module.binding(COALESCER),
                     'scope': 'Exact historical weight path/blob substitutions; an existing adjacent reference is retained only if its selected canonical HF blob identity and regular-file mode match exactly. Other collisions reject.'}
        return original_write(path, value)

    module.write = qualified_write
    module.preserved(prior['original_state'], base_owner().source_state(module.SOURCE, plan['authoritative_source']['selected_files']))
    if operation == 'prepare':
        result = module.prepare(directory)
    else:
        _, _, preflight = module.selected_preflight(directory)
        if preflight['recovery_driver_binding'] != module.binding(Path(__file__).resolve()):
            raise ValueError('frozen recovery driver differs')
        if preflight['coalescing_implementation_binding'] != module.binding(COALESCER):
            raise ValueError('frozen coalescing implementation differs')
        if preflight['prior_failed_attempt_bindings'] != prior_bindings:
            raise ValueError('preserved failed generation differs')
        result = (module.convert if operation == 'convert' else module.package)(directory, receipt_pin)
    module.preserved(prior['original_state'], base_owner().source_state(module.SOURCE, plan['authoritative_source']['selected_files']))
    module.fixed_json(FAILED / 'preflight.json', FAILED_PREFLIGHT_SHA)
    load_verified(COALESCER, COALESCER_SHA, 'verified_coalescer_after_operation')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'convert', 'package'))
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--hf-publication-receipt-binding', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    module = load_verified(DRIVER, DRIVER_SHA, 'frozen_root_hf_driver')
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
