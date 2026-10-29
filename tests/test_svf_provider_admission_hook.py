"""Authored provider-admission transports; never dispatch a real provider."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import swissknife_visual_functional_llm as adapter
from test_swissknife_visual_functional_llm import AdapterTests as _Fixture

class ProviderAdmissionTests(unittest.TestCase):
    setUp = _Fixture.setUp
    invoke = _Fixture.invoke

    def test_hook_binds_exact_compiled_attempt_and_cannot_mutate_contract(self):
        observed = []
        def claim(value):
            self.assertEqual(self.calls, [])
            self.assertFalse((self.root / 'receipt.progress.json').exists())
            observed.append(json.loads(json.dumps(value)))
            value['provider'] = 'different'
            value['input_files'][0]['sha256'] = '0' * 64
            value['screenshots'].clear()
        result = self.invoke(output_path='receipt.json', before_provider=claim)
        self.assertTrue(result['success'])
        self.assertEqual(len(observed), 1)
        bound = observed[0]
        self.assertEqual(set(bound), {'schema', 'invocation_id', 'task_id', 'mode', 'provider', 'model',
            'attempt_receipt_path', 'output_path', 'source_contract_sha256', 'prompt_sha256',
            'router_source_sha256', 'input_files', 'screenshots', 'timeout_seconds', 'model_context_bytes',
            'max_output_tokens', 'max_turns'})
        self.assertEqual(bound.pop('schema'), 'swissknife.visual-functional-provider-admission.v1')
        self.assertEqual(bound.pop('output_path'), 'receipt.json')
        for key, value in bound.items():
            self.assertEqual(value, result[key], key)
        self.assertEqual(str(uuid.UUID(result['invocation_id'])), result['invocation_id'])
        self.assertEqual(result['attempt_receipt_path'], f"model-invocations/receipt-{result['invocation_id']}.json")
        self.assertEqual(result['prompt_sha256'], hashlib.sha256(self.calls[0][0].encode()).hexdigest())
        self.assertTrue((self.root / result['attempt_receipt_path']).is_file())
        self.assertEqual(self.calls[0][1]['allocation_session_id'], result['invocation_id'])
        self.assertEqual(result['provider'], 'grok_cli')
        self.assertEqual(len(result['screenshots']), 1)

    def test_refused_claim_calls_neither_provider_nor_progress(self):
        class Refusal(RuntimeError): pass
        seen = []
        def refuse(bound):
            seen.append(bound)
            raise Refusal('already claimed')
        with self.assertRaisesRegex(Refusal, 'already claimed'):
            self.invoke(output_path='receipt.json', before_provider=refuse)
        self.assertEqual(len(seen), 1)
        self.assertEqual(self.calls, [])
        self.assertFalse((self.root / 'receipt.json').exists())
        self.assertFalse((self.root / 'receipt.progress.json').exists())

    def test_compiler_cap_auth_and_path_failures_never_claim(self):
        for kind in ('cap', 'auth', 'png', 'output', 'edit_scope', 'route'):
            with self.subTest(kind=kind):
                self.setUp()
                seen=[]
                kwargs={'output_path':'receipt.json', 'before_provider':seen.append}
                if kind=='cap':
                    self.source.write_text('x' * 40000)
                elif kind=='auth':
                    self.router._grok_cli_auth_available=lambda:False
                elif kind=='png':
                    self.image.write_text('not PNG')
                elif kind=='output':
                    kwargs['output_path']='app.js'
                elif kind=='edit_scope':
                    kwargs.update(mode='repair', predicted_files=['board.todo.md'])
                elif kind=='route':
                    self.profile.write_text(json.dumps({'todoPath':'board.todo.md','llm':{'model':'wrong'}}))
                with self.assertRaises(adapter.ModelAdapterError):
                    self.invoke(**kwargs)
                self.assertEqual(seen, [])
                self.assertEqual(self.calls, [])

    def test_hook_requires_callable_and_retained_receipt(self):
        for kwargs in ({'before_provider':lambda value:None}, {'before_provider':True,'output_path':'receipt.json'}):
            with self.assertRaisesRegex(adapter.ModelAdapterError, 'admission hook requires'):
                self.invoke(**kwargs)
        self.assertEqual(self.calls, [])

    def test_callback_source_or_image_or_router_drift_refuses_dispatch(self):
        for kind in ('input', 'board', 'profile', 'image', 'router', 'new_edit'):
            with self.subTest(kind=kind):
                self.setUp()
                def claim(_bound):
                    target={'input':self.source,'board':self.board,'profile':self.profile,
                            'image':self.image,'router':self.router_source,'new_edit':self.root/'new.js'}[kind]
                    target.write_bytes(b'changed by authored claim')
                kwargs={'output_path':'receipt.json','before_provider':claim}
                if kind=='new_edit':
                    self.response.update(mode='repair')
                    kwargs.update(mode='repair', predicted_files=['app.js','new.js'])
                with self.assertRaises(adapter.ModelAdapterError):
                    self.invoke(**kwargs)
                self.assertEqual(self.calls, [])
                self.assertFalse((self.root/'receipt.progress.json').exists())

    def test_source_drift_during_authenticated_lookup_does_not_claim(self):
        seen=[]
        def auth():
            self.source.write_text('drift before claim')
            return True
        self.router._grok_cli_auth_available=auth
        with self.assertRaises(adapter.ModelAdapterError):
            self.invoke(output_path='receipt.json',before_provider=seen.append)
        self.assertEqual(seen, [])
        self.assertEqual(self.calls, [])

    def test_future_attempt_and_progress_paths_are_checked_before_claim(self):
        for parent in ('model-invocations',):
            with self.subTest(parent=parent):
                seen=[]
                (self.root/parent).symlink_to(self.root/'absent-outside',target_is_directory=True)
                with self.assertRaisesRegex(adapter.ModelAdapterError,'symbolic links'):
                    self.invoke(output_path='receipt.json',before_provider=seen.append)
                self.assertEqual(seen,[])
                self.assertEqual(self.calls,[])
                (self.root/parent).unlink()

    def test_callback_artifact_path_substitution_refuses_dispatch(self):
        def substitute(_bound):
            (self.root/'model-invocations').symlink_to(self.root/'missing',target_is_directory=True)
        with self.assertRaisesRegex(adapter.ModelAdapterError,'symbolic links'):
            self.invoke(output_path='receipt.json',before_provider=substitute)
        self.assertEqual(self.calls,[])
        self.assertFalse((self.root/'receipt.progress.json').exists())

    def test_none_preserves_original_dispatch_and_limits(self):
        result=self.invoke(output_path='receipt.json',before_provider=None)
        self.assertEqual(len(self.calls),1)
        self.assertEqual((result['model_context_bytes'],result['max_turns']), (32768,8))
        self.assertFalse(result['allow_local_fallback'])
        self.assertFalse(result['completion_authority'])

    def test_repair_hook_preserves_edit_allowlist_and_exact_prompt(self):
        self.response.update(mode='repair', inspected_screenshots=[])
        seen=[]
        result=self.invoke('repair', output_path='repair.json', screenshot_paths=[],
                           predicted_files=['app.js'], before_provider=seen.append)
        self.assertEqual(result['model_context_bytes'],262144)
        self.assertEqual(seen[0]['mode'],'repair')
        self.assertEqual(self.calls[0][1]['temperature'],0)
        self.assertIn("export const label = 'before';",self.calls[0][0])
        self.assertEqual(self.source.read_text(),"export const label = 'before';\n")

if __name__=='__main__': unittest.main()
