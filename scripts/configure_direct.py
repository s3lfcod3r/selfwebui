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
from pathlib import Path

SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/opt/selfwebui/integrations')
DATA = Path(os.environ.get('CPTR_DATA_DIR', '/data'))
DB = DATA / 'app.db'
BRAIN = DATA / 'brain'
# Arbeitsbereiche mit Bonsai-Regeln; optional eine Projektdatei aus integrations/ (wird angehängt)
WORKSPACES = {'RTX2000': None, 'SelfWG': 'projekt_SelfWG.md', 'SelfDashboard': 'projekt_SelfDashboard.md', 'SelfStorm': 'projekt_SelfStorm.md', 'SelfStream': 'projekt_SelfStream.md', 'SelfStreamDesktop': 'projekt_SelfStreamDesktop.md',
              'SelfStore': 'projekt_SelfStore.md', 'SelfMailer': 'projekt_SelfMailer.md', 'SelfRemote': 'projekt_SelfRemote.md', 'SelfAuthenticator': 'projekt_SelfAuthenticator.md', 'SelfArchiver': 'projekt_SelfArchiver.md', 'SelfFon': 'projekt_SelfFon.md', 'SelfMediaHub': 'projekt_SelfMediaHub.md', 'SelfPoolTracker': 'projekt_SelfPoolTracker.md', 'SelfScreen': 'projekt_SelfScreen.md', 'SelfThreatMap': 'projekt_SelfThreatMap.md', 'SelfGuard': 'projekt_SelfGuard.md', 'SelfCoder': 'projekt_SelfCoder.md'}
MODELS = ['bonsai-2-27b', 'RTX2000/bonsai-2-27b']
# Tool-heavy work: lower temperature than the 1.0 of the model card; other values from the card.
PROJEKT_HINWEIS = (
    "\n\nPROJEKTREGELN\n"
    "Zu Beginn jeder Aufgabe in einem Projekt zuerst die Projektdatei deines Arbeitsbereichs lesen, falls sie existiert: "
    "cat /media/Safe-Storage/appdata/werkstatt/computer/data/workspaces/<Name>/PROJEKT.md. Der Arbeitsbereich <Name> steht in deinem Kontext "
    "(Pfad /data/workspaces/<Name>). Die Datei nennt Klon, Version, Schlüssel-Referenz, bekannte Punkte und Gelerntes. Danach arbeiten.\n")
COMPACT_TOKENS = 180000  # the model server has 262144 tokens of context
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
        params['builtin_tools'] = {group: False for group in (params.get('builtin_tools') or {})}
        params['request_params'] = dict(REQUEST_PARAMS)
        # cptr summarizes at 80k tokens by default; after that the Qwen template fails ('No user query found').
        params['compact_token_threshold'] = COMPACT_TOKENS
    for key, value in (('tool_servers', servers), ('chat.models', models)):
        connection.execute('update config set value=? where key=?', (json.dumps(value), key))
    connection.commit()
    toml = DATA / 'config.toml'
    shutil.copy(toml, str(toml) + '.vor-direkt-' + stamp)
    write_toml(toml, {'tool_servers': servers, 'chat.models': models})
    for name, project_file in WORKSPACES.items():
        directory = DATA / 'workspaces' / name
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / 'AGENTS.md'
        if target.is_file() and not (directory / 'AGENTS.md.vor-direkt').exists():
            shutil.copy(target, directory / 'AGENTS.md.vor-direkt')
        text = agents
        if project_file and (SOURCE / project_file).is_file():
            text += '\n\n' + (SOURCE / project_file).read_text(encoding='utf-8')
        target.write_text(text, encoding='utf-8')
        # PROJEKT.md nur anlegen, nie überschreiben: Bonsai trägt dort Gelerntes ein.
        if project_file and (SOURCE / project_file).is_file() and not (directory / 'PROJEKT.md').exists():
            (directory / 'PROJEKT.md').write_text((SOURCE / project_file).read_text(encoding='utf-8'), encoding='utf-8')
    print('Configured: tool server heim, models', MODELS, ', workspaces', list(WORKSPACES))


if __name__ == '__main__':
    main()
