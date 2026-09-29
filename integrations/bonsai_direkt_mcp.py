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
guard = LoopGuard()


def prop(kind, text):
    return {'type': kind, 'description': text}


COMMAND = {'type': 'object', 'required': ['befehl'], 'properties': {
    'befehl': prop('string', 'Shell-Befehl (bash). Ein Schritt pro Aufruf, kurz halten.'),
    'timeout': prop('integer', 'Sekunden bis Abbruch. Standard 60, höchstens 600. Lange Befehle mit festem Pfad und kleiner Suchtiefe.')}}

TOOLS = {
    'befehl_tower': ('Shell-Befehl als root auf dem Unraid-Tower (192.168.1.10). Shares unter /mnt/user, Docker, git. Nie über alle Shares suchen: feste Pfade, find mit -maxdepth.', COMMAND),
    'befehl_zimaboard': ('Shell-Befehl auf dem ZimaBoard 2 (192.168.1.103) als SvensenDE, für root sudo voranstellen. Dort laufen Bonsai und DerITler.', COMMAND),
    'ordner_auflisten': ('Inhalt eines Ordners unter /mnt/user auflisten.', {'type': 'object', 'properties': {
        'pfad': prop('string', 'Absoluter Pfad unter /mnt/user.')}}),
    'datei_lesen': ('Textdatei unter /mnt/user zeilenweise lesen (höchstens 2000 Zeilen je Aufruf).', {'type': 'object', 'required': ['pfad'], 'properties': {
        'pfad': prop('string', 'Absoluter Pfad unter /mnt/user.'),
        'ab_zeile': prop('integer', 'Erste Zeile, Standard 1.'),
        'zeilen': prop('integer', 'Anzahl Zeilen, Standard 400.')}}),
    'datei_schreiben': ('Neue Datei schreiben (überschreibt!) oder anhängen. Für Änderungen an bestehenden Dateien datei_ersetzen benutzen, nicht die ganze Datei neu schreiben.', {
        'type': 'object', 'required': ['pfad', 'inhalt'], 'properties': {
            'pfad': prop('string', 'Absoluter Pfad unter /mnt/user.'),
            'inhalt': prop('string', 'Kompletter Inhalt.'),
            'anhaengen': prop('boolean', 'true = ans Ende anhängen.')}}),
    'datei_ersetzen': ('Genau eine Textstelle in einer bestehenden Datei ersetzen. "alt" muss exakt und einmalig vorkommen (sonst Fehler, nichts wird geändert). Liefert Hashes und Zeilenzahl vorher/nachher als Beleg.', {
        'type': 'object', 'required': ['pfad', 'alt', 'neu'], 'properties': {
            'pfad': prop('string', 'Absoluter Pfad einer bestehenden Datei.'),
            'alt': prop('string', 'Exakter alter Text, einschließlich Einrückung.'),
            'neu': prop('string', 'Neuer Text.'),
            'alle': prop('boolean', 'true = alle Vorkommen ersetzen (sonst muss es genau eins geben).')}}),
}

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
open(tmp, "wb").write(new.encode("utf-8")); os.chmod(tmp, os.stat(path).st_mode); os.replace(tmp, path)
print(json.dumps({"pfad": path, "ersetzt": count if alle else 1,
    "zeilen_vorher": text.count("\n") + 1, "zeilen_nachher": new.count("\n") + 1,
    "sha256_vorher": hashlib.sha256(data).hexdigest()[:16], "sha256_nachher": hashlib.sha256(new.encode()).hexdigest()[:16]}))
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
        result = post('/befehl_tower', {'befehl': command, 'timeout': 30}, 45)
        return parse_edit(result)
    payload = {k: v for k, v in args.items() if k in TOOLS[name][1]['properties']}
    if name.startswith('befehl_'):
        if not isinstance(payload.get('befehl'), str) or not payload['befehl'].strip():
            raise ValueError('befehl (Text) erforderlich')
        payload['timeout'] = timeout
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
