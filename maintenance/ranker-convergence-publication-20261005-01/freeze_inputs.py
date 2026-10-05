"""Freeze the complete publication selection after the root final seal is quiet.

No classifier, codec, native tools, Git or remote operations are present. The
final plan and builder are externally pinned; generated outputs are not selected
into the package, avoiding self-reference. The plan is retained in HF separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import types

ROOT = Path('/home/barberb/lift_coding/maintenance/ranker-convergence-publication-20261005-01')


def freeze(plan, expected_plan_sha256, expected_builder_sha256):
    if not __debug__:
        raise ValueError('pinned reader assertions must remain enabled')
    if re.fullmatch('[0-9a-f]{64}', expected_builder_sha256 or '') is None:
        raise ValueError('independent exact final builder SHA256 required')
    builder = ROOT / 'build_package.py'
    if builder.resolve(strict=True) != builder or builder.is_symlink():
        raise ValueError('canonical final builder source required')
    raw = builder.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_builder_sha256:
        raise ValueError('externally pinned builder differs')
    module = types.ModuleType('held_convergence_input_freeze')
    module.__file__ = str(builder)
    exec(compile(raw, str(builder), 'exec'), module.__dict__)
    reader = module.load_source('reader')
    own_pin = reader.pin(Path(__file__).resolve())
    body, plan_pin, documents, facts = module.check_plan(reader, Path(plan), expected_plan_sha256)
    selected, exclusions, directories = module.inventory(reader, body, documents)
    selection_path, closure_path = ROOT / 'final-selection.json', ROOT / 'closed-inputs.json'
    if selection_path.exists() or closure_path.exists():
        raise ValueError('fresh final selection and closed-inputs required')
    selection_pin = reader.write(selection_path, {'schema': 'ranker-convergence-publication-final-selection@1', 'files': selected,
        'exclusions': exclusions, 'directories': directories})
    closure_pin = reader.write(closure_path, {'schema': 'ranker-convergence-publication-closed-inputs@1', 'plan': plan_pin,
        'final_selection': selection_pin, 'preparation_source': own_pin, 'publication_profile': module.PROFILE})
    module.check_closed(reader, closure_path, closure_pin['sha256'])
    if reader.pin(builder)['sha256'] != expected_builder_sha256 or reader.pin(Path(__file__).resolve()) != own_pin or reader.pin(Path(plan)) != plan_pin:
        raise ValueError('executed builder/preparation/plan changed')
    return {'closed_inputs': closure_pin, 'final_selection': selection_pin, 'selected_files': len(selected),
        'selected_bytes': sum(row['bytes'] for row in selected), 'native_qualification_jobs': 0, 'codec_calls': 0, 'remote_mutations': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--expected-plan-sha256', required=True)
    parser.add_argument('--expected-builder-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(freeze(args.plan, args.expected_plan_sha256, args.expected_builder_sha256), sort_keys=True))
