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
        self.assertEqual(names, ['befehl_tower', 'befehl_zimaboard', 'ordner_auflisten', 'datei_lesen', 'datei_schreiben', 'datei_ersetzen', 'arbeitsbereich_anlegen'])

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

    def test_write_creates_missing_folders_and_reports_new_file(self):
        path = os.path.join(self.tmp, 'neu', 'tief', 'b.txt')
        error, text = self.tool('datei_schreiben', pfad=path, inhalt='Größe\n')
        self.assertFalse(error); self.assertTrue(json.loads(text)['neu'])
        self.assertEqual(Path(path).read_text(encoding='utf-8'), 'Größe\n')

    def test_write_can_append_and_overwrite(self):
        path = self.file('a\n')
        self.assertFalse(self.tool('datei_schreiben', pfad=path, inhalt='b\n', anhaengen=True)[0])
        self.assertEqual(Path(path).read_text(encoding='utf-8'), 'a\nb\n')
        self.assertFalse(self.tool('datei_schreiben', pfad=path, inhalt='c\n')[0])
        self.assertEqual(Path(path).read_text(encoding='utf-8'), 'c\n')

    def test_write_rejects_relative_path_and_huge_content(self):
        error, text = self.tool('datei_schreiben', pfad='relativ.txt', inhalt='x')
        self.assertTrue(error); self.assertIn('Absoluter Pfad', text)
        error, text = self.tool('datei_schreiben', pfad=os.path.join(self.tmp, 'g.txt'), inhalt='x' * 70000)
        self.assertTrue(error); self.assertIn('zu groß', text)


class AlsNobodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        key = tempfile.NamedTemporaryFile('w', delete=False); key.write('k'); key.close()
        os.environ['BONSAI_WORKER_KEY_FILE'] = key.name
        sys.path.insert(0, str(INTEGRATIONS))
        import bonsai_direkt_mcp
        cls.als_nobody = staticmethod(bonsai_direkt_mcp.als_nobody)

    def test_plain_calls_and_chains_are_rewritten(self):
        f = self.als_nobody
        self.assertEqual(f('cd /x && git status'), 'cd /x && runuser -u nobody -- git status')
        self.assertEqual(f('git status | head; git diff'), 'runuser -u nobody -- git status | head; runuser -u nobody -- git diff')
        self.assertEqual(f("git -C '/a b' commit -m x"), "runuser -u nobody -- git -C '/a b' commit -m x")
        self.assertEqual(f('git --no-pager log -3'), 'runuser -u nobody -- git --no-pager log -3')

    def test_already_wrapped_and_other_words_are_left_alone(self):
        f = self.als_nobody
        for cmd in ['runuser -u nobody -- git log', 'docker exec GitHubTool git pull', 'docker exec GitHubTool gitpush selfwg',
                    '/usr/bin/git status', 'echo digit', 'git --version', 'ls github']:
            self.assertEqual(f(cmd), cmd, cmd)


class ArbeitsbereichTests(unittest.TestCase):
    """Führt das Anlege-Skript gegen eine Test-Datenbank aus (ohne Docker)."""
    @classmethod
    def setUpClass(cls):
        key = tempfile.NamedTemporaryFile('w', delete=False); key.write('k'); key.close()
        os.environ['BONSAI_WORKER_KEY_FILE'] = key.name
        sys.path.insert(0, str(INTEGRATIONS))
        import bonsai_direkt_mcp
        cls.mcp = bonsai_direkt_mcp

    def setUp(self):
        import sqlite3
        self.base = tempfile.mkdtemp()
        db = sqlite3.connect(os.path.join(self.base, 'app.db'))
        db.execute('create table workspaces (id text, user_id text, path text, name text, data text, created_at integer, updated_at integer)')
        db.execute("insert into workspaces values ('1','u1','/x/RTX2000','RTX2000','{}',1,1)"); db.commit(); db.close()

    def run_script(self, name, beschreibung=''):
        env = {**os.environ, 'CPTR_DATA_DIR': self.base, 'PYTHONIOENCODING': 'utf-8'}
        p = subprocess.run([sys.executable, '-c', self.mcp.WORKSPACE_SCRIPT, self.mcp.b64(name), self.mcp.b64(beschreibung)],
            capture_output=True, text=True, encoding='utf-8', env=env)
        return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])

    def test_creates_folder_files_and_database_row(self):
        code, out = self.run_script('SelfStore', 'Der App-Store für die Self-Apps')
        self.assertEqual(code, 0); self.assertEqual(out['arbeitsbereich'], 'SelfStore')
        folder = os.path.join(self.base, 'workspaces', 'SelfStore')
        self.assertIn('Der App-Store', Path(folder, 'PROJEKT.md').read_text(encoding='utf-8'))
        self.assertTrue(Path(folder, 'STATUS.md').is_file())
        import sqlite3
        row = sqlite3.connect(os.path.join(self.base, 'app.db')).execute("select user_id, path, data from workspaces where name='SelfStore'").fetchone()
        self.assertEqual(row[0], 'u1'); self.assertTrue(row[1].endswith('/workspaces/SelfStore'))
        layout = json.loads(row[2]); self.assertEqual(layout['groups'][0]['tabs'][0]['type'], 'files')

    def test_existing_or_invalid_names_are_rejected(self):
        self.assertEqual(self.run_script('SelfStore')[0], 0)
        code, out = self.run_script('SelfStore'); self.assertEqual(code, 4); self.assertIn('existiert bereits', out['fehler'])
        for bad in ['a', '../etc', 'Name mit Leerzeichen', 'x' * 41, '.versteckt']:
            code, out = self.run_script(bad); self.assertEqual(code, 3, bad)

    def test_empty_description_survives_the_shell(self):
        """Regression: ein leeres Argument darf in der Shell nicht verschwinden."""
        import shlex
        command = "python3 -c %s %s %s" % (self.mcp.shlex_quote('import sys; print(len(sys.argv))'),
            self.mcp.shlex_quote(self.mcp.b64('Name')), self.mcp.shlex_quote(self.mcp.b64('')))
        out = subprocess.run(['bash', '-c', command.replace('python3', '"%s"' % sys.executable.replace(chr(92), '/'))], capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), '3')


if __name__ == '__main__':
    unittest.main()
