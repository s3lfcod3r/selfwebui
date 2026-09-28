"""A bounded command relay to an explicitly connected, visible HTML browser."""
import asyncio
import hmac
import time
import uuid
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from cptr.routers.admin import require_admin

router=APIRouter(prefix='/api/selfwebui/browser')
worker_router=APIRouter(prefix='/v1/selfwebui')
lease=None
pending={}
lock=asyncio.Lock()

def admin(request):
    auth=require_admin(request)
    origin=request.headers.get('origin')
    if origin and origin.rstrip('/')!=str(request.base_url).rstrip('/'):
        raise HTTPException(403,'Foreign origin')
    return str(auth.user_id)

def check(request, token):
    user=admin(request)
    if not lease or lease['user']!=user or not hmac.compare_digest(lease['token'],token):
        raise HTTPException(409,'Browser is not connected to this controller')

@router.post('/connect')
async def connect(request:Request):
    global lease
    user=admin(request)
    if lease and time.monotonic()-lease['seen']<10:
        raise HTTPException(409,'A browser is already connected; disconnect it first')
    for item in pending.values():
        if not item['future'].done():item['future'].set_result({'fehler':'Vorherige Browser-Verbindung abgelaufen.'})
    lease={'user':user,'token':uuid.uuid4().hex,'seen':time.monotonic()}
    return {'token':lease['token']}

@router.post('/poll')
async def poll(request:Request):
    data=await request.json();check(request,data.get('token',''))
    lease['seen']=time.monotonic()
    command=next((p for p in pending.values() if not p['sent'] and p['token']==lease['token'] and not p['future'].done()),None)
    if command:
        command['sent']=True
        return {'id':command['id'],'action':command['action'],'data':command['data']}
    return {}

@router.post('/result')
async def result(request:Request):
    if len(await request.body())>60000:raise HTTPException(413)
    data=await request.json();check(request,data.get('token',''))
    item=pending.get(data.get('id'))
    if item and item['token']==lease['token'] and not item['future'].done():item['future'].set_result(data.get('result',{}))
    return {'ok':True}

@router.post('/disconnect')
async def disconnect(request:Request):
    global lease
    data=await request.json();check(request,data.get('token',''))
    lease=None
    for item in pending.values():
        if not item['future'].done():item['future'].set_result({'fehler':'Browser wurde manuell übernommen.'})
    return {'ok':True}

@worker_router.post('/browser/command')
async def command(request:Request):
    key=Path('/data/brain/worker.key').read_text().strip()
    if not hmac.compare_digest(request.headers.get('authorization',''),'Bearer '+key):raise HTTPException(403)
    if len(await request.body())>20000:raise HTTPException(413)
    data=await request.json();action=data.get('action')
    if action not in {'open','read','scroll','click','fill','screenshot'}:raise HTTPException(400)
    if action in {'click','fill'} and data.get('interactive') is not True:
        return {'fehler':'Klicken/Eingeben ist für diesen Auftrag nicht freigegeben.'}
    if action=='screenshot':
        return {'fehler':'Die direkte HTML-Ansicht liefert DOM/Text. Ein Bild dieser lokalen Ansicht kann nur der Benutzer aufnehmen; kein Screenshot aus einer anderen Sitzung wird vorgetäuscht.'}
    async with lock:
        if not lease or time.monotonic()-lease['seen']>10:
            return {'fehler':'Direkten Arbeiter-Browser in Computer öffnen und mit „Arbeiter verbinden“ freigeben. Kein Wechsel in eine versteckte Sitzung.'}
        ident=uuid.uuid4().hex;future=asyncio.get_running_loop().create_future()
        pending[ident]={'id':ident,'action':action,'data':data,'future':future,'sent':False,'token':lease['token']}
        try:return JSONResponse(await asyncio.wait_for(future,35))
        except asyncio.TimeoutError:return {'fehler':'Sichtbarer Browser antwortet nicht; Tab geöffnet lassen und erneut verbinden.'}
        finally:pending.pop(ident,None)

@worker_router.get('/test-page',response_class=HTMLResponse)
async def fixture():
    return '<!doctype html><title>Browser-Verbindungstest</title><h1>Direkter Arbeiter-Browser</h1><p id="value">Test bereit</p><button onclick="document.getElementById(\'value\').textContent=\'Klick erfolgreich\'">Testknopf</button>'

@router.get('/panel.js')
async def script():
    return FileResponse('/opt/selfwebui/extensions/direct_browser.js',media_type='application/javascript',headers={'Cache-Control':'no-store'})
