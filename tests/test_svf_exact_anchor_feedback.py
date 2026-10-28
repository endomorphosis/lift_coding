"""Exact retry diagnostics; authored fixtures never execute a provider or patch."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
REPO = Path(os.environ.get('SVF_FOUNDATION_REPOSITORY_ROOT', str(BASE)))
sys.path[:0] = [str(BASE / 'scripts'), str(REPO / 'scripts')]
import swissknife_visual_functional_llm as llm
import swissknife_visual_functional_worker as worker


class ExactAnchorFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        p = patch.object(worker, 'ROOT', self.root)
        p.start(); self.addCleanup(p.stop)
        self.task = {'task_id': 'SVF-099', 'title': 'Repair exact source', 'kind': 'implementation',
                     'acceptance': 'Existing actual result remains required', 'edit_paths': ['app.js']}
        self.profile = {'runtimeRoot': 'data/agent_supervisor/swissknife_visual_functional',
                        'humanPlanPath': 'plan.md', 'taskSpecPath': 'tasks.json', 'appContractPath': 'contracts.json',
                        'llm': {'provider': 'grok_cli', 'model': 'grok-4.7'}}
        self.directory = worker.runtime_root(self.profile) / 'tasks/SVF-099'
        self.directory.mkdir(parents=True)
        (self.root / 'profile.json').write_text(json.dumps(self.profile))
        (self.root / 'contracts.json').write_text('{"apps": []}')
        (self.root / 'tasks.json').write_text('{"tasks": []}')

    def feedback(self, source, old, *, prefix=None):
        (self.root / 'app.js').write_text(source)
        digest = worker.sha(self.root / 'app.js')
        edits = list(prefix or []) + [{'path': 'app.js', 'before_sha256': digest, 'old': old, 'new': 'corrected'}]
        response = {'schema': llm.RESPONSE_SCHEMA, 'task_id': 'SVF-099', 'mode': 'repair', 'decision': 'needs_changes',
                    'summary': 'Correct exact anchor.', 'inspected_screenshots': [], 'findings': [], 'edits': edits}
        for row in edits:
            row['before_sha256'] = digest
        path = self.directory / 'rejected-responses' / 'candidate.json'
        path.parent.mkdir(exist_ok=True)
        raw = (json.dumps(response, indent=2) + '\n').encode(); path.write_bytes(raw)
        feedback = {'schema': worker.REPAIR_FEEDBACK_SCHEMA, 'task_id': self.task['task_id'],
                    'task_spec_sha256': worker.stable(self.task), 'source_sha256': worker.repair_target_hashes(self.task),
                    'completion_authority': False,
                    'error': {'code': 'edit_anchor_match_count', 'path': 'app.js', 'hunk_index': len(edits), 'match_count': 0,
                              'old_sha256': llm._sha(old.encode()), 'new_sha256': llm._sha(b'corrected'),
                              'old_bytes': len(old.encode()), 'new_bytes': len(b'corrected'), 'current_sha256': digest},
                    'rejected_response': {'path': str(path.relative_to(self.root)), 'sha256': llm._sha(raw), 'bytes': len(raw),
                                          'response_sha256': llm._sha(llm._json(response).encode())}}
        worker.repair_feedback_path(self.profile, self.task).write_text(json.dumps(feedback))
        return feedback

    def test_inline_css_reveals_actual_whitespace_without_proposing_patch(self):
        selector = '.peer-line, [data-owner-observation] { overflow-wrap: anywhere; }'
        source = '.empty { padding: 14px; } ' + selector + '\n'
        feedback = self.feedback(source, '      ' + selector)
        result = worker._repair_anchor_context(self.task, worker.load_repair_feedback(self.profile, self.task))
        self.assertEqual(result['failed_old'], '      ' + selector)
        self.assertTrue(result['failed_old_complete'])
        self.assertIn('.empty { padding: 14px; } .peer-line', result['excerpt']['text'])
        self.assertEqual(result['source_sha256'], worker.sha(self.root / 'app.js'))
        self.assertEqual(result['unapplied_draft_sha256'], result['source_sha256'])
        self.assertNotIn('new', result)
        self.assertEqual((self.root / 'app.js').read_text(), source)
        self.assertEqual(feedback['error']['match_count'], 0)

    def test_json_missing_brace_excerpt_is_exact_source_not_a_repaired_guess(self):
        source = '{"op":"assert","probe":{"kind":"text","selector":"#actual-result"},"operator":"contains","expected":"http"}\n'
        old = source.rstrip().replace('},"operator"', ',"operator"')
        result = worker._repair_anchor_context(self.task, self.feedback(source, old))
        self.assertEqual(result['failed_old'], old)
        self.assertIn('},"operator"', result['excerpt']['text'])
        self.assertEqual(result['excerpt']['text'], source[result['excerpt']['byte_offset']:result['excerpt']['byte_offset'] + len(result['excerpt']['text'])])

    def test_preceding_hunks_are_replayed_only_in_memory_with_same_exact_validator(self):
        source = 'const color = "red";\n.keep { color: red; } .target { display: block; }\n'
        prefix = [{'path': 'app.js', 'before_sha256': None, 'old': 'color: red;', 'new': 'color: blue;'}]
        feedback = self.feedback(source, '      .target { display: block; }', prefix=prefix)
        result = worker._repair_anchor_context(self.task, feedback)
        self.assertIn('color: blue;', result['excerpt']['text'])
        self.assertNotEqual(result['unapplied_draft_sha256'], result['source_sha256'])
        self.assertEqual((self.root / 'app.js').read_text(), source)
        invalid = self.feedback(source, '      .target { display: block; }', prefix=[dict(prefix[0], old='missing preceding exact anchor')])
        self.assertIsNone(worker._repair_anchor_context(self.task, invalid))
        feedback = self.feedback(source, '      .target { display: block; }', prefix=prefix)
        bad = copy.deepcopy(feedback)
        # Corrupting a preceding retained edit invalidates its immutable body.
        body = self.root / bad['rejected_response']['path']; body.write_text(body.read_text().replace('color: red;', 'missing text'))
        self.assertIsNone(worker._repair_anchor_context(self.task, bad))

    def test_source_candidate_and_error_hash_tampering_never_become_context(self):
        feedback = self.feedback(' .target { display: block; }\n', '      .target { display: block; }')
        for key, value in [('hunk_index', 32), ('old_sha256', '0' * 64), ('match_count', 2)]:
            changed = copy.deepcopy(feedback); changed['error'][key] = value
            self.assertIsNone(worker._repair_anchor_context(self.task, changed))
        (self.root / 'app.js').write_text('foreign replacement')
        self.assertIsNone(worker._repair_anchor_context(self.task, feedback))

    def test_ambiguous_or_absent_locator_does_not_invent_source_match(self):
        feedback = self.feedback('same locator text twice\nsame locator text twice\n', '  same locator text twice')
        result = worker._repair_anchor_context(self.task, feedback)
        self.assertNotIn('excerpt', result)
        self.assertEqual(result['failed_old'], '  same locator text twice')

    def test_utf8_and_json_escaping_are_bounded_and_offsets_refer_to_exact_bytes(self):
        source = 'π' * 120 + ' .unique-selector { content: "你好"; }\n' + '雪' * 300
        old = '      .unique-selector { content: "你好"; }' + '\n' + '"\\\n雪' * 1000
        result = worker._repair_anchor_context(self.task, self.feedback(source, old))
        self.assertLessEqual(len(llm._json(result).encode()), 2048)
        self.assertFalse(result['failed_old_complete'])
        excerpt = result['excerpt']; raw = source.encode()
        self.assertEqual(raw[excerpt['byte_offset']:excerpt['byte_offset'] + len(excerpt['text'].encode())], excerpt['text'].encode())

    def invoke_model(self, inspect, *, pack=None):
        self.provider_calls = 0
        def invoke(*args, **kwargs):
            context = json.loads((self.root / kwargs['input_paths'][0]).read_bytes())
            inspect(context, kwargs)
            return {'success': True}
        with patch.object(worker, 'assert_no_campaign_hold'), patch.object(worker, 'assert_storage_available'), \
             patch.object(worker, 'workflow_fixtures', return_value=None), patch.object(worker, 'load_execution_failure', return_value=None), \
             patch.object(llm, 'invoke_task_model', side_effect=invoke), patch.object(llm, 'validate_model_receipt'):
            if pack is None:
                return worker.model('profile.json', self.task, 'repair', [], [], self.directory / 'next.json')
            with patch.object(worker, '_repair_inputs', side_effect=pack):
                return worker.model('profile.json', self.task, 'repair', [], [], self.directory / 'next.json')

    def test_next_model_packet_contains_diagnostic_and_complete_source_with_zero_provider_calls(self):
        source = '.empty { padding: 1px; } .target { display: block; }\n'
        self.feedback(source, '      .target { display: block; }')
        def inspect(context, kwargs):
            self.assertEqual(context['failed_edit_anchor']['failed_old'], '      .target { display: block; }')
            self.assertIn('.empty', context['failed_edit_anchor']['excerpt']['text'])
            self.assertIn('app.js', kwargs['input_paths'])
            self.assertEqual(context['complete_edit_targets'][0]['sha256'], worker.sha(self.root / 'app.js'))
            self.assertEqual(context['model_context_bytes'], 262144)
            self.assertIn('exact unique anchors', context['retry_instruction'])
        self.invoke_model(inspect)
        self.assertEqual((self.root / 'app.js').read_text(), source)

    def test_optional_diagnostic_cannot_turn_a_fitting_mandatory_packet_into_cap_refusal(self):
        self.feedback(' .target { display: block; }\n', '      .target { display: block; }')
        original = worker._repair_inputs; calls = []
        def pack(*args, **kwargs):
            context = json.loads(args[3].read_bytes()); calls.append('failed_edit_anchor' in context)
            if calls[-1]:
                raise llm.ModelContextBudgetError(262145, 262144)
            return original(*args, **kwargs)
        def inspect(context, kwargs):
            self.assertNotIn('failed_edit_anchor', context)
            self.assertIn('last_repair_error', context)
            self.assertIn('app.js', kwargs['input_paths'])
            self.assertEqual(context['model_context_bytes'], 262144)
        self.invoke_model(inspect, pack=pack)
        self.assertEqual(calls, [True, False])


if __name__ == '__main__':
    unittest.main()
