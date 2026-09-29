import json, os, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

INTEGRATIONS = Path(__file__).resolve().parents[1] / 'integrations'


class Worker(BaseHTTPRequestHandler):
    """Stub of the tool server: befehl_* really runs the command in bash."""
    calls = []
    def log_message(self, *args): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        Worker.calls.append((self.path, body))
        if self.path == '/befehl_tower':
            cmd = body['befehl'].replace('python3 ', '"%s" ' % sys.executable.replace('\\', '/'), 1)
            p = subprocess.run(['bash', '-c', cmd], capture_output=True, text=True, encoding='utf-8')
            out = {'exit_code': p.returncode, 'ausgabe': p.stdout + (('\n[stderr]\n' + p.stderr) if p.stderr.strip() else '')}
        elif self.path == '/datei_lesen':
            out = {'inhalt': Path(body['pfad']).read_text(encoding='utf-8')}
        else:
            out = {'fehler': 'unbekannt'}
        data = json.dumps(out).encode()
        self.send_response(200); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)


class DirectMcpTests(unittest.TestCase):
    def setUp(self):
        Worker.calls = []
        self.server = HTTPServer(('127.0.0.1', 0), Worker)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.tmp = tempfile.mkdtemp()
        self.key = os.path.join(self.tmp, 'key'); Path(self.key).write_text('k')
        self.proc = subprocess.Popen([sys.executable, str(INTEGRATIONS / 'bonsai_direkt_mcp.py')], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, text=True, encoding='utf-8', env={**os.environ, 'PYTHONIOENCODING': 'utf-8',
            'BONSAI_WORKER_KEY_FILE': self.key, 'BONSAI_WORKER_URL': 'http://127.0.0.1:%d' % self.server.server_port})
        self.ident = 0

    def tearDown(self):
        self.proc.kill(); self.proc.wait(); self.proc.stdin.close(); self.proc.stdout.close(); self.server.shutdown(); self.server.server_close()

    def rpc(self, method, params=None):
        self.ident += 1
        self.proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': self.ident, 'method': method, 'params': params or {}}) + '\n')
        self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())['result']

    def tool(self, name, **args):
        result = self.rpc('tools/call', {'name': name, 'arguments': args})
        return result['isError'], result['content'][0]['text']

    def file(self, text):
        path = os.path.join(self.tmp, 'a.txt'); Path(path).write_text(text, encoding='utf-8', newline='\n'); return path

    def test_tools_are_flat_and_do_not_include_the_planner_tool(self):
        names = [t['name'] for t in self.rpc('tools/list')['tools']]
        self.assertEqual(names, ['befehl_tower', 'befehl_zimaboard', 'ordner_auflisten', 'datei_lesen', 'datei_schreiben', 'datei_ersetzen'])

    def test_replace_changes_exactly_one_place_and_reports_hashes(self):
        path = self.file('eins\nzwei\ndrei\n')
        error, text = self.tool('datei_ersetzen', pfad=path, alt='zwei', neu='2')
        self.assertFalse(error)
        info = json.loads(text)
        self.assertEqual(Path(path).read_text(encoding='utf-8'), 'eins\n2\ndrei\n')
        self.assertNotEqual(info['sha256_vorher'], info['sha256_nachher'])
        self.assertEqual(info['ersetzt'], 1)

    def test_replace_refuses_ambiguous_match_and_leaves_file_untouched(self):
        path = self.file('x\nx\n')
        error, text = self.tool('datei_ersetzen', pfad=path, alt='x', neu='y')
        self.assertTrue(error); self.assertIn('text_mehrdeutig', text)
        self.assertEqual(Path(path).read_text(encoding='utf-8'), 'x\nx\n')

    def test_replace_reports_missing_text_with_diagnosis(self):
        path = self.file('abc\n')
        error, text = self.tool('datei_ersetzen', pfad=path, alt='zzz', neu='y')
        self.assertTrue(error); self.assertIn('text_nicht_gefunden', text)

    def test_replace_handles_quotes_and_umlauts(self):
        path = self.file("print('Größe')\n")
        error, _ = self.tool('datei_ersetzen', pfad=path, alt="'Größe'", neu='"Maß"')
        self.assertFalse(error)
        self.assertEqual(Path(path).read_text(encoding='utf-8'), 'print("Maß")\n')

    def test_failed_command_carries_diagnosis(self):
        error, text = self.tool('befehl_tower', befehl='exit 7')
        self.assertTrue(error); self.assertIn('exit_code_7', text)

    def test_identical_repeated_command_is_stopped_before_the_worker(self):
        for _ in range(5):
            error, text = self.tool('befehl_tower', befehl='echo hallo')
        self.assertTrue(error); self.assertIn('Schleife erkannt', text)
        self.assertEqual(len([c for c in Worker.calls if c[0] == '/befehl_tower']), 2)

    def test_missing_command_is_reported_without_calling_the_worker(self):
        error, text = self.tool('befehl_tower')
        self.assertTrue(error); self.assertEqual(Worker.calls, [])

    def test_default_timeout_is_capped(self):
        self.tool('befehl_tower', befehl='echo a', timeout=99999)
        self.assertEqual(Worker.calls[0][1]['timeout'], 600)


if __name__ == '__main__':
    unittest.main()
