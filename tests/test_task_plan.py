import unittest,runpy,io,sys,json,tempfile,time,threading
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,'/opt/selfwebui/integrations')
import durable_jobs as jobs
class DurableTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();jobs.ROOT=Path(self.tmp.name);jobs._active=None
 def tearDown(self):self.tmp.cleanup()
 def wait(self,ident):
  deadline=time.monotonic()+3
  while jobs._active and time.monotonic()<deadline:time.sleep(.01)
  self.assertIsNone(jobs._active)
  return jobs.load(ident)
 def test_result_survives_request_and_repeated_fetch(self):
  gate=threading.Event();calls=[]
  def runner(data):gate.wait(2);calls.append(data);return {'status':'fertig','bericht':'saved result'}
  data={'job_id':'a'*32,'auftrag':'Test'}
  first=jobs.start(data,runner)
  self.assertEqual(jobs.start(data,runner)['job_id'],first['job_id'])
  self.assertEqual(jobs.start({'auftrag':'Another'},runner)['status'],'bonsai_beschaeftigt')
  gate.set();record=self.wait(first['job_id'])
  jobs.recover()
  self.assertEqual(jobs.status(first['job_id'],lambda _: {})['steps'][0]['result']['bericht'],'saved result')
  self.assertEqual(len(calls),1)
 def test_serial_steps_and_error_stop(self):
  calls=[]
  def runner(data):
   calls.append(data)
   return {'status':'fertig' if len(calls)==1 else 'gescheitert','bericht':'first evidence'}
  result=jobs.start({'auftrag':'Review','teilauftraege':[{'titel':str(i),'auftrag':'Task'} for i in range(3)]},runner)
  record=self.wait(result['job_id']);self.assertEqual(len(calls),2)
  self.assertIn('first evidence',calls[1]['kontext']);self.assertEqual(record['phase'],'gescheitert')
 def test_restart_does_not_reexecute(self):
  jobs.save({'job_id':'b'*32,'phase':'starting','steps':[]})
  jobs.recover();self.assertEqual(jobs.load('b'*32)['phase'],'gescheitert')
 def test_invalid_plan_and_traversal(self):
  with self.assertRaises(ValueError):jobs.start({'auftrag':'test','teilauftraege':[{}]},lambda d:{})
  with self.assertRaises(ValueError):jobs.path('../secret')
class BridgeTests(unittest.TestCase):
 def test_start_returns_job_and_later_query_gets_saved_result(self):
  with patch.object(Path,'read_text',return_value='test-key'),patch.object(sys,'stdin',io.StringIO('')):
   bridge=runpy.run_path('/opt/selfwebui/integrations/bonsai_mcp.py')
  call=bridge['call'];requests=[]
  def transport(path,data=None):
   requests.append((path,data))
   if data:return {'job_id':data['job_id'],'phase':'waiting'}
   return {'job_id':path.split('=')[1],'done':False,'phase':'starting','steps':[]}
  with patch.dict(call.__globals__,request=transport):first=call({'auftrag':'Test'})
  state=json.loads(first['content'][0]['text']);self.assertFalse(state['done']);self.assertEqual(len(requests),2)
  def completed(path,data=None):return {'job_id':state['job_id'],'done':True,'phase':'fertig','steps':[{'result':{'bericht':'persisted'}}]}
  with patch.dict(call.__globals__,request=completed):second=call({'job_id':state['job_id']})
  self.assertFalse(second['isError']);self.assertIn('persisted',second['content'][0]['text'])
if __name__=='__main__':unittest.main()

