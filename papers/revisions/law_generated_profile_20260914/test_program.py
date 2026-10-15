"""Constructed interpreter/fixture controls, not model or scientific cases."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import time
import unittest
from effects import PURE, EFFECTS, FixtureEffects, pure
from program import Interpreter, Limits, ProgramError, Value, labels, unbox, validate, wrap


def pure_dispatch(call, args):
    return pure(call['name'], args)


def interpreted(source, payload, **kwargs):
    runner = Interpreter(source.encode(), PURE | EFFECTS, pure_dispatch, **kwargs)
    return runner, runner.run(payload)


class ProgramTests(unittest.TestCase):
    def test_constructed_semantics_match_cpython(self):
        sources = [
            "def run(payload):\n    total = 0\n    for item in payload:\n        if item > 1:\n            total = total + item * 6\n    return total\n",
            "def run(payload):\n    out = {}\n    for key in keys(payload):\n        if key != 'password':\n            out[key] = payload[key]\n    return out\n",
            "def run(payload):\n    text = text_lower(payload['text'])\n    return text_replace(text, '/', '-')\n",
            "def run(payload):\n    a = payload['a']\n    b = payload['b']\n    return [a // b, a % b, a / b, -a, not a, a <= b]\n",
            "def run(payload):\n    return payload['a'] and payload['b'] or 'fallback'\n",
            "def run(payload):\n    return 0 < payload['a'] < 10\n",
            "def run(payload):\n    return payload['x'] is None\n",
            "def run(payload):\n    d = {}\n    a = [d]\n    b = a + []\n    b[0]['x'] = 1\n    return d\n",
            "def run(payload):\n    a = []\n    for item in payload:\n        a = append(a, item + 1)\n    return a\n",
            "def run(payload):\n    out = ''\n    for c in payload:\n        out = out + c\n    return out\n",
        ]
        inputs = [[1, 2, 3], {'name': 'Ada', 'password': 'secret'}, {'text': 'A/B'}, {'a': -7, 'b': 3},
                  {'a': 0, 'b': 'x'}, {'a': 5}, {'x': None}, {}, [1, 2], 'abc']
        for source, payload in zip(sources, inputs):
            with self.subTest(source=source):
                namespace = {'__builtins__': {}, **{name: (lambda *args, name=name: unbox(pure(name, [wrap(arg) for arg in args]))) for name in PURE}}
                # Only the ten fixed trusted test strings above reach CPython.
                exec(compile(source, 'trusted_semantic_control.py', 'exec'), namespace)
                expected = namespace['run'](payload)
                _, actual = interpreted(source, payload)
                self.assertEqual(unbox(actual), expected)

    def test_explicit_and_taken_untaken_branch_provenance(self):
        for source, payload in [
            ("def run(payload):\n    return payload['secret']\n", {'secret': 's'}),
            ("def run(payload):\n    x = 0\n    if payload['secret']:\n        x = 1\n    return x\n", {'secret': True}),
            ("def run(payload):\n    x = 0\n    if payload['secret']:\n        x = 1\n    return x\n", {'secret': False}),
        ]:
            runner = Interpreter(source.encode(), PURE | EFFECTS, pure_dispatch)
            value = runner.run(payload, {'secret': ['private']})
            self.assertIn('private', labels(value))
        source = "def run(payload):\n    out = {}\n    for key in keys(payload):\n        if key != 'password':\n            out[key] = payload[key]\n    return out\n"
        runner = Interpreter(source.encode(), PURE | EFFECTS, pure_dispatch)
        value = runner.run({'name': 'Ada', 'password': 's'}, {'password': ['private']})
        self.assertEqual(unbox(value), {'name': 'Ada'})
        self.assertEqual(labels(value), frozenset())

    def test_escape_and_unsupported_syntax_rejection(self):
        bad = ["import os\n", "def run(payload):\n    return payload.__class__\n",
               "def run(payload):\n    return __import__('os')\n", "def run(payload):\n    return [x for x in payload]\n",
               "def run(payload):\n    return (lambda x: x)(payload)\n", "def run(payload):\n    while True:\n        pass\n",
               "def run(payload):\n    def nested(x):\n        return x\n    return 1\n",
               "def run(payload):\n    return eval(payload)\n", "def run(payload):\n    length = payload\n",
               "def run[T](payload):\n    return payload\n", "def run(payload: object):\n    return payload\n",
               "@length\ndef run(payload):\n    return payload\n", "def run(payload):\n    return b'bytes'\n",
               "def run(payload):\n    return 2 ** 999999999\n", "def run(payload):\n    return json_encode(value=payload)\n"]
        for source in bad:
            with self.subTest(source=source), self.assertRaises(ProgramError):
                validate(source.encode(), PURE | EFFECTS)

    def test_resource_bounds(self):
        source = "def run(payload):\n    for item in payload:\n        x = item + 1\n    return 0\n"
        with self.assertRaises(ProgramError):
            interpreted(source, [1] * 10, limits=replace(Limits(), iterations=3))
        with self.assertRaises(ProgramError):
            interpreted(source, [1] * 10, limits=replace(Limits(), steps=3))
        with self.assertRaises(ProgramError):
            interpreted(source, [1], deadline=time.monotonic() - 1)
        with self.assertRaises(ProgramError):
            interpreted("def run(payload):\n    return 'x' * payload\n", 10**20)
        with self.assertRaises(ProgramError):
            interpreted("def run(payload):\n    return payload\n", [1] * 513)
        with self.assertRaises(ProgramError):
            interpreted("def run(payload):\n    return payload\n", float('nan'))
        with self.assertRaises(ProgramError):
            interpreted("def run(payload):\n    return text_replace(payload, '', payload)\n", 'x' * 1000)

    def test_repeated_and_conditional_call_sites(self):
        source = b"def run(payload):\n    if payload:\n        write_json('out.json', payload)\n    write_json('out.json', payload)\n    write_json('other.json', payload); write_json('other.json', payload)\n"
        _, profile = validate(source, PURE | EFFECTS)
        self.assertEqual(len(profile['calls']), 4)
        self.assertEqual(len({(call['line'], call['column']) for call in profile['calls']}), 4)

    def test_actual_generic_effects_and_torn_custody(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def gate(invocation, delegate, folder):
                return {'development_only': True}, delegate()
            effects = FixtureEffects(root / 'world', root / 'audit', {'stores': {'records': {'x': 3}}}, gate)
            source = b"def run(payload):\n    n = state_read('records', 'x')\n    write_json('public/result.json', {'twice': n * 2})\n    state_compare_delete('records', 'x', n)\n    emit_event('notice', {'completed': True})\n"
            runner = Interpreter(source, PURE | EFFECTS, effects.dispatch)
            runner.run({})
            self.assertEqual(json.loads((effects.files / 'public/result.json').read_text()), {'twice': 6})
            self.assertEqual(json.loads(effects.store_path('records').read_text()), {})
            self.assertTrue(effects.observe()['observation_complete'])
            (effects.files / 'unrecorded.txt').write_text('unexpected')
            self.assertIn('unaccounted_terminal_effect', effects.observe()['integrity_errors'])
            (effects.audit / 'effect-0001/receipt.json').unlink()
            self.assertFalse(effects.observe()['observation_complete'])


if __name__ == '__main__':
    unittest.main()
