#!/usr/bin/env python3
"""Flat, small-model-friendly tools for working with Bonsai alone (no cloud planner).

Every tool maps to one HTTP endpoint of the worker tool server; the schemas are
deliberately flat. A loop brake stops identical repeated calls, failed calls carry
a diagnosis (cause, self-fixable, next step) and edits report hashes so a model
cannot claim a change that did not happen.
"""
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diagnose import diagnose
from loop_guard import LoopGuard

BASE = os.environ.get('BONSAI_WORKER_URL', 'http://OpenWebUI-Werkzeuge:8000').rstrip('/')
KEY = Path(os.environ.get('BONSAI_WORKER_KEY_FILE', '/data/brain/worker.key')).read_text().strip()
DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 600
MAX_WRITE = 60000  # one ssh argument is limited to ~128 KB (base64 inflates by a third)
guard = LoopGuard()


def prop(kind, text):
    return {'type': kind, 'description': text}


COMMAND = {'type': 'object', 'required': ['befehl'], 'properties': {
    'befehl': prop('string', 'Shell-Befehl (bash). Ein Schritt pro Aufruf, kurz halten.'),
    'timeout': prop('integer', 'Sekunden bis Abbruch. Standard 60, höchstens 600. Lange Befehle mit festem Pfad und kleiner Suchtiefe.')}}

TOOLS = {
    'befehl_werkstatt': ('Shell-Befehl als root auf der Werkstatt (ZimaBoard 2, 192.168.1.96). Docker (AndroidBuild, GitHubTool), git, Repos unter /media/Safe-Storage/appdata/werkstatt/repos. Nie über alle Shares suchen: feste Pfade, find mit -maxdepth.', COMMAND),
    'befehl_zimaboard': ('Shell-Befehl auf dem ZimaBoard 1 (192.168.1.103) als SvensenDE, für root sudo voranstellen. Dort laufen Bonsai und DerITler.', COMMAND),
    'ordner_auflisten': ('Inhalt eines Ordners unter /media/Safe-Storage/appdata/werkstatt auflisten.', {'type': 'object', 'properties': {
        'pfad': prop('string', 'Absoluter Pfad unter /media/Safe-Storage/appdata/werkstatt.')}}),
    'datei_lesen': ('Textdatei unter /media/Safe-Storage/appdata/werkstatt zeilenweise lesen (höchstens 2000 Zeilen je Aufruf).', {'type': 'object', 'required': ['pfad'], 'properties': {
        'pfad': prop('string', 'Absoluter Pfad unter /media/Safe-Storage/appdata/werkstatt.'),
        'ab_zeile': prop('integer', 'Erste Zeile, Standard 1.'),
        'zeilen': prop('integer', 'Anzahl Zeilen, Standard 400.')}}),
    'datei_schreiben': ('Neue Datei schreiben (überschreibt!) oder anhängen. Legt fehlende Ordner selbst an (kein mkdir nötig). Für Änderungen an bestehenden Dateien datei_ersetzen benutzen, nicht die ganze Datei neu schreiben.', {
        'type': 'object', 'required': ['pfad', 'inhalt'], 'properties': {
            'pfad': prop('string', 'Absoluter Pfad unter /media/Safe-Storage/appdata/werkstatt.'),
            'inhalt': prop('string', 'Kompletter Inhalt.'),
            'anhaengen': prop('boolean', 'true = ans Ende anhängen.')}}),
    'datei_ersetzen': ('Genau eine Textstelle in einer bestehenden Datei ersetzen. "alt" muss exakt und einmalig vorkommen (sonst Fehler, nichts wird geändert). Liefert Hashes und Zeilenzahl vorher/nachher als Beleg.', {
        'type': 'object', 'required': ['pfad', 'alt', 'neu'], 'properties': {
            'pfad': prop('string', 'Absoluter Pfad einer bestehenden Datei.'),
            'alt': prop('string', 'Exakter alter Text, einschließlich Einrückung.'),
            'neu': prop('string', 'Neuer Text.'),
            'alle': prop('boolean', 'true = alle Vorkommen ersetzen (sonst muss es genau eins geben).')}}),
    'arbeitsbereich_anlegen': ('Legt für ein NEUES Thema oder Projekt einen eigenen Arbeitsbereich in Open WebUI an (Ordner mit PROJEKT.md und STATUS.md, eigene Chat-Liste). Nur wenn Sven ein neues Thema startet und es noch keinen Arbeitsbereich dafür gibt. Er erscheint nach Neuladen der Seite links in der Seitenleiste.', {
        'type': 'object', 'required': ['name'], 'properties': {
            'name': prop('string', 'Kurzer Name des Themas, 2 bis 40 Zeichen: Buchstaben, Ziffern, Punkt, Unterstrich, Minus (z. B. SelfStore).'),
            'beschreibung': prop('string', 'Ein bis zwei Sätze, worum es geht (kommt in PROJEKT.md).')}}),
}

