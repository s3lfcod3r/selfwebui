"""Admin-only worker telemetry and explicitly requested task reports."""
import asyncio
import urllib.request
import os
import json
import math
import time
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
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
    return JSONResponse({'jobs': jobs[:30], 'scope': 'all-worker-jobs'}, headers={'Cache-Control': 'no-store'})

@router.get('/worker/panel.js')
async def script():
    return FileResponse('/opt/selfwebui/extensions/worker_panel.js', media_type='application/javascript', headers={'Cache-Control':'no-store'})
