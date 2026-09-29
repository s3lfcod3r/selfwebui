#!/usr/bin/env python3
"""Expose only the local Bonsai worker to the subscription-based planners."""
import json,sys,urllib.request,datetime,os
import threading,time,uuid,hashlib
from pathlib import Path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from loop_guard import LoopGuard,normalize,EXAMPLE
guard=LoopGuard()
BASE=os.environ.get('BONSAI_WORKER_URL','http://OpenWebUI-Werkzeuge:8000').rstrip('/')
KEY=Path(os.environ.get('BONSAI_WORKER_KEY_FILE','/data/brain/worker.key')).read_text().strip()
SCHEMA={'type':'object','required':['auftrag'],'properties':{'browser_interaktiv':{'type':'boolean','description':'Nur true bei ausdrücklich beauftragten Webseiten-Änderungen.'},'auftrag':{'type':'string','description':'Eigenstaendiger Auftrag mit Ziel und erwarteten Ergebnissen. Veraenderungen nur mit Nutzerauftrag.'},'kontext':{'type':'string','description':'Relevanter Kontext, Pfade, Hosts und Einschraenkungen.'},'denken':{'type':'string','enum':['aus','wenig','mittel','viel']}}}
def send(x):
    print(json.dumps(x,ensure_ascii=False),flush=True)
def request(path,data=None):
    req=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as response:return json.load(response)

def call(args):
    if not isinstance(args,dict):raise ValueError('Objekt erwartet')
    if args.get('aktion')=='werkzeuge':
        return {'content':[{'type':'text','text':json.dumps(request('/bonsai_tools'),ensure_ascii=False)}],'isError':False}
    if args.get('aktion')=='liste':
        records=request('/bonsai_jobs').get('jobs',[])
        items=[{k:r.get(k) for k in ['job_id','titel','projekt','phase','done','schritt','gesamt','started','updated']} for r in records]
        return {'content':[{'type':'text','text':json.dumps({'auftraege':items},ensure_ascii=False)}],'isError':False}
    job=args.get('job_id')
    existing=bool(job)
    if not job:
        if not isinstance(args.get('auftrag'),str) or not args['auftrag'].strip():raise ValueError('auftrag oder job_id erforderlich')
        job=uuid.uuid4().hex
        data={**args,'job_id':job}
        try:state=request('/bonsai_start',data)
        except OSError as error:
            if isinstance(error,urllib.error.HTTPError) and error.code in [400,401,403,413]:
                return {'content':[{'type':'text','text':json.dumps({'status':'abgelehnt','http_status':error.code,'hinweis':'Kein Auftrag gestartet. Berechtigung, Werkzeugnamen, exakte Argumente, Budget und doppelte Aufrufe prüfen; korrigierten Plan senden.'},ensure_ascii=False)}],'isError':True}
            # An ambiguous POST must never create a second execution.
            try:state=request('/bonsai_result?job_id='+job)
            except OSError:return {'content':[{'type':'text','text':json.dumps({'job_id':job,'status':'unbekannt','hinweis':'Startantwort unterbrochen. Mit dieser job_id erneut abfragen; Auftrag nicht neu starten.'},ensure_ascii=False)}],'isError':True}
        if state.get('status')=='bonsai_beschaeftigt':return {'content':[{'type':'text','text':json.dumps(state,ensure_ascii=False)}],'isError':True}
    if not isinstance(job,str) or len(job)!=32 or any(c not in '0123456789abcdef' for c in job):raise ValueError('Ungültige job_id')
    state=request('/bonsai_result?job_id='+job)
    deadline=time.monotonic()+15
    while existing and not state.get('done') and time.monotonic()<deadline:
        time.sleep(1)
        state=request('/bonsai_result?job_id='+job)
    if not state.get('done'):
        state['steps']=[{k:v for k,v in step.items() if k!='result'} for step in state.get('steps',[])]
        state['hinweis']='Auftrag läuft unabhängig weiter und speichert sein Ergebnis. Mit bonsai_auftrag und job_id denselben Auftrag erneut abfragen. Nicht erneut starten. Noch keinen nächsten abhängigen Auftrag ausführen.'
    return {'content':[{'type':'text','text':json.dumps(state,ensure_ascii=False)}], 'isError':bool(state.get('done') and state.get('phase') not in ['fertig','erledigt'])}

