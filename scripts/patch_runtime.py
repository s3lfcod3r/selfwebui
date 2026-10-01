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

# Context compaction keeps only the newest ~40 % of the history. In long tool-using runs that tail has no user
# message left, and the Qwen chat template then fails with 'No user query found in messages.' (the run dies).
# Fix: if the kept part has no user turn, put a copy of the last user message in front of it (task stays visible).
text = chat_task.read_text()
call_old = 'keep_zone = messages[split_idx:]'
func_anchor = 'def _summary_checkpoint_message_id('
if text.count(call_old) != 1 or text.count(func_anchor) != 1:
    raise SystemExit('Upstream compaction changed: review the user-turn fix')
helper = '''def _ensure_user_turn(keep_zone: list[dict], drop_zone: list[dict]) -> list[dict]:
    """Qwen templates need a user message; keep a copy of the last one when compaction dropped them all."""
    if any(m.get("role") == "user" for m in keep_zone):
        return keep_zone
    last_user = next((m for m in reversed(drop_zone) if m.get("role") == "user"), None)
    if last_user is None:
        last_user = {"role": "user", "content": "Fahre mit der Aufgabe fort."}
    return [{k: v for k, v in last_user.items() if k != "id"}] + list(keep_zone)


'''
text = text.replace(func_anchor, helper + func_anchor)
text = text.replace(call_old, call_old + '\n                keep_zone = _ensure_user_turn(keep_zone, drop_zone)')
chat_task.write_text(text)
print('Compaction keeps a user turn')
