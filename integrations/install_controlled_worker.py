"""Install the fixed-call worker into an existing tools container; restart idle worker."""
import argparse,shutil,time
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--app-dir',type=Path,required=True);args=parser.parse_args()
p=args.app_dir/'werkzeuge.py';s=p.read_text(encoding='utf-8')
if 'import controlled_worker as bonsai_arbeiter' not in s:
    if s.count('import bonsai_arbeiter\n')!=1:raise SystemExit('Unknown worker import')
    s=s.replace('import bonsai_arbeiter\n','import controlled_worker as bonsai_arbeiter\n')
anchor='durable_jobs.telemetry_reader = bonsai_arbeiter.telemetry.status\n'
validation='durable_jobs.request_validator = lambda data: bonsai_arbeiter.validate(data, ARBEITER_WERKZEUGE)\n'
if validation not in s:
    if anchor not in s:raise SystemExit('Install durable endpoints first')
    s=s.replace(anchor,anchor+validation)
if "self.path == '/bonsai_tools'" not in s:
    anchor='    def do_GET(self):\n'
    if s.count(anchor)!=1:raise SystemExit('Unknown handler')
    s=s.replace(anchor,anchor+"""        if self.path == '/bonsai_tools':
            if not self.berechtigt():return self.antwort(401, {'fehler':'nicht berechtigt'})
            return self.antwort(200, {'modus':'fester_plan','werkzeuge':[{'werkzeug':name,'beschreibung':item[1],'schema':item[2]} for name,item in ARBEITER_WERKZEUGE.items()]})
""")
compile(s,str(p),'exec')
backup=p.with_name('werkzeuge.py.before-controlled-'+str(int(time.time())))
shutil.copy2(p,backup)
for name in ['controlled_worker.py','durable_jobs.py']:
    shutil.copy2(Path(__file__).with_name(name),args.app_dir/name)
p.write_text(s,encoding='utf-8',newline='\n')
print('Installed fixed-call worker. Restart required. Backup:',backup)
