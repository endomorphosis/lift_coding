"""Seal the eight-panel evaluator only after successful completed training.

This preparation copies reviewed source and hashes saved files. It never loads
models, acquires resources, or starts the numerical evaluator.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

W = Path('/home/barberb/lift_coding')
R = W / 'artifacts/autoencoder-dual-bank-replay-20261007'
RUN = W / 'external/ipfs_datasets/workspace/test-logs/decoder-dual-bank-replay-20261007'
TRAIN = RUN / 'training-384-r1'
EVALUATOR = 'scripts/ops/autoencoder/evaluate_dual_bank_replay.py'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    require(not (RUN / 'evaluation-manifest.json').exists()
        and not (RUN / 'evaluation-plan.json').exists(), 'fresh evaluation seals required')
    terminal = {name: TRAIN / filename for name, filename in
        [('child_exit', 'child-exit.json'), ('resources_final', 'resources-final.json')]}
    require(read(terminal['child_exit'])['returncode'] == 0
        and read(terminal['resources_final'])['status'] == 'released'
        and read(RUN / 'training-384-r1-guardian-exit.json')['returncode'] == 0,
        'completed owned training and released resources required')
    summary_path = TRAIN / 'results/summary.json'
    summary = read(summary_path)
    require(summary['complete'] is True and summary['phase'] == 'training'
        and summary['dimension'] == 384 and len(summary['runs']) == 1,
        'one complete native384 fit required')
    source = R / 'evaluation/source/evaluate_dual_bank_replay.py'
    require(sha(source) == 'bd2862167fa61ba4451b79436e79609e5ff6d8280151256aab459ba9df1837f5',
        'reviewed evaluator source changed')
    source_review = R / 'independent-review/evaluation-source-independent-review.json'
    review = read(source_review)
    require(sha(source_review) == '324a82090b861e81e6e7798168062f07bb822bf7b7184620b750c06b661bd927'
        and review['passed'] is True and not review['findings'], 'clean frozen source review required')
    spec = importlib.util.spec_from_file_location('_dual_eval_metadata_only', source)
    evaluator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluator)
    original = read(RUN / 'training-manifest.json')
    inputs = dict(original['inputs'])

    def pin(path, wanted=None):
        path = Path(path).resolve()
        actual = sha(path)
        require(wanted is None or actual == wanted, 'saved reference changed: ' + str(path))
        previous = inputs.setdefault(str(path), actual)
        require(previous == actual, 'conflicting immutable input: ' + str(path))
        return path

    # Follow actual path/SHA saved-output references, rather than interpreting
    # historical mutable ledger locators as fresh numerical dependencies.
    seen = set()

    def collect(value):
        if type(value) is dict:
            if type(value.get('path')) is str and type(value.get('sha256')) is str:
                path = pin(value['path'], value['sha256'])
                if path.suffix == '.json' and path not in seen:
                    seen.add(path)
                    collect(read(path))
            for child in value.values():
                collect(child)
        elif type(value) is list:
            for child in value:
                collect(child)

    pin(summary_path)
    collect(summary)
    for path in sorted(TRAIN.rglob('*')):
        if path.is_file():
            pin(path)
    pin(RUN / 'training-384-r1-guardian-exit.json')
    for name in ['training-manifest.json', 'training-plan.json']:
        pin(RUN / name)
    for path in terminal.values():
        pin(path)
    pin(source)
    pin(source_review)
    pin(R / 'evaluation/source-freeze.json')
    destination = RUN / 'experiment-source' / EVALUATOR
    require(not destination.exists(), 'fresh deployed evaluator required')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    pin(destination, sha(source))
    v3 = W / 'external/ipfs_datasets/workspace/test-logs/decoder-fresh-normative-style-r2-20261004/preparation-r1/results/references.json'
    pin(v3, 'b85a24543587f88a185037c02094048eba6bc4bfbfacac465d35a8942a895d0c')
    pin(Path(__file__).resolve())
    for path, wanted in inputs.items():
        require(sha(path) == wanted, 'operational input changed: ' + path)
    extensions = dict(original['extensions'])
    extensions[EVALUATOR] = sha(destination)
    plan = dict(evaluator.PROFILE, input_sha256=inputs)
    plan_path = RUN / 'evaluation-plan.json'
    save(plan_path, plan)
    manifest = dict(schema='dual-bank-replay-postfit-evaluation-manifest/v1',
        inputs=inputs, extensions=extensions, plan_sha256=sha(plan_path),
        training_summary=str(summary_path),
        training_terminal={name: str(path) for name, path in terminal.items()},
        comparison_protocol=original['comparison_protocol'],
        initialization_extension_root=original['initialization_extension_root'],
        initialization_manifest=original['initialization_manifest'],
        initialization_plan=original['initialization_plan'],
        source_inventories=original['source_inventories'],
        scalar_observer_source=original['scalar_observer_source'],
        v3_references=str(v3), current_training_manifest_sha256=sha(RUN / 'training-manifest.json'),
        historical_schema_owners_only=True, qualification_granted=False)
    evaluator.validate_plan(plan, manifest)
    manifest_path = RUN / 'evaluation-manifest.json'
    save(manifest_path, manifest)
    receipt = dict(schema='dual-bank-replay-actual-evaluation-preparation/v1',
        passed=True, findings=[], inputs=len(inputs), extensions=extensions,
        files={str(path): dict(sha256=sha(path), bytes=path.stat().st_size)
            for path in [plan_path, manifest_path]},
        logical_panels=8, physical_panels=8, models_executed=False,
        reservation_acquired=False, qualified=False)
    save(R / 'evaluation/actual-input-preparation.json', receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
