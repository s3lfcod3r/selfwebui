"""Compatibility endpoints for the existing SelfDashboard widgets."""
import json,os,threading,time,urllib.request
from pathlib import Path
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import tokens,projects
LIVE=Path(os.environ.get('WORKER_LIVE','/worker-live'))

def project_status():
    result=projects.status()
    latest=None
    for p in LIVE.glob('*/*.json'):
        try:
            if p.stat().st_size>32768:continue
            value=json.loads(p.read_text())
            if isinstance(value,dict) and (latest is None or value.get('updated',0)>latest.get('updated',0)):latest=value
        except (OSError,ValueError):continue
    keyfile=Path(os.environ.get('WORKER_KEY_FILE','/run/worker.key'))
    if keyfile.is_file():
        try:
            base=os.environ.get('BONSAI_WORKER_URL','http://OpenWebUI-Werkzeuge:8000')
            req=urllib.request.Request(base+'/bonsai_jobs',headers={'Authorization':'Bearer '+keyfile.read_text().strip()})
            with urllib.request.urlopen(req,timeout=3) as response:plans=json.load(response).get('jobs',[])
            for plan in plans:
                for step in plan.get('steps',[]):
                    value=dict(step)
                    if plan.get('done') and plan.get('error'):value.update(phase='gescheitert',updated=plan.get('updated',0))
                    if latest is None or value.get('updated',0)>latest.get('updated',0):latest=value
        except (OSError,ValueError):pass
    if latest:
        phase=latest.get('phase');updated=latest.get('updated',0)
        terminal=phase in ['fertig','erledigt']
        stale=time.time()-updated>30 and not terminal
        state='fertig' if terminal else ('wartet' if stale or phase in ['gescheitert','bonsai_beschaeftigt','bonsai_nicht_verfuegbar'] else 'in Arbeit')
        info=('Letzter Auftrag abgeschlossen' if terminal else 'Kein aktuelles Aktivitätssignal' if stale else 'Arbeiterstatus: '+str(phase))
        result['projekte'].insert(0,{'name':'SelfWebUI · RTX-Arbeiter','geaendert':datetime.fromtimestamp(updated,timezone.utc).isoformat(),
            'fragen':[], 'aufgaben':[{'name':'Arbeiterauftrag','zustand':state,'text':info}]})
    result['quelle']='SelfWebUI: STATUS.md und RTX-Arbeitertelemetrie'
    return result

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            path=self.path.split('?')[0].rstrip('/')
            if path=='/tokens':data=tokens.antwort();data['quelle']='RTX-Modellserver; Cloud-Abos nicht enthalten'
            elif path=='/status':data=project_status()
            elif path=='/health':data={'ok':True}
            else:self.send_error(404);return
            body=json.dumps(data,ensure_ascii=False).encode()
            self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        except Exception:
            self.send_error(503,'Dashboard data unavailable')
    def log_message(self,*args):pass

if __name__=='__main__':
    tokens.lade()
    threading.Thread(target=tokens.schleife,daemon=True).start()
    ThreadingHTTPServer(('0.0.0.0',8098),Handler).serve_forever()
