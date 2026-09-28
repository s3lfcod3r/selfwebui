import sys,types,tempfile,time,unittest,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integrations'))
sys.modules.setdefault('browser_tools',types.SimpleNamespace(begin=lambda *_:None,end=lambda:None,wait_for_release=lambda:None))
sys.modules.setdefault('worker_telemetry',types.SimpleNamespace(update=lambda *a,**k:None,completion=lambda *a:None))
import controlled_worker as worker
import durable_jobs as jobs

class ControlledTests(unittest.TestCase):
 def setUp(self):
  self.called=[];self.checkpoints=[]
  self.tools={'read':(lambda args:self.called.append(args) or {'value':391},'',{})}
  self.data={'auftrag':'test','erlaubte_aufrufe':[{'werkzeug':'read','argumente':{'path':'approved'}}],'_checkpoint':self.checkpoints.append}
 def run_worker(self,response=None,error=None,data=None):
  response=response or {'choices':[{'message':{'content':'391'}}]}
  with patch.object(worker,'bonsai_bereit',return_value=True),patch.object(worker.telemetry,'completion',return_value=response,side_effect=error) as model:
   result=worker.bonsai_auftrag(data or self.data,self.tools)
   if model.called:self.assertNotIn('tools',model.call_args.args[1])
   return result
 def test_exact_once_and_checkpoints(self):
  result=self.run_worker()
  self.assertEqual(self.called,[{'path':'approved'}]);self.assertEqual(result['status'],'fertig')
  self.assertEqual(self.checkpoints[0][0]['zustand'],'begonnen')
  self.assertEqual(self.checkpoints[1][0]['ergebnis'],{'value':391})
 def test_model_cannot_add_or_change_tool_calls(self):
  result=self.run_worker({'choices':[{'message':{'content':'','tool_calls':[{'function':{'name':'read','arguments':'{"path":"secret"}'}}]}}]})
  self.assertEqual(self.called,[{'path':'approved'}]);self.assertEqual(result['status'],'teilweise')
 def test_invalid_plans_rejected_before_effects(self):
  for changes in [{'max_werkzeugaufrufe':True},{'max_werkzeugaufrufe':0},{'max_werkzeugaufrufe':41},{'erlaubte_aufrufe':self.data['erlaubte_aufrufe']*2},{'erlaubte_aufrufe':[{'werkzeug':'unknown','argumente':{}}]}]:
   with self.assertRaises(ValueError):self.run_worker(data={**self.data,**changes})
  self.assertEqual(self.called,[])
 def test_inference_failure_keeps_results(self):
  result=self.run_worker(error=TimeoutError())
  self.assertEqual(result['status'],'teilweise');self.assertEqual(result['werkzeug_protokoll'][0]['ergebnis']['value'],391)
 def test_checkpoint_failure_prevents_effect(self):
  def fail(_):raise OSError()
  result=self.run_worker(data={**self.data,'_checkpoint':fail})
  self.assertEqual(self.called,[]);self.assertNotEqual(result['status'],'fertig')
 def test_without_plan_no_tools(self):
  self.run_worker(data={'auftrag':'compute 23*17'})
  self.assertEqual(self.called,[])
 def test_tool_failure_stops_plan(self):
  self.tools['read']=(lambda a:{'exit_code':1,'ausgabe':'failed'},'',{})
  result=self.run_worker(data={**self.data,'erlaubte_aufrufe':self.data['erlaubte_aufrufe']+[{'werkzeug':'read','argumente':{'path':'second'}}]})
  self.assertEqual(len(result['werkzeug_protokoll']),1);self.assertEqual(result['status'],'teilweise')
 def test_durable_checkpoint_and_partial_terminal(self):
  with tempfile.TemporaryDirectory() as directory:
   with patch.object(jobs,'ROOT',Path(directory)),patch.object(jobs,'request_validator',worker.validate):
    def runner(data):
     data['_checkpoint']([{'zustand':'abgeschlossen','ergebnis':391}])
     return {'status':'teilweise','bericht':'limit'}
    ident=jobs.start({'auftrag':'test'},runner)['job_id']
    deadline=time.monotonic()+3
    while jobs._active and time.monotonic()<deadline:time.sleep(.01)
    state=jobs.status(ident,lambda _: {})
    self.assertTrue(state['done']);self.assertEqual(state['steps'][0]['werkzeug_protokoll'][0]['ergebnis'],391)
    jobs.recover();self.assertEqual(jobs.load(ident)['phase'],'teilweise')
 def test_restart_keeps_uncertain_intent_without_replay(self):
  with tempfile.TemporaryDirectory() as directory,patch.object(jobs,'ROOT',Path(directory)):
   ident='c'*32;jobs.save({'job_id':ident,'phase':'starting','steps':[{'phase':'tool','werkzeug_protokoll':[{'zustand':'begonnen'}]}]})
   jobs.recover();state=jobs.load(ident)
   self.assertEqual(state['phase'],'gescheitert');self.assertEqual(state['steps'][0]['result']['werkzeug_protokoll'][0]['zustand'],'begonnen')

if __name__=='__main__':unittest.main()
