import importlib.util
from pathlib import Path

root = Path(importlib.util.find_spec('cptr').origin).parent
path = root / 'frontend/build/browser-runtime.js'
source = path.read_text()
anchor = '  function report() {'
old = 'const url = new URL(value, base);'
if source.count(anchor) != 1 or source.count(old) != 1:
    raise SystemExit('Upstream runtime changed: review proxy patch before publishing')
block = Path('/opt/selfwebui/patches/dynamic-resources.js').read_text()
source = source.replace(anchor, block + anchor)
source = source.replace(old, 'const url = current.origin === location.origin ? new URL(`${current.pathname}${current.search}${current.hash}`, base) : new URL(value, base);')
path.write_text(source)
print('Patched', path)

chat_task = root / 'utils/chat_task.py'
text = chat_task.read_text()
old = 'chat_params.get("tool_approval_mode", "auto")'
if text.count(old) != 1:
    raise SystemExit('Upstream chat_task changed: review approval default')
chat_task.write_text(text.replace(old, 'chat_params.get("tool_approval_mode", "full")'))
print('Default tool approval: full')
