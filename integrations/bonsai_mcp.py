#!/usr/bin/env python3
"""Expose only the local Bonsai worker to the subscription-based planners."""
import json,sys,urllib.request,datetime,os
import threading,time,uuid,hashlib
from pathlib import Path
BASE=os.environ.get('BONSAI_WORKER_URL','http://OpenWebUI-Werkzeuge:8000').rstrip('/')
KEY=Path(os.environ.get('BONSAI_WORKER_KEY_FILE','/data/brain/worker.key')).read_text().strip()
SCHEMA={'type':'object','required':['auftrag'],'properties':{'browser_interaktiv':{'type':'boolean','description':'Nur true bei ausdrÃ¼cklich beauftragten Webseiten-Ã„nderungen.'},'auftrag':{'type':'string','description':'Eigenstaendiger Auftrag mit Ziel und erwarteten Ergebnissen. Veraenderungen nur mit Nutzerauftrag.'},'kontext':{'type':'string','description':'Relevanter Kontext, Pfade, Hosts und Einschraenkungen.'},'denken':{'type':'string','enum':['aus','wenig','mittel','viel']}}}
def send(x):
    print(json.dumps(x,ensure_ascii=False),flush=True)
def request(path,data=None):
    req=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)

def call(args):
    if not isinstance(args,dict):raise ValueError('Objekt erwartet')
    job=args.get('job_id')
    existing=bool(job)
    if not job:
        if not isinstance(args.get('auftrag'),str) or not args['auftrag'].strip():raise ValueError('auftrag oder job_id erforderlich')
        job=uuid.uuid4().hex
        data={**args,'job_id':job}
        try:state=request('/bonsai_start',data)
        except OSError:
            # An ambiguous POST must never create a second execution.
            try:state=request('/bonsai_result?job_id='+job)
            except OSError:return {'content':[{'type':'text','text':json.dumps({'job_id':job,'status':'unbekannt','hinweis':'Startantwort unterbrochen. Mit dieser job_id erneut abfragen; Auftrag nicht neu starten.'},ensure_ascii=False)}],'isError':True}
        if state.get('status')=='bonsai_beschaeftigt':return {'content':[{'type':'text','text':json.dumps(state,ensure_ascii=False)}],'isError':True}
    if not isinstance(job,str) or len(job)!=32 or any(c not in '0123456789abcdef' for c in job):raise ValueError('UngÃ¼ltige job_id')
    state=request('/bonsai_result?job_id='+job)
    deadline=time.monotonic()+15
    while existing and not state.get('done') and time.monotonic()<deadline:
        time.sleep(1)
        state=request('/bonsai_result?job_id='+job)
    if not state.get('done'):
        state['steps']=[{k:v for k,v in step.items() if k!='result'} for step in state.get('steps',[])]
        state['hinweis']='Auftrag lÃ¤uft unabhÃ¤ngig weiter und speichert sein Ergebnis. Mit bonsai_auftrag und job_id denselben Auftrag erneut abfragen. Nicht erneut starten. Noch keinen nÃ¤chsten abhÃ¤ngigen Auftrag ausfÃ¼hren.'
    return {'content':[{'type':'text','text':json.dumps(state,ensure_ascii=False)}], 'isError':bool(state.get('done') and state.get('phase') not in ['fertig','erledigt'])}

SCHEMA.pop('required',None)
SCHEMA['properties']['job_id']={'type':'string','description':'Gespeicherten Auftrag und Ergebnis mit dieser ID abfragen. Dabei keinen neuen Auftrag starten.'}
SCHEMA['properties'].update({
 'titel':{'type':'string','description':'Kurzer sichtbarer Titel dieses abgegrenzten Arbeiterauftrags; keine Geheimnisse.'},
 'projekt':{'type':'string','description':'Gemeinsamer Projektname fÃ¼r zusammengehÃ¶rige TeilauftrÃ¤ge.'},
 'teilauftraege':{'type':'array','minItems':1,'maxItems':12,'description':'Optionaler fester Arbeitsplan. Schritte laufen nacheinander in frischen Arbeiterkontexten; Fehler stoppt den Plan. FÃ¼r adaptive PrÃ¼fungen einzelne AuftrÃ¤ge mit titel/projekt senden.','items':{'type':'object','required':['titel','auftrag'],'properties':{'titel':{'type':'string'},'auftrag':{'type':'string'}}}}
})
for line in sys.stdin:
    try:
        msg=json.loads(line); method=msg.get('method'); ident=msg.get('id')
        if ident is None: continue
        if method=='initialize': result={'protocolVersion':msg.get('params',{}).get('protocolVersion','2024-11-05'),'capabilities':{'tools':{}},'serverInfo':{'name':'bonsai-arbeiter','version':'1.0.0'}}
        elif method=='ping': result={}
        elif method=='tools/list': result={'tools':[{'name':'bonsai_auftrag','description':'Delegiere Ausarbeitung, Recherche, Code und Ausfuehrung an Bonsai auf der RTX 2000E Ada. Startet einen dauerhaft gespeicherten Auftrag und liefert sofort seine job_id. Solange done=false ist, mit job_id wiederholt abfragen; nicht neu starten und nicht als erledigt melden. Nur ein Auftrag gleichzeitig. Pruefe den Bericht und das Werkzeugprotokoll. Bei Ausfall nicht selbst ausfuehren.','inputSchema':SCHEMA}]}
        elif method=='tools/call':
            p=msg.get('params',{})
            if p.get('name')!='bonsai_auftrag': raise ValueError('Unbekanntes Werkzeug')
            result=call(p.get('arguments',{}))
        else:
            send({'jsonrpc':'2.0','id':ident,'error':{'code':-32601,'message':'Method not found'}}); continue
        send({'jsonrpc':'2.0','id':ident,'result':result})
    except Exception as e:
        if 'ident' in locals() and ident is not None:
            send({'jsonrpc':'2.0','id':ident,'result':{'content':[{'type':'text','text':f'Bonsai-Auftrag fehlgeschlagen: {type(e).__name__}: {e}'}],'isError':True}})
