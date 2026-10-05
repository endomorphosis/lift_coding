"""Freeze publication selection only after the root's exact final seal is quiet.

The externally pinned plan supplies fixed documents, observed facts, exclusions,
and addition paths. This producer never runs a classifier, codec, native proof,
dependency setup, Git, or remote call. Its two outputs are never self-selected.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import types

ROOT = Path('/home/barberb/lift_coding/maintenance/ranker-curvature-publication-source-plan-20261005-01')


def freeze(*, plan, expected_plan_sha256, expected_builder_sha256):
    if type(expected_plan_sha256) is not str or re.fullmatch('[0-9a-f]{64}', expected_plan_sha256) is None:
        raise ValueError('independent exact final-plan SHA256 required')
    if type(expected_builder_sha256) is not str or re.fullmatch('[0-9a-f]{64}', expected_builder_sha256) is None:
        raise ValueError('independent exact final-builder SHA256 required')
    plan = Path(plan)
    if plan != ROOT / 'plan.json' or plan.resolve(strict=True) != plan:
        raise ValueError('fixed canonical root-owned final plan required')
    builder = ROOT / 'build_package.py'
    raw_builder = builder.read_bytes()
    if hashlib.sha256(raw_builder).hexdigest() != expected_builder_sha256:
        raise ValueError('executed final builder source pin differs')
    module = types.ModuleType('curvature_frozen_publication_preparation')
    module.__file__ = str(builder)
    exec(compile(raw_builder, str(builder), 'exec'), module.__dict__)
    reader = module.load_source(*module.HELPERS['reader'], 'curvature_frozen_preparation_reader')
    plan_pin = reader.pin(plan)
    if plan_pin['sha256'] != expected_plan_sha256:
        raise ValueError('externally pinned final plan differs')
    specification = json.loads(reader.read_regular(plan)[0])
    if specification.get('schema') != 'ranker-curvature-publication-plan@1':
        raise ValueError('root-frozen publication plan schema required')
    fixed = {'source_and_artifacts_quiet', 'scope_root', 'excluded_dependency_subtrees', 'publication_profile',
             'documents', 'semantic_policy', 'expected_sealed_file_count', 'expected_sealed_file_bytes',
             'excluded_zero_byte_locks', 'external_dependencies', 'explicit_addition_paths', 'semantic_roles'}
    if not fixed <= set(specification):
        raise ValueError('all final closure plan fields required')
    closure = {key: specification[key] for key in fixed - {'explicit_addition_paths'}}
    closure['schema'] = 'ranker-curvature-publication-closed-inputs@1'
    policy = closure['semantic_policy']
    policy_path = module.descriptor(policy)
    if reader.pin(policy_path) != policy:
        raise ValueError('root-frozen observed fact policy pin differs')
    closure['required_facts'] = json.loads(reader.read_regular(policy_path)[0])
    addition_paths = specification['explicit_addition_paths']
    if type(addition_paths) is not list or len(addition_paths) != len(set(addition_paths)) or not all(type(p) is str for p in addition_paths):
        raise ValueError('unique fixed explicit addition paths required')
    required_sources = (ROOT / 'build_package.py', ROOT / 'review_package.py', ROOT / 'freeze_inputs.py',
                        ROOT / 'publication-profile-authorization.json', plan, ROOT / 'required-facts.json')
    if not {str(p) for p in required_sources} <= set(addition_paths):
        raise ValueError('all executed publication tools/plan/policy must be explicitly selected')
    closure['explicit_additions'] = [reader.pin(Path(path)) for path in addition_paths]
    own_pin = reader.pin(Path(__file__).resolve())
    closure['preparation_source'] = own_pin
    closure['externally_pinned_plan'] = plan_pin
    closed_path, selection_path = ROOT / 'closed-inputs.json', ROOT / 'final-selection.json'
    if closed_path.exists() or selection_path.exists():
        raise ValueError('fresh closure and selection output files required')
    files, exclusions, directories = module.inventory(reader, closure['explicit_additions'], closure['excluded_zero_byte_locks'])
    # Bind the full sealed population before materializing either final file.
    documents = {name: json.loads(reader.read_regular(module.descriptor(row))[0])
                 for name, row in closure['documents'].items()}
    module.verify_seal(reader, closure, documents, files, exclusions)
    selected = {'schema': 'ranker-curvature-publication-final-selection@1',
                'files': [{**reader.pin(path), 'stat': reader.signature(path.lstat())} for path in files],
                'exclusions': exclusions, 'directories': directories}
    closure['final_selection'] = reader.write(selection_path, selected)
    # The external closed-inputs SHA binds selection and selected tool bytes,
    # without a circular demand that either output include its own digest.
    closed_pin = reader.write(closed_path, closure)
    module.check_closed_inputs(reader, closed_path, closed_pin['sha256'])
    module.verify_final_selection(reader, closure, files, exclusions, directories)
    if module.inventory(reader, closure['explicit_additions'], closure['excluded_zero_byte_locks']) != (files, exclusions, directories):
        raise ValueError('selected population/stat changed during input freeze')
    if reader.pin(builder)['sha256'] != expected_builder_sha256 or reader.pin(plan) != plan_pin or reader.pin(Path(__file__).resolve()) != own_pin:
        raise ValueError('executed preparation/builder/plan changed')
    for helper, expected in module.HELPERS.values():
        if reader.pin(helper)['sha256'] != expected:
            raise ValueError('frozen reader/scanner helper changed')
    return {'closed_inputs': closed_pin, 'final_selection': closure['final_selection'],
            'selected_files': len(files), 'selected_bytes': sum(row['bytes'] for row in selected['files']),
            'new_native_jobs': 0, 'remote_mutations': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--expected-plan-sha256', required=True)
    parser.add_argument('--expected-builder-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(freeze(plan=args.plan, expected_plan_sha256=args.expected_plan_sha256,
                            expected_builder_sha256=args.expected_builder_sha256), sort_keys=True))
