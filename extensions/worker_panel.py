"""Admin-only, content-free worker telemetry for Computer."""
import json
import math
import time
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse
from cptr.routers.admin import require_admin

router = APIRouter(prefix='/api/selfwebui')
ROOT = Path('/data/brain/live')
TERMINAL = {'fertig', 'erledigt', 'gescheitert', 'bonsai_beschaeftigt', 'bonsai_nicht_verfuegbar'}
PHASES = {'waiting', 'starting', 'prompt', 'generating', 'evaluating', 'tool'} | TERMINAL

def summary(raw, now):
    clean = {'phase': raw.get('phase') if raw.get('phase') in PHASES else 'unknown'}
    for key in ['started', 'updated', 'ended', 'tokens', 'step', 'tools', 'tps', 'last_tps']:
        value = raw.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
            clean[key] = value
    clean['stale'] = now - clean.get('updated', 0) > 15 and clean['phase'] not in TERMINAL
    return clean

@router.get('/worker/status')
async def status(request: Request):
    require_admin(request)
    now = time.time()
    jobs = []
    # No prompts, model outputs, host paths or credentials enter the response.
    for path in sorted(ROOT.glob('*/*.json'), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
        try:
            if path.stat().st_size > 32768:
                continue
            raw = json.loads(path.read_text())
            if now - raw.get('updated', 0) <= 86400:
                item = summary(raw, now)
                item['id'] = path.stem[:32]
                jobs.append(item)
        except (OSError, ValueError, TypeError):
            continue
    return JSONResponse({'jobs': jobs, 'scope': 'all-worker-jobs'}, headers={'Cache-Control': 'no-store'})

@router.get('/worker/panel.js')
async def script():
    return FileResponse('/opt/selfwebui/extensions/worker_panel.js', media_type='application/javascript', headers={'Cache-Control':'no-store'})