WORKSPACE_SCRIPT = r'''
import base64, json, os, re, sqlite3, sys, time, uuid
name, beschreibung = (base64.b64decode(a).decode() for a in sys.argv[1:3])
base = os.environ.get("CPTR_DATA_DIR", "/data")
if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{1,39}", name):
    print(json.dumps({"fehler": "Ungültiger Name (2 bis 40 Zeichen: Buchstaben, Ziffern, Punkt, Unterstrich, Minus)"})); sys.exit(3)
path = base + "/workspaces/" + name
db = sqlite3.connect(base + "/app.db", timeout=30)
if db.execute("select 1 from workspaces where path=?", (path,)).fetchone():
    print(json.dumps({"fehler": "Arbeitsbereich existiert bereits: " + name})); sys.exit(4)
user = db.execute("select user_id from workspaces order by created_at limit 1").fetchone()
if not user:
    print(json.dumps({"fehler": "Kein Nutzer mit Arbeitsbereichen gefunden"})); sys.exit(5)
os.makedirs(path, exist_ok=True)   # Ordner kann schon da sein (vom Update angelegt): dann nur den Eintrag ergänzen
datum = time.strftime("%d.%m.%Y")
projekt = ("# Projekt " + name + "\n\n- **Beschreibung:** " + (beschreibung.strip() or "(noch leer)") + "\n- **Angelegt:** " + datum
    + "\n- **Klon:** (noch nicht festgelegt)\n\n## Bekannte offene Punkte\n- (noch keine)\n\n## Gelernt (nicht wiederholen)\n- (noch nichts)\n")
status = "## Aufgaben\n- Projekt angelegt — in Arbeit: noch keine Aufgabe\n\n## Offene Fragen\n- (keine)\n"
for datei, inhalt in (("/PROJEKT.md", projekt), ("/STATUS.md", status)):
    if not os.path.exists(path + datei):   # vorhandene Dateien (z. B. Projektregeln) nie überschreiben
        open(path + datei, "w", encoding="utf-8").write(inhalt)
daten = {"groups": [{"id": "default", "tabs": [{"id": "files", "type": "files", "label": "Files", "permanent": True}],
    "activeTabId": "files", "tabHistory": ["files"]}], "activeGroupId": "default", "layout": {"type": "group", "groupId": "default"},
    "splitDirection": "horizontal", "splitRatio": 0.5, "fileBrowserCwd": path}
jetzt = int(time.time())
db.execute("insert into workspaces (id, user_id, path, name, data, created_at, updated_at) values (?,?,?,?,?,?,?)",
    (str(uuid.uuid4()), user[0], path, name, json.dumps(daten), jetzt, jetzt)); db.commit()
print(json.dumps({"arbeitsbereich": name, "pfad": path, "dateien": ["PROJEKT.md", "STATUS.md"],
    "hinweis": "Seite neu laden, dann links in der Seitenleiste öffnen und dort einen neuen Chat starten."}))
'''

