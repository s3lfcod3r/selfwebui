#!/usr/bin/env python3
"""Expose only the local Bonsai worker to the subscription-based planners."""
import json,sys,urllib.request,datetime,os
import threading,time,uuid,hashlib
from pathlib import Path
BASE=os.environ.get('BONSAI_WORKER_URL','http://OpenWebUI-Werkzeuge:8000').rstrip('/')
KEY=Path(os.environ.get('BONSAI_WORKER_KEY_FILE','/data/brain/worker.key')).read_text().strip()
SCHEMA={'type':'object','required':['auftrag'],'properties':{'browser_interaktiv':{'type':'boolean','description':'Nur true bei ausdrücklich beauftragten Webseiten-Änderungen.'},'auftrag':{'type':'string','description':'Eigenstaendiger Auftrag mit Ziel und erwarteten Ergebnissen. Veraenderungen nur mit Nutzerauftrag.'},'kontext':{'type':'string','description':'Relevanter Kontext, Pfade, Hosts und Einschraenkungen.'},'denken':{'type':'string','enum':['aus','wenig','mittel','viel']}}}
def send(x):
    print(json.dumps(x,ensure_ascii=False),flush=True)
def call(args):
    if not isinstance(args,dict) or not isinstance(args.get('auftrag'),str) or not args['auftrag'].strip(): raise ValueError('auftrag fehlt')
    job=uuid.uuid4().hex
    channel=os.environ.get('BONSAI_CHANNEL','selfwebui-worker')
    target=None
    if channel:
        directory=Path('/data/brain/live')/hashlib.sha256(channel.encode()).hexdigest()
        directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        target=directory/(job+'.json')
    def save(data):
        if target:
            temporary=target.with_suffix('.tmp')
            temporary.write_text(json.dumps(data))
            os.chmod(temporary,0o600)
            temporary.replace(target)
    started=time.time()
    latest={'job_id':job,'phase':'waiting','started':started,'updated':started}
    save(latest)
    stop=threading.Event()
    def poll():
        nonlocal latest
        while not stop.wait(1):
            try:
                req=urllib.request.Request(BASE+'/bonsai_status?job_id='+job,headers={'Authorization':'Bearer '+KEY})
                with urllib.request.urlopen(req,timeout=3) as r: state=json.load(r)
                latest={**latest,**state}
                save(latest)
            except (OSError,ValueError): pass
    thread=threading.Thread(target=poll,daemon=True)
    thread.start()
    req=urllib.request.Request(BASE+'/bonsai_auftrag',data=json.dumps({**args,'_telemetry_job':job}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+KEY},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=1600) as r: result=json.load(r)
    except Exception:
        stop.set();thread.join(timeout=5)
        save({**latest,'phase':'gescheitert','ended':time.time(),'updated':time.time()})
        raise
    finally:
        stop.set();thread.join(timeout=5)
    try:
        req=urllib.request.Request(BASE+'/bonsai_status?job_id='+job,headers={'Authorization':'Bearer '+KEY})
        with urllib.request.urlopen(req,timeout=3) as r: latest={**latest,**json.load(r)}
    except (OSError,ValueError): pass
    save({**latest,'phase':result.get('status','gescheitert'),'ended':time.time(),'updated':time.time()})
    with open('/data/brain/delegation.jsonl','a') as f:
        f.write(json.dumps({'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'auftrag':args['auftrag'],'result':result},ensure_ascii=False)+'\n')
    os.chmod('/data/brain/delegation.jsonl',0o600)
    return {'content':[{'type':'text','text':json.dumps(result,ensure_ascii=False)}],'isError':result.get('status') not in ('fertig','erledigt')}
for line in sys.stdin:
    try:
        msg=json.loads(line); method=msg.get('method'); ident=msg.get('id')
        if ident is None: continue
        if method=='initialize': result={'protocolVersion':msg.get('params',{}).get('protocolVersion','2024-11-05'),'capabilities':{'tools':{}},'serverInfo':{'name':'bonsai-arbeiter','version':'1.0.0'}}
        elif method=='ping': result={}
        elif method=='tools/list': result={'tools':[{'name':'bonsai_auftrag','description':'Delegiere Ausarbeitung, Recherche, Code und Ausfuehrung an Bonsai auf der RTX 2000E Ada. Nur ein Auftrag gleichzeitig. Pruefe den Bericht und das Werkzeugprotokoll. Bei Ausfall nicht selbst ausfuehren.','inputSchema':SCHEMA}]}
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
