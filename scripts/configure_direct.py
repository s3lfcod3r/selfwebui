"""Opt-in: run Bonsai alone (no cloud planner) in the RTX2000 workspace.

Usage: run in a one-off container while Computer is STOPPED (a running instance writes its cached
config back on shutdown and undoes the change): python configure_direct.py [integrations-dir]
Backs up app.db and config.toml first. config.toml [app_config] wins over the database on every start.
"""
import json
import os
import re
import shutil
import sqlite3
import sys
import time
import uuid
from pathlib import Path

SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/opt/selfwebui/integrations')
DATA = Path(os.environ.get('CPTR_DATA_DIR', '/data'))
DB = DATA / 'app.db'
BRAIN = DATA / 'brain'
# Arbeitsbereiche mit Bonsai-Regeln; optional eine Projektdatei aus integrations/ (wird angehängt)
WORKSPACES = {'RTX2000': None, 'SelfWG': 'projekt_SelfWG.md', 'SelfDashboard': 'projekt_SelfDashboard.md', 'SelfStorm': 'projekt_SelfStorm.md', 'SelfStream': 'projekt_SelfStream.md', 'SelfStreamDesktop': 'projekt_SelfStreamDesktop.md',
              'SelfStore': 'projekt_SelfStore.md', 'SelfMailer': 'projekt_SelfMailer.md', 'SelfRemote': 'projekt_SelfRemote.md', 'SelfAuthenticator': 'projekt_SelfAuthenticator.md', 'SelfArchiver': 'projekt_SelfArchiver.md', 'SelfFon': 'projekt_SelfFon.md', 'SelfMediaHub': 'projekt_SelfMediaHub.md', 'SelfPoolTracker': 'projekt_SelfPoolTracker.md', 'SelfScreen': 'projekt_SelfScreen.md', 'SelfThreatMap': 'projekt_SelfThreatMap.md', 'SelfGuard': 'projekt_SelfGuard.md', 'SelfCoder': 'projekt_SelfCoder.md'}
MODELS = ['bonsai-2-27b', 'RTX2000/bonsai-2-27b']
BUILTIN_ALLE = ('files', 'terminal', 'web', 'browser', 'memory', 'chats', 'skills', 'tasks', 'automations', 'images', 'subagents', 'notifications')
BUILTIN_AN = ('tasks', 'chats', 'memory', 'notifications', 'automations', 'subagents')   # 'browser' liefert hier keine Werkzeuge, bleibt aus
# Tool-heavy work: lower temperature than the 1.0 of the model card; other values from the card.
PROJEKT_HINWEIS = (
    "\n\nPROJEKTREGELN\n"
    "Zu Beginn jeder Aufgabe in einem Projekt zuerst die Projektdatei deines Arbeitsbereichs lesen, falls sie existiert: "
    "cat /media/Safe-Storage/appdata/werkstatt/computer/data/workspaces/<Name>/PROJEKT.md. Der Arbeitsbereich <Name> steht in deinem Kontext "
    "(Pfad /data/workspaces/<Name>). Die Datei nennt Klon, Version, Schlüssel-Referenz, bekannte Punkte und Gelerntes. Danach arbeiten.\n")
STATUS_START = ("## Aufgaben\n- Erste Prüfung des Projekts — offen: Struktur, Git-Stand, README, Version und Fehler prüfen, "
                "Befunde mit Datei:Zeile belegen, PROJEKT.md ergänzen\n\n## Offene Fragen\n- (keine)\n")
COMPACT_TOKENS = 70000  # Model server has 262144 tokens of context, but on the RTX 2000E replies slow down and Bonsai gets stuck in thinking
#                         above ~50-100k tokens (observed 02.-03.10.2026); compacting at 70k keeps chats short. Raise it again if summaries lose too much.
REQUEST_PARAMS = {'max_tokens': 16384, 'temperature': 0.7, 'top_p': 0.95, 'top_k': 20, 'min_p': 0.05}


def load(connection, key):
    row = connection.execute('select value from config where key=?', (key,)).fetchone()
    return json.loads(row[0]) if row and isinstance(row[0], str) else (row[0] if row else None)


