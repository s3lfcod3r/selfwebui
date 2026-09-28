"""Opt-in installer for the existing OpenWebUI-Werkzeuge service (run on its host)."""
import argparse,json,shutil,time
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--app-dir',type=Path,required=True)
parser.add_argument('--config-dir',type=Path,required=True)
parser.add_argument('--computer-url',required=True)
args=parser.parse_args()
source=args.app_dir/'browser_tools.py'
text=source.read_text()
marker='    import direct_browser_client\n'
if marker not in text:
    anchor="    with _condition:\n        wait_for_release()"
    if text.count(anchor)!=1:raise SystemExit('Unknown worker version; nothing changed')
    shutil.copy2(source,source.with_name('browser_tools.py.backup-'+str(int(time.time()))))
    text=text.replace(anchor,marker+"    if direct_browser_client.enabled():\n        return direct_browser_client.call(action,data,getattr(_local,'interactive',False))\n"+anchor)
    source.write_text(text)
shutil.copy2(Path(__file__).with_name('direct_browser_client.py'),args.app_dir/'direct_browser_client.py')
config=args.config_dir/'direct-browser.json'
if config.exists():shutil.copy2(config,config.with_suffix('.backup-'+str(int(time.time()))))
config.write_text(json.dumps({'url':args.computer_url}))
config.chmod(0o600)
print('Installed. Set configuration ownership to the worker UID, then restart the worker.')
