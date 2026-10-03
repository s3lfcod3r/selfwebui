"""Admin-only worker telemetry and explicitly requested task reports."""
import asyncio
import urllib.error
import urllib.request
import os
import json
import math
import time
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from cptr.routers.admin import require_admin

router = APIRouter(prefix='/api/selfwebui')
ROOT = Path('/data/brain/live')
TERMINAL = {'fertig', 'erledigt', 'teilweise', 'gescheitert', 'bonsai_beschaeftigt', 'bonsai_nicht_verfuegbar'}
PHASES = {'waiting', 'starting', 'prompt', 'generating', 'evaluating', 'tool'} | TERMINAL

def summary(raw, now):
    clean = {'phase': raw.get('phase') if raw.get('phase') in PHASES else 'unknown'}
    for key in ['started', 'updated', 'ended', 'tokens', 'step', 'tools', 'tps', 'last_tps']:
        value = raw.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
            clean[key] = value
    for key in ['titel','projekt','plan']:
        if isinstance(raw.get(key),str):clean[key]=raw[key][:100]
    for key in ['schritt','gesamt']:
        if isinstance(raw.get(key),int) and 1<=raw[key]<=12:clean[key]=raw[key]
    clean['stale'] = now - clean.get('updated', 0) > 15 and clean['phase'] not in TERMINAL
    return clean

_bonsai_cache = {'zeit': 0.0, 'zustand': 'unbekannt'}

def bonsai_zustand(now=None):
    """Health des Modellservers: bereit, laedt (Modell wird geladen) oder aus. Kurz zwischengespeichert."""
    now = time.monotonic() if now is None else now
    if now - _bonsai_cache['zeit'] < 5:
        return _bonsai_cache['zustand']
    url = os.environ.get('BONSAI_URL', 'http://192.168.1.103:8085').rstrip('/') + '/health'
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            zustand = 'bereit' if json.load(response).get('status') == 'ok' else 'laedt'
    except urllib.error.HTTPError as error:
        zustand = 'laedt' if error.code == 503 else 'aus'
    except (OSError, ValueError):
        zustand = 'aus'
    _bonsai_cache.update(zeit=now, zustand=zustand)
    return zustand

_aktiv_cache = {'zeit': 0.0, 'wert': None}

def bonsai_aktivitaet(now=None):
    """Was der Modellserver gerade tut: liest den Chat (Prompt-Verarbeitung) oder schreibt. None, wenn er frei ist."""
    now = time.monotonic() if now is None else now
    if now - _aktiv_cache['zeit'] < 1:
        return _aktiv_cache['wert']
    url = os.environ.get('BONSAI_URL', 'http://192.168.1.103:8085').rstrip('/') + '/slots'
    wert = None
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            for slot in json.load(response):
                if not slot.get('is_processing'):
                    continue
                gesamt, fertig = int(slot.get('n_prompt_tokens') or 0), int(slot.get('n_prompt_tokens_processed') or 0)
                geschrieben = max([int(t.get('n_decoded') or 0) for t in slot.get('next_token') or []] or [0])
                wert = {'phase': 'schreibt' if geschrieben else 'liest', 'gelesen': fertig, 'gesamt': gesamt, 'geschrieben': geschrieben}
                break
    except (OSError, ValueError, TypeError):
        wert = None
    _aktiv_cache.update(zeit=now, wert=wert)
    return wert

def remote_jobs():
    key=Path('/data/brain/worker.key').read_text().strip()
    base=os.environ.get('BONSAI_WORKER_URL','http://OpenWebUI-Werkzeuge:8000').rstrip('/')
    req=urllib.request.Request(base+'/bonsai_jobs',headers={'Authorization':'Bearer '+key})
    with urllib.request.urlopen(req,timeout=2) as response:return json.load(response).get('jobs',[])

@router.get('/worker/status')
async def status(request: Request):
    require_admin(request)
    now = time.time()
    jobs = []
    # Telemetry is allowlisted; separate task reports are visible to administrators only.
    for path in sorted(ROOT.glob('*/*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
        try:
            if path.stat().st_size > 32768:
                continue
            raw = json.loads(path.read_text())
            if now - raw.get('updated', 0) <= 86400:
                item = summary(raw, now)
                item['id'] = path.stem[:32]
                report=path.with_suffix('.result')
                if report.is_file() and report.stat().st_size<200000:
                    item['bericht']=str(json.loads(report.read_text()).get('bericht',''))[:16000]
                jobs.append(item)
        except (OSError, ValueError, TypeError):
            continue
    try:
        plans=await asyncio.to_thread(remote_jobs)
        for plan in plans:
            for raw in plan.get('steps',[]):
                item=summary(raw,now);item['id']=raw['job_id']
                if not plan.get('done') and raw is plan.get('steps',[])[-1]:item['stale']=False
                result=raw.get('result')
                if result:item['bericht']=str(result.get('bericht',result.get('hinweis','')))[:16000]
                elif plan.get('done') and plan.get('error'):
                    item.update(phase='gescheitert',bericht=plan['error'],stale=False)
                jobs=[j for j in jobs if j['id']!=item['id']];jobs.append(item)
        jobs.sort(key=lambda j:j.get('started',0),reverse=True)
    except (OSError,ValueError):
        return JSONResponse({'error':'worker_unreachable'},status_code=503,headers={'Cache-Control':'no-store'})
    zustand = await asyncio.to_thread(bonsai_zustand)
    aktivitaet = await asyncio.to_thread(bonsai_aktivitaet)
    return JSONResponse({'jobs': jobs[:30], 'scope': 'all-worker-jobs', 'bonsai': zustand, 'aktivitaet': aktivitaet}, headers={'Cache-Control': 'no-store'})

@router.get('/worker/panel.js')
async def script():
    # Spalte und Auswahl-Knöpfe (auswahl.js) laufen als ein Skript
    base = Path('/opt/selfwebui/extensions')
    text = chr(10).join((base / name).read_text(encoding='utf-8') for name in ('worker_panel.js', 'auswahl.js', 'chatstatus.js', 'meldung.js', 'loeschschutz.js'))
    return Response(text, media_type='application/javascript', headers={'Cache-Control':'no-store'})
