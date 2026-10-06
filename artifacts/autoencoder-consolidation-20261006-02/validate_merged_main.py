"""Integration and concurrent provenance checks on the actual merged main."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
candidate = OUT / 'datasets-merged-main'
freeze = json.loads((OUT / 'candidate-freeze.json').read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for relative, expected in freeze['files'].items(): assert sha(candidate / relative) == expected
paths = json.loads((OUT / 'grouped-decoder-integration-plan.json').read_text())['phase1']['test_paths'] + [
    'tests/unit/optimizers/logic_theorem_optimizer/test_autoencoder_runtime_registry.py',
    'tests/unit/optimizers/logic_theorem_optimizer/test_learned_formula_runtime.py',
    'tests/unit/optimizers/logic_theorem_optimizer/test_native_formula_runtime.py',
    'tests/unit/optimizers/logic_theorem_optimizer/test_grouped_formula_runtime.py',
    'tests/unit/logic/formalization/autoencoder/test_contextual_legal_ir_runtime.py',
]
test_pins = {path: sha(candidate / path) for path in paths}
xml_path = OUT / 'merged-main-validation.xml'
assert not xml_path.exists()
script = 'import torch, pytest; torch.set_num_threads(2); raise SystemExit(pytest.main(' + repr(
    ['-q', *paths, '--junitxml=' + str(xml_path)]) + '))'
command = [sys.executable, '-c', script]
env = dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONPATH=str(candidate),
           IPFS_DATASETS_NATIVE_LAKE_TEST_EXECUTABLE='/home/barberb/.elan/toolchains/leanprover--lean4---v4.26.0/bin/lake')
result = subprocess.run(command, cwd=candidate, env=env, capture_output=True, text=True, timeout=180)
(OUT / 'merged-main-validation-output.txt').write_text(result.stdout + result.stderr)
for relative, expected in freeze['files'].items(): assert sha(candidate / relative) == expected
for relative, expected in test_pins.items(): assert sha(candidate / relative) == expected
xml = ET.parse(xml_path).getroot()
counts = {key: sum(int(row.get(key, '0')) for row in xml.iter('testsuite'))
          for key in ('tests', 'failures', 'errors', 'skipped')}
assert counts['tests'] > 407 and all(counts[k] == 0 for k in ('failures', 'errors', 'skipped')), counts
from collections import Counter
case_key = lambda c: (c.get('classname'), c.get('name'))
original = Counter(case_key(c) for c in ET.parse(OUT / 'combined-main-validation.xml').getroot().iter('testcase'))
current = Counter(case_key(c) for c in xml.iter('testcase'))
assert len(list(ET.parse(OUT / 'combined-main-validation.xml').getroot().iter('testcase'))) == 407
assert all(current[k] == v for k, v in original.items())
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=candidate, text=True).strip()
assert head == '0f36163a585a9bf514c41d8eabe202936c000705'
assert result.returncode == 0
report = {'schema': 'grouped-legal-actual-merged-main-validation/v1', 'status': 'passed',
          'candidate_base': freeze['base'], 'actual_main_commit': head, 'original_407_cases_preserved': True, 'additional_contextual_runtime_cases': counts['tests'] - 407, 'candidate_worktree': str(candidate),
          'command': command, 'counts': counts, 'source_pins': freeze['files'],
          'test_pins': test_pins, 'source_and_tests_stable': True,
          'runner_sha256': sha(Path(__file__)), 'production_promotion': False,
          'new_training_experiment': False, 'unit_tests_include_small_optimizer_fixtures': True}
p = OUT / 'merged-main-validation.json'; assert not p.exists()
p.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'status': 'passed', 'counts': counts, 'receipt': str(p)}))
