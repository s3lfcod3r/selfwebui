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
        if self.path == '/befehl_werkstatt':
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
        os.environ['BONSAI_BACKUP_DIR'] = tempfile.mkdtemp()
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
        self.assertEqual(names, ['befehl_werkstatt', 'befehl_zimaboard', 'ordner_auflisten', 'datei_lesen', 'datei_schreiben', 'datei_ersetzen', 'doku_lesen', 'aenderung_rueckgaengig', 'projekt_pruefen', 'arbeitsbereich_anlegen'])

    def test_doku_lesen_refuses_foreign_domains_and_plain_http(self):
        error, text = self.tool('doku_lesen', url='https://evil.example.com/x')
        self.assertTrue(error); self.assertIn('nicht freigegeben', text)
        error, text = self.tool('doku_lesen', url='https://maxmind.github.io.evil.com/x')   # Endung täuscht nur
        self.assertTrue(error); self.assertIn('nicht freigegeben', text)
        error, text = self.tool('doku_lesen', url='http://docs.python.org/3/')
        self.assertTrue(error); self.assertIn('https', text)

    def test_doku_text_strips_markup_and_scripts(self):
        import importlib.util
        key = os.path.join(self.tmp, 'k.key'); Path(key).write_text('x')
        os.environ['BONSAI_WORKER_KEY_FILE'] = key
        spec = importlib.util.spec_from_file_location('mcp_doku', os.path.join(os.path.dirname(__file__), '..', 'integrations', 'bonsai_direkt_mcp.py'))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        text = module.doku_text('<html><head><title>t</title></head><body><script>alert(1)</script><h1>Titel</h1><p>a &amp; b</p><pre>x &lt; y</pre></body></html>')
        self.assertIn('Titel', text); self.assertIn('a & b', text); self.assertIn('x < y', text)
        self.assertNotIn('alert', text); self.assertNotIn('<', text.replace('x < y', ''))

    def test_edit_makes_backup_checks_syntax_and_can_be_undone(self):
        path = os.path.join(self.tmp, 'a.py'); Path(path).write_text('x = 1\n', encoding='utf-8')
        error, text = self.tool('datei_ersetzen', pfad=path, alt='x = 1', neu='x = (')   # absichtlich kaputt
        antwort = json.loads(text)
        self.assertTrue(antwort['sicherung']); self.assertTrue(antwort['syntax'].startswith('FEHLER')); self.assertIn('warnung', antwort)
        error, text = self.tool('aenderung_rueckgaengig', pfad=path)
        self.assertFalse(error); self.assertEqual(json.loads(text)['syntax'], 'ok')
        self.assertEqual(Path(path).read_text(encoding='utf-8'), 'x = 1\n')
        error, text = self.tool('aenderung_rueckgaengig', pfad=path, liste=True)
        self.assertGreaterEqual(len(json.loads(text)['sicherungen']), 2)   # Original und die kaputte Fassung

    def test_write_checks_json_and_undo_without_backup_is_an_error(self):
        path = os.path.join(self.tmp, 'b.json')
        error, text = self.tool('datei_schreiben', pfad=path, inhalt='{"a": }')
        self.assertTrue(json.loads(text)['syntax'].startswith('FEHLER'))
        error, text = self.tool('aenderung_rueckgaengig', pfad=os.path.join(self.tmp, 'nie-geaendert.txt'))
        self.assertTrue(error); self.assertIn('Keine Sicherung', text)

    def test_project_check_finds_syntax_errors_and_skips_foreign_commands(self):
        werk = os.path.join(self.tmp, 'werk'); os.makedirs(os.path.join(werk, 'repos', 'demo')); os.makedirs(os.path.join(werk, 'computer', 'data', 'workspaces', 'Demo'))
        Path(werk, 'repos', 'demo', 'ok.py').write_text('a = 1\n'); Path(werk, 'repos', 'demo', 'kaputt.py').write_text('def (:\n')
        Path(werk, 'computer', 'data', 'workspaces', 'Demo', 'PROJEKT.md').write_text('- **Prüfbefehl:** `rm -rf /tmp/x`\n', encoding='utf-8')
        os.environ['BONSAI_WERKSTATT'] = werk
        try:
            error, text = self.tool('projekt_pruefen', projekt='demo')
        finally:
            del os.environ['BONSAI_WERKSTATT']
        antwort = json.loads(text)
        self.assertEqual(antwort['syntax'], 'FEHLER'); self.assertEqual(antwort['dateien_geprueft'], 2)
        self.assertIn('kaputt.py', antwort['syntaxfehler'][0]); self.assertIn('pruefbefehl_hinweis', antwort)
        self.assertNotIn('pruefbefehl_exit', antwort)

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
        error, text = self.tool('befehl_werkstatt', befehl='exit 7')
        self.assertTrue(error); self.assertIn('exit_code_7', text)

    def test_identical_repeated_command_is_stopped_before_the_worker(self):
        for _ in range(5):
            error, text = self.tool('befehl_werkstatt', befehl='echo hallo')
        self.assertTrue(error); self.assertIn('Schleife erkannt', text)
        self.assertEqual(len([c for c in Worker.calls if c[0] == '/befehl_werkstatt']), 2)

    def test_missing_command_is_reported_without_calling_the_worker(self):
        error, text = self.tool('befehl_werkstatt')
        self.assertTrue(error); self.assertEqual(Worker.calls, [])

    def test_default_timeout_is_capped(self):
        self.tool('befehl_werkstatt', befehl='echo a', timeout=99999)
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
        self.assertEqual(f('cd /x && git status'), 'cd /x && /media/Safe-Storage/appdata/werkstatt/bin/git99 status')
        self.assertEqual(f('git status | head; git diff'), '/media/Safe-Storage/appdata/werkstatt/bin/git99 status | head; /media/Safe-Storage/appdata/werkstatt/bin/git99 diff')
        self.assertEqual(f("git -C '/a b' commit -m x"), "/media/Safe-Storage/appdata/werkstatt/bin/git99 -C '/a b' commit -m x")
        self.assertEqual(f('git --no-pager log -3'), '/media/Safe-Storage/appdata/werkstatt/bin/git99 --no-pager log -3')

    def test_text_in_quotes_and_heredocs_is_not_rewritten(self):
        f = self.als_nobody
        self.assertEqual(f('echo "git add x"'), 'echo "git add x"')
        self.assertEqual(f("printf '%s' 'fix: git add -A'"), "printf '%s' 'fix: git add -A'")
        self.assertEqual(f('git commit -m "fix git add"'), '/media/Safe-Storage/appdata/werkstatt/bin/git99 commit -m "fix git add"')
        heredoc = "cat > a <<'E'" + chr(10) + "git add -A" + chr(10) + "E" + chr(10)
        self.assertEqual(f(heredoc + "git status"), heredoc + "/media/Safe-Storage/appdata/werkstatt/bin/git99 status")
        self.assertEqual(f('cd x && (git status)'), 'cd x && (/media/Safe-Storage/appdata/werkstatt/bin/git99 status)')
        self.assertEqual(f('if true; then git status; fi'), 'if true; then /media/Safe-Storage/appdata/werkstatt/bin/git99 status; fi')
        self.assertEqual(f('echo git status'), 'echo git status')

    def test_already_wrapped_and_other_words_are_left_alone(self):
        f = self.als_nobody
        for cmd in ['/media/Safe-Storage/appdata/werkstatt/bin/git99 log', 'docker exec GitHubTool git pull', 'docker exec GitHubTool gitpush selfwg',
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

    def test_existing_folder_without_database_row_only_gets_the_row(self):
        folder = os.path.join(self.base, 'workspaces', 'SelfMailer'); os.makedirs(folder)
        Path(folder, 'PROJEKT.md').write_text('Projektregeln von Sven', encoding='utf-8')
        code, out = self.run_script('SelfMailer', 'Mail-Client')
        self.assertEqual(code, 0); self.assertEqual(out['arbeitsbereich'], 'SelfMailer')
        self.assertEqual(Path(folder, 'PROJEKT.md').read_text(encoding='utf-8'), 'Projektregeln von Sven')   # nicht überschrieben
        self.assertTrue(Path(folder, 'STATUS.md').is_file())                                              # fehlende Datei ergänzt
        import sqlite3
        self.assertEqual(sqlite3.connect(os.path.join(self.base, 'app.db')).execute("select count(*) from workspaces where name='SelfMailer'").fetchone()[0], 1)
        self.assertEqual(self.run_script('SelfMailer')[0], 4)   # jetzt gibt es die Zeile: zweites Anlegen wird abgelehnt

    def test_empty_description_survives_the_shell(self):
        """Regression: ein leeres Argument darf in der Shell nicht verschwinden."""
        import shlex
        command = "python3 -c %s %s %s" % (self.mcp.shlex_quote('import sys; print(len(sys.argv))'),
            self.mcp.shlex_quote(self.mcp.b64('Name')), self.mcp.shlex_quote(self.mcp.b64('')))
        out = subprocess.run(['bash', '-c', command.replace('python3', '"%s"' % sys.executable.replace(chr(92), '/'))], capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), '3')


