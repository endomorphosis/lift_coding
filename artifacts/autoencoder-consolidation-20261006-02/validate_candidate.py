"""Combined integration check on the frozen main-based candidate."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
candidate = OUT / 'datasets-integration'
freeze = json.loads((OUT / 'candidate-freeze.json').read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for relative, expected in freeze['files'].items(): assert sha(candidate / relative) == expected
paths = json.loads((OUT / 'grouped-decoder-integration-plan.json').read_text())['phase1']['test_paths'] + [
    'tests/unit/optimizers/logic_theorem_optimizer/test_autoencoder_runtime_registry.py',
    'tests/unit/optimizers/logic_theorem_optimizer/test_learned_formula_runtime.py',
    'tests/unit/optimizers/logic_theorem_optimizer/test_native_formula_runtime.py',
    'tests/unit/optimizers/logic_theorem_optimizer/test_grouped_formula_runtime.py',
]
test_pins = {path: sha(candidate / path) for path in paths}
xml_path = OUT / 'combined-main-validation.xml'
assert not xml_path.exists()
script = 'import torch, pytest; torch.set_num_threads(2); raise SystemExit(pytest.main(' + repr(
    ['-q', *paths, '--junitxml=' + str(xml_path)]) + '))'
command = [sys.executable, '-c', script]
env = dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONPATH=str(candidate),
           IPFS_DATASETS_NATIVE_LAKE_TEST_EXECUTABLE='/home/barberb/.elan/toolchains/leanprover--lean4---v4.26.0/bin/lake')
result = subprocess.run(command, cwd=candidate, env=env, capture_output=True, text=True, timeout=180)
(OUT / 'combined-main-validation-output.txt').write_text(result.stdout + result.stderr)
for relative, expected in freeze['files'].items(): assert sha(candidate / relative) == expected
for relative, expected in test_pins.items(): assert sha(candidate / relative) == expected
xml = ET.parse(xml_path).getroot()
counts = {key: sum(int(row.get(key, '0')) for row in xml.iter('testsuite'))
          for key in ('tests', 'failures', 'errors', 'skipped')}
assert counts == {'tests': 407, 'failures': 0, 'errors': 0, 'skipped': 0}, counts
assert result.returncode == 0
report = {'schema': 'grouped-legal-main-integration-combined-validation/v1', 'status': 'passed',
          'candidate_base': freeze['base'], 'candidate_worktree': str(candidate),
          'command': command, 'counts': counts, 'source_pins': freeze['files'],
          'test_pins': test_pins, 'source_and_tests_stable': True,
          'runner_sha256': sha(Path(__file__)), 'production_promotion': False,
          'new_training_experiment': False, 'unit_tests_include_small_optimizer_fixtures': True}
p = OUT / 'combined-main-validation.json'; assert not p.exists()
p.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'counts': counts, 'receipt': str(p)}))
