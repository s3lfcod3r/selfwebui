"""Install durable endpoints into the existing worker (restart after installation)."""
from pathlib import Path
import argparse,shutil,time
parser=argparse.ArgumentParser();parser.add_argument('--app-dir',type=Path,required=True);args=parser.parse_args()
p=args.app_dir/'werkzeuge.py';s=p.read_text()
if '# selfwebui durable jobs' not in s:
    get='    def do_GET(self):\n'
    post="        if self.path == '/browser_panel':"
    if s.count(get)!=1 or s.count(post)!=1:raise SystemExit('Unknown worker version; no change made')
    getblock="""        if self.path == '/bonsai_jobs' or self.path.startswith('/bonsai_result?'):
            if not self.berechtigt():return self.antwort(401, {'fehler':'nicht berechtigt'})
            try:
                from urllib.parse import urlparse,parse_qs
                if self.path == '/bonsai_jobs':return self.antwort(200, {'jobs':durable_jobs.listing(bonsai_arbeiter.telemetry.status)})
                job=parse_qs(urlparse(self.path).query).get('job_id',[''])[0]
                return self.antwort(200,durable_jobs.status(job,bonsai_arbeiter.telemetry.status))
            except (ValueError,OSError):return self.antwort(404, {'fehler':'Auftrag nicht gefunden'})
"""
    postblock="""        if self.path == '/bonsai_start':
            try:
                n=int(self.headers.get('Content-Length') or 0)
                if not 0<n<=262144:
                    self.close_connection=True
                    return self.antwort(413, {'fehler':'Anfrage zu groß'})
                data=json.loads(self.rfile.read(n))
                return self.antwort(200,durable_jobs.start(data,bonsai_auftrag))
            except (ValueError,TypeError):return self.antwort(400, {'fehler':'Ungültiger Auftrag'})
"""
    s=s.replace(get,get+getblock).replace(post,postblock+post)
    anchor='class Handler(BaseHTTPRequestHandler):'
    if s.count(anchor)!=1:raise SystemExit('Unknown handler')
    s=s.replace(anchor,'# selfwebui durable jobs\nimport durable_jobs\ndurable_jobs.telemetry_reader = bonsai_arbeiter.telemetry.status\ndurable_jobs.recover()\n\n'+anchor)
    shutil.copy2(p,p.with_name('werkzeuge.py.before-durable-'+str(int(time.time()))))
    p.write_text(s)
shutil.copy2(Path(__file__).with_name('durable_jobs.py'),args.app_dir/'durable_jobs.py')
print('Installed durable jobs; restart worker when idle.')