def write_toml(path, updates):
    """Replace `key = "<json>"` lines of [app_config]; cptr re-seeds the DB from this file at start."""
    lines = path.read_text(encoding='utf-8').split('\n')
    for key, value in updates.items():
        line = '%s = %s' % (json.dumps(key) if '.' in key else key, json.dumps(json.dumps(value, ensure_ascii=False)))
        pattern = re.compile(r'^"?%s"? = ' % re.escape(key))
        hits = [i for i, text in enumerate(lines) if pattern.match(text)]
        if len(hits) != 1:
            raise SystemExit('config.toml: expected exactly one line for ' + key)
        lines[hits[0]] = line
    path.write_text('\n'.join(lines), encoding='utf-8')


TOOL_FILES = ('bonsai_direkt_mcp.py', 'loop_guard.py', 'diagnose.py')


def install_tools():
    """Copy the tool server files from the image into /data/brain (they used to stay at the first installed version)."""
    BRAIN.mkdir(parents=True, exist_ok=True)
    for name in TOOL_FILES:
        source, target = SOURCE / name, BRAIN / name
        if not source.is_file():
            raise SystemExit('Missing in image: ' + name)
        if target.is_file() and target.read_bytes() == source.read_bytes():
            continue
        owner = target.stat() if target.is_file() else None
        if target.is_file():
            shutil.copy(target, str(target) + '.vor-update-' + time.strftime('%Y%m%d'))
        shutil.copy(source, target)
        if owner is not None:
            os.chown(target, owner.st_uid, owner.st_gid)
        print('Tool file updated:', name)


REGISTER = DATA / 'brain' / 'arbeitsbereiche-bekannt.json'


def lade_register(names):
    """Namen, für die schon einmal ein Arbeitsbereich angelegt wurde. Gibt es die Datei noch nicht (erster Lauf),
    gelten alle bisherigen Namen als schon angelegt: was Sven vorher gelöscht hat, bleibt gelöscht."""
    try:
        return set(json.loads(REGISTER.read_text(encoding='utf-8')))
    except (OSError, ValueError, TypeError):
        return set(names)


def plane_arbeitsbereiche(connection, names, bekannt):
    """(pflegen, neu, geloescht): pflegen = Eintrag vorhanden oder ganz neuer Name, neu = noch nie angelegt,
    geloescht = früher angelegt, jetzt ohne Eintrag (Sven hat ihn gelöscht): wird nicht wieder angelegt."""
    vorhanden = {row[0] for row in connection.execute('select path from workspaces')}
    pflegen, neu, geloescht = [], [], []
    for name in names:
        if '/data/workspaces/' + name in vorhanden:
            pflegen.append(name)
        elif name in bekannt:
            geloescht.append(name)
        else:
            pflegen.append(name)
            neu.append(name)
    return pflegen, neu, geloescht


def ensure_workspace_rows(connection, names):
    """Trägt fehlende Arbeitsbereiche in die Datenbank ein (die Seitenleiste zeigt nur Einträge, nicht Ordner)."""
    first = connection.execute('select user_id from workspaces order by created_at limit 1').fetchone()
    if not first:
        return []
    added = []
    for name in names:
        path = '/data/workspaces/' + name
        if connection.execute('select 1 from workspaces where path=?', (path,)).fetchone():
            continue
        data = {'groups': [{'id': 'default', 'tabs': [{'id': 'files', 'type': 'files', 'label': 'Files', 'permanent': True}],
                            'activeTabId': 'files', 'tabHistory': ['files']}], 'activeGroupId': 'default',
                'layout': {'type': 'group', 'groupId': 'default'}, 'splitDirection': 'horizontal', 'splitRatio': 0.5, 'fileBrowserCwd': path}
        now = int(time.time())
        connection.execute('insert into workspaces (id, user_id, path, name, data, created_at, updated_at) values (?,?,?,?,?,?,?)',
                           (str(uuid.uuid4()), first[0], path, name, json.dumps(data), now, now))
        added.append(name)
    connection.commit()
    return added


