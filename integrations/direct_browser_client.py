"""Worker-side relay; opt in with /geheim/direct-browser.json."""
import json
import os
import urllib.request
from pathlib import Path

CONFIG=Path('/geheim/direct-browser.json')
def enabled():
    return CONFIG.is_file()

def call(action,data,interactive=False):
    config=json.loads(CONFIG.read_text())
    key=Path(os.environ.get('SCHLUESSEL_DATEI','/geheim/schluessel.txt')).read_text().strip()
    request=urllib.request.Request(config['url'].rstrip('/')+'/v1/selfwebui/browser/command',
        data=json.dumps({**data,'action':action,'interactive':interactive is True}).encode(),
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=40) as response:return json.load(response)
    except (OSError,ValueError):
        return {'fehler':'Direkte Browser-Verbindung nicht erreichbar. Computer öffnen und Arbeiter-Browser verbinden.'}