SCHEMA.pop('required',None)
SCHEMA['properties']['aktion']={'type':'string','enum':['liste','werkzeuge'],'description':'liste: gespeicherte Aufträge finden. werkzeuge: erlaubte Werkzeugnamen und Argumentschemas abrufen. Beides führt keine Arbeit aus.'}
SCHEMA['properties']['job_id']={'type':'string','description':'Gespeicherten Auftrag und Ergebnis mit dieser ID abfragen. Dabei keinen neuen Auftrag starten.'}
SCHEMA['properties'].update({
 'titel':{'type':'string','description':'Kurzer sichtbarer Titel dieses abgegrenzten Arbeiterauftrags; keine Geheimnisse.'},
 'projekt':{'type':'string','description':'Gemeinsamer Projektname für zusammengehörige Teilaufträge.'},
 'teilauftraege':{'type':'array','minItems':1,'maxItems':12,'description':'Optionaler fester Arbeitsplan. Schritte laufen nacheinander in frischen Arbeiterkontexten; Fehler stoppt den Plan. Für adaptive Prüfungen einzelne Aufträge mit titel/projekt senden.','items':{'type':'object','required':['titel','auftrag'],'properties':{'titel':{'type':'string'},'auftrag':{'type':'string'}}}}
})
CALL_SCHEMA={'type':'array','maxItems':40,'description':'Feste Aufrufe einmal in Reihenfolge ausführen. Exakte Argumente vom Planer. Ohne Liste nur RTX-Analyse, keine Werkzeuge. Vorher aktion=werkzeuge für Schemas nutzen.','items':{'type':'object','required':['werkzeug','argumente'],'additionalProperties':False,'properties':{'werkzeug':{'type':'string'},'argumente':{'type':'object'}}}}
SCHEMA['properties']['erlaubte_aufrufe']=CALL_SCHEMA
SCHEMA['properties']['max_werkzeugaufrufe']={'type':'integer','minimum':1,'maximum':40,'default':8}
SCHEMA['properties']['teilauftraege']['items']['properties'].update({'erlaubte_aufrufe':CALL_SCHEMA,'max_werkzeugaufrufe':SCHEMA['properties']['max_werkzeugaufrufe']})
for line in sys.stdin:
    try:
        msg=json.loads(line); method=msg.get('method'); ident=msg.get('id')
        if ident is None: continue
        if method=='initialize': result={'protocolVersion':msg.get('params',{}).get('protocolVersion','2024-11-05'),'capabilities':{'tools':{}},'serverInfo':{'name':'bonsai-arbeiter','version':'1.0.0'}}
        elif method=='ping': result={}
        elif method=='tools/list': result={'tools':[{'name':'bonsai_auftrag','description':'Fester Ausführungsplan: erlaubte_aufrufe werden einmal ausgeführt, danach analysiert RTX ohne Werkzeugschleife. Ohne erlaubte_aufrufe nur Analyse des Kontexts. Werkzeugschemas mit aktion=werkzeuge abrufen. Startet einen dauerhaft gespeicherten Auftrag und liefert sofort seine job_id. Solange done=false ist, mit job_id wiederholt abfragen; nicht neu starten und nicht als erledigt melden. Nur ein Auftrag gleichzeitig. Pruefe den Bericht und das Werkzeugprotokoll. Bei Ausfall nicht selbst ausfuehren.','inputSchema':SCHEMA}]}
        elif method=='tools/call':
            p=msg.get('params',{})
            if p.get('name')!='bonsai_auftrag': raise ValueError('Unbekanntes Werkzeug')
            gargs=normalize(p.get('arguments',{}))
            hint=guard.before(gargs)
            if hint is not None:
                result={'content':[{'type':'text','text':hint}],'isError':True}
                guard.after(gargs,hint,True)
            else:
                try:result=call(gargs)
                except Exception as e:
                    result={'content':[{'type':'text','text':'Bonsai-Auftrag fehlgeschlagen: %s: %s. %s'%(type(e).__name__,e,EXAMPLE)}],'isError':True}
                text=result['content'][0]['text']
                extra=guard.after(gargs,text,bool(result.get('isError')))
                if extra:result['content'][0]['text']=text+'\n'+extra
        else:
            send({'jsonrpc':'2.0','id':ident,'error':{'code':-32601,'message':'Method not found'}}); continue
        send({'jsonrpc':'2.0','id':ident,'result':result})
    except Exception as e:
        if 'ident' in locals() and ident is not None:
            send({'jsonrpc':'2.0','id':ident,'result':{'content':[{'type':'text','text':f'Bonsai-Auftrag fehlgeschlagen: {type(e).__name__}: {e}'}],'isError':True}})
