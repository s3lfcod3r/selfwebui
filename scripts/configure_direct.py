"""Opt-in: run Bonsai alone (no cloud planner) in the RTX2000 workspace.

Usage inside the Computer container: python configure_direct.py [integrations-dir]
Backs up app.db first. Restart the container afterwards (tool servers are cached).
"""
import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/opt/selfwebui/integrations')
DB = Path('/data/app.db')
BRAIN = Path('/data/brain')
WORKSPACE = Path('/data/workspaces/RTX2000')
MODELS = ['bonsai-2-27b', 'RTX2000/bonsai-2-27b']
# Tool-heavy work: lower temperature than the 1.0 of the model card; other values from the card.
REQUEST_PARAMS = {'max_tokens': 16384, 'temperature': 0.7, 'top_p': 0.95, 'top_k': 20, 'min_p': 0.05}


def load(connection, key):
    row = connection.execute('select value from config where key=?', (key,)).fetchone()
    return json.loads(row[0]) if row and isinstance(row[0], str) else (row[0] if row else None)


def main():
    for name in ('bonsai_direkt_mcp.py', 'loop_guard.py', 'diagnose.py'):
        if not (BRAIN / name).is_file():
            raise SystemExit('Missing in /data/brain: ' + name)
    prompt = (SOURCE / 'direkt_prompt.md').read_text(encoding='utf-8')
    agents = (SOURCE / 'direkt_agents.md').read_text(encoding='utf-8')
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
    for key, value in (('tool_servers', servers), ('chat.models', models)):
        connection.execute('update config set value=? where key=?', (json.dumps(value), key))
    connection.commit()
    target = WORKSPACE / 'AGENTS.md'
    if target.is_file() and not (WORKSPACE / 'AGENTS.md.vor-direkt').exists():
        shutil.copy(target, WORKSPACE / 'AGENTS.md.vor-direkt')
    target.write_text(agents, encoding='utf-8')
    print('Configured: tool server heim, models', MODELS, ', workspace AGENTS.md')


if __name__ == '__main__':
    main()