EDIT_SCRIPT = r'''
import base64, hashlib, json, os, sys
path, alt, neu = (base64.b64decode(a).decode() for a in sys.argv[1:4])
alle = sys.argv[4] == "1"
if not os.path.isabs(path) or not os.path.isfile(path):
    print(json.dumps({"fehler": "Datei nicht gefunden: " + path})); sys.exit(3)
data = open(path, "rb").read(); text = data.decode("utf-8")
count = text.count(alt)
if not alt or count == 0:
    print(json.dumps({"fehler": "alt nicht gefunden", "hinweis": "Text exakt inklusive Leerzeichen aus datei_lesen kopieren."})); sys.exit(4)
if count > 1 and not alle:
    print(json.dumps({"fehler": "alt kommt %d-mal vor" % count, "hinweis": "Mehr Umgebung in alt aufnehmen oder alle=true setzen."})); sys.exit(5)
new = text.replace(alt, neu) if alle else text.replace(alt, neu, 1)
tmp = path + ".tmp-bonsai"
st = os.stat(path)
open(tmp, "wb").write(new.encode("utf-8")); os.chmod(tmp, st.st_mode)
try:
    os.chown(tmp, st.st_uid, st.st_gid)  # keep the owner: root-owned files break SMB access on the shares
except (OSError, AttributeError):  # AttributeError: no chown on Windows (tests only)
    pass
os.replace(tmp, path)
print(json.dumps({"pfad": path, "ersetzt": count if alle else 1,
    "zeilen_vorher": text.count("\n") + 1, "zeilen_nachher": new.count("\n") + 1,
    "sha256_vorher": hashlib.sha256(data).hexdigest()[:16], "sha256_nachher": hashlib.sha256(new.encode()).hexdigest()[:16]}))
'''

WRITE_SCRIPT = r'''
import base64, json, os, sys
path, content = (base64.b64decode(a).decode() for a in sys.argv[1:3])
append = sys.argv[3] == "1"
if not os.path.isabs(path):
    print(json.dumps({"fehler": "Absoluter Pfad erforderlich: " + path})); sys.exit(3)
missing, parent = [], os.path.dirname(path)
while parent and not os.path.isdir(parent):
    missing.append(parent); parent = os.path.dirname(parent)
os.makedirs(os.path.dirname(path), exist_ok=True)
existed = os.path.exists(path)
with open(path, "a" if append else "w", encoding="utf-8") as f:
    f.write(content)
if path.startswith("/media/Safe-Storage/appdata/werkstatt/"):  # new entries belong to nobody:users like the rest of the shares
    for created in missing + ([] if existed else [path]):
        os.chown(created, 99, 100)
print(json.dumps({"pfad": path, "geschrieben_zeichen": len(content), "modus": "a" if append else "w", "neu": not existed}))
'''


def post(path, data, timeout):
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode(),
        headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        try:
            return json.load(error)
        except ValueError:
            return {'fehler': 'HTTP %d' % error.code}
    except OSError as error:
        return {'fehler': 'Werkzeug-Server nicht erreichbar: %s' % type(error).__name__}


def b64(text):
    return base64.b64encode(text.encode()).decode()


# Git als root legt root-eigene Dateien in .git an; danach kann der Container GitHubTool (Nutzer 99) nicht mehr
# pushen oder pullen. Darum wird jeder git-Aufruf auf der Werkstatt (Board 2) als nobody ausgeführt, egal ob das Modell daran denkt.
GIT_AUFRUF = re.compile(
    r'(?<![\w./-])git(?=\s+(?:(?:-C\s+(?:"[^"]*"|\'[^\']*\'|\S+)|-c\s+\S+|--no-pager|-P)\s+)*[a-z])')


HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")
BEFEHLSANFANG = ';&|({\n`'


