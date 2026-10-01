from pathlib import Path
import cptr
root=Path(cptr.__file__).parent
p=root/'app.py';s=p.read_text();anchor='# Frontend (unchanged)'
if '# selfwebui extensions' not in s:
    if s.count(anchor)!=1:raise SystemExit('Upstream app changed; review extension mount')
    block='''# selfwebui extensions
import sys as _selfwebui_sys
_selfwebui_sys.path.insert(0, '/opt/selfwebui/extensions')
from worker_panel import router as _worker_panel_router
from direct_browser import router as _direct_browser_router, worker_router as _worker_browser_router
from fehlerchats import router as _fehlerchats_router
app.include_router(_worker_panel_router)
app.include_router(_direct_browser_router)
app.include_router(_worker_browser_router)
app.include_router(_fehlerchats_router)

'''
    p.write_text(s.replace(anchor,block+anchor))
p=root/'frontend/build/index.html';s=p.read_text()
if '/api/selfwebui/worker/panel.js' not in s:
    if '</body>' not in s:raise SystemExit('Upstream HTML changed')
    p.write_text(s.replace('</body>','<script defer src="/api/selfwebui/worker/panel.js"></script><script defer src="/api/selfwebui/browser/panel.js"></script></body>'))
print('Installed worker telemetry and direct-browser panel')