if __name__ == '__main__':
    unittest.main()


class EnsureWorkspaceRowsTest(unittest.TestCase):
    def test_adds_only_missing_rows_and_is_repeatable(self):
        import importlib.util
        import sqlite3
        spec = importlib.util.spec_from_file_location('configure_direct', os.path.join(os.path.dirname(__file__), '..', 'scripts', 'configure_direct.py'))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        db = sqlite3.connect(':memory:')
        db.execute('create table workspaces (id text, user_id text, path text, name text, data text, created_at integer, updated_at integer)')
        db.execute("insert into workspaces values ('1','u1','/data/workspaces/RTX2000','RTX2000','{}',1,1)")
        self.assertEqual(module.ensure_workspace_rows(db, ['RTX2000', 'SelfStore']), ['SelfStore'])
        self.assertEqual(module.ensure_workspace_rows(db, ['RTX2000', 'SelfStore']), [])
        self.assertEqual(db.execute("select user_id from workspaces where name='SelfStore'").fetchone()[0], 'u1')


class GeloeschteArbeitsbereicheTest(unittest.TestCase):
    def modul(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('configure_direct_g', os.path.join(os.path.dirname(__file__), '..', 'scripts', 'configure_direct.py'))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def test_deleted_workspace_stays_deleted_and_new_names_are_added(self):
        import sqlite3
        module = self.modul()
        db = sqlite3.connect(':memory:')
        db.execute('create table workspaces (id text, user_id text, path text, name text, data text, created_at integer, updated_at integer)')
        db.execute("insert into workspaces values ('1','u1','/data/workspaces/A','A','{}',1,1)")
        # A hat einen Eintrag, B wurde früher angelegt und von Sven gelöscht, C ist ein ganz neuer Name
        pflegen, neu, geloescht = module.plane_arbeitsbereiche(db, ['A', 'B', 'C'], {'A', 'B'})
        self.assertEqual((pflegen, neu, geloescht), (['A', 'C'], ['C'], ['B']))
        self.assertEqual(module.ensure_workspace_rows(db, neu), ['C'])
        names = [r[0] for r in db.execute('select name from workspaces order by name')]
        self.assertEqual(names, ['A', 'C'])   # B bleibt weg

    def test_first_run_without_register_treats_all_known_names_as_created(self):
        module = self.modul()
        module.REGISTER = module.Path(os.path.join(tempfile.mkdtemp(), 'fehlt.json'))
        self.assertEqual(module.lade_register(['A', 'B']), {'A', 'B'})