def geschuetzt(befehl):
    """Zeichen in Anführungszeichen und in Heredoc-Texten: dort steht Text, kein Befehl."""
    maske = [False] * len(befehl)
    ende = {}
    for treffer in HEREDOC.finditer(befehl):
        zeilenende = befehl.find('\n', treffer.end())
        if zeilenende < 0:
            continue
        pos = zeilenende + 1
        while pos < len(befehl):
            nach = befehl.find('\n', pos)
            zeile = befehl[pos:] if nach < 0 else befehl[pos:nach]
            if zeile.strip() == treffer.group(2):
                break
            if nach < 0:
                pos = len(befehl)
                break
            pos = nach + 1
        ende[zeilenende + 1] = pos
    quote, i = None, 0
    while i < len(befehl):
        if i in ende:
            for k in range(i, min(ende[i], len(befehl))):
                maske[k] = True
            i = ende[i]
            continue
        zeichen = befehl[i]
        if quote:
            maske[i] = True
            if zeichen == '\\' and quote == '"':
                i += 1
                if i < len(befehl):
                    maske[i] = True
            elif zeichen == quote:
                quote = None
        elif zeichen in '\'"':
            quote = zeichen
            maske[i] = True
        i += 1
    return maske


def als_nobody(befehl):
    """git-Aufrufe als nobody ausführen, aber nur dort, wo wirklich ein Befehl steht (nicht in Texten)."""
    maske = geschuetzt(befehl)

    def ersetze(treffer):
        start = treffer.start()
        davor = befehl[max(0, start - 60):start]
        if 'git99' in davor or 'docker exec' in davor or 'docker run' in davor:
            return treffer.group(0)
        if maske[start]:
            return treffer.group(0)
        pos = start - 1
        while pos >= 0 and befehl[pos] in ' \t':
            pos -= 1
        if pos >= 0 and befehl[pos] not in BEFEHLSANFANG:
            vorwort = re.search(r'(\w+)\s*$', befehl[:start])
            if not vorwort or vorwort.group(1) not in ('then', 'do', 'else', 'elif', 'time'):
                return treffer.group(0)
        return '/media/Safe-Storage/appdata/werkstatt/bin/git99'
    return GIT_AUFRUF.sub(ersetze, befehl)


def run(name, args):
    if name not in TOOLS:
        raise ValueError('Unbekanntes Werkzeug: ' + name)
    if not isinstance(args, dict):
        raise ValueError('Objekt erwartet')
    timeout = max(1, min(int(args.get('timeout') or DEFAULT_TIMEOUT), MAX_TIMEOUT))
    if name == 'datei_ersetzen':
        for field in ('pfad', 'alt', 'neu'):
            if not isinstance(args.get(field), str):
                raise ValueError('%s (Text) erforderlich' % field)
        command = "python3 -c %s %s %s %s %s" % (
            shlex_quote(EDIT_SCRIPT), b64(args['pfad']), b64(args['alt']), b64(args['neu']), '1' if args.get('alle') else '0')
        result = post('/befehl_werkstatt', {'befehl': command, 'timeout': 30}, 45)
        return parse_edit(result)
    if name == 'arbeitsbereich_anlegen':
        if not isinstance(args.get('name'), str):
            raise ValueError('name (Text) erforderlich')
        beschreibung = args.get('beschreibung') if isinstance(args.get('beschreibung'), str) else ''
        command = "docker exec OpenWebUI-Computer /opt/cptr/bin/python -c %s %s %s" % (
            shlex_quote(WORKSPACE_SCRIPT), shlex_quote(b64(args['name'])), shlex_quote(b64(beschreibung)))  # '' bleibt ein Argument
        return parse_edit(post('/befehl_werkstatt', {'befehl': command, 'timeout': 30}, 45))
    if name == 'datei_schreiben':
        for field in ('pfad', 'inhalt'):
            if not isinstance(args.get(field), str):
                raise ValueError('%s (Text) erforderlich' % field)
        if len(args['inhalt']) > MAX_WRITE:
            raise ValueError('Inhalt zu groß (%d Zeichen, höchstens %d). In Teilen mit anhaengen=true schreiben.' % (len(args['inhalt']), MAX_WRITE))
        command = "python3 -c %s %s %s %s" % (
            shlex_quote(WRITE_SCRIPT), b64(args['pfad']), b64(args['inhalt']), '1' if args.get('anhaengen') else '0')
        return parse_edit(post('/befehl_werkstatt', {'befehl': command, 'timeout': 30}, 45))
    payload = {k: v for k, v in args.items() if k in TOOLS[name][1]['properties']}
    if name.startswith('befehl_'):
        if not isinstance(payload.get('befehl'), str) or not payload['befehl'].strip():
            raise ValueError('befehl (Text) erforderlich')
        payload['timeout'] = timeout
        if name == 'befehl_werkstatt':
            payload['befehl'] = als_nobody(payload['befehl'])
    return post('/' + name, payload, timeout + 20)


