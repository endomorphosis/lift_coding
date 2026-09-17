#!/usr/bin/env python3
"""Isolated HTTP fixtures; never contacts a model or external service."""
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

import bounded_http


class FixtureServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        self.received = []
        super().__init__(('127.0.0.1', 0), FixtureHandler)


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        self.server.received.append({'path': self.path, 'body': data.decode('utf-8')})
        try:
            if self.path == '/slow-headers':
                time.sleep(0.8)
            if self.path == '/redirect':
                self.send_response(307)
                self.send_header('Location', '/redirect-target')
                self.end_headers()
                return
            if self.path == '/drip':
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                for block in [b'{"value":"'] + [b'x' * 32] * 100 + [b'"}']:
                    self.wfile.write(block)
                    self.wfile.flush()
                    time.sleep(0.025)
                return
            status = 503 if self.path == '/failed-http' else 200
            body = (b'x' * 4096 if self.path == '/oversize' else b'invalid json'
                    if self.path == '/invalid-json' else
                    json.dumps({'fixture': self.path, 'received': json.loads(data)}, ensure_ascii=False).encode())
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # Deadline/redirect rejection deliberately closes these fixtures.
            pass


class BoundedHTTPTests(unittest.TestCase):
    output = None

    @classmethod
    def setUpClass(cls):
        cls.server = FixtureServer()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.directory = self.output / self._testMethodName

    def call(self, suffix, *, remaining=2.0, maximum=bounded_http.MAX_RESPONSE_BYTES):
        return bounded_http.post_json(self.base + suffix, {'text': 'café', 'number': 7},
                                      self.directory, 'request', remaining, max_response_bytes=maximum)

    def receipt(self):
        value = json.loads((self.directory / 'request.receipt.json').read_text())
        self.assertTrue(value['child_termination_proven'])
        request = (self.directory / 'request.request.bin').read_bytes()
        self.assertEqual(hashlib.sha256(request).hexdigest(), value['request_sha256'])
        response = self.directory / 'request.response.bin'
        if response.is_file():
            self.assertEqual(hashlib.sha256(response.read_bytes()).hexdigest(), value['response_sha256'])
        return value

    def test_success_and_exact_bytes(self):
        result = self.call('/success')
        self.assertEqual(result, {'fixture': '/success', 'received': {'text': 'café', 'number': 7}})
        receipt = self.receipt()
        self.assertEqual(receipt['status'], 200)
        self.assertTrue(receipt['worker']['complete'])
        self.assertFalse(receipt['deadline_expired'])
        self.assertEqual((self.directory / 'request.request.bin').read_bytes(),
                         '{"number":7,"text":"café"}'.encode('utf-8'))

    def test_failed_http_body_retained(self):
        with self.assertRaises(bounded_http.HTTPTransportError):
            self.call('/failed-http')
        receipt = self.receipt()
        self.assertEqual(receipt['status'], 503)
        self.assertEqual(json.loads((self.directory / 'request.response.bin').read_bytes())['fixture'], '/failed-http')

    def test_slow_headers_hard_deadline(self):
        started = time.monotonic()
        with self.assertRaises(bounded_http.HTTPTransportError):
            self.call('/slow-headers', remaining=0.25)
        self.assertLess(time.monotonic() - started, 1.2)
        receipt = self.receipt()
        self.assertTrue(receipt['deadline_expired'])
        self.assertIsNotNone(receipt['deadline_overrun_seconds'])

    def test_drip_body_hard_deadline(self):
        started = time.monotonic()
        with self.assertRaises(bounded_http.HTTPTransportError):
            self.call('/drip', remaining=0.3)
        self.assertLess(time.monotonic() - started, 1.2)
        receipt = self.receipt()
        self.assertTrue(receipt['deadline_expired'])
        self.assertGreater(receipt['response_bytes_retained'], 0)
        self.assertLess(receipt['response_bytes_retained'], 3212)

    def test_oversized_body_rejected_and_bounded(self):
        with self.assertRaises(bounded_http.HTTPTransportError):
            self.call('/oversize', maximum=1024)
        receipt = self.receipt()
        self.assertEqual(receipt['response_bytes_retained'], 1025)
        self.assertTrue(receipt['worker']['body_limit_exceeded'])
        self.assertFalse(receipt['worker']['complete'])

    def test_expired_budget_never_dispatches(self):
        count = len(self.server.received)
        for remaining in (0, -1, float('nan'), float('inf'), True):
            with self.subTest(remaining=remaining), self.assertRaises(ValueError):
                self.call('/expired-budget', remaining=remaining)
        self.assertEqual(len(self.server.received), count)
        self.assertFalse(self.directory.exists())

    def test_redirect_never_followed(self):
        count = sum(r['path'] == '/redirect-target' for r in self.server.received)
        with self.assertRaises(bounded_http.HTTPTransportError):
            self.call('/redirect')
        receipt = self.receipt()
        self.assertIn('redirect', receipt['worker']['error'].lower())
        self.assertEqual(sum(r['path'] == '/redirect-target' for r in self.server.received), count)

    def test_repeated_request_never_dispatches(self):
        self.call('/once')
        count = len(self.server.received)
        with self.assertRaises(FileExistsError):
            self.call('/once')
        self.assertEqual(len(self.server.received), count)
        self.receipt()

    def test_invalid_json_keeps_complete_receipt(self):
        with self.assertRaises(json.JSONDecodeError):
            self.call('/invalid-json')
        receipt = self.receipt()
        self.assertEqual(receipt['status'], 200)
        self.assertTrue(receipt['worker']['complete'])

    def child_fixture(self, metadata):
        """Run a real short-lived child, replacing only its controlled output."""
        original = subprocess.Popen
        prefix = str(self.directory / 'request')
        source = ('import pathlib,sys; p=sys.argv[1]; '
                  'pathlib.Path(p+".response.bin").write_bytes(b"{}"); '
                  'pathlib.Path(p+".worker.json").write_text(sys.argv[2])')

        def start(*args, **kwargs):
            return original([sys.executable, '-I', '-c', source, prefix, metadata], **kwargs)

        return patch.object(bounded_http.subprocess, 'Popen', start)

    def test_partial_worker_metadata_preserves_parent_receipt(self):
        count = len(self.server.received)
        with self.child_fixture('{"complete":'), self.assertRaises(bounded_http.HTTPTransportError):
            self.call('/metadata-fixture')
        receipt = self.receipt()
        self.assertEqual(receipt['worker_metadata_error']['error_type'], 'JSONDecodeError')
        self.assertIsNone(receipt['worker'])
        self.assertEqual(len(self.server.received), count)

    def test_invalid_worker_shape_preserves_parent_receipt(self):
        with self.child_fixture('[]'), self.assertRaises(bounded_http.HTTPTransportError):
            self.call('/shape-fixture')
        receipt = self.receipt()
        self.assertEqual(receipt['worker_metadata_error']['error_type'], 'ValueError')
        self.assertIsNone(receipt['worker'])

    def test_process_start_failure_preserves_parent_receipt(self):
        count = len(self.server.received)
        with patch.object(bounded_http.subprocess, 'Popen', side_effect=OSError('isolated start failure')):
            with self.assertRaises(OSError):
                self.call('/start-fixture')
        receipt = self.receipt()
        self.assertFalse(receipt['child_started'])
        self.assertEqual(len(self.server.received), count)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True)
    BoundedHTTPTests.output = output
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BoundedHTTPTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    here = Path(__file__).resolve().parent
    report = {
        'schema': 'la-bounded-http-development-qualification/v1',
        'status': 'PASS' if result.wasSuccessful() else 'FAIL',
        'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'test_names': unittest.defaultTestLoader.getTestCaseNames(BoundedHTTPTests),
        'bounded_http_sha256': hashlib.sha256((here / 'bounded_http.py').read_bytes()).hexdigest(),
        'test_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'model_calls': 0, 'external_service_calls': 0,
        'scope': 'Isolated loopback HTTP fixture qualification, not model-service or whole-study admission',
        'fixture_requests': BoundedHTTPTests.server.received,
        'fixture_port': BoundedHTTPTests.server.server_port,
    }
    bounded_http.save(output / 'qualification.json', report)
    print(json.dumps(report, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
