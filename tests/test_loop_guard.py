import json, os, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

INTEGRATIONS = Path(__file__).resolve().parents[1] / 'integrations'
sys.path.insert(0, str(INTEGRATIONS))
from loop_guard import LoopGuard, normalize, REPEAT_LIMIT, ERROR_LIMIT, POLL_LIMIT


class GuardTests(unittest.TestCase):
    def test_third_identical_call_is_blocked(self):
        guard = LoopGuard(); args = {'aktion': 'werkzeuge'}
        for _ in range(REPEAT_LIMIT - 1):
            self.assertIsNone(guard.before(args)); guard.after(args, 'liste', False)
        self.assertIn('Schleife erkannt', guard.before(args))

    def test_changed_arguments_reset_the_streak(self):
        guard = LoopGuard()
        for args in ({'a': 1}, {'a': 1}, {'a': 2}, {'a': 2}):
            self.assertIsNone(guard.before(args)); guard.after(args, 'x', False)

    def test_job_polls_are_not_blocked(self):
        guard = LoopGuard(); poll = {'job_id': 'a' * 32}
        for _ in range(10):
            self.assertIsNone(guard.before(poll)); guard.after(poll, 'laeuft', False)

    def test_stalled_poll_gets_hint(self):
        guard = LoopGuard(); poll = {'job_id': 'a' * 32}; hint = None
        for _ in range(POLL_LIMIT):
            hint = guard.after(poll, 'gleich', False)
        self.assertIn('keinen Fortschritt', hint)

    def test_hard_stop_after_repeated_errors(self):
        guard = LoopGuard()
        for i in range(ERROR_LIMIT):
            guard.after({'n': i}, 'fehler', True)
        self.assertIn('STOPP', guard.before({'n': 99}))

    def test_success_resets_error_count(self):
        guard = LoopGuard()
        for i in range(ERROR_LIMIT - 1):
            guard.after({'n': i}, 'fehler', True)
        guard.after({'n': 50}, 'ok', False)
        self.assertIsNone(guard.before({'n': 51}))

    def test_normalize_fills_missing_auftrag(self):
        self.assertEqual(normalize({'titel': 'SelfWG klonen'})['auftrag'], 'SelfWG klonen')
        self.assertEqual(normalize({'aktion': 'liste'}), {'aktion': 'liste'})
        self.assertEqual(normalize({'job_id': 'x', 'titel': 't'}), {'job_id': 'x', 'titel': 't'})
        self.assertEqual(normalize({'auftrag': 'a', 'titel': 't'})['auftrag'], 'a')


class Worker(BaseHTTPRequestHandler):
    seen = []
    def log_message(self, *args): pass
    def _send(self, body):
        data = json.dumps(body).encode()
        self.send_response(200); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        Worker.seen.append(self.path)
        self._send({'werkzeuge': []} if self.path == '/bonsai_tools' else {'done': True, 'phase': 'fertig', 'job_id': 'x'})
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        Worker.seen.append(('POST', self.path, body))
        self._send({'job_id': body.get('job_id'), 'status': 'gestartet'})


class McpTests(unittest.TestCase):
    def setUp(self):
        Worker.seen = []
        self.server = HTTPServer(('127.0.0.1', 0), Worker)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.key = tempfile.NamedTemporaryFile('w', delete=False); self.key.write('k'); self.key.close()
        self.proc = subprocess.Popen([sys.executable, str(INTEGRATIONS / 'bonsai_mcp.py')], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, text=True, encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8', 'BONSAI_WORKER_KEY_FILE': self.key.name,
            'BONSAI_WORKER_URL': 'http://127.0.0.1:%d' % self.server.server_port})
        self.next_id = 0

    def tearDown(self):
        self.proc.kill(); self.server.shutdown(); os.unlink(self.key.name)

    def call(self, arguments):
        self.next_id += 1
        self.proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': self.next_id, 'method': 'tools/call',
            'params': {'name': 'bonsai_auftrag', 'arguments': arguments}}) + '\n'); self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())['result']

    def test_repeated_werkzeuge_call_is_stopped_before_the_worker(self):
        results = [self.call({'aktion': 'werkzeuge'}) for _ in range(5)]
        self.assertFalse(results[0]['isError']); self.assertFalse(results[1]['isError'])
        self.assertTrue(results[2]['isError']); self.assertIn('Schleife erkannt', results[2]['content'][0]['text'])
        self.assertEqual(Worker.seen.count('/bonsai_tools'), 2)

    def test_missing_auftrag_is_derived_from_titel(self):
        result = self.call({'projekt': 'SelfWG', 'titel': 'SelfWG klonen'})
        self.assertFalse(result['isError'])
        posts = [s for s in Worker.seen if isinstance(s, tuple)]
        self.assertEqual(posts[0][2]['auftrag'], 'SelfWG klonen')

    def test_error_message_contains_example(self):
        result = self.call({'projekt': 'SelfWG'})
        self.assertTrue(result['isError']); self.assertIn('Beispiel für einen gültigen Aufruf', result['content'][0]['text'])


if __name__ == '__main__':
    unittest.main()
