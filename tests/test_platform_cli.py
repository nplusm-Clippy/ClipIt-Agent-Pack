import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = json.loads((ROOT / 'tests/fixtures/platform-responses.json').read_text())


class Handler(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *_args):
        pass

    def do_GET(self):
        self.calls.append(('GET', self.path))
        fixture = {'/api/v1/agent/me': 'identity', '/api/v1/agent/platform/compatibility': 'compatibility',
                   '/api/v1/agent/platform/runs': 'runs'}[self.path.split('?')[0]]
        self.reply(200, FIXTURES[fixture]['body'])

    def do_POST(self):
        self.calls.append(('POST', self.path))
        self.rfile.read(int(self.headers.get('Content-Length', '0')))
        self.reply(503, {'error': {'code': 'OUTCOME_UNKNOWN', 'message': 'Check original receipt'}})

    def reply(self, status, payload):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())


class StandalonePlatformCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def invoke(self, *args):
        result = subprocess.run([sys.executable, '-m', 'clipit_plugin', *args], cwd=ROOT,
                                env={**os.environ, 'CLIPPER_API_KEY': 'synthetic-cli-key',
                                     'CLIPPER_BASE_URL': f'http://127.0.0.1:{self.server.server_port}',
                                     'CLIPPER_ALLOW_LOCAL_HTTP': '1'}, text=True, capture_output=True, timeout=10)
        self.assertNotIn('synthetic-cli-key', result.stdout + result.stderr)
        return result, json.loads(result.stdout)

    def test_no_hermes_connection_negotiation_and_json_output(self):
        result, value = self.invoke('status')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(value['accountId'], 'owner')
        self.assertEqual(value['compatibility']['contractVersion'], '2026-09-16')

    def test_paginated_runs_remain_available_without_a_native_plugin(self):
        result, value = self.invoke('runs', '--query', '{"limit":50}')
        self.assertEqual(result.returncode, 0)
        self.assertIsInstance(value['items'], list)
        self.assertIn('page', value)

    def test_unknown_mutation_exits_13_and_never_dispatches_twice(self):
        before = sum(method == 'POST' for method, _path in Handler.calls)
        result, value = self.invoke('execute', '--body', '{"idempotencyKey":"original-cli-key","request":{"functionName":"futureTool","parameters":{}}}')
        self.assertEqual(result.returncode, 13)
        self.assertTrue(value['error']['outcomeUnknown'])
        self.assertEqual(value['error']['idempotencyKey'], 'original-cli-key')
        self.assertEqual(sum(method == 'POST' for method, _path in Handler.calls) - before, 1)