def shlex_quote(text):
    return "'" + text.replace("'", "'\"'\"'") + "'"


def parse_edit(result):
    if result.get('exit_code') == 0:
        try:
            return json.loads(result['ausgabe'].strip().splitlines()[-1])
        except (ValueError, IndexError):
            return {'fehler': 'Unerwartete Antwort der Änderung', 'ausgabe': result.get('ausgabe', '')[:300]}
    try:
        return json.loads(result['ausgabe'].strip().splitlines()[0])
    except (ValueError, KeyError, IndexError):
        return {'fehler': 'Änderung fehlgeschlagen', 'ausgabe': str(result.get('ausgabe', ''))[:300]}


def failed(result):
    return isinstance(result, dict) and ('fehler' in result or ('exit_code' in result and result['exit_code'] != 0))


def handle(name, args):
    key = {'werkzeug': name, 'argumente': args}
    hint = guard.before(key)
    if hint is not None:
        guard.after(key, hint, True)
        return {'content': [{'type': 'text', 'text': hint}], 'isError': True}
    try:
        result = run(name, args)
    except Exception as error:
        result = {'fehler': '%s: %s' % (type(error).__name__, error)}
    bad = failed(result)
    if bad:
        result = {**result, 'diagnose': diagnose(result)}
    text = json.dumps(result, ensure_ascii=False)
    extra = guard.after(key, text, bad)
    return {'content': [{'type': 'text', 'text': text + ('\n' + extra if extra else '')}], 'isError': bad}


def send(message):
    print(json.dumps(message, ensure_ascii=False), flush=True)


def main():
    for line in sys.stdin:
        ident = None
        try:
            msg = json.loads(line)
            ident = msg.get('id')
            if ident is None:
                continue
            method = msg.get('method')
            if method == 'initialize':
                result = {'protocolVersion': msg.get('params', {}).get('protocolVersion', '2024-11-05'),
                    'capabilities': {'tools': {}}, 'serverInfo': {'name': 'bonsai-direkt', 'version': '1.0.0'}}
            elif method == 'ping':
                result = {}
            elif method == 'tools/list':
                result = {'tools': [{'name': n, 'description': d, 'inputSchema': s} for n, (d, s) in TOOLS.items()]}
            elif method == 'tools/call':
                params = msg.get('params', {})
                result = handle(params.get('name'), params.get('arguments', {}))
            else:
                send({'jsonrpc': '2.0', 'id': ident, 'error': {'code': -32601, 'message': 'Method not found'}})
                continue
            send({'jsonrpc': '2.0', 'id': ident, 'result': result})
        except Exception as error:
            if ident is not None:
                send({'jsonrpc': '2.0', 'id': ident, 'result': {'content': [{'type': 'text',
                    'text': 'Fehler: %s: %s' % (type(error).__name__, error)}], 'isError': True}})


if __name__ == '__main__':
    main()
