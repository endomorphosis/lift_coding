#!/usr/bin/python3.12
"""Actual metadata CLI controls; no source bodies, handlers, providers or scoring."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
BENCHMARK = next(parent / 'papers/completion/law_to_action/benchmark' for parent in Path(__file__).resolve().parents if (parent / 'papers/completion/law_to_action/benchmark').is_dir())
FILES = (
    'automated_evidence.py', 'qualify_final_runtime.py', 'source_pipeline.py',
    'handlers/effects.py', 'baselines.py', 'manifests/provers.json', 'arms.json',
    'resource_plan.json', 'protocol.json', 'manifests/sources.json',
    'manifests/splits.json', 'corpus_counts.json', 'automated_evidence_amendment.json',
    'annotations/automated_reference_manifest.json',
)

class SavedAdmissionCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='la-saved-admission-cli-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bench = self.root / 'papers/completion/law_to_action/benchmark'
        for name in FILES:
            dst = self.bench / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(BENCHMARK / name, dst)
        (self.root / 'external/ipfs_accelerate').mkdir(parents=True)
        spec = importlib.util.spec_from_file_location('isolated_automated_evidence', self.bench / 'automated_evidence.py')
        self.ae = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.ae)
        self.out = self.root / 'saved'
        self.out.mkdir()
        self.envelope = self.ae.build_valid_envelope()
        self.admission = self.ae.admit(self.envelope)
        self.assertTrue(self.admission['admitted'])
        self.save('automated_envelope.json', self.envelope)
        self.save('automated_admission.json', self.admission)

    def save(self, name, body):
        (self.out / name).write_text(json.dumps(body, sort_keys=True) + '\n')

    def cli_pair(self, expected, reason=None):
        originals = {p.name:p.read_bytes() for p in self.out.iterdir() if p.name != 'final_analysis.json'}
        for command in ('admit-final', 'analyze'):
            with self.subTest(command=command):
                # The fixture contains only metadata and hashed source files.
                # No native implementation, source corpus, gold or credential is mounted/copied.
                env = {'PATH':'/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE':'1', 'HOME':str(self.root)}
                run = subprocess.run(['/usr/bin/python3.12', '-B', str(self.bench / 'qualify_final_runtime.py'), command, '--out', str(self.out)], cwd=self.root, env=env, text=True, capture_output=True, timeout=15)
                self.assertEqual(expected, run.returncode, run.stderr + run.stdout[:2000])
                result = json.loads(run.stdout)
                self.assertFalse(result['scored'])
                self.assertEqual(expected == 0, result['admission']['admitted'])
                if reason:
                    self.assertIn(reason, result['admission']['reasons'])
        self.assertEqual(originals, {name:(self.out / name).read_bytes() for name in originals})

    def test_current_saved_pair_admits_without_scoring(self):
        self.cli_pair(0)

    def test_stale_current_profile_refused_by_both_clis(self):
        with (self.bench / 'baselines.py').open('a') as stream:
            stream.write('\n# A subsequent normal source revision.\n')
        self.cli_pair(2, 'stale_profile')

    def test_stale_current_budget_refused_by_both_clis(self):
        with (self.bench / 'resource_plan.json').open('a') as stream:
            stream.write('\n')
        self.cli_pair(2, 'stale_budget')

    def test_stale_current_source_manifest_refused_by_both_clis(self):
        with (self.bench / 'manifests/sources.json').open('a') as stream:
            stream.write('\n')
        self.cli_pair(2, 'missing_source_binding')

    def test_changed_population_refused_by_both_clis(self):
        self.envelope['case_inventory']['case_ids'].pop()
        self.save('automated_envelope.json', self.envelope)
        self.cli_pair(2, 'incomplete_case_accounting')

    def test_missing_original_envelope_refused_by_both_clis(self):
        (self.out / 'automated_envelope.json').unlink()
        self.cli_pair(2)

    def test_minimal_saved_boolean_is_not_authority(self):
        self.save('automated_admission.json', {'admitted':True, 'scored':False})
        self.cli_pair(2, 'saved_admission_envelope_mismatch')

    def test_saved_binding_mismatch_refused_by_both_clis(self):
        self.admission['bindings']['profile_digest'] = '0' * 64
        self.save('automated_admission.json', self.admission)
        self.cli_pair(2, 'saved_admission_envelope_mismatch')

    def test_changed_envelope_digest_refused_by_both_clis(self):
        self.envelope['qualification']['scope_note'] = 'Later metadata revision requires readmission.'
        self.save('automated_envelope.json', self.envelope)
        self.cli_pair(2, 'saved_admission_envelope_mismatch')

    def test_direct_analysis_requires_original_envelope(self):
        self.assertEqual('refused', self.ae.automated_analysis(self.admission)['status'])
        self.assertEqual('qualification_recorded_not_scored', self.ae.automated_analysis(self.admission, envelope=self.envelope)['status'])
        with (self.bench / 'baselines.py').open('a') as stream:
            stream.write('\n# Changed after admission.\n')
        result = self.ae.automated_analysis(self.admission, envelope=self.envelope)
        self.assertEqual('refused', result['status'])
        self.assertIn('stale_profile', result['admission']['reasons'])

    def test_new_observation_timestamp_is_allowed(self):
        self.admission['admitted_at'] = '2000-01-01T00:00:00Z'
        self.save('automated_admission.json', self.admission)
        self.cli_pair(0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
