"""Scan the explicitly pinned final selection and freeze the HF upload plan.

Archive shards are also independently classified by the closed package producer.
This step creates local files only and does not import project code or upload.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import types

WORKSPACE = Path('/home/barberb/lift_coding')
HF = WORKSPACE / 'maintenance/terminal-ir-publication-20261004-01/huggingface'
HELPERS = {
    'publisher': (HF / 'publish_successor_evidence_02.py', '670e064a8222ce1b0c962e202985974741a9a4476630b0541c7ec880b32009f2'),
    'archive': (HF / 'build_evidence_archive_02.py', 'f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036'),
    'classifier': (HF / 'classify_and_prepare_public_archive_07.py', 'dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8'),
    'reader': (HF / 'successor-source-model-package-03/build_package.py', '8c8eab266a053115cdf0ea11a8aea5323611c2ab049ec1541383831618e385ce'),
}
PREFIX = 'releases/20261004-terminal-codebase-ir-evidence-v1'
NAMESPACE = PREFIX + '/successor-ranker-trace-v1/'
MUTABLE = {'README.md', PREFIX + '/publication-status.json'}
SCAN_REMOTE = NAMESPACE + 'publication/metadata-scan-closed.json'


def need(condition, message):
    if condition is not True:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--expected-selection-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    publisher_path, publisher_sha = HELPERS['publisher']
    raw = publisher_path.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == publisher_sha, 'frozen reader changed')
    reader = types.ModuleType('frozen_metadata_publisher')
    reader.__file__ = str(publisher_path)
    exec(compile(raw, str(publisher_path), 'exec'), reader.__dict__)
    own_pin = reader.pin(Path(__file__).resolve())
    selection_pin, data = reader.stable_read(args.selection, retain_plan_bytes=True)
    need(selection_pin['sha256'] == args.expected_selection_sha256, 'explicit selection changed')
    selection = json.loads(data)
    need(selection['schema'] == 'terminal-ranker-trace-final-HF-selection@1'
         and selection['repo_id'] == 'Publicus/codebase-ir-proof-index', 'explicit root selection required')
    files = selection['files']
    need(3 <= len(files) < 100, 'selected file population bound')
    names = set()
    for item in files:
        name = item['remote']
        need(name not in names and not name.startswith('/') and '..' not in Path(name).parts
             and (name in MUTABLE or name.startswith(NAMESPACE)), 'unsafe/duplicate destination')
        names.add(name)
        need(item['local']['bytes'] <= 256 * 1024**2 and reader.pin(Path(item['local']['path'])) == item['local'],
             'selected file binding changed')
    need(MUTABLE.issubset(names), 'both explicit mutable pointers required')
    need(SCAN_REMOTE not in names, 'producer scan receipt destination must be reserved')
    # The root reviews the exact package receipts before constructing this
    # externally pinned selection. Every selected file is scanned below.
    package = selection['qualified_package_shards']
    need(isinstance(package, list) and len(package) > 0 and len({p['path'] for p in package}) == len(package),
         'exact qualified shard population required')
    selected_by_path = {item['local']['path']: item['local'] for item in files}
    for binding in package:
        need(selected_by_path.get(binding['path']) == binding and reader.pin(Path(binding['path'])) == binding,
             'qualified shard binding changed')
    need(len(selection['package_closure_and_review']) == 2, 'both package closure and independent review required')
    expected_outcomes = (
        ('ranker-trace-local-package-attempt@1', 'passed_local_frozen_package'),
        ('ranker-trace-full-decoded-member-file-only-review@1', 'passed'),
    )
    for descriptor, expected_outcome in zip(selection['package_closure_and_review'], expected_outcomes):
        binding, content = reader.stable_read(Path(descriptor['path']), retain_plan_bytes=True)
        need(binding == descriptor, 'package closure or review changed')
        document = json.loads(content)
        need((document.get('schema'), document.get('status')) == expected_outcome
             and selected_by_path.get(descriptor['path']) == descriptor, 'exact qualified package closure/review required')

    modules, helper_pins = {}, {}
    for name in ('archive', 'classifier', 'reader'):
        path, expected = HELPERS[name]
        binding, source = reader.stable_read(path, retain_plan_bytes=True)
        need(binding['sha256'] == expected, 'executed helper source changed')
        module = types.ModuleType('frozen_metadata_' + name)
        module.__file__ = str(path)
        exec(compile(source, str(path), 'exec'), module.__dict__)
        modules[name], helper_pins[name] = module, binding
    archive, classifier, file_reader = modules['archive'], modules['classifier'], modules['reader']
    scanner = archive.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in archive.PATTERNS if name != 'private_key_pem']
    budget = classifier.Budget(seconds=180, decoded_bytes=512 * 1024**2,
                               container_bytes=16 * 1024**2, members=10000, depth=6)
    output = args.output
    need(output.is_absolute() and output.resolve() == output and not output.exists()
         and output.parent.is_dir() and output.is_relative_to(WORKSPACE / 'maintenance'), 'new canonical output required')
    output.mkdir(mode=0o700)
    state = {'schema': 'terminal-ranker-trace-supplemental-metadata-scan@1', 'status': 'started',
             'selection': selection_pin, 'source': own_pin, 'helpers': helper_pins, 'new_native_jobs': 0,
             'external_mutations': 0, 'qualified_shards_independently_rescanned': package, 'primary_error_type': None}
    rows = []
    try:
        with tempfile.TemporaryDirectory(dir=output) as temporary:
            for item in files:
                need(item['local']['bytes'] <= 16 * 1024**2, 'final selected file byte bound')
                content, signature = file_reader.read_regular(Path(item['local']['path']))
                binding = {'path': item['local']['path'], 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
                need(binding == item['local'], 'metadata binding changed')
                inspection = classifier.Classifier(scanner, budget, Path(temporary))
                with tempfile.TemporaryFile(dir=temporary) as stream:
                    stream.write(content)
                    stream.seek(0)
                    inspection.inspect(stream)
                need(not inspection.hits, 'credential pattern or exact cached-value export veto')
                rows.append({'local': binding, 'remote': item['remote'], 'source_stat': signature,
                             'scan_counts': dict(inspection.counts), 'scan_hits': []})
        for item in files:
            need(reader.pin(Path(item['local']['path'])) == item['local'], 'selected file changed during scan')
        need(reader.pin(args.selection) == selection_pin and reader.pin(Path(__file__).resolve()) == own_pin,
             'selection or producer changed during scan')
        for name, binding in helper_pins.items():
            need(reader.pin(Path(binding['path'])) == binding, 'executed helper changed during scan')
        need(reader.pin(publisher_path)['sha256'] == publisher_sha, 'reader changed during scan')
        state.update({'status': 'passed', 'scanned_files': rows, 'selected_files_scanned': len(rows),
                      'decoded_work_bytes': budget.decoded, 'decoded_work_limit_bytes': 512 * 1024**2,
                      'per_container_limit_bytes': 16 * 1024**2, 'universal_secret_absence_claim': False,
                      'decoder_policy_scope': 'bounded publication-only verification; native solver and metadata limits unchanged',
                      'model_activation': False, 'proof_authority': False})
    except BaseException as problem:
        state.update(status='failed', primary_error_type=type(problem).__name__)
        raise
    finally:
        reader.save(output / 'metadata-scan-closed.json', state)
    receipt_pin = reader.pin(output / 'metadata-scan-closed.json')
    # Fixed producer-created scan summary contains only pins, counts and scope.
    plan = {'schema': 'terminal-ir-successor-evidence-publication-plan@1', 'repo_id': selection['repo_id'],
            'expected_parent_commit': selection['expected_parent_commit'], 'files': files + [
                {'local': receipt_pin, 'remote': SCAN_REMOTE}]}
    reader.save(output / 'plan.json', plan)
    print(json.dumps({'plan': reader.pin(output / 'plan.json'), 'scan': receipt_pin}, sort_keys=True))


if __name__ == '__main__':
    main()