def main():
    install_tools()
    for name in TOOL_FILES:
        if not (BRAIN / name).is_file():
            raise SystemExit('Missing in /data/brain: ' + name)
    agents = (SOURCE / 'direkt_agents.md').read_text(encoding='utf-8')
    # cptr liest AGENTS.md bei direkten Modell-Chats nicht ein: die allgemeinen Regeln gehören deshalb fest in den
    # Systemtext, die Projektdatei liest Bonsai zu Beginn selbst (Pfad des Arbeitsbereichs steht in seinem Kontext).
    prompt = (SOURCE / 'direkt_prompt.md').read_text(encoding='utf-8').rstrip('\n') + '\n\n' + agents.rstrip('\n') + PROJEKT_HINWEIS
    stamp = time.strftime('%Y%m%d')
    shutil.copy(DB, str(DB) + '.vor-direkt-' + stamp)
    connection = sqlite3.connect(DB, timeout=30)
    servers = [s for s in (load(connection, 'tool_servers') or []) if s.get('id') not in ('bonsai', 'heim')]
    servers.append(dict(id='heim', type='mcp_stdio', name='Heimnetz-Werkzeuge', command='/opt/cptr/bin/python',
        args=['/data/brain/bonsai_direkt_mcp.py'], env={}, cwd='/data/brain', enabled=True, auth_type='none'))
    models = load(connection, 'chat.models') or {}
    for model in MODELS:
        params = models.setdefault(model, {'is_active': True}).setdefault('params', {})
        models[model]['is_active'] = True
        params['system_prompt'] = prompt
        # Nur diese eingebauten Gruppen sind an (Aufgabenliste, frühere Chats, Memory, Meldungen, Zeitpläne, Hilfsagent, Browser).
        # Alles andere bleibt aus: Dateien und Terminal erledigen die einfachen heim_*-Werkzeuge, und Web (read_url) würde
        # die Freigabeliste von doku_lesen umgehen.
        params['builtin_tools'] = {group: group in BUILTIN_AN for group in BUILTIN_ALLE}
        params['request_params'] = dict(REQUEST_PARAMS)
        # cptr summarizes at 80k tokens by default; after that the Qwen template fails ('No user query found').
        params['compact_token_threshold'] = COMPACT_TOKENS
    for key, value in (('tool_servers', servers), ('chat.models', models)):
        connection.execute('update config set value=? where key=?', (json.dumps(value), key))
    connection.commit()
    toml = DATA / 'config.toml'
    shutil.copy(toml, str(toml) + '.vor-direkt-' + stamp)
    write_toml(toml, {'tool_servers': servers, 'chat.models': models})
    bekannt = lade_register(WORKSPACES)
    pflegen, neu_namen, geloescht = plane_arbeitsbereiche(connection, WORKSPACES, bekannt)
    for name, project_file in WORKSPACES.items():
        if name not in pflegen:
            continue   # von Sven gelöscht: Ordner und Regeln nicht wieder anlegen
        directory = DATA / 'workspaces' / name
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / 'AGENTS.md'
        if target.is_file() and not (directory / 'AGENTS.md.vor-direkt').exists():
            shutil.copy(target, directory / 'AGENTS.md.vor-direkt')
        text = agents
        if project_file and (SOURCE / project_file).is_file():
            text += '\n\n' + (SOURCE / project_file).read_text(encoding='utf-8')
        target.write_text(text, encoding='utf-8')
        # STATUS.md-Grundgerüst, damit "Neuer Chat mit Stand" bei neuen Projekten etwas zu lesen hat (nie überschreiben).
        if project_file and not (directory / 'STATUS.md').exists():
            (directory / 'STATUS.md').write_text(STATUS_START, encoding='utf-8')
        # PROJEKT.md nur anlegen, nie überschreiben: Bonsai trägt dort Gelerntes ein.
        if project_file and (SOURCE / project_file).is_file() and not (directory / 'PROJEKT.md').exists():
            (directory / 'PROJEKT.md').write_text((SOURCE / project_file).read_text(encoding='utf-8'), encoding='utf-8')
    added = ensure_workspace_rows(connection, neu_namen)
    REGISTER.parent.mkdir(parents=True, exist_ok=True)
    REGISTER.write_text(json.dumps(sorted(bekannt | set(pflegen))), encoding='utf-8')
    print('Configured: tool server heim, models', MODELS, ', workspaces', pflegen, ', neu in der Seitenleiste', added,
          ', gelöscht gelassen', geloescht)


if __name__ == '__main__':
    main()
